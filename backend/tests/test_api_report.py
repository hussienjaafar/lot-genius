import json
import os
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


@pytest.fixture
def temp_data(tmp_path):
    """Create temporary test data files."""
    # Create minimal items CSV
    items_df = pd.DataFrame([{"sku_local": "TEST001"}, {"sku_local": "TEST002"}])
    items_csv = tmp_path / "items.csv"
    items_df.to_csv(items_csv, index=False)

    # Create minimal optimizer JSON
    opt_data = {"bid": 100.0}
    opt_json = tmp_path / "opt.json"
    opt_json.write_text(json.dumps(opt_data), encoding="utf-8")

    return {
        "items_csv": str(items_csv),
        "opt_json": str(opt_json),
        "opt_data": opt_data,
        "tmp_path": tmp_path,
    }


def test_healthz():
    """Test health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_report_minimal(temp_data):
    """Test minimal report generation."""
    request_data = {
        "items_csv": temp_data["items_csv"],
        "opt_json_path": temp_data["opt_json"],
        "out_markdown": str(temp_data["tmp_path"] / "report.md"),
    }

    response = client.post("/v1/report", json=request_data)
    assert response.status_code == 200

    result = response.json()
    assert result["status"] == "ok"
    assert result["markdown_path"] == request_data["out_markdown"]
    assert result["markdown_preview"] is not None
    assert len(result["markdown_preview"]) > 0
    assert "# Lot Genius Report" in result["markdown_preview"]

    # Verify markdown file was created
    assert Path(request_data["out_markdown"]).exists()


def test_report_inline_json(temp_data):
    """Test report generation with inline JSON."""
    request_data = {
        "items_csv": temp_data["items_csv"],
        "opt_json_inline": temp_data["opt_data"],
        "out_markdown": str(temp_data["tmp_path"] / "report_inline.md"),
    }

    response = client.post("/v1/report", json=request_data)
    assert response.status_code == 200

    result = response.json()
    assert result["status"] == "ok"
    assert result["markdown_preview"] is not None


def test_report_missing_file():
    """Test report generation with missing file."""
    request_data = {
        "items_csv": "/nonexistent/path.csv",
        "opt_json_path": "/nonexistent/opt.json",
    }

    response = client.post("/v1/report", json=request_data)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_report_no_opt_json(temp_data):
    """Test report generation without optimizer JSON."""
    request_data = {"items_csv": temp_data["items_csv"]}  # Valid file, but no opt_json

    response = client.post("/v1/report", json=request_data)
    assert response.status_code == 400
    assert "must be provided" in response.json()["detail"]


def test_report_stream_minimal(temp_data):
    """Test minimal streaming report generation."""
    request_data = {
        "items_csv": temp_data["items_csv"],
        "opt_json_path": temp_data["opt_json"],
    }

    response = client.post("/v1/report/stream", json=request_data)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Parse SSE events
    content = response.content.decode("utf-8")
    events = []
    for line in content.split("\n"):
        if line.startswith("data: "):
            event_data = json.loads(line[6:])  # Remove "data: " prefix
            events.append(event_data)

    # Verify key events are present
    event_stages = [event.get("stage") for event in events]
    assert "start" in event_stages
    assert "generate_markdown" in event_stages
    assert "done" in event_stages

    # Verify structure of events
    start_event = next(e for e in events if e.get("stage") == "start")
    assert start_event["stage"] == "start"

    done_event = next(e for e in events if e.get("stage") == "done")
    assert done_event["stage"] == "done"
    assert done_event["ok"] is True


def test_api_key_protection(temp_data, monkeypatch):
    """Test API key protection when LOTGENIUS_API_KEY is set."""
    # Set API key environment variable
    monkeypatch.setenv("LOTGENIUS_API_KEY", "test-secret-key")

    request_data = {
        "items_csv": temp_data["items_csv"],
        "opt_json_path": temp_data["opt_json"],
    }

    # Request without API key should fail
    response = client.post("/v1/report", json=request_data)
    assert response.status_code == 401
    assert "Invalid or missing API key" in response.json()["detail"]

    # Request with wrong API key should fail
    response = client.post(
        "/v1/report", json=request_data, headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401

    # Request with correct API key should succeed
    response = client.post(
        "/v1/report", json=request_data, headers={"X-API-Key": "test-secret-key"}
    )
    assert response.status_code == 200


def test_api_key_optional_when_not_set(temp_data):
    """Test API is open when LOTGENIUS_API_KEY is not set."""
    # Ensure API key is not set
    if "LOTGENIUS_API_KEY" in os.environ:
        del os.environ["LOTGENIUS_API_KEY"]

    request_data = {
        "items_csv": temp_data["items_csv"],
        "opt_json_path": temp_data["opt_json"],
    }

    # Request without API key should succeed when key is not configured
    response = client.post("/v1/report", json=request_data)
    assert response.status_code == 200
