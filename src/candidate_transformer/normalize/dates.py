from __future__ import annotations

import re
from datetime import datetime


_MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def normalize_date_ym(raw: str | None) -> str | None:
    """Normalize a date string to YYYY-MM."""
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip().lower().replace("/", "-")

    # YYYY-MM or YYYY-MM-DD
    match = re.match(r"^(\d{4})-(\d{1,2})(?:-\d{1,2})?$", text)
    if match:
        year, month = match.group(1), match.group(2).zfill(2)
        if 1 <= int(month) <= 12:
            return f"{year}-{month}"

    # MM-YYYY or MM/YYYY
    match = re.match(r"^(\d{1,2})-(\d{4})$", text)
    if match:
        month, year = match.group(1).zfill(2), match.group(2)
        if 1 <= int(month) <= 12:
            return f"{year}-{month}"

    # Mon YYYY
    match = re.match(r"^([a-z]{3,9})\s+(\d{4})$", text)
    if match:
        month_key = match.group(1)[:3]
        if month_key in _MONTH_MAP:
            return f"{match.group(2)}-{_MONTH_MAP[month_key]}"

    # YYYY only
    match = re.match(r"^(\d{4})$", text)
    if match:
        return f"{match.group(1)}-01"

    # Present / current
    if text in {"present", "current", "now"}:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        return f"{now.year}-{now.month:02d}"

    return None


def parse_year_from_text(raw: str | None) -> int | None:
    if not raw:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", str(raw))
    if match:
        return int(match.group(0))
    return None
