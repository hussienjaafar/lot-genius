import json
from pathlib import Path

import pandas as pd
from click.testing import CliRunner

from backend.cli.estimate_price import main as cli


def test_cli_price_evidence_category_fallback(tmp_path):
    """Test that CLI writes fallback category 'default' to price_evidence.jsonl when category_hint not in priors."""
    # Priors that only contain "default"
    priors_path = tmp_path / "priors_default_only.json"
    priors_path.write_text(
        json.dumps({"default": {"p20_floor_abs": None, "p20_floor_frac_of_mu": 0.0}}),
        encoding="utf-8",
    )

    # Enriched CSV with a category hint NOT present in priors
    df = pd.DataFrame(
        [
            {
                "sku_local": "W1",
                "condition": "New",
                "category_hint": "widgets_not_in_priors",
                "keepa_price_new_med": 40.0,
                "keepa_offers_count": 4,
            }
        ]
    )
    in_csv = tmp_path / "enriched.csv"
    out_csv = tmp_path / "estimated.csv"
    ledger_out = tmp_path / "price_ledger.jsonl"
    evidence_out = tmp_path / "price_evidence.jsonl"
    df.to_csv(in_csv, index=False)

    # Run CLI
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--category-priors",
            str(priors_path),
            "--salvage-floor-frac",
            "0.0",
            "--out-csv",
            str(out_csv),
            "--ledger-out",
            str(ledger_out),
            "--price-evidence-out",
            str(evidence_out),
        ],
    )
    assert res.exit_code == 0, res.output

    # Verify price_evidence.jsonl reflects category fallback
    first_line = Path(evidence_out).read_text(encoding="utf-8").splitlines()[0]
    rec = json.loads(first_line)
    assert rec.get("est_price_category") == "default"  # <- fallback applied
    assert "sources" in rec and isinstance(rec["sources"], list)  # sanity check
    # Optional: these keys exist (may be null where appropriate)
    for k in [
        "est_price_mu",
        "est_price_sigma",
        "est_price_p5",
        "est_price_p5_floored",
    ]:
        assert k in rec
