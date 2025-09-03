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
from lotgenius.config import settings
from lotgenius.ids import extract_ids
from lotgenius.roi import optimize_bid


def _validate_calibration_path(path_str: str) -> Path:
    """
    Validate calibration log path for security.
    Only allow relative paths under repo or data/api/tmp.
    """
    path = Path(path_str)

    # Reject absolute paths that could be sensitive
    if path.is_absolute():
        # Allow temp directory
        temp_dir = Path(tempfile.gettempdir()).resolve()
        try:
            path.resolve().relative_to(temp_dir)
            return path
        except ValueError:
            pass

        # Reject sensitive absolute paths
        sensitive_prefixes = [
            "C:\\Windows",
            "C:\\Program Files",
            "C:\\ProgramData",
            "/etc",
            "/root",
            "/dev",
            "/proc",
            "/sys",
            "/boot",
        ]
        path_str_lower = str(path).lower()
        for prefix in sensitive_prefixes:
            if path_str_lower.startswith(prefix.lower()):
                raise ValueError(f"Path not allowed: {path_str}")

    # For relative paths, ensure they stay within reasonable bounds
    if ".." in path.parts:
        raise ValueError(f"Path traversal not allowed: {path_str}")

    return path


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
        stress_csv=req.stress_csv,
        stress_json=req.stress_json,
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
        preview += "\n\n(truncated)"

    # Include cache stats if enabled
    cache_stats = None
    try:
        from lotgenius.cache_metrics import get_registry, should_emit_metrics

        if should_emit_metrics():
            cache_stats = get_registry().get_all_stats()
    except ImportError:
        # cache_metrics module not available
        pass

    return ReportResponse(
        status="ok",
        markdown_path=str(markdown_path) if markdown_path else None,
        html_path=str(html_path) if html_path else None,
        pdf_path=str(pdf_path) if pdf_path else None,
        markdown_preview=preview,
        cache_stats=cache_stats,
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

    # Enrich with Keepa data, pricing, and sell probabilities
    from lotgenius.pricing import estimate_prices
    from lotgenius.resolve import enrich_keepa_stats, resolve_ids
    from lotgenius.sell import estimate_sell_p60

    items_df, resolve_ledger = resolve_ids(items_csv, threshold=88, use_network=True)
    items_df, stats_ledger = enrich_keepa_stats(items_df, use_network=True)
    items_df, price_ledger = estimate_prices(items_df)
    items_df, sell_ledger = estimate_sell_p60(items_df, days=60)

    # Extract optimizer parameters with defaults
    lo = opt_dict.get("lo", 0.0)
    hi = opt_dict.get("hi", 1000.0)

    # Apply evidence gate before Monte Carlo simulation
    from lotgenius.evidence import write_evidence
    from lotgenius.gating import passes_evidence_gate

    core_items = []
    upside_items = []

    for idx, row in items_df.iterrows():
        item = dict(row)
        # Use ID helper for consistent canonical handling
        ids = extract_ids(item)
        has_high_trust_id = bool(
            ids["asin"] or ids["upc"] or ids["ean"] or ids["upc_ean_asin"]
        )
        sold_comps_180d = int(
            (item.get("keepa_new_count") or 0) + (item.get("keepa_used_count") or 0)
        )
        has_secondary_signal = bool(
            (item.get("keepa_offers_count") or 0) > 0  # offer depth
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

    # Default min_cash_60d to settings.CASHFLOOR when not provided
    min_cash = opt_dict.get("min_cash_60d")
    if min_cash is None:
        min_cash = settings.CASHFLOOR

    # Extract throughput parameters
    mins_per_unit = opt_dict.get("mins_per_unit")
    capacity_mins_per_day = opt_dict.get("capacity_mins_per_day")

    # Runtime settings override for brand gating and hazmat policy
    original_gated_brands = settings.GATED_BRANDS_CSV
    original_hazmat_policy = settings.HAZMAT_POLICY

    try:
        gated_brands_csv = opt_dict.get("gated_brands_csv")
        hazmat_policy = opt_dict.get("hazmat_policy")

        if gated_brands_csv is not None:
            settings.GATED_BRANDS_CSV = gated_brands_csv
        if hazmat_policy is not None:
            settings.HAZMAT_POLICY = hazmat_policy.lower()

        # Run the optimizer (using the existing optimize_bid function) on core items only
        result = optimize_bid(
            core_df,
            lo=lo,
            hi=hi,
            roi_target=opt_dict.get("roi_target", 1.25),
            risk_threshold=opt_dict.get("risk_threshold", 0.80),
            min_cash_60d=min_cash,
            min_cash_60d_p5=opt_dict.get("min_cash_60d_p5"),
            throughput_mins_per_unit=mins_per_unit,
            capacity_mins_per_day=capacity_mins_per_day,
            sims=opt_dict.get("sims", 2000),
            salvage_frac=opt_dict.get(
                "salvage_frac", settings.CLEARANCE_VALUE_AT_HORIZON
            ),
            marketplace_fee_pct=opt_dict.get("marketplace_fee_pct", 0.12),
            payment_fee_pct=opt_dict.get("payment_fee_pct", 0.03),
            per_order_fee_fixed=opt_dict.get("per_order_fee_fixed", 0.40),
            shipping_per_order=opt_dict.get("shipping_per_order", 0.0),
            packaging_per_order=opt_dict.get("packaging_per_order", 0.0),
            refurb_per_order=opt_dict.get("refurb_per_order", 0.0),
            return_rate=opt_dict.get("return_rate", 0.08),
            salvage_fee_pct=opt_dict.get("salvage_fee_pct", 0.00),
            lot_fixed_cost=opt_dict.get("lot_fixed_cost", 0.0),
            # Manifest risk knobs
            defect_rate=opt_dict.get("defect_rate", 0.0),
            missing_rate=opt_dict.get("missing_rate", 0.0),
            grade_mismatch_rate=opt_dict.get("grade_mismatch_rate", 0.0),
            defect_recovery_frac=opt_dict.get("defect_recovery_frac", 0.5),
            missing_recovery_frac=opt_dict.get("missing_recovery_frac", 0.0),
            mismatch_discount_frac=opt_dict.get("mismatch_discount_frac", 0.2),
            # Ops + storage costs
            ops_cost_per_min=opt_dict.get("ops_cost_per_min", 0.0),
            storage_cost_per_unit_per_day=opt_dict.get(
                "storage_cost_per_unit_per_day", 0.0
            ),
            seed=opt_dict.get("seed", 1337),
        )
    finally:
        # Restore original settings
        settings.GATED_BRANDS_CSV = original_gated_brands
        settings.HAZMAT_POLICY = original_hazmat_policy

    # Add review flag if upside share is material (>25% of lot value)
    def _fnum(x) -> float:
        try:
            return float(x)
        except Exception:
            return 0.0

    def _item_value(it: dict) -> float:
        mu = _fnum(it.get("est_price_mu"))
        q = _fnum(it.get("quantity", 1))
        if q <= 0:
            q = 1.0
        return mu * q

    upside_value = sum(_item_value(i) for i in upside_items)
    core_value = sum(_item_value(i) for i in core_items)
    total_value = (upside_value + core_value) or 1.0
    review = (upside_value / total_value) > 0.25

    result["review"] = bool(review)
    result["core_items_count"] = len(core_items)
    result["upside_items_count"] = len(upside_items)
    if review:
        result["upside_value_ratio"] = upside_value / total_value

    # Optional calibration logging
    calibration_log_path = None
    calibration_log_written = opt_dict.get("calibration_log_path")
    if calibration_log_written and not core_df.empty:
        try:
            from lotgenius.calibration import log_predictions

            # Validate and prepare path
            validated_path = _validate_calibration_path(calibration_log_written)

            # Prepare context for logging
            context = {
                "roi_target": opt_dict.get("roi_target", 1.25),
                "risk_threshold": opt_dict.get("risk_threshold", 0.80),
                "horizon_days": settings.SELLTHROUGH_HORIZON_DAYS,
                "lot_id": opt_dict.get("lot_id"),
                "opt_source": "run_optimize",
                "opt_params": {
                    "roi_target": opt_dict.get("roi_target", 1.25),
                    "risk_threshold": opt_dict.get("risk_threshold", 0.80),
                    "sims": opt_dict.get("sims"),
                },
            }

            # Log predictions for core items used in optimization
            log_predictions(core_df, context, str(validated_path))
            calibration_log_path = str(validated_path)
        except Exception:
            # Calibration logging is optional, don't fail optimization
            pass

    # Create compact result (remove raw arrays to keep response size manageable)
    compact_result = {
        k: v
        for k, v in result.items()
        if k not in ["roi", "revenue", "cash_60d"]  # exclude raw simulation arrays
    }

    # Add calibration log path to result if created
    if calibration_log_path:
        compact_result["calibration_log_path"] = calibration_log_path

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
    stress_csv: Optional[str] = None,
    stress_json: Optional[str] = None,
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

    # Actually perform Keepa enrichment (was missing!)
    from lotgenius.resolve import enrich_keepa_stats, resolve_ids

    # Decide whether to hit network for Keepa based on configuration
    try:
        from lotgenius.config import settings as _settings

        use_keepa_network = bool(_settings.KEEPA_API_KEY)
    except Exception:
        use_keepa_network = False

    # Step 1: Resolve UPC/EAN/ASIN codes to ASINs via Keepa (or skip network)
    emit_phase("resolve_ids", "resolving product IDs")
    items_df, resolve_ledger = resolve_ids(
        items_csv, threshold=88, use_network=use_keepa_network
    )

    # Step 2: Fetch Keepa stats (pricing, offers, sales rank) for resolved ASINs
    emit_phase("enrich_keepa", "enriching with pricing data")
    items_df, stats_ledger = enrich_keepa_stats(items_df, use_network=use_keepa_network)

    # Step 3: Calculate price distributions using the pricing model
    emit_phase("price", "calculating price distributions")
    from lotgenius.pricing import estimate_prices

    items_df, price_ledger = estimate_prices(items_df)

    # Step 4: Calculate sell probabilities (needed for ROI optimization)
    emit_phase("sell", "modeling sell probabilities")
    from lotgenius.sell import estimate_sell_p60

    items_df, sell_ledger = estimate_sell_p60(items_df, days=60)

    # Apply evidence gate filtering and run optimization
    from lotgenius.evidence import compute_evidence, evidence_to_dict, write_evidence

    evidence_summaries: List[Dict[str, Any]] = []
    core_items: List[Dict[str, Any]] = []
    review_items: List[Dict[str, Any]] = []

    def _has_high_trust_id(it: Dict[str, Any]) -> bool:
        ids = extract_ids(it)
        return bool(ids["asin"] or ids["upc"] or ids["ean"] or ids["upc_ean_asin"])

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
                or (item.get("keepa_offers_count") or 0) > 0
            ),
        }

        # Safely extract item key, handling pandas Series
        def safe_get(key):
            val = item.get(key)
            if hasattr(val, "iloc") and len(val) > 0:  # pandas Series
                return val.iloc[0] if pd.notna(val.iloc[0]) else None
            return val if pd.notna(val) else None

        item_key = (
            safe_get("sku_local")
            or safe_get("title")
            or safe_get("asin")
            or f"item_{idx}"
        )

        ev = compute_evidence(
            item_key=str(item_key),
            has_high_trust_id=_has_high_trust_id(item),
            sold_comps=comps,
            secondary_signals=sec,
            sources={"keepa": bool(keepa_blob), "comps": len(comps)},
        )
        # Attach product_confidence into evidence meta using available signals
        try:
            from lotgenius.scoring import derive_signals_from_item, product_confidence

            sig = derive_signals_from_item(
                item=item,
                keepa_blob=keepa_blob if isinstance(keepa_blob, dict) else {},
                sold_comps=comps if isinstance(comps, list) else [],
                high_trust_id=ev.has_high_trust_id,
            )
            pc = product_confidence(sig)
            if ev.meta is None:
                ev.meta = {}
            ev.meta["product_confidence"] = float(pc)
        except Exception:
            # Non-fatal; keep evidence without product_confidence
            pass

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
        # Emit evidence summary between sell and optimize for frontend sequencing
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

    # Default min_cash_60d to settings.CASHFLOOR when not provided
    min_cash = opt_dict.get("min_cash_60d")
    if min_cash is None:
        min_cash = settings.CASHFLOOR

    # Extract throughput parameters
    mins_per_unit = opt_dict.get("mins_per_unit")
    capacity_mins_per_day = opt_dict.get("capacity_mins_per_day")

    # Runtime settings override for brand gating and hazmat policy
    original_gated_brands = settings.GATED_BRANDS_CSV
    original_hazmat_policy = settings.HAZMAT_POLICY

    try:
        gated_brands_csv = opt_dict.get("gated_brands_csv")
        hazmat_policy = opt_dict.get("hazmat_policy")

        if gated_brands_csv is not None:
            settings.GATED_BRANDS_CSV = gated_brands_csv
        if hazmat_policy is not None:
            settings.HAZMAT_POLICY = hazmat_policy.lower()

        # Emit optimize phase after evidence, then run optimizer on core items only
        emit_phase("optimize", "running ROI optimizer")
        if not core_df.empty:
            optimization_result = optimize_bid(
                core_df,
                lo=opt_dict.get("lo", 0.0),
                hi=opt_dict.get("hi", 1000.0),
                roi_target=opt_dict.get("roi_target", 1.25),
                risk_threshold=opt_dict.get("risk_threshold", 0.80),
                min_cash_60d=min_cash,
                min_cash_60d_p5=opt_dict.get("min_cash_60d_p5"),
                throughput_mins_per_unit=mins_per_unit,
                capacity_mins_per_day=capacity_mins_per_day,
                sims=opt_dict.get("sims", 2000),
                salvage_frac=opt_dict.get(
                    "salvage_frac", settings.CLEARANCE_VALUE_AT_HORIZON
                ),
                marketplace_fee_pct=opt_dict.get("marketplace_fee_pct", 0.12),
                payment_fee_pct=opt_dict.get("payment_fee_pct", 0.03),
                per_order_fee_fixed=opt_dict.get("per_order_fee_fixed", 0.40),
                shipping_per_order=opt_dict.get("shipping_per_order", 0.0),
                packaging_per_order=opt_dict.get("packaging_per_order", 0.0),
                refurb_per_order=opt_dict.get("refurb_per_order", 0.0),
                return_rate=opt_dict.get("return_rate", 0.08),
                salvage_fee_pct=opt_dict.get("salvage_fee_pct", 0.00),
                lot_fixed_cost=opt_dict.get("lot_fixed_cost", 0.0),
                # Manifest risk knobs
                defect_rate=opt_dict.get("defect_rate", 0.0),
                missing_rate=opt_dict.get("missing_rate", 0.0),
                grade_mismatch_rate=opt_dict.get("grade_mismatch_rate", 0.0),
                defect_recovery_frac=opt_dict.get("defect_recovery_frac", 0.5),
                missing_recovery_frac=opt_dict.get("missing_recovery_frac", 0.0),
                mismatch_discount_frac=opt_dict.get("mismatch_discount_frac", 0.2),
                # Ops + storage costs
                ops_cost_per_min=opt_dict.get("ops_cost_per_min", 0.0),
                storage_cost_per_unit_per_day=opt_dict.get(
                    "storage_cost_per_unit_per_day", 0.0
                ),
                seed=opt_dict.get("seed", 1337),
            )
        else:
            optimization_result = {"bid": 0.0, "roi_p50": 0.0, "items": 0}

        # Optional calibration logging in pipeline
        calibration_log_path = None
        calibration_log_written = opt_dict.get("calibration_log_path")
        if (
            calibration_log_written
            and not core_df.empty
            and (optimization_result.get("items") or 0) > 0
        ):
            try:
                from lotgenius.calibration import log_predictions

                # Validate and prepare path
                validated_path = _validate_calibration_path(calibration_log_written)

                # Prepare context for logging
                context = {
                    "roi_target": opt_dict.get("roi_target", 1.25),
                    "risk_threshold": opt_dict.get("risk_threshold", 0.80),
                    "horizon_days": settings.SELLTHROUGH_HORIZON_DAYS,
                    "lot_id": opt_dict.get("lot_id"),
                    "opt_source": "run_pipeline",
                    "opt_params": {
                        "roi_target": opt_dict.get("roi_target", 1.25),
                        "risk_threshold": opt_dict.get("risk_threshold", 0.80),
                        "sims": opt_dict.get("sims"),
                    },
                }

                # Log predictions for core items used in optimization
                count = log_predictions(core_df, context, str(validated_path))
                calibration_log_path = str(validated_path)
            except Exception:
                # Calibration logging is optional, don't fail pipeline
                pass

    finally:
        # Restore original settings
        settings.GATED_BRANDS_CSV = original_gated_brands
        settings.HAZMAT_POLICY = original_hazmat_policy

    # Generate the report using existing infrastructure
    emit_phase("render_report", "rendering markdown report")
    markdown_content = _mk_markdown(
        items_df,
        opt_dict,
        sweep_csv=None,
        sweep_png=None,
        evidence_jsonl=None,
        stress_csv=stress_csv,
        stress_json=stress_json,
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
        preview += "\n\n(truncated)"

    # Add review flag and evidence gate summary to result
    review_value = 0.0
    for i in review_items:
        mu = i.get("est_price_mu") or 0.0
        try:
            mu = float(mu)
        except Exception:
            mu = 0.0
        q = i.get("quantity", 1) or 1
        try:
            q = float(q)
        except Exception:
            q = 1.0
        if q <= 0:
            q = 1.0
        review_value += mu * q

    core_value = 0.0
    for i in core_items:
        mu = i.get("est_price_mu") or 0.0
        try:
            mu = float(mu)
        except Exception:
            mu = 0.0
        q = i.get("quantity", 1) or 1
        try:
            q = float(q)
        except Exception:
            q = 1.0
        if q <= 0:
            q = 1.0
        core_value += mu * q
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

    # Add calibration log path to result if created
    if "calibration_log_path" in locals() and calibration_log_path:
        result["calibration_log_path"] = calibration_log_path

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
            stress_csv=req.stress_csv,
            stress_json=req.stress_json,
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


def process_feed_to_pipeline_csv(
    feed_csv_path: str, output_csv_path: str
) -> Dict[str, Any]:
    """
    Helper to convert feed CSV to pipeline-ready CSV format.

    Args:
        feed_csv_path: Path to input feed CSV file
        output_csv_path: Path to write normalized pipeline CSV

    Returns:
        Dictionary with processing summary

    Raises:
        Various exceptions from feeds module for validation errors
    """
    # Import feeds functions (avoiding circular imports)
    from ..feeds import feed_to_pipeline_items, load_feed_csv

    # Load and normalize the feed
    feed_records = load_feed_csv(feed_csv_path)

    # Convert to pipeline-ready format
    pipeline_items = feed_to_pipeline_items(feed_records)

    # Write to CSV format compatible with existing pipeline
    df = pd.DataFrame(pipeline_items)

    # Ensure output directory exists
    output_path = Path(output_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV with consistent formatting
    df.to_csv(output_path, index=False)

    # Generate summary stats
    summary = {
        "input_records": len(feed_records),
        "output_items": len(pipeline_items),
        "unique_brands": (
            len(df["brand"].dropna().unique()) if "brand" in df.columns else 0
        ),
        "unique_conditions": (
            len(df["condition"].dropna().unique()) if "condition" in df.columns else 0
        ),
        "has_ids": {
            "asin": (
                df.get("asin", pd.Series()).notna()
                & (df.get("asin", pd.Series()) != "")
            ).sum(),
            "upc": (
                df.get("upc", pd.Series()).notna() & (df.get("upc", pd.Series()) != "")
            ).sum(),
            "ean": (
                df.get("ean", pd.Series()).notna() & (df.get("ean", pd.Series()) != "")
            ).sum(),
            "upc_ean_asin": (
                df.get("upc_ean_asin", pd.Series()).notna()
                & (df.get("upc_ean_asin", pd.Series()) != "")
            ).sum(),
        },
        "output_path": str(output_path),
    }

    return summary
