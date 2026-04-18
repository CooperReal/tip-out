from datetime import date as _date
from openpyxl import Workbook
import pytest

@pytest.fixture
def tiny_roster(tmp_path):
    wb = Workbook()
    emp = wb.active
    emp.title = "Employees"
    emp.append(["Canonical Name", "Role", "Active From", "Active To", "Notes"])
    emp.append(["Anthony Garcia", "server", _date(2025, 1, 1), None, ""])
    emp.append(["Jake Purvis", "bartender", _date(2025, 1, 1), None, ""])
    emp.append(["Kristin Bartosic", "bartender", _date(2025, 1, 1), None, ""])
    emp.append(["Andrew Roberts", "server", _date(2025, 1, 1), None, ""])
    emp.append(["Andrew Neita", "server", _date(2025, 1, 1), None, ""])
    aliases = wb.create_sheet("Name Aliases")
    aliases.append(["Raw Name", "Canonical Name"])
    aliases.append(["Anthony", "Anthony Garcia"])
    aliases.append(["anthony", "Anthony Garcia"])
    aliases.append(["Jake", "Jake Purvis"])
    aliases.append(["Kristin", "Kristin Bartosic"])
    aliases.append(["kristin", "Kristin Bartosic"])
    path = tmp_path / "roster.xlsx"
    wb.save(path)
    return path
