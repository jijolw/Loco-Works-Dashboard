"""
core/erp_edit.py - EDIT ONE FIELD of one coach visit in the Carriage ERP (office PC only, JIJO only).
Made by Claude for JIJO, 31-10-2026. Page: http://127.0.0.1:5000/edit  (not in the menu).

Same safety as 13_Fix_Actual_Despatch / 14_Fix_Status / 15_Fix_Corr_Comp:
 - the visit is read LIVE from ERP before the preview and again just before writing; if the field changed in
   between, nothing is written
 - a field that already has a value is changed only when 'replace existing' is ticked
 - after the write the visit is read back: the new value must be there and every other main field unchanged
 - every write is logged in data/erp_edit_log.csv (time, coach, demand, field, old, new, result)
Login from .env (no password in code).
"""
import csv
import json
import os
from datetime import datetime

import config
from core import rules as R

LOG = os.path.join(config.APP_DIR, "data", "erp_edit_log.csv")

# field -> (label, kind)   kind: date / status / text
FIELDS = {
    "corrPlace": ("Corrosion placed", "date"),
    "corrComp": ("Corrosion completed", "date"),
    "corrPd": ("Corrosion PDC", "date"),
    "pdcDate": ("PDC (despatch)", "date"),
    "dispatchDate": ("Outturn date (desp date)", "date"),
    "actualDispatchDate": ("Actual (physical) despatch date", "date"),
    "status": ("Status", "status"),
    "pitNum": ("Line / pit (e.g. PS/L1_1, OT/YD)", "text"),
}
STATUSES = ["Running", "Return"]
WATCH = ("coachNo", "receivedDate", "dispatchDate", "actualDispatchDate", "corrPlace", "corrComp", "corrPd",
         "pdcDate", "status", "pitNum", "repairType", "divisionId")

_sess = None


def _session(fresh=False):
    global _sess
    from core import erp_client
    if fresh or _sess is None:
        _sess = erp_client.get_session()
    return _sess


def _url(demand):
    return f"{config.ERP_API.rstrip('/')}/locos/masters/coach-receipts/{demand}"


def read_live(demand):
    for attempt in (0, 1):
        s = _session(fresh=bool(attempt))
        r = s.get(_url(demand), timeout=20)
        if r.status_code in (401, 403) and not attempt:
            continue
        r.raise_for_status()
        j = r.json()
        return j["data"] if isinstance(j, dict) and isinstance(j.get("data"), dict) else j
    raise RuntimeError("ERP login failed")


def visits(D, coach):
    """All visits of a coach in the export, latest first."""
    k = R.coach_key({"coachNo": coach})
    v = [d for d in D if R.coach_key(d) == k]
    return sorted(v, key=lambda d: str(d.get("receivedDate") or ""), reverse=True)


def as_erp(value, kind, sample):
    """Value in the form ERP uses. Dates follow the form of the record's other dates."""
    if kind != "date":
        return value
    if not value:
        return None
    d = R.pdate(value)
    s = str(sample or "")
    if len(s) >= 10 and s[4] == "-":
        return d.isoformat() + (s[10:] if "T" in s else "")
    if len(s) >= 10 and s[2] == "/":
        return d.strftime("%d/%m/%Y")
    if len(s) >= 10 and s[2] == "-":
        return d.strftime("%d-%m-%Y")
    return d.isoformat()


def _same(a, b, kind):
    if kind == "date":
        return (R.pdate(a) or None) == (R.pdate(b) or None)
    return str(a or "").strip() == str(b or "").strip()


def check(rec, field, new, replace):
    """-> (ok, message) - the rules before any write."""
    if field not in FIELDS:
        return False, "field not allowed"
    label, kind = FIELDS[field]
    old = rec.get(field)
    if kind == "date" and new and not R.pdate(new):
        return False, "date not understood"
    if kind == "status" and new not in STATUSES:
        return False, "status must be Running or Return"
    if _same(old, new, kind):
        return False, f"ERP already shows {old or 'blank'}"
    if kind == "date" and old not in (None, "") and not replace:      # status / line change normally - no tick needed
        return False, f"{label} already has {old} - tick 'replace existing' to change it"
    rd, nd = R.pdate(rec.get("receivedDate")), R.pdate(new) if kind == "date" else None
    if nd and rd and nd < rd:
        return False, f"date is before the received date {R.fmt(rd)}"
    if nd and nd > datetime.now().date() and field not in ("corrPd", "pdcDate"):
        return False, "date is in the future"
    return True, ""


def write(demand, coach, field, new, replace, expect_old):
    """Write one field and verify. Returns the record read back. Raises on any problem (nothing or one field written)."""
    label, kind = FIELDS[field]
    rec = read_live(demand)
    if R.coach_key(rec) != R.coach_key({"coachNo": coach}):
        raise RuntimeError(f"demand {demand} belongs to coach {rec.get('coachNo')} - not written")
    if not _same(rec.get(field), expect_old, kind):
        raise RuntimeError(f"{label} changed in ERP since the preview (now {rec.get(field) or 'blank'}) - not written")
    ok, msg = check(rec, field, new, replace)
    if not ok:
        raise RuntimeError(msg + " - not written")
    keep = {k: rec.get(k) for k in WATCH if k != field}
    sample = rec.get("receivedDate") or rec.get("corrPlace")
    old = rec.get(field)
    rec[field] = as_erp(new, kind, sample)
    s = _session()
    hdr = {"Content-Type": "application/json"}
    x = s.cookies.get("XSRF-TOKEN")
    if x:
        hdr["X-XSRF-TOKEN"] = x
    resp = s.put(_url(demand), data=json.dumps(rec), headers=hdr, timeout=20)
    result = f"HTTP {resp.status_code}"
    try:
        if resp.status_code >= 400:
            raise RuntimeError(f"ERP refused the change ({result}) {resp.text[:200]}")
        after = read_live(demand)
        if not _same(after.get(field), new, kind):
            raise RuntimeError(f"ERP accepted but {label} now reads {after.get(field) or 'blank'} - check in ERP")
        for k, v in keep.items():
            if str(after.get(k)) != str(v):
                raise RuntimeError(f"WARNING {k} changed {v} -> {after.get(k)} - check in ERP at once")
        result += " verified"
        return after
    except Exception as e:
        result += " " + str(e)
        raise
    finally:
        _log(coach, demand, field, old, rec[field], result)


def _log(coach, demand, field, old, new, result):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    new_file = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["time", "coach", "demand", "field", "old", "new", "result"])
        w.writerow([datetime.now().strftime("%d-%m-%Y %H:%M:%S"), coach, demand, field, old or "", new or "", result])


def recent_log(n=15):
    try:
        with open(LOG, encoding="utf-8") as f:
            return list(csv.DictReader(f))[-n:][::-1]
    except Exception:
        return []
