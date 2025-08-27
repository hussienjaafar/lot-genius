import gzip
import json
from pathlib import Path

import click
import pandas as pd
from lotgenius.config import settings
from lotgenius.ladder import compute_ladder_sellthrough, pricing_ladder
from lotgenius.sell import estimate_sell_p60, load_rank_to_sales
from lotgenius.survivorship import estimate_sell_p60_survival


def _write_jsonl(records, out_path: Path, gzip_output=False):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if gzip_output and not str(out_path).endswith(".gz"):
        out_path = out_path.with_suffix(out_path.suffix + ".gz")
    opener = (
        (lambda p: gzip.open(p, "wt", encoding="utf-8"))
        if gzip_output
        else (lambda p: open(p, "w", encoding="utf-8"))
    )
    with opener(out_path) as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return out_path


def _apply_pricing_ladder(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Apply pricing ladder to recalculate sell-through probabilities."""
    df = df.copy()

    # Add ladder metadata columns if they don't exist
    for col in ["sell_p60_ladder", "sell_ladder_segments"]:
        if col not in df.columns:
            df[col] = None

    for idx, row in df.iterrows():
        # Skip if we don't have the basic requirements
        if pd.isna(row.get("sell_p60")) or pd.isna(row.get("sell_hazard_daily")):
            continue

        # Use estimated price as base price for ladder
        base_price = None
        for price_col in ["est_price_p50", "est_price_median", "est_price_mu"]:
            if price_col in row and pd.notna(row[price_col]):
                base_price = float(row[price_col])
                break

        if base_price is None or base_price <= 0:
            continue

        # Generate pricing ladder segments
        ladder_segments = pricing_ladder(base_price, horizon_days=days)

        # Calculate ladder-based sell-through
        base_hazard = float(row["sell_hazard_daily"])
        ladder_p60 = compute_ladder_sellthrough(ladder_segments, base_hazard)

        # Update DataFrame with ladder results
        df.at[idx, "sell_p60_ladder"] = float(ladder_p60)
        df.at[idx, "sell_ladder_segments"] = json.dumps(ladder_segments)

        # Replace original sell_p60 with ladder version
        df.at[idx, "sell_p60"] = float(ladder_p60)

    return df


@click.command()
@click.argument("input_csv", type=click.Path(dir_okay=False, path_type=Path))
# Optional positional out path for compatibility with tests and simple usage
@click.argument(
    "out_csv_arg", required=False, type=click.Path(dir_okay=False, path_type=Path)
)
@click.option(
    "--out-csv",
    type=click.Path(dir_okay=False, path_type=Path),
    required=False,
)
@click.option(
    "--evidence-out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Optional sell_evidence NDJSON path",
)
@click.option("--gzip-evidence/--no-gzip-evidence", default=False, show_default=True)
@click.option(
    "--days",
    default=settings.SELLTHROUGH_HORIZON_DAYS,
    show_default=True,
    help="Horizon in days",
)
@click.option(
    "--list-price-mode",
    type=click.Choice(["p50", "mu", "custom"]),
    default="p50",
    show_default=True,
)
@click.option("--list-price-multiplier", default=1.0, show_default=True)
@click.option(
    "--custom-list-price-col",
    default=None,
    help="Column name if using list-price-mode=custom",
)
@click.option(
    "--rank-to-sales",
    type=click.Path(dir_okay=False, path_type=Path),
    default="backend/lotgenius/data/rank_to_sales.example.json",
    show_default=True,
)
@click.option(
    "--beta-price",
    default=0.8,
    show_default=True,
    help="Price sensitivity beta in exp(-beta*z)",
)
@click.option("--hazard-cap", default=1.0, show_default=True, help="Daily hazard cap")
@click.option("--cv-fallback", default=0.20, show_default=True)
@click.option(
    "--baseline-daily-sales",
    default=0.0,
    show_default=True,
    help="Fallback daily market sales when rank is missing",
)
@click.option(
    "--survival-model",
    type=click.Choice(["proxy", "loglogistic"]),
    default=settings.SURVIVAL_MODEL,
    show_default=True,
    help="Survival model type for sell-through estimation",
)
@click.option(
    "--survival-alpha",
    default=settings.SURVIVAL_ALPHA,
    show_default=True,
    help="Log-logistic scale parameter (time to 50% survival)",
)
@click.option(
    "--survival-beta",
    default=settings.SURVIVAL_BETA,
    show_default=True,
    help="Log-logistic shape parameter",
)
@click.option(
    "--use-pricing-ladder/--no-pricing-ladder",
    default=False,
    show_default=True,
    help="Use pricing ladder for piecewise sell-through calculation",
)
def main(
    input_csv,
    out_csv_arg,
    out_csv,
    evidence_out,
    gzip_evidence,
    days,
    list_price_mode,
    list_price_multiplier,
    custom_list_price_col,
    rank_to_sales,
    beta_price,
    hazard_cap,
    cv_fallback,
    baseline_daily_sales,
    survival_model,
    survival_alpha,
    survival_beta,
    use_pricing_ladder,
):
    """
    Compute per-item P(sold <= 60d) "p60" using proxy or log-logistic survival model.
    """
    df = pd.read_csv(input_csv, encoding="utf-8")

    # Prefer positional out path if provided; else require option
    if out_csv is None and out_csv_arg is not None:
        out_csv = out_csv_arg
    if out_csv is None:
        # Click will treat this as usage error similar to missing required option
        raise click.UsageError(
            "Output CSV path must be provided as positional argument or --out-csv option"
        )

    # Choose survival model based on CLI option
    if survival_model == "loglogistic":
        out_df, events = estimate_sell_p60_survival(
            df,
            alpha=float(survival_alpha),
            beta=float(survival_beta),
            days=days,
            cv_fallback=float(cv_fallback),
        )
    else:  # Default to proxy model
        mapping = load_rank_to_sales(str(rank_to_sales) if rank_to_sales else None)
        out_df, events = estimate_sell_p60(
            df,
            days=days,
            list_price_mode=list_price_mode,
            list_price_multiplier=float(list_price_multiplier),
            custom_list_price_col=custom_list_price_col,
            rank_to_sales=mapping,
            beta_price=float(beta_price),
            hazard_cap=float(hazard_cap),
            cv_fallback=float(cv_fallback),
            baseline_daily_sales=float(baseline_daily_sales),
        )

    # Apply pricing ladder if enabled
    if use_pricing_ladder:
        out_df = _apply_pricing_ladder(out_df, days)

    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_csv, index=False, encoding="utf-8")

    ev_path = None
    if evidence_out:
        ev_path = _write_jsonl(events, evidence_out, gzip_output=gzip_evidence)

    payload = {
        "input": str(input_csv),
        "rows": int(out_df.shape[0]),
        "estimated": int(pd.notna(out_df["sell_p60"]).sum()),
        "out_csv": str(out_csv),
        "sell_evidence_path": (str(ev_path) if ev_path else None),
        "days": days,
        "survival_model": survival_model,
        "survival_alpha": float(survival_alpha),
        "survival_beta": float(survival_beta),
        "use_pricing_ladder": use_pricing_ladder,
    }

    # Add proxy-model specific parameters if used
    if survival_model != "loglogistic":
        payload.update(
            {
                "list_price_mode": list_price_mode,
                "list_price_multiplier": float(list_price_multiplier),
                "rank_to_sales_path": str(rank_to_sales),
                "beta_price": float(beta_price),
                "hazard_cap": float(hazard_cap),
                "baseline_daily_sales": float(baseline_daily_sales),
            }
        )
    click.echo(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
