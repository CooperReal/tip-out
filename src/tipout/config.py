from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml


@dataclass
class Config:
    anchor_date: date
    roster_path: Path
    summary_path: Path

    @classmethod
    def load(cls, path: Path) -> "Config":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        base = path.parent

        def _resolve(key: str) -> Path:
            p = Path(data[key])
            return p if p.is_absolute() else (base / p).resolve()

        anchor = data["anchor_date"]
        if not isinstance(anchor, date):
            raise TypeError(f"anchor_date must be a YYYY-MM-DD date, got {anchor!r}")

        return cls(
            anchor_date=anchor,
            roster_path=_resolve("roster_path"),
            summary_path=_resolve("summary_path"),
        )
