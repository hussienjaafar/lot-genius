import json

import pandas as pd
from fastapi.testclient import TestClient

from backend.app.main import app


def _mk_inputs(tmp_path):
    items_csv = tmp_path / "items.csv"
    pd.DataFrame(
        [
            {
                "sku_local": "A",
                "est_price_mu": 60.0,
                "est_price_sigma": 12.0,
                "sell_p60": 0.6,
            }
        ]
    ).to_csv(items_csv, index=False)
    opt_json = tmp_path / "opt.json"
    opt_json.write_text(
        json.dumps(
            {
                "lo": 0,
                "hi": 100,
                "roi_target": 1.25,
                "risk_threshold": 0.80,
                "sims": 100,  # Small for fast tests
            }
        ),
        encoding="utf-8",
    )
    return str(items_csv), str(opt_json)


def test_pipeline_blocking(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, opt_path = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/pipeline",
        headers={"X-API-Key": "secret123"},
        json={"items_csv": items_csv, "opt_json_path": opt_path},
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert "phases" in payload and "markdown_preview" in payload
    # Check phases were completed
    phases = payload["phases"]
    expected_phases = [
        "start",
        "parse",
        "validate",
        "enrich_keepa",
        "price",
        "sell",
        "optimize",
        "render_report",
        "done",
    ]
    for phase in expected_phases:
        assert phase in phases


def test_pipeline_blocking_inline_json(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, _ = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/pipeline",
        headers={"X-API-Key": "secret123"},
        json={
            "items_csv": items_csv,
            "opt_json_inline": {
                "lo": 0,
                "hi": 100,
                "roi_target": 1.25,
                "risk_threshold": 0.80,
                "sims": 100,
            },
        },
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert "phases" in payload


def test_pipeline_with_outputs(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, opt_path = _mk_inputs(tmp_path)
    out_md = tmp_path / "report.md"
    r = client.post(
        "/v1/pipeline",
        headers={"X-API-Key": "secret123"},
        json={
            "items_csv": items_csv,
            "opt_json_path": opt_path,
            "out_markdown": str(out_md),
        },
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["markdown_path"] == str(out_md)
    # Verify file was written
    assert out_md.exists()
    content = out_md.read_text(encoding="utf-8")
    assert "Lot Analysis Report" in content or "Executive Summary" in content


def test_pipeline_stream(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, opt_path = _mk_inputs(tmp_path)
    with client.stream(
        "POST",
        "/v1/pipeline/stream",
        headers={"X-API-Key": "secret123"},
        json={"items_csv": items_csv, "opt_json_path": opt_path},
    ) as resp:
        assert resp.status_code == 200
        ctype = resp.headers.get("content-type", "")
        assert ctype.startswith("text/event-stream")
        # Check for nginx proxy header
        assert resp.headers.get("X-Accel-Buffering") == "no"
        body = ""
        for chunk in resp.iter_text():
            body += chunk
            if "done" in body:
                break
        # Check we saw several phases
        for token in [
            "start",
            "parse",
            "validate",
            "enrich_keepa",
            "price",
            "sell",
            "optimize",
            "render_report",
            "done",
        ]:
            assert token in body


def test_pipeline_missing_api_key(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, opt_path = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/pipeline", json={"items_csv": items_csv, "opt_json_path": opt_path}
    )
    assert r.status_code == 401


def test_pipeline_wrong_api_key(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, opt_path = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/pipeline",
        headers={"X-API-Key": "wrong"},
        json={"items_csv": items_csv, "opt_json_path": opt_path},
    )
    assert r.status_code == 401


def test_pipeline_missing_files(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    r = client.post(
        "/v1/pipeline",
        headers={"X-API-Key": "secret123"},
        json={"items_csv": "nonexistent.csv", "opt_json_path": "nonexistent.json"},
    )
    assert r.status_code == 404


def test_pipeline_no_opt_config(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, _ = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/pipeline",
        headers={"X-API-Key": "secret123"},
        json={"items_csv": items_csv},
    )  # Missing both opt_json_path and opt_json_inline
    assert r.status_code == 400


def test_pipeline_stream_inline_json(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, _ = _mk_inputs(tmp_path)
    with client.stream(
        "POST",
        "/v1/pipeline/stream",
        headers={"X-API-Key": "secret123"},
        json={
            "items_csv": items_csv,
            "opt_json_inline": {
                "lo": 0,
                "hi": 100,
                "roi_target": 1.25,
                "risk_threshold": 0.80,
                "sims": 100,
            },
        },
    ) as resp:
        assert resp.status_code == 200
        ctype = resp.headers.get("content-type", "")
        assert ctype.startswith("text/event-stream")
        body = ""
        for chunk in resp.iter_text():
            body += chunk
            if "done" in body:
                break
        assert "start" in body and "done" in body


def test_pipeline_path_traversal_attack(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    _, opt_path = _mk_inputs(tmp_path)
    # Try to access sensitive Windows files
    r = client.post(
        "/v1/pipeline",
        headers={"X-API-Key": "secret123"},
        json={
            "items_csv": "C:\\Windows\\system32\\config\\sam",
            "opt_json_path": opt_path,
        },
    )
    assert r.status_code == 400
    assert "Path not allowed" in r.json()["detail"]


def test_pipeline_stream_path_traversal_attack(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    _, opt_path = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/pipeline/stream",
        headers={"X-API-Key": "secret123"},
        json={
            "items_csv": "C:\\Windows\\system32\\config\\sam",
            "opt_json_path": opt_path,
        },
    )
    assert r.status_code == 400
    assert "Path not allowed" in r.json()["detail"]


def test_pipeline_output_path_traversal_attack(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, opt_path = _mk_inputs(tmp_path)
    # Try to write to sensitive Windows directory
    r = client.post(
        "/v1/pipeline",
        headers={"X-API-Key": "secret123"},
        json={
            "items_csv": items_csv,
            "opt_json_path": opt_path,
            "out_markdown": "C:\\Windows\\malicious.md",
        },
    )
    assert r.status_code == 400
    assert "Path not allowed" in r.json()["detail"]
