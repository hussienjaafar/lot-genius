import json
from pathlib import Path

import click
import pandas as pd
from lotgenius.headers import (
    find_conflicts,
    learn_alias,
    map_headers,
    suggest_candidates,
)


@click.command()
@click.argument(
    "csv_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--threshold", default=88, show_default=True, help="Fuzzy match threshold (0-100)"
)
@click.option(
    "--save-alias",
    nargs=2,
    multiple=True,
    metavar="SRC CANONICAL",
    help="Persist a header alias mapping (can be repeated)",
)
@click.option(
    "--show-candidates/--no-show-candidates",
    default=False,
    show_default=True,
    help="If true, prints top fuzzy matches for unmapped headers.",
)
@click.option(
    "--top-k",
    default=5,
    show_default=True,
    help="How many suggestions per unmapped header",
)
@click.option(
    "--fail-on-duplicates/--no-fail-on-duplicates",
    default=False,
    show_default=True,
    help="Exit with non-zero if multiple source headers map to the same canonical field.",
)
def main(
    csv_path: Path,
    threshold: int,
    save_alias: list[tuple[str, str]],
    show_candidates: bool,
    top_k: int,
    fail_on_duplicates: bool,
):
    """
    Preview header mappings for a CSV; print mapping + unmapped headers.
    You can persist learned aliases via --save-alias 'Cond.' condition, etc.
    """
    for src, dest in save_alias:
        learn_alias(src, dest)

    df = pd.read_csv(csv_path, nrows=1, encoding="utf-8")  # header row only
    mapping, unmapped = map_headers(list(df.columns), threshold=threshold)

    suggestions = {}
    if show_candidates and unmapped:
        for h in unmapped:
            suggestions[h] = suggest_candidates(h, top_k=top_k)

    conflicts = find_conflicts(mapping)
    if conflicts:
        click.secho(
            "WARNING: Multiple source headers mapped to the same canonical fields:",
            fg="yellow",
        )
        for canon, srcs in conflicts.items():
            click.secho(f"  - {canon}: {', '.join(srcs)}", fg="yellow")

    payload = {"path": str(csv_path), "mapping": mapping, "unmapped": unmapped}
    if show_candidates:
        payload["suggestions"] = suggestions
    if conflicts:
        payload["conflicts"] = conflicts

    click.echo(json.dumps(payload, indent=2))

    if conflicts and fail_on_duplicates:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
