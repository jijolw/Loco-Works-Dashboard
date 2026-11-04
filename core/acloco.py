"""
core/acloco.py - AC Loco Bay for the Daily Position report, READ ONLY from the new Carriage ERP (Claude for JIJO, 04-11-2026).

The ERP's own Aerial View screen reads:
    {ERP_API}/locos/aerial-view/ac-loco-aerial-codes   -> the 10 lines (Pit 10 ... Line 1)
    {ERP_API}/locos/aerial-view/ac-locos               -> loco on each line (locoNo, locoDescription, receivedDate, tfrDate)
    {ERP_API}/locos/aerial-view/unassigned-ac-locos    -> locos in the shop not placed on a line
Shed / repair come from {ERP_API}/acloco/masters/loco-receipts when that list can be read (else blank).
Saved in data/ac_bay.json at every ERP export; the report uses it, the typed AC bay is only the fallback.
AC locos stay out of every coach figure - this is only the AC Loco Bay box of the Daily Position report.
"""
import json
import os
from datetime import datetime

import config
from core import rules as R

FILE = os.path.join(config.APP_DIR, "data", "ac_bay.json")


def _nice(label):
    return " ".join(str(label or "").split())                 # "Pit  10" -> "Pit 10"


def _date(v):
    d = R.pdate(v)
    return d.isoformat() if d else ""


def _pick(rec, *words):
    for k, v in rec.items():
        lk = k.lower()
        if any(w in lk for w in words) and v not in (None, ""):
            return str(v).strip()
    return ""


def fetch(sess):
    api = config.ERP_API.rstrip("/")

    def get(path):
        r = sess.get(api + path, timeout=30)
        r.raise_for_status()
        j = r.json()
        return j.get("data", j) if isinstance(j, dict) else j

    codes = get("/locos/aerial-view/ac-loco-aerial-codes")
    on_line = {c.get("aerialCode"): c for c in get("/locos/aerial-view/ac-locos") if c.get("locoNo")}
    try:
        unassigned = [c for c in get("/locos/aerial-view/unassigned-ac-locos") if c.get("locoNo")]
    except Exception:
        unassigned = []
    extra = {}
    try:                                                       # shed / repair, if this list is readable
        for rec in get("/acloco/masters/loco-receipts"):
            if isinstance(rec, dict) and rec.get("demandId") is not None:
                extra[str(rec["demandId"])] = dict(shed=_pick(rec, "shed"), repair=_pick(rec, "repair", "nature"))
    except Exception:
        pass

    def item(c, line):
        x = extra.get(str(c.get("demandId")), {})
        return dict(line=line, type=c.get("locoDescription") or "", loco=str(c.get("locoNo") or ""),
                    repair=x.get("repair") or "POH", shed=x.get("shed") or "",
                    date=_date(c.get("receivedDate")), tfr=_date(c.get("tfrDate")), demand=c.get("demandId"))

    bay = []
    for c in codes:
        line = _nice(c.get("label"))
        loc = on_line.get(c.get("aerialCode"))
        bay.append(item(loc, line) if loc else {"line": line})
    # locos received in the last 2 years but not placed on a line (old empty demands left out)
    cut = datetime.now().date().replace(year=datetime.now().year - 2)
    others = [item(c, "") for c in unassigned if (R.pdate(c.get("receivedDate")) or cut) > cut]
    out = dict(read_at=datetime.now().strftime("%Y-%m-%d %H:%M"), bay=bay, others=others)
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    return out


def load():
    try:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
