import json
from pathlib import Path

import click
from lotgenius.parse import parse_and_clean


@click.command()
@click.argument(
    "csv_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--threshold", default=88, show_default=True, help="Fuzzy match threshold (0-100)"
)
@click.option(
    "--explode/--no-explode",
    default=True,
    show_default=True,
    help="Explode rows by quantity→one unit per row",
)
@click.option(
    "--out",
    "out_fmt",
    type=click.Choice(["csv", "parquet", "json"], case_sensitive=False),
    default="csv",
    show_default=True,
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="If not provided, prints JSON summary instead of writing a table",
)
@click.option(
    "--summary/--no-summary",
    default=True,
    show_default=True,
    help="Print a small JSON summary (mappings, counts)",
)
def main(
    csv_path: Path,
    threshold: int,
    explode: bool,
    out_fmt: str,
    output_path: Path | None,
    summary: bool,
):
    """
    Map → Clean → (optional) Explode a raw manifest CSV.
    If --output is provided, writes the cleaned/exploded table to that path (csv/parquet/json).
    Always prints a small JSON summary when --summary is on.
    """
    res = parse_and_clean(csv_path, fuzzy_threshold=threshold, explode=explode)

    # Write table if requested
    if output_path:
        df = (
            res.df_exploded if explode and res.df_exploded is not None else res.df_clean
        )
        if out_fmt.lower() == "csv":
            df.to_csv(output_path, index=False)
        elif out_fmt.lower() == "parquet":
            df.to_parquet(output_path, index=False)
        else:
            df.to_json(output_path, orient="records", force_ascii=False)
    # Summary
    if summary:
        payload = {
            "path": res.raw_path,
            "unmapped_headers": res.unmapped_headers,
            "mapped_count": len(res.mapped_columns),
            "total_headers": (len(res.mapped_columns) + len(res.unmapped_headers)),
            "clean_rows": int(res.df_clean.shape[0]),
            "exploded_rows": (
                int(res.df_exploded.shape[0]) if res.df_exploded is not None else None
            ),
            "wrote_table": bool(output_path),
            "format": out_fmt if output_path else None,
        }
        click.echo(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
