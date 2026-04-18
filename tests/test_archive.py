import json
import os
import time
from datetime import date
from hashlib import sha256
from pathlib import Path

import pytest


def _file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_runner(env):
    from tipout.runner import run
    from tipout.config import Config
    from tipout.period import PayPeriod

    cfg = Config.load(env["config_path"])
    period = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    run_id = run(cfg, env["pos_path"], env["hours_path"], period)
    return cfg, run_id


def test_archive_run_copies_inputs(tiny_runner_env):
    env = tiny_runner_env
    cfg, run_id = _run_runner(env)

    archive_root = cfg.archive_dir / run_id
    archived_pos = archive_root / "input_pos.xlsx"
    assert archived_pos.exists()
    assert _file_sha256(archived_pos) == _file_sha256(env["pos_path"])

    archived_hours = archive_root / "input_hours.xlsx"
    assert archived_hours.exists()
    assert _file_sha256(archived_hours) == _file_sha256(env["hours_path"])

    archived_roster = archive_root / "input_roster.xlsx"
    assert archived_roster.exists()
    assert _file_sha256(archived_roster) == _file_sha256(env["roster_path"])


def test_archive_includes_outputs(tiny_runner_env):
    env = tiny_runner_env
    cfg, run_id = _run_runner(env)

    archive_root = cfg.archive_dir / run_id
    assert (archive_root / "outputs" / "summary.xlsx").exists()
    assert (archive_root / "outputs" / "per_employee" / "Anthony Garcia.xlsx").exists()
    assert (archive_root / "outputs" / "anomaly_report.xlsx").exists()


def test_archive_has_hashes_and_run_json(tiny_runner_env):
    env = tiny_runner_env
    cfg, run_id = _run_runner(env)

    archive_root = cfg.archive_dir / run_id
    hashes_path = archive_root / "hashes.json"
    run_path = archive_root / "run.json"
    assert hashes_path.exists()
    assert run_path.exists()

    hashes = json.loads(hashes_path.read_text())
    expected_files = {
        p.relative_to(archive_root).as_posix()
        for p in archive_root.rglob("*")
        if p.is_file() and p.name not in {"hashes.json", "run.json"}
    }
    assert set(hashes.keys()) == expected_files
    for rel, digest in hashes.items():
        assert _file_sha256(archive_root / rel) == digest

    run_meta = json.loads(run_path.read_text())
    assert run_meta["run_id"] == run_id
    assert "tipout_version" in run_meta
    assert run_meta["period"]["start"] == "2025-12-29"
    assert run_meta["period"]["end"] == "2026-01-11"
    assert "started_at_utc" in run_meta
    assert "ended_at_utc" in run_meta
    assert run_meta["operator_answers"] == {}


def test_archive_run_is_readonly(tiny_runner_env):
    env = tiny_runner_env
    cfg, run_id = _run_runner(env)

    archived_pos = cfg.archive_dir / run_id / "input_pos.xlsx"
    assert archived_pos.exists()

    if os.name == "nt":
        with pytest.raises(PermissionError):
            archived_pos.open("ab").close()
    else:
        pytest.skip("read-only enforcement on POSIX is owner-permissive; not asserting")


def test_run_id_is_sortable_and_unique():
    from tipout.archive import make_run_id

    ids = []
    for _ in range(5):
        ids.append(make_run_id())
        time.sleep(0.0001)  # 100us — guarantees distinct microsecond readings
    assert len(set(ids)) == 5, "IDs must be unique"
    assert ids == sorted(ids), "IDs must sort in creation order"
