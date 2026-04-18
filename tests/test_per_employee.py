from datetime import date

import pytest
from openpyxl import Workbook, load_workbook

from tipout.hours import HoursEntry
from tipout.per_employee import append_period_tab_for_employee
from tipout.period import PayPeriod
from tipout.pos_parser import ShiftRow


def _mk_shift(
    d: date,
    raw: str = "Anthony",
    canon: str | None = "Anthony Garcia",
    *,
    cc_tips: float = 0.0,
    sa_tip_out: float = 0.0,
    bar_tipout: float = 0.0,
    total_tip_out: float = 0.0,
    barback: float = 0.0,
    bartender: float = 0.0,
    net_tip: float = 0.0,
    is_party: bool = False,
) -> ShiftRow:
    return ShiftRow(
        date=d,
        raw_name=raw,
        cc_tips=cc_tips,
        party=0.0,
        sa_tip_out=sa_tip_out,
        bar_tipout=bar_tipout,
        total_tip_out=total_tip_out,
        barback=barback,
        bartender=bartender,
        net_tip=net_tip,
        is_party=is_party,
        canonical_name=canon,
    )


def test_creates_new_file(tmp_path, tiny_roster):
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    shift_rows = [
        _mk_shift(date(2025, 12, 29), cc_tips=200.0, net_tip=150.0),
        _mk_shift(date(2025, 12, 30), cc_tips=300.0, net_tip=225.0),
    ]
    hours_entries = [
        HoursEntry(canonical="Anthony Garcia", date=date(2025, 12, 29), hours=7.0),
        HoursEntry(canonical="Anthony Garcia", date=date(2025, 12, 30), hours=8.0),
    ]
    path = tmp_path / "Anthony.xlsx"
    assert not path.exists()

    append_period_tab_for_employee(
        path, period, "Anthony Garcia", shift_rows, hours_entries
    )

    assert path.exists()
    wb = load_workbook(path)
    assert wb.sheetnames == ["Anthony 12.29 to 01.11.2026"]
    ws = wb["Anthony 12.29 to 01.11.2026"]

    # Row 1
    assert ws.cell(row=1, column=1).value == "Anthony"
    assert str(ws.cell(row=1, column=3).value).startswith("Pay Period 12/29")

    # Row 4 headers
    assert ws.cell(row=4, column=2).value == "Hours Worked"
    assert ws.cell(row=4, column=9).value == "Net Tip"

    # Row 5 = first day (openpyxl reads dates back as datetime)
    cell_a5 = ws.cell(row=5, column=1).value
    assert (cell_a5.date() if hasattr(cell_a5, "date") else cell_a5) == date(
        2025, 12, 29
    )
    assert ws.cell(row=5, column=9).value == 150.0

    # Row 20 totals
    assert ws.cell(row=20, column=2).value == 15.0  # 7 + 8
    assert ws.cell(row=20, column=9).value == 375.0  # 150 + 225

    # Row 23 col I = total_net_tip / total_hours
    assert ws.cell(row=23, column=9).value == 375.0 / 15.0


def test_appends_to_existing_file(tmp_path, tiny_roster):
    path = tmp_path / "Anthony.xlsx"
    # Pre-create with dummy prior tab
    wb = Workbook()
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]
    prior = wb.create_sheet("Anthony 09.29 to 10.12.2025")
    prior.cell(row=1, column=1, value="PRIOR_SENTINEL")
    wb.save(path)

    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    shift_rows = [_mk_shift(date(2025, 12, 29), net_tip=100.0)]
    hours_entries = [
        HoursEntry(canonical="Anthony Garcia", date=date(2025, 12, 29), hours=5.0)
    ]

    append_period_tab_for_employee(
        path, period, "Anthony Garcia", shift_rows, hours_entries
    )

    wb2 = load_workbook(path)
    assert "Anthony 09.29 to 10.12.2025" in wb2.sheetnames
    assert "Anthony 12.29 to 01.11.2026" in wb2.sheetnames
    assert (
        wb2["Anthony 09.29 to 10.12.2025"].cell(row=1, column=1).value
        == "PRIOR_SENTINEL"
    )


def test_rejects_duplicate_tab(tmp_path, tiny_roster):
    path = tmp_path / "Anthony.xlsx"
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    shift_rows = [_mk_shift(date(2025, 12, 29), net_tip=100.0)]
    hours_entries = [
        HoursEntry(canonical="Anthony Garcia", date=date(2025, 12, 29), hours=5.0)
    ]

    append_period_tab_for_employee(
        path, period, "Anthony Garcia", shift_rows, hours_entries
    )
    with pytest.raises(ValueError):
        append_period_tab_for_employee(
            path, period, "Anthony Garcia", shift_rows, hours_entries
        )


def test_party_flag_written(tmp_path, tiny_roster):
    path = tmp_path / "Anthony.xlsx"
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    shift_rows = [
        _mk_shift(date(2025, 12, 30), cc_tips=500.0, net_tip=400.0, is_party=True)
    ]
    hours_entries = [
        HoursEntry(canonical="Anthony Garcia", date=date(2025, 12, 30), hours=6.0)
    ]

    append_period_tab_for_employee(
        path, period, "Anthony Garcia", shift_rows, hours_entries
    )

    wb = load_workbook(path)
    ws = wb["Anthony 12.29 to 01.11.2026"]
    # 12/30 is day 2 = row 6 (openpyxl reads dates back as datetime)
    cell_a6 = ws.cell(row=6, column=1).value
    assert (cell_a6.date() if hasattr(cell_a6, "date") else cell_a6) == date(
        2025, 12, 30
    )
    assert ws.cell(row=6, column=10).value == "Party"


def test_no_hours_no_rate_row(tmp_path, tiny_roster):
    path = tmp_path / "Anthony.xlsx"
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    shift_rows = [_mk_shift(date(2025, 12, 29), cc_tips=200.0, net_tip=150.0)]
    hours_entries: list[HoursEntry] = []

    append_period_tab_for_employee(
        path, period, "Anthony Garcia", shift_rows, hours_entries
    )

    wb = load_workbook(path)
    ws = wb["Anthony 12.29 to 01.11.2026"]
    # Row 23 col I should be empty (no hours → no rate)
    assert ws.cell(row=23, column=9).value is None
