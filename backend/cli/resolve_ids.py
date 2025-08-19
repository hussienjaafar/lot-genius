import json
from pathlib import Path

import click
from lotgenius.resolve import enrich_keepa_stats, resolve_ids, write_ledger_jsonl


@click.command()
@click.argument(
    "csv_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--threshold",
    default=88,
    show_default=True,
    help="Fuzzy header match threshold (0-100)",
)
@click.option(
    "--network/--no-network",
    default=True,
    show_default=True,
    help="Use Keepa network lookups",
)
@click.option(
    "--out-enriched",
    type=click.Path(dir_okay=False, path_type=Path),
    default="data/out/resolved_enriched.csv",
    show_default=True,
)
@click.option(
    "--out-ledger",
    type=click.Path(dir_okay=False, path_type=Path),
    default="data/evidence/keepa_ledger.jsonl",
    show_default=True,
)
@click.option(
    "--with-stats/--no-with-stats",
    default=False,
    show_default=True,
    help="Fetch Keepa price/rank stats and attach to output + ledger",
)
@click.option(
    "--gzip-ledger/--no-gzip-ledger",
    default=False,
    show_default=True,
    help="Compress evidence ledger as JSONL.GZ",
)
def main(
    csv_path: Path,
    threshold: int,
    network: bool,
    out_enriched: Path,
    out_ledger: Path,
    with_stats: bool,
    gzip_ledger: bool,
):
    df, ledger = resolve_ids(csv_path, threshold=threshold, use_network=network)

    # Optional stats enrichment
    if with_stats and network:
        df, stats_ledger = enrich_keepa_stats(df, use_network=network)
        ledger.extend(stats_ledger)

    out_enriched.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_enriched, index=False)
    final_ledger_path = write_ledger_jsonl(ledger, out_ledger, gzip_output=gzip_ledger)

    # Compute source counts
    src_counts = {}
    if "resolved_source" in df.columns:
        vc = df["resolved_source"].dropna().value_counts()
        src_counts = {str(k): int(v) for k, v in vc.items()}

    # Check for stats columns presence
    stats_cols = [
        "keepa_price_new_med",
        "keepa_price_used_med",
        "keepa_salesrank_med",
        "keepa_offers_count",
    ]
    stats_columns_present = [col for col in stats_cols if col in df.columns]

    payload = {
        "input": str(csv_path),
        "rows": int(df.shape[0]),
        "resolved": int(df["asin"].notna().sum()),
        "unresolved": int(df["asin"].isna().sum()),
        "enriched_path": str(out_enriched),
        "ledger_path": str(final_ledger_path),
        "source_counts": src_counts,
        "with_stats": bool(with_stats),
        "stats_columns_present": stats_columns_present,
    }
    click.echo(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
