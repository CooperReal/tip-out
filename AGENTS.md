# AGENTS.md — onboarding for AI agents working on this repo

Read this first. It's a distilled map of the tipout codebase: what it does, how it's shaped, the invariants you must not break, and where to look when you need to go deeper. Every claim here is grounded in the knowledge graph under `graphify-runs/project/` (177 nodes, 309 edges) or the source itself.

## 30-second mental model

`tipout` is a Python CLI that turns a POS daily Excel workbook into a new tab on a 2-week tip-summary workbook used for payroll at a single restaurant (Surfing Deer).

It is a **pipeline with one human decision point**: "can I resolve this name?" Everything before and after is pure transformation.

```
POS workbook  →  parse_workbook()  →  list[ShiftRow]
                                           │
roster.xlsx   →  load_roster()     →  Roster.resolve(raw) → canonical | None
                                           │
                                  runner.run()  ← the only orchestration
                                           │
                              append_period_tab()  →  output/summary.xlsx (append)
```

The graph confirms this: shortest path from `parse_workbook()` to `append_period_tab()` is **2 hops**, both going through `runner.run()`. There is no sneaky side channel.

## The pipeline in more detail

1. **Parse** (`src/tipout/pos_parser.py`) — `parse_workbook(path)` walks every non-template sheet, auto-detects day-blocks by matching the column-header pattern (`CC Tips | Party | Cash RCP | SA Tip Out | Bar Tipout | TotalTip Out | Barback | Bartender | Net tip`), and yields `ShiftRow` records. Raises `SchemaError` if a sheet looks like a day-block sheet but isn't parseable — fail loud on schema drift.
2. **Filter** (`runner.py`) — keep shift rows where `period.start ≤ row.date ≤ period.end`.
3. **Resolve** (`roster.py`) — for each shift row, look up `raw_name` in the roster: first against `Employees` canonicals, then against `Name Aliases`. Case-insensitive. If any raw name fails to resolve, **raise `UnresolvedNames`** — do not fall back, do not guess.
4. **Build grid + write** (`summary.py`) — `build_grid(...)` constructs a 2D list for the tab; `append_period_tab(...)` appends a new tab to the summary workbook. Refuses to overwrite existing tabs.

## Core abstractions (graph-derived god nodes, ranked by edges)

These are the nodes with the highest connectivity in the project graph. If you're changing one of these, ripples through the system are highly likely.

| Abstraction | Where | Why it's central |
|---|---|---|
| `UnresolvedNames` | `src/tipout/runner.py` | 19 edges. Locus of human-in-the-loop. Every doc/plan/SKILL.md instruction about unknown names terminates here. |
| `load_roster()` / `Roster` | `src/tipout/roster.py` | Name resolution contract. Two sheets (`Employees`, `Name Aliases`), case-insensitive, `.resolve(raw) → canonical \| None`. |
| `PayPeriod` / `from_dates()` | `src/tipout/period.py` | Immutable 14-day window value. `from_dates(start,end)` asserts the length; `from_anchor()` snaps an arbitrary date to its 14-day block. |
| `Config` | `src/tipout/config.py` | Three fields: `anchor_date`, `roster_path`, `summary_path`. Relative paths resolve against the config file's dir, not cwd — so the CLI works regardless of where you run it. |
| `append_period_tab()` / `build_grid()` | `src/tipout/summary.py` | Writes the payroll tab. Append-only. Raises `ValueError` on duplicate tab. |
| `run()` | `src/tipout/runner.py` | The orchestration spine — 15 lines that touch every module. Highest cross-community betweenness (0.248). |
| `parse_workbook()` | `src/tipout/pos_parser.py` | Entry point for all POS input. Schema-drift handling lives here. |
| `validate_roster()` | `src/tipout/validator.py` | Preflight for `roster.xlsx`. Errors block; warnings don't. |

## Invariants (extracted from `rationale_for` edges — do not break)

These are explicit design decisions the code and docs agree on. The graph has a `rationale_for` edge for each:

1. **Append-only determinism.** `append_period_tab()` never overwrites. Re-running a completed period requires deleting the existing tab manually (`README.md → Append-only deterministic design principle → summary.append_period_tab`).
2. **Do not guess name mappings without user confirmation.** The unknown-names path always stops and asks. `UnresolvedNames → skills/tipout/SKILL.md: "Rule: do not guess name mappings without user confirmation"`.
3. **Parse by header, abort on schema drift.** `pos_parser` matches headers *by content*, not by cell position, and raises `SchemaError` if headers are unrecognizable. (`docs/plans/…design.md: Parse-by-header, abort on schema drift → pos_parser.parse_workbook / SchemaError`.)
4. **Year-rollover correctness: read dates from cells, not tab names.** Tab names can drift or be edited; cell dates are authoritative. (`design.md → parse_workbook`.)
5. **Name normalization lives in `roster.xlsx`, not code.** Spelling judgment is the operator's job; code just resolves. (`OVERVIEW.md: Name normalization problem → Roster`.)
6. **Split of responsibility: tipout owns math, Cowork owns human-in-the-loop.** The CLI is non-interactive by design; any UX (asking about unknown names, retry prompts) belongs to the Cowork/Claude-Code skill layer (`skills/tipout/SKILL.md`).

## The Unknown-Names Loop (the only user-visible control flow branch)

This is the one part of the pipeline where judgment enters. The graph has it as a **hyperedge**: `roster.resolve → UnresolvedNames → unknown_names.txt sidecar → operator workflow`.

Flow:
1. Some raw name in the POS fails to resolve.
2. `runner.run()` raises `UnresolvedNames(names)`.
3. CLI catches it, writes `unknown_names.txt` next to `config.yaml`, prints instructions, exits 1.
4. Operator edits `roster.xlsx` (add a new canonical in `Employees` **or** a new row in `Name Aliases`).
5. Operator re-runs the same command.
6. Loop until the CLI finishes with `Done.`

This is the only reason the CLI can exit non-zero after starting real work. The `test_cli_run_writes_unknowns_file_and_exits_nonzero()` test locks this contract in.

## Module map

| File | What it owns | Called by |
|---|---|---|
| `src/tipout/cli.py` | Click entry point. Commands: `version`, `init`, `run`, `bootstrap-roster`, `check-roster`. CLI-level `UnresolvedNames` catch → `unknown_names.txt`. | end user, `bootstrap.py` (indirectly) |
| `src/tipout/runner.py` | The 15-line orchestration. | `cli.run`, tests |
| `src/tipout/config.py` | YAML config loader. | `cli`, `run_all.py`, tests |
| `src/tipout/period.py` | `PayPeriod` dataclass + anchor math. | `cli`, `run_all.py`, tests |
| `src/tipout/pos_parser.py` | Day-block auto-detect, `ShiftRow` records, `SchemaError`. | `runner` |
| `src/tipout/roster.py` | `Roster` + `load_roster`, case-insensitive resolve. | `runner`, `run_all.py` |
| `src/tipout/summary.py` | Grid build + append-only tab write. | `runner` |
| `src/tipout/bootstrap.py` | One-shot harvester — reads canonicals+aliases from a hand-kept summary and writes a fresh `roster.xlsx`. | `cli.bootstrap-roster` |
| `src/tipout/validator.py` | `check-roster` implementation. Structural and semantic checks of `roster.xlsx`. | `cli.check-roster` |
| `run_all.py` (root, not `src/`) | Batch harness: reconciles every historical pay period against the hand-kept workbook. Includes `guess_mapping()` heuristics for unattended runs. **Separate from the shipped CLI** — do not import it from `src/tipout/`. |

## Docstring-to-code coupling

Every CLI command and every public class/function has a docstring that the graph captured as a `rationale_for` edge. Keep these in sync: if you change what a function does, update its docstring. The graph treats the docstring as the canonical justification. (23 `rationale_for` edges total — design docs explain *why*, docstrings explain *what*.)

## Tests

Fixtures in `tests/conftest.py` build in-memory POS + roster workbooks under `tmp_path`. `test_runner.py` is the end-to-end path. Test-density by community (from the graph):

- Roster + Summary Output: 9 tests
- POS Parser: 4 tests
- Roster Validator: 10 tests
- Bootstrap Roster: 5 tests
- Config + end-to-end: 8 tests
- Pay Period Math: 6 tests
- Roster Resolution: 5 tests

Run with `.venv/Scripts/pytest`. No test requires network or real Excel files on disk outside `tests/fixtures/`.

## Cowork / Claude-Code integration

`tipout-plugin/skills/tipout/SKILL.md` is an Agent Skill that wraps this CLI, shipped inside the `tipout-plugin/` Cowork plugin. It exists so an agent (Cowork, Claude Code, etc.) can drive the tool: set up the engine, run the period, follow the unknown-names loop, hand the operator the finished workbook.

**Distribution model (see `docs/superpowers/specs/2026-06-02-cowork-packaging-design.md`):** operators never install Python. The plugin is skill-only; the skill downloads a self-contained `tipout.exe` (built by `.github/workflows/release.yml` with PyInstaller) into `%USERPROFILE%\Documents\Tipout` on first run, and re-downloads it when the user says "update tipout". Releasing is `git tag vX.Y.Z && git push` — CI stamps the version, builds the exe + `tipout-plugin.zip`, and publishes a GitHub Release. The skill pulls from `releases/latest/download/tipout.exe`.

Its role in the graph: the skill references the CLI commands (`tipout init`, `tipout run`, `check-roster`, `bootstrap-roster`), implements the "Agent Skill" + "SKILL.md frontmatter" concepts from `docs/cowork-skill-refs/`, and carries the `do-not-guess` rule as a `rationale_for` edge back into `UnresolvedNames`.

Background reading if you're editing the skill or packaging it as a Cowork plugin: `docs/cowork-skill-refs/index.md` (read order in there).

## When you go to extend this

- **New column in the POS?** Add alias to `_HEADER_ALIASES` in `pos_parser.py`; add field to `ShiftRow`; thread through `build_grid`. Grep `ShiftRow` to find all sites.
- **New CLI command?** Add an `@main.command` in `cli.py` that delegates to a new module. Mirror the pattern of `check-roster`: CLI parses args, module does the work, CLI formats output.
- **New restaurant (WVM)?** WVM has AM/PM shifts and one-tab-per-day. The parser's day-block detection does not survive the layout change — it needs a separate parser module. `runner` / `summary` / `roster` can likely stay.
- **Roster schema change?** Update both `roster.py` (reader), `validator.py` (checker), and `bootstrap.py` (writer) together. Tests in `test_roster.py` + `test_validator.py` + `test_bootstrap.py` will catch drift.

## Operating constraints worth remembering

- **Windows-first.** README paths use `.venv/Scripts/`. The repo is developed and tested on Windows; macOS/Linux works but isn't the primary surface.
- **No network, no DB, no state file.** Everything is on disk in Excel or YAML. If you're reaching for one, something is probably off-design.
- **UTF-8 writes on Windows.** openpyxl handles this, but raw `Path.write_text()` without `encoding='utf-8'` will crash on non-ASCII content under cp1252. We hit this with graphify's report output.
- **`anchor_date` must be a Monday and must actually start a known pay period.** Don't drift this without updating the 14-day math in tests.

## Deeper dives

- Architecture rationale and non-obvious decisions: `docs/plans/2026-04-18-surfing-deer-tipout-automation-design.md`
- Phase-by-phase build log: `docs/plans/2026-04-18-surfing-deer-tipout-implementation.md`
- Business context (what each spreadsheet means to the operator): `OVERVIEW.md`
- Operator-facing usage: `README.md`
- Cowork / plugin / skill packaging references: `docs/cowork-skill-refs/`

## Exploring the graph itself

Both knowledge graphs live under `graphify-runs/`:

- `graphify-runs/project/graph.html` — open in a browser, interactive
- `graphify-runs/project/GRAPH_REPORT.md` — god nodes, surprising connections, suggested questions
- `graphify-runs/project/graph.json` — raw NetworkX-compatible JSON (what an agent should load if it wants to query programmatically)
- `graphify-runs/docs/*` — same, for the Cowork/Skills reference docs (`docs/cowork-skill-refs/`)

To query the graph from code: `from networkx.readwrite import json_graph; G = json_graph.node_link_graph(json.load(open('graphify-runs/project/graph.json')), edges='links')`. Then use standard NetworkX traversals — the highest-signal views are neighbors of god nodes, `rationale_for` edges, and the three hyperedges listed above.
