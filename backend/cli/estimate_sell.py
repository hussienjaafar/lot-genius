import gzip
import json
from pathlib import Path

import click
import pandas as pd
from lotgenius.sell import estimate_sell_p60, load_rank_to_sales


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


@click.command()
@click.argument("input_csv", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--out-csv", type=click.Path(dir_okay=False, path_type=Path), required=True
)
@click.option(
    "--evidence-out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Optional sell_evidence NDJSON path",
)
@click.option("--gzip-evidence/--no-gzip-evidence", default=False, show_default=True)
@click.option("--days", default=60, show_default=True, help="Horizon in days")
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
    help="Price sensitivity β in exp(-β·z)",
)
@click.option("--hazard-cap", default=1.0, show_default=True, help="Daily hazard cap")
@click.option("--cv-fallback", default=0.20, show_default=True)
def main(
    input_csv,
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
):
    """
    Compute per-item P(sold ≤ 60d) "p60" using a conservative, explainable proxy survival model.
    """
    df = pd.read_csv(input_csv)
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
    )

    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_csv, index=False)

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
        "list_price_mode": list_price_mode,
        "list_price_multiplier": float(list_price_multiplier),
        "rank_to_sales_path": str(rank_to_sales),
        "beta_price": float(beta_price),
        "hazard_cap": float(hazard_cap),
    }
    click.echo(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
