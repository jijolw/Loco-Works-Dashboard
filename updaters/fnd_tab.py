"""
updaters/fnd_tab.py - tab "FND" in the Workshop Coach Production Plan sheet (JIJO 04-11-2026).

FND coaches = outturned in ERP (desp date) but not yet physically despatched (no actual desp date), ANY month.
Corrosion is done, so only the remaining sections are tracked. Refreshed by Update_All every day:
 - rows come from ERP (coach, type, division, outturned on, days since outturn, despatch PDC);
 - what the shop typed is KEPT per coach: Revised PDC, the section columns and Remarks;
 - a coach physically despatched drops off; a new FND coach is added with the sections blank.
Revised PDC and section cells are FREE typing (JIJO 04-11: no drop-downs) - the shop types a date or "Completed";
they are date-formatted so a typed date shows dd/mm/yyyy, and new rows start blank.
"""
from datetime import datetime

from core import rules as R

SHEET_KEY = "1DWi99uWW0ReyblrXnT0MEBqzOPwYvhLCB9v9lWON0QQ"   # Workshop Coach Production Plan
TAB = "FND"
SECTIONS = ["Water Service", "Air Brake", "Train Lighting", "Trimming", "Carpentry", "Painting / Lettering",
            "Bio-toilet", "Final Inspection"]
HEAD = ["Sl. No", "Coach No", "Type", "Division", "Outturned On", "Days FND", "Despatch PDC (ERP)",
        "Revised Despatch PDC"] + SECTIONS + ["Remarks"]
NCOL = len(HEAD)                      # A..Q
FIRST = 3                             # row 1 title, row 2 headers


def fnd_coaches(D):
    latest = R.latest_per_coach(D)
    out = [d for d in latest.values()
           if R.pdate(d.get("dispatchDate")) and not R.pdate(d.get("actualDispatchDate")) and not R.is_excluded(d)]
    return sorted(out, key=lambda d: (R.pdate(d.get("dispatchDate")), d.get("_order", 0)))


def build(D, current):
    """current = rows read from the tab (A1:Q...) -> list of value rows for A3.. ."""
    keep = {}
    for r in current[FIRST - 1:]:
        r = list(r) + [""] * NCOL
        k = R.coach_key({"coachNo": str(r[1]).strip().lstrip("'").split(".")[0]})
        if k:
            keep[k] = r
    rows = []
    for i, d in enumerate(fnd_coaches(D), 1):
        old = keep.get(R.coach_key(d))
        typed = old[7:NCOL] if old else [""] * (NCOL - 7)
        out = R.pdate(d.get("dispatchDate"))
        pdc = R.pdate(d.get("pdcDate"))
        n = FIRST + i - 1
        rows.append([i, "'" + str(d.get("coachNo")), R.coach_type(d), d.get("divisionId") or (old[3] if old else ""),
                     out.isoformat() if out else "", f"=IF(E{n}=\"\",\"\",TODAY()-E{n})",
                     pdc.isoformat() if pdc else ""] + list(typed))
    return rows


def preview_lines(rows, current):
    before = {str(r[1]).strip().lstrip("'") for r in current[FIRST - 1:] if len(r) > 1 and str(r[1]).strip()}
    after = {r[1].lstrip("'") for r in rows}
    add, gone = sorted(after - before), sorted(before - after)
    return [f"    FND tab: {len(rows)} coaches" + (f" | new: {', '.join(add)}" if add else "")
            + (f" | dropped (physically despatched): {', '.join(gone)}" if gone else "")]


def read_current(sh):
    titles = {w.title: w for w in sh.worksheets()}
    # unformatted: a typed Revised PDC comes back as a date serial number and is written back unchanged
    # (a "05/11/2026" text could be re-read as 11 May in a US-locale sheet)
    return titles[TAB].get_values("A1:Q400", value_render_option="UNFORMATTED_VALUE") if TAB in titles else []


def _col(n):
    return chr(ord("A") + n - 1)


def apply(sh, rows, log):
    titles = {w.title: w for w in sh.worksheets()}
    ws = titles.get(TAB) or sh.add_worksheet(title=TAB, rows=400, cols=NCOL)
    title = f"FND COACHES - PENDING WORK (from ERP, updated {datetime.now():%d-%m-%Y %H:%M})"
    ws.batch_clear([f"A{FIRST}:{_col(NCOL)}400"])
    ws.update(range_name=f"A1:{_col(NCOL)}2", values=[[title] + [""] * (NCOL - 1), HEAD], value_input_option="USER_ENTERED")
    if rows:
        ws.update(range_name=f"A{FIRST}:{_col(NCOL)}{FIRST + len(rows) - 1}", values=rows, value_input_option="USER_ENTERED")
    sid = ws.id
    rng = lambda c0, c1: {"sheetId": sid, "startRowIndex": FIRST - 1, "endRowIndex": 400, "startColumnIndex": c0, "endColumnIndex": c1}
    req = [
        {"setDataValidation": {"range": rng(7, 8 + len(SECTIONS))}},          # no drop-down / picker rule
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": FIRST - 1, "endRowIndex": 400, "startColumnIndex": 4,
                                  "endColumnIndex": 8 + len(SECTIONS)},
                        "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "dd/mm/yyyy"}}},
                        "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": FIRST - 1, "endRowIndex": 400, "startColumnIndex": 5,
                                  "endColumnIndex": 6},
                        "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "0"}}},
                        "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 2, "startColumnIndex": 0,
                                  "endColumnIndex": NCOL},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}, "wrapStrategy": "WRAP"}},
                        "fields": "userEnteredFormat.textFormat.bold,userEnteredFormat.wrapStrategy"}},
        {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 2}},
                                   "fields": "gridProperties.frozenRowCount"}},
    ]
    sh.batch_update({"requests": req})
    back = ws.get_values(f"B{FIRST}:B{FIRST + len(rows) + 5}")
    got = [str(r[0]).lstrip("'") for r in back if r and str(r[0]).strip()]
    want = [r[1].lstrip("'") for r in rows]
    if got != want:
        raise RuntimeError(f"FND tab read-back differs ({len(got)} vs {len(want)}) - check the tab")
    log(f"  Production Plan FND tab - {len(rows)} coaches - verified")
