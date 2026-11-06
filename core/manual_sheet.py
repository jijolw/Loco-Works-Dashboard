"""
core/manual_sheet.py - the Daily Position items that are NOT in ERP, typed by the staff in the Google sheet
"Daily Position - Manual Entries (LW-PER)" (JIJO 06-11-2026). READ only, through the service account.

Tab Daily_Entry (static cells, overwritten every day - nothing is calculated, the report copies them):
    WORKING DAYS   Completed | Total      rows "This month", "This year"
    Item | Today | Month till date | Year till date | Holding      (Ac Loco, bogies ...)
    NMGHS CONV.    label | Balance target | Actual till date | Balance to achieve
    NOTES          one note per line under the NOTES heading
Tab Targets (history kept): Effective from | Activity | Yearly RB target (as shown) | RB number for prop. | Monthly HQ target
    -> the latest row on or before the position date is used, separately for RB and HQ.

apply(inp, as_on) puts these into the daily-report inputs; when the sheet cannot be read the saved copy
data/manual_sheet.json is used, and when there is none either the app's own typed figures stay.
"""
import json
import os
from datetime import date, datetime

import config

SHEET_KEY = config.get("MANUAL_SHEET_KEY", "1mDyl0ZJ4AqtC_sY8Vsldg0RsdBIvbpl1a12wRUG6Sa4")
FILE = os.path.join(config.APP_DIR, "data", "manual_sheet.json")


def _cell(r, i):
    return str(r[i]).strip() if len(r) > i and r[i] is not None else ""


def _num(v):
    try:
        f = float(str(v).replace(",", ""))
        return int(f) if f == int(f) else f
    except (TypeError, ValueError):
        return None


def _date(v):
    s = str(v).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def parse(entry, targets):
    """entry / targets = all values of the two tabs -> dict saved in data/manual_sheet.json."""
    out = {"updated_on": "", "wd": {}, "items": {}, "nmghs": None, "notes": [], "targets": []}
    section = None
    for r in entry:
        a = _cell(r, 0)
        al = a.lower()
        if al.startswith("updated on"):
            out["updated_on"] = _cell(r, 1)
        elif al.startswith("working days"):
            section = "wd"
        elif al == "item":
            section = "items"
        elif al.startswith("nmghs"):
            section = "nmghs"
        elif al.startswith("notes"):
            section = "notes"
        elif not a:
            if section in ("wd", "items", "nmghs"):
                section = None
        elif section == "wd" and al in ("this month", "this year"):
            k = "month" if al == "this month" else "year"
            out["wd"][k + "_completed"], out["wd"][k + "_total"] = _cell(r, 1), _cell(r, 2)
        elif section == "items":
            out["items"][a] = dict(day=_cell(r, 1), mon=_cell(r, 2), todate=_cell(r, 3), hold=_cell(r, 4))
        elif section == "nmghs" and out["nmghs"] is None:
            out["nmghs"] = dict(label=a, balance=_cell(r, 1), actual=_cell(r, 2), to_achieve=_cell(r, 3))
        if section == "notes" and a and not al.startswith("notes"):
            out["notes"].append(a)
    for r in targets[1:]:
        d = _date(_cell(r, 0))
        if d and _cell(r, 1):
            out["targets"].append(dict(frm=d.isoformat(), act=_cell(r, 1), rb=_cell(r, 2), basis=_cell(r, 3), hq=_cell(r, 4)))
    return out


def refresh():
    from updaters.common import open_sheet
    sh = open_sheet(SHEET_KEY)
    m = parse(sh.worksheet("Daily_Entry").get_values("A1:E60"), sh.worksheet("Targets").get_values("A1:F500"))
    m["read_at"] = datetime.now().strftime("%d-%m-%Y %H:%M")
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=1)
    return m


def load(live=True):
    """-> (data or None, error)."""
    err = None
    if live:
        try:
            return refresh(), None
        except Exception as e:
            err = f"Manual-entry sheet not read ({e}) - using the saved copy."
    try:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f), err
    except Exception:
        return None, err or "Manual-entry sheet not read and no saved copy."


def current_targets(m, as_on):
    """{activity: {"rb": text, "basis": number, "hq": number}} - latest row on/before as_on, RB and HQ separately."""
    rows = sorted((t for t in m.get("targets", []) if date.fromisoformat(t["frm"]) <= as_on), key=lambda t: t["frm"])
    out = {}
    for t in rows:
        o = out.setdefault(t["act"], {})
        if t["rb"] or t["basis"]:
            o["rb"], o["basis"] = t["rb"], t["basis"]
        if t["hq"] != "":
            o["hq"] = t["hq"]
    return out


def apply(inp, as_on, m):
    """Put the sheet values into the daily-report inputs (in memory only - the app's saved file is not changed)."""
    if not m:
        return inp
    from core import daily_inputs as DI
    wd = m.get("wd") or {}
    if (_num(wd.get("month_total")) or 0) > 31:        # a year figure typed in the month box - use the calendar
        wd = dict(wd, month_total="")
    if any(wd.values()):
        inp["override"] = dict(inp.get("override") or {}, for_date=as_on.isoformat(), month=f"{as_on:%Y-%m}",
                               fy=f"{as_on.year if as_on.month > 3 else as_on.year - 1}-{(as_on.year + (1 if as_on.month > 3 else 0)) % 100:02d}",
                               **{k: wd.get(k, "") for k in ("month_completed", "month_total", "year_completed", "year_total")})
    tg = current_targets(m, as_on)
    for key, label in DI.TARGET_ROWS:
        if label in tg:
            t = inp.setdefault("targets", {}).setdefault(key, {})
            t.update({k: tg[label][k] for k in ("rb", "basis", "hq") if k in tg[label]})
    typed = inp.setdefault("typed", [])
    have = {r.get("label") for r in typed}
    for label in m.get("items", {}):
        if label not in have:
            typed.append({"label": label})
    for r in typed:
        it = m.get("items", {}).get(r.get("label"))
        if not it:
            continue
        for k in ("base_date", "base_mon", "base_year", "daily"):    # static figures from the sheet, no formula
            r.pop(k, None)
        mon, yr = _num(it["mon"]) or 0, _num(it["todate"]) or 0
        r.update(day=it["day"], mon=it["mon"], todate=it["todate"], sep=str(yr - mon), hold=it["hold"])
        t = tg.get(r.get("label"), {})
        if "rb" in t:
            r["rb"] = t["rb"]
        if "hq" in t:
            r["hq"] = t["hq"]
    if m.get("nmghs"):
        inp["nmghs"] = m["nmghs"]
    if m.get("notes") is not None and (m.get("notes") or m.get("read_at")):
        inp["notes"] = "\n".join(m["notes"])
    return inp
