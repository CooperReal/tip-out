from datetime import date

import pytest
from openpyxl import Workbook, load_workbook

from tipout.period import PayPeriod
from tipout.pos_parser import ShiftRow
from tipout.roster import load_roster
from tipout.summary import _tab_name, append_period_tab, build_grid


def _shift(d: date, raw: str, canon: str | None, net: float) -> ShiftRow:
    return ShiftRow(
        date=d,
        raw_name=raw,
        cc_tips=0.0,
        party=0.0,
        sa_tip_out=0.0,
        bar_tipout=0.0,
        total_tip_out=0.0,
        barback=0.0,
        bartender=0.0,
        net_tip=net,
        is_party=False,
        canonical_name=canon,
    )


def test_build_grid_basic(tiny_roster):
    roster = load_roster(tiny_roster)
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [
        _shift(date(2025, 12, 29), "Anthony", "Anthony Garcia", 100.00),
        _shift(date(2025, 12, 31), "anthony", "Anthony Garcia", 200.00),
        _shift(date(2025, 12, 30), "Jake", "Jake Purvis", 50.00),
    ]

    grid = build_grid(period, rows, roster)

    # Row 1 title.
    assert grid[0][1] == "Surfing Deer Tip outs"

    # Row 3 date header.
    assert grid[2][0] is None
    assert grid[2][1] is None
    assert grid[2][2] == date(2025, 12, 29)
    assert grid[2][3] is None
    assert grid[2][4] == date(2025, 12, 30)
    # "Total Tips" at 0-indexed col 30 (= Excel col 31).
    assert grid[2][30] == "Total Tips"

    # Two employee rows: indexes 4 and 5.
    assert len(grid) == 6

    # Anthony Garcia row.
    assert grid[4][0] == "Anthony Garcia"
    # Most recent raw-name by date is 2025-12-31 -> "anthony".
    assert grid[4][1] == "anthony"
    assert grid[4][2] == 100.00  # day 1 = 12/29
    assert grid[4][4] is None  # day 2 = 12/30 no shift
    assert grid[4][6] == 200.00  # day 3 = 12/31
    assert grid[4][30] == 300.00  # period total

    # Jake Purvis row.
    assert grid[5][0] == "Jake Purvis"
    assert grid[5][1] == "Jake"
    assert grid[5][4] == 50.00  # day 2 = 12/30
    assert grid[5][30] == 50.00


def test_build_grid_respects_roster_order(tiny_roster):
    roster = load_roster(tiny_roster)
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    # Intentionally list Kristin before Anthony to ensure ordering comes from roster,
    # not from shift row order.
    rows = [
        _shift(date(2025, 12, 30), "Kristin", "Kristin Bartosic", 75.00),
        _shift(date(2025, 12, 30), "Jake", "Jake Purvis", 50.00),
        _shift(date(2025, 12, 29), "Anthony", "Anthony Garcia", 100.00),
    ]

    grid = build_grid(period, rows, roster)

    # Roster order: Anthony Garcia, Jake Purvis, Kristin Bartosic, ...
    assert grid[4][0] == "Anthony Garcia"
    assert grid[5][0] == "Jake Purvis"
    assert grid[6][0] == "Kristin Bartosic"


def test_build_grid_excludes_out_of_period(tiny_roster):
    roster = load_roster(tiny_roster)
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [
        _shift(date(2025, 12, 29), "Anthony", "Anthony Garcia", 100.00),
        # One day after period.end — must be excluded.
        _shift(date(2026, 1, 12), "Anthony", "Anthony Garcia", 999.00),
    ]

    grid = build_grid(period, rows, roster)

    # Only Anthony should appear, with total from the in-period shift only.
    assert len(grid) == 5
    assert grid[4][0] == "Anthony Garcia"
    assert grid[4][30] == 100.00


def test_build_grid_skips_rows_without_canonical(tiny_roster):
    roster = load_roster(tiny_roster)
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [
        _shift(date(2025, 12, 29), "Anthony", "Anthony Garcia", 100.00),
        _shift(date(2025, 12, 30), "Mystery Person", None, 42.00),
    ]

    grid = build_grid(period, rows, roster)

    # Only Anthony's row is present.
    assert len(grid) == 5
    assert grid[4][0] == "Anthony Garcia"
    assert grid[4][30] == 100.00


def test_append_period_tab_creates_new_file(tmp_path, tiny_roster):
    roster = load_roster(tiny_roster)
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [
        _shift(date(2025, 12, 29), "Anthony", "Anthony Garcia", 100.00),
        _shift(date(2025, 12, 30), "Jake", "Jake Purvis", 50.00),
    ]
    summary_path = tmp_path / "summary.xlsx"
    assert not summary_path.exists()

    append_period_tab(summary_path, period, rows, roster, hours_entries=None)

    assert summary_path.exists()
    wb = load_workbook(summary_path)
    assert wb.sheetnames == ["12.29 to 01.11.2026"]
    ws = wb["12.29 to 01.11.2026"]
    assert ws.cell(row=1, column=2).value == "Surfing Deer Tip outs"
    # First employee row (Excel row 5) should start with Anthony Garcia.
    assert ws.cell(row=5, column=1).value == "Anthony Garcia"
    assert ws.cell(row=5, column=2).value == "Anthony"
    # Total Tips total for Anthony should be 100.00 in column 31.
    assert ws.cell(row=5, column=31).value == 100.00


def test_append_period_tab_preserves_prior(tmp_path, tiny_roster):
    roster = load_roster(tiny_roster)
    summary_path = tmp_path / "summary.xlsx"

    # Pre-create a workbook with a prior sheet + sentinel value in A1.
    wb = Workbook()
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]
    prior = wb.create_sheet("09.29 to 10.12.2025")
    prior.cell(row=1, column=1, value="PRIOR_SENTINEL")
    wb.save(summary_path)

    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [_shift(date(2025, 12, 29), "Anthony", "Anthony Garcia", 100.00)]
    append_period_tab(summary_path, period, rows, roster, hours_entries=None)

    wb2 = load_workbook(summary_path)
    assert "09.29 to 10.12.2025" in wb2.sheetnames
    assert "12.29 to 01.11.2026" in wb2.sheetnames
    assert wb2["09.29 to 10.12.2025"].cell(row=1, column=1).value == "PRIOR_SENTINEL"


def test_append_period_tab_rejects_duplicate(tmp_path, tiny_roster):
    roster = load_roster(tiny_roster)
    summary_path = tmp_path / "summary.xlsx"
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [_shift(date(2025, 12, 29), "Anthony", "Anthony Garcia", 100.00)]

    append_period_tab(summary_path, period, rows, roster, hours_entries=None)
    with pytest.raises(ValueError):
        append_period_tab(summary_path, period, rows, roster, hours_entries=None)


def test_tab_name_formatting():
    p1 = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    assert _tab_name(p1) == "12.29 to 01.11.2026"

    # Same-year period.
    p2 = PayPeriod.from_dates(date(2025, 9, 29), date(2025, 10, 12))
    assert _tab_name(p2) == "09.29 to 10.12.2025"
