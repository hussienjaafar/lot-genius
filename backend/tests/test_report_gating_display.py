"""Test report rendering with gating policies."""

import json

import pandas as pd
import pytest
from lotgenius.cli.report_lot import _mk_markdown


@pytest.fixture
def sample_items_df():
    """Sample items DataFrame."""
    return pd.DataFrame(
        [
            {
                "sku_local": "APPLE_001",
                "est_price_mu": 100.0,
                "est_price_sigma": 15.0,
                "sell_p60": 0.8,
                "brand": "Apple",
                "is_hazmat": False,
            },
            {
                "sku_local": "BATTERY_002",
                "est_price_mu": 50.0,
                "est_price_sigma": 8.0,
                "sell_p60": 0.6,
                "brand": "Generic",
                "is_hazmat": True,
            },
        ]
    )


@pytest.fixture
def opt_result_with_evidence():
    """Optimization result with evidence gate summary."""
    return {
        "bid": 150.0,
        "roi_p50": 1.25,
        "roi_p95": 1.80,
        "prob_roi_ge_target": 0.85,
        "expected_cash_60d": 120.0,
        "meets_constraints": True,
        "roi_target": 1.20,
        "risk_threshold": 0.80,
        "payout_lag_days": 14,
        "evidence_gate": {
            "evidence_summary": {
                "total_items": 10,
                "core_count": 7,
                "upside_count": 3,
                "gate_pass_rate": 0.70,
                "core_percentage": 70.0,
                "upside_percentage": 30.0,
            }
        },
    }


@pytest.fixture
def opt_result_without_evidence():
    """Optimization result without evidence gate summary."""
    return {
        "bid": 150.0,
        "roi_p50": 1.25,
        "roi_p95": 1.80,
        "prob_roi_ge_target": 0.85,
        "expected_cash_60d": 120.0,
        "meets_constraints": True,
        "roi_target": 1.20,
        "risk_threshold": 0.80,
        "payout_lag_days": 14,
    }


class TestGatingReportDisplay:
    """Test gating policy display in reports."""

    def test_report_includes_gating_section_with_evidence(
        self, sample_items_df, opt_result_with_evidence, monkeypatch
    ):
        """Test that Gating/Hazmat section appears when evidence summary is available."""
        # Set some gating policies
        monkeypatch.setenv("GATED_BRANDS_CSV", "Apple,Samsung")
        monkeypatch.setenv("HAZMAT_POLICY", "exclude")

        # Force reload of settings
        import lotgenius.config
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()

        # Generate report
        markdown = _mk_markdown(sample_items_df, opt_result_with_evidence)

        # Check that Gating/Hazmat section is present
        assert "## Gating/Hazmat" in markdown
        assert "**Gated Brands:** Apple,Samsung" in markdown
        assert "**Hazmat Policy:** exclude" in markdown
        assert "**Core Items:** 7 (70.0%)" in markdown
        assert "**Review Items:** 3 (30.0%)" in markdown
        assert "**Total Items:** 10" in markdown

    def test_report_no_gating_section_without_evidence(
        self, sample_items_df, opt_result_without_evidence, monkeypatch
    ):
        """Test that Gating/Hazmat section does not appear without evidence summary."""
        # Set some gating policies
        monkeypatch.setenv("GATED_BRANDS_CSV", "Apple")
        monkeypatch.setenv("HAZMAT_POLICY", "review")

        # Force reload of settings
        import lotgenius.config
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()

        # Generate report
        markdown = _mk_markdown(sample_items_df, opt_result_without_evidence)

        # Check that Gating/Hazmat section is NOT present
        assert "## Gating/Hazmat" not in markdown

    def test_report_gating_section_with_empty_policies(
        self, sample_items_df, opt_result_with_evidence, monkeypatch
    ):
        """Test Gating/Hazmat section with empty/default policies."""
        # Set empty/default policies
        monkeypatch.setenv("GATED_BRANDS_CSV", "")
        monkeypatch.setenv("HAZMAT_POLICY", "allow")

        # Force reload of settings
        import lotgenius.config
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()

        # Generate report
        markdown = _mk_markdown(sample_items_df, opt_result_with_evidence)

        # Check that section shows default values
        assert "## Gating/Hazmat" in markdown
        assert "**Gated Brands:** None" in markdown
        assert "**Hazmat Policy:** allow" in markdown

    def test_report_gating_section_with_review_policy(
        self, sample_items_df, opt_result_with_evidence, monkeypatch
    ):
        """Test Gating/Hazmat section with review policy."""
        # Set review policy
        monkeypatch.setenv("GATED_BRANDS_CSV", "Apple")
        monkeypatch.setenv("HAZMAT_POLICY", "review")

        # Force reload of settings
        import lotgenius.config
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()

        # Generate report
        markdown = _mk_markdown(sample_items_df, opt_result_with_evidence)

        # Check policy values
        assert "**Gated Brands:** Apple" in markdown
        assert "**Hazmat Policy:** review" in markdown

    def test_report_gating_percentages_calculation(self, sample_items_df, monkeypatch):
        """Test that gating percentages are calculated correctly."""
        # Custom evidence summary with specific numbers
        opt_result = {
            "bid": 100.0,
            "roi_p50": 1.15,
            "evidence_gate": {
                "evidence_summary": {
                    "total_items": 20,
                    "core_count": 15,
                    "upside_count": 5,
                    "gate_pass_rate": 0.75,  # 75%
                }
            },
        }

        # Set policies
        monkeypatch.setenv("GATED_BRANDS_CSV", "")
        monkeypatch.setenv("HAZMAT_POLICY", "allow")

        # Force reload of settings
        import lotgenius.config
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()

        # Generate report
        markdown = _mk_markdown(sample_items_df, opt_result)

        # Check percentage calculations
        assert "**Core Items:** 15 (75.0%)" in markdown
        assert "**Review Items:** 5 (25.0%)" in markdown
        assert "**Total Items:** 20" in markdown

    def test_report_optimization_parameters_section_present(
        self, sample_items_df, opt_result_with_evidence
    ):
        """Test that Optimization Parameters section is still present."""
        # Generate report
        markdown = _mk_markdown(sample_items_df, opt_result_with_evidence)

        # Check that Optimization Parameters section exists
        assert "## Optimization Parameters" in markdown
        assert "**ROI Target:**" in markdown
        assert "**Risk Threshold:**" in markdown
        assert "**Payout Lag (days):** 14" in markdown

    def test_report_section_ordering(
        self, sample_items_df, opt_result_with_evidence, monkeypatch
    ):
        """Test that sections appear in correct order."""
        # Set policies
        monkeypatch.setenv("GATED_BRANDS_CSV", "Apple")
        monkeypatch.setenv("HAZMAT_POLICY", "exclude")

        # Force reload of settings
        import lotgenius.config
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()

        # Generate report
        markdown = _mk_markdown(sample_items_df, opt_result_with_evidence)

        # Find section positions
        opt_params_pos = markdown.find("## Optimization Parameters")
        gating_pos = markdown.find("## Gating/Hazmat")

        # Gating section should come after Optimization Parameters
        assert opt_params_pos != -1
        assert gating_pos != -1
        assert gating_pos > opt_params_pos

    def test_report_cli_integration(self, sample_items_df, tmp_path, monkeypatch):
        """Test full CLI to report integration with gating policies."""
        from click.testing import CliRunner

        from backend.cli.report_lot import main as report_cli

        # Create input files
        items_csv = tmp_path / "items.csv"
        sample_items_df.to_csv(items_csv, index=False)

        opt_json = tmp_path / "opt.json"
        opt_result_with_evidence = {
            "bid": 120.0,
            "roi_p50": 1.30,
            "evidence_gate": {
                "evidence_summary": {
                    "core_count": 8,
                    "upside_count": 2,
                    "total_items": 10,
                    "gate_pass_rate": 0.80,
                }
            },
        }
        opt_json.write_text(json.dumps(opt_result_with_evidence))

        out_markdown = tmp_path / "report.md"

        # Set gating policies
        monkeypatch.setenv("GATED_BRANDS_CSV", "Apple,Samsung")
        monkeypatch.setenv("HAZMAT_POLICY", "review")

        # Force reload of settings
        import lotgenius.config
        from lotgenius.config import Settings

        lotgenius.config.settings = Settings()

        # Run CLI
        res = CliRunner().invoke(
            report_cli,
            [
                "--items-csv",
                str(items_csv),
                "--opt-json",
                str(opt_json),
                "--out-markdown",
                str(out_markdown),
            ],
        )

        assert res.exit_code == 0, res.output
        assert out_markdown.exists()

        # Check report content
        report_content = out_markdown.read_text()
        assert "## Gating/Hazmat" in report_content
        assert "**Gated Brands:** Apple,Samsung" in report_content
        assert "**Hazmat Policy:** review" in report_content
