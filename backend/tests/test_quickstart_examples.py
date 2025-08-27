#!/usr/bin/env python3
"""
Test that quickstart examples work offline and produce ASCII-only output.
Tests demo CSV and JSON files to ensure they render valid reports without network access.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from backend.lotgenius.cli.report_lot import _mk_markdown


def test_demo_csv_loads_without_error():
    """Test that demo_manifest.csv can be loaded as valid DataFrame."""
    demo_dir = Path(__file__).parent.parent.parent / "examples" / "demo"
    demo_csv = demo_dir / "demo_manifest.csv"

    assert demo_csv.exists(), f"Demo CSV not found: {demo_csv}"

    # Load demo CSV
    df = pd.read_csv(demo_csv)

    # Basic structural validation
    assert len(df) > 0, "Demo CSV should contain at least one row"
    assert "sku_local" in df.columns, "Demo CSV should have sku_local column"
    assert "title" in df.columns, "Demo CSV should have title column"

    # Check for expected demo items
    assert len(df) == 3, "Demo CSV should contain exactly 3 items"

    # Verify data variety for demo purposes
    titles = df["title"].tolist()
    assert any(
        "iPhone" in title for title in titles
    ), "Demo should include iPhone example"
    assert any(
        "Samsung" in title for title in titles
    ), "Demo should include Samsung example"
    assert any(
        "Generic" in title for title in titles
    ), "Demo should include Generic example"


def test_demo_opt_json_loads_without_error():
    """Test that demo_opt.json can be loaded as valid optimizer config."""
    demo_dir = Path(__file__).parent.parent.parent / "examples" / "demo"
    demo_json = demo_dir / "demo_opt.json"

    assert demo_json.exists(), f"Demo JSON not found: {demo_json}"

    # Load demo JSON
    with open(demo_json, "r", encoding="utf-8") as f:
        opt_config = json.load(f)

    # Basic structural validation
    assert isinstance(opt_config, dict), "Demo JSON should be a dictionary"

    # Check for required optimizer parameters
    required_fields = ["lo", "hi", "roi_target", "risk_threshold", "sims"]
    for field in required_fields:
        assert field in opt_config, f"Demo JSON should contain {field}"

    # Validate reasonable demo values
    assert (
        opt_config["roi_target"] == 1.25
    ), "Demo should use conservative 1.25x ROI target"
    assert opt_config["risk_threshold"] == 0.80, "Demo should use 80% risk threshold"
    assert opt_config["lo"] == 0, "Demo should start bid search at 0"
    assert opt_config["hi"] > 0, "Demo should have positive max bid"


def test_report_markdown_generation_offline():
    """Test that _mk_markdown produces valid ASCII-only output with demo data."""
    demo_dir = Path(__file__).parent.parent.parent / "examples" / "demo"
    demo_csv = demo_dir / "demo_manifest.csv"
    demo_json = demo_dir / "demo_opt.json"

    # Load demo data
    df = pd.read_csv(demo_csv)
    with open(demo_json, "r", encoding="utf-8") as f:
        opt_config = json.load(f)

    # Create minimal optimizer result structure for testing
    # (In real usage, this would come from optimize_bid output)
    test_opt_result = {
        "bid": 800.0,
        "roi_target": opt_config["roi_target"],
        "risk_threshold": opt_config["risk_threshold"],
        "meets_constraints": True,
        "prob_roi_ge_target": 0.83,
        "roi_p5": 1.12,
        "roi_p50": 1.45,
        "roi_p95": 2.21,
        "expected_cash_60d": 675.50,
        "cash_60d_p5": 425.30,
        "config": opt_config,
    }

    # Generate markdown report (offline, no external calls)
    markdown_content = _mk_markdown(
        items=df,
        opt=test_opt_result,
        sweep_csv=None,
        sweep_png=None,
        evidence_jsonl=None,
    )

    # Basic structure validation
    assert isinstance(markdown_content, str), "Markdown content should be a string"
    assert len(markdown_content) > 0, "Markdown content should not be empty"

    # Check for required report sections
    required_headings = [
        "# Lot Genius Report",
        "## Executive Summary",
        "## Lot Overview",
        "## Optimization Parameters",
        "## Investment Decision",
    ]

    for heading in required_headings:
        assert heading in markdown_content, f"Report should contain heading: {heading}"

    # Verify key values are present
    assert "800.00" in markdown_content, "Report should show recommended bid"
    assert "1.25" in markdown_content, "Report should show ROI target"
    assert "0.80" in markdown_content, "Report should show risk threshold"
    assert (
        "PROCEED" in markdown_content
        or "PASS" in markdown_content
        or "REVIEW" in markdown_content
    ), "Report should contain investment decision"


def test_report_markdown_is_ascii_only():
    """Test that generated markdown contains only ASCII characters."""
    demo_dir = Path(__file__).parent.parent.parent / "examples" / "demo"
    demo_csv = demo_dir / "demo_manifest.csv"
    demo_json = demo_dir / "demo_opt.json"

    # Load demo data
    df = pd.read_csv(demo_csv)
    with open(demo_json, "r", encoding="utf-8") as f:
        opt_config = json.load(f)

    # Create test optimizer result
    test_opt_result = {
        "bid": 1200.0,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        "meets_constraints": False,  # Test PASS scenario
        "prob_roi_ge_target": 0.72,
        "roi_p5": 0.95,
        "roi_p50": 1.18,
        "roi_p95": 1.89,
        "expected_cash_60d": 890.25,
        "cash_60d_p5": 520.15,
        "config": opt_config,
    }

    # Generate markdown
    markdown_content = _mk_markdown(
        items=df,
        opt=test_opt_result,
        sweep_csv=None,
        sweep_png=None,
        evidence_jsonl=None,
    )

    # Check ASCII compliance
    try:
        markdown_content.encode("ascii")
    except UnicodeEncodeError as e:
        pytest.fail(f"Generated markdown contains non-ASCII characters: {e}")

    # Verify no Unicode symbols commonly found in reports
    unicode_chars_to_avoid = [
        "\u2705",
        "\u274c",
        "\u2192",
        "\u2190",
        "\u2191",
        "\u2193",  # Arrows and checkmarks
        "\u2265",
        "\u2264",
        "\u2260",
        "\u00b1",  # Mathematical symbols
        "\u00b0",
        "\u00d7",
        "\u00f7",  # Degree, multiply, divide
        "\u201c",
        "\u201d",
        "\u2018",
        "\u2019",  # Smart quotes
        "\u2013",
        "\u2014",  # Em/en dashes
    ]

    for char in unicode_chars_to_avoid:
        assert (
            char not in markdown_content
        ), f"Markdown should not contain Unicode character: {char}"

    # Verify expected ASCII-safe replacements are used instead
    if "PROCEED" not in markdown_content:
        # If not proceeding, should show clear ASCII decision
        assert (
            "PASS" in markdown_content or "REVIEW" in markdown_content
        ), "Should contain ASCII-safe decision indicator"


def test_demo_bundle_files_exist():
    """Test that all demo bundle files exist and are non-empty."""
    demo_dir = Path(__file__).parent.parent.parent / "examples" / "demo"

    required_files = ["demo_manifest.csv", "demo_opt.json", "demo_readme.txt"]

    for filename in required_files:
        file_path = demo_dir / filename
        assert file_path.exists(), f"Demo bundle file should exist: {filename}"
        assert (
            file_path.stat().st_size > 0
        ), f"Demo bundle file should not be empty: {filename}"


def test_getting_started_doc_exists():
    """Test that GETTING_STARTED.md exists and contains expected sections."""
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    getting_started = docs_dir / "GETTING_STARTED.md"

    assert getting_started.exists(), "GETTING_STARTED.md should exist"

    with open(getting_started, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for required sections
    required_sections = [
        "# Getting Started with Lot Genius",
        "## Option 1: Mock Demo",
        "## Option 2: Backend CLI Report Generation",
        "## Understanding the Results",
        "## Next Steps",
    ]

    for section in required_sections:
        assert section in content, f"Getting Started should contain section: {section}"


if __name__ == "__main__":
    # Allow running tests directly for development
    pytest.main([__file__, "-v"])
