"""Test that estimate_sell CLI respects SELLTHROUGH_HORIZON_DAYS from environment."""

import json
import subprocess
import tempfile
from pathlib import Path

import pandas as pd


def test_estimate_sell_cli_env_days_default(monkeypatch):
    """Test estimate_sell CLI uses environment SELLTHROUGH_HORIZON_DAYS as default."""
    # Set custom environment value
    monkeypatch.setenv("SELLTHROUGH_HORIZON_DAYS", "45")

    # Create a minimal test CSV
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        # Create minimal CSV with required columns for sell estimation
        df = pd.DataFrame(
            [
                {
                    "sku_local": "TEST-001",
                    "title": "Test Item",
                    "keepa_salesrank_med": 50000,
                    "keepa_offers_count": 5,
                    "est_price_mu": 50.0,
                    "est_price_sigma": 10.0,
                    "est_price_p50": 50.0,
                }
            ]
        )
        df.to_csv(f.name, index=False)
        input_csv = f.name

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            out_csv = f.name

        try:
            # Run the CLI command (should use 45 days from environment)
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "backend.cli.estimate_sell",
                    input_csv,
                    "--out-csv",
                    out_csv,
                ],
                capture_output=True,
                text=True,
                cwd="C:/Users/Husse/lot-genius",
            )

            # Check that command succeeded
            assert (
                result.returncode == 0
            ), f"Command failed with stderr: {result.stderr}"

            # The output should show days=45 in the printed payload or evidence
            # Since we don't have evidence output in this simple test, let's check the output CSV
            # was created and contains the expected sell_p60 column
            assert Path(out_csv).exists(), "Output CSV should be created"

            output_df = pd.read_csv(out_csv)
            assert (
                "sell_p60" in output_df.columns
            ), "Output should contain sell_p60 column"
            assert len(output_df) == 1, "Should have one row of output"

            # Verify the sell_p60 value is reasonable (between 0 and 1)
            sell_p60 = output_df["sell_p60"].iloc[0]
            assert (
                0 < sell_p60 <= 1
            ), f"sell_p60 should be between 0 and 1, got {sell_p60}"

        finally:
            # Clean up output file
            if Path(out_csv).exists():
                Path(out_csv).unlink()

    finally:
        # Clean up input file
        if Path(input_csv).exists():
            Path(input_csv).unlink()


def test_estimate_sell_cli_env_days_with_evidence(monkeypatch):
    """Test estimate_sell CLI env days with evidence output to verify the days parameter."""
    # Set custom environment value
    monkeypatch.setenv("SELLTHROUGH_HORIZON_DAYS", "45")

    # Create a minimal test CSV
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(
            [
                {
                    "sku_local": "TEST-002",
                    "title": "Test Item 2",
                    "keepa_salesrank_med": 25000,
                    "keepa_offers_count": 3,
                    "est_price_mu": 75.0,
                    "est_price_sigma": 15.0,
                    "est_price_p50": 75.0,
                }
            ]
        )
        df.to_csv(f.name, index=False)
        input_csv = f.name

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            out_csv = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            evidence_out = f.name

        try:
            # Run the CLI command with evidence output
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "backend.cli.estimate_sell",
                    input_csv,
                    "--out-csv",
                    out_csv,
                    "--evidence-out",
                    evidence_out,
                ],
                capture_output=True,
                text=True,
                cwd="C:/Users/Husse/lot-genius",
            )

            # Check that command succeeded
            assert (
                result.returncode == 0
            ), f"Command failed with stderr: {result.stderr}"

            # Check evidence file was created and contains the expected days parameter
            assert Path(evidence_out).exists(), "Evidence JSONL should be created"

            with open(evidence_out, "r") as f:
                evidence_lines = f.readlines()

            # Should have at least one evidence record
            assert len(evidence_lines) > 0, "Should have evidence records"

            # Parse the first evidence record and check for days=45
            first_evidence = json.loads(evidence_lines[0])

            # Look for days parameter in the evidence meta data
            assert "meta" in first_evidence, "Evidence should have meta field"
            meta = first_evidence["meta"]
            assert (
                "days" in meta
            ), f"Evidence meta should contain days field, got keys: {list(meta.keys())}"
            assert (
                meta["days"] == 45
            ), f"Expected days=45 in evidence, got {meta['days']}"

        finally:
            # Clean up files
            for path in [out_csv, evidence_out]:
                if Path(path).exists():
                    Path(path).unlink()

    finally:
        # Clean up input file
        if Path(input_csv).exists():
            Path(input_csv).unlink()


def test_estimate_sell_cli_explicit_days_override():
    """Test that explicit --days parameter still works and overrides environment."""
    # Create a minimal test CSV
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(
            [
                {
                    "sku_local": "TEST-003",
                    "title": "Test Item 3",
                    "keepa_salesrank_med": 75000,
                    "keepa_offers_count": 8,
                    "est_price_mu": 25.0,
                    "est_price_sigma": 5.0,
                    "est_price_p50": 25.0,
                }
            ]
        )
        df.to_csv(f.name, index=False)
        input_csv = f.name

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            out_csv = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            evidence_out = f.name

        try:
            # Run the CLI command with explicit --days=90 (should override environment)
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "backend.cli.estimate_sell",
                    input_csv,
                    "--out-csv",
                    out_csv,
                    "--evidence-out",
                    evidence_out,
                    "--days",
                    "90",
                ],
                capture_output=True,
                text=True,
                cwd="C:/Users/Husse/lot-genius",
            )

            # Check that command succeeded
            assert (
                result.returncode == 0
            ), f"Command failed with stderr: {result.stderr}"

            # Check evidence contains days=90 (explicit override)
            assert Path(evidence_out).exists(), "Evidence JSONL should be created"

            with open(evidence_out, "r") as f:
                evidence_lines = f.readlines()

            assert len(evidence_lines) > 0, "Should have evidence records"
            first_evidence = json.loads(evidence_lines[0])

            meta = first_evidence["meta"]
            assert meta["days"] == 90, f"Expected explicit days=90, got {meta['days']}"

        finally:
            # Clean up files
            for path in [out_csv, evidence_out]:
                if Path(path).exists():
                    Path(path).unlink()

    finally:
        # Clean up input file
        if Path(input_csv).exists():
            Path(input_csv).unlink()
