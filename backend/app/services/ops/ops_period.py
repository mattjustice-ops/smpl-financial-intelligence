"""Calendar month helpers for SMPL Ops reporting."""

from __future__ import annotations

import re
from datetime import datetime, timezone

_MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def parse_calendar_month(month: str) -> tuple[datetime, datetime]:
    """Return [start, end) UTC bounds for a YYYY-MM calendar month."""
    match = _MONTH_RE.match(month.strip())
    if not match:
        raise ValueError("month must be YYYY-MM")
    year = int(match.group(1))
    mon = int(match.group(2))
    start = datetime(year, mon, 1, tzinfo=timezone.utc)
    if mon == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, mon + 1, 1, tzinfo=timezone.utc)
    return start, end


def format_calendar_month(start: datetime) -> str:
    return f"{start.year:04d}-{start.month:02d}"


def recent_calendar_months(*, count: int = 12) -> list[str]:
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month
    months: list[str] = []
    for _ in range(max(1, min(count, 24))):
        months.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return months
