# Surfing Deer Tip-Out Automation — Design

**Date:** 2026-04-18
**Scope:** Surfing Deer only. Village Market at Watersound is deferred until SD is proven.

## Problem

Every pay period, someone manually produces three reports from the POS daily workbook:

1. `2026 SD 2 WK Tip Summary By employee.xlsx` — bi-weekly per-employee rollup for payroll and POS reconciliation.
2. Per-employee files (e.g. `Yvonne.xlsx`) — one file per employee, one tab per pay period, sent to staff who question their tips.
3. Monthly and yearly rollups (out of scope for v1).

The work is error-prone and slow. Automate it with a deterministic tool driven by a non-technical operator through Claude Cowork.

## Architecture

```
Operator drops files in inputs/, asks Cowork "run the tipout."
       │
       ▼
Cowork executes  tipout.exe run --period <dates>
       │
       ▼
Script reads POS + hours + roster, validates, writes deliverables
       │
       ▼
Cowork surfaces status/anomalies via structured JSON; operator answers
via enumerated menu choices; script re-invoked if needed.
```

**Split of responsibility:**
- **`tipout.exe`** — owns all math, name resolution, Excel output, validation. Deterministic. Testable.
- **Cowork** — owns the human interface. Never interprets operator free text as a mapping decision; relays structured choices only.

## Inputs

- **POS daily workbook** — `2026 SD Daily Tipout Worksheet.xlsx`. Full year, weekly tabs.
- **Hours file** — one Excel with columns `Employee Name`, `Date`, `Hours Worked`. Operator exports from scheduling system.
- **Pay-period anchor** — set once in config; biweekly windows computed deterministically from it. Year rollover handled by reading dates from cell contents, not tab names.

## Outputs

Written under `outputs/`:

- `2026 SD 2 WK Tip Summary By employee.xlsx` — updated with a new tab for the period. Prior tabs never modified.
- `per-employee/<Name>.xlsx` — one file per employee. New tab per period, appended. Prior tabs never modified. Columns: `Date`, `Hours Worked`, `CC Tips`, `SA Tip Out`, `Bar Tipout`, `TotalTip Out`, `Serv As`, `Bartender`, `Net Tip`, `Party` flag. Row 20 totals. Row 23 `$/hr` = Net Tip ÷ Hours. (No `308` artifact — it was a copy-paste error in the manual process.)
- `anomaly_report.xlsx` — soft anomalies for this run (see Error Handling).

## Roster

Single source of truth at `roster.xlsx`.

**Sheet `Employees`:**

| Canonical Name | Role | Active From | Active To | Notes |
|---|---|---|---|---|

`Role` history handled by multiple rows when someone changes role mid-tenure.

**Sheet `Name Aliases`:**

| Raw Name (as it appears on daily sheet) | Canonical Name |
|---|---|

Seeded from existing 2-week summary (col A ↔ col B).

### Adding new people

When the script sees a name not in `Name Aliases`:

1. Script halts, writes `pending_names.json` listing unknown raw strings and where they appeared.
2. Cowork reads the file, shows the operator an enumerated menu per entry:
   - New employee (with role dropdown)
   - Typo of existing employee (pick from list)
   - Ignore this run
3. Operator's answers are written to `pending_answers.json` as structured data.
4. Script re-invoked; updates roster; continues.

First-name collisions (≥2 active employees sharing a first name) force disambiguation every time until the raw spelling becomes unique.

## Data flow

```
1. Parse POS workbook:
   - For each weekly tab, detect day-blocks by header-row content, not fixed offsets.
   - Abort on schema drift (missing expected labels).
   - Extract per-day rows: (date, raw_name, CC Tips, Party, SA Tip Out, Bar Tipout,
     TotalTipOut, Barback, Bartender, Net Tip, is_party_day).
   - Drop blank / zero / template rows.

2. Resolve raw_name → canonical via roster. Unknowns halt (see above).

3. Filter to pay-period window [anchor + 14n, anchor + 14n + 13].

4. Join hours file on (canonical, date). Use same alias resolver on hours names.

5. Emit deliverables (see Outputs). Prior tabs never overwritten.

6. Archive run (see Audit Trail).
```

## Error & anomaly handling

**Hard stops — no deliverables produced:**

- Schema drift on any weekly tab.
- Unknown names not resolved.
- First-name ambiguity unresolved.
- Pay-period misalignment (missing tab, ambiguous year).
- Employee with tips but no hours, or hours but no tips.
- Regression test suite red.

**Soft anomalies — deliverables produced, flagged in `anomaly_report.xlsx`:**

- Tip-pool imbalance: `sum(SA Tip Out distributed)` ≠ `sum(Net Tips received by support tier)` ± $0.50.
- Server math: `Net Tip ≠ CC Tips + Party − TotalTipOut` ± $0.01.
- Outlier $/hour (<$10 or >$100).
- Period total drops >60% vs employee's 4-period rolling average despite hours present.
- New spelling that resolved via alias (informational).
- Duplicate row for same employee on same day with different numbers.

## Regression testing

**Goal:** reproduce all 8 existing hand-done pay periods exactly before going live.

**Fixtures** (`tests/fixtures/<period>/`):

- `input_pos.xlsx` — snapshot of POS state for that period.
- `input_hours.xlsx` — reverse-engineered from historical per-employee files.
- `input_roster.xlsx` — roster as it would have been.
- `expected/` — period tab of 2-week summary + every per-employee sheet for the period, with known historical artifacts (e.g. stray `308`) scrubbed.

**Runner:**

- Cell-by-cell diff: exact for strings/dates, ±$0.005 for numbers, ignore formatting-only diffs.
- Commands: `tipout test`, `tipout test --period <d>`, `tipout test --update` (fixture authoring only).
- **Green test suite is a precondition for any live run.** Cowork checks before invoking.

## Audit trail

Every run archives to `archive/<run-id>/`:

- Copy of input POS file (+ SHA-256).
- Copy of input hours file (+ SHA-256).
- Snapshot of `roster.xlsx`.
- Output files produced.
- Anomaly report.
- Log with script version / git SHA, timestamps, operator answers.

Archived folders are read-only. Payroll disputes cite a run ID, not "re-run today against current POS."

## Installation

**On operator's machine:**

```
C:\tipout\
├── tipout.exe               single-file executable (PyInstaller bundle)
├── roster.xlsx
├── config.yaml              pay-period anchor, paths
├── inputs\
├── outputs\
│   ├── 2026 SD 2 WK Tip Summary By employee.xlsx
│   └── per-employee\<Name>.xlsx
├── archive\<run-id>\
└── logs\
```

No Python install required. Updates = replace `tipout.exe`.

**Cowork playbook** (markdown instructions loaded into Cowork) tells it: when asked to run tip-out, execute `tipout.exe run --period <dates>`, parse the JSON status, relay enumerated menus for any hard stops, present anomaly summary after success.

**First-run setup** (one-time, technical):

1. Install Cowork.
2. Place `tipout.exe`, seeded `roster.xlsx`, `config.yaml` in `C:\tipout\`.
3. Load Cowork playbook.
4. Run `tipout.exe test` — all 8 historical fixtures must pass.
5. Hand off.

## Ongoing operator workflow

1. Drop POS file + hours file in `inputs\`.
2. Open Cowork → "run the tip-out."
3. Answer any menu prompts Cowork relays.
4. Review anomaly summary.
5. Pull deliverables from `outputs\` to send to payroll / staff.

## Out of scope for v1

- Watersound / WVM (different per-day layout, AM+PM split). Tackle once SD is stable.
- Monthly and yearly rollups. Add once bi-weekly is working.
- Automated delivery of per-employee sheets (email/portal). For now operator pulls from `outputs/per-employee/` manually.
- Encryption / password-protection of per-employee files. Mitigation for v1 is an access-controlled outputs folder + send log.

## Known risks & mitigations (from adversarial review)

| Risk | Mitigation |
|---|---|
| POS layout drift | Parse by header content, abort on schema mismatch. |
| First-name collisions | Roster `Active From/To`; force disambiguation when ambiguous. |
| Year rollover in dates | Parse dates from cell contents, never tab names. |
| Corrections after payroll sent | Append-only output + archived runs; corrections = new run with diff report. |
| LLM non-determinism in the driver | Cowork only relays enumerated menus; script owns all decisions. |
| PII in per-employee files | Access-controlled outputs folder + send log (stronger protection deferred). |
| Hours / POS name mismatch | Same alias resolver for both; mismatch = hard stop. |

## Open items

- Confirm `roster.xlsx` seed data by manually reviewing the 2-week summary's alias column before first live run.
- Confirm pay-period anchor date with user.
- Identify / build the hours-file export from the scheduling system.
- Decide Cowork playbook format by reviewing actual Cowork documentation at time of build.
