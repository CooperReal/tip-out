from datetime import date as _date

import pytest
from openpyxl import Workbook

from tipout.hours import HoursEntry, MissingHours, MissingTips, load_hours, validate_join
from tipout.pos_parser import ShiftRow
from tipout.roster import load_roster


def test_load_hours_resolves_aliases(tiny_roster, tiny_hours, tmp_path):
    roster = load_roster(tiny_roster)
    entries, unknown = load_hours(tiny_hours, roster)
    assert unknown == []
    assert len(entries) == 3
    by_canon = {e.canonical: e for e in entries}
    assert by_canon["Anthony Garcia"].date == _date(2025, 12, 29)
    assert by_canon["Anthony Garcia"].hours == 7.2
    assert by_canon["Jake Purvis"].hours == 6.5
    assert by_canon["Kristin Bartosic"].hours == 7.0

    # A raw alias like "Anthony" should also resolve through the roster.
    wb = Workbook()
    ws = wb.active
    ws.title = "Hours"
    ws.append(["Employee Name", "Date", "Hours Worked"])
    ws.append(["Anthony", _date(2025, 12, 30), 5.5])
    alt_path = tmp_path / "hours_alias.xlsx"
    wb.save(alt_path)
    alt_entries, alt_unknown = load_hours(alt_path, roster)
    assert alt_unknown == []
    assert len(alt_entries) == 1
    assert alt_entries[0].canonical == "Anthony Garcia"
    assert alt_entries[0].date == _date(2025, 12, 30)
    assert alt_entries[0].hours == 5.5


def test_load_hours_returns_unknown(tiny_roster, tmp_path):
    roster = load_roster(tiny_roster)
    wb = Workbook()
    ws = wb.active
    ws.title = "Hours"
    ws.append(["Employee Name", "Date", "Hours Worked"])
    ws.append(["Anthony Garcia", _date(2025, 12, 29), 7.2])
    ws.append(["Maya", _date(2025, 12, 29), 4.0])
    path = tmp_path / "hours_unknown.xlsx"
    wb.save(path)
    entries, unknown = load_hours(path, roster)
    assert len(entries) == 1
    assert entries[0].canonical == "Anthony Garcia"
    assert unknown == ["Maya"]


def _mk_shift(canonical, d, net_tip=100.0):
    return ShiftRow(
        date=d,
        raw_name=canonical,
        cc_tips=net_tip,
        party=0.0,
        sa_tip_out=0.0,
        bar_tipout=0.0,
        total_tip_out=0.0,
        barback=0.0,
        bartender=0.0,
        net_tip=net_tip,
        is_party=False,
        canonical_name=canonical,
    )


def test_validate_join_missing_hours_raises(tiny_roster):
    d = _date(2025, 12, 29)
    shift_rows = [
        _mk_shift("Anthony Garcia", d),
        _mk_shift("Jake Purvis", d),
    ]
    hours_entries = [
        HoursEntry(canonical="Anthony Garcia", date=d, hours=7.2),
        # Jake missing hours
    ]
    with pytest.raises(MissingHours) as excinfo:
        validate_join(shift_rows, hours_entries, d, d)
    assert ("Jake Purvis", d) in excinfo.value.args[0]


def test_validate_join_missing_tips_raises(tiny_roster):
    d = _date(2025, 12, 29)
    shift_rows = [
        _mk_shift("Anthony Garcia", d),
    ]
    hours_entries = [
        HoursEntry(canonical="Anthony Garcia", date=d, hours=7.2),
        HoursEntry(canonical="Jake Purvis", date=d, hours=6.5),
    ]
    with pytest.raises(MissingTips) as excinfo:
        validate_join(shift_rows, hours_entries, d, d)
    assert ("Jake Purvis", d) in excinfo.value.args[0]
