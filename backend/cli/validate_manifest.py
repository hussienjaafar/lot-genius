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
@click.option(
    "--strict/--no-strict",
    default=False,
    show_default=True,
    help="Exit non-zero when validation fails.",
)
@click.option(
    "--show-coverage/--no-show-coverage",
    default=False,
    show_default=True,
    help="Include a human-friendly percentage field in the JSON payload.",
)
def main(csv_path: Path, threshold: int, strict: bool, show_coverage: bool):
    """
    Validate a raw manifest CSV:
      - header mapping coverage,
      - minimal GE checks on mapped columns.
    Prints a JSON report with 'passed' boolean and notes.
    """
    rep = validate_manifest_csv(csv_path, fuzzy_threshold=threshold)
    failed_expectations = [
        r.get("expectation") for r in rep.ge_results if not r.get("success")
    ]
    payload = {
        "path": rep.path,
        "passed": rep.passed,
        "header_coverage": rep.header_coverage,
        "mapped_headers": rep.mapped_headers,
        "total_headers": rep.total_headers,
        "unmapped_headers": rep.unmapped_headers,
        "ge_success": rep.ge_success,
        "ge_results": rep.ge_results,
        "failed_expectations": failed_expectations,
        "notes": rep.notes,
    }
    if show_coverage:
        payload["header_coverage_pct"] = f"{rep.header_coverage:.0%}"
    click.echo(json.dumps(payload, indent=2))
    if strict and not payload["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
