from datetime import date

import pytest
from click.testing import CliRunner
from openpyxl import Workbook, load_workbook


def test_run_end_to_end(tiny_runner_env):
    from tipout.runner import run
    from tipout.config import Config
    from tipout.period import PayPeriod

    env = tiny_runner_env
    cfg = Config.load(env["config_path"])
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))

    run(cfg, env["pos_path"], period)

    assert cfg.summary_path.exists()
    wb = load_workbook(cfg.summary_path)
    assert wb.sheetnames == ["12.29 to 01.11.2026"]

    ws = wb["12.29 to 01.11.2026"]
    canonicals = [
        ws.cell(row=r, column=1).value
        for r in range(5, 20)
        if ws.cell(row=r, column=1).value
    ]
    assert canonicals == ["Anthony Garcia", "Jake Purvis"]


def test_run_raises_on_unknown_name(tiny_runner_env, tmp_path):
    from tipout.runner import run, UnresolvedNames
    from tipout.config import Config
    from tipout.period import PayPeriod

    env = tiny_runner_env

    broken_roster_path = tmp_path / "broken_roster.xlsx"
    wb = Workbook()
    emp = wb.active
    emp.title = "Employees"
    emp.append(["Canonical Name", "Role", "Active From", "Active To", "Notes"])
    emp.append(["Anthony Garcia", "server", date(2025, 1, 1), None, ""])
    aliases = wb.create_sheet("Name Aliases")
    aliases.append(["Raw Name", "Canonical Name"])
    aliases.append(["Anthony", "Anthony Garcia"])
    wb.save(broken_roster_path)

    cfg = Config.load(env["config_path"])
    cfg.roster_path = broken_roster_path
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))

    with pytest.raises(UnresolvedNames) as exc:
        run(cfg, env["pos_path"], period)
    assert "Jake" in exc.value.names


def test_cli_run_writes_unknowns_file_and_exits_nonzero(tiny_runner_env, tmp_path):
    """When a raw name is missing from the roster, the CLI writes unknown_names.txt and exits 1."""
    from tipout.cli import main

    env = tiny_runner_env

    # Replace the roster with one that omits Jake.
    broken_roster = tmp_path / "broken_roster.xlsx"
    wb = Workbook()
    emp = wb.active
    emp.title = "Employees"
    emp.append(["Canonical Name", "Role", "Active From", "Active To", "Notes"])
    emp.append(["Anthony Garcia", "server", date(2025, 1, 1), None, ""])
    aliases = wb.create_sheet("Name Aliases")
    aliases.append(["Raw Name", "Canonical Name"])
    aliases.append(["Anthony", "Anthony Garcia"])
    wb.save(broken_roster)

    # Point config at the broken roster.
    import yaml
    cfg_text = env["config_path"].read_text(encoding="utf-8")
    cfg_data = yaml.safe_load(cfg_text)
    cfg_data["roster_path"] = str(broken_roster)
    env["config_path"].write_text(yaml.safe_dump(cfg_data), encoding="utf-8")

    result = CliRunner().invoke(
        main,
        [
            "run",
            "--period", "2025-12-29:2026-01-11",
            "--config", str(env["config_path"]),
            "--pos", str(env["pos_path"]),
        ],
    )
    assert result.exit_code == 1
    unknowns_path = env["config_path"].parent / "unknown_names.txt"
    assert unknowns_path.exists()
    assert "Jake" in unknowns_path.read_text(encoding="utf-8")


def test_cli_run_success(tiny_runner_env):
    from tipout.cli import main

    env = tiny_runner_env
    result = CliRunner().invoke(
        main,
        [
            "run",
            "--period", "2025-12-29:2026-01-11",
            "--config", str(env["config_path"]),
            "--pos", str(env["pos_path"]),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Done." in result.output
