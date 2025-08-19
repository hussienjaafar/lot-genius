#!/usr/bin/env python3
"""
CLI tool to resolve Item IDs (UPC/EAN/ASIN) to ASINs using Keepa.

Reads a CSV file (output from parse_clean), attempts ID resolution,
and writes:
1. Enriched CSV with resolved_asin column
2. JSONL evidence ledger
"""

import json
from pathlib import Path
from typing import Optional

import click
from lotgenius.keepa_client import KeepaClient
from lotgenius.parse import parse_and_clean
from lotgenius.resolve import resolve_dataframe


@click.command()
@click.argument("input_csv", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-csv",
    type=click.Path(path_type=Path),
    help="Output CSV path (default: input_csv with _resolved suffix)",
)
@click.option(
    "--output-ledger",
    type=click.Path(path_type=Path),
    help="Output JSONL ledger path (default: input_csv with _ledger.jsonl suffix)",
)
@click.option(
    "--fuzzy-threshold",
    type=int,
    default=88,
    help="Fuzzy matching threshold for header mapping (default: 88)",
)
@click.option(
    "--explode/--no-explode",
    default=True,
    help="Explode quantity to individual units (default: True)",
)
@click.option(
    "--keepa-key", type=str, help="Keepa API key (overrides environment/config)"
)
def resolve_ids(
    input_csv: Path,
    output_csv: Optional[Path],
    output_ledger: Optional[Path],
    fuzzy_threshold: int,
    explode: bool,
    keepa_key: Optional[str],
):
    """
    Resolve product IDs to ASINs using Keepa API.

    INPUT_CSV should be a manifest CSV file. The tool will:
    1. Parse and clean the CSV using lotgenius.parse
    2. Attempt to resolve UPC/EAN/ASIN codes to canonical ASINs
    3. Output enriched CSV with resolved_asin column
    4. Output JSONL evidence ledger for audit trail

    Example:
        python -m cli.resolve_ids data/manifest.csv
        python -m cli.resolve_ids data/manifest.csv --output-csv results.csv --keepa-key your_key
    """

    # Set default output paths
    if output_csv is None:
        output_csv = input_csv.parent / f"{input_csv.stem}_resolved.csv"

    if output_ledger is None:
        output_ledger = input_csv.parent / f"{input_csv.stem}_ledger.jsonl"

    click.echo(f"Processing: {input_csv}")
    click.echo(f"Output CSV: {output_csv}")
    click.echo(f"Output ledger: {output_ledger}")

    # Step 1: Parse and clean the input CSV
    click.echo("Parsing and cleaning input CSV...")
    try:
        parse_result = parse_and_clean(
            input_csv, fuzzy_threshold=fuzzy_threshold, explode=explode
        )

        # Use exploded DataFrame if available, otherwise cleaned
        df_to_resolve = (
            parse_result.df_exploded
            if explode and parse_result.df_exploded is not None
            else parse_result.df_clean
        )

        click.echo(f"Parsed {len(df_to_resolve)} rows for resolution")

        if parse_result.unmapped_headers:
            click.echo(f"Warning: Unmapped headers: {parse_result.unmapped_headers}")

    except Exception as e:
        click.echo(f"Error parsing CSV: {e}", err=True)
        raise click.Abort()

    # Step 2: Initialize Keepa client
    try:
        if keepa_key:
            from lotgenius.keepa_client import KeepaConfig

            config = KeepaConfig(api_key=keepa_key)
            keepa_client = KeepaClient(config)
        else:
            keepa_client = KeepaClient()

        # Quick validation of API key
        if not keepa_client.cfg.api_key:
            click.echo(
                "Warning: No Keepa API key configured. Resolution will fail.", err=True
            )
            click.echo(
                "Set KEEPA_API_KEY environment variable or use --keepa-key option."
            )

    except Exception as e:
        click.echo(f"Error initializing Keepa client: {e}", err=True)
        raise click.Abort()

    # Step 3: Resolve IDs to ASINs
    click.echo("Resolving IDs to ASINs...")
    try:
        enriched_df, evidence_ledger = resolve_dataframe(df_to_resolve, keepa_client)

        # Count successful resolutions
        successful_resolutions = enriched_df["resolved_asin"].notna().sum()
        total_rows = len(enriched_df)
        success_rate = (
            successful_resolutions / total_rows * 100 if total_rows > 0 else 0
        )

        click.echo(
            f"Resolved {successful_resolutions}/{total_rows} items ({success_rate:.1f}%)"
        )

    except Exception as e:
        click.echo(f"Error during resolution: {e}", err=True)
        raise click.Abort()

    # Step 4: Write outputs
    try:
        # Ensure output directories exist
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        output_ledger.parent.mkdir(parents=True, exist_ok=True)

        # Write enriched CSV
        enriched_df.to_csv(output_csv, index=False)
        click.echo(f"Wrote enriched CSV: {output_csv}")

        # Write JSONL evidence ledger
        with open(output_ledger, "w") as f:
            for evidence_entry in evidence_ledger:
                f.write(json.dumps(evidence_entry) + "\n")

        click.echo(
            f"Wrote evidence ledger: {output_ledger} ({len(evidence_ledger)} entries)"
        )

    except Exception as e:
        click.echo(f"Error writing outputs: {e}", err=True)
        raise click.Abort()

    click.echo("Resolution complete!")


if __name__ == "__main__":
    resolve_ids()
