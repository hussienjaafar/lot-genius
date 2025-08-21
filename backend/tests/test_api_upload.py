import io
import json

import pandas as pd
from fastapi.testclient import TestClient

from backend.app.main import app


def _files():
    """Create test file uploads as BytesIO objects."""
    csv_bytes = io.BytesIO()
    pd.DataFrame(
        [
            {
                "sku_local": "A",
                "est_price_mu": 60.0,
                "est_price_sigma": 12.0,
                "sell_p60": 0.6,
            }
        ]
    ).to_csv(csv_bytes, index=False)
    csv_bytes.seek(0)

    opt_bytes = io.BytesIO(
        json.dumps(
            {
                "lo": 0,
                "hi": 100,
                "roi_target": 1.25,
                "risk_threshold": 0.80,
                "sims": 100,  # Small for fast tests
            }
        ).encode("utf-8")
    )
    opt_bytes.seek(0)

    return csv_bytes, opt_bytes


def test_optimize_upload_blocking(monkeypatch):
    """Test blocking optimize upload endpoint."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, opt = _files()

    r = client.post(
        "/v1/optimize/upload",
        headers={"X-API-Key": "secret123"},
        files={
            "items_csv": ("items.csv", csv, "text/csv"),
            "opt_json": ("opt.json", opt, "application/json"),
        },
    )
    assert r.status_code == 200
    js = r.json()
    assert js["status"] == "ok"
    assert "summary" in js
    assert isinstance(js["summary"], dict)
    # Check optimizer result structure
    summary = js["summary"]
    assert "bid" in summary
    assert "meets_constraints" in summary
    assert "prob_roi_ge_target" in summary


def test_optimize_upload_blocking_csv_only(monkeypatch):
    """Test optimize upload with only CSV file (no opt_json)."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, _ = _files()

    r = client.post(
        "/v1/optimize/upload",
        headers={"X-API-Key": "secret123"},
        files={"items_csv": ("items.csv", csv, "text/csv")},
    )
    # Should fail because opt_json or opt_json_inline is required
    assert r.status_code == 400
    assert "opt_json (file) or opt_json_inline (JSON) is required" in r.json()["detail"]


def test_optimize_upload_stream(monkeypatch):
    """Test streaming optimize upload endpoint."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, opt = _files()

    with client.stream(
        "POST",
        "/v1/optimize/upload/stream",
        headers={"X-API-Key": "secret123"},
        files={
            "items_csv": ("items.csv", csv, "text/csv"),
            "opt_json": ("opt.json", opt, "application/json"),
        },
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

        # Check we saw key events
        for event in ["start", "optimize", "done"]:
            assert event in body


def test_pipeline_upload_blocking(monkeypatch):
    """Test blocking pipeline upload endpoint."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, opt = _files()

    r = client.post(
        "/v1/pipeline/upload",
        headers={"X-API-Key": "secret123"},
        files={
            "items_csv": ("items.csv", csv, "text/csv"),
            "opt_json": ("opt.json", opt, "application/json"),
        },
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


def test_pipeline_upload_stream(monkeypatch):
    """Test streaming pipeline upload endpoint."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, opt = _files()

    with client.stream(
        "POST",
        "/v1/pipeline/upload/stream",
        headers={"X-API-Key": "secret123"},
        files={
            "items_csv": ("items.csv", csv, "text/csv"),
            "opt_json": ("opt.json", opt, "application/json"),
        },
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


def test_upload_auth_required(monkeypatch):
    """Test that upload endpoints require authentication."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, opt = _files()

    # Test all upload endpoints without auth
    endpoints = [
        "/v1/optimize/upload",
        "/v1/optimize/upload/stream",
        "/v1/pipeline/upload",
        "/v1/pipeline/upload/stream",
    ]

    for endpoint in endpoints:
        r = client.post(endpoint, files={"items_csv": ("items.csv", csv, "text/csv")})
        assert r.status_code == 401
        csv.seek(0)  # Reset for next test


def test_upload_wrong_api_key(monkeypatch):
    """Test upload endpoints with wrong API key."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, opt = _files()

    r = client.post(
        "/v1/optimize/upload",
        headers={"X-API-Key": "wrong"},
        files={"items_csv": ("items.csv", csv, "text/csv")},
    )
    assert r.status_code == 401


def test_upload_missing_csv(monkeypatch):
    """Test upload endpoints with missing required CSV file."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")

    r = client.post(
        "/v1/optimize/upload",
        headers={"X-API-Key": "secret123"},
        files={},  # No files
    )
    assert r.status_code == 422  # Validation error from FastAPI


def test_pipeline_upload_with_output_paths(monkeypatch, tmp_path):
    """Test pipeline upload with output file paths."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, opt = _files()

    out_md = tmp_path / "report.md"

    r = client.post(
        "/v1/pipeline/upload",
        headers={"X-API-Key": "secret123"},
        files={
            "items_csv": ("items.csv", csv, "text/csv"),
            "opt_json": ("opt.json", opt, "application/json"),
        },
        data={"out_markdown": str(out_md)},
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["markdown_path"] == str(out_md)
    # Verify file was written
    assert out_md.exists()
    content = out_md.read_text(encoding="utf-8")
    assert "Lot Analysis Report" in content or "Executive Summary" in content


def test_optimize_upload_with_output_path(monkeypatch, tmp_path):
    """Test optimize upload with output JSON path."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, opt = _files()

    out_json = tmp_path / "result.json"

    r = client.post(
        "/v1/optimize/upload",
        headers={"X-API-Key": "secret123"},
        files={
            "items_csv": ("items.csv", csv, "text/csv"),
            "opt_json": ("opt.json", opt, "application/json"),
        },
        data={"out_json": str(out_json)},
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["result_path"] == str(out_json)
    # Verify file was written
    assert out_json.exists()
    result_data = json.loads(out_json.read_text(encoding="utf-8"))
    assert "bid" in result_data


def test_upload_invalid_output_path(monkeypatch):
    """Test upload endpoints with invalid output paths (path traversal)."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, opt = _files()

    # Try to write to a sensitive Windows directory
    r = client.post(
        "/v1/pipeline/upload",
        headers={"X-API-Key": "secret123"},
        files={
            "items_csv": ("items.csv", csv, "text/csv"),
            "opt_json": ("opt.json", opt, "application/json"),
        },
        data={"out_markdown": "C:\\Windows\\malicious.md"},
    )
    assert r.status_code == 400
    assert "Path not allowed" in r.json()["detail"]


def test_pipeline_upload_stream_csv_only_400(monkeypatch):
    """Test streaming pipeline upload with only CSV file returns 400."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, _ = _files()

    r = client.post(
        "/v1/pipeline/upload/stream",
        headers={"X-API-Key": "secret123"},
        files={"items_csv": ("items.csv", csv, "text/csv")},
    )
    # Should fail with 400 before streaming starts
    assert r.status_code == 400
    assert "opt_json (file) or opt_json_inline (JSON) is required" in r.json()["detail"]


def test_optimize_upload_inline_config(monkeypatch):
    """Test optimize upload with inline JSON config."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, _ = _files()

    r = client.post(
        "/v1/optimize/upload",
        headers={"X-API-Key": "secret123"},
        files={"items_csv": ("items.csv", csv, "text/csv")},
        data={
            "opt_json_inline": json.dumps(
                {
                    "lo": 0,
                    "hi": 100,
                    "roi_target": 1.25,
                    "risk_threshold": 0.80,
                    "sims": 100,
                }
            )
        },
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert "summary" in payload
    # Check optimizer result structure
    summary = payload["summary"]
    assert "bid" in summary
    assert "meets_constraints" in summary
    assert "prob_roi_ge_target" in summary


def test_pipeline_upload_inline_config(monkeypatch):
    """Test pipeline upload with inline JSON config."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, _ = _files()

    r = client.post(
        "/v1/pipeline/upload",
        headers={"X-API-Key": "secret123"},
        files={"items_csv": ("items.csv", csv, "text/csv")},
        data={
            "opt_json_inline": json.dumps(
                {
                    "lo": 0,
                    "hi": 100,
                    "roi_target": 1.25,
                    "risk_threshold": 0.80,
                    "sims": 100,
                }
            )
        },
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


def test_upload_temp_file_cleanup(monkeypatch, tmp_path):
    """Test that temporary files are cleaned up after processing."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    csv, opt = _files()

    # Count temp files before
    import glob
    import tempfile

    temp_dir = tempfile.gettempdir()
    lotgenius_files_before = glob.glob(f"{temp_dir}/lotgenius_*")

    r = client.post(
        "/v1/optimize/upload",
        headers={"X-API-Key": "secret123"},
        files={
            "items_csv": ("items.csv", csv, "text/csv"),
            "opt_json": ("opt.json", opt, "application/json"),
        },
    )
    assert r.status_code == 200

    # Count temp files after - should be the same (files cleaned up)
    lotgenius_files_after = glob.glob(f"{temp_dir}/lotgenius_*")
    assert len(lotgenius_files_after) == len(lotgenius_files_before)


def test_optimize_upload_inline_config_new(monkeypatch):
    """Test optimize upload with inline JSON config."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    import io
    import json

    import pandas as pd

    csv = io.BytesIO()
    pd.DataFrame([{"sku_local": "A"}]).to_csv(csv, index=False)
    csv.seek(0)
    r = client.post(
        "/v1/optimize/upload",
        headers={"X-API-Key": "secret123"},
        files={"items_csv": ("items.csv", csv, "text/csv")},
        data={"opt_json_inline": json.dumps({"bid": 100})},
    )
    assert r.status_code == 200
    js = r.json()
    assert js["status"] == "ok"
    assert "summary" in js


def test_pipeline_upload_csv_only_400(monkeypatch):
    """Test pipeline upload with only CSV returns 400."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    import io

    import pandas as pd

    csv = io.BytesIO()
    pd.DataFrame([{"sku_local": "A"}]).to_csv(csv, index=False)
    csv.seek(0)
    r = client.post(
        "/v1/pipeline/upload",
        headers={"X-API-Key": "secret123"},
        files={"items_csv": ("items.csv", csv, "text/csv")},
    )
    assert r.status_code == 400
    assert "opt_json" in r.text


def test_pipeline_upload_stream_csv_only_400_new(monkeypatch):
    """Test streaming pipeline upload with only CSV returns 400."""
    client = TestClient(app)
    monkeypatch.setenv("LOTGENIUS_API_KEY", "secret123")
    import io

    import pandas as pd

    csv = io.BytesIO()
    pd.DataFrame([{"sku_local": "A"}]).to_csv(csv, index=False)
    csv.seek(0)
    with client.stream(
        "POST",
        "/v1/pipeline/upload/stream",
        headers={"X-API-Key": "secret123"},
        files={"items_csv": ("items.csv", csv, "text/csv")},
    ) as resp:
        assert resp.status_code == 400
