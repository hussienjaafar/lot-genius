from __future__ import annotations

import gzip
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .ids import normalize_asin, validate_upc_check_digit
from .keepa_client import KeepaClient, extract_primary_asin
from .keepa_extract import extract_stats_compact
from .parse import parse_and_clean


@dataclass
class EvidenceRecord:
    row_index: int
    sku_local: str | None
    upc_ean_asin: str | None
    source: str
    ok: bool
    match_asin: str | None
    cached: bool | None
    meta: Dict[str, Any]
    timestamp: str


def _id_kind(x: Optional[str]) -> str:
    if not x:
        return "none"
    s = x.strip()
    u = s.upper()
    if re.match(r"^B0[A-Z0-9]{8}$", u):
        return "asin_b0"
    if re.match(r"^[A-Z0-9]{10}$", u):
        return "asin_generic"
    if re.match(r"^\d{8,14}$", s):
        return "code"
    return "unknown"


def resolve_ids(
    csv_path: str | Path, threshold: int = 88, use_network: bool = True
) -> tuple[pd.DataFrame, List[EvidenceRecord]]:
    parsed = parse_and_clean(csv_path, fuzzy_threshold=threshold, explode=False)
    df = parsed.df_clean.copy()

    # Do not wipe existing ASIN values - preserve them for precedence logic
    if "asin" not in df.columns:
        df["asin"] = None
    df["resolved_source"] = None
    df["match_score"] = None

    client = KeepaClient()
    ledger: List[EvidenceRecord] = []

    for idx, row in df.iterrows():
        sku = row.get("sku_local") if isinstance(row.get("sku_local"), str) else None

        # Apply ID precedence: asin > upc > ean > canonical(upc_ean_asin)
        identifier_used = None
        identifier_type = None
        identifier_source = None

        # Priority 1: Explicit ASIN field
        explicit_asin = row.get("asin") if isinstance(row.get("asin"), str) else None
        if explicit_asin:
            normalized_asin = normalize_asin(explicit_asin)
            if normalized_asin:
                df.at[idx, "asin"] = normalized_asin
                df.at[idx, "resolved_source"] = "direct:asin"
                identifier_used = explicit_asin
                identifier_type = "asin"
                identifier_source = "explicit:asin"
                ledger.append(
                    EvidenceRecord(
                        row_index=int(idx),
                        sku_local=sku,
                        upc_ean_asin=row.get("upc_ean_asin"),
                        source="direct:asin",
                        ok=True,
                        match_asin=normalized_asin,
                        cached=True,
                        meta={
                            "note": "explicit ASIN field",
                            "identifier_source": identifier_source,
                            "identifier_type": identifier_type,
                            "identifier_used": identifier_used,
                        },
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
                continue

        # Priority 2: Explicit UPC field (12 digits, valid check digit)
        explicit_upc = row.get("upc") if isinstance(row.get("upc"), str) else None
        if explicit_upc and len(explicit_upc) == 12 and explicit_upc.isdigit():
            if validate_upc_check_digit(explicit_upc):
                identifier_used = explicit_upc
                identifier_type = "upc"
                identifier_source = "explicit:upc"
                if use_network:
                    resp = client.lookup_by_code(explicit_upc)
                    asin = (
                        extract_primary_asin(resp.get("data") or {})
                        if resp.get("ok")
                        else None
                    )
                    if asin:
                        label = (
                            "keepa:code:cached"
                            if resp.get("cached")
                            else "keepa:code:fresh"
                        )
                        df.at[idx, "asin"] = asin
                        df.at[idx, "resolved_source"] = label
                    ledger.append(
                        EvidenceRecord(
                            row_index=int(idx),
                            sku_local=sku,
                            upc_ean_asin=row.get("upc_ean_asin"),
                            source="keepa:code",
                            ok=bool(resp.get("ok")) and asin is not None,
                            match_asin=asin,
                            cached=resp.get("cached"),
                            meta={
                                "status": resp.get("status"),
                                "note": "explicit UPC lookup",
                                "cached": bool(resp.get("cached")),
                                "products": len(
                                    (resp.get("data") or {}).get("products") or []
                                ),
                                "code": explicit_upc,
                                "identifier_source": identifier_source,
                                "identifier_type": identifier_type,
                                "identifier_used": identifier_used,
                            },
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
                    )
                    if asin:
                        continue

        # Priority 3: Explicit EAN field (13 digits)
        explicit_ean = row.get("ean") if isinstance(row.get("ean"), str) else None
        if explicit_ean and len(explicit_ean) == 13 and explicit_ean.isdigit():
            identifier_used = explicit_ean
            identifier_type = "ean"
            identifier_source = "explicit:ean"
            if use_network:
                resp = client.lookup_by_code(explicit_ean)
                asin = (
                    extract_primary_asin(resp.get("data") or {})
                    if resp.get("ok")
                    else None
                )
                if asin:
                    label = (
                        "keepa:code:cached"
                        if resp.get("cached")
                        else "keepa:code:fresh"
                    )
                    df.at[idx, "asin"] = asin
                    df.at[idx, "resolved_source"] = label
                ledger.append(
                    EvidenceRecord(
                        row_index=int(idx),
                        sku_local=sku,
                        upc_ean_asin=row.get("upc_ean_asin"),
                        source="keepa:code",
                        ok=bool(resp.get("ok")) and asin is not None,
                        match_asin=asin,
                        cached=resp.get("cached"),
                        meta={
                            "status": resp.get("status"),
                            "note": "explicit EAN lookup",
                            "cached": bool(resp.get("cached")),
                            "products": len(
                                (resp.get("data") or {}).get("products") or []
                            ),
                            "code": explicit_ean,
                            "identifier_source": identifier_source,
                            "identifier_type": identifier_type,
                            "identifier_used": identifier_used,
                        },
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
                if asin:
                    continue

        # Priority 4: Fallback to canonical upc_ean_asin field
        canonical_id = (
            row.get("upc_ean_asin")
            if isinstance(row.get("upc_ean_asin"), str)
            else None
        )
        if canonical_id:
            kind = _id_kind(canonical_id)
            identifier_used = canonical_id
            identifier_source = "canonical"

            # Check if canonical contains ASIN
            if kind in ("asin_b0", "asin_generic"):
                asin = canonical_id.strip().upper()
                df.at[idx, "asin"] = asin
                df.at[idx, "resolved_source"] = "direct:asin"
                identifier_type = "asin"
                meta_note = (
                    "canonical ASIN (B0 pattern)"
                    if kind == "asin_b0"
                    else "canonical ASIN (generic 10-char)"
                )
                ledger.append(
                    EvidenceRecord(
                        row_index=int(idx),
                        sku_local=sku,
                        upc_ean_asin=canonical_id,
                        source="direct:asin",
                        ok=True,
                        match_asin=asin,
                        cached=True,
                        meta={
                            "note": meta_note,
                            "identifier_source": identifier_source,
                            "identifier_type": identifier_type,
                            "identifier_used": identifier_used,
                        },
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
                continue

            # Check if canonical contains UPC/EAN code
            elif kind == "code" and use_network:
                # Classify by digit count with UPC validation
                if len(canonical_id) == 12 and canonical_id.isdigit():
                    if validate_upc_check_digit(canonical_id):
                        identifier_type = "upc"
                    else:
                        identifier_type = "unknown"  # Invalid UPC, but still try lookup
                elif len(canonical_id) == 13 and canonical_id.isdigit():
                    identifier_type = "ean"
                else:
                    identifier_type = "unknown"

                resp = client.lookup_by_code(canonical_id)
                asin = (
                    extract_primary_asin(resp.get("data") or {})
                    if resp.get("ok")
                    else None
                )
                if asin:
                    label = (
                        "keepa:code:cached"
                        if resp.get("cached")
                        else "keepa:code:fresh"
                    )
                    df.at[idx, "asin"] = asin
                    df.at[idx, "resolved_source"] = label
                ledger.append(
                    EvidenceRecord(
                        row_index=int(idx),
                        sku_local=sku,
                        upc_ean_asin=canonical_id,
                        source="keepa:code",
                        ok=bool(resp.get("ok")) and asin is not None,
                        match_asin=asin,
                        cached=resp.get("cached"),
                        meta={
                            "status": resp.get("status"),
                            "note": "canonical code lookup",
                            "cached": bool(resp.get("cached")),
                            "products": len(
                                (resp.get("data") or {}).get("products") or []
                            ),
                            "code": canonical_id,
                            "identifier_source": identifier_source,
                            "identifier_type": identifier_type,
                            "identifier_used": identifier_used,
                        },
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
                if asin:
                    continue

        # Final fallback: no valid identifier found
        title = row.get("title") if isinstance(row.get("title"), str) else ""
        brand = row.get("brand") if isinstance(row.get("brand"), str) else ""
        model = row.get("model") if isinstance(row.get("model"), str) else ""
        query = " ".join([brand or "", model or ""]).strip() or (title or "").strip()
        source = "fallback:brand-model" if (brand or model) else "fallback:title"

        if query:
            ledger.append(
                EvidenceRecord(
                    row_index=int(idx),
                    sku_local=sku,
                    upc_ean_asin=canonical_id,
                    source=source,
                    ok=False,
                    match_asin=None,
                    cached=None,
                    meta={
                        "query": query,
                        "note": "stub - no network",
                        "identifier_source": "fallback",
                        "identifier_type": "unknown",
                        "identifier_used": query,
                    },
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
        else:
            ledger.append(
                EvidenceRecord(
                    row_index=int(idx),
                    sku_local=sku,
                    upc_ean_asin=canonical_id,
                    source="fallback:none",
                    ok=False,
                    match_asin=None,
                    cached=None,
                    meta={
                        "note": "no query available",
                        "identifier_source": "fallback",
                        "identifier_type": "unknown",
                        "identifier_used": None,
                    },
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

    return df, ledger


def write_ledger_jsonl(
    ledger: list[EvidenceRecord], out_path: str | Path, gzip_output: bool | None = None
):
    out_path = Path(out_path)
    if gzip_output is None:
        gzip_output = str(out_path).endswith(".gz")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if gzip_output and not str(out_path).endswith(".gz"):
        out_path = out_path.with_suffix(out_path.suffix + ".gz")
    opener = (
        (lambda p: gzip.open(p, "wt", encoding="utf-8"))
        if gzip_output
        else (lambda p: open(p, "w", encoding="utf-8"))
    )
    with opener(out_path) as f:
        for rec in ledger:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
    return out_path


def enrich_keepa_stats(df_in, use_network: bool = True):
    """
    For rows with an ASIN (or at least a code), fetch Keepa stats and
    return (df_with_columns, evidence_records).
    Adds columns (nullable):
      - keepa_price_new_med
      - keepa_price_used_med
      - keepa_salesrank_med
      - keepa_offers_count
    """
    df = df_in.copy()
    cols = [
        "keepa_price_new_med",
        "keepa_price_used_med",
        "keepa_salesrank_med",
        "keepa_offers_count",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None

    if not use_network:
        return df, []  # no-op

    client = KeepaClient()
    ledger = []
    for idx, row in df.iterrows():
        # Apply same precedence for stats: asin > upc > ean > canonical
        resp = None
        via = None
        identifier_used = None
        identifier_type = None
        identifier_source = None

        # Priority 1: Explicit ASIN
        explicit_asin = row.get("asin")
        if isinstance(explicit_asin, str) and explicit_asin:
            resp = client.fetch_stats_by_asin(explicit_asin)
            via = "asin"
            identifier_used = explicit_asin
            identifier_type = "asin"
            identifier_source = "explicit:asin"

        # Priority 2: Explicit UPC (12 digits, valid)
        elif not resp:
            explicit_upc = row.get("upc")
            if (
                isinstance(explicit_upc, str)
                and len(explicit_upc) == 12
                and explicit_upc.isdigit()
            ):
                if validate_upc_check_digit(explicit_upc):
                    resp = client.fetch_stats_by_code(explicit_upc)
                    via = "code"
                    identifier_used = explicit_upc
                    identifier_type = "upc"
                    identifier_source = "explicit:upc"

        # Priority 3: Explicit EAN (13 digits)
        if not resp:
            explicit_ean = row.get("ean")
            if (
                isinstance(explicit_ean, str)
                and len(explicit_ean) == 13
                and explicit_ean.isdigit()
            ):
                resp = client.fetch_stats_by_code(explicit_ean)
                via = "code"
                identifier_used = explicit_ean
                identifier_type = "ean"
                identifier_source = "explicit:ean"

        # Priority 4: Canonical fallback
        if not resp:
            canonical_code = row.get("upc_ean_asin")
            if (
                isinstance(canonical_code, str)
                and canonical_code
                and canonical_code.isdigit()
            ):
                resp = client.fetch_stats_by_code(canonical_code)
                via = "code"
                identifier_used = canonical_code
                identifier_source = "canonical"
                # Classify canonical by length
                if len(canonical_code) == 12:
                    if validate_upc_check_digit(canonical_code):
                        identifier_type = "upc"
                    else:
                        identifier_type = "unknown"
                elif len(canonical_code) == 13:
                    identifier_type = "ean"
                else:
                    identifier_type = "unknown"

        if not resp:
            continue

        ok = bool(resp.get("ok"))
        data = resp.get("data") or {}
        comp = (
            extract_stats_compact(data)
            if ok
            else {
                "price_new_median": None,
                "price_used_median": None,
                "salesrank_median": None,
                "offers_count": None,
            }
        )

        # write to df - use field names expected by evidence gate and pricing models
        if comp["price_new_median"] is not None:
            df.at[idx, "keepa_new_price"] = comp["price_new_median"]
            df.at[idx, "keepa_new_mu"] = comp["price_new_median"]  # Use same for mu
            df.at[idx, "keepa_price_new_med"] = comp[
                "price_new_median"
            ]  # Keep old name for compatibility
        if comp["price_used_median"] is not None:
            df.at[idx, "keepa_used_price"] = comp["price_used_median"]
            df.at[idx, "keepa_used_mu"] = comp["price_used_median"]  # Use same for mu
            df.at[idx, "keepa_price_used_med"] = comp[
                "price_used_median"
            ]  # Keep old name for compatibility
        if comp["salesrank_median"] is not None:
            df.at[idx, "keepa_salesrank_med"] = comp["salesrank_median"]
        if comp["offers_count"] is not None:
            df.at[idx, "keepa_offers_count"] = int(comp["offers_count"])

        # evidence record with enriched metadata
        ledger.append(
            EvidenceRecord(
                row_index=int(idx),
                sku_local=(
                    row.get("sku_local")
                    if isinstance(row.get("sku_local"), str)
                    else None
                ),
                upc_ean_asin=(
                    row.get("upc_ean_asin")
                    if isinstance(row.get("upc_ean_asin"), str)
                    else None
                ),
                source="keepa:stats",
                ok=ok,
                match_asin=explicit_asin if isinstance(explicit_asin, str) else None,
                cached=resp.get("cached"),
                meta={
                    "compact": comp,
                    "via": via,
                    "identifier_source": identifier_source,
                    "identifier_type": identifier_type,
                    "identifier_used": identifier_used,
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
    return df, ledger
