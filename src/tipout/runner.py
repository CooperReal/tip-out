from pathlib import Path

from tipout.config import Config
from tipout.per_employee import append_period_tab_for_employee
from tipout.period import PayPeriod
from tipout.pos_parser import parse_workbook
from tipout.roster import load_roster
from tipout.summary import append_period_tab


class UnresolvedNames(RuntimeError):
    """Raised when the POS file contains raw names not present in the roster."""

    def __init__(self, names: list[str]):
        self.names = sorted(set(names))
        super().__init__(f"Unresolved: {self.names}")


def run(config: Config, pos_path: Path, period: PayPeriod) -> None:
    """Read the POS workbook and append a new pay-period tab to the 2-week summary."""
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

    append_period_tab(config.summary_path, period, shift_rows, roster)

    # Per-employee files: one workbook per canonical with at least one shift
    # in the period. Files live alongside the summary, in `per-employee/`.
    output_dir = config.summary_path.parent
    canonicals_with_shifts = sorted(
        {r.canonical_name for r in shift_rows if r.canonical_name}
    )
    for canon in canonicals_with_shifts:
        append_period_tab_for_employee(output_dir, period, canon, shift_rows)
