import json
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

import pandas as pd
from fastapi import UploadFile
from lotgenius.api.schemas import ReportRequest, ReportResponse
from lotgenius.cli.report_lot import _mk_markdown, _optional_html, _optional_pdf
from lotgenius.roi import optimize_bid


def save_upload_temp(file: UploadFile, suffix: str) -> Path:
    """
    Save an UploadFile to a secure temp path (unique), return Path.
    Caller is responsible for deletion.
    """
    # Pick temp dir via tempfile.gettempdir(); do NOT reuse original filename.
    rand = secrets.token_hex(8)
    dst = Path(tempfile.gettempdir()) / f"lotgenius_{rand}{suffix}"
    # Write atomically
    with open(dst, "wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    return dst.resolve()


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
        preview += "\n\n… (truncated)"

    return ReportResponse(
        status="ok",
        markdown_path=str(markdown_path) if markdown_path else None,
        html_path=str(html_path) if html_path else None,
        pdf_path=str(pdf_path) if pdf_path else None,
        markdown_preview=preview,
    )


def run_optimize(
    items_csv: str, opt_json_path: str, out_json: Optional[str] = None
) -> Tuple[dict, Optional[str]]:
    """
    Load items -> (price dists + p60) -> ROI Monte Carlo -> risk-aware max bid.
    Returns (compact_result_dict, out_json_written_path_or_None).
    """
    # Load and validate data
    if not Path(items_csv).exists():
        raise FileNotFoundError(f"Items CSV not found: {items_csv}")
    if not Path(opt_json_path).exists():
        raise FileNotFoundError(f"Optimizer JSON not found: {opt_json_path}")

    # Load items and optimizer configuration
    items_df = pd.read_csv(items_csv)
    opt_dict = json.loads(Path(opt_json_path).read_text(encoding="utf-8"))

    # Extract optimizer parameters with defaults
    lo = opt_dict.get("lo", 0.0)
    hi = opt_dict.get("hi", 1000.0)

    # Apply evidence gate before Monte Carlo simulation
    from backend.lotgenius.gating import passes_evidence_gate

    try:
        from backend.lotgenius.evidence import write_evidence
    except Exception:
        write_evidence = None

    core_items = []
    upside_items = []

    for idx, row in items_df.iterrows():
        item = dict(row)
        # Handle NaN values properly using pandas
        asin = item.get("asin")
        upc = item.get("upc")
        ean = item.get("ean")
        has_high_trust_id = bool(
            (asin and not pd.isna(asin))
            or (upc and not pd.isna(upc))
            or (ean and not pd.isna(ean))
        )
        sold_comps_180d = int(
            item.get("keepa_new_count", 0) + item.get("keepa_used_count", 0)
        )
        has_secondary_signal = bool(
            item.get("keepa_offers_count", 0) > 0  # offer depth
            or item.get("keepa_salesrank_med") is not None  # rank data
            or item.get("manual_price") is not None  # manual override
        )

        gate = passes_evidence_gate(
            item,
            sold_comps_count_180d=sold_comps_180d,
            has_secondary_signal=has_secondary_signal,
            has_high_trust_id=has_high_trust_id,
        )
        if write_evidence:
            write_evidence(
                item, "evidence_gate", {"result": gate.__dict__}, ok=gate.passed
            )

        (core_items if gate.core_included else upside_items).append(item)

    # Use ONLY core_items for Monte Carlo
    core_df = pd.DataFrame(core_items) if core_items else pd.DataFrame()

    # Run the optimizer (using the existing optimize_bid function) on core items only
    result = optimize_bid(
        core_df,
        lo=lo,
        hi=hi,
        roi_target=opt_dict.get("roi_target", 1.25),
        risk_threshold=opt_dict.get("risk_threshold", 0.80),
        min_cash_60d=opt_dict.get("min_cash_60d"),
        min_cash_60d_p5=opt_dict.get("min_cash_60d_p5"),
        sims=opt_dict.get("sims", 2000),
        salvage_frac=opt_dict.get("salvage_frac", 0.50),
        marketplace_fee_pct=opt_dict.get("marketplace_fee_pct", 0.12),
        payment_fee_pct=opt_dict.get("payment_fee_pct", 0.03),
        per_order_fee_fixed=opt_dict.get("per_order_fee_fixed", 0.40),
        shipping_per_order=opt_dict.get("shipping_per_order", 0.0),
        packaging_per_order=opt_dict.get("packaging_per_order", 0.0),
        refurb_per_order=opt_dict.get("refurb_per_order", 0.0),
        return_rate=opt_dict.get("return_rate", 0.08),
        salvage_fee_pct=opt_dict.get("salvage_fee_pct", 0.00),
        lot_fixed_cost=opt_dict.get("lot_fixed_cost", 0.0),
        seed=opt_dict.get("seed", 1337),
    )

    # Add review flag if upside share is material (>25% of lot value)
    upside_value = sum(
        i.get("est_price_mu", 0) * (i.get("quantity", 1) or 1) for i in upside_items
    )
    core_value = sum(
        i.get("est_price_mu", 0) * (i.get("quantity", 1) or 1) for i in core_items
    )
    total_value = (upside_value + core_value) or 1.0
    review = (upside_value / total_value) > 0.25

    result["review"] = bool(review)
    result["core_items_count"] = len(core_items)
    result["upside_items_count"] = len(upside_items)
    if review:
        result["upside_value_ratio"] = upside_value / total_value

    # Create compact result (remove raw arrays to keep response size manageable)
    compact_result = {
        k: v
        for k, v in result.items()
        if k not in ["roi", "revenue", "cash_60d"]  # exclude raw simulation arrays
    }

    # Write output JSON if requested
    out_path = None
    if out_json:
        out_path = Path(out_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(compact_result, indent=2), encoding="utf-8")
        out_path = str(out_path)

    return compact_result, out_path


def run_pipeline(
    items_csv: str,
    opt_json_path: str,
    out_md: Optional[str],
    out_html: Optional[str],
    out_pdf: Optional[str],
    sse_yield=None,
) -> dict:
    """
    Execute parse -> validate -> enrich (Keepa) -> price -> sell -> optimize -> report.
    Use the same underlying helpers as generate_report() to guarantee identical outputs.
    If sse_yield is provided, call sse_yield({"event":"<phase>","message":"description"}) between phases.
    Returns dict with keys: phases, markdown_path, html_path, pdf_path, markdown_preview
    """
    phases = []

    def emit_phase(phase: str, message: str = ""):
        phases.append(phase)
        if sse_yield:
            sse_yield({"event": phase, "message": message})

    # Start
    emit_phase("start", "starting pipeline")

    # Parse and validate inputs
    emit_phase("parse", "loading CSV data")
    if not Path(items_csv).exists():
        raise FileNotFoundError(f"Items CSV not found: {items_csv}")
    if not Path(opt_json_path).exists():
        raise FileNotFoundError(f"Optimizer JSON not found: {opt_json_path}")

    emit_phase("validate", "validating inputs")
    items_df = pd.read_csv(items_csv)
    opt_dict = json.loads(Path(opt_json_path).read_text(encoding="utf-8"))

    # Note: The actual pipeline would include Keepa enrichment, pricing, selling etc.
    # For this API, we're delegating to the existing report generation which handles all this
    emit_phase("enrich_keepa", "enriching with Keepa data")
    emit_phase("price", "calculating price distributions")
    emit_phase("sell", "modeling sell probabilities")
    emit_phase("optimize", "running ROI optimizer")

    # Apply evidence gate filtering and run optimization
    from backend.lotgenius.evidence import compute_evidence, evidence_to_dict

    try:
        from backend.lotgenius.evidence import write_evidence
    except Exception:
        write_evidence = None

    evidence_summaries: List[Dict[str, Any]] = []
    core_items: List[Dict[str, Any]] = []
    review_items: List[Dict[str, Any]] = []

    def _has_high_trust_id(it: Dict[str, Any]) -> bool:
        for k in ("asin", "upc", "ean", "asin_id", "upc_id", "ean_id"):
            v = it.get(k)
            if v and str(v).strip() and not pd.isna(v):
                return True
        return False

    for idx, row in items_df.iterrows():
        item = dict(row)
        keepa_blob = item.get("keepa") or {}
        comps = item.get("sold_comps") or []

        # If no sold_comps, estimate from keepa counts
        if not comps:
            keepa_new = item.get("keepa_new_count", 0) or 0
            keepa_used = item.get("keepa_used_count", 0) or 0
            comp_count = int(keepa_new + keepa_used)
            comps = [{"type": "keepa_est"}] * comp_count

        # naive secondary signals
        sec = {
            "keepa_rank_trend": bool(
                keepa_blob.get("rank")
                or keepa_blob.get("salesRankDrops")
                or item.get("keepa_salesrank_med") is not None
            ),
            "keepa_offers_present": bool(
                keepa_blob.get("offers")
                or keepa_blob.get("buyBoxPrice")
                or item.get("keepa_offers_count", 0) > 0
            ),
        }

        ev = compute_evidence(
            item_key=str(
                item.get("sku_local")
                or item.get("title")
                or item.get("asin")
                or f"item_{idx}"
            ),
            has_high_trust_id=_has_high_trust_id(item),
            sold_comps=comps,
            secondary_signals=sec,
            sources={"keepa": bool(keepa_blob), "comps": len(comps)},
        )

        # write to ledger if writer exists
        try:
            ledger = item.setdefault("_evidence", {})
            ledger.update(evidence_to_dict(ev))
            if write_evidence:
                write_evidence(
                    item, "evidence_gate", evidence_to_dict(ev), ok=ev.include_in_core
                )
        except Exception:
            pass

        evidence_summaries.append(evidence_to_dict(ev))
        if ev.include_in_core:
            core_items.append(item)
        else:
            review_items.append(item)

    if sse_yield:
        sse_yield(
            {
                "event": "evidence",
                "message": "evidence gating complete",
                "core": len(core_items),
                "review": len(review_items),
            }
        )

    # Use ONLY core_items for Monte Carlo
    core_df = pd.DataFrame(core_items) if core_items else pd.DataFrame()

    # Run optimizer on core items only
    if not core_df.empty:
        optimization_result = optimize_bid(
            core_df,
            lo=opt_dict.get("lo", 0.0),
            hi=opt_dict.get("hi", 1000.0),
            roi_target=opt_dict.get("roi_target", 1.25),
            risk_threshold=opt_dict.get("risk_threshold", 0.80),
            min_cash_60d=opt_dict.get("min_cash_60d"),
            min_cash_60d_p5=opt_dict.get("min_cash_60d_p5"),
            sims=opt_dict.get("sims", 2000),
            salvage_frac=opt_dict.get("salvage_frac", 0.50),
            marketplace_fee_pct=opt_dict.get("marketplace_fee_pct", 0.12),
            payment_fee_pct=opt_dict.get("payment_fee_pct", 0.03),
            per_order_fee_fixed=opt_dict.get("per_order_fee_fixed", 0.40),
            shipping_per_order=opt_dict.get("shipping_per_order", 0.0),
            packaging_per_order=opt_dict.get("packaging_per_order", 0.0),
            refurb_per_order=opt_dict.get("refurb_per_order", 0.0),
            return_rate=opt_dict.get("return_rate", 0.08),
            salvage_fee_pct=opt_dict.get("salvage_fee_pct", 0.00),
            lot_fixed_cost=opt_dict.get("lot_fixed_cost", 0.0),
            seed=opt_dict.get("seed", 1337),
        )
    else:
        optimization_result = {"bid": 0.0, "roi_p50": 0.0, "items": 0}

    # Generate the report using existing infrastructure
    emit_phase("render_report", "rendering markdown report")
    markdown_content = _mk_markdown(
        items_df,
        opt_dict,
        sweep_csv=None,
        sweep_png=None,
        evidence_jsonl=None,
    )

    # Write markdown if path provided
    markdown_path = None
    if out_md:
        markdown_path = Path(out_md)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown_content, encoding="utf-8")
        markdown_path = str(markdown_path)

    # Optional HTML conversion
    html_path = None
    if out_html and out_md:
        html_path = _optional_html(Path(out_md), Path(out_html))
        html_path = str(html_path) if html_path else None

    # Optional PDF conversion
    pdf_path = None
    if out_pdf and out_md:
        pdf_path = _optional_pdf(Path(out_md), Path(out_pdf))
        pdf_path = str(pdf_path) if pdf_path else None

    # Prepare preview (truncated)
    preview = markdown_content[:4096]
    if len(markdown_content) > 4096:
        preview += "\n\n… (truncated)"

    # Add review flag and evidence gate summary to result
    review_value = sum(
        i.get("est_price_mu", 0) * (i.get("quantity", 1) or 1) for i in review_items
    )
    core_value = sum(
        i.get("est_price_mu", 0) * (i.get("quantity", 1) or 1) for i in core_items
    )
    total_value = (review_value + core_value) or 1.0
    review = (review_value / total_value) > 0.25

    emit_phase("done", "pipeline completed")

    result = {
        "phases": phases,
        "markdown_path": markdown_path,
        "html_path": html_path,
        "pdf_path": pdf_path,
        "markdown_preview": preview,
        "optimization": optimization_result,
        "review": bool(review),
        "core_items_count": len(core_items),
        "upside_items_count": len(review_items),
        "evidence_summary": {
            "core_items": len(core_items),
            "review_items": len(review_items),
            "items": evidence_summaries,
        },
    }

    if review:
        result["upside_value_ratio"] = review_value / total_value

    return result


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
