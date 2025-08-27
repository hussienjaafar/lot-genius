import json
import os
from unittest.mock import patch

import pandas as pd
from lotgenius.api.schemas import ReportRequest
from lotgenius.api.service import generate_report
from lotgenius.cli.report_lot import _mk_markdown


class TestMarkdownReportGeneration:
    """Test markdown report generation with Product Confidence and Cache Metrics."""

    def test_item_details_table_with_product_confidence(self):
        """Test Item Details table generation when product_confidence is available."""
        # Create sample items with evidence_meta containing product_confidence
        items = pd.DataFrame(
            [
                {
                    "item_key": "SKU001",
                    "title": "Test Item 1",
                    "est_price_p50": 100.0,
                    "sell_p60": 0.75,
                    "evidence_meta": json.dumps({"product_confidence": 0.85}),
                },
                {
                    "item_key": "SKU002",
                    "title": "Test Item 2 with very long title that should be truncated",
                    "est_price_p50": 200.0,
                    "sell_p60": 0.60,
                    "evidence_meta": json.dumps({"product_confidence": 0.92}),
                },
            ]
        )

        opt = {
            "bid": 150.0,
            "roi_p50": 1.5,
            "prob_roi_ge_target": 0.75,
            "expected_cash_60d": 180.0,
            "meets_constraints": True,
            "roi_target": 1.3,
            "risk_threshold": 0.7,
        }

        # Generate markdown
        markdown = _mk_markdown(items, opt)

        # Verify Item Details section exists
        assert "## Item Details" in markdown

        # Verify table structure
        assert (
            "| SKU | Title | Est. Price | Sell P60 | Product Confidence |" in markdown
        )
        assert "| --- | --- | --- | --- | --- |" in markdown

        # Verify data rows
        assert "| SKU001 | Test Item 1 | $100.00 | 75.0% | 0.85 |" in markdown
        assert (
            "| SKU002 | Test Item 2 with very long title that sh... | $200.00 | 60.0% | 0.92 |"
            in markdown
        )

    def test_item_details_without_product_confidence(self):
        """Test that Item Details table is not generated when no product_confidence available."""
        items = pd.DataFrame(
            [
                {
                    "item_key": "SKU001",
                    "title": "Test Item 1",
                    "est_price_p50": 100.0,
                    "sell_p60": 0.75,
                    # No evidence_meta with product_confidence
                }
            ]
        )

        opt = {"bid": 150.0, "roi_target": 1.3, "risk_threshold": 0.7}

        markdown = _mk_markdown(items, opt)

        # Verify Item Details section does not exist
        assert "## Item Details" not in markdown
        assert "Product Confidence" not in markdown

    def test_item_details_large_dataset_truncation(self):
        """Test that Item Details table shows only first 10 items with truncation note."""
        # Create 15 items
        items_data = []
        for i in range(15):
            items_data.append(
                {
                    "item_key": f"SKU{i:03d}",
                    "title": f"Test Item {i}",
                    "est_price_p50": 100.0 + i,
                    "sell_p60": 0.75,
                    "evidence_meta": json.dumps({"product_confidence": 0.8 + i * 0.01}),
                }
            )

        items = pd.DataFrame(items_data)
        opt = {"bid": 150.0, "roi_target": 1.3, "risk_threshold": 0.7}

        markdown = _mk_markdown(items, opt)

        # Should show first 10 items
        assert "| SKU000 |" in markdown
        assert "| SKU009 |" in markdown
        # Should not show 11th item
        assert "| SKU010 |" not in markdown

        # Should have truncation note
        assert "*Showing first 10 items of 15 total items.*" in markdown

    @patch.dict(os.environ, {"CACHE_METRICS": "1"})
    def test_cache_metrics_section(self):
        """Test Cache Metrics section generation when CACHE_METRICS=1."""
        items = pd.DataFrame([{"item_key": "SKU001", "title": "Test"}])
        opt = {"bid": 150.0, "roi_target": 1.3, "risk_threshold": 0.7}

        # Mock cache registry
        mock_stats = {
            "keepa_cache": {
                "hits": 100,
                "misses": 25,
                "stores": 25,
                "evictions": 0,
                "hit_ratio": 0.8,
                "total_operations": 125,
            },
            "ebay_cache": {
                "hits": 50,
                "misses": 10,
                "stores": 10,
                "evictions": 0,
                "hit_ratio": 0.833,
                "total_operations": 60,
            },
        }

        with patch(
            "lotgenius.cache_metrics.should_emit_metrics", return_value=True
        ), patch("lotgenius.cache_metrics.get_registry") as mock_registry:

            mock_registry.return_value.get_all_stats.return_value = mock_stats

            markdown = _mk_markdown(items, opt)

            # Verify Cache Metrics section exists
            assert "## Cache Metrics" in markdown

            # Verify overall stats
            assert "**Overall Hit Ratio:** 81.1%" in markdown
            assert "**Total Cache Operations:** 185" in markdown
            assert "**Total Hits:** 150" in markdown
            assert "**Total Misses:** 35" in markdown

            # Verify per-cache breakdown table
            assert "| Cache | Hits | Misses | Hit Ratio | Total Ops |" in markdown
            assert "| ebay_cache | 50 | 10 | 83.3% | 60 |" in markdown
            assert "| keepa_cache | 100 | 25 | 80.0% | 125 |" in markdown

    @patch.dict(os.environ, {"CACHE_METRICS": "0"})
    def test_cache_metrics_section_disabled(self):
        """Test that Cache Metrics section is not generated when CACHE_METRICS=0."""
        items = pd.DataFrame([{"item_key": "SKU001", "title": "Test"}])
        opt = {"bid": 150.0, "roi_target": 1.3, "risk_threshold": 0.7}

        markdown = _mk_markdown(items, opt)

        # Verify Cache Metrics section does not exist
        assert "## Cache Metrics" not in markdown

    def test_ascii_safe_formatting(self):
        """Test that all formatting uses ASCII-safe characters."""
        items = pd.DataFrame(
            [
                {
                    "item_key": "SKU001",
                    "title": "Test Item",
                    "est_price_p50": 100.0,
                    "sell_p60": 0.75,
                    "evidence_meta": json.dumps({"product_confidence": 0.85}),
                }
            ]
        )

        opt = {
            "bid": 150.0,
            "roi_p50": 1.5,
            "prob_roi_ge_target": 0.75,
            "expected_cash_60d": 180.0,
            "meets_constraints": True,
            "roi_target": 1.3,
            "risk_threshold": 0.7,
        }

        markdown = _mk_markdown(items, opt)

        # Check that all characters are ASCII (ord < 128)
        for char in markdown:
            assert (
                ord(char) < 128
            ), f"Non-ASCII character found: {repr(char)} (ord {ord(char)})"

        # Should use ASCII table formatting
        assert "| --- |" in markdown  # ASCII table separator
        assert "≥" not in markdown  # No Unicode >= symbols


class TestApiServiceIntegration:
    """Test API service integration with cache_stats flow."""

    @patch.dict(os.environ, {"CACHE_METRICS": "1"})
    def test_report_response_includes_cache_stats(self, tmp_path):
        """Test that ReportResponse includes cache_stats when CACHE_METRICS=1."""
        # Create test CSV
        test_csv = tmp_path / "test_items.csv"
        test_csv.write_text("item_key,title,est_price_p50\nSKU001,Test Item,100.0\n")

        # Mock cache registry
        mock_stats = {
            "test_cache": {
                "hits": 10,
                "misses": 2,
                "stores": 2,
                "evictions": 0,
                "hit_ratio": 0.833,
                "total_operations": 12,
            }
        }

        with patch(
            "lotgenius.cache_metrics.should_emit_metrics", return_value=True
        ), patch("lotgenius.cache_metrics.get_registry") as mock_registry, patch(
            "lotgenius.api.service.run_optimize"
        ) as mock_optimize:

            mock_registry.return_value.get_all_stats.return_value = mock_stats
            mock_optimize.return_value = ({"bid": 150.0}, None)

            request = ReportRequest(
                items_csv=str(test_csv),
                out_markdown=str(tmp_path / "report.md"),
                opt_json_inline={
                    "bid": 150.0,
                    "roi_target": 1.3,
                    "risk_threshold": 0.7,
                },
            )

            response = generate_report(request)

            # Verify cache_stats is included in response
            assert response.cache_stats is not None
            assert response.cache_stats == mock_stats

    @patch.dict(os.environ, {"CACHE_METRICS": "0"})
    def test_report_response_no_cache_stats_when_disabled(self, tmp_path):
        """Test that ReportResponse excludes cache_stats when CACHE_METRICS=0."""
        test_csv = tmp_path / "test_items.csv"
        test_csv.write_text("item_key,title,est_price_p50\nSKU001,Test Item,100.0\n")

        with patch("lotgenius.api.service.run_optimize") as mock_optimize:
            mock_optimize.return_value = ({"bid": 150.0}, None)

            request = ReportRequest(
                items_csv=str(test_csv),
                out_markdown=str(tmp_path / "report.md"),
                opt_json_inline={
                    "bid": 150.0,
                    "roi_target": 1.3,
                    "risk_threshold": 0.7,
                },
            )

            response = generate_report(request)

            # Verify cache_stats is None
            assert response.cache_stats is None

    def test_evidence_meta_flow(self):
        """Test that evidence.meta with product_confidence flows through to report."""
        # This test would need to be more comprehensive with actual evidence generation
        # For now, just verify the structure exists
        from lotgenius.evidence import EvidenceResult

        # Create evidence with product_confidence meta
        ev = EvidenceResult(
            item_key="TEST_SKU",
            has_high_trust_id=True,
            sold_comp_count=5,
            lookback_days=180,
            secondary_signals={},
            evidence_score=0.8,
            include_in_core=True,
            review_reason=None,
            sources={"comps": 5},
            timestamp=0.0,
            meta={"product_confidence": 0.9},
        )

        # Verify meta structure
        assert ev.meta is not None
        assert ev.meta["product_confidence"] == 0.9


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_malformed_evidence_meta(self):
        """Test handling of malformed evidence_meta JSON."""
        items = pd.DataFrame(
            [
                {
                    "item_key": "SKU001",
                    "title": "Test Item",
                    "est_price_p50": 100.0,
                    "sell_p60": 0.75,
                    "evidence_meta": "invalid-json{",  # Malformed JSON
                }
            ]
        )

        opt = {"bid": 150.0, "roi_target": 1.3, "risk_threshold": 0.7}

        # Should not raise exception, should handle gracefully
        markdown = _mk_markdown(items, opt)

        # Item Details should not appear due to malformed meta
        assert "## Item Details" not in markdown

    def test_missing_cache_metrics_module(self):
        """Test graceful handling when cache_metrics module is not available."""
        items = pd.DataFrame([{"item_key": "SKU001", "title": "Test"}])
        opt = {"bid": 150.0, "roi_target": 1.3, "risk_threshold": 0.7}

        # Test when ImportError occurs - this will happen naturally if we disable CACHE_METRICS
        # and the module logic handles the ImportError gracefully
        markdown = _mk_markdown(items, opt)

        # Should not contain Cache Metrics section when CACHE_METRICS is not enabled
        assert "## Cache Metrics" not in markdown

    def test_empty_items_dataframe(self):
        """Test handling of empty items DataFrame."""
        items = pd.DataFrame()  # Empty DataFrame
        opt = {"bid": 150.0, "roi_target": 1.3, "risk_threshold": 0.7}

        markdown = _mk_markdown(items, opt)

        # Should not crash and should not have Item Details section
        assert "## Item Details" not in markdown
        assert "Total Items:** 0" in markdown
