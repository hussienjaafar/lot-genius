from pathlib import Path

from lotgenius.validation import validate_manifest_csv


def test_golden_manifests_pass(tmp_path: Path):
    # Validate a few golden manifests
    base = Path("data/golden_manifests")
    to_check = [
        "01_basic.csv",
        "02_aliases.csv",
        "03_minimal.csv",
        "04_qty_variants.csv",
        "06_condition_mixed.csv",
    ]
    for name in to_check:
        rep = validate_manifest_csv(base / name, fuzzy_threshold=85)
        assert rep.passed, f"{name} failed: {rep.notes}"


def test_bad_low_coverage_fails():
    rep = validate_manifest_csv(
        "data/golden_manifests/bad_low_coverage.csv", fuzzy_threshold=85
    )
    assert not rep.passed
    assert rep.header_coverage < 0.70
