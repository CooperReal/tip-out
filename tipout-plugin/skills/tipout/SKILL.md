---
name: tipout
description: Generate the 2-week tip-out summary for Surfing Deer or Watersound (WVM) by running the `tipout` engine. Use this skill any time the user wants to run a pay-period tip-out, produce or update the 2-week summary workbook from a POS daily export, reconcile tips payable, add/edit employees in the tip-out roster, or update the tipout tool to the latest version. Trigger when the user mentions a POS file, pay period, tip summary, Surfing Deer payroll, Watersound, WVM, run the Watersound tip-out, an unknown-name / alias situation, or says "update tipout". Do NOT trigger for general-purpose spreadsheet editing or payroll math unrelated to tip distribution.
allowed-tools: Bash(cd *) Bash(ls *) Bash(cat *) Bash(mkdir *) Bash(curl *) Bash(powershell *) Bash(./tipout.exe *) Read Edit
---

# Tipout — pay-period summary runner (Surfing Deer + Watersound)

Use this skill to produce a new pay-period tab in the 2-week summary workbook from a POS daily export — for either Surfing Deer (SD) or Watersound Village Market (WVM).

## Choosing the restaurant

The operator tells you which restaurant they're running. Each restaurant has its own project folder so rosters, configs, and output never collide:

- **Surfing Deer (SD):** `%USERPROFILE%\Documents\Tipout` (i.e. `"$HOME/Documents/Tipout"`)
- **Watersound (WVM):** `%USERPROFILE%\Documents\Tipout-WVM` (i.e. `"$HOME/Documents/Tipout-WVM"`)

Pass `--restaurant sd` (the default) or `--restaurant wvm` to the `run` command. Keep one skill and one engine binary — SD and WVM share the same `tipout.exe`.

The tool has two parts, and you (the agent) manage both so the user never has to:

- **This skill** — the instructions you're reading. Installed once as a Cowork plugin.
- **The engine** — a single self-contained program, `tipout.exe`, that does the calculation. No Python or other install is needed; you download it automatically.

The project folder lives at a fixed location: **`%USERPROFILE%\Documents\Tipout`** (in Bash on this Windows machine, that is `"$HOME/Documents/Tipout"`). Everything — the engine, config, roster, and output — lives there. **Always `cd` into that folder first**, then call the engine as `./tipout.exe`.

## Setup (first run — fully automatic)

Before doing anything else, make sure the engine exists. Run:

```bash
ls "$HOME/Documents/Tipout/tipout.exe"
```

If it is missing, set it up without asking the user to do anything manual:

```bash
mkdir -p "$HOME/Documents/Tipout/output"
cd "$HOME/Documents/Tipout"
curl -L -o tipout.exe https://github.com/CooperReal/tip-out/releases/latest/download/tipout.exe
powershell -Command "Unblock-File -Path 'tipout.exe'"
./tipout.exe version > version.txt
```

Then scaffold the config and an empty roster (skip files that already exist; it refuses to overwrite without `--force`):

```bash
cd "$HOME/Documents/Tipout"
./tipout.exe init
```

If the user has an existing hand-done 2-week summary workbook, seed the roster from it instead:

```bash
cd "$HOME/Documents/Tipout"
./tipout.exe init --from-summary "<path-to-their-existing-summary.xlsx>" --force
```

**WVM first-time roster seeding:** there is no prior hand-done WVM summary, so seed from the WVM daily worksheet directly:

```bash
cd "$HOME/Documents/Tipout-WVM"
./tipout.exe bootstrap-roster --from-wvm-daily "<WVM daily.xlsx>" --out roster.xlsx --force
```

This collects every distinct worker name and their role group. Important caveat: **do NOT merge same-first-name people who come from different role groups** — `Carlos` (WAIT AM) and `Carlos Legaspi` (To Go) are different people. Merging them corrupts both records. Use the role-group column as the disambiguator.

Confirm it worked with `./tipout.exe version` from the project folder you set up (Surfing Deer: `Documents/Tipout`; Watersound: `Documents/Tipout-WVM`), then tell the user setup is complete.

## Updating tipout ("update tipout")

When the user says they want the latest version (e.g. after Cooper publishes a change they requested), they do **not** reinstall anything. You update the engine for them:

```bash
cd "$HOME/Documents/Tipout"
cat version.txt                 # the version currently installed
curl -sL https://api.github.com/repos/CooperReal/tip-out/releases/latest
```

From the API response, read `tag_name` (the latest version) and `body` (the release notes / what changed).

- If the installed version already matches `tag_name`, tell the user they're already up to date and stop.
- Otherwise download the new engine and record the version:

  ```bash
  cd "$HOME/Documents/Tipout"
  curl -L -o tipout.exe https://github.com/CooperReal/tip-out/releases/latest/download/tipout.exe
  powershell -Command "Unblock-File -Path 'tipout.exe'"
  ./tipout.exe version > version.txt
  ```

  Then summarize for the user what changed, using the release notes (`body`) from the API response.

The roster, config, and previous output in `Documents\Tipout` are untouched by an update.

## What the tool does

- Reads the POS daily workbook (e.g. `2026 SD Daily Tipout Worksheet.xlsx`) supplied by the user.
- Maps raw employee names (first names, typos, annotations like "(Party)" or "(Xen)") to canonical names via a roster workbook.
- Appends a new tab for the requested pay period to `output/summary.xlsx`. The grand total should match what the operator's hand-done version would have produced.
- Output is **append-only** — existing tabs for prior periods are never modified.

## When the user wants to change how the tip-out works

If the user asks to change the way the tip-out is calculated, distributed, or presented — anything that would require code or formula changes — **DO NOT make the change in this session**. Only Cooper can change the engine's behavior. Your job in this situation is to capture a clear written spec the user can send to Cooper.

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

   > Email this spec to Cooper at henry.cooper.real@gmail.com to update the plugin. Once Cooper publishes the update, just tell me "update tipout" and I'll pull in the new version for you.

4. Do not improvise a workaround. No one-off Python scripts, no manual edits to the summary workbook to "approximate" the new behavior. The point of routing through Cooper is that the change becomes a permanent, tested part of the tool used everywhere.

## Required inputs

Inside `Documents\Tipout`:

- `config.yaml` — YAML with `anchor_date`, `roster_path`, `summary_path`. Created by `./tipout.exe init`.
- `roster.xlsx` — has `Employees` sheet (canonical names) and `Name Aliases` sheet (raw-name → canonical). Created by `./tipout.exe init`.
- A POS daily workbook path (can be anywhere; passed as `--pos`).

## Running a pay period

Always `cd` into the project directory first so relative paths in `config.yaml` resolve.

**Surfing Deer (SD):**

```bash
cd "$HOME/Documents/Tipout"
./tipout.exe run --period 2026-01-12:2026-01-25 --pos "<POS-file.xlsx>" --hours "<TimeClock.csv>"
```

**Watersound (WVM):**

```bash
cd "$HOME/Documents/Tipout-WVM"
./tipout.exe run --restaurant wvm --period 2026-01-12:2026-01-25 --pos "<WVM daily.xlsx>"
```

WVM is **summary only**: it produces `output/summary.xlsx` and does **not** produce per-employee files. `--hours` is **not accepted** with `--restaurant wvm` — passing it is an error.

- `--restaurant` is `sd` (default) or `wvm`.
- `--period` is `YYYY-MM-DD:YYYY-MM-DD`, inclusive, must be exactly 14 days apart.
- `--pos` is the POS daily workbook path (quote it if the name has spaces).
- `--hours` is optional (SD only) — when supplied, the Toast Time Clock CSV populates the `Hours Worked` column and `$/hr` cell on each per-employee period tab. Omit it and those cells stay blank.
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

After the user confirms the mappings, update `roster.xlsx` using `openpyxl` (preferred) or by asking the user to save their own Excel edits, then re-run the same `./tipout.exe run` command. Repeat until the tool exits 0.

**Do not guess mappings without user confirmation** — misattributed tips directly cause payroll errors. If a raw name could plausibly match more than one existing canonical (e.g. two Andrews in the roster), ask the user which one.

The same flow applies when an unknown name appears in the time clock CSV: the tool exits 1 and writes `unknown_hours_names.txt`. Add the new name as an alias or new employee in `roster.xlsx`, then re-run with the same arguments.

## Re-running an already-completed period

The summary workbook is append-only and will reject a duplicate tab with `Tab '...' already exists — delete to re-run`. To re-run intentionally (e.g. after a correction), delete the tab for that period in `output/summary.xlsx` first, or move/delete the file entirely.

## Full command reference

Run all of these from inside `Documents\Tipout` (`cd "$HOME/Documents/Tipout"` first):

- `./tipout.exe init [--dir <path>] [--from-summary <file>] [--anchor YYYY-MM-DD] [--force]` — scaffold a fresh project (`config.yaml`, `roster.xlsx`, `output/`). `--from-summary` seeds the roster from an existing hand-done summary.
- `./tipout.exe run --period <start>:<end> --pos <file> [--restaurant sd|wvm] [--hours <csv>] [--config <path>]` — primary command. `--restaurant` defaults to `sd`. `--hours` is SD-only.
- `./tipout.exe bootstrap-roster --from-summary <file> --out <file> [--force]` — seed only the roster from an existing SD summary.
- `./tipout.exe bootstrap-roster --from-wvm-daily <file> --out <file> [--force]` — seed a WVM roster from the WVM daily worksheet (distinct names + role groups; no aliases seeded).
- `./tipout.exe check-roster <file>` — validate a roster workbook for structural and semantic issues (orphan aliases, duplicates, first-name collisions). Run this after any manual roster edit or when the user "uploads a new roster."
- `./tipout.exe version` — print tool version.

All options are discoverable via `./tipout.exe <cmd> --help`.

## Output

- `output/summary.xlsx` — the 2-week summary workbook. One tab per pay period. Col A = canonical name, col B = most-recent raw spelling seen that period, cols C..AC = daily Net Tip per day (14 days), col AE = period total.
- `unknown_names.txt` — only present when a run hit unresolved names. Safe to delete after resolving.
- `unknown_hours_names.txt` — only present when a run hit unresolved names from the time-clock CSV. Safe to delete after resolving.
- `output/per-employee/<Name>.xlsx` — one workbook per canonical employee (SD only); layout matches the hand-done `Yvonne.xlsx` reference (`Hours Worked` at col B, `$/hr` on totals row col J).

**For WVM (`--restaurant wvm`), only `output/summary.xlsx` is produced.** No per-employee files are written and `--hours` is rejected.

## Troubleshooting

- `tipout.exe` missing or `No such file` → run the **Setup (first run)** steps above to download it.
- Windows SmartScreen / antivirus warns about `tipout.exe` → the `Unblock-File` step in setup clears the "downloaded from the internet" mark. You always run the engine from the command line (never a double-click), so the SmartScreen pop-up does not apply. If antivirus quarantines it, ask the user to allow the file, or tell Cooper.
- `ValueError: Tab '...' already exists` → the period already has a tab. Delete it in Excel or delete the whole `summary.xlsx` to re-run.
- `TypeError: anchor_date must be a YYYY-MM-DD date` → the config YAML has `anchor_date` wrapped in quotes. Remove the quotes so YAML parses it as a date.
- Any `SchemaError` from the parser → the POS file's layout changed. Do not try to patch around it; ask the user to verify the POS export is the expected weekly-tabs workbook.
- `no WVM day-tabs found` → you ran `--restaurant wvm` against a non-WVM file (or forgot `--restaurant wvm` and pointed at the WVM file). Re-check the `--restaurant` flag and confirm `--pos` points at the correct file.
- `WVM integrity check failed` → a day's summary total does not match the WVM sheet's own total for that day. The file may be malformed for that day. No output is written. Tell the operator and ask them to inspect the flagged date's tab.
