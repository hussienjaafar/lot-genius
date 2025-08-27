"""
CLI for automated calibration run - consumes predictions and outcomes to generate metrics and suggestions.
"""

import json
from datetime import datetime
from pathlib import Path

import click
from lotgenius.calibration import (
    compute_metrics,
    join_predictions_outcomes,
    load_outcomes,
    load_predictions,
    suggest_adjustments,
    write_suggestions,
)
from lotgenius.config import settings


@click.command()
@click.argument("predictions_jsonl", type=click.Path(exists=True))
@click.argument("outcomes_csv", type=click.Path(exists=True))
@click.option("--out-metrics", type=click.Path(), help="Output path for metrics JSON")
@click.option(
    "--out-suggestions", type=click.Path(), help="Output path for suggestions JSON"
)
@click.option(
    "--history-dir",
    type=click.Path(),
    default="backend/lotgenius/data/calibration/history",
    show_default=True,
    help="Directory for timestamped history files",
)
def main(predictions_jsonl, outcomes_csv, out_metrics, out_suggestions, history_dir):
    """
    Run calibration analysis on predictions and outcomes data.

    Consumes predictions JSONL and outcomes CSV, computes metrics,
    suggests adjustments, and writes timestamped history files.

    PREDICTIONS_JSONL: Path to predictions JSONL file
    OUTCOMES_CSV: Path to outcomes CSV file
    """

    # Setup paths
    history_dir = Path(history_dir)
    history_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for history files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Default output paths if not specified
    if not out_metrics:
        out_metrics = history_dir / f"metrics_{timestamp}.json"
    if not out_suggestions:
        out_suggestions = history_dir / f"suggestions_{timestamp}.json"

    try:
        click.echo(f"Loading predictions from {predictions_jsonl}...")
        predictions = load_predictions(predictions_jsonl)
        click.echo(f"Loaded {len(predictions)} predictions")

        click.echo(f"Loading outcomes from {outcomes_csv}...")
        outcomes = load_outcomes(outcomes_csv)
        click.echo(f"Loaded {len(outcomes)} outcomes")

        click.echo("Joining predictions with outcomes...")
        joined_data = join_predictions_outcomes(predictions, outcomes)
        click.echo(f"Joined {len(joined_data)} records")

        if len(joined_data) == 0:
            click.echo(
                "Warning: No matching records found between predictions and outcomes",
                err=True,
            )
            return

        click.echo("Computing calibration metrics...")
        metrics = compute_metrics(joined_data, settings.SELLTHROUGH_HORIZON_DAYS)

        click.echo("Generating adjustment suggestions...")
        suggestions = suggest_adjustments(joined_data)

        # Write metrics
        click.echo(f"Writing metrics to {out_metrics}...")
        with open(out_metrics, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        # Write suggestions
        click.echo(f"Writing suggestions to {out_suggestions}...")
        write_suggestions(suggestions, str(out_suggestions))

        # Update canonical suggestions file
        canonical_suggestions = Path(
            "backend/lotgenius/data/calibration_suggestions.json"
        )
        canonical_suggestions.parent.mkdir(parents=True, exist_ok=True)
        click.echo(f"Updating canonical suggestions at {canonical_suggestions}...")
        write_suggestions(suggestions, str(canonical_suggestions))

        # Write timestamped history copies
        history_metrics = history_dir / f"metrics_{timestamp}.json"
        history_suggestions = history_dir / f"suggestions_{timestamp}.json"

        if str(out_metrics) != str(history_metrics):
            click.echo(f"Writing history metrics to {history_metrics}...")
            with open(history_metrics, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)

        if str(out_suggestions) != str(history_suggestions):
            click.echo(f"Writing history suggestions to {history_suggestions}...")
            write_suggestions(suggestions, str(history_suggestions))

        # Summary
        click.echo("\n=== Calibration Run Complete ===")
        click.echo(f"Metrics written to: {out_metrics}")
        click.echo(f"Suggestions written to: {out_suggestions}")
        click.echo(f"Canonical suggestions updated: {canonical_suggestions}")
        click.echo(f"History files in: {history_dir}")

        # Show key metrics
        if "overall" in metrics:
            overall = metrics["overall"]
            click.echo("\nOverall Metrics:")
            if "mae" in overall:
                click.echo(f"  Mean Absolute Error: {overall['mae']:.4f}")
            if "rmse" in overall:
                click.echo(f"  Root Mean Square Error: {overall['rmse']:.4f}")
            if "bias" in overall:
                click.echo(f"  Bias: {overall['bias']:.4f}")

    except Exception as e:
        click.echo(f"Error during calibration run: {e}", err=True)
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
