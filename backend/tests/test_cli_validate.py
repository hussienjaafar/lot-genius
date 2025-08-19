import json
from pathlib import Path

from cli.validate_manifest import main as cli
from click.testing import CliRunner


def test_cli_includes_pct_and_failures(tmp_path: Path):
    runner = CliRunner()
    res = runner.invoke(cli, ["data/golden_manifests/01_basic.csv", "--show-coverage"])
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["passed"] is True
    assert "header_coverage" in payload
    assert "header_coverage_pct" in payload  # added by --show-coverage
    assert "failed_expectations" in payload
    assert isinstance(payload["failed_expectations"], list)
    # golden should have no failed expectations
    assert not payload["failed_expectations"]


def test_cli_strict_failure(tmp_path):
    from cli.validate_manifest import main as cli
    from click.testing import CliRunner

    bad = "data/golden_manifests/bad_low_coverage.csv"
    runner = CliRunner()
    res = runner.invoke(cli, [bad, "--strict"])
    assert res.exit_code == 2
    # Should still emit JSON we can parse
    import json

    payload = json.loads(res.output)
    assert payload["passed"] is False


def test_cli_good_json_parseable_with_pct_and_bool_success():
    import json

    from cli.validate_manifest import main as cli
    from click.testing import CliRunner

    runner = CliRunner()
    res = runner.invoke(cli, ["data/golden_manifests/01_basic.csv", "--show-coverage"])
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["passed"] is True
    assert "header_coverage_pct" in payload
    # GE results must be JSON-native bools
    assert all(isinstance(r["success"], bool) for r in payload.get("ge_results", []))
