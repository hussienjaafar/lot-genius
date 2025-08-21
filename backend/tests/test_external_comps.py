from importlib import reload
from pathlib import Path

from backend.lotgenius.datasources import ebay_scraper
from backend.lotgenius.pricing.external_comps import external_comps_estimator

FIXT = Path(__file__).parent / "data" / "ebay_sold_sample.html"


def test_default_scrapers_off(monkeypatch):
    monkeypatch.setenv("ENABLE_EBAY_SCRAPER", "false")
    monkeypatch.setenv("ENABLE_FB_SCRAPER", "false")
    monkeypatch.setenv("SCRAPER_TOS_ACK", "false")
    from backend.lotgenius import config as cfg

    reload(cfg)
    # External estimator should be None because scrapers are off
    est = external_comps_estimator(
        {"title": "Logitech M185 Wireless Mouse", "brand": "Logitech"}
    )
    assert est is None


def test_ebay_parser_fixture(monkeypatch):
    # Enable eBay + ToS ack; monkeypatch requests.get to return fixture contents
    monkeypatch.setenv("ENABLE_EBAY_SCRAPER", "true")
    monkeypatch.setenv("SCRAPER_TOS_ACK", "true")
    monkeypatch.setenv("ENABLE_FB_SCRAPER", "false")
    from backend.lotgenius import config as cfg

    reload(cfg)

    # Also patch the settings directly to ensure they're set
    monkeypatch.setattr(cfg.settings, "ENABLE_EBAY_SCRAPER", True)
    monkeypatch.setattr(cfg.settings, "SCRAPER_TOS_ACK", True)
    monkeypatch.setattr(cfg.settings, "ENABLE_FB_SCRAPER", False)

    class DummyResp:
        status_code = 200
        text = FIXT.read_text(encoding="utf-8")

        def raise_for_status(self):
            pass

    monkeypatch.setattr(ebay_scraper.requests, "get", lambda *a, **k: DummyResp())
    monkeypatch.setattr(ebay_scraper, "_sleep_jitter", lambda *a, **k: None)

    # Also patch settings in external_comps module
    from backend.lotgenius.pricing import external_comps

    monkeypatch.setattr(external_comps.settings, "ENABLE_EBAY_SCRAPER", True)
    monkeypatch.setattr(external_comps.settings, "SCRAPER_TOS_ACK", True)
    monkeypatch.setattr(external_comps.settings, "ENABLE_FB_SCRAPER", False)

    est = external_comps_estimator(
        {"title": "Logitech M185 Wireless Mouse", "brand": "Logitech"}
    )
    assert est is not None
    assert est["source"] == "external_comps"
    assert est["n"] >= 3
    assert 10.0 <= est["point"] <= 12.5
