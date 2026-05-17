"""Parse a Toast Time Clock CSV export into a flat list of HoursRow.

The CSV is block-structured: each block opens with a row like
``ANDREW ROBERTS - MAITRE'D Mon 05-04-2026 - Sun 05-17-2026,,,,,,,`` followed
by a column-header row, one row per shift, and a ``Total,,,,...`` row. Blank
rows separate blocks. One person can appear in multiple blocks with different
roles; this parser keeps shifts separate and lets downstream code aggregate.

The raw name is the substring before the first ' - ' in the block header,
``.title()``-cased for human-readable error messages. The roster's
case-insensitive resolver handles the actual matching.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class HoursRow:
    raw_name: str   # title-cased from the CSV's uppercase
    date: date      # from Start Date; midnight-crossing shifts attribute here
    hours: float    # from the Duration (Hours) column


# Last column index in a shift row: Start Date, Start Time, End Date, End Time,
# Reported Tips, Regular Hours, Overtime Hours, Duration (Hours) → 7.
_DURATION_COL = 7
_DATE_FMT = "%a, %m-%d-%y"


def parse_time_clock(path: Path) -> list[HoursRow]:
    rows: list[HoursRow] = []
    current_name: str | None = None
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.reader(fh):
            if not raw or not (raw[0] or "").strip():
                current_name = None
                continue
            first = raw[0].strip()
            if first == "Start Date":
                continue
            if first == "Total":
                continue
            if " - " in first:
                # Block header: NAME - ROLE <date-range>
                name_part = first.split(" - ", 1)[0].strip()
                current_name = name_part.title()
                continue
            # Anything else is a shift row.
            try:
                d = datetime.strptime(first, _DATE_FMT).date()
            except ValueError as exc:
                raise ValueError(
                    f"Time clock CSV: unrecognized row starting with {first!r}"
                ) from exc
            if current_name is None:
                raise ValueError(
                    f"Time clock CSV: shift row {first!r} appears before any "
                    "block header (NAME - ROLE)."
                )
            if len(raw) <= _DURATION_COL or not raw[_DURATION_COL].strip():
                hours = 0.0
            else:
                try:
                    hours = float(raw[_DURATION_COL])
                except ValueError as exc:
                    raise ValueError(
                        f"Time clock CSV: unparseable Duration value "
                        f"{raw[_DURATION_COL]!r} in shift row starting {first!r}"
                    ) from exc
            rows.append(HoursRow(raw_name=current_name, date=d, hours=hours))
    return rows
