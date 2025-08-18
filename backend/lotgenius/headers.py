from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Tuple

from rapidfuzz import fuzz, process

# Canonical destination fields (underscore style)
CANONICAL = [
    "sku_local",
    "title",
    "brand",
    "model",
    "upc_ean_asin",
    "condition",
    "quantity",
    "est_cost_per_unit",
    "notes",
    "category_hint",
    "msrp",
    "color_size_variant",
    "lot_id",
]

# Synonyms for first-pass exact/normalized checks
SYNONYMS: Dict[str, list[str]] = {
    "upc_ean_asin": [
        "UPC",
        "UPC Code",
        "Barcode",
        "EAN",
        "GTIN",
        "ASIN",
        "UPC/EAN",
        "Product Code",
    ],
    "condition": ["Condition", "Cond.", "Grade", "Grading", "Item Condition"],
    "quantity": ["Qty", "QTY", "QTY.", "Quantity", "Count", "Units"],
    "est_cost_per_unit": [
        "Unit Cost",
        "Cost/Unit",
        "Est. Cost Per Unit",
        "Price Paid Per Unit",
        "Unit Price",
    ],
    "msrp": ["MSRP", "List Price", "Retail Price", "SRP"],
    "brand": ["Brand", "Mfr", "Manufacturer", "Maker"],
    "model": ["Model", "Model #", "Model Number", "M/N", "Part No", "PN", "SKU Model"],
    "category_hint": ["Category", "Dept", "Department", "Type", "Class"],
    "title": ["Title", "Item Name", "Product Title", "Name", "Description"],
    "sku_local": ["SKU", "Seller SKU", "Internal SKU", "Item ID", "Local SKU"],
    "notes": ["Notes", "Comments", "Remark", "Memo"],
    "color_size_variant": [
        "Variant",
        "Options",
        "Style",
        "Color",
        "Size",
        "Color/Size",
        "Attributes",
    ],
    "lot_id": ["Lot", "Pallet", "Manifest ID", "Auction Lot", "Lot ID"],
}

# Where we remember confirmed header→canonical mappings
ALIAS_STORE = Path("data/aliases/header_aliases.json")


def _normalize(s: str) -> str:
    return "".join(ch for ch in s.lower().strip() if ch.isalnum())


def _load_aliases() -> Dict[str, str]:
    if ALIAS_STORE.exists():
        try:
            return json.loads(ALIAS_STORE.read_text())
        except Exception:
            return {}
    return {}


def _save_aliases(aliases: Dict[str, str]) -> None:
    ALIAS_STORE.parent.mkdir(parents=True, exist_ok=True)
    ALIAS_STORE.write_text(json.dumps(aliases, indent=2, ensure_ascii=False))


def learn_alias(source_header: str, canonical: str) -> None:
    """Persist a confirmed mapping header→canonical."""
    if canonical not in CANONICAL:
        raise ValueError(f"Unknown canonical field: {canonical}")
    aliases = _load_aliases()
    aliases[source_header] = canonical
    _save_aliases(aliases)


def map_headers(
    headers: Iterable[str], threshold: int = 88
) -> Tuple[Dict[str, str], list[str]]:
    """
    Map source CSV headers to canonical fields using:
      1) learned aliases
      2) synonym exact/normalized match
      3) RapidFuzz fuzzy match against canonical+synonyms
    Returns (mapping, unmapped_headers)
    """
    aliases = _load_aliases()
    mapping: Dict[str, str] = {}
    unmapped: list[str] = []

    # Build candidate list for fuzzy search
    candidates = set(CANONICAL)
    for k, syns in SYNONYMS.items():
        candidates.add(k)
        candidates.update(syns)
    candidates_list = list(candidates)

    for h in headers:
        h_stripped = h.strip()
        # learned alias?
        if h_stripped in aliases:
            mapping[h_stripped] = aliases[h_stripped]
            continue
        # synonym exact/normalized
        norm = _normalize(h_stripped)
        found = False
        for dest, syns in SYNONYMS.items():
            if norm == _normalize(dest) or any(norm == _normalize(s) for s in syns):
                mapping[h_stripped] = dest
                found = True
                break
        if found:
            continue
        # fuzzy
        best, score, _ = process.extractOne(
            h_stripped, candidates_list, scorer=fuzz.WRatio
        )
        if score >= threshold:
            # Map synonym hit back to its canonical key
            dest = (
                best
                if best in CANONICAL
                else next((k for k, v in SYNONYMS.items() if best in v), None)
            )
            if dest:
                mapping[h_stripped] = dest
                continue
        unmapped.append(h_stripped)

    # ensure we don't map multiple source headers to same canonical when avoidable
    # (leave as-is; later steps can add disambiguation UI)
    return mapping, unmapped


def suggest_candidates(src_header: str, top_k: int = 5) -> list[dict]:
    """
    Return top-k fuzzy candidates for a source header.
    Each item: {"candidate": str, "canonical": str|None, "score": int}
    """
    # Build same candidate universe as map_headers
    candidates = set(CANONICAL)
    for k, syns in SYNONYMS.items():
        candidates.add(k)
        candidates.update(syns)
    cand_list = list(candidates)

    results = process.extract(src_header, cand_list, scorer=fuzz.WRatio, limit=top_k)
    out = []
    for cand, score, _ in results:
        if cand in CANONICAL:
            canonical = cand
        else:
            canonical = next((k for k, v in SYNONYMS.items() if cand in v), None)
        out.append({"candidate": cand, "canonical": canonical, "score": int(score)})
    return out
