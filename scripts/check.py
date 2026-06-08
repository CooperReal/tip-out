#!/usr/bin/env python3
"""tipout quality gate.

Subcommands:
  post-tool  Claude PostToolUse hook: check the edited file, emit advisory context.
  stop       Claude Stop hook: auto-fix, then run the full gate; block on failure.
  full       ruff check + format-check + mypy + pytest (manual / CI).
  lint       ruff check + format-check + mypy (no pytest).
  fast       ruff check + mypy on a single --file.

Designed to run under the project .venv (the hooks invoke .venv/bin/python). If
launched by an older interpreter it re-execs itself under .venv.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_SCRUB_ENV_VARS = ("__PYVENV_LAUNCHER__", "PYTHONHOME", "PYTHONPATH")


def _venv_python(repo_root=REPO_ROOT):
    win = repo_root / ".venv" / "Scripts" / "python.exe"
    return win if win.exists() else repo_root / ".venv" / "bin" / "python"


# --- 3.8-safe guard: ensure we run under the project venv (Python >= 3.11) ---
if sys.version_info < (3, 11):  # noqa: UP036  (intentional <3.11 re-exec guard)
    _vpy = _venv_python()
    if _vpy.exists() and Path(sys.executable).resolve() != _vpy.resolve():
        _env = {k: v for k, v in os.environ.items() if k not in _SCRUB_ENV_VARS}
        os.execve(str(_vpy), [str(_vpy), str(Path(__file__).resolve()), *sys.argv[1:]], _env)
    sys.stderr.write(
        "check.py needs Python >= 3.11 (the project .venv). Run: uv pip install -e '.[dev]'\n"
    )
    raise SystemExit(1)

import argparse  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402

SCOPE = ["src/tipout", "tests", "run_all.py", "scripts"]
# _IN_SCOPE_DIR_PREFIXES is intentionally broader than SCOPE (uses "src/" not "src/tipout"):
# new packages under src/ are still checked on edit, not just the known src/tipout package.
_IN_SCOPE_DIR_PREFIXES = ("src/", "tests/", "scripts/")
_IN_SCOPE_FILES = ("run_all.py",)


def _clean_env():
    """Env for subprocesses, minus vars that corrupt a spawned venv interpreter."""
    env = dict(os.environ)
    for var in _SCRUB_ENV_VARS:
        env.pop(var, None)
    return env


def _ruff_cmd():
    win = REPO_ROOT / ".venv" / "Scripts" / "ruff.exe"
    nix = REPO_ROOT / ".venv" / "bin" / "ruff"
    if win.exists():
        return [str(win)]
    if nix.exists():
        return [str(nix)]
    return [str(_venv_python()), "-m", "ruff"]


def _py_module(module):
    return [str(_venv_python()), "-m", module]


def _in_scope(path):
    try:
        rel = Path(path).resolve().relative_to(REPO_ROOT)
    except ValueError:
        return False
    if rel.suffix != ".py":
        return False
    posix = rel.as_posix()
    return posix.startswith(_IN_SCOPE_DIR_PREFIXES) or posix in _IN_SCOPE_FILES


def _capture(cmd):
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=_clean_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError:
        return (1, f"{cmd[0]} not found. Run: uv pip install -e '.[dev]'\n")
    return proc.returncode, proc.stdout


def _mutate(cmd):
    try:
        subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=_clean_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return  # _capture in the verify step will surface a clear message


def _ruff_check(paths):
    return _capture([*_ruff_cmd(), "check", *paths])


def _ruff_format_check(paths):
    return _capture([*_ruff_cmd(), "format", "--check", *paths])


def _mypy(paths):
    return _capture([*_py_module("mypy"), *paths])


def _pytest():
    return _capture([*_py_module("pytest"), "-q"])


def _failures(results):
    return [(name, out) for name, (code, out) in results if code != 0]


def _report(results):
    failures = _failures(results)
    if not failures:
        print("All checks passed.")
        return 0
    for name, out in failures:
        print(f"\n===== {name} FAILED =====")
        print(out.rstrip())
    return 1


def cmd_full():
    return _report(
        [
            ("ruff check", _ruff_check(SCOPE)),
            ("ruff format", _ruff_format_check(SCOPE)),
            ("mypy", _mypy(SCOPE)),
            ("pytest", _pytest()),
        ]
    )


def cmd_lint():
    return _report(
        [
            ("ruff check", _ruff_check(SCOPE)),
            ("ruff format", _ruff_format_check(SCOPE)),
            ("mypy", _mypy(SCOPE)),
        ]
    )


def cmd_fast(file):
    if not _in_scope(file):
        return 0
    return _report(
        [
            ("ruff check", _capture([*_ruff_cmd(), "check", file])),
            ("mypy", _capture([*_py_module("mypy"), "--follow-imports=silent", file])),
        ]
    )


def _read_hook_stdin():
    try:
        raw = sys.stdin.read()
    except OSError:
        return {}
    try:
        return json.loads(raw or "{}")
    except ValueError:
        return {}


def cmd_post_tool():
    data = _read_hook_stdin()
    file = (data.get("tool_input") or {}).get("file_path")
    context = ""
    if file and _in_scope(file):
        parts = []
        for name, (code, out) in [
            ("ruff check", _capture([*_ruff_cmd(), "check", file])),
            ("mypy", _capture([*_py_module("mypy"), "--follow-imports=silent", file])),
        ]:
            if code != 0:
                parts.append(f"[{name}]\n{out.strip()}")
        if parts:
            joined = "\n\n".join(parts)
            context = f"Quality gate (advisory, non-blocking) found issues in {file}:\n\n{joined}"
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": context,
                }
            }
        )
    )
    return 0


def cmd_stop():
    data = _read_hook_stdin()
    # The turn is ending, so it is safe to auto-fix now.
    _mutate([*_ruff_cmd(), "format", *SCOPE])
    _mutate([*_ruff_cmd(), "check", "--fix", *SCOPE])
    _mutate([*_ruff_cmd(), "format", *SCOPE])
    results = [
        ("ruff check", _ruff_check(SCOPE)),
        ("ruff format", _ruff_format_check(SCOPE)),
        ("mypy", _mypy(SCOPE)),
        ("pytest", _pytest()),
    ]
    failures = _failures(results)
    if not failures:
        return 0
    summary = "\n\n".join(f"[{name}]\n{out.strip()}" for name, out in failures)
    if data.get("stop_hook_active"):
        # Safety valve: do not loop forever; surface and allow the stop.
        sys.stderr.write(f"Quality gate STILL failing after a fix attempt:\n{summary}\n")
        return 0
    sys.stderr.write(f"Quality gate failed; fix before finishing:\n{summary}\n")
    return 2


def main(argv=None):
    parser = argparse.ArgumentParser(prog="check.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("post-tool")
    sub.add_parser("stop")
    sub.add_parser("full")
    sub.add_parser("lint")
    fast = sub.add_parser("fast")
    fast.add_argument("--file", required=True)
    args = parser.parse_args(argv)
    return {
        "post-tool": cmd_post_tool,
        "stop": cmd_stop,
        "full": cmd_full,
        "lint": cmd_lint,
        "fast": lambda: cmd_fast(args.file),
    }[args.cmd]()


if __name__ == "__main__":
    raise SystemExit(main())
