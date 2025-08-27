import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from click.testing import CliRunner
from lotgenius.cli.report_lot import main as cli


@pytest.fixture
def sample_items():
    """Sample items CSV data."""
    return pd.DataFrame(
        [
            {
                "sku_local": "X1",
                "est_price_mu": 60.0,
                "est_price_p50": 55.0,
                "sell_p60": 0.7,
            },
            {
                "sku_local": "X2",
                "est_price_mu": 40.0,
                "est_price_p50": 38.0,
                "sell_p60": 0.6,
            },
        ]
    )


@pytest.fixture
def sample_optimizer():
    """Sample optimizer JSON data."""
    return {
        "bid": 75.0,
        "roi_p50": 1.35,
        "prob_roi_ge_target": 0.82,
        "expected_cash_60d": 45.0,
        "meets_constraints": True,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
    }


def test_report_lot_basic(tmp_path, sample_items, sample_optimizer):
    """Test basic report generation with markdown output only."""
    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(sample_optimizer), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
        ],
    )

    assert result.exit_code == 0
    assert out_md.exists()

    # Check markdown content
    md_content = out_md.read_text(encoding="utf-8")
    assert "# Lot Genius Report" in md_content
    assert "Executive Summary" in md_content
    assert "$75.00" in md_content  # recommended bid
    assert "1.35x" in md_content  # ROI P50
    assert "82.0%" in md_content  # probability
    assert (
        "Yes" in md_content
    )  # meets constraints (emoji formatter in executive summary)
    assert "ROI Target:" in md_content  # Executive Summary bullets when present
    assert "Risk Threshold:" in md_content  # Executive Summary bullets when present
    # Verify Executive Summary bullets appear with bold formatting
    assert "- ROI Target: **" in md_content
    assert "- Risk Threshold: **" in md_content
    assert "- ROI Target: **1.25x**" in md_content
    assert "- Risk Threshold: **P(ROI>=target) >= 0.80**" in md_content

    # Check JSON output
    output_data = json.loads(result.output)
    assert output_data["out_markdown"] == str(out_md)
    assert output_data["out_html"] is None
    assert output_data["out_pdf"] is None


def test_report_lot_with_artifacts(tmp_path, sample_items, sample_optimizer):
    """Test report generation with artifact references."""
    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"
    sweep_csv = tmp_path / "sweep.csv"
    sweep_png = tmp_path / "sweep.png"
    evidence_jsonl = tmp_path / "evidence.jsonl"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(sample_optimizer), encoding="utf-8")
    # Create all artifact files so they show up
    Path(sweep_csv).write_text("dummy\n", encoding="utf-8")
    Path(sweep_png).write_text("dummy\n", encoding="utf-8")
    Path(evidence_jsonl).write_text('{"source":"test"}\n', encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
            "--sweep-csv",
            str(sweep_csv),
            "--sweep-png",
            str(sweep_png),
            "--evidence-jsonl",
            str(evidence_jsonl),
        ],
    )

    assert result.exit_code == 0

    # Check artifact references in markdown
    md_content = out_md.read_text(encoding="utf-8")
    assert "Supporting Artifacts" in md_content
    assert str(sweep_csv) in md_content
    assert str(sweep_png) in md_content
    assert str(evidence_jsonl) in md_content

    # Check JSON output includes artifacts
    output_data = json.loads(result.output)
    artifacts = output_data["artifact_references"]
    assert artifacts["sweep_csv"] == str(sweep_csv)
    assert artifacts["sweep_png"] == str(sweep_png)
    assert artifacts["evidence_jsonl"] == str(evidence_jsonl)


def test_report_lot_fails_constraints(tmp_path, sample_items):
    """Test report generation when constraints are not met."""
    opt_fail = {
        "bid": 0.0,
        "roi_p50": 0.8,
        "prob_roi_ge_target": 0.0,
        "expected_cash_60d": 0.0,
        "meets_constraints": False,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
    }

    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(opt_fail), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
        ],
    )

    assert result.exit_code == 0

    # Check failure indication in markdown
    md_content = out_md.read_text(encoding="utf-8")
    assert "**PASS**" in md_content
    assert "**Meets All Constraints:** No" in md_content
    assert "does not meet" in md_content


@patch("subprocess.run")
def test_report_lot_html_conversion_success(
    mock_run, tmp_path, sample_items, sample_optimizer
):
    """Test successful HTML conversion with pandoc."""
    mock_run.return_value.returncode = 0

    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"
    out_html = tmp_path / "report.html"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(sample_optimizer), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
            "--out-html",
            str(out_html),
        ],
    )

    assert result.exit_code == 0
    mock_run.assert_called_once()

    # Check that pandoc was called correctly
    args, kwargs = mock_run.call_args
    assert "pandoc" in args[0]
    assert str(out_md) in args[0]
    assert str(out_html) in args[0]

    # Check JSON output
    output_data = json.loads(result.output)
    assert output_data["out_html"] == str(out_html)


@patch("subprocess.run")
def test_report_lot_pdf_conversion_success(
    mock_run, tmp_path, sample_items, sample_optimizer
):
    """Test successful PDF conversion with pandoc."""
    mock_run.return_value.returncode = 0

    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"
    out_pdf = tmp_path / "report.pdf"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(sample_optimizer), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
            "--out-pdf",
            str(out_pdf),
        ],
    )

    assert result.exit_code == 0
    mock_run.assert_called_once()

    # Check that pandoc was called with PDF options
    args, kwargs = mock_run.call_args
    assert "pandoc" in args[0]
    assert "--pdf-engine=pdflatex" in args[0]

    # Check JSON output
    output_data = json.loads(result.output)
    assert output_data["out_pdf"] == str(out_pdf)


@patch("subprocess.run", side_effect=FileNotFoundError())
def test_report_lot_pandoc_not_found(
    mock_run, tmp_path, sample_items, sample_optimizer
):
    """Test graceful handling when pandoc is not available."""
    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"
    out_html = tmp_path / "report.html"

    sample_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(sample_optimizer), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
            "--out-html",
            str(out_html),
        ],
    )

    assert result.exit_code == 0
    assert "pandoc not found" in result.output

    # Check that markdown was still generated
    assert out_md.exists()

    # Extract JSON from output (it should be after the warning)
    output_lines = result.output.strip().split("\n")
    json_start = -1
    for i, line in enumerate(output_lines):
        if line.strip().startswith("{"):
            json_start = i
            break

    assert json_start >= 0, "No JSON found in output"
    json_output = "\n".join(output_lines[json_start:])
    output_data = json.loads(json_output)
    assert output_data["out_html"] is None


def test_report_lot_missing_columns(tmp_path):
    """Test report generation with minimal/missing columns."""
    minimal_items = pd.DataFrame([{"sku_local": "X1"}])
    minimal_opt = {"bid": 100.0}

    items_csv = tmp_path / "items.csv"
    opt_json = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"

    minimal_items.to_csv(items_csv, index=False)
    Path(opt_json).write_text(json.dumps(minimal_opt), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--items-csv",
            str(items_csv),
            "--opt-json",
            str(opt_json),
            "--out-markdown",
            str(out_md),
        ],
    )

    assert result.exit_code == 0
    assert out_md.exists()

    # Should handle missing data gracefully
    md_content = out_md.read_text(encoding="utf-8")
    assert "N/A" in md_content  # Should show N/A for missing values
    assert (
        "Meets All Constraints:** N/A" in md_content
    )  # Always show meets constraints as Yes/No/N/A


def test_report_meets_na_when_missing(tmp_path):
    """Test that meets_constraints shows N/A when missing from opt.json."""
    import json
    from pathlib import Path

    import pandas as pd
    from click.testing import CliRunner
    from lotgenius.cli.report_lot import main as cli

    items = pd.DataFrame([{"sku_local": "A"}])
    opt = {"bid": 100.0}
    in_csv = tmp_path / "items.csv"
    oj = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"
    items.to_csv(in_csv, index=False)
    Path(oj).write_text(json.dumps(opt), encoding="utf-8")
    res = CliRunner().invoke(
        cli,
        [
            "--items-csv",
            str(in_csv),
            "--opt-json",
            str(oj),
            "--out-markdown",
            str(out_md),
        ],
    )
    assert res.exit_code == 0
    md = out_md.read_text(encoding="utf-8")
    assert "Meets All Constraints" in md and ("N/A" in md)
    assert "**REVIEW**" in md  # Should show REVIEW state for missing meets_constraints


def test_report_wires_roi_and_risk_from_opt(tmp_path):
    """Test that ROI target and risk threshold are wired from opt.json."""
    import json
    from pathlib import Path

    import pandas as pd
    from click.testing import CliRunner
    from lotgenius.cli.report_lot import main as cli

    items = pd.DataFrame([{"sku_local": "A"}])
    opt = {
        "bid": 200.0,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
        "meets_constraints": True,
    }
    in_csv = tmp_path / "items.csv"
    oj = tmp_path / "opt.json"
    out_md = tmp_path / "report.md"
    items.to_csv(in_csv, index=False)
    Path(oj).write_text(json.dumps(opt), encoding="utf-8")
    res = CliRunner().invoke(
        cli,
        [
            "--items-csv",
            str(in_csv),
            "--opt-json",
            str(oj),
            "--out-markdown",
            str(out_md),
        ],
    )
    assert res.exit_code == 0
    md = out_md.read_text(encoding="utf-8")
    assert "ROI Target:" in md and "1.25" in md
    assert "Risk Threshold:" in md and "0.80" in md
    assert "Meets All Constraints" in md and ("Yes" in md)


def test_report_review_and_no_artifacts_when_missing(tmp_path):
    """Test missing meets => REVIEW and no artifacts."""
    import json
    from pathlib import Path

    import pandas as pd
    from click.testing import CliRunner
    from lotgenius.cli.report_lot import main as cli

    items = pd.DataFrame([{"sku_local": "A"}])
    p_items = tmp_path / "i.csv"
    items.to_csv(p_items, index=False)
    p_opt = tmp_path / "o.json"
    p_out = tmp_path / "r.md"
    Path(p_opt).write_text(json.dumps({"bid": 100.0}), encoding="utf-8")
    res = CliRunner().invoke(
        cli,
        [
            "--items-csv",
            str(p_items),
            "--opt-json",
            str(p_opt),
            "--out-markdown",
            str(p_out),
        ],
    )
    assert res.exit_code == 0
    md = p_out.read_text(encoding="utf-8")
    assert "Meets All Constraints" in md and "N/A" in md
    assert "REVIEW" in md
    assert "Supporting Artifacts" not in md


def test_report_proceed_and_knobs_from_opt(tmp_path):
    """Test knobs in opt => PROCEED and correct values."""
    import json
    from pathlib import Path

    import pandas as pd
    from click.testing import CliRunner
    from lotgenius.cli.report_lot import main as cli

    items = pd.DataFrame([{"sku_local": "A"}])
    p_items = tmp_path / "i.csv"
    items.to_csv(p_items, index=False)
    p_opt = tmp_path / "o.json"
    p_out = tmp_path / "r.md"
    Path(p_opt).write_text(
        json.dumps(
            {
                "bid": 200.0,
                "roi_target": 1.25,
                "risk_threshold": 0.80,
                "meets_constraints": True,
            }
        ),
        encoding="utf-8",
    )
    res = CliRunner().invoke(
        cli,
        [
            "--items-csv",
            str(p_items),
            "--opt-json",
            str(p_opt),
            "--out-markdown",
            str(p_out),
        ],
    )
    assert res.exit_code == 0
    md = p_out.read_text(encoding="utf-8")
    assert "PROCEED" in md
    assert "ROI Target:" in md and "1.25" in md
    assert "Risk Threshold:" in md and "0.80" in md
    assert "- **Risk Threshold:**" in md  # Title Case in top bullets
    assert "Supporting Artifacts" not in md


def test_report_knobs_from_evidence_and_artifacts_gated(tmp_path):
    """Test evidence fallback only when file passed and exists."""
    import json
    from pathlib import Path

    import pandas as pd
    from click.testing import CliRunner
    from lotgenius.cli.report_lot import main as cli

    items = pd.DataFrame([{"sku_local": "A"}])
    p_items = tmp_path / "i.csv"
    items.to_csv(p_items, index=False)
    p_opt = tmp_path / "o.json"
    p_out = tmp_path / "r.md"
    p_ev = tmp_path / "ev.jsonl"
    Path(p_opt).write_text(
        json.dumps({"bid": 150.0, "meets_constraints": False}), encoding="utf-8"
    )
    Path(p_ev).write_text(
        json.dumps(
            {
                "source": "optimize:bid",
                "meta": {"roi_target": 1.30, "risk_threshold": 0.85},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    res = CliRunner().invoke(
        cli,
        [
            "--items-csv",
            str(p_items),
            "--opt-json",
            str(p_opt),
            "--out-markdown",
            str(p_out),
            "--evidence-jsonl",
            str(p_ev),
        ],
    )
    assert res.exit_code == 0
    md = p_out.read_text(encoding="utf-8")
    assert "PASS" in md
    assert "ROI Target:" in md and "1.30" in md
    assert "Risk Threshold:" in md and "0.85" in md
    assert "Optimization Audit Trail" in md


def test_params_section_present_with_evidence_knobs(tmp_path):
    """Test that Optimization Parameters section is always present."""
    import json
    from pathlib import Path

    import pandas as pd
    from click.testing import CliRunner
    from lotgenius.cli.report_lot import main as cli

    items = pd.DataFrame([{"sku_local": "A"}])
    p_items = tmp_path / "i.csv"
    items.to_csv(p_items, index=False)

    # Knobs only in evidence
    p_opt = tmp_path / "o.json"
    Path(p_opt).write_text(
        json.dumps({"bid": 150.0, "meets_constraints": False}), encoding="utf-8"
    )
    p_ev = tmp_path / "ev.jsonl"
    Path(p_ev).write_text(
        json.dumps(
            {
                "source": "optimize:bid",
                "meta": {"roi_target": 1.30, "risk_threshold": 0.85},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    p_out = tmp_path / "r.md"
    res = CliRunner().invoke(
        cli,
        [
            "--items-csv",
            str(p_items),
            "--opt-json",
            str(p_opt),
            "--out-markdown",
            str(p_out),
            "--evidence-jsonl",
            str(p_ev),
        ],
    )
    assert res.exit_code == 0
    md = p_out.read_text(encoding="utf-8")

    # The section must be present regardless of source
    assert "## Optimization Parameters" in md
    assert "ROI Target:" in md
    assert "1.30" in md
    assert "Risk Threshold:" in md
    assert "0.85" in md
