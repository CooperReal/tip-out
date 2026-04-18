from pathlib import Path
from datetime import timedelta
from openpyxl import Workbook, load_workbook

from tipout.period import PayPeriod
from tipout.pos_parser import ShiftRow
from tipout.hours import HoursEntry


COLUMNS = [
    "",             # col A: date (label omitted; row 5+ date fills the cell)
    "Hours Worked", # col B
    "CC Tips",      # col C
    "SA Tip Out",   # col D
    "Bar Tipout",   # col E
    "TotalTip Out", # col F
    "Serv As",      # col G
    "Bartender",    # col H
    "Net Tip",      # col I
]


def _tab_name(canonical: str, period: PayPeriod) -> str:
    first = canonical.split()[0]
    return (
        f"{first} {period.start.month:02d}.{period.start.day:02d} to "
        f"{period.end.month:02d}.{period.end.day:02d}.{period.end.year}"
    )


def append_period_tab_for_employee(
    path: Path,
    period: PayPeriod,
    canonical: str,
    shift_rows: list[ShiftRow],
    hours_entries: list[HoursEntry],
) -> None:
    """Append a new pay-period tab to this employee's workbook.

    `shift_rows` and `hours_entries` should already be filtered to this employee
    and this period — the writer does NOT filter again.

    Creates the workbook if absent (removing openpyxl's default 'Sheet').
    Raises ValueError if a tab for this period already exists.
    """
    if path.exists():
        wb = load_workbook(path)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        wb = Workbook()
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]

    tab_name = _tab_name(canonical, period)
    if tab_name in wb.sheetnames:
        raise ValueError(f"Tab {tab_name!r} already exists in {path}")

    ws = wb.create_sheet(tab_name)

    # Row 1: title
    first_name = canonical.split()[0]
    ws.cell(row=1, column=1, value=first_name)
    period_label = (
        f"Pay Period {period.start.month:02d}/{period.start.day:02d} to "
        f"{period.end.month:02d}/{period.end.day:02d}"
    )
    ws.cell(row=1, column=3, value=period_label)

    # Row 4: column headers (col A blank = date column)
    for c, header in enumerate(COLUMNS, start=1):
        if header:
            ws.cell(row=4, column=c, value=header)

    # Index shift rows and hours by date for fast lookup
    shifts_by_date = {r.date: r for r in shift_rows}
    hours_by_date = {h.date: h.hours for h in hours_entries}

    # Rows 5..18 — one per day in the 14-day window
    for i in range(14):
        d = period.start + timedelta(days=i)
        r = 5 + i
        ws.cell(row=r, column=1, value=d)
        if d in hours_by_date:
            ws.cell(row=r, column=2, value=hours_by_date[d])
        sh = shifts_by_date.get(d)
        if sh is not None:
            ws.cell(row=r, column=3, value=sh.cc_tips or None)
            ws.cell(row=r, column=4, value=sh.sa_tip_out or None)
            ws.cell(row=r, column=5, value=sh.bar_tipout or None)
            ws.cell(row=r, column=6, value=sh.total_tip_out or None)
            ws.cell(row=r, column=7, value=sh.barback or None)   # col G = "Serv As"
            ws.cell(row=r, column=8, value=sh.bartender or None) # col H = "Bartender"
            ws.cell(row=r, column=9, value=sh.net_tip or None)   # col I = "Net Tip"
            if sh.is_party:
                ws.cell(row=r, column=10, value="Party")

    # Row 20: totals (sum of rows 5..18)
    total_hours = sum(hours_by_date.values())
    totals_by_col: dict[int, float] = {
        3: sum(r.cc_tips for r in shift_rows),
        4: sum(r.sa_tip_out for r in shift_rows),
        5: sum(r.bar_tipout for r in shift_rows),
        6: sum(r.total_tip_out for r in shift_rows),
        7: sum(r.barback for r in shift_rows),
        8: sum(r.bartender for r in shift_rows),
        9: sum(r.net_tip for r in shift_rows),
    }
    if total_hours:
        ws.cell(row=20, column=2, value=total_hours)
    for c, v in totals_by_col.items():
        if v:
            ws.cell(row=20, column=c, value=v)

    # Row 23 col I: effective $/hour (Python-computed for determinism)
    total_net_tip = totals_by_col[9]
    if total_hours > 0 and total_net_tip > 0:
        ws.cell(row=23, column=9, value=total_net_tip / total_hours)

    wb.save(path)
