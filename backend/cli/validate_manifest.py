import json
from pathlib import Path

import click
from lotgenius.validation import validate_manifest_csv


@click.command()
@click.argument(
    "csv_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--threshold", default=88, show_default=True, help="Fuzzy match threshold (0-100)"
)
def main(csv_path: Path, threshold: int):
    """
    Validate a raw manifest CSV:
      - header mapping coverage,
      - minimal GE checks on mapped columns.
    Prints a JSON report with 'passed' boolean and notes.
    """
    rep = validate_manifest_csv(csv_path, fuzzy_threshold=threshold)
    payload = {
        "path": rep.path,
        "passed": rep.passed,
        "header_coverage": rep.header_coverage,
        "mapped_headers": rep.mapped_headers,
        "total_headers": rep.total_headers,
        "unmapped_headers": rep.unmapped_headers,
        "ge_success": rep.ge_success,
        "ge_results": rep.ge_results,
        "notes": rep.notes,
    }
    click.echo(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
