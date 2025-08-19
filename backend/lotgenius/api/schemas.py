from typing import Optional

from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    items_csv: str = Field(..., description="Path to items CSV on server filesystem")
    opt_json_path: Optional[str] = Field(None, description="Path to optimizer JSON")
    opt_json_inline: Optional[dict] = Field(
        None, description="Inline optimizer JSON (if no path)"
    )
    evidence_jsonl: Optional[str] = None
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
