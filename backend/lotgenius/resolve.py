from __future__ import annotations

import gzip
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

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

    df["asin"] = None
    df["resolved_source"] = None
    df["match_score"] = None

    client = KeepaClient()
    ledger: List[EvidenceRecord] = []

    for idx, row in df.iterrows():
        sku = row.get("sku_local") if isinstance(row.get("sku_local"), str) else None
        ident = (
            row.get("upc_ean_asin")
            if isinstance(row.get("upc_ean_asin"), str)
            else None
        )
        kind = _id_kind(ident)

        # Case 1: already an ASIN-like id
        if kind in ("asin_b0", "asin_generic"):
            asin = ident.strip().upper()
            df.at[idx, "asin"] = asin
            df.at[idx, "resolved_source"] = "direct:asin"
            meta_note = (
                "provided ASIN (B0 pattern)"
                if kind == "asin_b0"
                else "provided ASIN (generic 10-char)"
            )
            ledger.append(
                EvidenceRecord(
                    row_index=int(idx),
                    sku_local=sku,
                    upc_ean_asin=ident,
                    source="direct:asin",
                    ok=True,
                    match_asin=asin,
                    cached=True,
                    meta={"note": meta_note},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            continue

        # Case 2: UPC/EAN via Keepa
        if kind == "code" and use_network:
            resp = client.lookup_by_code(ident)
            asin = (
                extract_primary_asin(resp.get("data") or {}) if resp.get("ok") else None
            )
            if asin:
                label = (
                    "keepa:code:cached" if resp.get("cached") else "keepa:code:fresh"
                )
                df.at[idx, "asin"] = asin
                df.at[idx, "resolved_source"] = label
            ledger.append(
                EvidenceRecord(
                    row_index=int(idx),
                    sku_local=sku,
                    upc_ean_asin=ident,
                    source="keepa:code",
                    ok=bool(resp.get("ok")) and asin is not None,
                    match_asin=asin,
                    cached=resp.get("cached"),
                    meta={
                        "status": resp.get("status"),
                        "note": "code lookup",
                        "cached": bool(resp.get("cached")),
                        "products": len((resp.get("data") or {}).get("products") or []),
                        "code": ident,
                    },
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            if asin:
                continue

        # Case 3: fallback (no network)
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
                    upc_ean_asin=ident,
                    source=source,
                    ok=False,
                    match_asin=None,
                    cached=None,
                    meta={"query": query, "note": "stub - no network"},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
        else:
            ledger.append(
                EvidenceRecord(
                    row_index=int(idx),
                    sku_local=sku,
                    upc_ean_asin=ident,
                    source="fallback:none",
                    ok=False,
                    match_asin=None,
                    cached=None,
                    meta={"note": "no query available"},
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
        asin = row.get("asin")
        code = row.get("upc_ean_asin")
        resp = None
        if isinstance(asin, str) and asin:
            resp = client.fetch_stats_by_asin(asin)
        elif isinstance(code, str) and code and code.isdigit():
            resp = client.fetch_stats_by_code(code)
        else:
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

        # write to df
        if comp["price_new_median"] is not None:
            df.at[idx, "keepa_price_new_med"] = comp["price_new_median"]
        if comp["price_used_median"] is not None:
            df.at[idx, "keepa_price_used_med"] = comp["price_used_median"]
        if comp["salesrank_median"] is not None:
            df.at[idx, "keepa_salesrank_med"] = comp["salesrank_median"]
        if comp["offers_count"] is not None:
            df.at[idx, "keepa_offers_count"] = int(comp["offers_count"])

        # evidence record
        ledger.append(
            EvidenceRecord(
                row_index=int(idx),
                sku_local=(
                    row.get("sku_local")
                    if isinstance(row.get("sku_local"), str)
                    else None
                ),
                upc_ean_asin=code if isinstance(code, str) else None,
                source="keepa:stats",
                ok=ok,
                match_asin=asin if isinstance(asin, str) else None,
                cached=resp.get("cached"),
                meta={
                    "compact": comp,
                    "via": "asin" if isinstance(asin, str) and asin else "code",
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
    return df, ledger
