import json
from pathlib import Path

import click
import numpy as np
import pandas as pd
from lotgenius.roi import DEFAULTS, optimize_bid


def _to_json_serializable(obj):
    """Convert numpy arrays to lists for JSON serialization."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_to_json_serializable(item) for item in obj]
    else:
        return obj


@click.command()
@click.argument("input_csv", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--out-json",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Write optimization summary JSON",
)
# Constraints
@click.option(
    "--roi-target", default=DEFAULTS["roi_target"], show_default=True, type=float
)
@click.option(
    "--risk-threshold",
    default=DEFAULTS["risk_threshold"],
    show_default=True,
    type=float,
    help="Require P(ROI >= roi_target) >= risk_threshold",
)
@click.option(
    "--min-cash-60d",
    default=None,
    type=float,
    help="Optional expected cash recovered within 60d threshold",
)
@click.option(
    "--min-cash-60d-p5",
    default=None,
    type=float,
    help="Optional P5 cash recovered within 60d threshold (VaR)",
)
# Search bracket
@click.option("--lo", required=True, type=float, help="Low end of bid search bracket")
@click.option("--hi", required=True, type=float, help="High end of bid search bracket")
@click.option(
    "--tol",
    default=10.0,
    show_default=True,
    type=float,
    help="Bisection tolerance in dollars",
)
@click.option("--max-iter", default=32, show_default=True, type=int)
# Cost knobs
@click.option("--sims", default=2000, show_default=True, type=int)
@click.option("--salvage-frac", default=0.50, show_default=True, type=float)
@click.option("--marketplace-fee-pct", default=0.12, show_default=True, type=float)
@click.option("--payment-fee-pct", default=0.03, show_default=True, type=float)
@click.option("--per-order-fee-fixed", default=0.40, show_default=True, type=float)
@click.option("--shipping-per-order", default=0.0, show_default=True, type=float)
@click.option("--packaging-per-order", default=0.0, show_default=True, type=float)
@click.option("--refurb-per-order", default=0.0, show_default=True, type=float)
@click.option("--return-rate", default=0.08, show_default=True, type=float)
@click.option("--salvage-fee-pct", default=0.00, show_default=True, type=float)
@click.option(
    "--lot-fixed-cost",
    default=0.0,
    show_default=True,
    type=float,
    help="Fixed cost added to bid in ROI denominator",
)
@click.option("--seed", default=1337, show_default=True, type=int)
@click.option(
    "--include-samples/--no-include-samples",
    default=False,
    show_default=True,
    help="Include raw Monte Carlo arrays (revenue, cash_60d) in out_json",
)
@click.option(
    "--evidence-out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write one-line NDJSON evidence for optimizer",
)
def main(
    input_csv,
    out_json,
    roi_target,
    risk_threshold,
    min_cash_60d,
    min_cash_60d_p5,
    lo,
    hi,
    tol,
    max_iter,
    sims,
    salvage_frac,
    marketplace_fee_pct,
    payment_fee_pct,
    per_order_fee_fixed,
    shipping_per_order,
    packaging_per_order,
    refurb_per_order,
    return_rate,
    salvage_fee_pct,
    lot_fixed_cost,
    seed,
    include_samples,
    evidence_out,
):
    """
    Optimize lot bid using Monte Carlo simulation and bisection search.
    """
    df = pd.read_csv(input_csv)
    result = optimize_bid(
        df,
        lo=float(lo),
        hi=float(hi),
        tol=float(tol),
        max_iter=int(max_iter),
        roi_target=float(roi_target),
        risk_threshold=float(risk_threshold),
        min_cash_60d=(None if min_cash_60d is None else float(min_cash_60d)),
        min_cash_60d_p5=(None if min_cash_60d_p5 is None else float(min_cash_60d_p5)),
        sims=int(sims),
        salvage_frac=float(salvage_frac),
        marketplace_fee_pct=float(marketplace_fee_pct),
        payment_fee_pct=float(payment_fee_pct),
        per_order_fee_fixed=float(per_order_fee_fixed),
        shipping_per_order=float(shipping_per_order),
        packaging_per_order=float(packaging_per_order),
        refurb_per_order=float(refurb_per_order),
        return_rate=float(return_rate),
        salvage_fee_pct=float(salvage_fee_pct),
        lot_fixed_cost=float(lot_fixed_cost),
        seed=int(seed),
    )
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    # Write evidence NDJSON if requested
    ev_path = None
    if evidence_out:
        ev_path = Path(evidence_out)
        ev_path.parent.mkdir(parents=True, exist_ok=True)
        ev = {
            "source": "optimize:bid",
            "ok": bool(result.get("meets_constraints", False)),
            "meta": {
                "roi_target": float(roi_target),
                "risk_threshold": float(risk_threshold),
                "min_cash_60d": (None if min_cash_60d is None else float(min_cash_60d)),
                "min_cash_60d_p5": (
                    None if min_cash_60d_p5 is None else float(min_cash_60d_p5)
                ),
                "sims": int(sims),
                "salvage_frac": float(salvage_frac),
                "marketplace_fee_pct": float(marketplace_fee_pct),
                "payment_fee_pct": float(payment_fee_pct),
                "per_order_fee_fixed": float(per_order_fee_fixed),
                "shipping_per_order": float(shipping_per_order),
                "packaging_per_order": float(packaging_per_order),
                "refurb_per_order": float(refurb_per_order),
                "return_rate": float(return_rate),
                "salvage_fee_pct": float(salvage_fee_pct),
                "lot_fixed_cost": float(lot_fixed_cost),
                "lo": float(lo),
                "hi": float(hi),
                "tol": float(tol),
                "max_iter": int(max_iter),
            },
            "result": {
                "bid": float(result.get("bid", 0.0)),
                "roi_p5": float(result.get("roi_p5", 0.0)),
                "roi_p50": float(result.get("roi_p50", 0.0)),
                "roi_p95": float(result.get("roi_p95", 0.0)),
                "prob_roi_ge_target": float(result.get("prob_roi_ge_target", 0.0)),
                "expected_cash_60d": float(result.get("expected_cash_60d", 0.0)),
                "cash_60d_p5": (
                    float(result.get("cash_60d_p5", 0.0))
                    if "cash_60d_p5" in result
                    else None
                ),
                "iterations": int(result.get("iterations", 0)),
                "meets_constraints": bool(result.get("meets_constraints", False)),
                "timestamp": result.get("timestamp"),
            },
        }
        with open(ev_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # Prepare result for JSON output
    out_dict = dict(result)
    if not include_samples:
        for k in ("revenue", "cash_60d"):
            out_dict.pop(k, None)
    json_result = _to_json_serializable(out_dict)

    out_json.write_text(json.dumps(json_result, indent=2), encoding="utf-8")
    click.echo(
        json.dumps(
            {
                "input": str(input_csv),
                "out_json": str(out_json),
                "recommended_bid": float(result["bid"]),
                "roi_p5": float(result["roi_p5"]),
                "roi_p50": float(result["roi_p50"]),
                "roi_p95": float(result["roi_p95"]),
                "prob_roi_ge_target": float(result["prob_roi_ge_target"]),
                "expected_cash_60d": float(result["expected_cash_60d"]),
                "cash_60d_p5": float(result["cash_60d_p5"]),
                "meets_constraints": bool(result["meets_constraints"]),
                "evidence_out": str(ev_path) if ev_path else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
