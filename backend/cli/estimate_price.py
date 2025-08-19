import json
from pathlib import Path

import click
import pandas as pd
from lotgenius.pricing import estimate_prices


@click.command()
@click.argument(
    "input_csv", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--cv-fallback",
    default=0.20,
    show_default=True,
    help="Fallback CV (σ/μ) when a source lacks spread info",
)
@click.option(
    "--prior-keepa", default=0.50, show_default=True, help="Source prior for Keepa"
)
@click.option(
    "--prior-ebay",
    default=0.35,
    show_default=True,
    help="Source prior for eBay (unused for now)",
)
@click.option(
    "--prior-other", default=0.15, show_default=True, help="Source prior for Others"
)
@click.option(
    "--use-used-for-nonnew/--no-use-used-for-nonnew",
    default=True,
    show_default=True,
    help="Prefer used median when condition is not New-ish",
)
@click.option(
    "--out-csv",
    type=click.Path(dir_okay=False, path_type=Path),
    default="data/out/estimated_prices.csv",
    show_default=True,
)
@click.option(
    "--ledger-in",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Optional existing ledger to append to (.jsonl or .jsonl.gz)",
)
@click.option(
    "--ledger-out",
    type=click.Path(dir_okay=False, path_type=Path),
    default="data/evidence/price_ledger.jsonl",
    show_default=True,
)
@click.option(
    "--gzip-ledger/--no-gzip-ledger",
    default=False,
    show_default=True,
    help="Compress ledger as JSONL.GZ",
)
def main(
    input_csv: Path,
    cv_fallback: float,
    prior_keepa: float,
    prior_ebay: float,
    prior_other: float,
    use_used_for_nonnew: bool,
    out_csv: Path,
    ledger_in: Path | None,
    ledger_out: Path,
    gzip_ledger: bool,
):
    """
    Compute per-item price distributions (μ, σ, P5/P50/P95) from enriched CSV (Step 6),
    and emit price evidence records. Does not hit the network.
    """
    priors = {"keepa": prior_keepa, "ebay": prior_ebay, "other": prior_other}
    df = pd.read_csv(input_csv)
    df2, price_ledger = estimate_prices(
        df,
        cv_fallback=cv_fallback,
        priors=priors,
        use_used_for_nonnew=use_used_for_nonnew,
    )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df2.to_csv(out_csv, index=False)

    # Combine with prior ledger if provided
    combined_records = []
    if ledger_in:
        try:
            import gzip
            import json as _json

            p = Path(ledger_in)
            if str(p).endswith(".gz"):
                with gzip.open(p, "rt", encoding="utf-8") as f:
                    combined_records.extend(
                        [_json.loads(line) for line in f if line.strip()]
                    )
            else:
                with open(p, "r", encoding="utf-8") as f:
                    combined_records.extend(
                        [_json.loads(line) for line in f if line.strip()]
                    )
        except Exception:
            pass

    # Append new events
    from dataclasses import asdict

    combined_records.extend([asdict(x) for x in price_ledger])

    # Write combined records using the shared writer
    # (writer takes EvidenceRecord list, so we serialize ourselves)
    # Provide a small helper here:
    def _write_jsonl(records, out_path, gzip_output=False):
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if gzip_output and not str(out_path).endswith(".gz"):
            out_path = out_path.with_suffix(out_path.suffix + ".gz")
        opener = (
            (lambda p: gzip.open(p, "wt", encoding="utf-8"))
            if gzip_output
            else (lambda p: open(p, "w", encoding="utf-8"))
        )
        import json as _json

        with opener(out_path) as f:
            for r in records:
                f.write(_json.dumps(r, ensure_ascii=False) + "\n")
        return out_path

    final_ledger_path = _write_jsonl(
        combined_records, ledger_out, gzip_output=gzip_ledger
    )

    payload = {
        "input": str(input_csv),
        "rows": int(df2.shape[0]),
        "estimated": int(pd.notna(df2["est_price_mu"]).sum()),
        "out_csv": str(out_csv),
        "ledger_path": str(final_ledger_path),
        "sources_used_sample": df2["est_price_sources"].dropna().head(3).tolist(),
    }
    click.echo(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
