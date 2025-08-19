import json
from pathlib import Path

from lotgenius.keepa_client import KeepaClient, KeepaConfig, extract_primary_asin


class DummyResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


def test_extract_primary_asin_fixture():
    payload = json.loads(
        Path("backend/tests/fixtures/keepa/lookup_upc_ok.json").read_text(
            encoding="utf-8"
        )
    )
    assert extract_primary_asin(payload) == "B00TESTASIN"


def test_lookup_by_code_caches(monkeypatch, tmp_path):
    # Use isolated cache path for test
    cache_path = tmp_path / "keepa_cache.sqlite"
    monkeypatch.setattr("lotgenius.keepa_client._DB_PATH", cache_path)

    cfg = KeepaConfig(api_key="FAKE_KEY", ttl_days=1)
    client = KeepaClient(cfg)
    payload = json.loads(
        Path("backend/tests/fixtures/keepa/lookup_upc_ok.json").read_text(
            encoding="utf-8"
        )
    )
    calls = {"n": 0}

    def fake_get(url, params=None, timeout=None):
        calls["n"] += 1
        return DummyResp(200, payload)

    monkeypatch.setattr(client.session, "get", fake_get)
    r1 = client.lookup_by_code("012345678905")
    assert r1["ok"] and not r1["cached"]
    r2 = client.lookup_by_code("012345678905")
    assert r2["ok"] and r2["cached"]
    assert calls["n"] == 1
