from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .keepa_client import KeepaClient, extract_primary_asin
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


def write_ledger_jsonl(ledger: list[EvidenceRecord], out_path: str | Path):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in ledger:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
