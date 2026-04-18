from dataclasses import dataclass
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

EXPECTED_HEADERS = [
    "CC Tips", "SA Tip Out", "Bar Tipout",
    "TotalTip Out", "Barback", "Bartender", "Net tip",
]

@dataclass
class ShiftRow:
    date: date
    raw_name: str
    cc_tips: float
    party: float
    sa_tip_out: float
    bar_tipout: float
    total_tip_out: float
    barback: float
    bartender: float
    net_tip: float
    is_party: bool  # True if Party column had value (vs Cash RCP)

def parse_workbook(path: Path) -> list[ShiftRow]:
    wb = load_workbook(path, data_only=True)
    rows: list[ShiftRow] = []
    for sheet_name in wb.sheetnames:
        if sheet_name.strip() in {"Bank Master", "Sheet1"}:
            continue
        ws = wb[sheet_name]
        rows.extend(_parse_sheet(ws))
    return rows

def _parse_sheet(ws) -> list[ShiftRow]:
    blocks = _find_day_blocks(ws)
    out: list[ShiftRow] = []
    for block in blocks:
        out.extend(_parse_block(ws, block))
    return out

def _find_day_blocks(ws) -> list[dict]:
    """Return list of {start_col, headers: dict[label, col], date: date}."""
    header_row = 4
    blocks = []
    c = 1
    max_c = ws.max_column
    while c <= max_c:
        headers = {}
        for offset in range(12):  # scan up to 12 cols for a block's headers
            v = ws.cell(row=header_row, column=c + offset).value
            if isinstance(v, str) and v.strip() in {
                "CC Tips", "Party", "Cash RCP", "SA Tip Out", "Bar Tipout",
                "TotalTip Out", "Barback", "Bartender", "Net tip",
            }:
                headers[v.strip()] = c + offset
        if all(h in headers for h in EXPECTED_HEADERS):
            date_cell = ws.cell(row=3, column=c + 1).value  # date typically at col+1
            if not hasattr(date_cell, "date"):
                # fall back: search for a date in row 3 within block
                for offset in range(12):
                    v = ws.cell(row=3, column=c + offset).value
                    if hasattr(v, "date"):
                        date_cell = v
                        break
                else:
                    raise ValueError(
                        f"No date found in row 3 for day-block starting at col {c} "
                        f"in sheet {ws.title!r}"
                    )
            blocks.append({
                "start_col": c,
                "headers": headers,
                "date": date_cell.date(),
            })
            c = max(headers.values()) + 2  # advance past this block
        else:
            c += 1
    return blocks

def _parse_block(ws, block) -> list[ShiftRow]:
    out = []
    name_col = block["start_col"] + 1
    for r in range(5, 33):  # rows 5–32; row 33+ is reconciliation
        raw_name = ws.cell(row=r, column=name_col).value
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        def g(label):
            col = block["headers"].get(label)
            if col is None:
                return 0.0
            v = ws.cell(row=r, column=col).value
            return float(v) if isinstance(v, (int, float)) else 0.0
        net = g("Net tip")
        if net == 0.0 and g("CC Tips") == 0.0:
            continue
        is_party = "Party" in block["headers"] and g("Party") > 0
        out.append(ShiftRow(
            date=block["date"],
            raw_name=raw_name.strip(),
            cc_tips=g("CC Tips"),
            party=g("Party") if is_party else 0.0,
            sa_tip_out=g("SA Tip Out"),
            bar_tipout=g("Bar Tipout"),
            total_tip_out=g("TotalTip Out"),
            barback=g("Barback"),
            bartender=g("Bartender"),
            net_tip=net,
            is_party=is_party,
        ))
    return out
