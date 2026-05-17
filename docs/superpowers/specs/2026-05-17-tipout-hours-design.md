# Tipout — Add Hours Worked to per-employee sheets

**Date:** 2026-05-17
**Status:** Spec, awaiting implementation
**Author:** Cooper + Claude

## Problem

Per-employee workbooks under `output/per-employee/<canonical>.xlsx` currently show daily tip flows but not hours. The hand-done `Yvonne.xlsx` reference workbook places `Hours Worked` between Date and CC Tips and computes `$/hr = Net Tip total ÷ Hours total`. We want to match that layout, sourcing hours from the Toast Time Clock CSV (e.g. `Surfing Deer - Time Clock 05.04 to 07.17.2026.csv`).

## Scope

In scope:
- Parse the Toast Time Clock CSV.
- Insert a `Hours Worked` column at position B of each per-employee period tab.
- Add a `$/hr` cell on the totals row, to the right of Net Tip.
- New optional CLI flag `--hours <csv>`.
- Strict name resolution: an unmatched CSV name blocks the run, parallel to the existing POS unknown-names flow.

Out of scope:
- Renaming or reordering any existing tip columns.
- Hours on the 2-week summary tab (`output/summary.xlsx`).
- Adding a `Serv As` column.
- Inferring hours when the CSV is absent.

## Design

### Architecture

```
src/tipout/
├── time_clock.py       NEW — parses Toast CSV → list[HoursRow]
├── runner.py           MODIFIED — accepts hours_path; new UnresolvedHoursNames exception
├── per_employee.py     MODIFIED — Hours Worked col B + $/hr on totals row
└── cli.py              MODIFIED — --hours flag; writes unknown_hours_names.txt on error
```

Hours data is its own domain (different source, different cardinality from POS rows), so it lives in its own module. It flows through the pipeline as a `dict[(canonical, date), float]` — never mixed into `ShiftRow`.

### `time_clock.py`

Public surface:

```python
@dataclass(frozen=True)
class HoursRow:
    raw_name: str       # title-cased from CSV's UPPERCASE, e.g. "Andrew Roberts"
    date: date          # from the shift's Start Date
    hours: float        # CSV's Duration (Hours) value

def parse_time_clock(path: Path) -> list[HoursRow]: ...
```

Parsing rules:

- The CSV is **block-structured**: every block starts with a row like `<NAME> - <ROLE> Mon 05-04-2026 - Sun 05-17-2026,,,,,,,` followed by a header row, then shift rows, then a `Total,,,,...` row.
- **Name** = the first cell of the block-header row, split on ` - `, take everything before. Apply `.title()`. The role suffix is discarded — multiple roles per person sum together (Q5-A).
- **Shift rows**: `Start Date` parsed as `"%a, %m-%d-%y"` (e.g. `"Fri, 05-08-26"`), `Duration (Hours)` → `hours`. Rows whose Start Date is the literal `"Total"` are skipped. Blank rows skipped.
- **Shifts crossing midnight** attribute to **Start Date** (e.g. a shift ending at `Sat 12:03 AM` after starting `Fri 3:21 PM` counts as Friday).
- The CSV's outer date-range in the block header is **informational**; we filter by pay period downstream using actual shift dates.

The parser does no roster resolution — it returns raw rows. Resolution happens in the runner so the same `Roster` instance is used for both POS and hours.

### `runner.py` changes

```python
class UnresolvedHoursNames(RuntimeError):
    def __init__(self, names: list[str]): ...

def run(
    config: Config,
    pos_path: Path,
    period: PayPeriod,
    hours_path: Path | None = None,    # NEW
) -> None: ...
```

Flow:

1. Load roster.
2. Parse POS, resolve names, raise `UnresolvedNames` on misses (unchanged).
3. **If `hours_path` is set**:
   a. Parse with `parse_time_clock`.
   b. Filter rows to `period.start <= row.date <= period.end`.
   c. Resolve each row's `raw_name` via `roster.resolve()`. Collect unresolved names. If any, raise `UnresolvedHoursNames(unresolved)`.
   d. Aggregate to `hours_by_canonical: dict[str, dict[date, float]]` — sum across roles and across multiple shifts on the same day.
4. Write the summary tab (unchanged).
5. For each canonical with POS shifts in the period, call `append_period_tab_for_employee(..., hours_by_date=hours_by_canonical.get(canon))`.

**Decisions for edge cases:**

- **CSV present, person has hours but no POS tips for the period.** No per-employee tab is created (today's behavior — tabs are only generated for canonicals with POS shifts). Their hours go nowhere. This is acceptable for v1: a tab without tips has nothing to report on. We may revisit if managers complain.
- **CSV present, person has POS tips but no hours.** Tab is written with the Hours column entirely blank and the `$/hr` cell blank. (No error — that person just wasn't on the time clock for those shifts.)
- **CSV's date range doesn't overlap the requested pay period.** No error, no warning. The hours dict is empty; every tab gets blank Hours. (We can add a warning later if this turns into a foot-gun.)
- **`hours_path` is `None`.** Every per-employee tab is written as it is today: no Hours column, no `$/hr` cell. The CLI tolerates running without `--hours`.

### `per_employee.py` changes

Column layout becomes (1-indexed):

| Col | Header |
|---|---|
| A | Date |
| B | **Hours Worked** ← NEW |
| C | CC Tips |
| D | SA Tip Out |
| E | Bar Tipout |
| F | Total Tip Out |
| G | Barback |
| H | Bartender |
| I | Net Tip |
| J | **$/hr** ← NEW (totals row only — header label, totals-row value) |

Layout constants update: `TOTAL_COLS = 10`. New column-width entry: `"B": 12.0`, `"J": 9.0`. All existing constants for the tip columns shift right by one.

`build_grid` signature:

```python
def build_grid(
    period: PayPeriod,
    canonical: str,
    shift_rows: list[ShiftRow],
    hours_by_date: dict[date, float] | None = None,    # NEW
) -> list[list[Any]]: ...
```

Behavior:

- When `hours_by_date is None`: column B and column J are written as empty (header row gets the labels regardless, so column count is stable). Actually — see open question below.
- When provided: each day row in col B gets `_round2(hours_by_date.get(d, 0.0))` if nonzero, else blank. The totals row gets `sum(hours_by_date.values())` in col B.
- `$/hr` totals-row cell = `net_tip_total / hours_total` rounded to 2 decimals when `hours_total > 0`, blank otherwise. The header for col J is `$/hr`.

The grid stays at 14 data rows + 1 totals row regardless of presence of hours, so `_apply_styling` only needs minor adjustments for the new column count and the new `$/hr` cell format.

**Open question (for review):** when `hours_by_date is None`, should we still write columns B and J at all? Two options:
- **Always write 10 columns.** Layout is stable across runs; column B and J are blank when hours weren't provided.
- **Conditionally write 8 or 10 columns.** No empty column B for hours-free runs.

Default in this spec: **always write 10 columns**. Consistency across periods is more valuable than saving an empty column on legacy runs. (Easy to flip if Cooper disagrees.)

### `cli.py` changes

```bash
tipout run --period <P> --pos <xlsx> [--hours <csv>] [--config <path>]
```

If `runner.run` raises `UnresolvedHoursNames`:

1. Write `unknown_hours_names.txt` (one name per line) in CWD.
2. Print: `Found N unknown name(s) in the time clock CSV for this period. List written to unknown_hours_names.txt. Open roster.xlsx in Excel, add each unknown name to either the Employees sheet (as a new canonical) or the Name Aliases sheet (pointing at an existing canonical). Then re-run.`
3. Exit 1.

Mirrors the existing POS unknown-names UX.

## Testing

New unit tests:

- `tests/test_time_clock.py`:
  - Parse a small fixture CSV with two blocks (different roles for the same person), a shift that crosses midnight, a Total row, and a blank-row separator. Assert correct `HoursRow` list including title-casing.
  - Parse fixture with a malformed block header (no ` - ` separator) — assert clean failure.

- `tests/test_per_employee.py` (extend existing):
  - `build_grid` with `hours_by_date=None` produces today's layout extended to 10 columns with col B and J blank.
  - `build_grid` with hours produces correct per-day values and totals.
  - `$/hr` cell is blank when hours total is 0, populated otherwise.
  - Per-day Hours cell is blank when 0, populated when nonzero (matches existing tip-cell convention).

- `tests/test_runner.py` (new or extend):
  - `run()` without `hours_path` is unchanged behavior.
  - `run()` with `hours_path` and all CSV names resolvable produces per-employee files with hours filled.
  - `run()` with `hours_path` and unresolvable CSV names raises `UnresolvedHoursNames` *before* writing any per-employee file. (Important: we don't want partial writes.)

End-to-end manual check:

- Re-run `tipout run --period 2026-05-04:2026-05-17 --pos "2026 SD Daily Tipout Worksheet.xlsx" --hours "Surfing Deer - Time Clock 05.04 to 07.17.2026.csv"`. Spot-check a few per-employee files against the CSV's per-block `Total` row for hours, and against Yvonne's hand-done sheet for `$/hr` shape.

## Risks / non-decisions

- **Name divergence between POS and CSV.** The same person could appear under different raw strings in each source (e.g. POS `Anthony` vs CSV `ANTHONY GARCIA`). Both resolve to `Anthony Garcia` via the alias system, so this works — but it does mean the alias table now serves two consumers. Adding `--hours` for the first time may surface a new wave of unknown-name prompts.
- **Hours-but-no-tips canonicals get silently dropped.** Acceptable for v1; revisit on user feedback.
- **Toast CSV format drift.** If Toast ever changes the column order or block-header shape, the parser will need an update. Mirror the POS parser's approach: fail loudly with a `SchemaError`-style message rather than silently mis-parse.

## File touch list

- `src/tipout/time_clock.py` — new
- `src/tipout/per_employee.py` — modified (layout constants, new optional arg, $/hr cell)
- `src/tipout/runner.py` — modified (hours_path arg, new exception, aggregation)
- `src/tipout/cli.py` — modified (--hours flag, UnresolvedHoursNames handler)
- `tests/test_time_clock.py` — new
- `tests/test_per_employee.py` — extended
- `tests/test_runner.py` — extended or new
- `tests/fixtures/tiny_time_clock.csv` — new
- `tipout-plugin/skills/tipout/SKILL.md` — document the new `--hours` flag in the run example and in the command reference

No changes needed to: `pos_parser.py`, `roster.py`, `summary.py`, `period.py`, `config.py`.
