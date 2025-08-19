import json
from pathlib import Path

import pandas as pd
from cli.estimate_price import main as cli
from click.testing import CliRunner


def test_cli_estimate_prices(tmp_path):
    df = pd.DataFrame(
        [
            {
                "sku_local": "A1",
                "condition": "Used-Good",
                "keepa_price_used_med": 120.0,
                "keepa_offers_count": 8,
            },
            {
                "sku_local": "A2",
                "condition": "New",
                "keepa_price_new_med": 200.0,
                "keepa_offers_count": 4,
            },
            {"sku_local": "A3", "condition": "New"},  # missing stats
        ]
    )
    in_csv = tmp_path / "enriched.csv"
    out_csv = tmp_path / "estimated.csv"
    ledger_out = tmp_path / "price_ledger.jsonl"
    df.to_csv(in_csv, index=False)

    runner = CliRunner()
    res = runner.invoke(
        cli,
        [
            str(in_csv),
            "--cv-fallback",
            "0.2",
            "--use-used-for-nonnew",
            "--out-csv",
            str(out_csv),
            "--ledger-out",
            str(ledger_out),
        ],
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["estimated"] >= 2
    assert Path(payload["out_csv"]).exists()
    assert Path(payload["ledger_path"]).exists()
