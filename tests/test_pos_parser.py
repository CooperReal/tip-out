from pathlib import Path

from tipout.pos_parser import parse_workbook

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_pos.xlsx"


def test_parses_single_day_block():
    rows = parse_workbook(FIXTURE)
    assert len(rows) == 2
    anthony = next(r for r in rows if r.raw_name == "Anthony")
    assert anthony.date.isoformat() == "2025-12-29"
    assert anthony.cc_tips == 583.0
    assert anthony.sa_tip_out == 73.81
    assert anthony.bar_tipout == 34.8
    assert anthony.net_tip == 474.39
    assert anthony.is_party is False
