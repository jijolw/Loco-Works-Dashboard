"""
updaters/despatched_tab.py - tab "Despatched" in the Workshop Coach Production Plan sheet (JIJO 07-11-2026).

Despatched tab = coaches SHOP OUT (ERP actual despatch date - the shop's despatch, JIJO 11-11-2026) in the CURRENT
month, with column K 'Physical Despatch' = HQ OUT TURN physical date, or 'In yard (RFD/FND)' while it waits. Including
previous-month FND coaches despatched this month. Refreshed by Update_All (step 3g), after the FND tab:
 - a coach that drops off the FND tab because it went out is added here;
 - rows already in the tab (typed by staff or added earlier) are KEPT as they are - only blank cells are filled
   from ERP; a typed coach that ERP does not show is never removed;
 - new month: the old month's rows are first copied to a tab "Despatched <Mon YYYY>", then the tab starts fresh;
 - coaches with no plan tab (tower wagons etc.) are left out and listed in the preview (same as the plan tabs).
Dates are real dates shown dd/mm/yy (11-11-2026; before: text dd.mm.yy); data rows are written RAW so
coach numbers keep leading zeros and dates are not re-read as US dates.
"""
from datetime import date, datetime

from core import rules as R
from core import physical as P
from core import sheet_dates as SD          # dates as real dates dd/mm/yy (JIJO 11-11-2026)

SHEET_KEY = "1DWi99uWW0ReyblrXnT0MEBqzOPwYvhLCB9v9lWON0QQ"   # Workshop Coach Production Plan
TAB = "Despatched"
HEAD = ["Sl. No", "Coach No", "Coach Group", "Type", "Division", "Corrosion Completed On", "Despatch PDC",
        "Outturn Date", "Despatched On", "Remarks", "Physical Despatch"]
NCOL = len(HEAD)                     # A..K (K added 11-11-2026)
FIRST = 3                            # row 1 title, row 2 headers
LAST = 150
MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER",
          "NOVEMBER", "DECEMBER"]
AC_GROUPS = ("LWACCN", "LWACCW", "LWCBAC (Pantry)")


def plan_group(d):
    """Plan tab name for a coach (same tabs as the Production Plan); None = not in the plan."""
    fam, grp, _ = R.classify(d)
    t = R.coach_type(d)
    if grp == "OR":                                   # OR coach goes with its coach type
        if t.startswith(("LW", "LS")):
            return "LHB AC" if any(k in t for k in ("ACC", "CBAC")) else "LHB NAC"
        return "ICF" if t[:2] in ("GS", "CN", "CZ", "SL") else None
    if fam == "ICF":
        return "ICF"
    if fam == "LHB":
        return "LHB AC" if grp in AC_GROUPS else "LHB NAC"
    if grp in ("DEMU TC", "DEMU DPC"):
        return "DEMU TC"
    if grp in ("MEMU TC", "EMU TC", "MEMU MC", "EMU MC"):
        return "EMU MEMU TC"
    if grp.startswith(("ART", "ARMV", "ARME")):
        return "ART"
    if grp.startswith("NMG"):
        return "NMG"
    return None


def _d(v):
    """ERP date -> sheet serial number (written RAW, shown dd/mm/yy by the column format) - JIJO 11-11-2026
    (was text dd.mm.yy)."""
    return SD.serial(R.pdate(v))


def _parse(s):
    return SD.to_date(s)


def _txt(v):
    x = SD.to_date(v)
    return x.strftime("%d/%m/%y") if x else str(v)


def _phys(d):
    """K: HQ physical despatch date, or 'In yard (RFD)' while the coach waits after shop out."""
    if P.in_yard(d):
        return f"In yard ({d.get('_hqStatus') or 'FND'})"
    return _d(d.get("actualDispatchDate"))


def _fnd_remark(d, as_on):
    """Previous-month FND despatched this month -> 'FND of Oct' (outturn counted in that month, not this one)."""
    out = R.pdate(d.get("dispatchDate"))
    if out and (out.year, out.month) < (as_on.year, as_on.month):
        return "FND of " + MONTHS[out.month - 1].title()[:3]
    return ""


def title_for(as_on):
    return f"DESPATCHED COACHES - {MONTHS[as_on.month - 1]} {as_on.year}"


def despatched_in_month(D, as_on):
    """All coaches with actual (physical) despatch date in as_on's month (HQ OUT TURN date when listed there,
    else ERP - see core.physical) -> ({key: demand}, [left-out text])."""
    found, left = {}, []
    for d in D:
        if R.is_excluded(d):
            continue
        ad = R.pdate(P.shop_out(d))                 # shop out (ERP actual despatch)
        if not ad or ad.year != as_on.year or ad.month != as_on.month or ad > as_on:
            continue
        k = R.coach_key(d)
        if k in found and R.pdate(P.shop_out(found[k])) >= ad:
            continue
        if plan_group(d) is None:
            left.append(f"{d.get('coachNo')} {R.coach_type(d)}")
            continue
        found[k] = d
    return found, sorted(set(left))


def build(D, current, as_on=None):
    """current = rows read from the tab (A1:J...) -> dict(rows, new_month, archive, added, left)."""
    as_on = as_on or date.today()
    old_title = str(current[0][0]).strip().upper() if current and current[0] else ""
    new_month = old_title != title_for(as_on)
    old_rows = [list(r) + [""] * NCOL for r in current[FIRST - 1:] if len(r) > 1 and str(r[1]).strip()]
    keep = {} if new_month else {R.coach_key({"coachNo": str(r[1]).strip().lstrip("'")}): r[:NCOL] for r in old_rows}
    erp, left = despatched_in_month(D, as_on)
    added = []
    for k, d in erp.items():
        fill = ["", str(d.get("coachNo")).strip(), plan_group(d), R.coach_type(d), d.get("divisionId") or "",
                _d(d.get("corrComp")), _d(d.get("pdcDate")), _d(d.get("dispatchDate")), _d(P.shop_out(d)),
                _fnd_remark(d, as_on), _phys(d)]
        if k in keep:                                 # keep what is there, fill only blank cells
            keep[k] = [c if str(c).strip() else fill[i] for i, c in enumerate(keep[k])]
            keep[k][10] = fill[10] or keep[k][10]     # K is the program's: refreshed every run (yard -> physical date)
        else:
            keep[k] = fill
            added.append(str(d.get("coachNo")).strip())
    rows = sorted(keep.values(), key=lambda r: (_parse(r[8]) or date.max, str(r[1])))
    for i, r in enumerate(rows, 1):
        r[0] = i
        r[1] = str(r[1]).strip().lstrip("'")        # written RAW -> text, leading zeros kept (086247)
        for j in (5, 6, 7, 8, 10):                  # typed 06.11.26 / 06/11/2026 ... -> real date (autocorrect)
            r[j] = SD.serial(r[j])
    # rows already in the tab are never removed; list those whose Despatched On differs from ERP shop out
    latest = R.latest_per_coach(D)
    hq_flags = []
    for r in rows:
        d = latest.get(R.coach_key({"coachNo": r[1]}))
        so = R.pdate(P.shop_out(d)) if d else None
        if so and _parse(r[8]) and _parse(r[8]) != so:
            hq_flags.append(f"{r[1]} Despatched On {_txt(r[8])} but ERP shop out {_txt(so)} - not changed")
    archive = None
    if new_month and old_rows and old_title.startswith("DESPATCHED COACHES - "):
        archive = "Despatched " + old_title.replace("DESPATCHED COACHES - ", "").title()[:3] + " " + old_title[-4:]
    return {"rows": rows, "new_month": new_month, "archive": archive, "old_count": len(old_rows),
            "added": added, "left": left, "title": title_for(as_on), "hq_flags": hq_flags}


def preview_lines(plan):
    out = []
    if plan["new_month"] and plan["old_count"]:
        out.append(f"    New month: {plan['old_count']} old rows copied to tab '{plan['archive']}', then the tab starts fresh")
    out.append(f"    Despatched tab: {len(plan['rows'])} coaches ({plan['title'].split(' - ')[1]})"
               + (f" | new: {', '.join(plan['added'])}" if plan["added"] else " | nothing new"))
    if plan["left"]:
        out.append(f"    left out (no plan tab): {', '.join(plan['left'])}")
    for f in plan.get("hq_flags", []):
        out.append(f"    CHECK: {f}")
    return out


def read_current(sh):
    titles = {w.title: w for w in sh.worksheets()}
    return titles[TAB].get_values(f"A1:K{LAST}") if TAB in titles else []


def apply(sh, plan, log):
    titles = {w.title: w for w in sh.worksheets()}
    ws = titles.get(TAB) or sh.add_worksheet(title=TAB, rows=LAST, cols=NCOL)
    if plan["archive"]:
        if plan["archive"] in titles:
            log(f"  Despatched: tab '{plan['archive']}' already exists - old rows NOT copied again")
        else:
            sh.duplicate_sheet(ws.id, insert_sheet_index=len(titles), new_sheet_name=plan["archive"])
            log(f"  Despatched: old month copied to tab '{plan['archive']}'")
    rows = plan["rows"]
    if ws.col_count < NCOL:
        ws.add_cols(NCOL - ws.col_count)
    ws.batch_clear([f"A{FIRST}:K{LAST}"])
    ws.update(range_name="A1:K2", values=[[plan["title"]] + [""] * (NCOL - 1), HEAD], value_input_option="USER_ENTERED")
    if rows:
        ws.update(range_name=f"A{FIRST}:K{FIRST + len(rows) - 1}", values=rows, value_input_option="RAW")
    sh.batch_update({"requests": [{"repeatCell": {
        "range": {"sheetId": ws.id, "startRowIndex": FIRST - 1, "endRowIndex": min(LAST, ws.row_count),
                  "startColumnIndex": 5, "endColumnIndex": 9},
        "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": SD.PATTERN}}},
        "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {"range": {"sheetId": ws.id, "startRowIndex": FIRST - 1, "endRowIndex": min(LAST, ws.row_count),
                  "startColumnIndex": 10, "endColumnIndex": 11},
        "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": SD.PATTERN}}},
        "fields": "userEnteredFormat.numberFormat"}}]})
    back = ws.get_values(f"B{FIRST}:B{FIRST + len(rows) + 5}")
    got = [str(r[0]).lstrip("'") for r in back if r and str(r[0]).strip()]
    want = [str(r[1]).lstrip("'") for r in rows]
    if got != want:
        raise RuntimeError(f"Despatched tab read-back differs ({len(got)} vs {len(want)}) - check the tab")
    log(f"  Production Plan Despatched tab - {len(rows)} coaches - verified")
