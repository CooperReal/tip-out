from dataclasses import dataclass
from datetime import date
from pathlib import Path
import yaml

@dataclass
class Config:
    anchor_date: date
    roster_path: Path
    summary_path: Path
    per_employee_dir: Path
    archive_dir: Path

    @classmethod
    def load(cls, path: Path) -> "Config":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        base = path.parent  # relative paths resolve against the config file's dir
        def p(key: str) -> Path:
            v = data[key]
            pp = Path(v)
            return pp if pp.is_absolute() else (base / pp).resolve()
        anchor = data["anchor_date"]
        if not isinstance(anchor, date):
            raise TypeError(f"anchor_date must be a YYYY-MM-DD date, got {anchor!r}")
        return cls(
            anchor_date=anchor,
            roster_path=p("roster_path"),
            summary_path=p("summary_path"),
            per_employee_dir=p("per_employee_dir"),
            archive_dir=p("archive_dir"),
        )
