from datetime import date
from pathlib import Path

import pytest

from tipout.time_clock import HoursRow, parse_time_clock

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_time_clock.csv"


def test_parse_returns_one_row_per_shift_with_title_cased_name():
    rows = parse_time_clock(FIXTURE)
    # 2 Anthony WAIT shifts + 1 Anthony MANAGER shift + 1 Jake shift = 4
    assert len(rows) == 4
    assert all(isinstance(r, HoursRow) for r in rows)
    # All names title-cased from upper.
    names = {r.raw_name for r in rows}
    assert names == {"Anthony Garcia", "Jake Purvis"}


def test_parse_attributes_midnight_crossing_to_start_date():
    rows = parse_time_clock(FIXTURE)
    anthony_dates = sorted(r.date for r in rows if r.raw_name == "Anthony Garcia")
    # Three shifts: 12-29 (WAIT) + 12-29 (MANAGER) + 12-30 (WAIT, crosses midnight)
    assert anthony_dates == [date(2025, 12, 29), date(2025, 12, 29), date(2025, 12, 30)]


def test_parse_keeps_each_shift_separate_for_same_day_multi_role():
    """Aggregation across roles is the runner's job, not the parser's."""
    rows = parse_time_clock(FIXTURE)
    anthony_1229 = [
        r.hours for r in rows if r.raw_name == "Anthony Garcia" and r.date == date(2025, 12, 29)
    ]
    assert sorted(anthony_1229) == [4.0, 7.5]


def test_parse_uses_duration_hours_column():
    """Should pick the last column (Duration), not Regular Hours, even when they differ."""
    rows = parse_time_clock(FIXTURE)
    jake = [r for r in rows if r.raw_name == "Jake Purvis"]
    assert len(jake) == 1
    assert jake[0].hours == 7.0  # Regular 6.5 + OT 0.5 = Duration 7.0


def test_parse_raises_on_shift_row_before_any_block_header(tmp_path):
    """A date-like row with no preceding block header is a schema error."""
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "Start Date,Start Time,End Date,End Time,Reported Tips,"
        "Regular Hours,Overtime Hours,Duration (Hours)\n"
        '"Mon, 12-29-25",3:00 PM,"Mon, 12-29-25",10:30 PM,0,7.5,0,7.5\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        parse_time_clock(bad)


def test_parse_raises_on_unparseable_duration_value(tmp_path):
    bad = tmp_path / "bad_duration.csv"
    bad.write_text(
        "ANTHONY GARCIA - WAIT Mon 12-29-2025 - Sun 01-04-2026,,,,,,,\n"
        "Start Date,Start Time,End Date,End Time,Reported Tips,"
        "Regular Hours,Overtime Hours,Duration (Hours)\n"
        '"Mon, 12-29-25",3:00 PM,"Mon, 12-29-25",10:30 PM,0,7.5,0,abc\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duration"):
        parse_time_clock(bad)
