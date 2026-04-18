# Surfing Deer Tip-Out Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a deterministic Python CLI (`tipout`) that reads a POS daily workbook + an hours file + a roster, and produces the 2-week summary + per-employee sheets for a given pay period, validated against a regression test harness using real historical data.

**Architecture:** Python 3.11, openpyxl for Excel I/O, pytest for tests, click for CLI, pyyaml for config. Pure functions for parsing/rollup; Excel I/O isolated at edges. Outputs append-only (never modify prior tabs). Every run archives inputs + outputs by run-ID.

**Tech Stack:** Python 3.11 · openpyxl · pytest · click · pyyaml · PyInstaller (deferred)

**Design reference:** `docs/plans/2026-04-18-surfing-deer-tipout-automation-design.md`

**Executing engineer assumptions:** Skilled developer, new to this codebase and restaurant-tip-out domain. Knows Python + pytest but not openpyxl. Read the design doc first — this plan assumes it.

---

## Phase 0 — Project setup

### Task 0.1: Create Python project skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/tipout/__init__.py`
- Create: `src/tipout/cli.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `README.md`

**Step 1: Write `pyproject.toml`**

```toml
[project]
name = "tipout"
version = "0.1.0"
description = "Surfing Deer tip-out automation"
requires-python = ">=3.11"
dependencies = [
    "openpyxl>=3.1",
    "click>=8.1",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
]

[project.scripts]
tipout = "tipout.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: Minimal CLI in `src/tipout/cli.py`**

```python
import click

@click.group()
def main():
    """Surfing Deer tip-out automation."""

@main.command()
def version():
    """Print tool version."""
    from tipout import __version__
    click.echo(__version__)

if __name__ == "__main__":
    main()
```

**Step 3: `src/tipout/__init__.py`**

```python
__version__ = "0.1.0"
```

**Step 4: Install and verify**

Run:
```
py -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/tipout version
```
Expected output: `0.1.0`

**Step 5: `README.md` with quickstart**

Brief. Installation + `tipout --help`. 15 lines max.

**Step 6: Commit**

```
git add pyproject.toml src/ tests/ README.md
git commit -m "chore: scaffold Python project with click CLI"
```

---

### Task 0.2: Test harness smoke test

**Files:**
- Create: `tests/test_smoke.py`

**Step 1: Write smoke test**

```python
from tipout import __version__

def test_version_exists():
    assert __version__ == "0.1.0"
```

**Step 2: Run**

```
.venv/Scripts/pytest -v
```
Expected: 1 passed.

**Step 3: Commit**

```
git add tests/
git commit -m "test: smoke test harness verified"
```

---

## Phase 1 — POS parser

The POS file is the trickiest input. Before parsing, manually open `2026 SD Daily Tipout Worksheet.xlsx` in Excel and read the design doc's "Data observed" section. Key facts:
- Each weekly tab has 7 day-blocks, arranged side-by-side (3 blocks in the first row of blocks, then the next 3, then 1 — actually all 7 across; each block is ~10 columns wide starting at col A for Mon, col K for Tue, etc. — **verify by reading headers, not by counting columns**).
- Column labels per block: `PM | <Day> | CC Tips | Party OR Cash RCP | SA Tip Out | Bar Tipout | TotalTip Out | Barback | Bartender | Net tip`.
- Row 4 has the column headers. Row 3 has the date. Rows 5–N have worker rows. Rows 33–41 have the deposit reconciliation block (ignore for now).
- Blank name or zero Net Tip → skip row.
- **Read dates from row 3 cell values, never from tab names.**

### Task 1.1: Day-block detection by header

**Files:**
- Create: `src/tipout/pos_parser.py`
- Create: `tests/test_pos_parser.py`
- Create: `tests/fixtures/tiny_pos.xlsx` (hand-build a 1-day fixture — see step 1 below)

**Step 1: Build `tests/fixtures/tiny_pos.xlsx` by hand**

Open Excel. Create one sheet named `12.29 to 01.04.2026`. Populate exactly one day-block in columns A–J:

- Row 1 col A: `Surfing Deer Daily Cash`
- Row 3 col B: date `2025-12-29` (real date cell, not text)
- Row 3 col D: `Monday`
- Row 4 headers: `PM | Monday | CC Tips | Party | SA Tip Out | Bar Tipout | TotalTip Out | Barback | Bartender | Net tip`
- Row 5: ` | Anthony | 583 | | 73.81 | 34.8 | 108.61 | | | 474.39`
- Row 6: ` | Jake | 219.87 | | 10.25 | | 10.25 | | 65.2 | 274.82`
- Row 7: blank

Save as `tests/fixtures/tiny_pos.xlsx`. **This is the only fixture that goes in git** (tiny, synthetic-looking enough; double-check names are common first names — they are).

Actually: since `*.xlsx` is gitignored, add an exception to `.gitignore`:

```
!tests/fixtures/tiny_pos.xlsx
```

**Step 2: Write failing test**

```python
# tests/test_pos_parser.py
from pathlib import Path
from tipout.pos_parser import parse_workbook

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_pos.xlsx"

def test_parses_single_day_block():
    rows = parse_workbook(FIXTURE)
    assert len(rows) == 2
    anthony = next(r for r in rows if r.raw_name == "Anthony")
    assert anthony.date.isoformat() == "2025-12-29"
    assert anthony.cc_tips == 583.0
    assert anthony.sa_tip_out == 73.81
    assert anthony.bar_tipout == 34.8
    assert anthony.net_tip == 474.39
    assert anthony.is_party is False
```

**Step 3: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_pos_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tipout.pos_parser'`.

**Step 4: Write minimal parser**

```python
# src/tipout/pos_parser.py
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook

EXPECTED_HEADERS = [
    "CC Tips", "SA Tip Out", "Bar Tipout",
    "TotalTip Out", "Barback", "Bartender", "Net tip",
]

@dataclass
class ShiftRow:
    date: date
    raw_name: str
    cc_tips: float
    party: float
    sa_tip_out: float
    bar_tipout: float
    total_tip_out: float
    barback: float
    bartender: float
    net_tip: float
    is_party: bool  # True if Party column had value (vs Cash RCP)

def parse_workbook(path: Path) -> list[ShiftRow]:
    wb = load_workbook(path, data_only=True)
    rows: list[ShiftRow] = []
    for sheet_name in wb.sheetnames:
        if sheet_name.strip() in {"Bank Master", "Sheet1"}:
            continue
        ws = wb[sheet_name]
        rows.extend(_parse_sheet(ws))
    return rows

def _parse_sheet(ws) -> list[ShiftRow]:
    blocks = _find_day_blocks(ws)
    out: list[ShiftRow] = []
    for block in blocks:
        out.extend(_parse_block(ws, block))
    return out

def _find_day_blocks(ws) -> list[dict]:
    """Return list of {start_col, headers: dict[label, col], date: date}."""
    header_row = 4
    blocks = []
    c = 1
    max_c = ws.max_column
    while c <= max_c:
        headers = {}
        for offset in range(12):  # scan up to 12 cols for a block's headers
            v = ws.cell(row=header_row, column=c + offset).value
            if isinstance(v, str) and v.strip() in {
                "CC Tips", "Party", "Cash RCP", "SA Tip Out", "Bar Tipout",
                "TotalTip Out", "Barback", "Bartender", "Net tip",
            }:
                headers[v.strip()] = c + offset
        if all(h in headers for h in EXPECTED_HEADERS):
            date_cell = ws.cell(row=3, column=c + 1).value  # date typically at col+1
            if not hasattr(date_cell, "date"):
                # fall back: search for a date in row 3 within block
                for offset in range(12):
                    v = ws.cell(row=3, column=c + offset).value
                    if hasattr(v, "date"):
                        date_cell = v
                        break
            blocks.append({
                "start_col": c,
                "headers": headers,
                "date": date_cell.date() if hasattr(date_cell, "date") else None,
            })
            c += 10  # advance past this block
        else:
            c += 1
    return blocks

def _parse_block(ws, block) -> list[ShiftRow]:
    out = []
    name_col = block["start_col"] + 1
    for r in range(5, 33):  # rows 5–32; row 33+ is reconciliation
        raw_name = ws.cell(row=r, column=name_col).value
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        def g(label):
            col = block["headers"].get(label)
            if col is None:
                return 0.0
            v = ws.cell(row=r, column=col).value
            return float(v) if isinstance(v, (int, float)) else 0.0
        net = g("Net tip")
        if net == 0.0 and g("CC Tips") == 0.0:
            continue
        is_party = "Party" in block["headers"] and g("Party") > 0
        out.append(ShiftRow(
            date=block["date"],
            raw_name=raw_name.strip(),
            cc_tips=g("CC Tips"),
            party=g("Party") if is_party else 0.0,
            sa_tip_out=g("SA Tip Out"),
            bar_tipout=g("Bar Tipout"),
            total_tip_out=g("TotalTip Out"),
            barback=g("Barback"),
            bartender=g("Bartender"),
            net_tip=net,
            is_party=is_party,
        ))
    return out
```

**Step 5: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_pos_parser.py -v`
Expected: PASS.

**Step 6: Commit**

```
git add src/tipout/pos_parser.py tests/test_pos_parser.py tests/fixtures/tiny_pos.xlsx .gitignore
git commit -m "feat(parser): detect day-blocks by header content and extract shift rows"
```

---

### Task 1.2: Schema drift detection

**Files:**
- Modify: `src/tipout/pos_parser.py`
- Modify: `tests/test_pos_parser.py`

**Step 1: Test — missing header label raises**

Add to `tests/test_pos_parser.py`:

```python
import pytest
from tipout.pos_parser import parse_workbook, SchemaError
# In code editor, build a fixture programmatically with openpyxl that lacks 'Net tip' header.

def test_schema_drift_raises(tmp_path):
    from openpyxl import Workbook
    from datetime import date as _date
    wb = Workbook()
    ws = wb.active
    ws.title = "test week"
    ws["A1"] = "Surfing Deer"
    ws["B3"] = _date(2026, 1, 5)
    ws["A4"] = "PM"
    ws["B4"] = "Monday"
    ws["C4"] = "CC Tips"
    ws["J4"] = "WRONG HEADER"  # should be "Net tip"
    p = tmp_path / "broken.xlsx"
    wb.save(p)
    with pytest.raises(SchemaError):
        parse_workbook(p)
```

**Step 2: Run — FAIL** (SchemaError not defined yet).

**Step 3: Implement**

Add to `pos_parser.py`:

```python
class SchemaError(RuntimeError):
    pass
```

Modify `_find_day_blocks`: after scanning, if ZERO blocks found on a sheet that has a date in row 3, raise `SchemaError(f"No valid day-blocks in {ws.title!r}")`.

**Step 4: Run — PASS.**

**Step 5: Commit**

```
git commit -am "feat(parser): raise SchemaError when a sheet has no valid day-blocks"
```

---

### Task 1.3: Multi-day and multi-week fixtures

Extend the parser tests using **real** `2026 SD Daily Tipout Worksheet.xlsx` copied into `tests/fixtures/real_pos_sample.xlsx`. This file is gitignored.

**Step 1:** Copy real file locally:
```
cp "2026 SD Daily Tipout Worksheet.xlsx" tests/fixtures/real_pos_sample.xlsx
```

**Step 2: Add tests that assert known counts/values**

```python
def test_real_workbook_parses(skipif_no_real):
    path = Path(__file__).parent / "fixtures" / "real_pos_sample.xlsx"
    if not path.exists():
        pytest.skip("real fixture not present")
    rows = parse_workbook(path)
    # from known data in the first day-block of 12.29:
    dec29 = [r for r in rows if r.date.isoformat() == "2025-12-29"]
    assert any(r.raw_name == "Anthony" and r.net_tip == 474.39 for r in dec29)
    assert any(r.raw_name == "Jake" for r in dec29)
    # Party example from 03.02 for "Patrick (Party)":
    mar2 = [r for r in rows if r.date.isoformat() == "2026-03-02" and "Patrick" in r.raw_name]
    assert any(r.is_party for r in mar2)
```

**Step 3: Run and fix any regressions.** Iterate on parser until real data parses.

**Step 4: Commit** parser fixes.

---

## Phase 2 — Roster & name resolution

### Task 2.1: Roster loader

**Files:**
- Create: `src/tipout/roster.py`
- Create: `tests/test_roster.py`
- Create: `tests/fixtures/tiny_roster.xlsx` (committed; synthetic)

**Step 1: Build `tiny_roster.xlsx` programmatically in a fixture helper**

Add to `tests/conftest.py`:

```python
from datetime import date as _date
from openpyxl import Workbook
import pytest

@pytest.fixture
def tiny_roster(tmp_path):
    wb = Workbook()
    emp = wb.active
    emp.title = "Employees"
    emp.append(["Canonical Name", "Role", "Active From", "Active To", "Notes"])
    emp.append(["Anthony Garcia", "server", _date(2025, 1, 1), None, ""])
    emp.append(["Jake Purvis", "bartender", _date(2025, 1, 1), None, ""])
    emp.append(["Kristin Bartosic", "bartender", _date(2025, 1, 1), None, ""])
    aliases = wb.create_sheet("Name Aliases")
    aliases.append(["Raw Name", "Canonical Name"])
    aliases.append(["Anthony", "Anthony Garcia"])
    aliases.append(["anthony", "Anthony Garcia"])
    aliases.append(["Jake", "Jake Purvis"])
    aliases.append(["Kristin", "Kristin Bartosic"])
    aliases.append(["kristin", "Kristin Bartosic"])
    path = tmp_path / "roster.xlsx"
    wb.save(path)
    return path
```

**Step 2: Test — load roster, resolve known name, unknown returns None**

```python
from tipout.roster import load_roster

def test_load_roster_resolves_known_alias(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.resolve("Anthony") == "Anthony Garcia"
    assert roster.resolve("anthony") == "Anthony Garcia"
    assert roster.resolve("Jake") == "Jake Purvis"

def test_unknown_name_returns_none(tiny_roster):
    roster = load_roster(tiny_roster)
    assert roster.resolve("Maya") is None
```

**Step 3: Run — FAIL.**

**Step 4: Implement**

```python
# src/tipout/roster.py
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from openpyxl import load_workbook

@dataclass
class Employee:
    canonical: str
    role: str
    active_from: date | None
    active_to: date | None

@dataclass
class Roster:
    employees: dict[str, Employee]
    aliases: dict[str, str]  # raw -> canonical

    def resolve(self, raw: str) -> str | None:
        return self.aliases.get(raw) or self.aliases.get(raw.strip())

def load_roster(path: Path) -> Roster:
    wb = load_workbook(path, data_only=True)
    emps: dict[str, Employee] = {}
    for row in wb["Employees"].iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        name, role, af, at, *_ = row
        emps[name] = Employee(
            canonical=name,
            role=role or "",
            active_from=af if isinstance(af, date) else None,
            active_to=at if isinstance(at, date) else None,
        )
    aliases: dict[str, str] = {}
    for row in wb["Name Aliases"].iter_rows(min_row=2, values_only=True):
        if not row or not row[0] or not row[1]:
            continue
        aliases[row[0]] = row[1]
    return Roster(employees=emps, aliases=aliases)
```

**Step 5: Run — PASS.**

**Step 6: Commit**

```
git commit -am "feat(roster): load employees and name aliases from xlsx"
```

---

### Task 2.2: First-name ambiguity

**Files:** modify `src/tipout/roster.py` and tests.

**Step 1: Test — two active Andrews in roster, resolving "Andrew" raises**

Extend `tiny_roster` fixture to add `Andrew Roberts` and `Andrew Neita`, both active, both with alias `Andrew` pointing to different canonicals — OR test that if no alias entry exists and the roster has 2+ Andrews, resolving "Andrew" raises `AmbiguousName`.

Decision: the alias table IS the source of truth. If "Andrew" alias maps to "Andrew Roberts" explicitly, use it. Only raise if no alias AND multiple first-name matches. (Edit: keep resolve() returning None for unknown; add a separate `fuzzy_candidates(raw)` method that returns possible canonicals for when the caller needs to report ambiguity.)

**Step 2: Implement `fuzzy_candidates`**

```python
def fuzzy_candidates(self, raw: str) -> list[str]:
    """Return canonicals whose first name matches raw (case-insensitive, ignoring role tags like '(Xen)')."""
    first = raw.split()[0].strip().lower().rstrip(",")
    return [
        e.canonical for e in self.employees.values()
        if e.canonical.split()[0].lower() == first
    ]
```

**Step 3: Tests** for: one match, two matches, zero matches.

**Step 4: Commit.**

---

### Task 2.3: Unknown-name collection

**Files:**
- Create: `src/tipout/name_resolution.py`
- Create: `tests/test_name_resolution.py`

**Step 1: Test — resolving a list of raw names returns resolved + unknown lists**

```python
from tipout.name_resolution import resolve_all

def test_resolve_all_separates_known_and_unknown(tiny_roster):
    from tipout.roster import load_roster
    roster = load_roster(tiny_roster)
    resolved, unknown = resolve_all(["Anthony", "Jake", "Maya", "Unknown"], roster)
    assert resolved == {"Anthony": "Anthony Garcia", "Jake": "Jake Purvis"}
    assert set(unknown) == {"Maya", "Unknown"}
```

**Step 2: Implement**

```python
# src/tipout/name_resolution.py
from tipout.roster import Roster

def resolve_all(raw_names: list[str], roster: Roster) -> tuple[dict[str, str], list[str]]:
    resolved: dict[str, str] = {}
    unknown: list[str] = []
    for raw in set(raw_names):
        canon = roster.resolve(raw)
        if canon:
            resolved[raw] = canon
        else:
            unknown.append(raw)
    return resolved, sorted(unknown)
```

**Step 3: PASS. Commit.**

---

## Phase 3 — Hours file

### Task 3.1: Hours file loader + join

**Files:**
- Create: `src/tipout/hours.py`
- Create: `tests/test_hours.py`
- Create synthetic `tests/fixtures/tiny_hours.xlsx` via conftest fixture.

**Step 1: conftest fixture `tiny_hours`** — 3 rows: (Anthony Garcia, 2025-12-29, 7.2), (Jake Purvis, 2025-12-29, 6.5), (Kristin Bartosic, 2025-12-29, 7.0).

**Step 2: Tests:**
- `load_hours(path)` returns list of `(canonical, date, hours)` with aliases resolved.
- Joining against shift rows matches correctly.
- Shift row with tips but no hours → `MissingHours` raised.
- Hours row with no tips → `MissingTips` raised (both are hard stops).

**Step 3: Implement**

```python
# src/tipout/hours.py
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from openpyxl import load_workbook

from tipout.roster import Roster

@dataclass
class HoursEntry:
    canonical: str
    date: date
    hours: float

class MissingHours(RuntimeError): pass
class MissingTips(RuntimeError): pass

def load_hours(path: Path, roster: Roster) -> tuple[list[HoursEntry], list[str]]:
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    entries = []
    unknown = []
    headers = [c.value for c in ws[1]]
    for row in ws.iter_rows(min_row=2, values_only=True):
        name, d, h = row[0], row[1], row[2]
        if not name:
            continue
        canon = roster.resolve(name)
        if not canon:
            unknown.append(name)
            continue
        entries.append(HoursEntry(canonical=canon, date=d.date() if hasattr(d, "date") else d, hours=float(h)))
    return entries, sorted(set(unknown))

def validate_join(shift_rows, hours_entries, period_start, period_end):
    """Raise MissingHours/MissingTips if any (canonical, date) in period has one side without the other."""
    from collections import defaultdict
    by_shift = defaultdict(lambda: {"tips": False, "hours": False})
    for r in shift_rows:
        if period_start <= r.date <= period_end:
            by_shift[(r.canonical_name, r.date)]["tips"] = True
    for h in hours_entries:
        if period_start <= h.date <= period_end:
            by_shift[(h.canonical, h.date)]["hours"] = True
    missing_hours = [k for k, v in by_shift.items() if v["tips"] and not v["hours"]]
    missing_tips = [k for k, v in by_shift.items() if v["hours"] and not v["tips"]]
    if missing_hours:
        raise MissingHours(missing_hours)
    if missing_tips:
        raise MissingTips(missing_tips)
```

(Note: `shift_rows` here need a `canonical_name` field — add it to `ShiftRow` and resolve via roster before calling validate_join. Small refactor.)

**Step 4: Run tests. Commit.**

---

## Phase 4 — Rollup + output emission

### Task 4.1: Pay-period model + config

**Files:**
- Create: `src/tipout/period.py`
- Create: `tests/test_period.py`
- Create: `src/tipout/config.py`
- Create: `tests/fixtures/tiny_config.yaml`

**Step 1: Test — given anchor 2025-12-29, period index 0 is 12/29–01/11.**

```python
from datetime import date
from tipout.period import PayPeriod

def test_pay_period_from_anchor():
    p = PayPeriod.from_anchor(anchor=date(2025, 12, 29), containing_date=date(2026, 1, 5))
    assert p.start == date(2025, 12, 29)
    assert p.end == date(2026, 1, 11)
```

**Step 2: Implement**

```python
# src/tipout/period.py
from dataclasses import dataclass
from datetime import date, timedelta

@dataclass(frozen=True)
class PayPeriod:
    start: date
    end: date  # inclusive

    @classmethod
    def from_anchor(cls, anchor: date, containing_date: date) -> "PayPeriod":
        delta_days = (containing_date - anchor).days
        periods_in = delta_days // 14
        start = anchor + timedelta(days=14 * periods_in)
        return cls(start=start, end=start + timedelta(days=13))

    @classmethod
    def from_dates(cls, start: date, end: date) -> "PayPeriod":
        assert (end - start).days == 13, "pay period must be 14 days inclusive"
        return cls(start=start, end=end)
```

Config loader reads `anchor_date` from yaml.

**Step 3: Commit.**

---

### Task 4.2: 2-week summary tab builder

**Files:**
- Create: `src/tipout/summary.py`
- Create: `tests/test_summary.py`

Summary structure: col A = canonical name, col B = raw-name-as-seen (pick most-recent raw spelling for that employee in the period), then 14 (date, blank) pairs, then a total column.

**Step 1: Test** — given 3 shift rows across 2 employees in a period, build the expected row layout and column-31 totals.

**Step 2: Implement** the builder that returns a 2D list of values, not yet writing Excel.

**Step 3: Test for stable ordering** — employees sorted by order they appear in roster's `Employees` sheet.

**Step 4: Commit.**

---

### Task 4.3: 2-week summary Excel writer (append-only)

**Files:**
- Modify: `src/tipout/summary.py`
- `tests/test_summary.py`

**Step 1: Test** — open existing summary file (fixture with one pre-existing period tab), call writer, verify new tab added without touching old.

**Step 2: Implement**

```python
def append_period_tab(summary_path: Path, period: PayPeriod, shift_rows, roster, hours_entries):
    wb = load_workbook(summary_path) if summary_path.exists() else Workbook()
    tab_name = _tab_name(period)
    if tab_name in wb.sheetnames:
        raise ValueError(f"Tab {tab_name!r} already exists — delete to re-run")
    ws = wb.create_sheet(tab_name)
    grid = build_grid(period, shift_rows, roster)  # from Task 4.2
    for r, row in enumerate(grid, start=1):
        for c, val in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=val)
    wb.save(summary_path)
```

**Step 3: Commit.**

---

### Task 4.4: Per-employee file writer

Same append-only pattern, one file per active employee for the period. File created if missing.

**Files:**
- Create: `src/tipout/per_employee.py`
- Tests.

Columns per the design doc (no `308`). Row 20 totals. Row 23 col C blank (was historical artifact). Row 23 col I: `=SUM(I5:I18)/SUM(B5:B18)` as an Excel formula — or compute Python-side and write as float. Pick Python-side for determinism.

**Test, implement, commit.**

---

## Phase 5 — Orchestration & CLI

### Task 5.1: `tipout run` end-to-end

**Files:**
- Modify: `src/tipout/cli.py`
- Create: `src/tipout/runner.py`
- Tests: `tests/test_runner.py`

**Step 1: Test** — full pipeline with tiny fixtures end-to-end: parser → roster resolve → hours join → period filter → summary tab + per-employee file written. Assert expected cells in output.

**Step 2: Implement `runner.run(config, pos_path, hours_path, period)`**

```python
# src/tipout/runner.py
from pathlib import Path
from tipout.pos_parser import parse_workbook
from tipout.roster import load_roster
from tipout.name_resolution import resolve_all
from tipout.hours import load_hours, validate_join
from tipout.summary import append_period_tab
from tipout.per_employee import append_period_tab_for_employee
from tipout.period import PayPeriod

class UnresolvedNames(RuntimeError):
    def __init__(self, names: list[str]):
        self.names = names
        super().__init__(f"Unresolved: {names}")

def run(config, pos_path: Path, hours_path: Path, period: PayPeriod):
    roster = load_roster(config.roster_path)
    shift_rows = parse_workbook(pos_path)
    raw_names = {r.raw_name for r in shift_rows}
    resolved, unknown = resolve_all(list(raw_names), roster)
    if unknown:
        raise UnresolvedNames(unknown)
    for r in shift_rows:
        r.canonical_name = resolved[r.raw_name]
    hours_entries, hours_unknown = load_hours(hours_path, roster)
    if hours_unknown:
        raise UnresolvedNames(hours_unknown)
    validate_join(shift_rows, hours_entries, period.start, period.end)
    period_rows = [r for r in shift_rows if period.start <= r.date <= period.end]
    append_period_tab(config.summary_path, period, period_rows, roster, hours_entries)
    for canonical in sorted({r.canonical_name for r in period_rows}):
        per_emp_path = config.per_employee_dir / f"{canonical}.xlsx"
        append_period_tab_for_employee(
            per_emp_path, period, canonical,
            [r for r in period_rows if r.canonical_name == canonical],
            [h for h in hours_entries if h.canonical == canonical],
        )
```

**Step 3: CLI `tipout run --period 2026-04-06:2026-04-19` picks up paths from `config.yaml`.**

**Step 4: Commit.**

---

### Task 5.2: JSON status output + pending_names flow

**Files:** modify `cli.py` and `runner.py`.

**Step 1: Test** — run with unknown name present, assert:
1. No deliverables written.
2. `pending_names.json` written with expected structure.
3. CLI stdout is one JSON object with `status="awaiting_input"`, exit code non-zero.

**Step 2: Implement** the exception-to-JSON mapping at the CLI layer.

**Step 3: Test the complete resume flow** — write `pending_answers.json`, re-run, roster gets updated, pipeline completes.

**Step 4: Commit.**

---

## Phase 6 — Anomaly checks

### Task 6.1: Tip-pool imbalance check

**Files:**
- Create: `src/tipout/anomalies.py`
- Tests.

Pure function: input = list of shift rows for one day, output = list of anomaly records.

Check 1: `sum(SA Tip Out across tier-1 rows) ≈ sum(Net Tips received by support tier rows)` within $0.50.

**Test, implement, commit.**

### Task 6.2: Server net-tip math check

`net_tip ≈ cc_tips + party - total_tip_out` ± $0.01 for server-tier rows. **Test, implement, commit.**

### Task 6.3: Outlier $/hour (<$10, >$100)

**Test, implement, commit.**

### Task 6.4: Period-over-period drop check

Compare current period total to employee's prior-4-periods rolling average. Flag if drop > 60% with hours > 0. Requires reading prior tabs of the summary file. **Test, implement, commit.**

### Task 6.5: Duplicate-row check

Same canonical on same date, different tip numbers → flag. **Test, implement, commit.**

### Task 6.6: Anomaly report writer

Emit `anomaly_report.xlsx` listing all anomalies for a run. **Test, implement, commit.**

---

## Phase 7 — Regression harness

### Task 7.1: Fixture layout + loader

**Files:**
- Create: `tests/fixtures/periods/<period>/README.md` (describes each fixture)
- Create: `tests/regression.py`
- Create: `src/tipout/cli.py` `test` command

Structure per period:
```
tests/fixtures/periods/2025-12-29_to_2026-01-11/
  input_pos.xlsx
  input_hours.xlsx
  input_roster.xlsx
  expected/
    summary_tab.xlsx      # single-tab workbook with just this period's tab
    per_employee/<Name>.xlsx  # per-employee file, just this period's tab
```

All period fixtures gitignored (contain real names + wages).

**Step 1: Build one fixture** for `2025-12-29_to_2026-01-11`:
- Copy POS workbook (trim to only that weekly tab + next weekly tab) as `input_pos.xlsx`.
- Extract hours from the existing per-employee files (Yvonne etc.) where available; for staff without existing files, hand-construct plausible hours.
- Build roster from the 2-week summary's alias column (A↔B).
- Extract the period's tab from the existing 2-week summary as `expected/summary_tab.xlsx`.
- For each employee with a file, extract that period's tab only.
- Scrub `308` artifact from expected per-employee files.

**Step 2: Runner**

```python
# tests/regression.py
def run_fixture(period_dir: Path) -> list[str]:
    """Run full pipeline against fixture. Return list of diff strings vs expected/. Empty list = pass."""
```

**Step 3: `tipout test` command** iterates all fixtures under `tests/fixtures/periods/`.

**Step 4: Commit**.

### Task 7.2: Cell-level differ

Compares two workbooks cell-by-cell:
- Exact match for strings, dates, bools.
- Numbers: tolerance ±0.005.
- Formatting-only differences ignored.
- Returns list of `(sheet, cell_ref, expected, actual)` tuples.

**Test, implement, commit.**

### Task 7.3: Iteratively add fixtures for all 8 historical periods

Each fixture add is its own commit. Expect bugs surfaced by each; fix in parser/rollup/emitter. The `tipout test` suite is green when all 8 periods match within tolerance.

**This is the single most important milestone.** Nothing ships until it's green.

---

## Phase 8 — Audit trail

### Task 8.1: Run-ID + input archival

**Files:**
- Create: `src/tipout/archive.py`

Before any output is written, archive:
- Copy of input POS file → `archive/<run-id>/input_pos.xlsx`
- Copy of input hours → `archive/<run-id>/input_hours.xlsx`
- Copy of roster → `archive/<run-id>/roster.xlsx`
- SHA-256 of each → `archive/<run-id>/hashes.json`
- `run.json` with script version, timestamps, operator answers, period, config hash.

After outputs written, copy them into `archive/<run-id>/outputs/`.

**Tests, implement, commit.**

### Task 8.2: Archive is read-only

On POSIX, chmod 0o444. On Windows, use `stat.S_IREAD`. **Test, commit.**

---

## Phase 9 — CLI polish + error surfacing

### Task 9.1: Human-readable stdout when not invoked by Cowork

Add `--json` flag. Default output is friendly text. `--json` output is strict JSON for Cowork.

**Tests, commit.**

### Task 9.2: `tipout doctor`

Verify: Python version, openpyxl available, config.yaml parses, roster.xlsx loads, test suite status. **Commit.**

---

## Out of scope (future plans)

- PyInstaller bundle (`tipout.exe`) — separate deployment plan.
- Cowork playbook markdown — separate plan once v1 runs end-to-end.
- WVM / Watersound — separate plan; different parser, same downstream.
- Monthly/yearly rollups — separate plan.
- Email delivery of per-employee sheets — separate plan.
- Per-employee file password protection — separate plan.

---

## Definition of done for v1

- [ ] `tipout run --period <dates>` produces summary tab + per-employee tabs matching existing hand-done output to ±$0.005.
- [ ] `tipout test` green against all 8 historical pay periods.
- [ ] Unknown names trigger JSON `awaiting_input`, resume flow via `pending_answers.json` works.
- [ ] Hours/tips mismatch is a hard stop with clear error.
- [ ] Schema drift on POS file is a hard stop.
- [ ] Every run produces `archive/<run-id>/` with inputs + outputs + hashes.
- [ ] Anomalies emit to `anomaly_report.xlsx` without blocking output.
- [ ] README documents local usage.
