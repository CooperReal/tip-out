from datetime import date as _date

from click.testing import CliRunner
from openpyxl import load_workbook

from tipout.cli import main


def test_cli_run_wvm_writes_summary(tiny_wvm_runner_env):
    env = tiny_wvm_runner_env
    res = CliRunner().invoke(main, [
        "run", "--restaurant", "wvm",
        "--period", "2025-12-29:2026-01-11",
        "--pos", str(env["pos_path"]),
        "--config", str(env["config_path"]),
    ])
    assert res.exit_code == 0, res.output
    wb = load_workbook(env["summary_path"])
    assert wb["12.29 to 01.11.2026"]["A1"].value.startswith("Watersound Village Market")


def test_cli_run_wvm_with_hours_errors(tiny_wvm_runner_env):
    env = tiny_wvm_runner_env
    res = CliRunner().invoke(main, [
        "run", "--restaurant", "wvm",
        "--period", "2025-12-29:2026-01-11",
        "--pos", str(env["pos_path"]),
        "--config", str(env["config_path"]),
        "--hours", str(env["pos_path"]),
    ])
    assert res.exit_code != 0
    assert "hours" in res.output.lower()
