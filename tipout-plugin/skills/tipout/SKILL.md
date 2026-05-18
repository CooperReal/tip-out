---
name: tipout
description: Generate the 2-week tip-out summary for Surfing Deer by running the `tipout` CLI. Use this skill any time the user wants to run a pay-period tip-out, produce or update the 2-week summary workbook from a POS daily export, reconcile tips payable, or add/edit employees in the tip-out roster. Trigger when the user mentions a POS file, pay period, tip summary, Surfing Deer payroll, or an unknown-name / alias situation in the tipout tool. Do NOT trigger for general-purpose spreadsheet editing, payroll math unrelated to tip distribution, or Watersound/WVM (different tool).
allowed-tools: Bash(cd *) Bash(tipout *) Bash(ls *) Bash(cat *) Read Edit
---

# Tipout — Surfing Deer pay-period summary runner

Use this skill to produce a new pay-period tab in the Surfing Deer 2-week summary workbook from a POS daily export.

## One-time setup (per machine)

Before this skill works on a new machine:

1. The `tipout` CLI must be on `PATH`. From a checkout of the `tip-out` repo:
   ```bash
   pipx install .          # preferred — isolated, on PATH everywhere
   # or
   pip install -e .        # editable install into the active env
   ```
   Verify with `tipout version`.
2. The project directory must contain `config.yaml`, `roster.xlsx`, and an `output/` folder. Its absolute path is supplied to this plugin at install time as `${user_config.project_dir}`.

## What the tool does

- Reads the POS daily workbook (e.g. `2026 SD Daily Tipout Worksheet.xlsx`) supplied by the user.
- Maps raw employee names (first names, typos, annotations like "(Party)" or "(Xen)") to canonical names via a roster workbook.
- Appends a new tab for the requested pay period to `output/summary.xlsx`. The grand total should match what the operator's hand-done version would have produced.
- Output is **append-only** — existing tabs for prior periods are never modified.

## When the user wants to change how the tip-out works

If the user asks to change the way the tip-out is calculated, distributed, or presented — anything that would require code or formula changes — **DO NOT make the change in this session**. The skill is installed from the `tip-out` plugin on GitHub and only Cooper can change its behavior. Your job in this situation is to capture a clear written spec the user can send to Cooper.

Examples that ARE behavior changes (route through this flow):

- "Bar backs should also receive a share."
- "The split between servers and support is wrong."
- "Brunch shifts should be calculated differently."
- "Add a new column showing X."
- "Stop including credit card tips."
- "The output workbook should also include Y."
- "The per-employee files should look different."

Examples that are NOT behavior changes (handle normally, in-session):

- Adding a new employee or alias to `roster.xlsx` — this is data entry, follow the unknown-names flow above.
- Re-running a period after a correction.
- Fixing a typo in `config.yaml`.

When you detect a behavior-change request:

1. Ask clarifying questions, one or two at a time, until the change is unambiguous. You need:
   - The current behavior the user wants to change.
   - The new behavior they want.
   - Whether it applies always or only in certain conditions (specific roles, shifts, dates, pay periods).
   - At least one concrete worked example (inputs → expected output) so Cooper can verify the change matches intent.
   - Any edge cases or open questions the user is unsure about.

2. Save the spec as a markdown file in the user's current working folder named `Tipout Change Request - YYYY-MM-DD.md` with these sections, in this order:
   - **Requester** — name, date, restaurant role.
   - **Summary** — one sentence describing the change.
   - **Current behavior** — what the tip-out does today.
   - **Requested behavior** — what it should do instead.
   - **Worked example** — concrete inputs and the expected output under the new behavior.
   - **Edge cases / open questions** — anything still unresolved.

3. Show the user a link to the file and then say exactly this:

   > Email this spec to Cooper at henry.cooper.real@gmail.com to update the plugin. Once Cooper publishes the update, reinstall the plugin in Cowork Settings → Plugins to pick up the change.

4. Do not improvise a workaround. No one-off Python scripts, no manual edits to the summary workbook to "approximate" the new behavior. The point of routing through Cooper is that the change becomes a permanent, tested part of the plugin used everywhere.

## Required inputs

Inside `${user_config.project_dir}`:

- `config.yaml` — YAML with `anchor_date`, `roster_path`, `summary_path`.
- `roster.xlsx` — has `Employees` sheet (canonical names) and `Name Aliases` sheet (raw-name → canonical).
- A POS daily workbook path (can be anywhere; passed as `--pos`).

If `roster.xlsx` does not yet exist, seed it from an existing hand-done 2-week summary:

```bash
cd "${user_config.project_dir}"
tipout bootstrap-roster --from-summary "<existing-2-week-summary.xlsx>" --out roster.xlsx
```

## Running a pay period

Always `cd` into the project directory first so relative paths in `config.yaml` resolve:

```bash
cd "${user_config.project_dir}"
tipout run --period 2026-01-12:2026-01-25 --pos "<POS-file.xlsx>" --hours "<TimeClock.csv>"
```

- `--period` is `YYYY-MM-DD:YYYY-MM-DD`, inclusive, must be exactly 14 days apart.
- `--pos` is the POS daily workbook path (quote it if the name has spaces).
- `--hours` is optional — when supplied, the Toast Time Clock CSV populates the `Hours Worked` column and `$/hr` cell on each per-employee period tab. Omit it and those cells stay blank.
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

The same flow applies when an unknown name appears in the time clock CSV: the tool exits 1 and writes `unknown_hours_names.txt`. Add the new name as an alias or new employee in `roster.xlsx`, then re-run with the same arguments.

## Re-running an already-completed period

The summary workbook is append-only and will reject a duplicate tab with `Tab '...' already exists — delete to re-run`. To re-run intentionally (e.g. after a correction), delete the tab for that period in `output/summary.xlsx` first, or move/delete the file entirely.

## Full command reference

- `tipout run --period <start>:<end> --pos <file> [--hours <csv>] [--config <path>]` — primary command.
- `tipout bootstrap-roster --from-summary <file> --out <file> [--force]` — one-time roster seeding.
- `tipout check-roster <file>` — validate a roster workbook for structural and semantic issues (orphan aliases, duplicates, first-name collisions). Run this after any manual roster edit or when the user "uploads a new roster."
- `tipout version` — print tool version.

All options are discoverable via `tipout <cmd> --help`.

## Output

- `output/summary.xlsx` — the 2-week summary workbook. One tab per pay period. Col A = canonical name, col B = most-recent raw spelling seen that period, cols C..AC = daily Net Tip per day (14 days), col AE = period total.
- `unknown_names.txt` — only present when a run hit unresolved names. Safe to delete after resolving.
- `unknown_hours_names.txt` — only present when a run hit unresolved names from the time-clock CSV. Safe to delete after resolving.
- `output/per-employee/<Name>.xlsx` — one workbook per canonical employee; layout matches the hand-done `Yvonne.xlsx` reference (`Hours Worked` at col B, `$/hr` on totals row col J).

## Troubleshooting

- `tipout: command not found` (or similar) → the CLI isn't on `PATH` on this machine. Run the one-time setup above.
- `ValueError: Tab '...' already exists` → the period already has a tab. Delete it in Excel or delete the whole `summary.xlsx` to re-run.
- `TypeError: anchor_date must be a YYYY-MM-DD date` → the config YAML has `anchor_date` wrapped in quotes. Remove the quotes so YAML parses it as a date.
- Any `SchemaError` from the parser → the POS file's layout changed. Do not try to patch around it; ask the user to verify the POS export is the expected weekly-tabs workbook.
