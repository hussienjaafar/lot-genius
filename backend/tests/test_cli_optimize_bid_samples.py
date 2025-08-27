import json

import pandas as pd
from click.testing import CliRunner

from backend.cli.optimize_bid import main as cli


def _mkdf():
    return pd.DataFrame(
        [
            {
                "sku_local": "X",
                "est_price_mu": 60.0,
                "est_price_sigma": 12.0,
                "sell_p60": 0.6,
            }
        ]
    )


def test_compact_output_without_flag(tmp_path):
    """Test default behavior omits revenue and cash_60d arrays."""
    df = _mkdf()
    in_csv = tmp_path / "in.csv"
    outp = tmp_path / "opt.json"
    df.to_csv(in_csv, index=False)
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(outp),
            "--lo",
            "0",
            "--hi",
            "1000",
            "--sims",
            "50",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(outp.read_text(encoding="utf-8"))
    assert "revenue" not in data and "cash_60d" not in data and "roi" not in data


def test_full_output_with_flag(tmp_path):
    """Test --include-samples includes revenue, cash_60d, and roi arrays."""
    df = _mkdf()
    in_csv = tmp_path / "in.csv"
    outp = tmp_path / "opt_full.json"
    df.to_csv(in_csv, index=False)
    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--out-json",
            str(outp),
            "--lo",
            "0",
            "--hi",
            "1000",
            "--sims",
            "50",
            "--include-samples",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(outp.read_text(encoding="utf-8"))
    assert "revenue" in data and "cash_60d" in data and "roi" in data
    assert (
        len(data["revenue"]) > 0 and len(data["cash_60d"]) > 0 and len(data["roi"]) > 0
    )
