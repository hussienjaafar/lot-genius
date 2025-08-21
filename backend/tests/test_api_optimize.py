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


def test_optimize_blocking(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, opt_path = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/optimize",
        headers={"X-API-Key": "secret123"},
        json={"items_csv": items_csv, "opt_json_path": opt_path},
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert "summary" in payload and isinstance(payload["summary"], dict)
    # Check optimizer result structure
    summary = payload["summary"]
    assert "bid" in summary
    assert "meets_constraints" in summary
    assert "prob_roi_ge_target" in summary


def test_optimize_blocking_inline_json(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, _ = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/optimize",
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
    assert "summary" in payload


def test_optimize_with_output_file(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, opt_path = _mk_inputs(tmp_path)
    out_json = tmp_path / "result.json"
    r = client.post(
        "/v1/optimize",
        headers={"X-API-Key": "secret123"},
        json={
            "items_csv": items_csv,
            "opt_json_path": opt_path,
            "out_json": str(out_json),
        },
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["result_path"] == str(out_json)
    # Verify file was written
    assert out_json.exists()
    result_data = json.loads(out_json.read_text(encoding="utf-8"))
    assert "bid" in result_data


def test_optimize_stream(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, opt_path = _mk_inputs(tmp_path)
    with client.stream(
        "POST",
        "/v1/optimize/stream",
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
        assert "data:" in body and "start" in body and "done" in body


def test_optimize_missing_api_key(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, opt_path = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/optimize", json={"items_csv": items_csv, "opt_json_path": opt_path}
    )
    assert r.status_code == 401


def test_optimize_wrong_api_key(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, opt_path = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/optimize",
        headers={"X-API-Key": "wrong"},
        json={"items_csv": items_csv, "opt_json_path": opt_path},
    )
    assert r.status_code == 401


def test_optimize_missing_files(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    r = client.post(
        "/v1/optimize",
        headers={"X-API-Key": "secret123"},
        json={"items_csv": "nonexistent.csv", "opt_json_path": "nonexistent.json"},
    )
    assert r.status_code == 404


def test_optimize_no_opt_config(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    items_csv, _ = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/optimize",
        headers={"X-API-Key": "secret123"},
        json={"items_csv": items_csv},
    )  # Missing both opt_json_path and opt_json_inline
    assert r.status_code == 400


def test_optimize_path_traversal_attack(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    _, opt_path = _mk_inputs(tmp_path)
    # Try to access sensitive Windows files
    r = client.post(
        "/v1/optimize",
        headers={"X-API-Key": "secret123"},
        json={
            "items_csv": "C:\\Windows\\system32\\config\\sam",
            "opt_json_path": opt_path,
        },
    )
    assert r.status_code == 400
    assert "Path not allowed" in r.json()["detail"]


def test_optimize_stream_path_traversal_attack(tmp_path, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    _, opt_path = _mk_inputs(tmp_path)
    r = client.post(
        "/v1/optimize/stream",
        headers={"X-API-Key": "secret123"},
        json={
            "items_csv": "C:\\Windows\\system32\\config\\sam",
            "opt_json_path": opt_path,
        },
    )
    assert r.status_code == 400
    assert "Path not allowed" in r.json()["detail"]
