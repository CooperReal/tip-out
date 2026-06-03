# Tipout for Cowork — packaging & distribution design

**Date:** 2026-06-02
**Status:** Approved (design), ready for implementation
**Repo:** https://github.com/CooperReal/tip-out

## Problem

The tipout tool ships today as a GitHub repo. To use it in Claude Cowork, a
non-technical operator (the maintainer's parents, on a basic Windows machine)
had to:

1. Navigate GitHub and get the plugin/skill code into Cowork.
2. Install Python and run `pipx install .` / `pip install -e .` in a terminal so
   the `tipout` CLI lands on `PATH`.

Both steps were hard. Updates were worse — there was no clear path to "get the
new version," so the operators were confused every time the tool changed.

**Goal:** make install a single one-time file upload (no GitHub browsing, no
terminal, no Python), and make updates fully conversational — the operator says
"update tipout" and their Cowork Claude does the rest.

## Constraints & confirmed facts

- **Target:** Claude Cowork (the Cowork tab of Claude Desktop). Tools run
  **locally on the user's Windows machine** — confirmed by the plugin model
  (bundled MCP servers / `bin/` executables run "on the user's machine") and
  empirically by the operators' prior working setup (a local install only works
  if Bash executes locally).
- **OS:** Windows only for the operators. A Windows `.exe` is the right engine
  artifact. (The Windows-specific approach was explicitly accepted.)
- **Updates:** must be runnable from inside a Cowork session ("Claude does it for
  them"). We do **not** rely on any Cowork plugin "update" button — that flow is
  undocumented in Cowork.
- **Repo/releases public:** confirmed OK, so downloads use the stable GitHub
  "latest" URL with no login.
- **Build:** GitHub Actions (Windows runner) is acceptable; no local Windows
  needed.
- **Prerequisite to document:** the operators' Cowork must have *code execution /
  Bash* enabled (one-time toggle).

## Core idea: two-layer split

Separate the rarely-changing instructions from the often-changing logic so each
updates on its own cadence.

| Layer | Artifact | Changes | Update mechanism |
|---|---|---|---|
| **Plugin (skill)** | `tipout-plugin.zip` → `SKILL.md` + `plugin.json` | rarely | one-time upload in Cowork |
| **Engine** | `tipout.exe` (PyInstaller, no Python needed) | often | self-update from a session ("update tipout") |

The engine lives **outside** the plugin so the skill can replace it from within a
session. `${CLAUDE_PLUGIN_ROOT}` resets on plugin update and a session shouldn't
mutate plugin files, so the engine must not live in the plugin's `bin/`.

## Operator experience

1. **Once, ever:** open the link to `tipout-plugin.zip`, then in Cowork:
   *Customize → Browse plugins → upload* the file. (Plus a one-time "enable code
   execution" toggle if not already on.)
2. **Each pay period:** "Run the tip-out for this period" + provide the POS file —
   unchanged from today.
3. **Updates:** type **"update tipout"**. Claude downloads the latest engine and
   reports what changed.

## Folder layout (created automatically on first run)

Fixed, discoverable path — **no install-time "type your project path" prompt**.
The current `userConfig.project_dir` prompt in `plugin.json` is removed.

```
%USERPROFILE%\Documents\Tipout\
├── tipout.exe        ← engine (downloaded; "update tipout" replaces this)
├── config.yaml       ← scaffolded on first run
├── roster.xlsx       ← scaffolded (optionally seeded from an existing summary)
├── version.txt       ← installed engine version (for update comparison)
└── output\
    └── summary.xlsx   ← append-only results
```

The skill invokes the engine by absolute path, e.g.
`"%USERPROFILE%\Documents\Tipout\tipout.exe" run --period ... --pos ...`.

## First-run setup (skill-driven, automatic)

When the skill detects no `tipout.exe` in the folder, Claude:

1. Creates `Documents\Tipout\output\`.
2. Downloads the engine (curl ships with Windows 10+, shell-agnostic):
   ```
   curl -L -o "%USERPROFILE%\Documents\Tipout\tipout.exe" \
     https://github.com/CooperReal/tip-out/releases/latest/download/tipout.exe
   ```
   then `powershell -Command "Unblock-File '<path>\tipout.exe'"`.
3. Scaffolds `config.yaml` + `roster.xlsx` via a new `tipout init` command.
   Optional: `tipout init --from-summary <old workbook>` seeds the roster from the
   operator's hand-kept summary, reusing the existing
   `bootstrap.extract_roster_from_summary` / `write_roster` logic.
4. Writes `version.txt` from `tipout version`.
5. Verifies with `tipout version`.

## Update flow ("update tipout")

1. Read `version.txt` (current) and fetch the latest release metadata:
   `https://api.github.com/repos/CooperReal/tip-out/releases/latest` →
   `tag_name` + `body` (release notes).
2. If current == latest → tell the operator they're already up to date.
3. Otherwise: re-download `tipout.exe`, `Unblock-File`, write new `version.txt`,
   verify `tipout version`, and report the release notes ("what changed").

The existing **change-request flow stays** (when an operator wants *behavior*
changed, the skill writes a spec for the maintainer). The only difference: once a
change ships, operators say "update tipout" instead of re-fetching from GitHub.

## Release pipeline (maintainer side)

GitHub Actions workflow on a **Windows runner**, triggered on tag `v*`:

1. `pip install pyinstaller .`
2. Build a single-file `tipout.exe` with the version stamped from the tag.
3. Zip the skill folder into `tipout-plugin.zip`.
4. Create a GitHub Release with both assets attached. The
   `releases/latest/download/tipout.exe` URL then auto-points to the newest.

**Releasing becomes:** `git tag v0.2.0 && git push --tags`.

Version source of truth: the git tag. CI stamps `tipout/__init__.py:__version__`
(and `plugin.json` version) from the tag at build time so `tipout version`
matches the release.

## New / changed components

| Component | Change |
|---|---|
| `src/tipout/cli.py` | Add `tipout init` command (scaffold `config.yaml` + `roster.xlsx`; `--from-summary` seeds roster). |
| `tipout-plugin/.claude-plugin/plugin.json` | Remove `userConfig.project_dir`; bump version; keep skill-only. |
| `tipout-plugin/skills/tipout/SKILL.md` | New "Setup (first run)" + "Update" sections; invoke engine by absolute path; widen `allowed-tools` for download/run; document the fixed folder. |
| `.github/workflows/release.yml` (new) | Windows build → PyInstaller exe + plugin zip → GitHub Release on tag. |
| `pyproject.toml` | Add `pyinstaller` to a build/dev extra if needed. |
| `README.md` / `AGENTS.md` | Document the new install/update story and release procedure. |

## Risks / residual notes

- **SmartScreen / AV:** largely sidestepped — the skill always runs the exe
  *programmatically* (CLI), never via GUI double-click, and the download step runs
  `Unblock-File`. Residual: PyInstaller exes can trip AV false-positives;
  mitigation is code-signing, deferred past v1.
- **Code-execution toggle** must be enabled in the operators' Cowork (documented
  as a one-time step).
- **First install is not conversational** (chicken-and-egg). It remains a one-time
  file upload; everything after is conversational.

## Out of scope (v1)

- Code signing the exe.
- A hosted Cowork marketplace (custom-marketplace support in Cowork is
  undocumented; revisit later).
- macOS/Linux engine artifacts (operators are Windows-only).
