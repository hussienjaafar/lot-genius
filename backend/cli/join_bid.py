import json
from pathlib import Path

import click
import pandas as pd


@click.command()
@click.option(
    "--items-csv",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Per-unit CSV (e.g., estimated_sell.csv)",
)
@click.option(
    "--opt-json",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="optimizer JSON",
)
@click.option(
    "--out-csv", type=click.Path(dir_okay=False, path_type=Path), required=True
)
@click.option(
    "--mode",
    type=click.Choice(["one-row", "broadcast"]),
    default="one-row",
    show_default=True,
)
def main(items_csv, opt_json, out_csv, mode):
    """
    Join recommended bid: produce a single-row lot summary or broadcast to items.
    """
    items = pd.read_csv(items_csv, encoding="utf-8")
    opt = json.loads(Path(opt_json).read_text(encoding="utf-8"))

    # Flatten relevant fields
    summary = {
        "recommended_bid": float(opt.get("bid", 0.0)),
        "roi_p5": float(opt.get("roi_p5", 0.0)),
        "roi_p50": float(opt.get("roi_p50", 0.0)),
        "roi_p95": float(opt.get("roi_p95", 0.0)),
        "prob_roi_ge_target": float(opt.get("prob_roi_ge_target", 0.0)),
        "expected_cash_60d": float(opt.get("expected_cash_60d", 0.0)),
        "cash_60d_p5": (
            float(opt.get("cash_60d_p5", 0.0)) if "cash_60d_p5" in opt else None
        ),
        "meets_constraints": bool(opt.get("meets_constraints", False)),
    }
    # Add roi_target and risk_threshold if present in optimizer JSON
    summary.update(
        {
            "roi_target": float(opt.get("roi_target")) if "roi_target" in opt else None,
            "risk_threshold": (
                float(opt.get("risk_threshold")) if "risk_threshold" in opt else None
            ),
        }
    )
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "broadcast":
        # attach the summary columns to every item row
        for k, v in summary.items():
            items[k] = v
        items.to_csv(out_path, index=False, encoding="utf-8")
    else:
        # single-row lot summary with a few aggregations
        row = {**summary}
        if "lot_id" in items.columns:
            lots = items["lot_id"].nunique()
            row["lot_id_count"] = int(lots)
        row["items"] = int(items.shape[0])
        row["est_total_mu"] = float(
            items.get("est_price_mu", pd.Series([])).sum(skipna=True)
        )
        row["est_total_p50"] = (
            float(
                items.get(
                    "est_price_p50", items.get("est_price_median", pd.Series([]))
                ).sum(skipna=True)
            )
            if ("est_price_p50" in items.columns or "est_price_median" in items.columns)
            else None
        )
        pd.DataFrame([row]).to_csv(out_path, index=False, encoding="utf-8")

    click.echo(
        json.dumps(
            {
                "items_csv": str(items_csv),
                "opt_json": str(opt_json),
                "out_csv": str(out_path),
                "mode": mode,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
