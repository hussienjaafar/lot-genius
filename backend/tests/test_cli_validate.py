import json
from pathlib import Path

from click.testing import CliRunner

from backend.cli.validate_manifest import main as cli


def test_cli_includes_pct_and_failures(tmp_path: Path):
    runner = CliRunner()
    res = runner.invoke(cli, ["data/golden_manifests/01_basic.csv", "--show-coverage"])
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert "header_coverage" in payload
    assert "header_coverage_pct" in payload  # added by --show-coverage
    assert "failed_expectations" in payload
    assert isinstance(payload["failed_expectations"], list)
    # golden should have no failed expectations
    assert not payload["failed_expectations"]
