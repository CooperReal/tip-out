from datetime import datetime, timezone
from pathlib import Path

from tipout.pos_parser import parse_workbook
from tipout.roster import load_roster
from tipout.name_resolution import resolve_all
from tipout.hours import load_hours, validate_join
from tipout.summary import append_period_tab
from tipout.per_employee import append_period_tab_for_employee
from tipout.period import PayPeriod
from tipout.anomalies import check_all, write_report
from tipout.archive import archive_run, make_run_id


IGNORE_SENTINEL = "__IGNORE__"


class UnresolvedNames(RuntimeError):
    def __init__(self, names: list[str]):
        self.names = names
        super().__init__(f"Unresolved: {names}")


def run(config, pos_path: Path, hours_path: Path | None, period: PayPeriod):
    started_at = datetime.now(timezone.utc)
    run_id = make_run_id()
    roster = load_roster(config.roster_path)
    shift_rows = parse_workbook(pos_path)
    raw_names = {r.raw_name for r in shift_rows}
    resolved, unknown = resolve_all(list(raw_names), roster)
    if unknown:
        raise UnresolvedNames(unknown)
    for r in shift_rows:
        r.canonical_name = resolved[r.raw_name]
    # Drop ignored shift rows after resolution so they don't reach validation/emission.
    shift_rows = [r for r in shift_rows if r.canonical_name != IGNORE_SENTINEL]

    if hours_path is not None:
        hours_entries, hours_unknown = load_hours(hours_path, roster)
        if hours_unknown:
            raise UnresolvedNames(hours_unknown)
        hours_entries = [h for h in hours_entries if h.canonical != IGNORE_SENTINEL]
        validate_join(shift_rows, hours_entries, period.start, period.end)
    else:
        hours_entries = []

    period_rows = [r for r in shift_rows if period.start <= r.date <= period.end]
    append_period_tab(config.summary_path, period, period_rows, roster, hours_entries)

    if hours_path is not None:
        for canonical in sorted({r.canonical_name for r in period_rows}):
            per_emp_path = config.per_employee_dir / f"{canonical}.xlsx"
            append_period_tab_for_employee(
                per_emp_path,
                period,
                canonical,
                [r for r in period_rows if r.canonical_name == canonical],
                [h for h in hours_entries if h.canonical == canonical],
            )

    anomaly_path = config.summary_path.parent / "anomaly_report.xlsx"
    anomalies = check_all(
        period_rows, hours_entries, roster, config.summary_path, period
    )
    write_report(anomaly_path, anomalies, period)
    archive_run(run_id, config, pos_path, hours_path, period, started_at)
    return run_id
