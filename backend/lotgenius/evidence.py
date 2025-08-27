"""
Evidence gating and Two-Source Rule enforcement.

This module centralizes the evidence quality requirements for pricing data.
Items that don't meet the Two-Source Rule are excluded from ROI calculations
and marked as "upside" opportunities in reports.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class EvidenceResult:
    item_key: str
    has_high_trust_id: bool
    sold_comp_count: int
    lookback_days: int
    secondary_signals: Dict[str, bool]
    evidence_score: float
    include_in_core: bool
    review_reason: Optional[str] = None
    # raw traces for ledger
    sources: Dict[str, Any] = None
    timestamp: float = 0.0
    # additional computed metadata to surface in ledgers (e.g., product_confidence)
    meta: Dict[str, Any] | None = None


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "t", "yes", "y")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except Exception:
        return default


def _score(
    recency_days: int, comp_count: int, has_secondary: bool, has_id: bool
) -> float:
    # Simple monotone score: ID >> secondary >> comps >> recency
    # 0..1 scale with diminishing returns
    s = 0.0
    if has_id:
        s += 0.6
    if has_secondary:
        s += 0.2
    s += min(0.2, 0.02 * comp_count)  # 10+ comps caps at 0.2
    # recency bonus if within 60 days
    if recency_days <= 60:
        s += 0.05
    elif recency_days <= 120:
        s += 0.02
    return min(1.0, s)


def compute_evidence(
    *,
    item_key: str,
    has_high_trust_id: bool,
    sold_comps: List[Dict[str, Any]],
    lookback_days: int = None,
    secondary_signals: Dict[str, bool] | None = None,
    sources: Dict[str, Any] | None = None,
) -> EvidenceResult:
    MIN_COMPS = _env_int("EVIDENCE_MIN_COMPS", 3)
    LOOKBACK = _env_int(
        "EVIDENCE_LOOKBACK_DAYS", 180 if lookback_days is None else lookback_days
    )
    REQUIRE_SECONDARY = _env_bool("EVIDENCE_REQUIRE_SECONDARY", True)

    secondary_signals = secondary_signals or {}
    now = time.time()

    # Filter comps within lookback window if they carry 'sold_at' or similar
    # If no timestamp fields, trust caller to filter; here we count them all.
    comp_count = 0
    for c in sold_comps:
        ts = None
        for k in ("sold_at", "sold_ts", "timestamp", "date"):
            if k in c:
                ts = c[k]
                break
        if ts is None:
            # count if unknown (caller may already filtered)
            comp_count += 1
        else:
            try:
                # accept epoch or iso8601
                if isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(ts)
                else:
                    dt = datetime.fromisoformat(str(ts).replace("Z", ""))
                if (datetime.now() - dt) <= timedelta(days=LOOKBACK):
                    comp_count += 1
            except Exception:
                comp_count += 1

    has_secondary = any(secondary_signals.values())
    allow_without_secondary = not REQUIRE_SECONDARY

    include_in_core = False
    review_reason: Optional[str] = None

    if has_high_trust_id:
        include_in_core = True
    else:
        if comp_count >= MIN_COMPS and (has_secondary or allow_without_secondary):
            include_in_core = True
        else:
            include_in_core = False
            missing = []
            if comp_count < MIN_COMPS:
                missing.append(f"insufficient_comps({comp_count}<{MIN_COMPS})")
            if REQUIRE_SECONDARY and not has_secondary:
                missing.append("no_secondary_signal")
            review_reason = ";".join(missing) if missing else "low_trust"

    score = _score(LOOKBACK, comp_count, has_secondary, has_high_trust_id)
    return EvidenceResult(
        item_key=item_key,
        has_high_trust_id=has_high_trust_id,
        sold_comp_count=comp_count,
        lookback_days=LOOKBACK,
        secondary_signals=secondary_signals,
        evidence_score=score,
        include_in_core=include_in_core,
        review_reason=review_reason,
        sources=sources or {},
        timestamp=now,
        meta={},
    )


def evidence_to_dict(ev: EvidenceResult) -> Dict[str, Any]:
    d = asdict(ev)
    # compact secondary signals to names that are true
    d["secondary_active"] = [k for k, v in (ev.secondary_signals or {}).items() if v]
    return d


@dataclass
class EvidenceGateResult:
    """Result of evidence gate evaluation."""

    passes: bool
    reason: str
    details: Dict[str, Any]
    comps_count: int
    secondary_signals: List[str]


def passes_evidence_gate(
    item: Union[pd.Series, Dict[str, Any]],
    evidence_ledger: Optional[List[Dict[str, Any]]] = None,
    lookback_days: int = 180,
) -> EvidenceGateResult:
    """
    Centralized Two-Source Rule enforcement.

    Rule: Item must have ≥3 comps in past 180 days + ≥1 secondary signal

    Secondary signals include:
    - External comps (eBay, Facebook Marketplace)
    - Alternative Keepa categories (used vs new)
    - Cross-category pricing hints
    - Manual price overrides
    - Historical pricing patterns

    Args:
        item: Item data (DataFrame row or dict)
        evidence_ledger: Optional evidence records for this item
        lookback_days: Days to look back for comps (default: 180)

    Returns:
        EvidenceGateResult with pass/fail status and reasoning
    """
    if isinstance(item, pd.Series):
        item_dict = item.to_dict()
    else:
        item_dict = dict(item)

    comps_count = 0
    secondary_signals = []
    details = {}

    # Count Keepa comps in lookback period
    keepa_comps = _count_keepa_comps(item_dict, lookback_days)
    comps_count += keepa_comps
    details["keepa_comps"] = keepa_comps

    # Count external comps
    external_comps = _count_external_comps(item_dict, evidence_ledger, lookback_days)
    comps_count += external_comps
    if external_comps > 0:
        secondary_signals.append("external_comps")
    details["external_comps"] = external_comps

    # Check for secondary signals
    secondary_signals.extend(_detect_secondary_signals(item_dict, evidence_ledger))

    # Apply Two-Source Rule
    meets_comps_threshold = comps_count >= 3
    has_secondary_signal = len(secondary_signals) >= 1
    passes = meets_comps_threshold and has_secondary_signal

    if passes:
        reason = f"Passes Two-Source Rule: {comps_count} comps + {len(secondary_signals)} secondary signals"
    elif not meets_comps_threshold:
        reason = f"Insufficient comps: {comps_count} < 3 required"
    else:
        reason = f"No secondary signals found (has {comps_count} comps)"

    details.update(
        {
            "meets_comps_threshold": meets_comps_threshold,
            "has_secondary_signal": has_secondary_signal,
            "secondary_signals": secondary_signals,
            "lookback_days": lookback_days,
        }
    )

    logger.debug(f"Evidence gate for item: {reason}")

    return EvidenceGateResult(
        passes=passes,
        reason=reason,
        details=details,
        comps_count=comps_count,
        secondary_signals=secondary_signals,
    )


def _count_keepa_comps(item: Dict[str, Any], lookback_days: int) -> int:
    """Count Keepa comparables within lookback period."""
    # Look for Keepa statistics that indicate comp count
    keepa_indicators = [
        "keepa_new_count",
        "keepa_used_count",
        "keepa_sales_count",
        "keepa_n",
        "n_comps",
        "comp_count",
    ]

    total_comps = 0
    for indicator in keepa_indicators:
        if indicator in item and item[indicator] is not None:
            try:
                count = int(float(item[indicator]))
                total_comps += count
            except (ValueError, TypeError):
                continue

    # If no explicit count, infer from pricing confidence
    if total_comps == 0:
        # High confidence pricing suggests adequate comps
        mu = item.get("est_price_mu", 0)
        sigma = item.get("est_price_sigma", 0)
        if mu > 0 and sigma > 0:
            cv = sigma / mu
            if cv < 0.3:  # Low coefficient of variation suggests good comps
                total_comps = 5  # Conservative estimate
            elif cv < 0.5:
                total_comps = 3
            else:
                total_comps = 1

    return total_comps


def _count_external_comps(
    item: Dict[str, Any],
    evidence_ledger: Optional[List[Dict[str, Any]]],
    lookback_days: int,
) -> int:
    """Count external comps from evidence ledger."""
    if not evidence_ledger:
        return 0

    total_external = 0

    for evidence in evidence_ledger:
        if "external_comps_summary" in evidence:
            ext_summary = evidence["external_comps_summary"]
            if not isinstance(ext_summary, dict):
                continue

            # Prefer num_comps when present and valid
            if "num_comps" in ext_summary:
                try:
                    count = int(ext_summary["num_comps"])
                    if count >= 0:
                        total_external += count
                        continue
                except (ValueError, TypeError):
                    pass

            # Fallback to summing by_source values if present
            if "by_source" in ext_summary and isinstance(
                ext_summary["by_source"], dict
            ):
                try:
                    by_source_sum = sum(
                        int(v)
                        for v in ext_summary["by_source"].values()
                        if isinstance(v, (int, float)) and v >= 0
                    )
                    total_external += by_source_sum
                    continue
                except (ValueError, TypeError):
                    pass

            # Legacy fallback for total_comps
            if "total_comps" in ext_summary:
                try:
                    count = int(ext_summary["total_comps"])
                    if count >= 0:
                        total_external += count
                except (ValueError, TypeError):
                    pass

    return total_external


def _detect_secondary_signals(
    item: Dict[str, Any], evidence_ledger: Optional[List[Dict[str, Any]]]
) -> List[str]:
    """Detect secondary pricing signals beyond primary Keepa data."""
    signals = []

    # Check for manual price overrides
    def _has_valid_value(item_dict, key):
        """Check if item has a valid (non-None, non-NaN) value for key."""
        import pandas as pd

        value = item_dict.get(key)
        return value is not None and not pd.isna(value) and str(value).strip() != ""

    if any(
        _has_valid_value(item, key)
        for key in ["manual_price", "override_price", "expert_price"]
    ):
        signals.append("manual_override")

    # Check for multiple Keepa categories (new vs used)
    has_new = any(
        (item.get(key) or 0) > 0 for key in ["keepa_new_price", "keepa_new_mu"]
    )
    has_used = any(
        (item.get(key) or 0) > 0 for key in ["keepa_used_price", "keepa_used_mu"]
    )
    if has_new and has_used:
        signals.append("multi_condition")

    # Check for category-based pricing hints
    if _has_valid_value(item, "category_hint") or _has_valid_value(
        item, "category_name"
    ):
        signals.append("category_pricing")

    # Check for historical pricing patterns in evidence ledger
    if evidence_ledger:
        for evidence in evidence_ledger:
            if evidence.get("source", "").startswith("keepa:") and evidence.get("ok"):
                if "historical_trend" in evidence.get("meta", {}):
                    signals.append("historical_trend")
                    break

    # Check for price confidence indicators
    est_price_mu = item.get("est_price_mu", 0)
    est_price_sigma = item.get("est_price_sigma", 0)
    if est_price_mu > 0 and est_price_sigma > 0:
        cv = est_price_sigma / est_price_mu
        if cv < 0.2:  # Very low variance suggests strong signal
            signals.append("high_confidence")

    # Check for UPC/ASIN resolution as quality signal
    if item.get("asin") and item.get("resolved_source") == "direct:asin":
        signals.append("direct_asin")

    return list(set(signals))  # Remove duplicates


def filter_items_by_evidence_gate(
    df: pd.DataFrame, evidence_ledger: Optional[List[Dict[str, Any]]] = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filter DataFrame by evidence gate, returning (passed, failed) items.

    Args:
        df: DataFrame of items to filter
        evidence_ledger: Evidence records for items

    Returns:
        (passed_items_df, failed_items_df)
    """
    passed_items = []
    failed_items = []

    for idx, row in df.iterrows():
        # Use centralized gating logic
        from .gating import passes_evidence_gate as central_gate

        # Extract gate parameters from row/evidence
        # Handle pandas NaN values properly - NaN is truthy but not a valid ID
        def _is_valid_id(value):
            """Check if value is a valid ID (not None, NaN, or empty string)."""
            import pandas as pd

            return value is not None and not pd.isna(value) and str(value).strip() != ""

        has_high_trust_id = (
            _is_valid_id(row.get("asin"))
            or _is_valid_id(row.get("upc"))
            or _is_valid_id(row.get("ean"))
        )

        # Count primary comps from Keepa
        keepa_comps = int(
            (row.get("keepa_new_count") or 0) + (row.get("keepa_used_count") or 0)
        )

        # Add external comps from evidence ledger
        external_comps = _count_external_comps(dict(row), evidence_ledger, 180)
        sold_comps_180d = keepa_comps + external_comps

        # Check for secondary signals (rank trend, offer depth, etc.)
        basic_secondary_signals = [
            (row.get("keepa_offers_count") or 0) > 0,  # offer depth
            _is_valid_id(row.get("keepa_salesrank_med")),  # rank data
            _is_valid_id(row.get("manual_price")),  # manual override
        ]

        # Add external comps as secondary signal
        advanced_secondary_signals = _detect_secondary_signals(
            dict(row), evidence_ledger
        )
        if external_comps > 0:
            advanced_secondary_signals.append("external_comps")

        has_secondary_signal = (
            any(basic_secondary_signals) or len(advanced_secondary_signals) > 0
        )

        gate_result = central_gate(
            dict(row),
            sold_comps_count_180d=sold_comps_180d,
            has_secondary_signal=has_secondary_signal,
            has_high_trust_id=has_high_trust_id,
        )

        # Add evidence gate metadata to row
        row_with_gate = row.copy()
        row_with_gate["evidence_gate_passes"] = gate_result.passed
        row_with_gate["evidence_gate_reason"] = gate_result.reason
        row_with_gate["evidence_gate_tags"] = ",".join(gate_result.tags)
        row_with_gate["evidence_core_included"] = gate_result.core_included

        if gate_result.passed:
            passed_items.append(row_with_gate)
        else:
            failed_items.append(row_with_gate)

    passed_df = pd.DataFrame(passed_items) if passed_items else pd.DataFrame()
    failed_df = pd.DataFrame(failed_items) if failed_items else pd.DataFrame()

    logger.info(
        f"Evidence gate: {len(passed_items)} passed, {len(failed_items)} failed"
    )

    return passed_df, failed_df


def mark_items_as_upside(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mark items that failed evidence gate as 'upside' opportunities.

    These items are excluded from core ROI calculations but tracked
    separately as potential value if evidence improves.
    """
    df_marked = df.copy()
    df_marked["item_category"] = "upside"
    df_marked["upside_reason"] = df_marked.get(
        "evidence_gate_reason", "Failed evidence gate"
    )

    return df_marked


# Global evidence ledger for real evidence writing
_global_evidence_ledger: List[Dict[str, Any]] = []


def write_evidence(
    item: Dict[str, Any], source: str, data: Dict[str, Any], ok: bool = True
) -> None:
    """
    Write evidence record to the global evidence ledger.

    This is the real evidence writer that external_comps should use
    instead of maintaining its own local stub.
    """
    from .ids import extract_ids
    from .resolve import EvidenceRecord

    ids = extract_ids(item)
    # Flatten data into meta for easier downstream access while also
    # preserving the original payload under a 'data' key for compatibility.
    meta_payload: Dict[str, Any] = {"item_title": item.get("title")}
    try:
        if isinstance(data, dict):
            meta_payload.update(data)
            meta_payload.setdefault("data", data)
        else:
            meta_payload["data"] = data
    except Exception:
        meta_payload["data"] = data

    record = EvidenceRecord(
        row_index=item.get("row_index"),
        sku_local=item.get("sku_local"),
        upc_ean_asin=ids["upc_ean_asin"] or ids["asin"],
        source=source,
        ok=ok,
        match_asin=ids["asin"],
        cached=False,
        meta=meta_payload,
        timestamp=datetime.now().isoformat(),
    )
    _global_evidence_ledger.append(record.__dict__)
