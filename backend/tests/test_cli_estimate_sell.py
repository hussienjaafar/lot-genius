import json
from pathlib import Path

import pandas as pd
from click.testing import CliRunner

from backend.cli.estimate_sell import main as cli


def test_cli_estimate_sell_outputs(tmp_path):
    """Test that CLI produces expected outputs with proper structure."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "S1",
                "keepa_sales_rank_med": 60000,
                "keepa_offers_count": 5,
                "est_price_mu": 60.0,
                "est_price_sigma": 12.0,
                "est_price_p50": 60.0,
            }
        ]
    )
    in_csv = tmp_path / "in.csv"
    out_csv = tmp_path / "out.csv"
    ev = tmp_path / "sell_evidence.jsonl"
    df.to_csv(in_csv, index=False)

    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-csv",
            str(out_csv),
            "--evidence-out",
            str(ev),
            "--days",
            "60",
            "--list-price-mode",
            "p50",
            "--list-price-multiplier",
            "1.0",
        ],
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert Path(payload["out_csv"]).exists()
    assert Path(payload["sell_evidence_path"]).exists()

    # Check output CSV has expected columns
    out_df = pd.read_csv(out_csv)
    expected_cols = [
        "sell_p60",
        "sell_hazard_daily",
        "sell_ptm_z",
        "sell_rank_used",
        "sell_offers_used",
    ]
    for col in expected_cols:
        assert col in out_df.columns

    # Check evidence NDJSON structure
    with open(ev, "r", encoding="utf-8") as f:
        line = f.readline().strip()
        evidence = json.loads(line)
        assert evidence["source"] == "sell:estimate"
        assert evidence["ok"] is True
        assert "meta" in evidence


def test_cli_gzip_evidence(tmp_path):
    """Test that gzipped evidence output works."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "S2",
                "keepa_sales_rank_med": 80000,
                "keepa_offers_count": 3,
                "est_price_mu": 40.0,
                "est_price_sigma": 8.0,
                "est_price_p50": 40.0,
            }
        ]
    )
    in_csv = tmp_path / "in.csv"
    out_csv = tmp_path / "out.csv"
    ev = tmp_path / "sell_evidence.jsonl"
    df.to_csv(in_csv, index=False)

    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-csv",
            str(out_csv),
            "--evidence-out",
            str(ev),
            "--gzip-evidence",
            "--days",
            "30",
        ],
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)

    # Should create .gz file
    assert payload["sell_evidence_path"].endswith(".gz")
    assert Path(payload["sell_evidence_path"]).exists()


def test_cli_no_evidence_out(tmp_path):
    """Test CLI works without evidence output."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "S3",
                "keepa_sales_rank_med": 100000,
                "keepa_offers_count": 10,
                "est_price_mu": 30.0,
                "est_price_sigma": 6.0,
                "est_price_p50": 30.0,
            }
        ]
    )
    in_csv = tmp_path / "in.csv"
    out_csv = tmp_path / "out.csv"
    df.to_csv(in_csv, index=False)

    res = CliRunner().invoke(cli, [str(in_csv), "--out-csv", str(out_csv)])
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["sell_evidence_path"] is None
    assert Path(payload["out_csv"]).exists()

    # Verify data sanity
    out_df = pd.read_csv(out_csv)
    assert 0.0 <= out_df.loc[0, "sell_p60"] <= 1.0
