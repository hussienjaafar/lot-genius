from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import pandas as pd

from .headers import map_headers
from .schema import ConditionEnum

# ---------- Public API ----------


@dataclass
class ParseResult:
    raw_path: str
    mapped_columns: Dict[str, str]
    unmapped_headers: list[str]
    df_mapped: pd.DataFrame  # mapped, before cleaning
    df_clean: pd.DataFrame  # mapped + cleaned
    df_exploded: pd.DataFrame | None  # exploded to one unit per row (if explode=True)


def parse_and_clean(
    csv_path: str | Path, fuzzy_threshold: int = 88, explode: bool = True
) -> ParseResult:
    p = Path(csv_path)
    # read with utf-8-sig to handle BOM if present (aligns with validator)
    df_raw = pd.read_csv(p, encoding="utf-8-sig")
    mapping, unmapped = map_headers(list(df_raw.columns), threshold=fuzzy_threshold)
    df_mapped = df_raw.rename(columns=mapping)

    df_clean = _clean_canonical(df_mapped.copy())

    df_exploded = _explode_quantity(df_clean) if explode else None

    return ParseResult(
        raw_path=str(p),
        mapped_columns=mapping,
        unmapped_headers=unmapped,
        df_mapped=df_mapped,
        df_clean=df_clean,
        df_exploded=df_exploded,
    )


# ---------- Cleaning/Normalization helpers ----------

_CANONICAL_STR_COLS = [
    "sku_local",
    "title",
    "brand",
    "model",
    "upc_ean_asin",
    "notes",
    "category_hint",
    "color_size_variant",
    "lot_id",
]
_CANONICAL_FLOAT_COLS = ["msrp", "est_cost_per_unit"]
_CANONICAL_INT_COLS = ["quantity"]

_CONDITION_ALIASES = {
    "new": ConditionEnum.New,
    "brandnew": ConditionEnum.New,
    "likenew": ConditionEnum.LikeNew,
    "openbox": ConditionEnum.LikeNew,
    "open_box": ConditionEnum.LikeNew,
    "usedgood": ConditionEnum.UsedGood,
    "good": ConditionEnum.UsedGood,
    "usedfair": ConditionEnum.UsedFair,
    "fair": ConditionEnum.UsedFair,
    "acceptable": ConditionEnum.UsedFair,
    "salvage": ConditionEnum.Salvage,
    "parts": ConditionEnum.Salvage,
    "forparts": ConditionEnum.Salvage,
}


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for c in _CANONICAL_FLOAT_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in _CANONICAL_INT_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(1).astype("Int64")
            # ensure strictly positive; fallback to 1 if invalid
            df.loc[(df[c].isna()) | (df[c] <= 0), c] = 1
            df[c] = df[c].astype(int)
    return df


def _strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    for c in _CANONICAL_STR_COLS:
        if c in df.columns:
            df[c] = df[c].astype(str).where(df[c].notna(), None)
            df[c] = df[c].apply(lambda x: x.strip() if isinstance(x, str) else x)
    return df


def _normalize_id_fields(df: pd.DataFrame) -> pd.DataFrame:
    # UPC/EAN/ASIN often have spaces/hyphens; keep alnum only
    if "upc_ean_asin" in df.columns:

        def _norm_id(x: str | None) -> str | None:
            if not isinstance(x, str):
                return x
            y = re.sub(r"[^0-9A-Za-z]", "", x)
            return y or None

        df["upc_ean_asin"] = df["upc_ean_asin"].apply(_norm_id)
    return df


def _normalize_condition_value(val) -> ConditionEnum | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).lower().strip()
    s = re.sub(r"[^a-z0-9]+", "", s)  # collapse spaces/punct
    return _CONDITION_ALIASES.get(s, None)


def _normalize_condition_col(df: pd.DataFrame) -> pd.DataFrame:
    if "condition" in df.columns:
        df["condition"] = df["condition"].apply(_normalize_condition_value)
        # Convert to string values of enum for consistency with GE checks (which expect strings)
        df["condition"] = df["condition"].map(
            lambda e: e.value if isinstance(e, ConditionEnum) else None
        )
    return df


def _clean_canonical(df: pd.DataFrame) -> pd.DataFrame:
    # Only operate on known canonical columns; unknown columns are left as-is
    df = _strip_strings(df)
    df = _coerce_numeric(df)
    df = _normalize_id_fields(df)
    df = _normalize_condition_col(df)
    # Title is required in Item schema; if missing, attempt to fallback from 'description' or similar (already mapped)
    # Leave strict validation to later steps; here we best-effort.
    return df


def _explode_quantity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Produce one row per physical unit, preserving a back-pointer to parent.
    Adds:
      - unit_index: 1..quantity within each original row
      - parent_row_index: original DataFrame index for traceability
    Quantity is set to 1 in the exploded DataFrame.
    """
    if "quantity" not in df.columns:
        return df.copy()
    # Ensure integer
    q = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)
    q[q <= 0] = 1

    # Repeat each row by its quantity
    repeated = df.loc[df.index.repeat(q)].copy()
    # Within each parent group, enumerate unit index
    repeated["parent_row_index"] = repeated.groupby(level=0).cumcount()  # temp
    # The cumcount above counts across entire frame; fix to 0..(n-1) per original row
    # Better: groupby original index then cumcount
    repeated["parent_row_index"] = repeated.groupby(level=0).cumcount()
    # Convert to 1-based unit index scoped to original rows
    # We need a stable grouping key of the original index; create a helper column
    repeated["__orig_idx__"] = repeated.index
    repeated["unit_index"] = repeated.groupby("__orig_idx__").cumcount() + 1
    repeated.drop(columns=["__orig_idx__"], inplace=True)

    # Normalize quantity to 1 for each unit
    repeated["quantity"] = 1

    # Optional: create a simple unit key if sku_local & lot_id exist
    if "lot_id" in repeated.columns and "sku_local" in repeated.columns:

        def _mk_key(row):
            lot = row["lot_id"] or "NA"
            sku = row["sku_local"] or "NA"
            return f"{lot}::{sku}::u{row['unit_index']}"

        repeated["unit_key"] = repeated.apply(_mk_key, axis=1)

    return repeated.reset_index(drop=True)
