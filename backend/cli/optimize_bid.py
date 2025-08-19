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
@click.option("--seed", default=1337, show_default=True, type=int)
def main(
    input_csv,
    out_json,
    roi_target,
    risk_threshold,
    min_cash_60d,
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
    seed,
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
        seed=int(seed),
    )
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(_to_json_serializable(result), indent=2), encoding="utf-8"
    )
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
                "meets_constraints": bool(result["meets_constraints"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
