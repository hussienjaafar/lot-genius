import json
from pathlib import Path

import pandas as pd
from click.testing import CliRunner

from backend.cli.optimize_bid import main as cli


def test_cli_optimize_bid_smoke(tmp_path):
    """Test CLI basic functionality and output structure."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "A1",
                "est_price_mu": 60.0,
                "est_price_sigma": 12.0,
                "sell_p60": 0.6,
            }
        ]
    )
    in_csv = tmp_path / "in.csv"
    out_json = tmp_path / "opt.json"
    df.to_csv(in_csv, index=False)

    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(out_json),
            "--lo",
            "0",
            "--hi",
            "500",
            "--roi-target",
            "1.25",
            "--risk-threshold",
            "0.80",
            "--sims",
            "500",
        ],
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert Path(payload["out_json"]).exists()
    assert "recommended_bid" in payload and "roi_p50" in payload


def test_cli_with_cash_constraint(tmp_path):
    """Test CLI with min-cash-60d constraint."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "B1",
                "est_price_mu": 80.0,
                "est_price_sigma": 15.0,
                "sell_p60": 0.7,
            }
        ]
    )
    in_csv = tmp_path / "in.csv"
    out_json = tmp_path / "opt.json"
    df.to_csv(in_csv, index=False)

    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(out_json),
            "--lo",
            "0",
            "--hi",
            "300",
            "--min-cash-60d",
            "20.0",
            "--sims",
            "500",
        ],
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert "expected_cash_60d" in payload
    assert "meets_constraints" in payload


def test_cli_output_json_structure(tmp_path):
    """Test that output JSON has all expected fields."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "C1",
                "est_price_mu": 40.0,
                "est_price_sigma": 8.0,
                "sell_p60": 0.5,
            }
        ]
    )
    in_csv = tmp_path / "in.csv"
    out_json = tmp_path / "opt.json"
    df.to_csv(in_csv, index=False)

    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(out_json),
            "--lo",
            "0",
            "--hi",
            "200",
            "--sims",
            "300",
        ],
    )
    assert res.exit_code == 0, res.output

    # Check JSON file contents
    with open(out_json, "r", encoding="utf-8") as f:
        full_result = json.load(f)

    expected_fields = [
        "bid",
        "roi_p5",
        "roi_p50",
        "roi_p95",
        "prob_roi_ge_target",
        "expected_cash_60d",
        "meets_constraints",
        "iterations",
        "timestamp",
    ]
    for field in expected_fields:
        assert field in full_result, f"Missing field {field} in output JSON"
