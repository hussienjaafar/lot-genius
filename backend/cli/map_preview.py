import json
from pathlib import Path

import click
import pandas as pd
from lotgenius.headers import learn_alias, map_headers


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
def main(csv_path: Path, threshold: int, save_alias: list[tuple[str, str]]):
    """
    Preview header mappings for a CSV; print mapping + unmapped headers.
    You can persist learned aliases via --save-alias 'Cond.' condition, etc.
    """
    for src, dest in save_alias:
        learn_alias(src, dest)

    df = pd.read_csv(csv_path, nrows=1)  # header row only
    mapping, unmapped = map_headers(list(df.columns), threshold=threshold)
    click.echo(
        json.dumps(
            {"path": str(csv_path), "mapping": mapping, "unmapped": unmapped}, indent=2
        )
    )


if __name__ == "__main__":
    main()
