# Tipout Hours Worked Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Hours Worked` column and `$/hr` totals cell to each per-employee period tab, sourced from a new optional `--hours <csv>` CLI flag that ingests Toast Time Clock CSV exports.

**Architecture:** New module `src/tipout/time_clock.py` parses the CSV and returns a flat list of `HoursRow`. `runner.run()` accepts an optional `hours_path`, resolves CSV names against the existing roster (strict, parallel to the POS unknown-names flow), aggregates to `dict[(canonical, date), hours]`, and passes per-canonical slices into `append_period_tab_for_employee`. Per-employee grid expands from 8 to 10 columns; layout is stable regardless of whether `--hours` was passed.

**Tech Stack:** Python 3.11, click, openpyxl, pytest. Existing project conventions: TDD, frequent commits, fixture-driven tests in `tests/`.

**Reference spec:** `docs/superpowers/specs/2026-05-17-tipout-hours-design.md`

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `src/tipout/time_clock.py` | NEW | Parse Toast Time Clock CSV → `list[HoursRow]`. No roster resolution. |
| `src/tipout/per_employee.py` | MODIFY | Extend grid layout to 10 columns (Hours Worked at B, $/hr at J). New optional `hours_by_date` arg on `build_grid` and `append_period_tab_for_employee`. |
| `src/tipout/runner.py` | MODIFY | Accept optional `hours_path: Path | None`. New `UnresolvedHoursNames` exception. Aggregate CSV rows to `dict[str, dict[date, float]]` and thread per-canonical slice into per-employee writer. |
| `src/tipout/cli.py` | MODIFY | New `--hours` option on the `run` command. On `UnresolvedHoursNames`, write `unknown_hours_names.txt` and exit 1 (mirrors existing `UnresolvedNames` UX). |
| `tests/test_time_clock.py` | NEW | Parser unit tests (block detection, midnight-crossing, role aggregation, malformed input). |
| `tests/fixtures/tiny_time_clock.csv` | NEW | Minimal hand-written CSV fixture mirroring Toast format. |
| `tests/test_per_employee.py` | MODIFY | Update existing column-position assertions (CC Tips moves from col 2→3, etc.). Add new tests for `hours_by_date` parameter. |
| `tests/test_runner.py` | MODIFY | New tests covering `hours_path` plumbing, `UnresolvedHoursNames`, and partial-write safety. |
| `tests/conftest.py` | MODIFY | Extend `tiny_runner_env` fixture to optionally produce a matching tiny time clock CSV. |
| `tipout-plugin/skills/tipout/SKILL.md` | MODIFY | Document `--hours` flag in invocation example and command reference. |

---

## Task 1: Time-clock CSV parser

**Files:**
- Create: `src/tipout/time_clock.py`
- Create: `tests/test_time_clock.py`
- Create: `tests/fixtures/tiny_time_clock.csv`

- [ ] **Step 1: Create the test fixture CSV**

Write `tests/fixtures/tiny_time_clock.csv` exactly as below (mirrors the Toast block format — name+role header, column header, shift rows, per-block Total, blank separators):

```csv
ANTHONY GARCIA - WAIT Mon 12-29-2025 - Sun 01-04-2026,,,,,,,
Start Date,Start Time,End Date,End Time,Reported Tips,Regular Hours,Overtime Hours,Duration (Hours)
"Mon, 12-29-25",3:00 PM,"Mon, 12-29-25",10:30 PM,0,7.5,0,7.5
"Tue, 12-30-25",3:00 PM,"Wed, 12-31-25",12:30 AM,0,9.5,0,9.5
Total,,,,0,17.0,0,17.0
ANTHONY GARCIA - MANAGER,,,,,,,
Start Date,Start Time,End Date,End Time,Reported Tips,Regular Hours,Overtime Hours,Duration (Hours)
"Mon, 12-29-25",10:00 AM,"Mon, 12-29-25",2:00 PM,0,4.0,0,4.0
Total,,,,0,4.0,0,4.0
JAKE PURVIS - BARTENDER Mon 12-29-2025 - Sun 01-04-2026,,,,,,,
Start Date,Start Time,End Date,End Time,Reported Tips,Regular Hours,Overtime Hours,Duration (Hours)
"Tue, 12-30-25",4:00 PM,"Tue, 12-30-25",11:00 PM,0,6.5,0.5,7.0
Total,,,,0,6.5,0.5,7.0
```

(Note: Anthony Garcia has two roles on 12-29 — the test will verify they sum to 11.5h. The 12-30 shift crosses midnight to 12-31 but must attribute to 12-30.)

- [ ] **Step 2: Write the failing test file**

Create `tests/test_time_clock.py`:

```python
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
    anthony_1229 = [r.hours for r in rows if r.raw_name == "Anthony Garcia" and r.date == date(2025, 12, 29)]
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
        'Start Date,Start Time,End Date,End Time,Reported Tips,Regular Hours,Overtime Hours,Duration (Hours)\n'
        '"Mon, 12-29-25",3:00 PM,"Mon, 12-29-25",10:30 PM,0,7.5,0,7.5\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        parse_time_clock(bad)
```

- [ ] **Step 3: Run the test file to confirm it fails (module missing)**

Run: `.venv/Scripts/python -m pytest tests/test_time_clock.py -v`
Expected: every test errors with `ModuleNotFoundError: No module named 'tipout.time_clock'`.

- [ ] **Step 4: Implement `src/tipout/time_clock.py`**

```python
"""Parse a Toast Time Clock CSV export into a flat list of HoursRow.

The CSV is block-structured: each block opens with a row like
``ANDREW ROBERTS - MAITRE'D Mon 05-04-2026 - Sun 05-17-2026,,,,,,,`` followed
by a column-header row, one row per shift, and a ``Total,,,,...`` row. Blank
rows separate blocks. One person can appear in multiple blocks with different
roles; this parser keeps shifts separate and lets downstream code aggregate.

The raw name is the substring before the first ' - ' in the block header,
``.title()``-cased for human-readable error messages. The roster's
case-insensitive resolver handles the actual matching.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class HoursRow:
    raw_name: str   # title-cased from the CSV's uppercase
    date: date      # from Start Date; midnight-crossing shifts attribute here
    hours: float    # from the Duration (Hours) column


# Last column index in a shift row: Start Date, Start Time, End Date, End Time,
# Reported Tips, Regular Hours, Overtime Hours, Duration (Hours) → 7.
_DURATION_COL = 7
_DATE_FMT = "%a, %m-%d-%y"


def parse_time_clock(path: Path) -> list[HoursRow]:
    rows: list[HoursRow] = []
    current_name: str | None = None
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.reader(fh):
            if not raw or not (raw[0] or "").strip():
                current_name = None
                continue
            first = raw[0].strip()
            if first == "Start Date":
                continue
            if first == "Total":
                continue
            if " - " in first:
                # Block header: NAME - ROLE <date-range>
                name_part = first.split(" - ", 1)[0].strip()
                current_name = name_part.title()
                continue
            # Anything else is a shift row.
            try:
                d = datetime.strptime(first, _DATE_FMT).date()
            except ValueError as exc:
                raise ValueError(
                    f"Time clock CSV: unrecognized row starting with {first!r}"
                ) from exc
            if current_name is None:
                raise ValueError(
                    f"Time clock CSV: shift row {first!r} appears before any "
                    "block header (NAME - ROLE)."
                )
            try:
                hours = float(raw[_DURATION_COL]) if len(raw) > _DURATION_COL else 0.0
            except ValueError:
                hours = 0.0
            rows.append(HoursRow(raw_name=current_name, date=d, hours=hours))
    return rows
```

- [ ] **Step 5: Run the tests; verify all pass**

Run: `.venv/Scripts/python -m pytest tests/test_time_clock.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/tipout/time_clock.py tests/test_time_clock.py tests/fixtures/tiny_time_clock.csv
git commit -m "feat(time_clock): parse Toast Time Clock CSV into HoursRow list"
```

---

## Task 2: Extend per-employee grid to 10 columns with Hours Worked + $/hr

**Files:**
- Modify: `src/tipout/per_employee.py`
- Modify: `tests/test_per_employee.py`

**Layout change**: insert `Hours Worked` at col B (shift all tip columns right by 1), append `$/hr` at col J (header + totals-row value only; day rows leave J blank).

- [ ] **Step 1: Update the existing column-position tests in `tests/test_per_employee.py`**

The shifted columns must be reflected in `test_build_grid_layout_and_totals`, `test_build_grid_omits_other_employees`, `test_build_grid_excludes_out_of_period`, and `test_append_period_tab_writes_file_with_styling`. Apply these exact edits:

In `test_build_grid_layout_and_totals`, replace the header-row assertion and the day-2/totals assertions:

```python
    # Header row.
    assert grid[1] == [
        "Date", "Hours Worked", "CC Tips", "SA Tip Out", "Bar Tipout",
        "Total Tip Out", "Barback", "Bartender", "Net Tip", "$/hr",
    ]

    # 2 header rows + 14 day rows + 1 totals row = 17 rows.
    assert len(grid) == 17

    # Day 1 = 12/29 = no shift -> all None except date.
    day1 = grid[2]
    assert day1[0] == date(2025, 12, 29)
    assert all(v is None for v in day1[1:])

    # Day 2 = 12/30 = first shift. CC Tips is now col index 2 (B is Hours).
    day2 = grid[3]
    assert day2[0] == date(2025, 12, 30)
    assert day2[1] is None       # Hours Worked (not provided)
    assert day2[2] == 231.0      # CC Tips
    assert day2[3] == 10.53      # SA Tip Out
    assert day2[4] == 33.90      # Bar Tipout
    assert day2[5] == 44.43      # Total Tip Out
    assert day2[6] is None       # Barback (zero)
    assert day2[7] == 105.80     # Bartender
    assert day2[8] == 292.37     # Net Tip
    assert day2[9] is None       # $/hr (day rows always blank)

    # Totals row.
    totals = grid[-1]
    assert totals[0] == "Total"
    assert totals[1] is None     # Hours total — none provided
    assert totals[2] == 511.57   # CC Tips total
    assert totals[8] == 632.38   # Net Tip total
    assert totals[9] is None     # $/hr blank when hours total is 0
```

In `test_build_grid_omits_other_employees`, change `grid[-1][7]` to `grid[-1][8]`.

In `test_build_grid_excludes_out_of_period`, change `grid[-1][7]` to `grid[-1][8]`.

In `test_append_period_tab_writes_file_with_styling`, change the cell-value assertion from `ws.cell(row=4, column=2).value == 231.0` to:

```python
    # CC Tips now at col 3 (col 2 = Hours Worked, blank here).
    assert ws.cell(row=4, column=2).value is None
    assert ws.cell(row=4, column=3).value == 231.0
```

Also update the number-format check to point at the new CC Tips column:

```python
    assert ws.cell(row=4, column=3).number_format == TIP_FORMAT
```

And the bold-totals check:

```python
    assert ws.cell(row=17, column=3).font.bold is True
```

- [ ] **Step 2: Add new tests covering the `hours_by_date` parameter**

Append to `tests/test_per_employee.py`:

```python
def test_build_grid_with_hours_populates_b_and_j():
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [
        _shift(date(2025, 12, 30), "Yvonne Lewis", net_tip=200.0),
        _shift(date(2025, 12, 31), "Yvonne Lewis", net_tip=300.0),
    ]
    hours_by_date = {
        date(2025, 12, 30): 7.5,
        date(2025, 12, 31): 5.0,
        # Day with hours but no tips — still surfaces in Hours column.
        date(2026, 1, 1): 4.0,
    }

    grid = build_grid(period, "Yvonne Lewis", rows, hours_by_date=hours_by_date)

    # Day 2 = 12/30
    assert grid[3][1] == 7.5
    # Day 3 = 12/31
    assert grid[4][1] == 5.0
    # Day 4 = 1/1 (no tip shift, but hours present)
    assert grid[5][1] == 4.0
    # Day 5 onward: no hours, no tips → blank
    assert grid[6][1] is None

    # Totals row.
    totals = grid[-1]
    assert totals[1] == 16.5    # hours total
    # $/hr = Net Tip total (500.0) / Hours total (16.5) → 30.30
    assert totals[9] == round(500.0 / 16.5, 2)


def test_build_grid_with_zero_hours_total_leaves_per_hr_blank():
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    rows = [_shift(date(2025, 12, 30), "Yvonne Lewis", net_tip=50.0)]
    grid = build_grid(period, "Yvonne Lewis", rows, hours_by_date={})
    totals = grid[-1]
    assert totals[1] is None    # no hours
    assert totals[9] is None    # $/hr left blank, not zero
```

- [ ] **Step 3: Run the tests; verify failures**

Run: `.venv/Scripts/python -m pytest tests/test_per_employee.py -v`
Expected: failures across the board (header mismatch, index errors, missing kwarg).

- [ ] **Step 4: Edit `src/tipout/per_employee.py`** to expand the layout.

Apply these changes:

(a) Update the module docstring's third sentence — remove the "NOT written because the tool has no hours data source today" caveat. New docstring:

```python
"""Per-employee tip-out workbooks.

One file per canonical employee under `<output_dir>/per-employee/<Name>.xlsx`.
One tab per pay period, appended (existing tabs untouched). Layout matches
the hand-done Yvonne.xlsx reference: Hours Worked at col B, tip columns
C..I, $/hr at col J on the totals row only.
"""
```

(b) Update column constants:

```python
TIP_COLUMNS: list[tuple[str, str]] = [
    ("CC Tips", "cc_tips"),
    ("SA Tip Out", "sa_tip_out"),
    ("Bar Tipout", "bar_tipout"),
    ("Total Tip Out", "total_tip_out"),
    ("Barback", "barback"),
    ("Bartender", "bartender"),
    ("Net Tip", "net_tip"),
]
HOURS_HEADER = "Hours Worked"
PER_HR_HEADER = "$/hr"
TOTAL_COLS = 1 + 1 + len(TIP_COLUMNS) + 1  # Date + Hours + 7 tips + $/hr = 10

TITLE_ROW = 1
HEADER_ROW = 2
FIRST_DATA_ROW = 3
DATE_COL = 1
HOURS_COL = 2
FIRST_TIP_COL = 3
NET_TIP_COL = 2 + len(TIP_COLUMNS)        # = 9 (col I)
PER_HR_COL = TOTAL_COLS                    # = 10 (col J)

COLUMN_WIDTHS: dict[str, float] = {
    "A": 11.0,   # Date
    "B": 12.0,   # Hours Worked
    "C": 11.0, "D": 11.0, "E": 11.0,
    "F": 13.0,   # Total Tip Out
    "G": 11.0, "H": 11.0,
    "I": 12.0,   # Net Tip
    "J": 9.0,    # $/hr
}
```

(c) Update `build_grid` signature and body to accept `hours_by_date`:

```python
def build_grid(
    period: PayPeriod,
    canonical: str,
    shift_rows: list[ShiftRow],
    hours_by_date: dict[date, float] | None = None,
) -> list[list[Any]]:
    """Return a 2D grid for one employee's per-period tab.

    Layout: row 1 title, row 2 column headers, rows 3..16 = 14 day rows,
    row 17 = totals. Day rows always present (blanks where no shift).
    When ``hours_by_date`` is provided, col B is populated per-day and col J
    on the totals row holds Net Tip total ÷ Hours total (blank if Hours = 0).
    """
    hours_by_date = hours_by_date or {}

    in_period = [
        r
        for r in shift_rows
        if r.canonical_name == canonical
        and period.start <= r.date <= period.end
    ]

    by_date: dict[date, dict[str, float]] = defaultdict(
        lambda: {attr: 0.0 for _, attr in TIP_COLUMNS}
    )
    for r in in_period:
        for _, attr in TIP_COLUMNS:
            by_date[r.date][attr] += getattr(r, attr)

    dates_in_period = [period.start + timedelta(days=i) for i in range(14)]

    title = (
        f"{canonical}   Pay Period "
        f"{period.start.month:02d}.{period.start.day:02d} to "
        f"{period.end.month:02d}.{period.end.day:02d}.{period.end.year}"
    )

    row1: list[Any] = [None] * TOTAL_COLS
    row1[0] = title

    row2: list[Any] = (
        ["Date", HOURS_HEADER]
        + [label for label, _ in TIP_COLUMNS]
        + [PER_HR_HEADER]
    )

    grid: list[list[Any]] = [row1, row2]

    totals: dict[str, float] = {attr: 0.0 for _, attr in TIP_COLUMNS}
    hours_total = 0.0
    for d in dates_in_period:
        row: list[Any] = [None] * TOTAL_COLS
        row[0] = d
        hours = hours_by_date.get(d, 0.0)
        if hours:
            row[HOURS_COL - 1] = _round2(hours)
            hours_total += hours
        day_data = by_date.get(d)
        if day_data:
            for col_idx, (_, attr) in enumerate(TIP_COLUMNS, start=FIRST_TIP_COL - 1):
                v = _round2(day_data[attr])
                if v != 0:
                    row[col_idx] = v
                    totals[attr] += v
        # $/hr column (J) is always blank on day rows.
        grid.append(row)

    totals_row: list[Any] = [None] * TOTAL_COLS
    totals_row[0] = "Total"
    if hours_total:
        totals_row[HOURS_COL - 1] = _round2(hours_total)
    for col_idx, (_, attr) in enumerate(TIP_COLUMNS, start=FIRST_TIP_COL - 1):
        totals_row[col_idx] = _round2(totals[attr])
    net_tip_total = totals[TIP_COLUMNS[-1][1]]
    if hours_total > 0:
        totals_row[PER_HR_COL - 1] = round(net_tip_total / hours_total, 2)
    grid.append(totals_row)

    return grid
```

(d) Update `_apply_styling`'s tip-column loop bound. Replace the loop that runs from `FIRST_TIP_COL` to `TOTAL_COLS + 1` with one that explicitly skips the `$/hr` column on day rows and that applies the tip format to columns Hours through Net Tip plus the `$/hr` cell on the totals row only. Replace the two inner loops in `_apply_styling` with:

```python
    # Tip number format on Hours, all tip columns, and the $/hr cell on totals.
    for r in range(FIRST_DATA_ROW, totals_row + 1):
        for c in range(HOURS_COL, NET_TIP_COL + 1):
            ws.cell(row=r, column=c).number_format = TIP_FORMAT
    ws.cell(row=totals_row, column=PER_HR_COL).number_format = TIP_FORMAT
```

(All other parts of `_apply_styling` — column widths, freeze panes, header fill, title merge, totals-row bolding, borders — operate over `range(1, TOTAL_COLS + 1)` and therefore extend to col J automatically since `TOTAL_COLS` is now 10. No further edits needed.)

(e) Update `append_period_tab_for_employee` to plumb `hours_by_date` through:

```python
def append_period_tab_for_employee(
    output_dir: Path,
    period: PayPeriod,
    canonical: str,
    shift_rows: list[ShiftRow],
    hours_by_date: dict[date, float] | None = None,
) -> Path:
    ...
    ws = wb.create_sheet(tab)
    grid = build_grid(period, canonical, shift_rows, hours_by_date=hours_by_date)
    for r, row_values in enumerate(grid, start=1):
        for c, val in enumerate(row_values, start=1):
            if val is not None:
                ws.cell(row=r, column=c, value=val)
    ...
```

- [ ] **Step 5: Run the tests; verify all pass**

Run: `.venv/Scripts/python -m pytest tests/test_per_employee.py -v`
Expected: all PASS (including the two new ones).

- [ ] **Step 6: Commit**

```bash
git add src/tipout/per_employee.py tests/test_per_employee.py
git commit -m "feat(per_employee): add Hours Worked col + \$/hr totals cell"
```

---

## Task 3: Wire hours through the runner

**Files:**
- Modify: `src/tipout/runner.py`
- Modify: `tests/test_runner.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Extend the `tiny_runner_env` fixture in `tests/conftest.py`** to also write a matching tiny time-clock CSV. Add to the end of the fixture, just before `return {...}`:

```python
    hours_csv = tmp_path / "time_clock.csv"
    hours_csv.write_text(
        "ANTHONY GARCIA - WAIT Mon 12-29-2025 - Sun 01-04-2026,,,,,,,\n"
        "Start Date,Start Time,End Date,End Time,Reported Tips,Regular Hours,Overtime Hours,Duration (Hours)\n"
        '"Mon, 12-29-25",3:00 PM,"Mon, 12-29-25",10:30 PM,0,6.0,0,6.0\n'
        "Total,,,,0,6.0,0,6.0\n"
        "JAKE PURVIS - BARTENDER Mon 12-29-2025 - Sun 01-04-2026,,,,,,,\n"
        "Start Date,Start Time,End Date,End Time,Reported Tips,Regular Hours,Overtime Hours,Duration (Hours)\n"
        '"Mon, 12-29-25",4:00 PM,"Mon, 12-29-25",11:00 PM,0,7.0,0,7.0\n'
        "Total,,,,0,7.0,0,7.0\n",
        encoding="utf-8",
    )
```

And include it in the returned dict:

```python
    return {
        "config_path": config_path,
        "pos_path": pos_path,
        "roster_path": roster_path,
        "summary_path": summary_path,
        "hours_path": hours_csv,
    }
```

- [ ] **Step 2: Add new test cases to `tests/test_runner.py`**

Append:

```python
def test_run_with_hours_populates_per_employee_files(tiny_runner_env):
    from tipout.runner import run
    from tipout.config import Config
    from tipout.period import PayPeriod

    env = tiny_runner_env
    cfg = Config.load(env["config_path"])
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))

    run(cfg, env["pos_path"], period, hours_path=env["hours_path"])

    per_emp_dir = cfg.summary_path.parent / "per-employee"
    anthony = load_workbook(per_emp_dir / "Anthony Garcia.xlsx")
    ws = anthony["12.29 to 01.11.2026"]
    # Day 1 = 12/29 is at row 3; Hours Worked is col B.
    assert ws.cell(row=3, column=2).value == 6.0
    # Totals row 17, col B = Hours total
    assert ws.cell(row=17, column=2).value == 6.0
    # $/hr in col J on totals row > 0
    assert ws.cell(row=17, column=10).value > 0


def test_run_without_hours_writes_blank_hours_columns(tiny_runner_env):
    from tipout.runner import run
    from tipout.config import Config
    from tipout.period import PayPeriod

    env = tiny_runner_env
    cfg = Config.load(env["config_path"])
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))

    run(cfg, env["pos_path"], period)    # no hours_path

    per_emp_dir = cfg.summary_path.parent / "per-employee"
    anthony = load_workbook(per_emp_dir / "Anthony Garcia.xlsx")
    ws = anthony["12.29 to 01.11.2026"]
    # Header still includes Hours Worked at col B and $/hr at col J — layout is stable.
    assert ws.cell(row=2, column=2).value == "Hours Worked"
    assert ws.cell(row=2, column=10).value == "$/hr"
    # But Hours Worked cells are blank.
    assert ws.cell(row=3, column=2).value is None
    assert ws.cell(row=17, column=2).value is None


def test_run_raises_unresolved_hours_names_before_writing_any_file(
    tiny_runner_env, tmp_path
):
    from tipout.runner import run, UnresolvedHoursNames
    from tipout.config import Config
    from tipout.period import PayPeriod

    env = tiny_runner_env
    # Hours CSV with a name (Stranger Person) that isn't in the roster.
    bad_csv = tmp_path / "bad_hours.csv"
    bad_csv.write_text(
        "STRANGER PERSON - WAIT Mon 12-29-2025 - Sun 01-04-2026,,,,,,,\n"
        "Start Date,Start Time,End Date,End Time,Reported Tips,Regular Hours,Overtime Hours,Duration (Hours)\n"
        '"Mon, 12-29-25",3:00 PM,"Mon, 12-29-25",10:30 PM,0,5.0,0,5.0\n'
        "Total,,,,0,5.0,0,5.0\n",
        encoding="utf-8",
    )

    cfg = Config.load(env["config_path"])
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))

    per_emp_dir = cfg.summary_path.parent / "per-employee"
    assert not per_emp_dir.exists()

    with pytest.raises(UnresolvedHoursNames) as exc:
        run(cfg, env["pos_path"], period, hours_path=bad_csv)
    assert "Stranger Person" in exc.value.names
    # Critical: no per-employee files were written.
    assert not per_emp_dir.exists()


def test_run_filters_hours_to_pay_period(tiny_runner_env, tmp_path):
    """Hours rows outside the requested period must not appear in per-employee tabs."""
    from tipout.runner import run
    from tipout.config import Config
    from tipout.period import PayPeriod

    env = tiny_runner_env

    # CSV with a shift INSIDE the period and one OUTSIDE.
    csv_path = tmp_path / "wider_hours.csv"
    csv_path.write_text(
        "ANTHONY GARCIA - WAIT Mon 12-29-2025 - Sun 01-25-2026,,,,,,,\n"
        "Start Date,Start Time,End Date,End Time,Reported Tips,Regular Hours,Overtime Hours,Duration (Hours)\n"
        '"Mon, 12-29-25",3:00 PM,"Mon, 12-29-25",10:30 PM,0,6.0,0,6.0\n'
        '"Mon, 01-12-26",3:00 PM,"Mon, 01-12-26",10:30 PM,0,8.0,0,8.0\n'
        "Total,,,,0,14.0,0,14.0\n",
        encoding="utf-8",
    )

    cfg = Config.load(env["config_path"])
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))

    run(cfg, env["pos_path"], period, hours_path=csv_path)

    per_emp_dir = cfg.summary_path.parent / "per-employee"
    anthony = load_workbook(per_emp_dir / "Anthony Garcia.xlsx")
    ws = anthony["12.29 to 01.11.2026"]
    # Hours total = only the 12-29 shift (6.0); the 01-12 shift is outside this period.
    assert ws.cell(row=17, column=2).value == 6.0
```

- [ ] **Step 3: Run tests; verify failures**

Run: `.venv/Scripts/python -m pytest tests/test_runner.py -v`
Expected: 4 new tests fail with `ImportError: cannot import name 'UnresolvedHoursNames'` or `TypeError: run() got an unexpected keyword argument 'hours_path'`.

- [ ] **Step 4: Edit `src/tipout/runner.py`**

Replace the file with:

```python
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
```

- [ ] **Step 5: Run all runner tests; verify pass**

Run: `.venv/Scripts/python -m pytest tests/test_runner.py -v`
Expected: all PASS (previously existing + 4 new).

- [ ] **Step 6: Commit**

```bash
git add src/tipout/runner.py tests/test_runner.py tests/conftest.py
git commit -m "feat(runner): plumb --hours data through to per-employee tabs"
```

---

## Task 4: Add `--hours` flag to the CLI

**Files:**
- Modify: `src/tipout/cli.py`
- Modify: `tests/test_runner.py` (CLI-level tests live here today)

- [ ] **Step 1: Add CLI tests for the new flag**

Append to `tests/test_runner.py`:

```python
def test_cli_run_with_hours_flag(tiny_runner_env):
    from tipout.cli import main

    env = tiny_runner_env
    result = CliRunner().invoke(
        main,
        [
            "run",
            "--period", "2025-12-29:2026-01-11",
            "--config", str(env["config_path"]),
            "--pos", str(env["pos_path"]),
            "--hours", str(env["hours_path"]),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Done." in result.output

    per_emp_dir = env["summary_path"].parent / "per-employee"
    wb = load_workbook(per_emp_dir / "Anthony Garcia.xlsx")
    ws = wb["12.29 to 01.11.2026"]
    assert ws.cell(row=17, column=2).value == 6.0  # Hours total


def test_cli_writes_unknown_hours_file_on_resolution_failure(tiny_runner_env, tmp_path):
    from tipout.cli import main

    env = tiny_runner_env
    bad_csv = tmp_path / "bad_hours.csv"
    bad_csv.write_text(
        "STRANGER PERSON - WAIT Mon 12-29-2025 - Sun 01-04-2026,,,,,,,\n"
        "Start Date,Start Time,End Date,End Time,Reported Tips,Regular Hours,Overtime Hours,Duration (Hours)\n"
        '"Mon, 12-29-25",3:00 PM,"Mon, 12-29-25",10:30 PM,0,5.0,0,5.0\n'
        "Total,,,,0,5.0,0,5.0\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        main,
        [
            "run",
            "--period", "2025-12-29:2026-01-11",
            "--config", str(env["config_path"]),
            "--pos", str(env["pos_path"]),
            "--hours", str(bad_csv),
        ],
    )
    assert result.exit_code == 1
    unknowns_path = env["config_path"].parent / "unknown_hours_names.txt"
    assert unknowns_path.exists()
    assert "Stranger Person" in unknowns_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run CLI tests; verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_runner.py::test_cli_run_with_hours_flag tests/test_runner.py::test_cli_writes_unknown_hours_file_on_resolution_failure -v`
Expected: failures — `--hours` option not recognized.

- [ ] **Step 3: Edit `src/tipout/cli.py`** — add the `--hours` option and the `UnresolvedHoursNames` handler.

In the `run` command, add a new `@click.option` block (between `--pos` and `--config`):

```python
@click.option(
    "--hours",
    "hours_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to Toast Time Clock CSV (optional). Populates per-employee Hours Worked + $/hr.",
)
```

Update the `run` function signature to accept `hours_path`:

```python
def run(period_str, pos_path, config_path, hours_path):
```

Update the import line to also pull in `UnresolvedHoursNames`:

```python
    from tipout.runner import run as _run, UnresolvedNames, UnresolvedHoursNames
```

Update the `_run` call to forward `hours_path`:

```python
    try:
        _run(cfg, pos_path, period, hours_path=hours_path)
    except UnresolvedNames as exc:
        unknowns_path = config_path.parent / "unknown_names.txt"
        unknowns_path.write_text("\n".join(exc.names) + "\n", encoding="utf-8")
        click.echo(
            f"Found {len(exc.names)} unknown name(s) in the POS file for this period.",
            err=True,
        )
        click.echo(f"List written to {unknowns_path}.", err=True)
        click.echo(
            "Open roster.xlsx in Excel, add each unknown name to either the "
            "Employees sheet (as a new canonical) or the Name Aliases sheet "
            "(pointing at an existing canonical). Then re-run.",
            err=True,
        )
        raise SystemExit(1)
    except UnresolvedHoursNames as exc:
        unknowns_path = config_path.parent / "unknown_hours_names.txt"
        unknowns_path.write_text("\n".join(exc.names) + "\n", encoding="utf-8")
        click.echo(
            f"Found {len(exc.names)} unknown name(s) in the time clock CSV for this period.",
            err=True,
        )
        click.echo(f"List written to {unknowns_path}.", err=True)
        click.echo(
            "Open roster.xlsx in Excel, add each unknown name to either the "
            "Employees sheet (as a new canonical) or the Name Aliases sheet "
            "(pointing at an existing canonical). Then re-run.",
            err=True,
        )
        raise SystemExit(1)
```

- [ ] **Step 4: Run the full test suite; verify all pass**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: every test PASS, no regressions.

- [ ] **Step 5: Commit**

```bash
git add src/tipout/cli.py tests/test_runner.py
git commit -m "feat(cli): add --hours flag and unknown-hours-names handling"
```

---

## Task 5: Document `--hours` in the plugin SKILL.md

**Files:**
- Modify: `tipout-plugin/skills/tipout/SKILL.md`

- [ ] **Step 1: Update the "Running a pay period" section** in `tipout-plugin/skills/tipout/SKILL.md`.

Replace the existing code block + bullet list with:

````markdown
```bash
cd "${user_config.project_dir}"
tipout run --period 2026-01-12:2026-01-25 --pos "<POS-file.xlsx>" --hours "<TimeClock.csv>"
```

- `--period` is `YYYY-MM-DD:YYYY-MM-DD`, inclusive, must be exactly 14 days apart.
- `--pos` is the POS daily workbook path (quote it if the name has spaces).
- `--hours` is optional — when supplied, the Toast Time Clock CSV populates the `Hours Worked` column and `$/hr` cell on each per-employee period tab. Omit it and those cells stay blank.
- `--config` defaults to `./config.yaml`.
````

- [ ] **Step 2: Update the "Handling unknown names" section** to cover the hours-CSV variant.

After the existing "When this happens, present the list of unknown names" paragraph block, add:

```markdown
The same flow applies when an unknown name appears in the time clock CSV: the tool exits 1 and writes `unknown_hours_names.txt`. Add the new name as an alias or new employee in `roster.xlsx`, then re-run with the same arguments.
```

- [ ] **Step 3: Update "Full command reference"** to mention `--hours`:

Change the first bullet under "Full command reference" to:

```markdown
- `tipout run --period <start>:<end> --pos <file> [--hours <csv>] [--config <path>]` — primary command.
```

- [ ] **Step 4: Update the "Output" section** to mention the hours-related artifacts:

After the `unknown_names.txt` bullet, add:

```markdown
- `unknown_hours_names.txt` — only present when a run hit unresolved names from the time-clock CSV. Safe to delete after resolving.
- `output/per-employee/<Name>.xlsx` — one workbook per canonical employee; layout matches the hand-done `Yvonne.xlsx` reference (`Hours Worked` at col B, `$/hr` on totals row col J).
```

- [ ] **Step 5: Commit**

```bash
git add tipout-plugin/skills/tipout/SKILL.md
git commit -m "docs(skill): document --hours flag and per-employee output"
```

---

## Task 6: End-to-end smoke test with real data

**Files:** none — manual verification.

- [ ] **Step 1: Re-run the actual pay period that was just processed**

The 05.04–05.17 period tab already exists in `output/summary.xlsx`. Per the spec, the summary is append-only, but per-employee tabs are also append-only — we'd hit "tab already exists" errors. So first remove the existing per-employee tabs for this period:

```bash
.venv/Scripts/python <<'PY'
from pathlib import Path
import openpyxl

per_emp = Path("output/per-employee")
removed = 0
for f in per_emp.glob("*.xlsx"):
    wb = openpyxl.load_workbook(f)
    if "05.04 to 05.17.2026" in wb.sheetnames:
        del wb["05.04 to 05.17.2026"]
        if wb.sheetnames:
            wb.save(f)
        else:
            f.unlink()
        removed += 1
print(f"Cleared 05.04-05.17 tab from {removed} per-employee file(s).")
PY
```

Also delete `05.04 to 05.17.2026` from `output/summary.xlsx`:

```bash
.venv/Scripts/python <<'PY'
import openpyxl
wb = openpyxl.load_workbook("output/summary.xlsx")
if "05.04 to 05.17.2026" in wb.sheetnames:
    del wb["05.04 to 05.17.2026"]
    wb.save("output/summary.xlsx")
    print("Deleted 05.04-05.17 from summary.")
PY
```

- [ ] **Step 2: Run with the real POS + CSV**

```bash
.venv/Scripts/tipout run \
  --period 2026-05-04:2026-05-17 \
  --pos "2026 SD Daily Tipout Worksheet.xlsx" \
  --hours "Surfing Deer - Time Clock 05.04 to 07.17.2026.csv"
```

Expected: either `Done. ...` (clean run) or `Found N unknown name(s) in the time clock CSV` (unknowns from the CSV — handle each per the SKILL.md flow, then re-run). Note: this is real data, expect some unknowns the first time.

- [ ] **Step 3: Spot-check a per-employee file**

```bash
.venv/Scripts/python <<'PY'
import openpyxl
wb = openpyxl.load_workbook("output/per-employee/Anthony Garcia.xlsx")
ws = wb["05.04 to 05.17.2026"]
print("Header:", [ws.cell(row=2, column=c).value for c in range(1, 11)])
print("Totals:", [ws.cell(row=17, column=c).value for c in range(1, 11)])
PY
```

Expected: header row prints `['Date', 'Hours Worked', 'CC Tips', 'SA Tip Out', 'Bar Tipout', 'Total Tip Out', 'Barback', 'Bartender', 'Net Tip', '$/hr']`. Totals row has a non-zero `Hours Worked` (col 2) and a non-zero `$/hr` (col 10).

- [ ] **Step 4: Cross-check against the CSV's per-block totals**

Open `Surfing Deer - Time Clock 05.04 to 07.17.2026.csv` in a text editor; find the `ANTHONY GARCIA - WAIT` block; sum the `Duration (Hours)` column from the block's `Total` row(s) across all of Anthony's blocks. This should equal the value in cell B17 of his per-employee tab.

Report the comparison to Cooper before declaring this task complete.

---

## Self-review checklist (for the plan author — not for the executor)

Spec coverage:
- §1 architecture → Task 1 (time_clock.py), Task 2 (per_employee.py), Task 3 (runner.py), Task 4 (cli.py). ✓
- §2 parser rules → Task 1 Step 4. ✓
- §3 runner edge cases → Task 3 Step 2 (4 tests). ✓
- §4 per_employee layout → Task 2. ✓
- §5 CLI flag + error UX → Task 4. ✓
- §6 testing strategy → unit tests in Tasks 1-4, manual smoke in Task 6. ✓
- §7 Docs / file touch list → Task 5 covers the SKILL.md change. ✓

Type consistency: `HoursRow` defined Task 1; consumed Task 3 via `parse_time_clock`. `UnresolvedHoursNames` defined Task 3; raised in `_aggregate_hours` (Task 3), caught in CLI (Task 4). `hours_by_date: dict[date, float] | None` consistent across `build_grid`, `append_period_tab_for_employee`, runner.

No placeholders detected.
