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
    "asin",
    "upc",
    "ean",
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
    # Normalize individual ID fields first
    def _norm_id(x: str | None) -> str | None:
        if not isinstance(x, str):
            return x
        y = re.sub(r"[^0-9A-Za-z]", "", x)
        return y or None

    # Normalize separate ID fields
    for id_field in ["asin", "upc", "ean"]:
        if id_field in df.columns:
            df[id_field] = df[id_field].apply(_norm_id)

    # Normalize canonical field if present
    if "upc_ean_asin" in df.columns:
        df["upc_ean_asin"] = df["upc_ean_asin"].apply(_norm_id)

    # Populate canonical upc_ean_asin with precedence: asin > upc > ean > existing canonical
    # Create the canonical column if any ID fields exist
    has_id_fields = any(
        field in df.columns for field in ["asin", "upc", "ean", "upc_ean_asin"]
    )

    if has_id_fields:
        # Ensure canonical column exists
        if "upc_ean_asin" not in df.columns:
            df["upc_ean_asin"] = None

        def _populate_canonical(row):
            # If canonical already has a value and no separate fields, keep it
            canonical_val = row.get("upc_ean_asin")
            asin_val = row.get("asin")
            upc_val = row.get("upc")
            ean_val = row.get("ean")

            # Apply precedence: asin > upc > ean > existing canonical
            if asin_val:
                return asin_val
            elif upc_val:
                return upc_val
            elif ean_val:
                return ean_val
            else:
                return canonical_val

        df["upc_ean_asin"] = df.apply(_populate_canonical, axis=1)

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
      - parent_row_index: original row index before explosion
      - unit_index: 1..quantity within each parent
    Sets quantity=1 on all exploded rows.
    """
    if "quantity" not in df.columns:
        return df.copy()

    # Coerce & clamp quantity
    q = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)
    q[q <= 0] = 1

    # Capture original index as parent pointer, then repeat by quantity
    base = df.reset_index(drop=False).rename(columns={"index": "parent_row_index"})
    repeated = base.loc[base.index.repeat(q)].copy()

    # Unit index is 1..n within each original parent row
    repeated["unit_index"] = repeated.groupby("parent_row_index").cumcount() + 1

    # Normalize quantity to 1 for each unit
    repeated["quantity"] = 1

    # Optional unit key for convenience
    if "lot_id" in repeated.columns and "sku_local" in repeated.columns:

        def _mk_key(row):
            lot = row["lot_id"] or "NA"
            sku = row["sku_local"] or "NA"
            return f"{lot}::{sku}::u{row['unit_index']}"

        repeated["unit_key"] = repeated.apply(_mk_key, axis=1)

    return repeated.reset_index(drop=True)
