# tipout — Surfing Deer tip-out automation

A small Python CLI that reads a pay period's POS daily workbook and appends a new tab to the 2-week tip summary workbook used for payroll reconciliation.

## Quick start (for the operator)

You run this once per pay period, after the POS export is saved to disk.

1. Export the POS daily workbook as usual (e.g. `2026 SD Daily Tipout Worksheet.xlsx`). Save it somewhere you can find it.
2. Open a terminal in this folder (`tip-out`) and run:

   ```
   .venv/Scripts/tipout run --period 2026-01-12:2026-01-25 --pos "2026 SD Daily Tipout Worksheet.xlsx"
   ```

   Replace the two dates with the start and end of the pay period (14 days, inclusive). Replace the POS path with the file you just exported.

3. If the tool prints `Found N unknown name(s) in the POS file for this period.`, follow the steps under **Handling unknown names** below, then re-run the same command. Repeat until the command finishes with `Done.`
4. Open `output/summary.xlsx`. The new pay-period tab is appended. Send the workbook to payroll.

That's it. You don't need to edit Python or touch code.

### Checking the version

```
.venv/Scripts/tipout version
```

## What the files mean

- **`config.yaml`** — three settings the tool needs. `anchor_date` is any Monday that starts a known pay period (pay-period math counts in 14-day blocks from there). `roster_path` and `summary_path` tell the tool where to find the roster and where to write the summary. The example committed to this repo points at `roster.xlsx` and `output/summary.xlsx`.
- **`roster.xlsx`** — the source of truth for employee names. Two sheets:
  - `Employees` — one row per canonical (correctly spelled) employee name.
  - `Name Aliases` — maps a raw spelling as it appears in the POS export (left column) to a canonical name in `Employees` (right column).
- **POS daily workbook** — exported from the POS system by the operator. Weekly tabs with day-blocks inside. The tool auto-detects day-blocks and pulls shift rows from them; it does not care about tab names.
- **`output/summary.xlsx`** — the 2-week tip summary. Each `tipout run` appends one new tab for the pay period. Old tabs are never touched.

## Handling unknown names

The POS export spells names however the staff typed them. When a raw name doesn't match anything in `roster.xlsx`, the tool stops and writes every unknown name to `unknown_names.txt` (next to `config.yaml`).

Open `unknown_names.txt`, then open `roster.xlsx` in Excel. For each unknown name:

- **Misspelling or nickname of an existing employee** — go to the `Name Aliases` sheet and add a row with the raw spelling on the left and the existing canonical name on the right.
- **A genuinely new employee** — go to the `Employees` sheet and add a row with the canonical spelling.

Save `roster.xlsx`, close it, and re-run the same `tipout run` command. Repeat if more unknowns turn up.

## Validating a roster

Before trusting a roster (especially one someone else prepared or one you just edited), run:

```
.venv/Scripts/tipout check-roster roster.xlsx
```

The command reports:

- **Errors** — missing sheets, blank canonical names, aliases pointing at non-existent canonicals, malformed headers. A run with any error exits non-zero; `tipout run` will likely fail too.
- **Warnings** — duplicate canonicals, duplicate raw aliases, first-name collisions that will need explicit aliases to disambiguate. These don't block `tipout run` but are likely future bugs.

Zero errors + zero warnings prints `OK (no issues).`.

## Starting from scratch: bootstrap a roster

If you don't yet have a `roster.xlsx` but do have a prior, hand-maintained 2-week summary workbook, you can seed a roster from it:

```
.venv/Scripts/tipout bootstrap-roster --from-summary "2026 SD 2 WK Tip Summary By employee.xlsx" --out roster.xlsx
```

Pass `--force` to overwrite an existing `roster.xlsx`. This reads canonical names and aliases that are already embedded in the hand-done summary and writes them into the new roster format.

## For developers

### Install

Python 3.11 or newer. Developed and tested on Windows; should work on macOS/Linux but the Windows paths in this README are what we actually run.

```
py -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/tipout --help
```

### Test

```
.venv/Scripts/pytest
```

Fixtures live under `tests/fixtures/`. A synthetic POS workbook drives the end-to-end runner test.

### Project layout

All code is under `src/tipout/`:

- `cli.py` — click entry point. Commands: `version`, `init`, `run`, `bootstrap-roster`, `check-roster`.
- `config.py` — loads `config.yaml` into a `Config` dataclass; resolves relative paths against the config file's directory.
- `period.py` — `PayPeriod` value object plus anchor-based pay-period math (14-day blocks from `anchor_date`).
- `pos_parser.py` — reads the POS daily workbook. Detects day-blocks by header content, normalizes column aliases, produces `ShiftRow` records. Raises `SchemaError` on unrecognizable sheets.
- `roster.py` — loads `Employees` and `Name Aliases` sheets from `roster.xlsx`. `Roster.resolve(raw)` returns a canonical name or `None`. `fuzzy_candidates` helps surface first-name ambiguity.
- `summary.py` — builds the 2-week grid from shift rows and append-writes a new pay-period tab to `summary.xlsx`. Existing tabs are untouched.
- `runner.py` — orchestrates parse, resolve, build, write. Raises `UnresolvedNames` when raw names can't be mapped, which the CLI catches and turns into `unknown_names.txt`.
- `bootstrap.py` — one-shot roster extractor that harvests canonical names and aliases from a legacy hand-maintained summary workbook.

### Design notes

The tool is append-only and deterministic: re-running a period overwrites nothing by accident, and the only way a name gets into the summary is via the roster. All human judgment (spelling decisions, new hires) lives in `roster.xlsx` and is edited by hand in Excel. There is no DB, no state file, no network.

## Using this from Claude Cowork (for operators)

The operator does **not** install Python or clone this repo. The tool ships as a Cowork plugin (`tipout-plugin/`) that bundles the skill; the skill itself downloads a self-contained engine (`tipout.exe`) on first use.

**One-time install (Windows):**

1. Download `tipout-plugin.zip` from the [latest release](https://github.com/CooperReal/tip-out/releases/latest).
2. In Claude Desktop → **Cowork** tab → **Customize** → **Browse plugins** → **upload** the zip.
3. Make sure code execution / Bash is enabled in Cowork.

That's it. The first time you ask Cowork to run a tip-out, it creates `Documents\Tipout`, downloads the engine, and scaffolds `config.yaml` + `roster.xlsx`. To get a newer version later, just tell Cowork **"update tipout"** — it re-downloads the engine and tells you what changed. No reinstalling, no GitHub, no terminal.

Then ask it to "run the tipout for the pay period starting on <date>" and it will run the engine, walk you through any unknown names, and hand you the finished workbook.

## Releasing (for the maintainer)

Releases are built by GitHub Actions on a Windows runner (`.github/workflows/release.yml`). To cut a new version:

```
git tag v0.2.0
git push origin v0.2.0
```

CI stamps the version from the tag into `src/tipout/__init__.py` and `plugin.json`, builds `tipout.exe` with PyInstaller, packages `tipout-plugin.zip`, and publishes both as assets on a GitHub Release. The skill always pulls the engine from `releases/latest/download/tipout.exe`, so operators get the new engine the moment they say "update tipout" — no plugin reinstall needed unless the skill instructions themselves changed (then re-upload the new `tipout-plugin.zip`).

The repo's Releases must be public so the download URL works without a login.

## Deeper context

- Design rationale: [`docs/plans/2026-04-18-surfing-deer-tipout-automation-design.md`](docs/plans/2026-04-18-surfing-deer-tipout-automation-design.md)
- Phase-by-phase build plan: [`docs/plans/2026-04-18-surfing-deer-tipout-implementation.md`](docs/plans/2026-04-18-surfing-deer-tipout-implementation.md)
