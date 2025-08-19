import json
from pathlib import Path

import pandas as pd
from click.testing import CliRunner

from backend.cli.optimize_bid import main as cli


def test_optimize_evidence_ndjson(tmp_path):
    """Test optimize_bid writes evidence NDJSON with knobs and results."""
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
    ev = tmp_path / "opt_evidence.jsonl"
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
            "--sims",
            "200",
            "--evidence-out",
            str(ev),
        ],
    )
    assert res.exit_code == 0, res.output
    assert Path(ev).exists()
    line = Path(ev).read_text(encoding="utf-8").splitlines()[0]
    rec = json.loads(line)
    assert rec.get("source") == "optimize:bid"
    assert "result" in rec and "meta" in rec
    assert "bid" in rec["result"]
