from datetime import date

import pytest

from tipout.period import PayPeriod


def test_pay_period_from_anchor():
    p = PayPeriod.from_anchor(anchor=date(2025, 12, 29), containing_date=date(2026, 1, 5))
    assert p.start == date(2025, 12, 29)
    assert p.end == date(2026, 1, 11)


def test_pay_period_from_anchor_year_rollover():
    p = PayPeriod.from_anchor(anchor=date(2025, 12, 29), containing_date=date(2026, 1, 1))
    assert p.start == date(2025, 12, 29)
    assert p.end == date(2026, 1, 11)


def test_pay_period_from_anchor_second_period():
    p = PayPeriod.from_anchor(anchor=date(2025, 12, 29), containing_date=date(2026, 1, 12))
    assert p.start == date(2026, 1, 12)
    assert p.end == date(2026, 1, 25)


def test_pay_period_from_dates_valid():
    p = PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 11))
    assert p.start == date(2025, 12, 29)
    assert p.end == date(2026, 1, 11)


def test_pay_period_from_dates_invalid_length():
    with pytest.raises(AssertionError):
        PayPeriod.from_dates(date(2025, 12, 29), date(2026, 1, 12))
