from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class GateResult:
    passed: bool
    reason: str
    tags: list[str]
    core_included: bool  # whether to include in ROI core


def passes_evidence_gate(
    item: Dict[str, Any],
    sold_comps_count_180d: int,
    has_secondary_signal: bool,
    has_high_trust_id: bool,  # True if UPC/EAN/ASIN matched confidently
) -> GateResult:
    # High-trust ID bypass
    if has_high_trust_id:
        return GateResult(True, "High-trust ID present", ["id:trusted"], True)

    # Otherwise enforce: ≥3 sold comps within 180d AND ≥1 secondary signal
    if sold_comps_count_180d >= 3 and has_secondary_signal:
        return GateResult(
            True, "Comps+secondary OK", ["comps:>=3", "secondary:yes"], True
        )

    # Fail -> exclude from ROI core; keep as upside
    tags = []
    if sold_comps_count_180d < 3:
        tags.append("comps:<3")
    if not has_secondary_signal:
        tags.append("secondary:no")
    return GateResult(False, "Insufficient evidence for core", tags, False)
