import json
from pathlib import Path

from click.testing import CliRunner

from tipout.doctor import run_checks


def _by_name(checks):
    return {c.name: c for c in checks}


def test_doctor_all_pass(tiny_runner_env):
    checks = run_checks(tiny_runner_env["config_path"])
    by = _by_name(checks)
    assert by["python_version"].status == "pass"
    assert by["openpyxl_import"].status == "pass"
    assert by["config_loads"].status == "pass"
    assert by["roster_loads"].status == "pass"
    assert by["outputs_writable"].status == "pass"
    # _synthetic fixture lives in the repo and is discovered statically.
    assert by["regression"].status == "pass"


def test_doctor_missing_config(tmp_path):
    missing = tmp_path / "nope.yaml"
    checks = run_checks(missing)
    by = _by_name(checks)
    assert by["config_loads"].status == "fail"
    assert "not found" in by["config_loads"].detail
    assert by["roster_loads"].status == "warn"
    assert by["outputs_writable"].status == "warn"


def test_doctor_json_output(tiny_runner_env):
    from tipout.cli import main
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["doctor", "--config", str(tiny_runner_env["config_path"]), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "status" in payload
    assert "checks" in payload
    assert isinstance(payload["checks"], list)
    assert all({"name", "status", "detail"} <= set(c) for c in payload["checks"])


def test_doctor_exit_code_pass_vs_fail(tmp_path, tiny_runner_env):
    from tipout.cli import main
    runner = CliRunner()

    # Missing config -> fail -> exit 1
    missing = tmp_path / "nope.yaml"
    bad = runner.invoke(main, ["doctor", "--config", str(missing)])
    assert bad.exit_code == 1, bad.output

    # Good config -> pass -> exit 0
    good = runner.invoke(
        main, ["doctor", "--config", str(tiny_runner_env["config_path"])]
    )
    assert good.exit_code == 0, good.output
