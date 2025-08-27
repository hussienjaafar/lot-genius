from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .config import settings


@dataclass
class GateResult:
    passed: bool
    reason: str
    tags: list[str]
    core_included: bool  # whether to include in ROI core


def _ambiguity_flags(item: Dict[str, Any]) -> List[str]:
    """
    Detect ambiguity flags from item metadata that indicate lower confidence.

    Returns list of active ambiguity flags:
    - "generic:title": Title contains generic terms
    - "ambiguous:brand": Missing or empty brand (only if title exists)
    - "ambiguous:condition": Unknown or missing condition (only if item has descriptive fields)
    """
    flags = []

    # Check for generic terms in title (only if title exists)
    title = (item.get("title") or "").strip()
    if title:
        generic_terms = {
            "bundle",
            "lot",
            "assorted",
            "various",
            "pack",
            "generic",
            "case",
            "piece",
            "damaged",
            "broken",
            "repair",
            "for parts",
            "wholesale",
        }

        title_lower = title.lower()
        if any(term in title_lower for term in generic_terms):
            flags.append("generic:title")

    # Only check for missing brand/condition if we have some item metadata to work with
    # This prevents empty test items {} from triggering ambiguity flags
    has_descriptive_fields = any(
        item.get(field) for field in ["title", "brand", "condition", "category"]
    )

    if has_descriptive_fields:
        # Check for missing/empty brand (only if we have other descriptive data)
        brand_raw = item.get("brand")
        if brand_raw is None or (
            hasattr(brand_raw, "__str__") and str(brand_raw).lower() == "nan"
        ):
            brand = ""
        else:
            brand = str(brand_raw).strip()
        if not brand and title:  # Only flag missing brand if we have a title
            flags.append("ambiguous:brand")

        # Check for unknown/missing condition (only if item has other descriptive fields)
        condition_raw = item.get("condition")
        if condition_raw is None or (
            hasattr(condition_raw, "__str__") and str(condition_raw).lower() == "nan"
        ):
            condition = ""
        else:
            condition = str(condition_raw).strip().lower()
        if condition and condition in ["unknown", "unspecified"]:
            flags.append("ambiguous:condition")
        # Note: Don't flag missing condition unless it's explicitly unknown

    return flags


def passes_evidence_gate(
    item: Dict[str, Any],
    sold_comps_count_180d: int,
    has_secondary_signal: bool,
    has_high_trust_id: bool,  # True if UPC/EAN/ASIN matched confidently
) -> GateResult:
    # First enforce brand gating and hazmat policy
    brand_raw = item.get("brand")
    # Handle pandas NaN properly
    if brand_raw is None or (
        hasattr(brand_raw, "__str__") and str(brand_raw).lower() == "nan"
    ):
        brand = ""
    else:
        brand = str(brand_raw).strip().lower()
    gated = False
    gated_reason = None
    tags: list[str] = []

    # Brand gating via comma-separated list in settings
    if settings.GATED_BRANDS_CSV:
        try:
            gated_brands = {
                b.strip().lower()
                for b in settings.GATED_BRANDS_CSV.split(",")
                if b.strip()
            }
        except Exception:
            gated_brands = set()
        if brand and brand in gated_brands:
            gated = True
            gated_reason = f"Brand gated: {item.get('brand')}"
            tags.append("brand:gated")

    # Hazmat policy (from Keepa or item flag)
    hazmat_flag = False
    # Keepa may embed hazmat flag in nested blob or as flat field
    keepa_blob = item.get("keepa") or {}
    try:
        hazmat_flag = bool(item.get("hazmat") or keepa_blob.get("hazmat"))
    except Exception:
        hazmat_flag = bool(item.get("hazmat", False))
    policy = (settings.HAZMAT_POLICY or "review").strip().lower()
    if hazmat_flag:
        tags.append("hazmat")
        if policy == "exclude":
            gated = True
            gated_reason = (
                gated_reason + "; " if gated_reason else ""
            ) + "Hazmat excluded"
        elif policy == "review":
            # mark for review but allow in core unless other criteria fail
            tags.append("hazmat:review")
        else:
            tags.append("hazmat:allow")

    if gated:
        return GateResult(False, gated_reason or "Gated by policy", tags, False)

    # High-trust ID bypass (unchanged behavior)
    if has_high_trust_id:
        return GateResult(True, "High-trust ID present", ["id:trusted"] + tags, True)

    # Confidence-aware adaptive threshold calculation
    ambiguity_flags = _ambiguity_flags(item)

    # Configuration with safe defaults
    base_comps = getattr(settings, "EVIDENCE_MIN_COMPS_BASE", 3)
    bonus_per_flag = getattr(settings, "EVIDENCE_AMBIGUITY_BONUS_PER_FLAG", 1)
    max_comps = getattr(settings, "EVIDENCE_MIN_COMPS_MAX", 5)

    required_comps = min(max_comps, base_comps + bonus_per_flag * len(ambiguity_flags))

    # Add ambiguity and requirement tags
    ambiguity_tags = ambiguity_flags.copy()
    req_tag = f"conf:req_comps:{required_comps}"

    # Apply adaptive threshold: ≥required_comps sold comps AND ≥1 secondary signal
    if sold_comps_count_180d >= required_comps and has_secondary_signal:
        return GateResult(
            True,
            "Comps+secondary OK",
            [f"comps:>={required_comps}", "secondary:yes"]
            + ambiguity_tags
            + [req_tag]
            + tags,
            True,
        )

    # Fail -> exclude from ROI core; keep as upside
    fail_tags = []
    if sold_comps_count_180d < required_comps:
        # Keep legacy tag format for existing tests but also add specific count
        if required_comps == 3:
            fail_tags.append("comps:<3")  # Legacy format
        else:
            fail_tags.append(f"comps:<{required_comps}")
    if not has_secondary_signal:
        fail_tags.append("secondary:no")

    # Construct appropriate failure reason
    if sold_comps_count_180d < required_comps and not has_secondary_signal:
        reason = "Insufficient comps and no secondary signals"
    elif sold_comps_count_180d < required_comps:
        reason = "Insufficient comps"
    else:
        reason = "No secondary signals"

    return GateResult(
        False, reason, fail_tags + ambiguity_tags + [req_tag] + tags, False
    )
