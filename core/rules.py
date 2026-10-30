"""
core/rules.py - LW/PER business rules (single rulebook for the whole app).

Outturn  = desp date (dispatchDate) in the period - never physical despatch.
FND      = desp date filled, actual desp date (actualDispatchDate) empty.
Excluded = RETURN / COND(emned/emnded) / BHOPAL in status, remarks or repairDesc, or repair type 161.
           Excluded visits are never in holding, outturn, despatch or cycle time.
Holding  = received, no desp date, not excluded - one entry per coach (latest demand).
Not inside = data-entered in ERP (received date) but no pit and no status yet - coach still outside the
           workshop (JIJO 30-10-2026). Not in holding / yard; listed separately. Joins holding once a pit is entered.
Groups   = coach_groups.csv (edit that file; unknown types show as OTHERS).
           Repair type 4 = OR; 201 = ART CONVERSION / ARMV CONVERSION (type ARMVCONV); NMG 181/281/2 or /C = NMG CONVERSION.
AC locos are not handled anywhere.
"""
import csv
import os
from datetime import datetime, date

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUPS_CSV = os.path.join(APP_DIR, "coach_groups.csv")

HEAVY_HOURS = 500          # pre-survey / final hours >= 500 -> HEAVY (ICF and LHB alike)


# ---------------------------------------------------------------- dates
def pdate(v):
    """Parse ERP dates: 2026-09-10, 10/09/2026, 10.09.26, 2026-09-10T.. -> date or None."""
    if not v:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip().split("T")[0].split(" ")[0].replace(".", "/").replace("-", "/")
    a = s.split("/")
    if len(a) != 3:
        return None
    try:
        if len(a[0]) == 4:
            return date(int(a[0]), int(a[1]), int(a[2]))
        y = int(a[2])
        y = y + 2000 if y < 100 else y
        return date(y, int(a[1]), int(a[0]))
    except ValueError:
        return None


def fy_of(d):
    """Financial year label for a date: 2026-27."""
    if not d:
        return ""
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def fy_start(label):
    return date(int(label[:4]), 4, 1)


def fy_end(label):
    return date(int(label[:4]) + 1, 3, 31)


def month_start(d):
    return date(d.year, d.month, 1)


def fmt(d):
    return d.strftime("%d-%m-%Y") if d else ""


# ---------------------------------------------------------------- exclusions
def is_excluded(d):
    txt = " ".join(str(d.get(k) or "") for k in ("status", "remarks", "repairDesc")).upper()
    return any(x in txt for x in ("RETURN", "COND", "BHOPAL")) or str(d.get("repairType")) == "161"


# ---------------------------------------------------------------- coach groups
_groups_cache = {"mtime": None, "rows": []}


def _load_groups():
    try:
        mt = os.path.getmtime(GROUPS_CSV)
    except OSError:
        return []
    if _groups_cache["mtime"] != mt:
        with open(GROUPS_CSV, newline="", encoding="utf-8-sig") as f:
            rows = [r for r in csv.DictReader(f) if (r.get("erp_type") or "").strip()]
        for r in rows:
            r["erp_type"] = r["erp_type"].strip().upper()
            r["match"] = (r.get("match") or "exact").strip().lower()
            r["order"] = int(r.get("order") or 999)
        _groups_cache.update(mtime=mt, rows=rows)
    return _groups_cache["rows"]


def coach_type(d):
    return (d.get("_coachTypeDescription") or d.get("coachDesc") or d.get("coachType") or "").strip().upper()


def classify(d):
    """-> (family, group, order). Repair-type rules first, then coach_groups.csv (exact before prefix)."""
    t = coach_type(d)
    rep = str(d.get("repairType") or "").strip()
    if rep == "4":
        return "Special", "OR", 58
    if rep == "201":                                  # ART / ARMV conversion (repair type 201 = ART Conv)
        return ("Special", "ARMV CONVERSION", 54) if t.startswith("ARMV") else ("Special", "ART CONVERSION", 52.5)
    rows = _load_groups()
    hit = next((r for r in rows if r["match"] == "exact" and r["erp_type"] == t), None)
    if not hit:
        hit = next((r for r in sorted(rows, key=lambda r: -len(r["erp_type"]))
                    if r["match"] == "prefix" and t.startswith(r["erp_type"])), None)
    if not hit:
        return "Others", "OTHERS", 999
    fam, grp, order = hit["family"], hit["group"], hit["order"]
    if grp == "NMG POH" and (rep in ("181", "281", "2") or t.endswith("/C")):
        return fam, "NMG CONVERSION", order + 1
    return fam, grp, order


FAMILY_ORDER = ["ICF", "LHB", "DEMU Shop", "TC family", "Vande Bharat", "Special", "Others"]


# ---------------------------------------------------------------- holding / FND
def coach_key(d):
    return str(d.get("coachNo") or "").strip().replace(" ", "").lstrip("0")


def latest_per_coach(demands):
    best = {}
    for d in demands:
        k = coach_key(d)
        if not k:
            continue
        key = (pdate(d.get("receivedDate")) or date.min, int(d.get("demandId") or 0))
        if k not in best or key > best[k][0]:
            best[k] = (key, d)
    return {k: v[1] for k, v in best.items()}


def not_yet_inside(d):
    """Data-entered in ERP but not taken inside yet (JIJO 30-10-2026): received date filled,
    no desp date, not excluded, but no pit AND no status. The coach is still outside the workshop.
    It joins holding as soon as a pit (OT/YD, OT/IN or a shop pit) is entered in ERP."""
    return (bool(d.get("receivedDate")) and not d.get("dispatchDate") and not is_excluded(d)
            and not str(d.get("pitNum") or "").strip() and not str(d.get("status") or "").strip())


def in_holding(d):
    return (bool(d.get("receivedDate")) and not d.get("dispatchDate") and not is_excluded(d)
            and not not_yet_inside(d))


def is_fnd(d):
    return bool(pdate(d.get("dispatchDate"))) and not d.get("actualDispatchDate") and not is_excluded(d)


YARD_PITS = ("OT/YD", "OT/IN", "TS_", "YARD")


def location(d):
    pit = str(d.get("pitNum") or "").upper().strip()
    if not pit or pit.startswith(YARD_PITS) or str(d.get("stageId")) == "1001":
        return "Yard"
    return "Work area"


def hours(d, field):
    try:
        v = float(d.get(field))
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def light_heavy(d):
    h = hours(d, "preSurveyHrs")
    if h is None:
        return ""
    return "HEAVY" if h >= HEAVY_HOURS else "LIGHT"
