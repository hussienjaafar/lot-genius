import json
from pathlib import Path

from cli.resolve_ids import main as resolve_cli
from click.testing import CliRunner
from lotgenius.resolve import resolve_ids


def _fake_client_init(self, cfg=None):
    payload = json.loads(
        Path("backend/tests/fixtures/keepa/lookup_upc_ok.json").read_text(
            encoding="utf-8"
        )
    )

    # minimal cfg
    self.cfg = cfg or type(
        "C",
        (),
        {
            "api_key": "FAKE",  # pragma: allowlist secret
            "domain": 1,
            "timeout_sec": 5,
            "ttl_days": 7,
            "backoff_initial": 0.1,
            "backoff_max": 1.0,
            "max_retries": 1,
        },
    )
    self.session = None  # Not used in our mock

    # Mock the lookup_by_code method to return expected structure
    def fake_lookup_by_code(code):
        return {
            "ok": True,
            "cached": False,  # Fresh network hit for testing
            "data": payload,
        }

    self.lookup_by_code = fake_lookup_by_code


def test_resolve_ids_upc_to_asin(monkeypatch):
    monkeypatch.setattr(
        "lotgenius.keepa_client.KeepaClient.__init__", _fake_client_init
    )
    df, ledger = resolve_ids(
        "backend/tests/fixtures/manifest_multiqty.csv", threshold=85, use_network=True
    )
    assert (df["asin"] == "B00TESTASIN").any()
    assert any(
        rec.ok and rec.source == "keepa:code" and rec.match_asin == "B00TESTASIN"
        for rec in ledger
    )


def test_resolve_cli_summary(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "lotgenius.keepa_client.KeepaClient.__init__", _fake_client_init
    )
    out_csv = tmp_path / "enriched.csv"
    out_ledger = tmp_path / "ledger.jsonl"
    runner = CliRunner()
    res = runner.invoke(
        resolve_cli,
        [
            "backend/tests/fixtures/manifest_multiqty.csv",
            "--network",
            "--out-enriched",
            str(out_csv),
            "--out-ledger",
            str(out_ledger),
        ],
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["resolved"] >= 1
    assert out_csv.exists() and out_ledger.exists()
    lines = [
        line
        for line in out_ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert lines and json.loads(lines[0])
    assert "source_counts" in payload and isinstance(payload["source_counts"], dict)
    # with our patched Keepa, at least one keepa:code should appear
    if payload["resolved"] >= 1:
        assert any(
            k.startswith("keepa:code") or k == "keepa:code"
            for k in payload["source_counts"].keys()
        )


def test_evidence_meta_includes_code(monkeypatch):
    # Patch Keepa to ensure we hit keepa:code
    from lotgenius.keepa_client import KeepaClient

    payload = json.loads(
        Path("backend/tests/fixtures/keepa/lookup_upc_ok.json").read_text(
            encoding="utf-8"
        )
    )

    def fake_lookup(self, code):
        return {"ok": True, "cached": False, "data": payload}

    monkeypatch.setattr(KeepaClient, "lookup_by_code", fake_lookup)

    from lotgenius.resolve import resolve_ids

    df, ledger = resolve_ids(
        "backend/tests/fixtures/manifest_multiqty.csv", threshold=85, use_network=True
    )
    # At least one evidence record for keepa:code has a code field
    keepa_events = [e for e in ledger if e.source.startswith("keepa:code")]
    assert keepa_events, "Expected at least one keepa:code evidence event"
    assert any(
        e.meta.get("code") for e in keepa_events
    ), "keepa evidence should include queried 'code'"


def test_cli_gzip_ledger(monkeypatch, tmp_path):
    # Patch Keepa

    payload = json.loads(
        Path("backend/tests/fixtures/keepa/lookup_upc_ok.json").read_text(
            encoding="utf-8"
        )
    )

    class DummyResp:
        def __init__(self):
            self.status_code = 200
            self._payload = payload
            self.text = json.dumps(payload)

        def json(self):
            return self._payload

    def fake_init(self, cfg=None):
        self.cfg = cfg or type(
            "C",
            (),
            {
                "api_key": "FAKE",  # pragma: allowlist secret
                "domain": 1,
                "timeout_sec": 5,
                "ttl_days": 7,
                "backoff_initial": 0.1,
                "backoff_max": 1.0,
                "max_retries": 1,
            },
        )

        class Sess:
            def get(self, url, params=None, timeout=None):
                return DummyResp()

        self.session = Sess()

    monkeypatch.setattr("lotgenius.keepa_client.KeepaClient.__init__", fake_init)

    from cli.resolve_ids import main as resolve_cli
    from click.testing import CliRunner

    out_csv = tmp_path / "enriched.csv"
    out_ledger = tmp_path / "ledger.jsonl"  # no .gz here; flag should append it
    runner = CliRunner()
    res = runner.invoke(
        resolve_cli,
        [
            "backend/tests/fixtures/manifest_multiqty.csv",
            "--network",
            "--gzip-ledger",
            "--out-enriched",
            str(out_csv),
            "--out-ledger",
            str(out_ledger),
        ],
    )
    assert res.exit_code == 0, res.output
    payload_cli = json.loads(res.output)
    assert payload_cli["ledger_path"].endswith(".gz")
    gz_path = Path(payload_cli["ledger_path"])
    assert gz_path.exists()
    # Read back first line through gzip
    import gzip

    with gzip.open(gz_path, "rt", encoding="utf-8") as f:
        line = f.readline()
    json.loads(line)  # should parse
