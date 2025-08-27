"""
CLI for applying calibration suggestions to create bounded overrides.
"""

import json
from pathlib import Path

import click


@click.command()
@click.option(
    "--suggestions",
    type=click.Path(exists=True),
    required=True,
    help="Path to suggestions JSON file",
)
@click.option(
    "--out-overrides",
    type=click.Path(),
    required=True,
    help="Output path for overrides JSON file",
)
@click.option(
    "--min-factor",
    type=float,
    default=0.5,
    show_default=True,
    help="Minimum allowed condition factor",
)
@click.option(
    "--max-factor",
    type=float,
    default=1.2,
    show_default=True,
    help="Maximum allowed condition factor",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be applied without writing file"
)
def main(suggestions, out_overrides, min_factor, max_factor, dry_run):
    """
    Apply calibration suggestions to create bounded condition factor overrides.

    Reads suggestions JSON, extracts condition price factor adjustments,
    clamps values to safe bounds, and writes overrides JSON.
    """

    if min_factor >= max_factor:
        raise click.ClickException(
            f"min-factor ({min_factor}) must be less than max-factor ({max_factor})"
        )

    if min_factor <= 0:
        raise click.ClickException(f"min-factor ({min_factor}) must be positive")

    try:
        click.echo(f"Loading suggestions from {suggestions}...")
        with open(suggestions, "r", encoding="utf-8") as f:
            suggestions_data = json.load(f)

        # Extract condition price factor suggestions
        condition_factors = {}

        if "suggestions" in suggestions_data:
            for suggestion in suggestions_data["suggestions"]:
                if suggestion.get("type") == "condition_price_factor":
                    condition = suggestion.get("condition")
                    suggested_factor = suggestion.get("suggested_factor")

                    if condition and suggested_factor is not None:
                        # Apply bounds
                        bounded_factor = max(
                            min_factor, min(max_factor, float(suggested_factor))
                        )
                        condition_factors[condition] = bounded_factor

                        if bounded_factor != suggested_factor:
                            click.echo(
                                f"  Bounded {condition}: {suggested_factor:.4f} -> {bounded_factor:.4f}"
                            )
                        else:
                            click.echo(f"  Applied {condition}: {bounded_factor:.4f}")

        if not condition_factors:
            click.echo("No condition price factor suggestions found")
            if not dry_run:
                # Still create an empty overrides file
                overrides_data = {"CONDITION_PRICE_FACTOR": {}}
            else:
                return
        else:
            click.echo(f"\nFound {len(condition_factors)} condition factor suggestions")
            overrides_data = {"CONDITION_PRICE_FACTOR": condition_factors}

        if dry_run:
            click.echo("\n=== DRY RUN - Would write overrides ===")
            click.echo(json.dumps(overrides_data, indent=2))
            click.echo(f"Would write to: {out_overrides}")
        else:
            # Write overrides file
            out_path = Path(out_overrides)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            click.echo(f"\nWriting overrides to {out_overrides}...")
            with open(out_overrides, "w", encoding="utf-8") as f:
                json.dump(overrides_data, f, indent=2, ensure_ascii=False)

            click.echo("\n=== Calibration Overrides Applied ===")
            click.echo(f"Overrides written to: {out_overrides}")
            click.echo(f"Bounded factors: {len(condition_factors)}")
            click.echo(f"Bounds applied: [{min_factor}, {max_factor}]")

            click.echo("\nTo activate these overrides, set environment variable:")
            click.echo(f"LOTGENIUS_CALIBRATION_OVERRIDES={out_overrides}")

            if condition_factors:
                click.echo("\nFactor adjustments:")
                for condition, factor in condition_factors.items():
                    click.echo(f"  {condition}: {factor:.4f}")

    except FileNotFoundError:
        raise click.ClickException(f"Suggestions file not found: {suggestions}")
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in suggestions file: {e}")
    except Exception as e:
        click.echo(f"Error applying suggestions: {e}", err=True)
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
