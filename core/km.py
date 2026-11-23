"""
core/km.py - Kumbh Mela status from the HQ sheet "2026 KM SPLs", tab LW/PER (READ ONLY, never written).
Used by the Daily Position page 1 line (JIJO 12-11-2026): KM coaches despatched / POH completed / under POH, by type.
The nominated total is not shown (it keeps changing). Saved copy: data/km_status.json (same file daily_sync writes).
"""
import csv
import io
import json
import os
import re
import urllib.request
from datetime import datetime

import config

FILE = os.path.join(config.APP_DIR, "data", "km_status.json")


def _key(c):
    return re.sub(r"\D", "", str(c or "")).lstrip("0")


def refresh():
    """Read the HQ LW/PER tab (gviz csv) -> saves and returns {updated, read_at, coaches{no: status}, types{no: type}}."""
    url = (f"https://docs.google.com/spreadsheets/d/{config.HQ_KM_SHEET_KEY}/gviz/tq?tqx=out:csv"
           f"&sheet=LW%2FPER&t={datetime.now():%H%M%S}")
    rows = list(csv.reader(io.StringIO(urllib.request.urlopen(url, timeout=30).read().decode("utf-8"))))
    hi = next(i for i, r in enumerate(rows) if "coach no." in [c.strip().lower() for c in r])
    h = [c.strip().lower() for c in rows[hi]]
    ix = lambda name: next((i for i, c in enumerate(h) if c.startswith(name)), None)
    i_no, i_type, i_st = ix("coach no"), ix("coach type"), ix("status")
    upd = next((r[r.index(c) + 1] for r in rows[:hi] for c in r if "updated date" in c.lower() and r.index(c) + 1 < len(r)), "")
    coaches, types = {}, {}
    for r in rows[hi + 1:]:
        if i_st is None or len(r) <= i_st or not r[i_no].strip():
            continue
        k = _key(r[i_no])
        coaches[k] = r[i_st].strip().upper()
        if i_type is not None and i_type < len(r):
            types[k] = r[i_type].strip().upper()
    out = {"updated": upd, "read_at": f"{datetime.now():%Y-%m-%d %H:%M}", "coaches": coaches, "types": types}
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(out, f)
    return out


def load():
    try:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
