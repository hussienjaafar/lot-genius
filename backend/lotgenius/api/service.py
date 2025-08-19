import json
import os
from pathlib import Path
from typing import Any, Dict, Generator

import pandas as pd
from lotgenius.api.schemas import ReportRequest, ReportResponse
from lotgenius.cli.report_lot import _mk_markdown, _optional_html, _optional_pdf


def validate_file_paths(req: ReportRequest) -> None:
    """Validate that required file paths exist."""
    if not Path(req.items_csv).exists():
        raise FileNotFoundError(f"Items CSV not found: {req.items_csv}")

    if req.opt_json_path and not Path(req.opt_json_path).exists():
        raise FileNotFoundError(f"Optimizer JSON not found: {req.opt_json_path}")

    if req.evidence_jsonl and not Path(req.evidence_jsonl).exists():
        raise FileNotFoundError(f"Evidence JSONL not found: {req.evidence_jsonl}")


def prepare_opt_json(req: ReportRequest) -> str:
    """Prepare optimizer JSON, either from path or inline data."""
    if req.opt_json_path:
        return req.opt_json_path

    if req.opt_json_inline:
        # Create temp file for inline JSON
        temp_dir = Path("data/api/tmp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        temp_file = temp_dir / f"opt_{os.getpid()}_{id(req.opt_json_inline)}.json"
        temp_file.write_text(json.dumps(req.opt_json_inline), encoding="utf-8")
        return str(temp_file)

    raise ValueError("Either opt_json_path or opt_json_inline must be provided")


def generate_report(req: ReportRequest) -> ReportResponse:
    """Generate report synchronously."""
    # Validate inputs
    validate_file_paths(req)

    # Load data
    items_df = pd.read_csv(req.items_csv)
    opt_json_path = prepare_opt_json(req)
    opt_dict = json.loads(Path(opt_json_path).read_text(encoding="utf-8"))

    # Generate markdown
    markdown_content = _mk_markdown(
        items_df,
        opt_dict,
        sweep_csv=None,  # Not used in API
        sweep_png=None,  # Not used in API
        evidence_jsonl=req.evidence_jsonl,
    )

    # Write markdown if path provided
    markdown_path = None
    if req.out_markdown:
        markdown_path = Path(req.out_markdown)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown_content, encoding="utf-8")

    # Optional HTML conversion
    html_path = None
    if req.out_html and req.out_markdown:
        html_path = _optional_html(Path(req.out_markdown), Path(req.out_html))

    # Optional PDF conversion
    pdf_path = None
    if req.out_pdf and req.out_markdown:
        pdf_path = _optional_pdf(Path(req.out_markdown), Path(req.out_pdf))

    # Clean up temp file if created
    if req.opt_json_inline and opt_json_path != req.opt_json_path:
        try:
            Path(opt_json_path).unlink()
        except Exception:
            pass  # Best effort cleanup

    # Prepare preview (truncated)
    preview = markdown_content[:4096]
    if len(markdown_content) > 4096:
        preview += "\n\n... (truncated)"

    return ReportResponse(
        status="ok",
        markdown_path=str(markdown_path) if markdown_path else None,
        html_path=str(html_path) if html_path else None,
        pdf_path=str(pdf_path) if pdf_path else None,
        markdown_preview=preview,
    )


def report_stream(req: ReportRequest) -> Generator[Dict[str, Any], None, None]:
    """Generate report with streaming progress events."""
    try:
        # Start
        yield {"stage": "start"}

        # Validate inputs
        validate_file_paths(req)

        # Load data
        items_df = pd.read_csv(req.items_csv)
        opt_json_path = prepare_opt_json(req)
        opt_dict = json.loads(Path(opt_json_path).read_text(encoding="utf-8"))

        # Generate markdown
        markdown_content = _mk_markdown(
            items_df,
            opt_dict,
            sweep_csv=None,
            sweep_png=None,
            evidence_jsonl=req.evidence_jsonl,
        )
        yield {"stage": "generate_markdown", "ok": True}

        # Write markdown if path provided
        markdown_path = None
        if req.out_markdown:
            markdown_path = Path(req.out_markdown)
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text(markdown_content, encoding="utf-8")

        # Optional HTML conversion
        html_path = None
        if req.out_html and req.out_markdown:
            html_path = _optional_html(Path(req.out_markdown), Path(req.out_html))
            yield {"stage": "html", "ok": html_path is not None}

        # Optional PDF conversion
        pdf_path = None
        if req.out_pdf and req.out_markdown:
            pdf_path = _optional_pdf(Path(req.out_markdown), Path(req.out_pdf))
            yield {"stage": "pdf", "ok": pdf_path is not None}

        # Clean up temp file if created
        if req.opt_json_inline and opt_json_path != req.opt_json_path:
            try:
                Path(opt_json_path).unlink()
            except Exception:
                pass

        # Done
        yield {"stage": "done", "ok": True}

    except Exception as e:
        yield {"stage": "error", "ok": False, "error": str(e)}
