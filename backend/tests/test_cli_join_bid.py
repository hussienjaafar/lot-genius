import json
from pathlib import Path

import pandas as pd
from click.testing import CliRunner

from backend.cli.join_bid import main as cli


def test_join_bid_one_row(tmp_path):
    """Test join_bid creates single-row lot summary."""
    items = pd.DataFrame(
        [
            {
                "sku_local": "X",
                "est_price_mu": 60.0,
                "est_price_sigma": 12.0,
                "sell_p60": 0.6,
            }
        ]
    )
    opt = {
        "bid": 123.0,
        "roi_p50": 1.4,
        "prob_roi_ge_target": 0.82,
        "expected_cash_60d": 50.0,
    }
    in_csv = tmp_path / "items.csv"
    oj = tmp_path / "opt.json"
    out_csv = tmp_path / "joined.csv"
    items.to_csv(in_csv, index=False)
    Path(oj).write_text(json.dumps(opt), encoding="utf-8")
    res = CliRunner().invoke(
        cli,
        [
            "--items-csv",
            str(in_csv),
            "--opt-json",
            str(oj),
            "--out-csv",
            str(out_csv),
            "--mode",
            "one-row",
        ],
    )
    assert res.exit_code == 0, res.output
    out = pd.read_csv(out_csv)
    assert out.shape[0] == 1 and "recommended_bid" in out.columns


def test_join_bid_broadcast(tmp_path):
    """Test join_bid broadcasts optimizer results to all items."""
    items = pd.DataFrame([{"sku_local": "X"}, {"sku_local": "Y"}])
    opt = {
        "bid": 200.0,
        "roi_p50": 1.3,
        "prob_roi_ge_target": 0.80,
        "expected_cash_60d": 40.0,
    }
    in_csv = tmp_path / "items.csv"
    oj = tmp_path / "opt.json"
    out_csv = tmp_path / "joined.csv"
    items.to_csv(in_csv, index=False)
    Path(oj).write_text(json.dumps(opt), encoding="utf-8")
    res = CliRunner().invoke(
        cli,
        [
            "--items-csv",
            str(in_csv),
            "--opt-json",
            str(oj),
            "--out-csv",
            str(out_csv),
            "--mode",
            "broadcast",
        ],
    )
    assert res.exit_code == 0, res.output
    out = pd.read_csv(out_csv)
    assert "recommended_bid" in out.columns and out.shape[0] == 2


def test_join_bid_one_row_with_targets(tmp_path):
    """Test join_bid one-row mode includes roi_target and risk_threshold when present."""
    items = pd.DataFrame(
        [
            {
                "sku_local": "X",
                "est_price_mu": 60.0,
                "est_price_sigma": 12.0,
                "sell_p60": 0.6,
            }
        ]
    )
    opt = {
        "bid": 123.0,
        "roi_p50": 1.4,
        "prob_roi_ge_target": 0.82,
        "expected_cash_60d": 50.0,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
    }
    in_csv = tmp_path / "items.csv"
    oj = tmp_path / "opt.json"
    out_csv = tmp_path / "joined.csv"
    items.to_csv(in_csv, index=False)
    Path(oj).write_text(json.dumps(opt), encoding="utf-8")
    res = CliRunner().invoke(
        cli,
        [
            "--items-csv",
            str(in_csv),
            "--opt-json",
            str(oj),
            "--out-csv",
            str(out_csv),
            "--mode",
            "one-row",
        ],
    )
    assert res.exit_code == 0, res.output
    out = pd.read_csv(out_csv)
    assert {"roi_target", "risk_threshold"}.issubset(out.columns)


def test_join_bid_broadcast_with_targets(tmp_path):
    """Test join_bid broadcast mode includes roi_target and risk_threshold when present."""
    items = pd.DataFrame([{"sku_local": "X"}, {"sku_local": "Y"}])
    opt = {
        "bid": 200.0,
        "roi_p50": 1.3,
        "prob_roi_ge_target": 0.80,
        "expected_cash_60d": 40.0,
        "roi_target": 1.25,
        "risk_threshold": 0.80,
    }
    in_csv = tmp_path / "items.csv"
    oj = tmp_path / "opt.json"
    out_csv = tmp_path / "joined.csv"
    items.to_csv(in_csv, index=False)
    Path(oj).write_text(json.dumps(opt), encoding="utf-8")
    res = CliRunner().invoke(
        cli,
        [
            "--items-csv",
            str(in_csv),
            "--opt-json",
            str(oj),
            "--out-csv",
            str(out_csv),
            "--mode",
            "broadcast",
        ],
    )
    assert res.exit_code == 0, res.output
    out = pd.read_csv(out_csv)
    assert {"roi_target", "risk_threshold"}.issubset(out.columns)
