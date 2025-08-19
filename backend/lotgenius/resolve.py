from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pandas as pd

from .keepa_client import KeepaClient, extract_primary_asin
from .schema import Item


@dataclass
class Evidence:
    """Evidence entry for tracking resolution attempts"""

    source: str  # e.g., "keepa_lookup", "title_search_stub"
    timestamp: str  # ISO format
    raw: dict
    asin: str | None = None
    success: bool = False


@dataclass
class ResolutionResult:
    """Result of attempting to resolve an Item to ASIN"""

    item: Item
    asin: str | None = None
    success: bool = False
    evidence: List[Evidence] = field(default_factory=list)


def resolve_item_to_asin(
    item: Item, keepa_client: Optional[KeepaClient] = None
) -> ResolutionResult:
    """
    Attempts to resolve an Item to an ASIN using multiple strategies:
    1. Lookup by UPC/EAN/ASIN via Keepa
    2. Fallback to title search (stubbed for Step 5)

    Returns ResolutionResult with evidence ledger.
    """
    if keepa_client is None:
        keepa_client = KeepaClient()

    result = ResolutionResult(item=item)
    timestamp = datetime.utcnow().isoformat()

    # Strategy 1: Direct code lookup via Keepa
    if item.upc_ean_asin:
        try:
            keepa_resp = keepa_client.lookup_by_code(item.upc_ean_asin)
            evidence = Evidence(
                source="keepa_lookup", timestamp=timestamp, raw=keepa_resp
            )

            if keepa_resp.get("ok"):
                asin = extract_primary_asin(keepa_resp.get("data", {}))
                if asin:
                    evidence.asin = asin
                    evidence.success = True
                    result.asin = asin
                    result.success = True

            result.evidence.append(evidence)

            # If successful, return early
            if result.success:
                return result

        except Exception as e:
            # Log but continue to fallback strategies
            evidence = Evidence(
                source="keepa_lookup",
                timestamp=timestamp,
                raw={"error": str(e)},
                success=False,
            )
            result.evidence.append(evidence)

    # Strategy 2: Title search fallback (stubbed for Step 5)
    if item.title:
        try:
            # For Step 5, we use the stubbed title search
            search_resp = keepa_client.search_by_title(item.title)
            evidence = Evidence(
                source="title_search_stub",
                timestamp=timestamp,
                raw=search_resp,
                success=False,  # Always false for stub
            )
            result.evidence.append(evidence)

        except Exception as e:
            evidence = Evidence(
                source="title_search_stub",
                timestamp=timestamp,
                raw={"error": str(e)},
                success=False,
            )
            result.evidence.append(evidence)

    return result


def resolve_dataframe(
    df: pd.DataFrame, keepa_client: Optional[KeepaClient] = None
) -> tuple[pd.DataFrame, List[dict]]:
    """
    Resolve a DataFrame of items to ASINs.

    Args:
        df: DataFrame with Item-compatible columns
        keepa_client: Optional KeepaClient instance

    Returns:
        tuple of (enriched_df, evidence_ledger)
        - enriched_df: Original DataFrame with additional 'resolved_asin' column
        - evidence_ledger: List of evidence entries (JSONL-ready dicts)
    """
    if keepa_client is None:
        keepa_client = KeepaClient()

    enriched_df = df.copy()
    enriched_df["resolved_asin"] = None
    evidence_ledger = []

    for idx, row in df.iterrows():
        # Convert row to Item for resolution
        try:
            # Create Item from row, handling missing columns gracefully
            item_data = {}
            for field_name in [
                "title",
                "brand",
                "model",
                "upc_ean_asin",
                "condition",
                "notes",
                "category_hint",
                "color_size_variant",
            ]:
                if field_name in row.index:
                    item_data[field_name] = row[field_name]

            # Required fields with defaults
            item_data.setdefault("title", "")
            item_data.setdefault("condition", "New")

            item = Item(**item_data)

            # Resolve the item
            resolution = resolve_item_to_asin(item, keepa_client)

            # Update enriched DataFrame
            if resolution.success and resolution.asin:
                enriched_df.at[idx, "resolved_asin"] = resolution.asin

            # Add evidence to ledger
            for evidence in resolution.evidence:
                ledger_entry = {
                    "row_index": int(idx),
                    "source": evidence.source,
                    "timestamp": evidence.timestamp,
                    "raw": evidence.raw,
                    "asin": evidence.asin,
                    "success": evidence.success,
                    "item_title": item.title,
                    "item_upc_ean_asin": item.upc_ean_asin,
                }
                evidence_ledger.append(ledger_entry)

        except Exception as e:
            # Log error but continue processing
            logging.warning(f"Failed to resolve row {idx}: {e}")
            evidence_entry = {
                "row_index": int(idx),
                "source": "resolution_error",
                "timestamp": datetime.utcnow().isoformat(),
                "raw": {"error": str(e)},
                "asin": None,
                "success": False,
                "item_title": row.get("title", ""),
                "item_upc_ean_asin": row.get("upc_ean_asin", ""),
            }
            evidence_ledger.append(evidence_entry)

    return enriched_df, evidence_ledger
