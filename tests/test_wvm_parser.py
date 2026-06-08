from datetime import date

import pytest

from tests.wvm_fixtures import build_wvm_workbook


@pytest.fixture
def wvm_path(tmp_path):
    p = tmp_path / "wvm.xlsx"
    build_wvm_workbook(p)
    return p


def test_fixture_builds_expected_sheets(wvm_path):
    from openpyxl import load_workbook
    names = [n.strip() for n in load_workbook(wvm_path).sheetnames]
    assert "12.29.25" in names
    assert "Sheet1" in names
    assert "01.08.2026" in names


from tipout.wvm_parser import parse_workbook


def test_parse_reads_net_tip_and_date_from_happy_tab(wvm_path):
    rows = parse_workbook(wvm_path)
    by = [(r.date, r.raw_name, r.net_tip) for r in rows]
    assert (date(2025, 12, 29), "Ornella", 162.28) in by
    assert (date(2025, 12, 29), "Dwayne Graham", 424.28) in by


def test_parse_skips_zero_rows(wvm_path):
    rows = parse_workbook(wvm_path)
    assert not [r for r in rows if r.raw_name == "Heather"]  # net 0 -> skipped


def test_parse_skips_sheet1(wvm_path):
    rows = parse_workbook(wvm_path)
    # Sheet1 has no date-shaped name; nothing should come from it (no crash).
    assert all(r.date is not None for r in rows)


def test_parse_does_not_read_po_block(wvm_path):
    rows = parse_workbook(wvm_path)
    assert not [r for r in rows if r.raw_name == "Total CC Tips"]


def test_parse_keeps_only_net_tip_other_fields_zero(wvm_path):
    rows = parse_workbook(wvm_path)
    r = next(r for r in rows if r.raw_name == "Ornella" and r.date == date(2025, 12, 29))
    assert r.cc_tips == 0.0 and r.bar_tipout == 0.0 and r.is_party is False
