"""
core/daily_inputs.py - figures typed for the Daily Position report (things the coach ERP does not have)
and the working-day count. Saved on the office PC in data/daily_report.json; the form keeps the last values.

Working days (JIJO 31-10-2026): Sunday = holiday, Saturday = half day, Monday-Friday = 1 day, minus the holidays
JIJO ticks / types in the form. Checked against the old report: Oct-26 23.5 total, 23 completed on 30-10;
2026-27 271 total, 163 completed on 30-10 (needs all 16 holidays of the year entered).
"""
import copy
import json
import os
from datetime import date, datetime, timedelta

import config
from core import rules as R

FILE = os.path.join(config.APP_DIR, "data", "daily_report.json")

AC_LINES = ["Pit 10", "Pit 9", "Line 8", "Line 7", "Line 6", "Line 5", "Line 4", "Line 3", "Line 2", "Line 1"]

DEFAULT = {
    "holidays": [{"date": "2026-10-02", "name": "Gandhi Jayanthi"}],
    "saturday_half": True,
    "override": {"month_completed": "", "month_total": "", "year_completed": "", "year_total": ""},
    # page-2 targets: rb = text shown, basis = number for the proportionate target, hq = monthly HQ target
    "targets": {
        "ICF": {"rb": "300", "basis": "300", "hq": "28"},
        "NMG": {"rb": "-", "basis": "", "hq": "1"},
        "ARTC": {"rb": "-", "basis": "", "hq": "2"},
        "LHBN": {"rb": "60 (HQ-120)", "basis": "120", "hq": "10"},
        "LHBA": {"rb": "36 (HQ-48)", "basis": "48", "hq": "5"},
        "EMUONLY": {"rb": "", "basis": "", "hq": "0"},
        "EMU": {"rb": "88", "basis": "88", "hq": "8"},
        "DEMU": {"rb": "54", "basis": "54", "hq": "4"},
        "SPART": {"rb": "2", "basis": "2", "hq": "0"},
        "TW4": {"rb": "3", "basis": "3", "hq": "0"},
        "TW8": {"rb": "12", "basis": "12", "hq": "0"},
        "OR": {"rb": "-", "basis": "", "hq": "1"},
    },
    "rb_total_text": "555+ (HQ-72)",
    "typed": [
        {"label": "Ac Loco", "rb": "60", "prop": "36.09", "sep": "30", "todate": "33", "hq": "05", "mprop": "4.89", "mon": "4", "day": "0", "hold": "7"},
        {"label": "IOH of ICF bogies", "rb": "-", "prop": "-", "sep": "66", "todate": "66", "hq": "0", "mprop": "0", "mon": "0", "day": "0", "hold": "-"},
        {"label": "SS1 of bogies - LHB", "rb": "840", "prop": "505.24", "sep": "374", "todate": "435", "hq": "74", "mprop": "72.43", "mon": "61", "day": "2", "hold": "8+0 RFD"},
        {"label": "SS1 of bogies - VB SS1", "rb": "96", "prop": "57.74", "sep": "61", "todate": "66", "hq": "28", "mprop": "27.4", "mon": "5", "day": "0", "hold": "SS1-5+0 RFD"},
        {"label": "SS1 of bogies - VB SS2", "rb": "80", "prop": "48.12", "sep": "52", "todate": "70", "hq": "", "mprop": "0", "mon": "18", "day": "0", "hold": "SS2-12+0 RFD"},
    ],
    "nmghs": {"label": "Balance Target 2025-26", "balance": "33", "actual": "24", "to_achieve": "9"},
    "ac_bay": [
        {"line": "Pit 10", "type": "WAG7", "loco": "27435", "repair": "POH", "shed": "ED", "date": ""},
        {"line": "Pit 9"},
        {"line": "Line 8", "type": "WAP7", "loco": "30680", "repair": "POH", "shed": "RPM", "date": "2026-10-05"},
        {"line": "Line 7", "type": "WAP7", "loco": "30644", "repair": "POH", "shed": "ED", "date": "2026-10-26"},
        {"line": "Line 6"},
        {"line": "Line 5", "type": "WAG7", "loco": "27537", "repair": "POH", "shed": "RPDX", "date": "2026-10-17"},
        {"line": "Line 4", "type": "WAG7", "loco": "27393", "repair": "POH", "shed": "ED", "date": "2026-09-25"},
        {"line": "Line 3", "type": "WAG7", "loco": "27387", "repair": "POH", "shed": "KZJ", "date": "2026-10-07"},
        {"line": "Line 2"}, {"line": "Line 1"},
    ],
    "plan": [
        {"coach": "GS 096409", "corr_pdc": "2026-10-28", "desp_pdc": "2026-10-28"},
        {"coach": "LWACCN 232950", "corr_pdc": "2026-10-22", "desp_pdc": "2026-10-28"},
        {"coach": "LWS 195541", "corr_pdc": "2026-10-23", "desp_pdc": "2026-10-28"},
        {"coach": "TC 128169", "corr_pdc": "", "desp_pdc": "2026-10-28"},
        {"coach": "CN 136233", "corr_pdc": "2026-10-27", "desp_pdc": "2026-10-29"},
        {"coach": "LWSCN 176230", "corr_pdc": "2026-10-21", "desp_pdc": "2026-10-29"},
        {"coach": "GS 116416", "corr_pdc": "2026-10-24", "desp_pdc": "2026-10-30"},
        {"coach": "LWSCN 186251", "corr_pdc": "2026-10-24", "desp_pdc": "2026-10-30"},
        {"coach": "TC 128167", "corr_pdc": "", "desp_pdc": "2026-10-30"},
        {"coach": "TC 128168", "corr_pdc": "", "desp_pdc": "2026-10-31"},
    ],
    "notes": "EIR -22 Inside loco work at 01/06/2025",
    "saved_at": "",
}

TARGET_ROWS = [("ICF", "ICF NAC Coach POH"), ("NMG", "ICF - NMG POH/Conv"), ("ARTC", "ARMV/Conv"),
               ("LHBN", "LHB NAC POH"), ("LHBA", "LHB AC POH"), ("EMUONLY", "EMU (HQ target only)"),
               ("EMU", "EMU + MEMU (RB) / MEMU (HQ)"), ("DEMU", "DEMU DPC/TC"), ("SPART", "SPART/Spic"),
               ("TW4", "TW -4W"), ("TW8", "TW -8W"), ("OR", "OR")]
TYPED_FIELDS = [("label", "Activity"), ("rb", "Yearly target"), ("prop", "Prop till date"), ("sep", "Cum. upto last month"),
                ("todate", "Till date"), ("hq", "Monthly HQ target"), ("mprop", "Prop till date (month)"),
                ("mon", "Month till date"), ("day", "Last working day"), ("hold", "Holding")]


def load():
    try:
        with open(FILE, encoding="utf-8") as f:
            saved = json.load(f)
    except Exception:
        saved = {}
    out = copy.deepcopy(DEFAULT)
    out.update({k: v for k, v in saved.items() if k in DEFAULT})
    for k, v in DEFAULT["targets"].items():
        out["targets"].setdefault(k, dict(v))
    return out


def save(d):
    d = dict(d, saved_at=datetime.now().strftime("%d-%m-%Y %H:%M"))
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    if os.path.exists(FILE):                              # keep the previous version
        try:
            os.replace(FILE, FILE + ".bak")
        except OSError:
            pass
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    return d


def from_form(form, current, staff=False):
    """Build the inputs dict from the posted form (missing parts keep their current values).
    staff=True (staff Daily Report app): only the daily items change - holidays, override and targets stay as they are."""
    d = copy.deepcopy(current)
    if staff:
        return _daily_items(form, d)
    hol = []
    for ds, nm in zip(form.getlist("hol_date"), form.getlist("hol_name")):
        if ds.strip():
            hol.append({"date": ds.strip(), "name": nm.strip()})
    d["holidays"] = sorted(hol, key=lambda h: h["date"])
    d["saturday_half"] = form.get("saturday_half") == "1"
    d["override"] = {k: form.get("ov_" + k, "").strip() for k in DEFAULT["override"]}
    for key, _ in TARGET_ROWS:
        d["targets"][key] = {f: form.get(f"t_{key}_{f}", "").strip() for f in ("rb", "basis", "hq")}
    d["rb_total_text"] = form.get("rb_total_text", "").strip()
    return _daily_items(form, d)


def _daily_items(form, d):
    """Typed rows, NMGHS, AC loco bay, weekly plan and notes."""
    typed = []
    for i in range(int(form.get("typed_n", 0) or 0)):
        r = {k: form.get(f"ty_{i}_{k}", "").strip() for k, _ in TYPED_FIELDS}
        if r["label"]:
            typed.append(r)
    d["typed"] = typed
    d["nmghs"] = {k: form.get("nm_" + k, "").strip() for k in ("label", "balance", "actual", "to_achieve")}
    d["ac_bay"] = [{"line": ln, **{k: form.get(f"ac_{i}_{k}", "").strip() for k in ("type", "loco", "repair", "shed", "date")}}
                   for i, ln in enumerate(AC_LINES)]
    plan = []
    for i in range(int(form.get("plan_n", 0) or 0)):
        c = form.get(f"pl_{i}_coach", "").strip().upper()
        if c:
            plan.append({"coach": c, "corr_pdc": form.get(f"pl_{i}_corr", "").strip(),
                         "desp_pdc": form.get(f"pl_{i}_desp", "").strip()})
    d["plan"] = plan
    d["notes"] = form.get("notes", "").strip()
    return d


# ---------------------------------------------------------------- working days
def day_value(d, holidays, saturday_half=True):
    if d.weekday() == 6 or d.isoformat() in holidays:
        return 0.0
    if d.weekday() == 5:
        return 0.5 if saturday_half else 1.0
    return 1.0


def _sum(a, b, holidays, sat):
    t, d = 0.0, a
    while d <= b:
        t += day_value(d, holidays, sat)
        d += timedelta(days=1)
    return t


def working_days(as_on, inp):
    """Completed = up to and including as_on (the report's 'end of day')."""
    hol = {h["date"] for h in inp.get("holidays", [])}
    sat = inp.get("saturday_half", True)
    m0 = date(as_on.year, as_on.month, 1)
    m1 = date(as_on.year + (as_on.month == 12), as_on.month % 12 + 1, 1) - timedelta(days=1)
    y0 = R.fy_start(R.fy_of(as_on))
    y1 = R.fy_end(R.fy_of(as_on))
    wd = dict(month_completed=_sum(m0, as_on, hol, sat), month_total=_sum(m0, m1, hol, sat),
              year_completed=_sum(y0, as_on, hol, sat), year_total=_sum(y0, y1, hol, sat))
    wd["auto"] = dict(wd)
    for k, v in (inp.get("override") or {}).items():
        try:
            if str(v).strip():
                wd[k] = float(v)
        except ValueError:
            pass
    wd["holidays_in_year"] = sum(1 for h in hol if y0.isoformat() <= h <= y1.isoformat())
    return wd
