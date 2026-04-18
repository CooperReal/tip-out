import json
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

    run(cfg, env["pos_path"], env["hours_path"], period)

    # Summary file created with one tab
    assert cfg.summary_path.exists()
    wb = load_workbook(cfg.summary_path)
    assert wb.sheetnames == ["12.29 to 01.11.2026"]

    ws = wb["12.29 to 01.11.2026"]
    # Col A row 5+ has canonical names in roster order
    canonicals_in_summary = [
        ws.cell(row=r, column=1).value
        for r in range(5, 20)
        if ws.cell(row=r, column=1).value
    ]
    assert canonicals_in_summary == ["Anthony Garcia", "Jake Purvis"]

    # Per-employee files exist
    anthony_path = cfg.per_employee_dir / "Anthony Garcia.xlsx"
    jake_path = cfg.per_employee_dir / "Jake Purvis.xlsx"
    assert anthony_path.exists()
    assert jake_path.exists()

    # Anthony's sheet has the expected date + hours + net_tip
    awb = load_workbook(anthony_path)
    sheet = awb[awb.sheetnames[0]]
    assert sheet.cell(row=5, column=2).value == 7.2       # hours
    assert sheet.cell(row=5, column=9).value == 474.39    # net tip
    assert sheet.cell(row=20, column=2).value == 7.2      # total hours
    assert sheet.cell(row=20, column=9).value == 474.39   # total net tip
    assert sheet.cell(row=23, column=9).value == 474.39 / 7.2  # $/hour


def test_run_raises_on_unknown_name(tiny_runner_env, tmp_path):
    """Roster missing one of the shift names -> UnresolvedNames."""
    from tipout.runner import run, UnresolvedNames
    from tipout.config import Config
    from tipout.period import PayPeriod

    env = tiny_runner_env

    # Rewrite roster to omit Jake
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

    # Patch config to use the broken roster
    cfg = Config.load(env["config_path"])
    cfg.roster_path = broken_roster_path
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))

    with pytest.raises(UnresolvedNames) as exc:
        run(cfg, env["pos_path"], env["hours_path"], period)
    assert "Jake" in exc.value.names


def test_run_without_hours_skips_per_employee(tiny_runner_env):
    from tipout.runner import run
    from tipout.config import Config
    from tipout.period import PayPeriod

    env = tiny_runner_env
    cfg = Config.load(env["config_path"])
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))

    run_id = run(cfg, env["pos_path"], None, period)

    # Summary file exists.
    assert cfg.summary_path.exists()

    # Per-employee dir is empty (or contains no xlsx).
    if cfg.per_employee_dir.exists():
        per_emp_files = list(cfg.per_employee_dir.glob("*.xlsx"))
        assert per_emp_files == []

    # Archive exists with the expected metadata.
    archive_root = cfg.archive_dir / run_id
    assert archive_root.exists()
    run_meta = json.loads((archive_root / "run.json").read_text())
    assert run_meta["hours_provided"] is False

    # No input_hours.xlsx should have been copied.
    assert not (archive_root / "input_hours.xlsx").exists()


def test_cli_run_without_hours(tiny_runner_env):
    from tipout.cli import main

    env = tiny_runner_env
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "run",
            "--period",
            "2025-12-29:2026-01-11",
            "--config",
            str(env["config_path"]),
            "--pos",
            str(env["pos_path"]),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "summary-only" in result.output.lower()
