import json
from pathlib import Path

import click
from lotgenius.resolve import resolve_ids, write_ledger_jsonl


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
def main(
    csv_path: Path, threshold: int, network: bool, out_enriched: Path, out_ledger: Path
):
    df, ledger = resolve_ids(csv_path, threshold=threshold, use_network=network)
    out_enriched.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_enriched, index=False)
    write_ledger_jsonl(ledger, out_ledger)

    # Compute source counts
    src_counts = {}
    if "resolved_source" in df.columns:
        vc = df["resolved_source"].dropna().value_counts()
        src_counts = {str(k): int(v) for k, v in vc.items()}

    payload = {
        "input": str(csv_path),
        "rows": int(df.shape[0]),
        "resolved": int(df["asin"].notna().sum()),
        "unresolved": int(df["asin"].isna().sum()),
        "enriched_path": str(out_enriched),
        "ledger_path": str(out_ledger),
        "source_counts": src_counts,
    }
    click.echo(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
