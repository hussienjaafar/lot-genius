from pathlib import Path

import pandas as pd
from click.testing import CliRunner

from backend.cli.sweep_bid import main as cli


def test_sweep_bid_outputs(tmp_path):
    """Test sweep_bid creates output CSV with required columns."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "S1",
                "est_price_mu": 60.0,
                "est_price_sigma": 12.0,
                "sell_p60": 0.6,
            }
        ]
    )
    in_csv = tmp_path / "in.csv"
    out_csv = tmp_path / "sweep.csv"
    df.to_csv(in_csv, index=False)
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-csv",
            str(out_csv),
            "--lo",
            "0",
            "--hi",
            "200",
            "--step",
            "50",
            "--sims",
            "200",
        ],
    )
    assert res.exit_code == 0, res.output
    assert Path(out_csv).exists()
    rows = pd.read_csv(out_csv)
    assert set(
        [
            "bid",
            "prob_roi_ge_target",
            "roi_p50",
            "expected_cash_60d",
            "meets_constraints",
        ]
    ).issubset(rows.columns)
    assert rows.shape[0] >= 3
