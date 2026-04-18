from datetime import date
from pathlib import Path

import pytest

from tipout.config import Config


FIXTURE = Path(__file__).parent / "fixtures" / "tiny_config.yaml"


def test_load_tiny_config():
    cfg = Config.load(FIXTURE)
    base = FIXTURE.parent.resolve()
    assert cfg.anchor_date == date(2025, 12, 29)
    assert cfg.roster_path == (base / "roster.xlsx").resolve()
    assert cfg.summary_path == (base / "summary.xlsx").resolve()
    assert cfg.per_employee_dir == (base / "per-employee").resolve()
    assert cfg.archive_dir == (base / "archive").resolve()


def test_load_rejects_string_anchor_date(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        'anchor_date: "2025-12-29"\n'
        "roster_path: roster.xlsx\n"
        "summary_path: summary.xlsx\n"
        "per_employee_dir: per-employee\n"
        "archive_dir: archive\n",
        encoding="utf-8",
    )
    with pytest.raises(TypeError):
        Config.load(bad)
