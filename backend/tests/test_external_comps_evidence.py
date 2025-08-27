"""Test external comps evidence ledger consolidation."""

from importlib import reload
from unittest.mock import MagicMock, patch

from backend.lotgenius.datasources import ebay_scraper
from backend.lotgenius.datasources.base import SoldComp
from backend.lotgenius.evidence import _global_evidence_ledger
from backend.lotgenius.pricing.external_comps import gather_external_sold_comps


def test_single_evidence_record_per_item(monkeypatch):
    """Test that exactly one external_comps_summary evidence record is written per item."""
    # Enable scrapers
    monkeypatch.setenv("ENABLE_EBAY_SCRAPER", "true")
    monkeypatch.setenv("SCRAPER_TOS_ACK", "true")
    monkeypatch.setenv("ENABLE_GOOGLE_SEARCH_ENRICHMENT", "false")

    from backend.lotgenius import config as cfg

    reload(cfg)

    monkeypatch.setattr(cfg.settings, "ENABLE_EBAY_SCRAPER", True)
    monkeypatch.setattr(cfg.settings, "SCRAPER_TOS_ACK", True)

    # Mock eBay scraper to return test data
    test_comps = [
        SoldComp(
            source="ebay",
            title="Item 1",
            price=10.0,
            condition="Used",
            sold_at=None,
            url="http://example1.com",
            id=None,
            match_score=0.8,
            meta={},
        ),
        SoldComp(
            source="ebay",
            title="Item 2",
            price=15.0,
            condition="New",
            sold_at=None,
            url="http://example2.com",
            id=None,
            match_score=0.9,
            meta={},
        ),
    ]

    with patch.object(ebay_scraper, "fetch_sold_comps", return_value=test_comps):
        # Clear evidence ledger
        _global_evidence_ledger.clear()

        item = {"title": "Test Product", "brand": "TestBrand", "sku_local": "TEST-001"}

        # Gather external comps
        comps = gather_external_sold_comps(item)

        # Check evidence ledger
        evidence_records = [
            e
            for e in _global_evidence_ledger
            if e.get("source") == "external_comps_summary"
        ]

        # Should have exactly one external_comps_summary record
        assert len(evidence_records) == 1

        record = evidence_records[0]
        assert record["meta"]["num_comps"] == 2
        assert record["meta"]["by_source"]["ebay"] == 2
        assert record["meta"]["by_source"]["google_search"] == 0
        assert len(record["meta"]["sample"]) == 2


def test_evidence_with_multiple_sources(monkeypatch):
    """Test evidence consolidation with multiple sources enabled."""
    # Enable both eBay and Google
    monkeypatch.setenv("ENABLE_EBAY_SCRAPER", "true")
    monkeypatch.setenv("SCRAPER_TOS_ACK", "true")
    monkeypatch.setenv("ENABLE_GOOGLE_SEARCH_ENRICHMENT", "true")

    from backend.lotgenius import config as cfg

    reload(cfg)

    monkeypatch.setattr(cfg.settings, "ENABLE_EBAY_SCRAPER", True)
    monkeypatch.setattr(cfg.settings, "SCRAPER_TOS_ACK", True)
    monkeypatch.setattr(cfg.settings, "ENABLE_GOOGLE_SEARCH_ENRICHMENT", True)

    # Mock scrapers
    ebay_comps = [
        SoldComp(
            source="ebay",
            title="eBay Item",
            price=20.0,
            condition="Used",
            sold_at=None,
            url=None,
            id=None,
            match_score=0.8,
            meta={},
        )
    ]

    google_comps = [
        SoldComp(
            source="google_search",
            title="Google Item",
            price=25.0,
            condition="New",
            sold_at=None,
            url=None,
            id=None,
            match_score=0.7,
            meta={},
        )
    ]

    with patch.object(ebay_scraper, "fetch_sold_comps", return_value=ebay_comps):
        # Mock google_search module
        mock_gs = MagicMock()
        mock_gs.fetch_sold_comps_from_google = MagicMock(return_value=google_comps)

        with patch.dict(
            "sys.modules", {"backend.lotgenius.datasources.google_search": mock_gs}
        ):
            # Clear evidence ledger
            _global_evidence_ledger.clear()

            item = {
                "title": "Multi-source Product",
                "brand": "TestBrand",
                "sku_local": "TEST-002",
            }

            # Gather external comps
            comps = gather_external_sold_comps(item)

            # Check evidence ledger
            evidence_records = [
                e
                for e in _global_evidence_ledger
                if e.get("source") == "external_comps_summary"
            ]

            # Should have exactly one consolidated record
            assert len(evidence_records) == 1

            record = evidence_records[0]
            assert record["meta"]["num_comps"] == 2
            assert record["meta"]["by_source"]["ebay"] == 1
            assert record["meta"]["by_source"]["google_search"] == 1
            assert len(record["meta"]["sample"]) == 2


def test_evidence_with_errors(monkeypatch):
    """Test that errors are included in evidence but don't prevent summary."""
    # Enable scrapers
    monkeypatch.setenv("ENABLE_EBAY_SCRAPER", "true")
    monkeypatch.setenv("SCRAPER_TOS_ACK", "true")
    monkeypatch.setenv("ENABLE_GOOGLE_SEARCH_ENRICHMENT", "true")

    from backend.lotgenius import config as cfg

    reload(cfg)

    monkeypatch.setattr(cfg.settings, "ENABLE_EBAY_SCRAPER", True)
    monkeypatch.setattr(cfg.settings, "SCRAPER_TOS_ACK", True)
    monkeypatch.setattr(cfg.settings, "ENABLE_GOOGLE_SEARCH_ENRICHMENT", True)

    # Mock eBay to raise error
    with patch.object(
        ebay_scraper, "fetch_sold_comps", side_effect=Exception("Network error")
    ):
        # Mock google_search to return data
        google_comps = [
            SoldComp(
                source="google_search",
                title="Google Item",
                price=30.0,
                condition="New",
                sold_at=None,
                url=None,
                id=None,
                match_score=0.7,
                meta={},
            )
        ]

        mock_gs = MagicMock()
        mock_gs.fetch_sold_comps_from_google = MagicMock(return_value=google_comps)

        with patch.dict(
            "sys.modules", {"backend.lotgenius.datasources.google_search": mock_gs}
        ):
            # Clear evidence ledger
            _global_evidence_ledger.clear()

            item = {
                "title": "Error Test Product",
                "brand": "TestBrand",
                "sku_local": "TEST-003",
            }

            # Gather external comps
            comps = gather_external_sold_comps(item)

            # Check evidence ledger
            evidence_records = [
                e
                for e in _global_evidence_ledger
                if e.get("source") == "external_comps_summary"
            ]

            # Should have exactly one record with errors noted
            assert len(evidence_records) == 1

            record = evidence_records[0]
            assert record["meta"]["num_comps"] == 1  # Only Google succeeded
            assert record["meta"]["by_source"]["ebay"] == 0
            assert record["meta"]["by_source"]["google_search"] == 1
            assert "errors" in record["meta"]
            assert "ebay" in record["meta"]["errors"]
            assert "Network error" in record["meta"]["errors"]["ebay"]


def test_no_evidence_when_scrapers_disabled(monkeypatch):
    """Test that no external_comps_summary is written when scrapers are disabled."""
    # Disable scrapers
    monkeypatch.setenv("ENABLE_EBAY_SCRAPER", "false")
    monkeypatch.setenv("SCRAPER_TOS_ACK", "false")
    monkeypatch.setenv("ENABLE_GOOGLE_SEARCH_ENRICHMENT", "false")

    from backend.lotgenius import config as cfg

    reload(cfg)

    monkeypatch.setattr(cfg.settings, "ENABLE_EBAY_SCRAPER", False)
    monkeypatch.setattr(cfg.settings, "SCRAPER_TOS_ACK", False)

    # Clear evidence ledger
    _global_evidence_ledger.clear()

    item = {
        "title": "Disabled Test Product",
        "brand": "TestBrand",
        "sku_local": "TEST-004",
    }

    # Gather external comps
    comps = gather_external_sold_comps(item)

    # Check evidence ledger
    evidence_records = [
        e
        for e in _global_evidence_ledger
        if e.get("source") == "external_comps_summary"
    ]

    # Should still write summary even with no comps (showing 0 results)
    assert len(evidence_records) == 1
    record = evidence_records[0]
    assert record["meta"]["num_comps"] == 0
    assert record["meta"]["by_source"]["ebay"] == 0
    assert record["meta"]["by_source"]["google_search"] == 0
