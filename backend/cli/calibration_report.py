#!/usr/bin/env python3
"""
CLI helper for calibration reporting.

Loads predictions JSONL and outcomes CSV, computes metrics, and generates
adjustment suggestions.
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from lotgenius.calibration import (
    compute_metrics,
    join_predictions_outcomes,
    load_outcomes,
    load_predictions,
    suggest_adjustments,
)


@click.command()
@click.argument("predictions_jsonl", type=click.Path(exists=True, path_type=Path))
@click.argument("outcomes_csv", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--out-json", type=click.Path(path_type=Path), help="Output JSON report path"
)
@click.option(
    "--out-md", type=click.Path(path_type=Path), help="Output Markdown report path"
)
@click.option(
    "--horizon-days", type=int, default=60, help="Horizon days for calibration"
)
def main(
    predictions_jsonl: Path,
    outcomes_csv: Path,
    out_json: Optional[Path],
    out_md: Optional[Path],
    horizon_days: int,
):
    """
    Generate calibration report from predictions and outcomes.

    PREDICTIONS_JSONL: Path to predictions JSONL file
    OUTCOMES_CSV: Path to outcomes CSV file
    """
    try:
        # Load data
        click.echo("Loading predictions...")
        predictions = load_predictions(str(predictions_jsonl))

        click.echo("Loading outcomes...")
        outcomes = load_outcomes(str(outcomes_csv))

        if predictions.empty:
            click.echo("No predictions found.", err=True)
            sys.exit(1)
        if outcomes.empty:
            click.echo("No outcomes found.", err=True)
            sys.exit(1)

        # Join data
        click.echo("Joining predictions and outcomes...")
        joined = join_predictions_outcomes(predictions, outcomes)

        if joined.empty:
            click.echo(
                "No matching records found between predictions and outcomes.", err=True
            )
            sys.exit(1)

        click.echo(f"Found {len(joined)} matching records.")

        # Compute metrics
        click.echo("Computing metrics...")
        metrics = compute_metrics(joined, horizon_days)

        # Generate suggestions
        click.echo("Generating adjustment suggestions...")
        suggestions = suggest_adjustments(joined)

        # Combine into report
        report = {
            "summary": {
                "predictions_file": str(predictions_jsonl),
                "outcomes_file": str(outcomes_csv),
                "n_predictions": len(predictions),
                "n_outcomes": len(outcomes),
                "n_matched": len(joined),
                "match_rate": len(joined) / len(predictions),
                "horizon_days": horizon_days,
            },
            "metrics": metrics,
            "suggestions": suggestions,
        }

        # Write JSON report
        if out_json:
            out_json.parent.mkdir(parents=True, exist_ok=True)
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            click.echo(f"JSON report written to: {out_json}")

        # Write Markdown report
        if out_md:
            out_md.parent.mkdir(parents=True, exist_ok=True)
            markdown_content = _generate_markdown_report(report)
            with open(out_md, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            click.echo(f"Markdown report written to: {out_md}")

        # Print summary to console
        click.echo("\n=== Calibration Report Summary ===")
        click.echo(
            f"Matched records: {len(joined)}/{len(predictions)} ({len(joined)/len(predictions)*100:.1f}%)"
        )

        # Print key metrics if available
        if "price_metrics" in metrics:
            pm = metrics["price_metrics"]
            click.echo(f"Price MAE: ${pm['mae']:.2f}")
            if pm["mape"] is not None:
                click.echo(f"Price MAPE: {pm['mape']*100:.1f}%")

        if "probability_metrics" in metrics:
            pb = metrics["probability_metrics"]
            click.echo(f"Brier Score: {pb['brier_score']:.4f}")

        # Print key suggestions if available
        if "condition_price_factors" in suggestions:
            click.echo("\nCondition factor suggestions:")
            for condition, adj in suggestions["condition_price_factors"].items():
                current = adj["current_factor"]
                suggested = adj["suggested_factor"]
                change_pct = (suggested / current - 1) * 100
                click.echo(
                    f"  {condition}: {current:.3f} -> {suggested:.3f} ({change_pct:+.1f}%)"
                )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _generate_markdown_report(report: dict) -> str:
    """Generate Markdown report content."""
    lines = []

    lines.append("# Calibration Report")
    lines.append("")

    # Summary
    summary = report["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Predictions file**: {summary['predictions_file']}")
    lines.append(f"- **Outcomes file**: {summary['outcomes_file']}")
    lines.append(
        f"- **Records matched**: {summary['n_matched']}/{summary['n_predictions']} ({summary['match_rate']*100:.1f}%)"
    )
    lines.append(f"- **Horizon**: {summary['horizon_days']} days")
    lines.append("")

    # Metrics
    metrics = report["metrics"]
    lines.append("## Metrics")
    lines.append("")

    if "price_metrics" in metrics:
        pm = metrics["price_metrics"]
        lines.append("### Price Prediction")
        lines.append("")
        lines.append(f"- **MAE**: ${pm['mae']:.2f}")
        lines.append(f"- **RMSE**: ${pm['rmse']:.2f}")
        if pm["mape"] is not None:
            lines.append(f"- **MAPE**: {pm['mape']*100:.1f}%")
        lines.append(f"- **Samples**: {pm['n_samples']}")
        lines.append("")

    if "probability_metrics" in metrics:
        pb = metrics["probability_metrics"]
        lines.append("### Probability Calibration")
        lines.append("")
        lines.append(f"- **Brier Score**: {pb['brier_score']:.4f}")
        lines.append(f"- **Samples**: {pb['n_samples']}")
        lines.append("")

        if pb["calibration_bins"]:
            lines.append("#### Calibration by Bins")
            lines.append("")
            lines.append(
                "| Predicted Range | Samples | Pred Mean | Actual Rate | Bias |"
            )
            lines.append(
                "|----------------|---------|-----------|-------------|------|"
            )
            for bin_data in pb["calibration_bins"]:
                lines.append(
                    f"| {bin_data['bin']} | {bin_data['n_samples']} | {bin_data['pred_mean']:.3f} | {bin_data['actual_rate']:.3f} | {bin_data['bias']:+.3f} |"
                )
            lines.append("")

    if "holding_days_metrics" in metrics:
        hm = metrics["holding_days_metrics"]
        lines.append("### Holding Days Calibration")
        lines.append("")
        lines.append(f"- **MAE**: {hm['mae']:.1f} days")
        lines.append(f"- **Median Error**: {hm['median_error']:+.1f} days")
        lines.append(f"- **Samples**: {hm['n_samples']}")
        lines.append("")

    # Suggestions
    suggestions = report["suggestions"]
    lines.append("## Adjustment Suggestions")
    lines.append("")

    if "condition_price_factors" in suggestions:
        lines.append("### Condition Price Factors")
        lines.append("")
        lines.append("| Condition | Current | Suggested | Change % | Samples |")
        lines.append("|-----------|---------|-----------|----------|---------|")
        for condition, adj in suggestions["condition_price_factors"].items():
            current = adj["current_factor"]
            suggested = adj["suggested_factor"]
            change_pct = (suggested / current - 1) * 100
            lines.append(
                f"| {condition} | {current:.3f} | {suggested:.3f} | {change_pct:+.1f}% | {adj['n_samples']} |"
            )
        lines.append("")

    if "survival_alpha_scaling" in suggestions:
        sas = suggestions["survival_alpha_scaling"]
        lines.append("### Survival Model Scaling")
        lines.append("")
        lines.append(
            f"- **Holding days ratio**: {sas['median_holding_days_ratio']:.3f}"
        )
        lines.append(f"- **Suggestion**: {sas['suggestion']}")
        lines.append(f"- **Samples**: {sas['n_samples']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
