from click.testing import CliRunner
from openpyxl import load_workbook

from tests.wvm_fixtures import build_wvm_workbook
from tipout.cli import main
from tipout.roster import load_roster


def test_cli_run_wvm_writes_summary(tiny_wvm_runner_env):
    env = tiny_wvm_runner_env
    res = CliRunner().invoke(
        main,
        [
            "run",
            "--restaurant",
            "wvm",
            "--period",
            "2025-12-29:2026-01-11",
            "--pos",
            str(env["pos_path"]),
            "--config",
            str(env["config_path"]),
        ],
    )
    assert res.exit_code == 0, res.output
    wb = load_workbook(env["summary_path"])
    assert wb["12.29 to 01.11.2026"]["A1"].value.startswith("Watersound Village Market")


def test_cli_run_wvm_with_hours_errors(tiny_wvm_runner_env):
    env = tiny_wvm_runner_env
    res = CliRunner().invoke(
        main,
        [
            "run",
            "--restaurant",
            "wvm",
            "--period",
            "2025-12-29:2026-01-11",
            "--pos",
            str(env["pos_path"]),
            "--config",
            str(env["config_path"]),
            "--hours",
            str(env["pos_path"]),
        ],
    )
    assert res.exit_code != 0
    assert "hours" in res.output.lower()


def test_cli_bootstrap_from_wvm_daily(tmp_path):
    wvm = tmp_path / "wvm.xlsx"
    build_wvm_workbook(wvm)
    out = tmp_path / "roster.xlsx"
    res = CliRunner().invoke(
        main,
        [
            "bootstrap-roster",
            "--from-wvm-daily",
            str(wvm),
            "--out",
            str(out),
        ],
    )
    assert res.exit_code == 0, res.output
    roster = load_roster(out)
    assert "Ornella" in roster.employees
    assert "Cristian Cedeo" in roster.employees


def test_cli_bootstrap_requires_a_source(tmp_path):
    out = tmp_path / "roster.xlsx"
    res = CliRunner().invoke(main, ["bootstrap-roster", "--out", str(out)])
    assert res.exit_code != 0
    assert "exactly one" in res.output.lower()


def test_cli_bootstrap_rejects_both_sources(tmp_path):
    f = tmp_path / "wvm.xlsx"
    build_wvm_workbook(f)
    out = tmp_path / "roster.xlsx"
    res = CliRunner().invoke(
        main,
        [
            "bootstrap-roster",
            "--from-summary",
            str(f),
            "--from-wvm-daily",
            str(f),
            "--out",
            str(out),
        ],
    )
    assert res.exit_code != 0
    assert "exactly one" in res.output.lower()
