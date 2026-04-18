from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import secrets
import shutil
import stat

from tipout import __version__
from tipout.config import Config
from tipout.period import PayPeriod


def make_run_id() -> str:
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H-%M-%S")
    micros = f"{now.microsecond:06d}"
    return f"{ts}-{micros}-{secrets.token_hex(3)}"


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _freeze_readonly(root: Path) -> None:
    """Set every file under root to read-only (best-effort, Windows-safe)."""
    for p in root.rglob("*"):
        if p.is_file():
            try:
                os.chmod(p, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            except OSError:
                # On Windows, the read-only bit is the only control we have; ignore if it fails.
                pass


def archive_run(
    run_id: str,
    config: Config,
    pos_path: Path,
    hours_path: Path | None,
    period: PayPeriod,
    started_at: datetime,
    operator_answers: dict | None = None,
) -> Path:
    """Copy inputs + outputs + roster into archive/<run-id>/ and freeze it read-only.

    ``hours_path`` may be ``None`` for summary-only runs; in that case no hours
    file is copied and ``run.json`` records ``hours_provided: False``.

    Returns the archive directory path.
    """
    archive_root = config.archive_dir / run_id
    (archive_root / "outputs" / "per_employee").mkdir(parents=True, exist_ok=True)

    # 1. Copy inputs
    shutil.copy2(pos_path, archive_root / "input_pos.xlsx")
    if hours_path is not None:
        shutil.copy2(hours_path, archive_root / "input_hours.xlsx")
    shutil.copy2(config.roster_path, archive_root / "input_roster.xlsx")

    # 2. Copy outputs (summary + per-employee + anomaly report)
    outputs_dir = archive_root / "outputs"

    if config.summary_path.exists():
        shutil.copy2(config.summary_path, outputs_dir / "summary.xlsx")

    if config.per_employee_dir.exists():
        for src in sorted(config.per_employee_dir.glob("*.xlsx")):
            shutil.copy2(src, outputs_dir / "per_employee" / src.name)

    anomaly_src = config.summary_path.parent / "anomaly_report.xlsx"
    if anomaly_src.exists():
        shutil.copy2(anomaly_src, outputs_dir / "anomaly_report.xlsx")

    # 3. Compute SHA-256 for every file now in the archive
    hashes: dict[str, str] = {}
    for p in archive_root.rglob("*"):
        if p.is_file() and p.name not in {"hashes.json", "run.json"}:
            rel = p.relative_to(archive_root).as_posix()
            hashes[rel] = _sha256(p)

    # 4. Write hashes.json
    (archive_root / "hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True)
    )

    # 5. Write run.json
    ended_at = datetime.now(timezone.utc)
    run_meta = {
        "run_id": run_id,
        "tipout_version": __version__,
        "period": {
            "start": period.start.isoformat(),
            "end": period.end.isoformat(),
        },
        "started_at_utc": started_at.isoformat(),
        "ended_at_utc": ended_at.isoformat(),
        "operator_answers": operator_answers or {},
        "hours_provided": hours_path is not None,
    }
    (archive_root / "run.json").write_text(
        json.dumps(run_meta, indent=2, sort_keys=True)
    )

    # 6. Freeze read-only
    _freeze_readonly(archive_root)

    return archive_root
