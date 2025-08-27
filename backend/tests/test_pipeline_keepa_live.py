"""Live Keepa pipeline integration tests - run only when KEEPA_API_KEY is set."""

import io
import json
import os
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app
try:
    from backend.app.main import app
except ImportError:
    from app.main import app


# Skip all tests if KEEPA_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("KEEPA_API_KEY"),
    reason="KEEPA_API_KEY not set - skipping live Keepa pipeline tests",
)


@pytest.fixture
def client():
    """Create TestClient for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def small_test_csv():
    """
    Create a small CSV with 1-2 rows for pipeline testing.
    Using known UPCs that should resolve via Keepa.
    """
    csv_content = """title,condition,category,upc
Echo Dot (3rd Gen),New,Electronics,841667174051
Echo Dot (4th Gen),Used - Good,Electronics,841667177386"""

    return csv_content


def parse_sse_events(response_content: str) -> List[Dict[str, Any]]:
    """
    Parse SSE stream content into a list of events.
    Each SSE frame has format:
    event: stage_name
    data: {"phase": "...", "message": "..."}

    """
    events = []
    lines = response_content.strip().split("\n")

    i = 0
    while i < len(lines):
        if lines[i].startswith("event: "):
            stage = lines[i][7:].strip()

            # Look for corresponding data line
            if i + 1 < len(lines) and lines[i + 1].startswith("data: "):
                data_line = lines[i + 1][6:].strip()

                try:
                    data = json.loads(data_line)
                except json.JSONDecodeError:
                    # If not JSON, store as raw string
                    data = {"raw": data_line}

                events.append({"stage": stage, "data": data})

                i += 2
            else:
                # Event without data
                events.append({"stage": stage, "data": {}})
                i += 1
        else:
            i += 1

    return events


@pytest.mark.skipif(
    not os.getenv("KEEPA_API_KEY"),
    reason="KEEPA_API_KEY not set - skipping live Keepa pipeline test",
)
@pytest.mark.skipif(
    os.getenv("SCRAPER_TOS_ACK") != "1",
    reason="SCRAPER_TOS_ACK not set to 1 - skipping scraper-dependent test",
)
def test_pipeline_streaming_with_keepa_integration(client, small_test_csv):
    """
    Test the full pipeline with live Keepa integration.
    POST small CSV to /v1/pipeline/upload/stream and verify SSE phases.
    """
    # Create CSV file-like object
    csv_file = io.BytesIO(small_test_csv.encode("utf-8"))

    # Prepare multipart form data
    files = {"items_csv": ("test.csv", csv_file, "text/csv")}

    # Make request to pipeline endpoint
    response = client.post("/v1/pipeline/upload/stream", files=files)

    # Should get streaming response
    assert (
        response.status_code == 200
    ), f"Pipeline request failed: {response.status_code} {response.text}"
    assert response.headers.get("content-type") == "text/event-stream"

    # Parse SSE events
    response_text = response.text
    events = parse_sse_events(response_text)

    print(f"Received {len(events)} SSE events")

    # Extract event stages for validation
    stages = [event["stage"] for event in events]
    print(f"Pipeline stages: {stages}")

    # Required phases that should be present
    required_phases = ["enrich_keepa", "price", "sell", "evidence", "optimize", "done"]

    for required_phase in required_phases:
        assert (
            required_phase in stages
        ), f"Missing required phase: {required_phase}. Got stages: {stages}"

    # Verify final event is 'done' with final_summary
    final_event = None
    for event in events:
        if event["stage"] == "done":
            final_event = event
            break

    assert final_event is not None, "No 'done' event found in pipeline"

    # Check final summary structure
    final_data = final_event["data"]
    assert "type" in final_data, f"Final event missing 'type' field: {final_data}"
    assert (
        final_data["type"] == "final_summary"
    ), f"Final event type should be 'final_summary', got: {final_data.get('type')}"

    # Should have non-empty payload
    assert "payload" in final_data, f"Final event missing 'payload' field: {final_data}"
    payload = final_data["payload"]
    assert payload is not None and len(payload) > 0, "Final payload should be non-empty"

    # Basic payload structure checks
    expected_payload_fields = [
        "bid",
        "roi_p50",
        "cash_60d_p50",
        "items",
        "meets_constraints",
    ]
    for field in expected_payload_fields:
        if field in payload:
            print(f"✓ Payload contains {field}: {payload[field]}")

    print("✓ Pipeline completed successfully with Keepa integration")
    print(f"✓ Final payload keys: {list(payload.keys())}")


@pytest.mark.skipif(
    not os.getenv("KEEPA_API_KEY"),
    reason="KEEPA_API_KEY not set - skipping live Keepa pipeline test",
)
def test_pipeline_keepa_enrichment_phase(client, small_test_csv):
    """
    Focused test on the enrich_keepa phase to verify Keepa integration.
    This test doesn't require SCRAPER_TOS_ACK.
    """
    # Create CSV file-like object
    csv_file = io.BytesIO(small_test_csv.encode("utf-8"))

    # Prepare multipart form data
    files = {"items_csv": ("test.csv", csv_file, "text/csv")}

    # Make request to pipeline endpoint
    response = client.post("/v1/pipeline/upload/stream", files=files)

    # Should get streaming response
    assert response.status_code == 200

    # Parse SSE events
    events = parse_sse_events(response.text)
    stages = [event["stage"] for event in events]

    # Should have enrich_keepa phase
    assert "enrich_keepa" in stages, f"Missing enrich_keepa phase. Got stages: {stages}"

    # Find the enrich_keepa event
    keepa_event = None
    for event in events:
        if event["stage"] == "enrich_keepa":
            keepa_event = event
            break

    assert keepa_event is not None
    print(f"✓ Keepa enrichment phase found: {keepa_event['data']}")

    # Should eventually complete (have done phase)
    assert "done" in stages, "Pipeline should complete with 'done' phase"

    print("✓ Keepa enrichment phase executed successfully")


def test_pipeline_without_multipart_fails(client):
    """Test that pipeline endpoint requires multipart form data."""
    # Try to send JSON instead of multipart
    response = client.post("/v1/pipeline/upload/stream", json={"test": "data"})

    # Should fail - exact error depends on implementation
    assert response.status_code != 200, "Pipeline should reject non-multipart requests"
    print(
        f"✓ Pipeline correctly rejects non-multipart requests: {response.status_code}"
    )


def test_pipeline_without_csv_file_fails(client):
    """Test that pipeline endpoint requires CSV file."""
    # Send multipart but without the required CSV file
    files = {"wrong_field": ("test.txt", io.BytesIO(b"test"), "text/plain")}

    response = client.post("/v1/pipeline/upload/stream", files=files)

    # Should fail due to missing CSV
    assert response.status_code != 200, "Pipeline should require items_csv file"
    print(f"✓ Pipeline correctly rejects requests without CSV: {response.status_code}")
