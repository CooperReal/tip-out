from collections import defaultdict
from datetime import date as _date
from pathlib import Path

from tipout.config import Config
from tipout.per_employee import append_period_tab_for_employee
from tipout.period import PayPeriod
from tipout.pos_parser import parse_workbook
from tipout.roster import Roster, load_roster
from tipout.summary import append_period_tab
from tipout.time_clock import parse_time_clock


class UnresolvedNames(RuntimeError):
    """Raised when the POS file contains raw names not present in the roster."""

    def __init__(self, names: list[str]):
        self.names = sorted(set(names))
        super().__init__(f"Unresolved: {self.names}")


class UnresolvedHoursNames(RuntimeError):
    """Raised when the time-clock CSV contains raw names not present in the roster."""

    def __init__(self, names: list[str]):
        self.names = sorted(set(names))
        super().__init__(f"Unresolved hours names: {self.names}")


def _aggregate_hours(
    roster: Roster, csv_path: Path, period: PayPeriod
) -> dict[str, dict[_date, float]]:
    """Resolve raw CSV names to canonicals; sum hours per (canonical, date).

    Raises UnresolvedHoursNames if any raw name in the period fails to resolve.
    """
    rows = parse_time_clock(csv_path)
    rows = [r for r in rows if period.start <= r.date <= period.end]

    unresolved: list[str] = []
    out: dict[str, dict[_date, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        canon = roster.resolve(r.raw_name)
        if canon is None:
            unresolved.append(r.raw_name)
            continue
        out[canon][r.date] += r.hours
    if unresolved:
        raise UnresolvedHoursNames(unresolved)
    # Flatten inner defaultdicts to regular dicts for clean downstream consumption.
    return {canon: dict(by_date) for canon, by_date in out.items()}


def run(
    config: Config,
    pos_path: Path,
    period: PayPeriod,
    hours_path: Path | None = None,
) -> None:
    """Read the POS workbook (and optional time-clock CSV) and append a new pay-period tab."""
    roster = load_roster(config.roster_path)
    shift_rows = parse_workbook(pos_path)
    shift_rows = [r for r in shift_rows if period.start <= r.date <= period.end]

    unknown: list[str] = []
    for r in shift_rows:
        canon = roster.resolve(r.raw_name)
        if canon is None:
            unknown.append(r.raw_name)
        else:
            r.canonical_name = canon
    if unknown:
        raise UnresolvedNames(unknown)

    # Resolve hours BEFORE writing any output: failures must short-circuit
    # with no partial state on disk.
    hours_by_canonical: dict[str, dict[_date, float]] = {}
    if hours_path is not None:
        hours_by_canonical = _aggregate_hours(roster, hours_path, period)

    append_period_tab(config.summary_path, period, shift_rows, roster)

    output_dir = config.summary_path.parent
    canonicals_with_shifts = sorted(
        {r.canonical_name for r in shift_rows if r.canonical_name}
    )
    for canon in canonicals_with_shifts:
        append_period_tab_for_employee(
            output_dir,
            period,
            canon,
            shift_rows,
            hours_by_date=hours_by_canonical.get(canon),
        )
