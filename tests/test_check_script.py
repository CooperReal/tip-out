"""Self-tests for the quality-gate runner (scripts/check.py)."""

import io
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check  # noqa: E402


def test_clean_env_scrubs_launcher_vars(monkeypatch):
    monkeypatch.setenv("__PYVENV_LAUNCHER__", "/whatever")
    monkeypatch.setenv("PYTHONHOME", "/whatever")
    monkeypatch.setenv("PYTHONPATH", "/whatever")
    env = check._clean_env()
    assert "__PYVENV_LAUNCHER__" not in env
    assert "PYTHONHOME" not in env
    assert "PYTHONPATH" not in env


def test_venv_python_exists():
    assert check._venv_python().exists()


def test_in_scope_accepts_project_python_files():
    assert check._in_scope(str(REPO / "src" / "tipout" / "cli.py"))
    assert check._in_scope(str(REPO / "tests" / "test_summary.py"))
    assert check._in_scope(str(REPO / "run_all.py"))
    assert check._in_scope(str(REPO / "scripts" / "check.py"))


def test_in_scope_rejects_others():
    assert not check._in_scope(str(REPO / "README.md"))
    assert not check._in_scope(str(REPO / "docs" / "anything.py"))
    assert not check._in_scope("/tmp/elsewhere.py")


def test_lint_passes_on_clean_tree():
    # Runs ruff + mypy (NOT pytest -> no recursion). Requires the tree to be clean.
    assert check.cmd_lint() == 0


def test_post_tool_emits_hook_json(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    rc = check.cmd_post_tool()
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert out["hookSpecificOutput"]["additionalContext"] == ""
