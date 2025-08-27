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
@click.option(
    "--stress-csv",
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    help="Optional stress scenarios CSV path for Scenario Diffs section",
)
@click.option(
    "--stress-json",
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    help="Optional stress scenarios JSON path for Scenario Diffs section",
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
    stress_csv,
    stress_json,
):
    """
    Generate a concise Lot Genius report from per-unit CSV and optimizer JSON.
    """
    items = pd.read_csv(items_csv)
    opt = json.loads(Path(opt_json).read_text(encoding="utf-8"))

    # Generate markdown content
    markdown_content = _mk_markdown(
        items, opt, sweep_csv, sweep_png, evidence_jsonl, stress_csv, stress_json
    )

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
            "stress_csv": str(stress_csv) if stress_csv else None,
            "stress_json": str(stress_json) if stress_json else None,
        },
    }

    click.echo(json.dumps(summary, indent=2))


def _mk_markdown(
    items,
    opt,
    sweep_csv=None,
    sweep_png=None,
    evidence_jsonl=None,
    stress_csv=None,
    stress_json=None,
):
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

    # Parse stress scenario data if provided
    stress_df = None
    if stress_csv and Path(stress_csv).exists():
        try:
            stress_df = pd.read_csv(stress_csv)
        except Exception:
            pass
    elif stress_json and Path(stress_json).exists():
        try:
            stress_data = json.loads(Path(stress_json).read_text(encoding="utf-8"))
            if isinstance(stress_data, list) and stress_data:
                stress_df = pd.DataFrame(stress_data)
        except Exception:
            pass

    # Validate stress data has required columns
    if stress_df is not None:
        required_cols = ["scenario", "bid", "prob_roi_ge_target", "expected_cash_60d"]
        if not all(col in stress_df.columns for col in required_cols):
            stress_df = None

    # Format numbers
    def fmt_currency(x):
        return f"${x:,.2f}" if x is not None and not pd.isna(x) else "N/A"

    def fmt_pct(x):
        return f"{x:.1%}" if x is not None and not pd.isna(x) else "N/A"

    def fmt_ratio(x):
        return f"{x:.2f}x" if x is not None and not pd.isna(x) else "N/A"

    def fmt_bool(x):
        if x is True:
            return "Yes"
        if x is False:
            return "No"
        return "N/A"

    def fmt_bool_emoji(x):
        if x is True:
            return "Yes"
        if x is False:
            return "No"
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
                f"- ROI Target: **{roi_target:.2f}x**"
                if roi_target is not None
                else "- ROI Target: **N/A**"
            ),
            f"- Risk Threshold: **P(ROI>=target) >= {fmt_prob2(risk_threshold)}**",
            "",
        ]
    )

    md_lines.extend(
        [
            "## Lot Overview",
            "",
            f"- **Total Items:** {item_count:,}",
            f"- **Estimated Total Value (mu):** {fmt_currency(total_mu)}",
            f"- **Estimated Total Value (P50):** {fmt_currency(total_p50)}",
            f"- **Average 60-day Sell Probability:** {fmt_pct(avg_sell_p60)}",
        ]
    )

    # Add Item Details table if Product Confidence data is available
    has_product_confidence = False
    if len(items) > 0:
        # Check if any items have product_confidence in their evidence meta
        for col in items.columns:
            if col.startswith("evidence_meta") and "product_confidence" in str(
                items[col].iloc[0] if pd.notna(items[col].iloc[0]) else ""
            ):
                has_product_confidence = True
                break

        # Alternative check: look for evidence_meta column containing product_confidence
        if "evidence_meta" in items.columns:
            sample_meta = (
                items["evidence_meta"].dropna().iloc[0]
                if len(items["evidence_meta"].dropna()) > 0
                else None
            )
            if sample_meta and isinstance(sample_meta, str):
                try:
                    import json

                    meta_dict = json.loads(sample_meta)
                    has_product_confidence = "product_confidence" in meta_dict
                except (json.JSONDecodeError, TypeError):
                    pass

    if has_product_confidence or "product_confidence" in items.columns:
        md_lines.extend(["", "## Item Details", ""])

        # Show first 10 items (or all if fewer) in a table format
        display_items = items.head(10)

        # Table header
        headers = ["SKU", "Title", "Est. Price", "Sell P60"]
        if has_product_confidence:
            headers.append("Product Confidence")

        md_lines.append("| " + " | ".join(headers) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Table rows
        for idx, row in display_items.iterrows():
            # Extract basic fields
            sku = str(row.get("item_key", row.get("sku", "N/A")))[
                :20
            ]  # Truncate long SKUs
            title = str(row.get("title", "N/A"))[:40] + (
                "..." if len(str(row.get("title", ""))) > 40 else ""
            )  # Truncate long titles

            # Price (prefer est_price_p50, fallback to est_price_mu)
            price = row.get(
                "est_price_p50", row.get("est_price_mu", row.get("est_price_median"))
            )
            price_str = (
                fmt_currency(price)
                if price is not None and not pd.isna(price)
                else "N/A"
            )

            # Sell probability
            sell_p60 = row.get("sell_p60")
            sell_p60_str = (
                fmt_pct(sell_p60)
                if sell_p60 is not None and not pd.isna(sell_p60)
                else "N/A"
            )

            # Product confidence
            confidence_str = "N/A"
            if has_product_confidence:
                # Try to extract product_confidence from evidence_meta
                if "evidence_meta" in row and pd.notna(row["evidence_meta"]):
                    try:
                        meta_dict = json.loads(str(row["evidence_meta"]))
                        confidence = meta_dict.get("product_confidence")
                        if confidence is not None:
                            confidence_str = f"{confidence:.2f}"
                    except:
                        pass
                # Or directly from product_confidence column
                elif "product_confidence" in row and pd.notna(
                    row["product_confidence"]
                ):
                    confidence_str = f"{row['product_confidence']:.2f}"

            # Build row
            row_data = [sku, title, price_str, sell_p60_str]
            if has_product_confidence:
                row_data.append(confidence_str)

            md_lines.append("| " + " | ".join(row_data) + " |")

        # Add note if there are more items
        if len(items) > 10:
            md_lines.extend(
                ["", f"*Showing first 10 items of {len(items)} total items.*"]
            )

    # Get payout lag from opt result or fallback to settings
    payout_lag_days = opt.get("payout_lag_days")
    if payout_lag_days is None:
        from lotgenius.config import settings

        payout_lag_days = settings.PAYOUT_LAG_DAYS

    # Get cashfloor from opt result or fallback to settings
    cashfloor = opt.get("cashfloor")
    if cashfloor is None:
        from lotgenius.config import settings

        cashfloor = settings.CASHFLOOR

    # Consolidated Constraints section
    md_lines.extend(
        [
            "",
            "## Constraints",
            "",
            (
                f"- **ROI Target:** {roi_target:.2f}x"
                if roi_target is not None
                else "- **ROI Target:** N/A"
            ),
            f"- **Risk Threshold:** P(ROI>=target) >= {fmt_prob2(risk_threshold)}",
            f"- **Cashfloor:** {fmt_currency(cashfloor)}",
            f"- **Payout Lag:** {payout_lag_days} days",
        ]
    )

    # Add throughput constraints if available
    if "throughput" in opt and isinstance(opt["throughput"], dict):
        throughput = opt["throughput"]
        throughput_status = "Pass" if throughput.get("throughput_ok") else "Fail"
        md_lines.append(f"- **Throughput Constraint:** {throughput_status}")

    # Add gating/hazmat counts if evidence summary is available
    evidence_summary = opt.get("evidence_gate", {}).get("evidence_summary")
    if evidence_summary:
        core_count = evidence_summary.get("core_count", 0)
        upside_count = evidence_summary.get("upside_count", 0)
        md_lines.extend(
            [
                f"- **Gated Items:** {core_count} core, {upside_count} review",
            ]
        )

    md_lines.append("")

    md_lines.extend(
        [
            "## Optimization Parameters",
            "",
            (
                f"- **ROI Target:** {roi_target:.2f}x"
                if roi_target is not None
                else "- **ROI Target:** N/A"
            ),
            f"- **Risk Threshold:** P(ROI>=target) >= {fmt_prob2(risk_threshold)}",
            f"- **Payout Lag (days):** {payout_lag_days}",
            "",
        ]
    )

    # Add Gating/Hazmat section when evidence summary is available
    if evidence_summary:
        from lotgenius.config import settings

        # Get policy values from settings (these may have been overridden at runtime)
        gated_brands = settings.GATED_BRANDS_CSV or "None"
        hazmat_policy = settings.HAZMAT_POLICY or "allow"

        core_count = evidence_summary.get("core_count", 0)
        upside_count = evidence_summary.get("upside_count", 0)
        total_items = evidence_summary.get("total_items", core_count + upside_count)
        gate_pass_rate = evidence_summary.get("gate_pass_rate", 0.0) * 100

        md_lines.extend(
            [
                "## Gating/Hazmat",
                "",
                f"- **Gated Brands:** {gated_brands}",
                f"- **Hazmat Policy:** {hazmat_policy}",
                f"- **Core Items:** {core_count} ({gate_pass_rate:.1f}%)",
                f"- **Review Items:** {upside_count} ({100 - gate_pass_rate:.1f}%)",
                f"- **Total Items:** {total_items}",
                "",
            ]
        )

    # Add Throughput section if throughput data is present
    if "throughput" in opt and isinstance(opt["throughput"], dict):
        throughput = opt["throughput"]
        md_lines.extend(
            [
                "## Throughput",
                "",
                f"- **Mins per unit:** {throughput.get('mins_per_unit', 'N/A')}",
                f"- **Capacity mins/day:** {throughput.get('capacity_mins_per_day', 'N/A')}",
                f"- **Total mins required (lot):** {throughput.get('total_minutes_required', 'N/A')}",
                f"- **Available mins (horizon):** {throughput.get('available_minutes', 'N/A')}",
                f"- **Throughput OK:** {fmt_bool(throughput.get('throughput_ok'))}",
                "",
            ]
        )

    # Add Pricing Ladder section if ladder data is present
    if "sell_ladder_segments" in items.columns:
        # Filter for valid ladder segments (not null, not empty, and valid JSON)
        def has_valid_ladder(seg):
            if pd.isna(seg) or seg == "":
                return False
            try:
                parsed = json.loads(seg)
                return isinstance(parsed, list)  # Allow empty lists as valid
            except (json.JSONDecodeError, TypeError):
                return False

        ladder_mask = items["sell_ladder_segments"].apply(has_valid_ladder)
        ladder_items = items[ladder_mask]
        non_ladder_items = items[~ladder_mask]
    else:
        ladder_items = pd.DataFrame()
        non_ladder_items = items

    if len(ladder_items) > 0:
        # Calculate ladder vs non-ladder comparison metrics
        ladder_avg_p60 = (
            ladder_items["sell_p60"].mean() if "sell_p60" in ladder_items.columns else 0
        )
        non_ladder_avg_p60 = (
            non_ladder_items["sell_p60"].mean()
            if "sell_p60" in non_ladder_items.columns and len(non_ladder_items) > 0
            else 0
        )

        # Get sample ladder segments for display
        sample_segments = None
        if len(ladder_items) > 0 and "sell_ladder_segments" in ladder_items.columns:
            try:
                sample_segments_str = ladder_items["sell_ladder_segments"].iloc[0]
                sample_segments = (
                    json.loads(sample_segments_str) if sample_segments_str else None
                )
            except Exception:
                pass

        md_lines.extend(
            [
                "## Pricing Ladder",
                "",
                f"- **Items with Ladder Pricing:** {len(ladder_items)} ({len(ladder_items)/len(items)*100:.1f}%)",
                f"- **Ladder Avg Sell-through (60d):** {fmt_pct(ladder_avg_p60)}",
                f"- **Standard Avg Sell-through (60d):** {fmt_pct(non_ladder_avg_p60)}",
            ]
        )

        if sample_segments:
            md_lines.extend(["", "**Sample Pricing Schedule:**", ""])
            for i, segment in enumerate(sample_segments):
                md_lines.append(
                    f"- Days {segment['day_from']}-{segment['day_to']}: {fmt_currency(segment['price'])}"
                )

        md_lines.append("")

    md_lines.extend(
        [
            "## Investment Decision",
            "",
        ]
    )

    # Investment recommendation
    if meets_constraints is True:
        md_lines.extend(
            [
                "**PROCEED** - This lot meets the configured investment criteria.",
                "",
                f"The recommended bid of {fmt_currency(recommended_bid)} has a "
                f"{fmt_pct(prob_roi_ge_target)} probability of achieving the target ROI of "
                f"{roi_target if roi_target is not None else 'N/A'}x, which exceeds the Risk Threshold of "
                f"{fmt_prob2(risk_threshold)}.",
            ]
        )
    elif meets_constraints is False:
        md_lines.extend(
            [
                "**PASS** - This lot does not meet the configured investment criteria.",
                "",
                f"No feasible bid was found that achieves the target ROI of "
                f"{roi_target if roi_target is not None else 'N/A'}x with probability >= "
                f"{fmt_prob2(risk_threshold)}. Consider lowering the ROI Target "
                "or Risk Threshold, or look for a different lot.",
            ]
        )
    else:
        md_lines.extend(
            [
                "**REVIEW** - Unable to determine investment recommendation.",
                "",
                "Missing constraint evaluation data. Please check input parameters and optimizer configuration.",
            ]
        )

    # Add Scenario Diffs section if stress data available
    if stress_df is not None and len(stress_df) > 0:
        baseline_row = stress_df[stress_df["scenario"] == "baseline"]
        if len(baseline_row) == 1:
            baseline = baseline_row.iloc[0]
            md_lines.extend(["", "## Scenario Diffs", ""])

            # Table header
            md_lines.extend(
                [
                    "| Scenario | Bid | Δ Bid | Prob ≥ Target | Δ Prob | 60d Cash | Δ Cash |",
                    "|----------|-----|-------|---------------|--------|----------|--------|",
                ]
            )

            # Add baseline row
            md_lines.append(
                f"| **{baseline['scenario']}** | "
                f"{fmt_currency(baseline['bid'])} | - | "
                f"{fmt_pct(baseline['prob_roi_ge_target'])} | - | "
                f"{fmt_currency(baseline['expected_cash_60d'])} | - |"
            )

            # Add stressed scenarios with deltas
            for _, row in stress_df.iterrows():
                if row["scenario"] != "baseline":
                    delta_bid = (
                        row["bid"] - baseline["bid"]
                        if pd.notna(row["bid"]) and pd.notna(baseline["bid"])
                        else None
                    )
                    delta_prob = (
                        row["prob_roi_ge_target"] - baseline["prob_roi_ge_target"]
                        if pd.notna(row["prob_roi_ge_target"])
                        and pd.notna(baseline["prob_roi_ge_target"])
                        else None
                    )
                    delta_cash = (
                        row["expected_cash_60d"] - baseline["expected_cash_60d"]
                        if pd.notna(row["expected_cash_60d"])
                        and pd.notna(baseline["expected_cash_60d"])
                        else None
                    )

                    def fmt_delta_currency(x):
                        if x is None or pd.isna(x):
                            return "N/A"
                        if x >= 0:
                            return f"+{fmt_currency(x)}"
                        else:
                            return f"-{fmt_currency(abs(x))}"

                    def fmt_delta_pct(x):
                        if x is None or pd.isna(x):
                            return "N/A"
                        if x >= 0:
                            return f"+{fmt_pct(x)}"
                        else:
                            return f"-{fmt_pct(abs(x))}"

                    md_lines.append(
                        f"| **{row['scenario']}** | "
                        f"{fmt_currency(row['bid'])} | "
                        f"{fmt_delta_currency(delta_bid)} | "
                        f"{fmt_pct(row['prob_roi_ge_target'])} | "
                        f"{fmt_delta_pct(delta_prob)} | "
                        f"{fmt_currency(row['expected_cash_60d'])} | "
                        f"{fmt_delta_currency(delta_cash)} |"
                    )

    # Add Cache Metrics section if CACHE_METRICS=1 and metrics available
    try:
        from lotgenius.cache_metrics import get_registry, should_emit_metrics

        if should_emit_metrics():
            cache_stats = get_registry().get_all_stats()
            if cache_stats:
                md_lines.extend(["", "## Cache Metrics", ""])

                # Overall summary
                total_hits = sum(stats["hits"] for stats in cache_stats.values())
                total_misses = sum(stats["misses"] for stats in cache_stats.values())
                total_operations = total_hits + total_misses
                overall_hit_ratio = (
                    total_hits / total_operations if total_operations > 0 else 0.0
                )

                md_lines.extend(
                    [
                        f"- **Overall Hit Ratio:** {overall_hit_ratio:.1%}",
                        f"- **Total Cache Operations:** {total_operations:,}",
                        f"- **Total Hits:** {total_hits:,}",
                        f"- **Total Misses:** {total_misses:,}",
                        "",
                    ]
                )

                # Per-cache breakdown if more than one cache
                if len(cache_stats) > 1:
                    md_lines.extend(
                        [
                            "**Cache Breakdown:**",
                            "",
                            "| Cache | Hits | Misses | Hit Ratio | Total Ops |",
                            "|-------|------|--------|-----------|-----------|",
                        ]
                    )

                    for cache_name, stats in sorted(cache_stats.items()):
                        hit_ratio_str = (
                            f"{stats['hit_ratio']:.1%}"
                            if stats["hit_ratio"] > 0
                            else "0.0%"
                        )
                        md_lines.append(
                            f"| {cache_name} | {stats['hits']:,} | {stats['misses']:,} | "
                            f"{hit_ratio_str} | {stats['total_operations']:,} |"
                        )
    except ImportError:
        # cache_metrics module not available, skip section
        pass

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
