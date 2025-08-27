from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    items_csv: str = Field(..., description="Path to items CSV on server filesystem")
    opt_json_path: Optional[str] = Field(None, description="Path to optimizer JSON")
    opt_json_inline: Optional[dict] = Field(
        None, description="Inline optimizer JSON (if no path)"
    )
    evidence_jsonl: Optional[str] = None
    stress_csv: Optional[str] = None
    stress_json: Optional[str] = None
    out_markdown: Optional[str] = None
    out_html: Optional[str] = None
    out_pdf: Optional[str] = None


class ReportResponse(BaseModel):
    status: str
    markdown_path: Optional[str] = None
    html_path: Optional[str] = None
    pdf_path: Optional[str] = None
    # Include a small preview for convenience:
    markdown_preview: Optional[str] = None
    # Optional cache metrics when CACHE_METRICS=1
    cache_stats: Optional[Dict[str, Any]] = None


class OptimizeRequest(BaseModel):
    # Path to canonical item CSV (can be a raw manifest; rely on same ingestion as report)
    items_csv: str
    # Either inline optimizer knobs or path to a JSON file (same behavior as report)
    opt_json_inline: Optional[Dict[str, Any]] = None
    opt_json_path: Optional[str] = None
    # Optional outputs (for debugging/inspection), OK if omitted
    out_json: Optional[str] = None  # write the optimizer result JSON here if provided


class OptimizeResponse(BaseModel):
    status: str  # "ok" | "error"
    summary: Dict[
        str, Any
    ]  # compact optimizer result (evidence, max_bid, constraints met, etc.)
    result_path: Optional[str] = None  # if out_json provided and successfully written


class PipelineRequest(BaseModel):
    items_csv: str
    opt_json_inline: Optional[Dict[str, Any]] = None
    opt_json_path: Optional[str] = None
    # Optional artifacts
    stress_csv: Optional[str] = None
    stress_json: Optional[str] = None
    out_markdown: Optional[str] = None
    out_html: Optional[str] = None
    out_pdf: Optional[str] = None


class PipelineResponse(BaseModel):
    status: str  # "ok" | "error"
    phases: List[str]  # ordered phases completed
    markdown_preview: Optional[str] = None
    markdown_path: Optional[str] = None
    html_path: Optional[str] = None
    pdf_path: Optional[str] = None


class FeedRequest(BaseModel):
    """Request schema for feed/watchlist CSV import."""

    feed_csv: str = Field(..., description="Path to feed CSV on server filesystem")
    opt_json_inline: Optional[Dict[str, Any]] = Field(
        None, description="Inline optimizer JSON (if needed)"
    )
    opt_json_path: Optional[str] = Field(None, description="Path to optimizer JSON")
    # Output options
    out_csv: Optional[str] = Field(None, description="Output normalized CSV path")
    out_json: Optional[str] = Field(None, description="Output normalized JSON path")


class FeedResponse(BaseModel):
    """Response schema for feed/watchlist processing."""

    status: str  # "ok" | "error"
    items_processed: int
    items_normalized: Optional[str] = None  # Path to normalized items CSV/JSON
    pipeline_ready: bool = False  # Whether items are ready for pipeline
    summary: Dict[str, Any] = {}  # Basic stats about the feed
