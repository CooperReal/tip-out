"""Preflight checks for tipout.

Each check returns a Check record. The CLI command renders them either as
human-readable lines or as JSON. Used to confirm a deployment is healthy
before a pay-period run.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass(frozen=True)
class Check:
    name: str
    status: str  # "pass" | "warn" | "fail"
    detail: str


def run_checks(config_path: Path) -> list[Check]:
    checks: list[Check] = []

    # 1. Python version
    py = sys.version_info
    if (py.major, py.minor) >= (3, 11):
        checks.append(Check("python_version", "pass", f"{py.major}.{py.minor}.{py.micro}"))
    else:
        checks.append(Check(
            "python_version", "fail",
            f"need 3.11+, have {py.major}.{py.minor}.{py.micro}",
        ))

    # 2. openpyxl import
    try:
        import openpyxl  # noqa: F401
        checks.append(Check("openpyxl_import", "pass", openpyxl.__version__))
    except ImportError as e:
        checks.append(Check("openpyxl_import", "fail", str(e)))

    # 3. Config loads
    cfg = None
    if not config_path.exists():
        checks.append(Check("config_loads", "fail", f"not found at {config_path}"))
    else:
        try:
            from tipout.config import Config
            cfg = Config.load(config_path)
            checks.append(Check("config_loads", "pass", f"loaded {config_path.name}"))
        except Exception as e:
            checks.append(Check("config_loads", "fail", f"{type(e).__name__}: {e}"))

    # 4. Roster loads
    if cfg is None:
        checks.append(Check("roster_loads", "warn", "skipped (config failed)"))
    elif not cfg.roster_path.exists():
        checks.append(Check("roster_loads", "fail", f"not found at {cfg.roster_path}"))
    else:
        try:
            from tipout.roster import load_roster
            roster = load_roster(cfg.roster_path)
            checks.append(Check(
                "roster_loads", "pass",
                f"{len(roster.employees)} employees, {len(roster.aliases)} aliases",
            ))
        except Exception as e:
            checks.append(Check("roster_loads", "fail", f"{type(e).__name__}: {e}"))

    # 5. Output directories writable
    if cfg is None:
        checks.append(Check("outputs_writable", "warn", "skipped (config failed)"))
    else:
        issues: list[str] = []
        for label, p in [
            ("summary parent", cfg.summary_path.parent),
            ("per_employee_dir", cfg.per_employee_dir),
            ("archive_dir", cfg.archive_dir),
        ]:
            try:
                p.mkdir(parents=True, exist_ok=True)
                probe = p / ".tipout_doctor_probe"
                probe.write_text("ok")
                probe.unlink()
            except Exception as e:
                issues.append(f"{label}: {type(e).__name__}: {e}")
        if issues:
            checks.append(Check("outputs_writable", "warn", "; ".join(issues)))
        else:
            checks.append(Check("outputs_writable", "pass", "all 3 directories writable"))

    # 6. Regression harness
    try:
        from tipout.regression import list_fixtures, run_fixture
        fixtures = list_fixtures()
        if not fixtures:
            checks.append(Check("regression", "warn", "no fixtures found"))
        else:
            failed = 0
            for fx in fixtures:
                diffs = run_fixture(fx)
                if diffs:
                    failed += 1
            if failed == 0:
                checks.append(Check("regression", "pass", f"{len(fixtures)} fixture(s) green"))
            else:
                checks.append(Check(
                    "regression", "fail",
                    f"{failed}/{len(fixtures)} fixture(s) failed",
                ))
    except Exception as e:
        checks.append(Check("regression", "fail", f"harness error: {type(e).__name__}: {e}"))

    return checks
