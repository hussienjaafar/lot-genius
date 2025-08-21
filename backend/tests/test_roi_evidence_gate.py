"""
Tests for ROI calculations with evidence gating integration.
"""

import pandas as pd
import pytest
from lotgenius.roi import apply_evidence_gate_to_items, simulate_lot_outcomes


class TestApplyEvidenceGate:
    """Test evidence gate application in ROI context."""

    def test_apply_evidence_gate_basic(self):
        """Test basic evidence gate application."""
        df = pd.DataFrame(
            [
                {
                    "sku_local": "ITEM001",
                    "keepa_new_count": 5,
                    "asin": "B01234567",  # pragma: allowlist secret
                    "resolved_source": "direct:asin",
                    "est_price_mu": 50.0,
                    "est_price_sigma": 10.0,
                    "sell_p60": 0.8,
                },
                {
                    "sku_local": "ITEM002",
                    "keepa_new_count": 1,  # Insufficient comps
                    "est_price_mu": 30.0,
                    "est_price_sigma": 8.0,
                    "sell_p60": 0.7,
                },
            ]
        )

        result = apply_evidence_gate_to_items(df)

        assert len(result["core_items"]) == 1
        assert len(result["upside_items"]) == 1
        assert result["evidence_summary"]["total_items"] == 2
        assert result["evidence_summary"]["core_count"] == 1
        assert result["evidence_summary"]["upside_count"] == 1
        assert result["evidence_summary"]["gate_pass_rate"] == 0.5

    def test_apply_evidence_gate_empty_df(self):
        """Test evidence gate with empty DataFrame."""
        df = pd.DataFrame()

        result = apply_evidence_gate_to_items(df)

        assert len(result["core_items"]) == 0
        assert len(result["upside_items"]) == 0
        assert result["evidence_summary"]["total_items"] == 0
        assert result["evidence_summary"]["gate_pass_rate"] == 0.0

    def test_apply_evidence_gate_all_pass(self):
        """Test when all items pass evidence gate."""
        df = pd.DataFrame(
            [
                {
                    "keepa_new_count": 4,
                    "asin": "B01234567",  # pragma: allowlist secret
                    "resolved_source": "direct:asin",
                },
                {"keepa_new_count": 6, "manual_price": 45.0},
            ]
        )

        result = apply_evidence_gate_to_items(df)

        assert len(result["core_items"]) == 2
        assert len(result["upside_items"]) == 0
        assert result["evidence_summary"]["gate_pass_rate"] == 1.0

    def test_apply_evidence_gate_all_fail(self):
        """Test when all items fail evidence gate."""
        df = pd.DataFrame(
            [
                {
                    "keepa_new_count": 1,  # Insufficient comps
                    "est_price_mu": 30.0,
                    "est_price_sigma": 20.0,
                },
                {
                    "keepa_new_count": 2,  # Insufficient comps
                    "est_price_mu": 40.0,
                    "est_price_sigma": 25.0,
                },
            ]
        )

        result = apply_evidence_gate_to_items(df)

        assert len(result["core_items"]) == 0
        assert len(result["upside_items"]) == 2
        assert result["evidence_summary"]["gate_pass_rate"] == 0.0


class TestSimulateLotOutcomesWithEvidenceGate:
    """Test ROI simulation with evidence gating enabled."""

    def test_simulate_without_evidence_gate(self):
        """Test normal simulation without evidence gating."""
        df = pd.DataFrame(
            [
                {
                    "est_price_mu": 50.0,
                    "est_price_sigma": 10.0,
                    "sell_p60": 0.8,
                    "keepa_new_count": 2,  # Would fail evidence gate
                },
                {
                    "est_price_mu": 75.0,
                    "est_price_sigma": 15.0,
                    "sell_p60": 0.9,
                    "keepa_new_count": 5,  # Would pass evidence gate
                },
            ]
        )

        result = simulate_lot_outcomes(
            df, bid=200.0, sims=100, apply_evidence_gate=False
        )

        assert result["items"] == 2  # Both items included
        assert "evidence_gate" not in result
        assert result["bid"] == 200.0

    def test_simulate_with_evidence_gate(self):
        """Test simulation with evidence gating enabled."""
        df = pd.DataFrame(
            [
                {
                    "est_price_mu": 50.0,
                    "est_price_sigma": 10.0,
                    "sell_p60": 0.8,
                    "keepa_new_count": 2,  # Insufficient comps - will be excluded
                },
                {
                    "est_price_mu": 75.0,
                    "est_price_sigma": 15.0,
                    "sell_p60": 0.9,
                    "keepa_new_count": 5,
                    "asin": "B01234567",  # pragma: allowlist secret
                    "resolved_source": "direct:asin",  # Has secondary signal - will pass
                },
            ]
        )

        result = simulate_lot_outcomes(
            df, bid=200.0, sims=100, apply_evidence_gate=True
        )

        assert result["items"] == 1  # Only passing item included in ROI
        assert "evidence_gate" in result
        assert result["evidence_gate"]["evidence_summary"]["core_count"] == 1
        assert result["evidence_gate"]["evidence_summary"]["upside_count"] == 1

    def test_simulate_with_evidence_gate_all_fail(self):
        """Test simulation when all items fail evidence gate."""
        df = pd.DataFrame(
            [
                {
                    "est_price_mu": 50.0,
                    "est_price_sigma": 10.0,
                    "sell_p60": 0.8,
                    "keepa_new_count": 1,  # Insufficient comps
                },
                {
                    "est_price_mu": 75.0,
                    "est_price_sigma": 15.0,
                    "sell_p60": 0.9,
                    "keepa_new_count": 2,  # Insufficient comps
                },
            ]
        )

        result = simulate_lot_outcomes(
            df, bid=200.0, sims=100, apply_evidence_gate=True
        )

        assert result["items"] == 0  # No items pass evidence gate
        assert "evidence_gate" in result
        assert result["evidence_gate"]["evidence_summary"]["core_count"] == 0
        assert result["evidence_gate"]["evidence_summary"]["upside_count"] == 2

        # ROI should be zeros when no valid items
        assert result["roi_p50"] == 0.0
        assert result["prob_roi_ge_target"] is None

    def test_simulate_with_external_comps_evidence(self):
        """Test simulation with external comps in evidence ledger."""
        df = pd.DataFrame(
            [
                {
                    "est_price_mu": 45.0,
                    "est_price_sigma": 8.0,
                    "sell_p60": 0.85,
                    "keepa_new_count": 2,  # Insufficient primary comps
                }
            ]
        )

        evidence_ledger = [
            {
                "external_comps_summary": {
                    "total_comps": 4,  # External comps boost total to 6
                    "estimated_price": 44.0,
                }
            }
        ]

        result = simulate_lot_outcomes(
            df,
            bid=100.0,
            sims=100,
            apply_evidence_gate=True,
            evidence_ledger=evidence_ledger,
        )

        assert result["items"] == 1  # Item passes with external comps
        assert "evidence_gate" in result
        assert result["evidence_gate"]["evidence_summary"]["core_count"] == 1
        assert result["evidence_gate"]["evidence_summary"]["upside_count"] == 0

    def test_evidence_gate_preserves_other_parameters(self):
        """Test that evidence gating doesn't interfere with other ROI parameters."""
        df = pd.DataFrame(
            [
                {
                    "est_price_mu": 60.0,
                    "est_price_sigma": 12.0,
                    "sell_p60": 0.9,
                    "keepa_new_count": 5,
                    "asin": "B01234567",  # pragma: allowlist secret
                    "resolved_source": "direct:asin",
                }
            ]
        )

        custom_params = {
            "sims": 500,
            "marketplace_fee_pct": 0.15,
            "return_rate": 0.10,
            "salvage_frac": 0.60,
        }

        result = simulate_lot_outcomes(
            df, bid=150.0, apply_evidence_gate=True, **custom_params
        )

        assert result["sims"] == 500
        assert result["bid"] == 150.0
        assert result["items"] == 1
        assert "evidence_gate" in result

        # Verify arrays have correct length
        assert len(result["roi"]) == 500
        assert len(result["revenue"]) == 500


class TestEvidenceGateMetrics:
    """Test evidence gate metrics and reporting."""

    def test_evidence_summary_metrics(self):
        """Test evidence summary calculation."""
        df = pd.DataFrame(
            [
                {
                    "keepa_new_count": 5,
                    "asin": "B01",
                    "resolved_source": "direct:asin",
                },  # Pass
                {"keepa_new_count": 4, "manual_price": 30.0},  # Pass
                {"keepa_new_count": 2},  # Fail - insufficient comps
                {"keepa_new_count": 6},  # Fail - no secondary signal
                {"keepa_new_count": 3, "category_hint": "Electronics"},  # Pass
            ]
        )

        result = apply_evidence_gate_to_items(df)
        summary = result["evidence_summary"]

        assert summary["total_items"] == 5
        assert summary["core_count"] == 3
        assert summary["upside_count"] == 2
        assert summary["gate_pass_rate"] == 0.6
        assert summary["core_percentage"] == 60.0
        assert summary["upside_percentage"] == 40.0

    def test_upside_tracking(self):
        """Test that upside items are properly tracked."""
        df = pd.DataFrame(
            [
                {
                    "sku_local": "UPSIDE001",
                    "keepa_new_count": 1,  # Insufficient comps
                    "est_price_mu": 40.0,
                },
                {
                    "sku_local": "UPSIDE002",
                    "keepa_new_count": 5,  # Sufficient comps but no secondary signal
                    "est_price_mu": 60.0,
                    "est_price_sigma": 30.0,  # High CV, no high confidence
                },
            ]
        )

        result = apply_evidence_gate_to_items(df)
        upside_items = result["upside_items"]

        assert len(upside_items) == 2
        assert all(upside_items["item_category"] == "upside")
        assert "upside_reason" in upside_items.columns

        # Verify specific failure reasons
        reasons = upside_items["upside_reason"].tolist()
        assert any("Insufficient comps" in reason for reason in reasons)
        assert any("No secondary signals" in reason for reason in reasons)


if __name__ == "__main__":
    pytest.main([__file__])
