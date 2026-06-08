from collections import defaultdict
from datetime import date as _date
from pathlib import Path

from tipout import wvm_parser
from tipout.config import Config
from tipout.per_employee import append_period_tab_for_employee
from tipout.period import PayPeriod
from tipout.pos_parser import parse_workbook
from tipout.roster import Roster, load_roster
from tipout.summary import append_period_tab
from tipout.time_clock import parse_time_clock

_PARSERS = {"sd": parse_workbook, "wvm": wvm_parser.parse_workbook}
_DISPLAY = {"sd": "Surfing Deer", "wvm": "Watersound Village Market"}


class UnresolvedNames(RuntimeError):
    """Raised when the POS file contains raw names not present in the roster."""

    def __init__(self, names: list[str]):
        self.names = sorted(set(names))
        super().__init__(f"Unresolved: {self.names}")


class UnresolvedHoursNames(RuntimeError):
    """Raised when the time-clock CSV contains raw names not present in the roster."""

    def __init__(self, names: list[str]):
        self.names = sorted(set(names))
        super().__init__(f"Unresolved (hours): {self.names}")


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


class DanglingAlias(RuntimeError):
    """A resolved canonical name is not present in the roster's Employees sheet."""

    def __init__(self, names: list[str]):
        self.names = sorted(set(names))
        super().__init__(f"Dangling alias target(s) not in Employees: {self.names}")


class L56Mismatch(RuntimeError):
    """A day's summary net-tip total disagrees with the WVM sheet's own total."""

    def __init__(self, day: _date, written: float, expected: float):
        self.day, self.written, self.expected = day, written, expected
        super().__init__(
            f"WVM integrity check failed for {day}: summary total {written:.2f} "
            f"!= sheet total {expected:.2f}"
        )


def _check_l56(pos_path: Path, period: PayPeriod, shift_rows, roster: Roster) -> None:
    """Each in-period day's summary net-tip total must equal that tab's own total."""
    expected = wvm_parser.read_day_net_totals(pos_path)
    written: dict[_date, float] = defaultdict(float)
    for r in shift_rows:
        if r.canonical_name in roster.employees:
            written[r.date] += r.net_tip
    for d, exp in expected.items():
        if not (period.start <= d <= period.end):
            continue
        got = written.get(d, 0.0)
        if abs(round(got, 2) - round(exp, 2)) > 0.005:
            raise L56Mismatch(d, got, exp)


def run(
    config: Config,
    pos_path: Path,
    period: PayPeriod,
    hours_path: Path | None = None,
    restaurant: str = "sd",
) -> None:
    """Read the POS workbook and append a new pay-period tab.

    restaurant selects the parser ('sd' or 'wvm'). For 'wvm' the summary is the only
    deliverable (no per-employee files) and --hours is not supported.
    """
    if restaurant not in _PARSERS:
        raise ValueError(f"Unknown restaurant {restaurant!r} (expected one of {sorted(_PARSERS)})")
    if restaurant == "wvm" and hours_path is not None:
        raise ValueError("--hours is not supported for WVM (summary only)")

    roster = load_roster(config.roster_path)
    shift_rows = _PARSERS[restaurant](pos_path)
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

    dangling = [
        r.canonical_name
        for r in shift_rows
        if r.canonical_name is not None and r.canonical_name not in roster.employees
    ]
    if dangling:
        raise DanglingAlias(dangling)

    if restaurant == "wvm":
        _check_l56(pos_path, period, shift_rows, roster)

    # Resolve hours BEFORE writing any output: failures must short-circuit
    # with no partial state on disk.
    hours_by_canonical: dict[str, dict[_date, float]] = {}
    if hours_path is not None:
        hours_by_canonical = _aggregate_hours(roster, hours_path, period)

    append_period_tab(
        config.summary_path,
        period,
        shift_rows,
        roster,
        restaurant_name=_DISPLAY[restaurant],
    )

    if restaurant == "wvm":
        return  # summary only

    output_dir = config.summary_path.parent
    canonicals_with_shifts = sorted({r.canonical_name for r in shift_rows if r.canonical_name})
    for canon in canonicals_with_shifts:
        append_period_tab_for_employee(
            output_dir,
            period,
            canon,
            shift_rows,
            hours_by_date=hours_by_canonical.get(canon),
        )
