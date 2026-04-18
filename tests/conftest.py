from datetime import date as _date

import pytest
import yaml
from openpyxl import Workbook


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


@pytest.fixture
def tiny_runner_env(tmp_path):
    """Build POS + roster + config under tmp_path for end-to-end tests.

    POS has Anthony + Jake on 2025-12-29 (Monday of the first pay period).
    """
    pos_wb = Workbook()
    ws = pos_wb.active
    ws.title = "12.29 to 01.04.2026"
    ws["A1"] = "Surfing Deer Daily Cash"
    ws["B3"] = _date(2025, 12, 29)
    ws["D3"] = "Monday"
    ws["A4"] = "PM"
    ws["B4"] = "Monday"
    ws["C4"] = "CC Tips"
    ws["D4"] = "Party"
    ws["E4"] = "SA Tip Out"
    ws["F4"] = "Bar Tipout"
    ws["G4"] = "TotalTip Out"
    ws["H4"] = "Barback"
    ws["I4"] = "Bartender"
    ws["J4"] = "Net tip"
    ws["B5"] = "Anthony"
    ws["C5"] = 583
    ws["E5"] = 73.81
    ws["F5"] = 34.8
    ws["G5"] = 108.61
    ws["J5"] = 474.39
    ws["B6"] = "Jake"
    ws["C6"] = 219.87
    ws["E6"] = 10.25
    ws["G6"] = 10.25
    ws["I6"] = 65.2
    ws["J6"] = 274.82
    pos_path = tmp_path / "pos.xlsx"
    pos_wb.save(pos_path)

    rwb = Workbook()
    emp = rwb.active
    emp.title = "Employees"
    emp.append(["Canonical Name", "Role", "Active From", "Active To", "Notes"])
    emp.append(["Anthony Garcia", "server", _date(2025, 1, 1), None, ""])
    emp.append(["Jake Purvis", "bartender", _date(2025, 1, 1), None, ""])
    aliases = rwb.create_sheet("Name Aliases")
    aliases.append(["Raw Name", "Canonical Name"])
    aliases.append(["Anthony", "Anthony Garcia"])
    aliases.append(["Jake", "Jake Purvis"])
    roster_path = tmp_path / "roster.xlsx"
    rwb.save(roster_path)

    summary_path = tmp_path / "summary.xlsx"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "anchor_date": _date(2025, 12, 29),
                "roster_path": str(roster_path),
                "summary_path": str(summary_path),
            }
        ),
        encoding="utf-8",
    )

    return {
        "config_path": config_path,
        "pos_path": pos_path,
        "roster_path": roster_path,
        "summary_path": summary_path,
    }
