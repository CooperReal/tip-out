# src/tipout/roster.py
from dataclasses import dataclass
from pathlib import Path
from openpyxl import load_workbook

@dataclass
class Employee:
    canonical: str
    role: str

@dataclass
class Roster:
    employees: dict[str, Employee]
    aliases: dict[str, str]  # raw -> canonical

    def resolve(self, raw: str) -> str | None:
        key = raw.strip() if isinstance(raw, str) else raw
        if key in self.employees:
            return key
        return self.aliases.get(raw) or self.aliases.get(key)

def load_roster(path: Path) -> Roster:
    wb = load_workbook(path, data_only=True)
    emps: dict[str, Employee] = {}
    for row in wb["Employees"].iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        name = row[0]
        role = row[1] if len(row) > 1 else None
        emps[name] = Employee(canonical=name, role=role or "")
    aliases: dict[str, str] = {}
    for row in wb["Name Aliases"].iter_rows(min_row=2, values_only=True):
        if not row or not row[0] or not row[1]:
            continue
        aliases[row[0]] = row[1]
    return Roster(employees=emps, aliases=aliases)
