import gzip
import json

import pandas as pd
from backend.cli.estimate_price import main as cli
from click.testing import CliRunner


def test_cli_exports_price_evidence_ndjson(tmp_path):
    """Test that CLI exports compact price evidence NDJSON when requested."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "A1",
                "condition": "New",
                "category": "Electronics",
                "keepa_price_new_med": 120.0,
                "keepa_offers_count": 8,
            },
            {
                "sku_local": "A2",
                "condition": "Used-Good",
                "category": "Books",
                "keepa_price_used_med": 25.0,
                "keepa_offers_count": 3,
            },
            {"sku_local": "A3", "condition": "New"},  # missing stats
        ]
    )

    in_csv = tmp_path / "enriched.csv"
    out_csv = tmp_path / "estimated.csv"
    ledger_out = tmp_path / "price_ledger.jsonl"
    evidence_out = tmp_path / "price_evidence.ndjson"
    category_priors = tmp_path / "category_priors.json"

    # Create category priors file
    category_priors.write_text(
        json.dumps(
            {
                "Electronics": {"p20_floor_abs": 15.0, "p20_floor_frac_of_mu": 0.1},
                "Books": {"p20_floor_abs": None, "p20_floor_frac_of_mu": 0.2},
            }
        )
    )

    df.to_csv(in_csv, index=False)

    runner = CliRunner()
    res = runner.invoke(
        cli,
        [
            str(in_csv),
            "--cv-fallback",
            "0.2",
            "--out-csv",
            str(out_csv),
            "--ledger-out",
            str(ledger_out),
            "--category-priors",
            str(category_priors),
            "--salvage-floor-frac",
            "0.05",
            "--price-evidence-out",
            str(evidence_out),
        ],
    )

    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)

    # Check that price evidence file was created
    assert evidence_out.exists()
    assert "price_evidence_path" in payload
    assert payload["price_evidence_path"] == str(evidence_out)

    # Read and verify evidence content
    evidence_lines = evidence_out.read_text(encoding="utf-8").strip().split("\n")
    evidence_records = [json.loads(line) for line in evidence_lines if line.strip()]

    # Should have records for rows with successful estimates (A1, A2, not A3)
    assert len(evidence_records) == 2

    # Check first record (Electronics with floor)
    rec1 = evidence_records[0]
    assert rec1["row_index"] == 0
    assert rec1["sku_local"] == "A1"
    assert "est_price_mu" in rec1
    assert "est_price_p5" in rec1
    assert "est_price_p5_floored" in rec1
    assert rec1["est_price_category"] == "Electronics"

    # Check second record (Books)
    rec2 = evidence_records[1]
    assert rec2["row_index"] == 1
    assert rec2["sku_local"] == "A2"
    assert rec2["est_price_category"] == "Books"

    # Verify compact format (no null values present)
    for record in evidence_records:
        for value in record.values():
            assert value is not None


def test_cli_exports_gzipped_price_evidence(tmp_path):
    """Test that CLI exports gzipped price evidence when requested."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "B1",
                "condition": "New",
                "keepa_price_new_med": 100.0,
                "keepa_offers_count": 5,
            }
        ]
    )

    in_csv = tmp_path / "enriched.csv"
    out_csv = tmp_path / "estimated.csv"
    ledger_out = tmp_path / "price_ledger.jsonl"
    evidence_out = tmp_path / "price_evidence.ndjson"

    df.to_csv(in_csv, index=False)

    runner = CliRunner()
    res = runner.invoke(
        cli,
        [
            str(in_csv),
            "--out-csv",
            str(out_csv),
            "--ledger-out",
            str(ledger_out),
            "--price-evidence-out",
            str(evidence_out),
            "--gzip-evidence",
        ],
    )

    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)

    # Check that gzipped file was created
    expected_gz_path = evidence_out.with_suffix(evidence_out.suffix + ".gz")
    assert expected_gz_path.exists()
    assert payload["price_evidence_path"] == str(expected_gz_path)

    # Verify we can read the gzipped content
    with gzip.open(expected_gz_path, "rt", encoding="utf-8") as f:
        evidence_content = f.read().strip()

    evidence_lines = evidence_content.split("\n")
    evidence_records = [json.loads(line) for line in evidence_lines if line.strip()]
    assert len(evidence_records) == 1
    assert evidence_records[0]["sku_local"] == "B1"


def test_cli_no_price_evidence_when_not_requested(tmp_path):
    """Test that CLI doesn't export price evidence when not requested."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "C1",
                "condition": "New",
                "keepa_price_new_med": 80.0,
                "keepa_offers_count": 4,
            }
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
            "--out-csv",
            str(out_csv),
            "--ledger-out",
            str(ledger_out),
            # No --price-evidence-out flag
        ],
    )

    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)

    # Check that price evidence path is not in payload
    assert "price_evidence_path" not in payload


def test_cli_price_evidence_fields(tmp_path):
    """Test that price evidence includes all expected fields."""
    df = pd.DataFrame(
        [
            {
                "sku_local": "A1",
                "condition": "New",
                "category_hint": "electronics",
                "keepa_price_new_med": 40.0,
                "keepa_offers_count": 5,
            }
        ]
    )

    in_csv = tmp_path / "enriched.csv"
    out_csv = tmp_path / "estimated.csv"
    ledger_out = tmp_path / "price_ledger.jsonl"
    evidence_out = tmp_path / "price_evidence.jsonl"
    df.to_csv(in_csv, index=False)

    from pathlib import Path

    runner = CliRunner()
    res = runner.invoke(
        cli,
        [
            str(in_csv),
            "--category-priors",
            "backend/tests/fixtures/category_priors.json",
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
    line = Path(evidence_out).read_text(encoding="utf-8").splitlines()[0]
    rec = json.loads(line)
    for k in [
        "est_price_mu",
        "est_price_sigma",
        "est_price_p5",
        "est_price_p5_floored",
        "est_price_category",
        "sources",
    ]:
        assert k in rec
