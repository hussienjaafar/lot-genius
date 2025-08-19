import json
from pathlib import Path

import click
import pandas as pd
from lotgenius.roi import feasible


@click.command()
@click.argument("input_csv", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--out-csv", type=click.Path(dir_okay=False, path_type=Path), required=True
)
@click.option("--lo", required=True, type=float, help="Low end of bid sweep")
@click.option("--hi", required=True, type=float, help="High end of bid sweep")
@click.option("--step", required=True, type=float, help="Step size in dollars")
# Constraints
@click.option("--roi-target", default=1.25, show_default=True, type=float)
@click.option("--risk-threshold", default=0.80, show_default=True, type=float)
@click.option("--min-cash-60d", default=None, type=float)
@click.option("--min-cash-60d-p5", default=None, type=float)
# Costs
@click.option("--sims", default=1000, show_default=True, type=int)
@click.option("--salvage-frac", default=0.50, show_default=True, type=float)
@click.option("--marketplace-fee-pct", default=0.12, show_default=True, type=float)
@click.option("--payment-fee-pct", default=0.03, show_default=True, type=float)
@click.option("--per-order-fee-fixed", default=0.40, show_default=True, type=float)
@click.option("--shipping-per-order", default=0.0, show_default=True, type=float)
@click.option("--packaging-per-order", default=0.0, show_default=True, type=float)
@click.option("--refurb-per-order", default=0.0, show_default=True, type=float)
@click.option("--return-rate", default=0.08, show_default=True, type=float)
@click.option("--salvage-fee-pct", default=0.00, show_default=True, type=float)
@click.option("--lot-fixed-cost", default=0.0, show_default=True, type=float)
@click.option("--seed", default=1337, show_default=True, type=int)
def main(
    input_csv,
    out_csv,
    lo,
    hi,
    step,
    roi_target,
    risk_threshold,
    min_cash_60d,
    min_cash_60d_p5,
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
):
    """
    Sweep bids between [lo,hi] and record P(ROI≥target), ROI quantiles, cash stats.
    """
    df = pd.read_csv(input_csv)
    rows = []
    b = float(lo)
    while b <= hi + 1e-9:
        ok, mc = feasible(
            df,
            b,
            roi_target=roi_target,
            risk_threshold=risk_threshold,
            min_cash_60d=min_cash_60d,
            min_cash_60d_p5=min_cash_60d_p5,
            sims=sims,
            salvage_frac=salvage_frac,
            marketplace_fee_pct=marketplace_fee_pct,
            payment_fee_pct=payment_fee_pct,
            per_order_fee_fixed=per_order_fee_fixed,
            shipping_per_order=shipping_per_order,
            packaging_per_order=packaging_per_order,
            refurb_per_order=refurb_per_order,
            return_rate=return_rate,
            salvage_fee_pct=salvage_fee_pct,
            lot_fixed_cost=lot_fixed_cost,
            seed=seed,
        )
        rows.append(
            {
                "bid": float(b),
                "prob_roi_ge_target": float(mc.get("prob_roi_ge_target", 0.0)),
                "roi_p5": float(mc.get("roi_p5", 0.0)),
                "roi_p50": float(mc.get("roi_p50", 0.0)),
                "roi_p95": float(mc.get("roi_p95", 0.0)),
                "expected_cash_60d": float(mc.get("expected_cash_60d", 0.0)),
                "cash_60d_p5": (
                    float(mc.get("cash_60d_p5", 0.0)) if "cash_60d_p5" in mc else None
                ),
                "meets_constraints": bool(mc.get("meets_constraints", False)),
            }
        )
        b += float(step)

    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    click.echo(
        json.dumps(
            {
                "input": str(input_csv),
                "out_csv": str(out_csv),
                "rows": len(rows),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
