from dataclasses import dataclass
from datetime import date, timedelta

@dataclass(frozen=True)
class PayPeriod:
    start: date
    end: date  # inclusive

    @classmethod
    def from_anchor(cls, anchor: date, containing_date: date) -> "PayPeriod":
        delta_days = (containing_date - anchor).days
        periods_in = delta_days // 14
        start = anchor + timedelta(days=14 * periods_in)
        return cls(start=start, end=start + timedelta(days=13))

    @classmethod
    def from_dates(cls, start: date, end: date) -> "PayPeriod":
        assert (end - start).days == 13, "pay period must be 14 days inclusive"
        return cls(start=start, end=end)
