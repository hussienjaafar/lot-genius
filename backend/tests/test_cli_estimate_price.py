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


def test_cli_combines_ledger_in(tmp_path):
    # Build a prior ledger with one record
    prior = tmp_path / "prior.jsonl"
    prior.write_text('{"source":"resolve:test","ok":true}\n', encoding="utf-8")

    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "sku_local": "C1",
                "condition": "New",
                "keepa_price_new_med": 100.0,
                "keepa_offers_count": 3,
            }
        ]
    )
    in_csv = tmp_path / "enriched.csv"
    out_csv = tmp_path / "estimated.csv"
    ledger_out = tmp_path / "combined.jsonl"
    df.to_csv(in_csv, index=False)

    from cli.estimate_price import main as cli
    from click.testing import CliRunner

    res = CliRunner().invoke(
        cli,
        [
            str(in_csv),
            "--ledger-in",
            str(prior),
            "--out-csv",
            str(out_csv),
            "--ledger-out",
            str(ledger_out),
        ],
    )
    assert res.exit_code == 0, res.output
    # Combined file should contain at least 2 lines (prior + new)
    lines = [
        line
        for line in Path(ledger_out).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) >= 2
