from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from tipout.period import PayPeriod
from tipout.pos_parser import ShiftRow
from tipout.roster import Roster


def build_grid(
    period: PayPeriod, shift_rows: list[ShiftRow], roster: Roster
) -> list[list[Any]]:
    """
    Return a 2D grid of cell values for the 2-week summary tab. Rows indexed from 0
    (= Excel row 1). None denotes a blank cell.

    Only shift rows within the period and with a resolved canonical_name are considered.
    Employees appear in the order they appear in roster.employees (dict insertion =
    xlsx row order).
    """
    # Filter to period, require canonical_name.
    in_period = [
        r
        for r in shift_rows
        if period.start <= r.date <= period.end and r.canonical_name
    ]

    # Group by canonical: {canonical: {date: summed net_tip}}
    by_emp_date: dict[str, dict[date, float]] = defaultdict(dict)
    # Track most-recent raw-name per canonical (by date; lexicographic tiebreak).
    latest_raw: dict[str, tuple[date, str]] = {}

    for r in in_period:
        day_map = by_emp_date[r.canonical_name]
        day_map[r.date] = day_map.get(r.date, 0.0) + r.net_tip

        prev = latest_raw.get(r.canonical_name)
        if (
            prev is None
            or r.date > prev[0]
            or (r.date == prev[0] and r.raw_name < prev[1])
        ):
            latest_raw[r.canonical_name] = (r.date, r.raw_name)

    # Employees with activity, in roster insertion order.
    ordered_canonicals = [c for c in roster.employees.keys() if c in by_emp_date]

    dates_in_period = [period.start + timedelta(days=i) for i in range(14)]

    # Row 1: title block.
    row1: list[Any] = [None, "Surfing Deer Tip outs"] + [None] * 30
    # Row 2: blank separator.
    row2: list[Any] = [None] * 32
    # Row 3: date header — A, B blank; then 14 (date, blank) pairs; then "Total Tips";
    # then 2 trailing blanks to match 32-column width.
    row3: list[Any] = [None, None]
    for d in dates_in_period:
        row3 += [d, None]
    row3 += ["Total Tips", None, None]
    # Row 4: blank separator.
    row4: list[Any] = [None] * 32

    grid: list[list[Any]] = [row1, row2, row3, row4]

    for canon in ordered_canonicals:
        day_tips = by_emp_date[canon]
        total = sum(day_tips.values())
        raw = latest_raw[canon][1]
        row: list[Any] = [canon, raw]
        for d in dates_in_period:
            row += [day_tips.get(d), None]
        row += [total]
        grid.append(row)

    return grid
