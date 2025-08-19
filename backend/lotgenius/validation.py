from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .ge_suite import run_ge_checks
from .headers import map_headers

# Thresholds (tunable later via config if needed)
HEADER_COVERAGE_MIN = 0.70  # ≥70% of source headers should map to some canonical field

CANONICAL_COLS = {
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
}


@dataclass
class ValidationReport:
    path: str
    header_coverage: float
    total_headers: int
    mapped_headers: int
    unmapped_headers: list[str]
    ge_success: bool
    ge_results: list[dict]
    passed: bool
    notes: list[str]


def _apply_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    # Rename mapped columns to canonical names; leave others as-is
    renamed = df.rename(columns=mapping)
    return renamed


def validate_manifest_csv(
    csv_path: str | Path, fuzzy_threshold: int = 88
) -> ValidationReport:
    p = Path(csv_path)
    df = pd.read_csv(p)

    # Compute mapping and coverage
    mapping, unmapped = map_headers(list(df.columns), threshold=fuzzy_threshold)
    mapped_headers = len(mapping)
    total_headers = len(df.columns)
    header_coverage = mapped_headers / max(1, total_headers)

    mapped_df = _apply_mapping(df, mapping)

    # Basic content sanity: if canonical columns exist, ensure types are sensible (coerce where easy)
    if "quantity" in mapped_df.columns:
        mapped_df["quantity"] = pd.to_numeric(mapped_df["quantity"], errors="coerce")

    if "msrp" in mapped_df.columns:
        mapped_df["msrp"] = pd.to_numeric(mapped_df["msrp"], errors="coerce")

    # Great Expectations light checks (only on columns that exist)
    ge = run_ge_checks(mapped_df)

    # Decide pass/fail
    passed = (header_coverage >= HEADER_COVERAGE_MIN) and ge["success"]

    notes: list[str] = []
    if header_coverage < HEADER_COVERAGE_MIN:
        notes.append(
            f"Header coverage {header_coverage:.0%} below threshold {HEADER_COVERAGE_MIN:.0%}."
        )
    if not ge["success"]:
        bad = [r for r in ge["results"] if not r["success"]]
        notes.append(f"GE checks failed: {[r['expectation'] for r in bad]}")

    return ValidationReport(
        path=str(p),
        header_coverage=header_coverage,
        total_headers=total_headers,
        mapped_headers=mapped_headers,
        unmapped_headers=unmapped,
        ge_success=ge["success"],
        ge_results=ge["results"],
        passed=passed,
        notes=notes,
    )
