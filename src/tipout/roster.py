# src/tipout/roster.py
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from openpyxl import load_workbook

@dataclass
class Employee:
    canonical: str
    role: str
    active_from: date | None
    active_to: date | None

@dataclass
class Roster:
    employees: dict[str, Employee]
    aliases: dict[str, str]  # raw -> canonical

    def resolve(self, raw: str) -> str | None:
        key = raw.strip() if isinstance(raw, str) else raw
        if key in self.employees:
            return key
        return self.aliases.get(raw) or self.aliases.get(key)

    def fuzzy_candidates(self, raw: str) -> list[str]:
        """Return canonicals whose first name matches raw (case-insensitive, ignoring role tags like '(Xen)')."""
        first = raw.split()[0].strip().lower().rstrip(",")
        return [
            e.canonical for e in self.employees.values()
            if e.canonical.split()[0].lower() == first
        ]

def load_roster(path: Path) -> Roster:
    wb = load_workbook(path, data_only=True)
    emps: dict[str, Employee] = {}
    for row in wb["Employees"].iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        name, role, af, at, *_ = row
        emps[name] = Employee(
            canonical=name,
            role=role or "",
            active_from=af if isinstance(af, date) else None,
            active_to=at if isinstance(at, date) else None,
        )
    aliases: dict[str, str] = {}
    for row in wb["Name Aliases"].iter_rows(min_row=2, values_only=True):
        if not row or not row[0] or not row[1]:
            continue
        aliases[row[0]] = row[1]
    return Roster(employees=emps, aliases=aliases)
