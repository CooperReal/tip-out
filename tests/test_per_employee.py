from datetime import date

import pytest
from openpyxl import load_workbook

from tipout.per_employee import (
    DATE_FORMAT,
    TIP_FORMAT,
    _safe_filename,
    append_period_tab_for_employee,
    build_grid,
)
from tipout.period import PayPeriod
from tipout.pos_parser import ShiftRow


def _shift(d: date, canon: str | None, **vals) -> ShiftRow:
    base = dict(
        cc_tips=0.0, party=0.0, sa_tip_out=0.0, bar_tipout=0.0,
        total_tip_out=0.0, barback=0.0, bartender=0.0, net_tip=0.0,
        is_party=False,
    )
    base.update(vals)
    return ShiftRow(
        date=d,
        raw_name=canon or "raw",
        canonical_name=canon,
        **base,
    )


def test_build_grid_layout_and_totals():
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [
        _shift(
            date(2025, 12, 30), "Yvonne Lewis",
            cc_tips=231.0, sa_tip_out=10.53, bar_tipout=33.90,
            total_tip_out=44.43, bartender=105.80, net_tip=292.37,
        ),
        _shift(
            date(2025, 12, 31), "Yvonne Lewis",
            cc_tips=280.57, sa_tip_out=13.38, total_tip_out=13.38,
            bartender=72.82, net_tip=340.01,
        ),
    ]

    grid = build_grid(period, "Yvonne Lewis", rows)

    # Title in R1C1.
    assert "Yvonne Lewis" in grid[0][0]
    assert "12.29 to 01.11.2026" in grid[0][0]

    # Header row.
    assert grid[1] == [
        "Date", "CC Tips", "SA Tip Out", "Bar Tipout",
        "Total Tip Out", "Barback", "Bartender", "Net Tip",
    ]

    # 2 header rows + 14 day rows + 1 totals row = 17 rows.
    assert len(grid) == 17

    # Day 1 = 12/29 = no shift -> all None except date.
    day1 = grid[2]
    assert day1[0] == date(2025, 12, 29)
    assert all(v is None for v in day1[1:])

    # Day 2 = 12/30 = first shift.
    day2 = grid[3]
    assert day2[0] == date(2025, 12, 30)
    assert day2[1] == 231.0      # CC Tips
    assert day2[2] == 10.53      # SA Tip Out
    assert day2[3] == 33.90      # Bar Tipout
    assert day2[4] == 44.43      # Total Tip Out
    assert day2[5] is None       # Barback (zero)
    assert day2[6] == 105.80     # Bartender
    assert day2[7] == 292.37     # Net Tip

    # Totals row.
    totals = grid[-1]
    assert totals[0] == "Total"
    assert totals[1] == 511.57   # 231.00 + 280.57
    assert totals[7] == 632.38   # 292.37 + 340.01


def test_build_grid_omits_other_employees():
    """Shifts for different canonicals must be ignored."""
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [
        _shift(date(2025, 12, 30), "Yvonne Lewis", net_tip=100.0),
        _shift(date(2025, 12, 30), "Other Person", net_tip=999.0),
    ]

    grid = build_grid(period, "Yvonne Lewis", rows)
    assert grid[-1][7] == 100.0   # totals: only Yvonne counted


def test_build_grid_excludes_out_of_period():
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [
        _shift(date(2025, 12, 29), "Yvonne Lewis", net_tip=50.0),
        _shift(date(2026, 1, 12), "Yvonne Lewis", net_tip=999.0),  # one day past end
    ]

    grid = build_grid(period, "Yvonne Lewis", rows)
    assert grid[-1][7] == 50.0


def test_append_period_tab_writes_file_with_styling(tmp_path):
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [
        _shift(
            date(2025, 12, 30), "Yvonne Lewis",
            cc_tips=231.0, net_tip=292.37,
        ),
    ]

    written = append_period_tab_for_employee(tmp_path, period, "Yvonne Lewis", rows)

    assert written == tmp_path / "per-employee" / "Yvonne Lewis.xlsx"
    assert written.exists()

    wb = load_workbook(written)
    assert wb.sheetnames == ["12.29 to 01.11.2026"]
    ws = wb["12.29 to 01.11.2026"]

    # Title.
    assert "Yvonne Lewis" in ws.cell(row=1, column=1).value

    # Day 2 = 12/30 has CC Tips populated. (openpyxl reads back date → datetime.)
    cell_date = ws.cell(row=4, column=1).value
    assert (cell_date.year, cell_date.month, cell_date.day) == (2025, 12, 30)
    assert ws.cell(row=4, column=2).value == 231.0

    # Number formats applied.
    assert ws.cell(row=3, column=1).number_format == DATE_FORMAT
    assert ws.cell(row=4, column=2).number_format == TIP_FORMAT

    # Frozen pane locks title + header.
    assert ws.freeze_panes == "A3"

    # Borders on body cells.
    assert ws.cell(row=4, column=2).border.left.style == "thin"

    # Totals row at row 17, bold.
    assert ws.cell(row=17, column=1).value == "Total"
    assert ws.cell(row=17, column=2).font.bold is True


def test_append_period_tab_appends_without_overwriting(tmp_path):
    period1 = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    period2 = PayPeriod.from_dates(date(2026, 1, 12), date(2026, 1, 25))
    rows = [
        _shift(date(2025, 12, 29), "Yvonne Lewis", net_tip=50.0),
        _shift(date(2026, 1, 12), "Yvonne Lewis", net_tip=80.0),
    ]

    append_period_tab_for_employee(tmp_path, period1, "Yvonne Lewis", rows)
    append_period_tab_for_employee(tmp_path, period2, "Yvonne Lewis", rows)

    wb = load_workbook(tmp_path / "per-employee" / "Yvonne Lewis.xlsx")
    assert wb.sheetnames == ["12.29 to 01.11.2026", "01.12 to 01.25.2026"]


def test_append_period_tab_rejects_duplicate_period(tmp_path):
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [_shift(date(2025, 12, 29), "Yvonne Lewis", net_tip=50.0)]

    append_period_tab_for_employee(tmp_path, period, "Yvonne Lewis", rows)
    with pytest.raises(ValueError):
        append_period_tab_for_employee(tmp_path, period, "Yvonne Lewis", rows)


def test_safe_filename_strips_illegal_chars():
    assert _safe_filename("Anthony Garcia") == "Anthony Garcia"
    assert _safe_filename('Bad/Name?') == "Bad_Name_"
    assert _safe_filename("Marcus, Eric") == "Marcus, Eric"  # comma is legal
