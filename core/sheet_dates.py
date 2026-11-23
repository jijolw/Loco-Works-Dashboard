"""
core/sheet_dates.py - read whatever the shop typed in a date cell and give back a real date (JIJO 11-11-2026).

Accepted (day first, Indian style): 11.11.2026, 11.11.26, 11/11/2026, 11/11/26, 11-11-2026, 11-11-26, 11 11 26,
111126, 11112026, 11.11 (no year -> this year), 2026-11-11, 11-Nov-2026, 11 Nov 26, a sheet date serial (46337).
Anything else (words like 'Completed') is returned unchanged by fix(); to_date() returns None.
Sheets show every date column as dd/mm/yy (PATTERN).
"""
import re
from datetime import date, datetime, timedelta

PATTERN = "dd/mm/yy"
_EPOCH = date(1899, 12, 30)
_MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _mk(y, m, d):
    y = int(y)
    y += 2000 if y < 100 else 0
    try:
        x = date(y, int(m), int(d))
    except ValueError:
        return None
    return x if 2000 <= x.year <= 2100 else None


def to_date(v, today=None):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)) and 30000 < v < 80000:          # sheet serial number
        return _EPOCH + timedelta(days=int(v))
    s = str(v).strip().lstrip("'")
    if re.fullmatch(r"\d{5}(\.0+)?", s) and 30000 < float(s) < 80000:
        return _EPOCH + timedelta(days=int(float(s)))
    today = today or date.today()
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)                      # 2026-11-11
    if m:
        return _mk(m.group(1), m.group(2), m.group(3))
    m = re.fullmatch(r"(\d{1,2})\s*[./\- ]\s*(\d{1,2})\s*[./\- ]\s*(\d{2}|\d{4})", s)  # 11.11.26 / 11/11/2026
    if m:
        return _mk(m.group(3), m.group(2), m.group(1))
    m = re.fullmatch(r"(\d{1,2})\s*[./\-]\s*(\d{1,2})", s)                           # 11.11 -> this year
    if m:
        return _mk(today.year, m.group(2), m.group(1))
    m = re.fullmatch(r"(\d{2})(\d{2})(\d{2}|\d{4})", s)                              # 111126 / 11112026
    if m:
        return _mk(m.group(3), m.group(2), m.group(1))
    m = re.fullmatch(r"(\d{1,2})[\s\-./]*([A-Za-z]{3})[A-Za-z]*[\s\-./,]*(\d{2}|\d{4})", s)   # 11-Nov-2026
    if m and m.group(2).lower() in _MON:
        return _mk(m.group(3), _MON[m.group(2).lower()], m.group(1))
    return None


def fix(v, today=None):
    """For writing with USER_ENTERED in an en_GB sheet: a date -> 'dd/mm/yyyy', other text unchanged."""
    d = to_date(v, today)
    return d.strftime("%d/%m/%Y") if d else ("" if v is None else str(v).strip())


def serial(v, today=None):
    """For writing RAW: a date -> sheet serial number (shown by the dd/mm/yy format), other text unchanged."""
    d = to_date(v, today)
    return (d - _EPOCH).days if d else ("" if v is None else v)
