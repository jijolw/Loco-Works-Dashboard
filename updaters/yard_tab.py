"""
updaters/yard_tab.py - tab "Shop Out - Yard" in the Workshop Coach Production Plan sheet (JIJO 11-11-2026).

Coaches the shop has finished and sent out (SHOP OUT = ERP actual despatch date) but which are still physically in the
yard - waiting for rubber, cleaning, VG, Kumbh Mela etc. - until HQ OUT TURN marks them DESP (core/physical.py).
They are no longer the shop's FND (FND tab) and not yet gone.
 - rows from ERP + HQ OUT TURN every Update_All run; a coach drops off when HQ OUT TURN marks it DESP;
 - Reason (drop-down: Rubber / Cleaning / VG / Kumbh Mela / Other - free typing allowed) and Remarks are typed by
   staff and KEPT per coach;
 - Days in Yard = TODAY() - Shop Out.
Columns: A Sl | B Coach No | C Coach Group | D Type | E Division | F Outturned On | G Shop Out | H Days in Yard |
         I HQ Status | J Reason | K Remarks
"""
from core import rules as R
from core import physical as P
from core import sheet_dates as SD
from updaters.despatched_tab import plan_group

SHEET_KEY = "1DWi99uWW0ReyblrXnT0MEBqzOPwYvhLCB9v9lWON0QQ"   # Workshop Coach Production Plan
TAB = "Shop Out - Yard"
HEAD = ["Sl. No", "Coach No", "Coach Group", "Type", "Division", "Outturned On", "Shop Out", "Days in Yard",
        "HQ Status", "Reason", "Remarks"]
NCOL = len(HEAD)                        # A..K
FIRST = 3
LAST = 200
REASONS = ["Rubber", "Cleaning", "VG", "Kumbh Mela", "Other"]


def yard_coaches(D):
    out = [d for d in R.latest_per_coach(D).values() if P.in_yard(d)]
    return sorted(out, key=lambda d: (R.pdate(P.shop_out(d)), str(d.get("coachNo"))))


def build(D, current):
    keep = {}
    for r in current[FIRST - 1:]:
        r = list(r) + [""] * NCOL
        k = R.coach_key({"coachNo": str(r[1]).strip().lstrip("'")})
        if k:
            keep[k] = r
    rows = []
    for i, d in enumerate(yard_coaches(D), 1):
        old = keep.get(R.coach_key(d), [""] * NCOL)
        reason = old[9] or ("Kumbh Mela" if d.get("_hqStatus") == "RFD" else "")
        rows.append([i, str(d.get("coachNo")).strip(), plan_group(d) or R.coach_type(d), R.coach_type(d),
                     d.get("divisionId") or old[4], SD.serial(R.pdate(d.get("dispatchDate"))),
                     SD.serial(R.pdate(P.shop_out(d))), "", d.get("_hqStatus") or "", reason, old[10]])
    return rows


def preview_lines(rows, current):
    before = {str(r[1]).strip().lstrip("'") for r in current[FIRST - 1:] if len(r) > 1 and str(r[1]).strip()}
    after = {str(r[1]) for r in rows}
    add, gone = sorted(after - before), sorted(before - after)
    return [f"    Shop Out - Yard tab: {len(rows)} coaches (shop out, not yet physically despatched)"
            + (f" | new: {', '.join(add)}" if add else "")
            + (f" | dropped (physically despatched): {', '.join(gone)}" if gone else "")]


def read_current(sh):
    titles = {w.title: w for w in sh.worksheets()}
    return titles[TAB].get_values(f"A1:K{LAST}") if TAB in titles else []


def apply(sh, rows, log):
    titles = {w.title: w for w in sh.worksheets()}
    ws = titles.get(TAB) or sh.add_worksheet(title=TAB, rows=LAST, cols=NCOL)
    sid = ws.id
    ws.batch_clear([f"A{FIRST}:K{LAST}"])
    ws.update(range_name="A1:K2", values=[["SHOP OUT - WAITING IN YARD (not yet physically despatched)"] + [""] * (NCOL - 1),
                                          HEAD], value_input_option="USER_ENTERED")
    if rows:
        ws.update(range_name=f"A{FIRST}:K{FIRST + len(rows) - 1}", values=rows, value_input_option="RAW")
        ws.update(range_name=f"H{FIRST}:H{FIRST + len(rows) - 1}",
                  values=[[f'=IF(G{n}="","",TODAY()-G{n})'] for n in range(FIRST, FIRST + len(rows))],
                  value_input_option="USER_ENTERED")
    end = min(LAST, ws.row_count)
    rng = lambda c0, c1, r0=FIRST - 1, r1=end: {"sheetId": sid, "startRowIndex": r0, "endRowIndex": r1,  # noqa: E731
                                                "startColumnIndex": c0, "endColumnIndex": c1}
    sh.batch_update({"requests": [
        {"repeatCell": {"range": rng(5, 7), "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": SD.PATTERN}}},
                        "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {"range": rng(7, 8), "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "0"}}},
                        "fields": "userEnteredFormat.numberFormat"}},
        {"setDataValidation": {"range": rng(9, 10), "rule": {"condition": {"type": "ONE_OF_LIST",
            "values": [{"userEnteredValue": x} for x in REASONS]}, "strict": False, "showCustomUi": True}}},
        {"repeatCell": {"range": rng(0, NCOL, 0, 2), "cell": {"userEnteredFormat": {"textFormat": {"bold": True}, "wrapStrategy": "WRAP"}},
                        "fields": "userEnteredFormat.textFormat.bold,userEnteredFormat.wrapStrategy"}},
        {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 2}},
                                   "fields": "gridProperties.frozenRowCount"}},
    ]})
    back = ws.get_values(f"B{FIRST}:B{FIRST + len(rows) + 5}")
    got = [str(r[0]).lstrip("'") for r in back if r and str(r[0]).strip()]
    if got != [str(r[1]) for r in rows]:
        raise RuntimeError("Shop Out - Yard tab read-back differs - check the tab")
    log(f"  Production Plan 'Shop Out - Yard' tab - {len(rows)} coaches - verified")
