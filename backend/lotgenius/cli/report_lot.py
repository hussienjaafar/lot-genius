import json
import subprocess
from pathlib import Path

import click
import pandas as pd


def _load_last_evidence_record(p):
    """Load the last record from an NDJSON evidence file."""
    try:
        lines = [
            ln for ln in Path(p).read_text(encoding="utf-8").splitlines() if ln.strip()
        ]
        return json.loads(lines[-1]) if lines else None
    except Exception:
        return None


@click.command()
@click.option(
    "--items-csv",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Per-unit CSV (from Step 8 - estimated sell through)",
)
@click.option(
    "--opt-json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Optimizer JSON (from Step 9)",
)
@click.option(
    "--out-markdown",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output Markdown report path",
)
@click.option(
    "--out-html",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Optional HTML output path (requires pandoc)",
)
@click.option(
    "--out-pdf",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Optional PDF output path (requires pandoc + LaTeX)",
)
@click.option(
    "--sweep-csv",
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    help="Optional sweep CSV path to reference",
)
@click.option(
    "--sweep-png",
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    help="Optional sweep PNG path to reference",
)
@click.option(
    "--evidence-jsonl",
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    help="Optional optimizer evidence JSONL path to reference",
)
def main(
    items_csv,
    opt_json,
    out_markdown,
    out_html,
    out_pdf,
    sweep_csv,
    sweep_png,
    evidence_jsonl,
):
    """
    Generate a concise Lot Genius report from per-unit CSV and optimizer JSON.
    """
    items = pd.read_csv(items_csv)
    opt = json.loads(Path(opt_json).read_text(encoding="utf-8"))

    # Generate markdown content
    markdown_content = _mk_markdown(items, opt, sweep_csv, sweep_png, evidence_jsonl)

    # Write markdown
    out_markdown_path = Path(out_markdown)
    out_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    out_markdown_path.write_text(markdown_content, encoding="utf-8")

    # Optional HTML conversion
    html_path = None
    if out_html:
        html_path = _optional_html(out_markdown_path, Path(out_html))

    # Optional PDF conversion
    pdf_path = None
    if out_pdf:
        pdf_path = _optional_pdf(out_markdown_path, Path(out_pdf))

    # Output summary
    summary = {
        "items_csv": str(items_csv),
        "opt_json": str(opt_json),
        "out_markdown": str(out_markdown_path),
        "out_html": str(html_path) if html_path else None,
        "out_pdf": str(pdf_path) if pdf_path else None,
        "artifact_references": {
            "sweep_csv": str(sweep_csv) if sweep_csv else None,
            "sweep_png": str(sweep_png) if sweep_png else None,
            "evidence_jsonl": str(evidence_jsonl) if evidence_jsonl else None,
        },
    }

    click.echo(json.dumps(summary, indent=2))


def _mk_markdown(items, opt, sweep_csv=None, sweep_png=None, evidence_jsonl=None):
    """Generate Markdown report content."""
    # Extract key metrics
    item_count = len(items)

    # Items totals/averages with column existence checks
    if "est_price_mu" in items.columns:
        total_mu = float(items["est_price_mu"].sum(skipna=True))
    else:
        total_mu = None

    if "est_price_p50" in items.columns:
        total_p50 = float(items["est_price_p50"].sum(skipna=True))
    elif "est_price_median" in items.columns:
        total_p50 = float(items["est_price_median"].sum(skipna=True))
    else:
        total_p50 = None

    avg_sell_p60 = (
        float(items["sell_p60"].mean(skipna=True))
        if "sell_p60" in items.columns
        else None
    )

    # Optimizer metrics (no default coercion - let None flow to fmt_*)
    recommended_bid = opt.get("bid")
    roi_p50 = opt.get("roi_p50")
    prob_roi_ge_target = opt.get("prob_roi_ge_target")
    expected_cash_60d = opt.get("expected_cash_60d")
    meets_constraints = opt.get("meets_constraints")
    roi_target = opt.get("roi_target")
    risk_threshold = opt.get("risk_threshold")

    # Evidence fallback if values missing and evidence file provided and exists
    if (
        evidence_jsonl
        and (roi_target is None or risk_threshold is None)
        and Path(evidence_jsonl).exists()
    ):
        rec = _load_last_evidence_record(evidence_jsonl)
        meta = (rec or {}).get("meta", {}) if isinstance(rec, dict) else {}
        roi_target = meta.get("roi_target", roi_target)
        risk_threshold = meta.get("risk_threshold", risk_threshold)

    # Type safety for formatting after fallback
    try:
        roi_target = float(roi_target) if roi_target is not None else None
    except Exception:
        pass
    try:
        risk_threshold = float(risk_threshold) if risk_threshold is not None else None
    except Exception:
        pass

    # Format numbers
    def fmt_currency(x):
        return f"${x:,.2f}" if x is not None and not pd.isna(x) else "N/A"

    def fmt_pct(x):
        return f"{x:.1%}" if x is not None and not pd.isna(x) else "N/A"

    def fmt_ratio(x):
        return f"{x:.2f}×" if x is not None and not pd.isna(x) else "N/A"

    def fmt_bool(x):
        if x is True:
            return "Yes"
        if x is False:
            return "No"
        return "N/A"

    def fmt_bool_emoji(x):
        if x is True:
            return "✅ Yes"
        if x is False:
            return "❌ No"
        return "N/A"

    def fmt_prob2(x):
        return f"{x:.2f}" if x is not None and not pd.isna(x) else "N/A"

    # Build markdown content
    md_lines = [
        "# Lot Genius Report",
        "",
        "## Executive Summary",
        "",
        f"**Recommended Maximum Bid:** {fmt_currency(recommended_bid)}",
        f"**Expected ROI (P50):** {fmt_ratio(roi_p50)}",
        f"**Probability of Meeting ROI Target:** {fmt_pct(prob_roi_ge_target)}",
        f"**Expected 60-day Cash Recovery:** {fmt_currency(expected_cash_60d)}",
        f"**Meets All Constraints:** {fmt_bool_emoji(meets_constraints)}",
    ]

    # Add unconditional Executive Summary bullets
    md_lines.extend(
        [
            "",
            (
                f"- ROI Target: **{roi_target:.2f}×**"
                if roi_target is not None
                else "- ROI Target: **N/A**"
            ),
            f"- Risk Threshold: **P(ROI≥target) ≥ {fmt_prob2(risk_threshold)}**",
            "",
        ]
    )

    md_lines.extend(
        [
            "## Lot Overview",
            "",
            f"- **Total Items:** {item_count:,}",
            f"- **Estimated Total Value (μ):** {fmt_currency(total_mu)}",
            f"- **Estimated Total Value (P50):** {fmt_currency(total_p50)}",
            f"- **Average 60-day Sell Probability:** {fmt_pct(avg_sell_p60)}",
        ]
    )

    md_lines.extend(
        [
            "",
            "## Optimization Parameters",
            "",
            (
                f"- **ROI Target:** {roi_target:.2f}×"
                if roi_target is not None
                else "- **ROI Target:** N/A"
            ),
            f"- **Risk Threshold:** P(ROI≥target) ≥ {fmt_prob2(risk_threshold)}",
            "",
            "## Investment Decision",
            "",
        ]
    )

    # Investment recommendation
    if meets_constraints is True:
        md_lines.extend(
            [
                "🟢 **PROCEED** - This lot meets the configured investment criteria.",
                "",
                f"The recommended bid of {fmt_currency(recommended_bid)} has a "
                f"{fmt_pct(prob_roi_ge_target)} probability of achieving the target ROI of "
                f"{roi_target if roi_target is not None else 'N/A'}×, which exceeds the Risk Threshold of "
                f"{fmt_prob2(risk_threshold)}.",
            ]
        )
    elif meets_constraints is False:
        md_lines.extend(
            [
                "🔴 **PASS** - This lot does not meet the configured investment criteria.",
                "",
                f"No feasible bid was found that achieves the target ROI of "
                f"{roi_target if roi_target is not None else 'N/A'}× with probability ≥ "
                f"{fmt_prob2(risk_threshold)}. Consider lowering the ROI Target "
                "or Risk Threshold, or look for a different lot.",
            ]
        )
    else:
        md_lines.extend(
            [
                "🟡 **REVIEW** - Unable to determine investment recommendation.",
                "",
                "Missing constraint evaluation data. Please check input parameters and optimizer configuration.",
            ]
        )

    # Add artifact references only if files exist
    show_artifacts = False
    if sweep_csv and Path(sweep_csv).exists():
        show_artifacts = True
    if sweep_png and Path(sweep_png).exists():
        show_artifacts = True
    if evidence_jsonl and Path(evidence_jsonl).exists():
        show_artifacts = True

    if show_artifacts:
        md_lines.extend(["", "## Supporting Artifacts", ""])
        if sweep_csv and Path(sweep_csv).exists():
            md_lines.append(f"- **Bid Sensitivity Analysis:** `{sweep_csv}`")
        if sweep_png and Path(sweep_png).exists():
            md_lines.append(f"- **Bid Sensitivity Chart:** `{sweep_png}`")
        if evidence_jsonl and Path(evidence_jsonl).exists():
            md_lines.append(f"- **Optimization Audit Trail:** `{evidence_jsonl}`")

    md_lines.extend(
        [
            "",
            "---",
            "",
            "*Generated by Lot Genius Step 9.2*",
            "",
        ]
    )

    return "\n".join(md_lines)


def _optional_html(markdown_path, html_path):
    """Convert markdown to HTML using pandoc (if available)."""
    try:
        html_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["pandoc", str(markdown_path), "-o", str(html_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return html_path
    except FileNotFoundError:
        click.echo("Warning: pandoc not found, skipping HTML conversion", err=True)
        return None
    except subprocess.CalledProcessError as e:
        click.echo(f"Error converting to HTML: {e.stderr}", err=True)
        return None


def _optional_pdf(markdown_path, pdf_path):
    """Convert markdown to PDF using pandoc (if available)."""
    try:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "pandoc",
                str(markdown_path),
                "-o",
                str(pdf_path),
                "--pdf-engine=pdflatex",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return pdf_path
    except FileNotFoundError:
        click.echo("Warning: pandoc not found, skipping PDF conversion", err=True)
        return None
    except subprocess.CalledProcessError as e:
        click.echo(f"Error converting to PDF: {e.stderr}", err=True)
        return None


if __name__ == "__main__":
    main()
