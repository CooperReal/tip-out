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
