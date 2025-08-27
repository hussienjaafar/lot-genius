#!/usr/bin/env python3
"""CLI tool for importing and normalizing feed/watchlist CSVs."""

import json
import sys
from pathlib import Path
from typing import Optional

import click

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lotgenius.feeds import FeedValidationError, feed_to_pipeline_items, load_feed_csv


@click.command()
@click.argument("input_csv", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-csv",
    type=click.Path(path_type=Path),
    help="Output CSV path (default: data/feeds/out/normalized_<input_name>.csv)",
)
@click.option(
    "--output-json",
    type=click.Path(path_type=Path),
    help="Output JSON path (default: data/feeds/out/normalized_<input_name>.json)",
)
@click.option("--quiet", "-q", is_flag=True, help="Suppress progress output")
@click.option(
    "--validate-only",
    is_flag=True,
    help="Only validate the feed, do not generate output files",
)
def main(
    input_csv: Path,
    output_csv: Optional[Path],
    output_json: Optional[Path],
    quiet: bool,
    validate_only: bool,
):
    """
    Import and normalize a feed/watchlist CSV for pipeline processing.

    INPUT_CSV: Path to the feed CSV file to import

    The tool will:
    1. Validate the feed CSV structure and required fields
    2. Normalize conditions, brands, and other fields
    3. Apply ID extraction and validation
    4. Generate pipeline-ready CSV and/or JSON output

    Example:
        python -m cli.import_feed my_watchlist.csv
        python -m cli.import_feed feeds/items.csv --output-csv output.csv --quiet
    """
    try:
        if not quiet:
            click.echo(f"Loading feed CSV: {input_csv}")

        # Load and validate the feed
        feed_records = load_feed_csv(str(input_csv))

        if not quiet:
            click.echo(f"[+] Successfully loaded {len(feed_records)} records")

        # Convert to pipeline format
        pipeline_items = feed_to_pipeline_items(feed_records)

        if not quiet:
            click.echo(f"[+] Converted to {len(pipeline_items)} pipeline-ready items")

        if validate_only:
            if not quiet:
                click.echo("[+] Validation completed successfully")
            return

        # Determine output paths
        input_stem = input_csv.stem

        if not output_csv:
            output_csv = Path("data/feeds/out") / f"normalized_{input_stem}.csv"

        if not output_json:
            output_json = Path("data/feeds/out") / f"normalized_{input_stem}.json"

        # Ensure output directories exist
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        output_json.parent.mkdir(parents=True, exist_ok=True)

        # Write CSV output
        import pandas as pd

        df = pd.DataFrame(pipeline_items)
        df.to_csv(output_csv, index=False)

        if not quiet:
            click.echo(f"[+] Wrote normalized CSV: {output_csv}")

        # Write JSON output
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(pipeline_items, f, indent=2, default=str)

        if not quiet:
            click.echo(f"[+] Wrote normalized JSON: {output_json}")

        # Print summary statistics
        if not quiet:
            print_summary(pipeline_items, df)

    except FeedValidationError as e:
        click.echo(f"[X] Feed validation error: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(f"[X] File not found: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"[X] Unexpected error: {e}", err=True)
        sys.exit(1)


def print_summary(pipeline_items, df):
    """Print summary statistics about the processed feed."""
    click.echo("\n[*] Feed Summary:")
    click.echo(f"  Total items: {len(pipeline_items)}")

    # Count items with different ID types
    id_counts = {
        "ASIN": sum(1 for item in pipeline_items if item.get("asin")),
        "UPC": sum(1 for item in pipeline_items if item.get("upc")),
        "EAN": sum(1 for item in pipeline_items if item.get("ean")),
        "UPC/EAN/ASIN": sum(1 for item in pipeline_items if item.get("upc_ean_asin")),
        "Brand only": sum(
            1
            for item in pipeline_items
            if item.get("brand")
            and not any(
                [
                    item.get("asin"),
                    item.get("upc"),
                    item.get("ean"),
                    item.get("upc_ean_asin"),
                ]
            )
        ),
    }

    click.echo("  ID distribution:")
    for id_type, count in id_counts.items():
        if count > 0:
            click.echo(f"    {id_type}: {count}")

    # Condition distribution
    condition_col = df.get("condition")
    if condition_col is not None and len(condition_col.dropna()) > 0:
        conditions = condition_col.value_counts()
        click.echo("  Conditions:")
        for condition, count in conditions.head().items():
            click.echo(f"    {condition}: {count}")

    # Brand distribution (top 5)
    brand_col = df.get("brand")
    if brand_col is not None and len(brand_col.dropna()) > 0:
        brands = brand_col.value_counts()
        click.echo("  Top brands:")
        for brand, count in brands.head(5).items():
            if brand:  # Skip empty brands
                click.echo(f"    {brand}: {count}")


if __name__ == "__main__":
    main()
