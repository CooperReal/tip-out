---
name: tipout
description: Generate the 2-week tip-out summary for Surfing Deer by running the `tipout` CLI. Use this skill any time the user wants to run a pay-period tip-out, produce or update the 2-week summary workbook from a POS daily export, reconcile tips payable, or add/edit employees in the tip-out roster. Trigger when the user mentions a POS file, pay period, tip summary, Surfing Deer payroll, or an unknown-name / alias situation in the tipout tool. Do NOT trigger for general-purpose spreadsheet editing, payroll math unrelated to tip distribution, or Watersound/WVM (different tool).
allowed-tools: Bash(cd *) Bash(.venv/Scripts/tipout *) Bash(ls *) Bash(cat *) Read Edit
---

# Tipout — Surfing Deer pay-period summary runner

Use this skill to produce a new pay-period tab in the Surfing Deer 2-week summary workbook from a POS daily export.

## What the tool does

- Reads the POS daily workbook (e.g. `2026 SD Daily Tipout Worksheet.xlsx`) supplied by the user.
- Maps raw employee names (first names, typos, annotations like "(Party)" or "(Xen)") to canonical names via a roster workbook.
- Appends a new tab for the requested pay period to `output/summary.xlsx`. The grand total should match what the operator's hand-done version would have produced.
- Output is **append-only** — existing tabs for prior periods are never modified.

## Required inputs

The project root must contain (or the user must have):

- `config.yaml` — YAML with `anchor_date`, `roster_path`, `summary_path`.
- `roster.xlsx` — has `Employees` sheet (canonical names) and `Name Aliases` sheet (raw-name → canonical).
- A POS daily workbook path.

If `roster.xlsx` does not yet exist, seed it from an existing hand-done 2-week summary:

```bash
.venv/Scripts/tipout bootstrap-roster --from-summary "<existing-2-week-summary.xlsx>" --out roster.xlsx
```

## Running a pay period

Work from the `tip-out` project directory. Typical invocation:

```bash
.venv/Scripts/tipout run --period 2026-01-12:2026-01-25 --pos "<POS-file.xlsx>"
```

- `--period` is `YYYY-MM-DD:YYYY-MM-DD`, inclusive, must be exactly 14 days apart.
- `--pos` is the POS daily workbook path (quote it if the name has spaces).
- `--config` defaults to `./config.yaml`.

On success the tool prints `Done.` and writes/updates `output/summary.xlsx`.

## Handling unknown names (the common case)

If the POS file contains a raw name the roster hasn't seen, the tool:

1. Exits with code `1`.
2. Writes `unknown_names.txt` listing each unresolved raw name, one per line.
3. Prints a short message with the next step.

When this happens, present the list of unknown names to the user and ask, for each one, whether it is:

- **An alias for an existing employee** (e.g. "Anthony" → "Anthony Garcia"). Find likely canonicals by reading `roster.xlsx`'s `Employees` sheet. Add a row to the `Name Aliases` sheet: `Raw Name | Canonical Name`.
- **A new employee**. Add a row to the `Employees` sheet: `Canonical Name | Role | Active From | Active To | Notes`. Role is free text (e.g. `server`, `bartender`, `support`). Active From can be today's date; the other fields can be blank.

After the user confirms the mappings, update `roster.xlsx` using `openpyxl` (preferred) or by asking the user to save their own Excel edits, then re-run the same `tipout run` command. Repeat until the tool exits 0.

**Do not guess mappings without user confirmation** — misattributed tips directly cause payroll errors. If a raw name could plausibly match more than one existing canonical (e.g. two Andrews in the roster), ask the user which one.

## Re-running an already-completed period

The summary workbook is append-only and will reject a duplicate tab with `Tab '...' already exists — delete to re-run`. To re-run intentionally (e.g. after a correction), delete the tab for that period in `output/summary.xlsx` first, or move/delete the file entirely.

## Full command reference

- `tipout run --period <start>:<end> --pos <file> [--config <path>]` — primary command.
- `tipout bootstrap-roster --from-summary <file> --out <file> [--force]` — one-time roster seeding.
- `tipout check-roster <file>` — validate a roster workbook for structural and semantic issues (orphan aliases, duplicates, first-name collisions). Run this after any manual roster edit or when the user "uploads a new roster."
- `tipout version` — print tool version.

All options are discoverable via `tipout <cmd> --help`.

## Output

- `output/summary.xlsx` — the 2-week summary workbook. One tab per pay period. Col A = canonical name, col B = most-recent raw spelling seen that period, cols C..AC = daily Net Tip per day (14 days), col AE = period total.
- `unknown_names.txt` — only present when a run hit unresolved names. Safe to delete after resolving.

## Troubleshooting

- `ValueError: Tab '...' already exists` → the period already has a tab. Delete it in Excel or delete the whole `summary.xlsx` to re-run.
- `TypeError: anchor_date must be a YYYY-MM-DD date` → the config YAML has `anchor_date` wrapped in quotes. Remove the quotes so YAML parses it as a date.
- Any `SchemaError` from the parser → the POS file's layout changed. Do not try to patch around it; ask the user to verify the POS export is the expected weekly-tabs workbook.
