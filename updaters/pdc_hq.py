"""
updaters/pdc_hq.py - JIJO's sheet "PDC for CN GS SLR Coaches" (HQ / CW-PER holding format), tabs GS, CN, GSLRD, CZ.
Rules (JIJO 22-10 / 26-10 / 27-10-2026):
 - Rows = ICF coaches under process or in yard only (holding: received, no desp date, not excluded). No FND.
 - STATUS: CORROSION COMPLETED (corrComp) > UNDER CORROSION (corrPlace, or TFR, or pit HCB/LCB) > YARD.
 - PDC = ERP pdcDate; the sheet value is kept only when ERP is blank. REMARKS, COUP kept from the sheet.
 - DIVN = ERP divisionId, else the sheet value. LIGHT / HEAVY: pre-survey hrs >= 500 HEAVY.
 - NO OF DAYS = formula =TODAY()-G<row>. Sorted by PDC (blank last), then receipt date.
 - REMARKS for condemnation come from OUR Condemnation_Pipeline tab (JIJO 03-11-2026): a coach listed there that is
   not yet condemned gets its pipeline status (e.g. "Proposed for condemnation", "M268 Given - condemnation");
   an old typed "nominated / proposed for condemnation" remark on a coach no longer in the pipeline is cleared.
   Already-condemned rows of the pipeline are ignored. Other remarks stay as typed.
 - 10-11-2026 (JIJO): ICF FND / RFD coaches are shown again, below the holding rows, until they are physically
   despatched. Physical = HQ OUT TURN sheet (core.physical overlay in core.data): RFD/FND there = still inside,
   DESP = gone (row drops). STATUS = FND or RFD; REMARKS 'Outturned dd/mm/yyyy' unless something is typed.
 - 09-11-2026 (JIJO): coaches proposed for condemnation (in Condemnation_Pipeline, not yet condemned) are LEFT OUT of
   the rows - balance holding only, same as the Production Plan. They are listed in the preview (LEFT_OUT).
"""
import re
from datetime import date, datetime

from core import rules as R
from analysis.position import holding, fnd_now
from core import physical as P

SHEET_KEY = "12Ajz-OuZPPe-zbRpKfqGRCx2UySxW4lVKfhtAgyEccY"
TABS = {"GS": "GS", "CN": "CN", "SLR / GSLRD": "GSLRD", "CZ": "CZ"}
HEAD = ["SL No.", "RLY", "RS TRANS CODE", "COACH RS NO.", "COUP", "TYPE OF COACHES", "RECEIPT DATE", "SCHEDULE",
        "PRE HRS", "LIGHT / HEAVY", "DIVN", "NO OF DAYS", "STATUS", "PDC", "REMARKS"]


def _sheet_date(v):
    """Sheet shows dd.mm.yy; return a date."""
    v = (v or "").strip()
    if not v:
        return None
    for f in ("%d.%m.%y", "%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, f).date()
        except ValueError:
            pass
    return None


def status(d):
    pit = str(d.get("pitNum") or "").upper()
    if d.get("corrComp"):
        return "CORROSION COMPLETED"
    if d.get("corrPlace") or d.get("tfr") or pit.startswith(("HCB", "LCB")):
        return "UNDER CORROSION"
    return "YARD"


LEFT_OUT = []                                           # filled by build(): coaches left out (condemnation)
_STALE = re.compile(r"(nominat|propos)\w*.*condemn|condemn\w*.*(nominat|propos)", re.I)


def pipeline_remarks(rows):
    """rows of core.condemnation.load() -> {coach key: remark} for coaches not yet condemned."""
    out = {}
    for r in rows or []:
        st = next((str(v).strip() for k, v in r.items() if "status" in k.lower()), "")
        if st.lower().startswith("condemn"):                 # Condemned / Condemnded - already done
            continue
        k = R.coach_key({"coachNo": r.get("coach", "")})
        if k:
            out[k] = st if "condemn" in st.lower() else (f"{st} - condemnation" if st else "Proposed for condemnation")
    return out


def build(demands, as_on, current, cond=None):
    """current = {tab: [rows as read from the sheet]}; cond = pipeline_remarks(...) -> {tab: [value rows]}."""
    cond = cond or {}
    keep = {}
    for tab, rows in current.items():
        for r in rows[2:]:
            r = list(r) + [""] * 15
            k = r[3].strip().lstrip("'").lstrip("0")
            if k:
                keep[k] = dict(coup=r[4].strip(), divn=r[10].strip(), pdc=_sheet_date(r[13]), rem=r[14].strip())
    out = {t: [] for t in TABS.values()}
    LEFT_OUT.clear()
    for h in holding(demands, as_on):
        tab = TABS.get(h["_group"])
        if not tab:
            continue
        k = R.coach_key(h)
        if k in cond:                                   # proposed for condemnation -> not in the rows (JIJO 09-11)
            LEFT_OUT.append(f"{h.get('coachNo')} {R.coach_type(h)}")
            continue
        old = keep.get(k, {})
        pdc = R.pdate(h.get("pdcDate")) or old.get("pdc")
        pre = R.hours(h, "preSurveyHrs")
        rem = old.get("rem", "")
        if k in cond:
            rem = cond[k]
        elif _STALE.search(rem):
            rem = ""
        out[tab].append(dict(
            sort=(pdc or date(9998, 1, 1), R.pdate(h.get("receivedDate")) or date.max),
            vals=["", "SR", R.coach_type(h), "'" + str(h.get("coachNo")), old.get("coup", ""), "NAC",
                  (R.pdate(h.get("receivedDate")) or "").isoformat() if h.get("receivedDate") else "", "POH",
                  int(pre) if pre else "", R.light_heavy(h), h.get("divisionId") or old.get("divn", ""), "",
                  status(h), pdc.isoformat() if pdc else "", rem]))
    for f in fnd_now(demands):                          # ICF FND / RFD - still physically inside (JIJO 10-11)
        tab = TABS.get(f["_group"])
        if not tab:
            continue
        k = R.coach_key(f)
        old = keep.get(k, {})
        out_d = R.pdate(f.get("dispatchDate"))
        pdc = R.pdate(f.get("pdcDate")) or old.get("pdc")
        pre = R.hours(f, "preSurveyHrs")
        rem = old.get("rem", "")
        if not rem or rem.lower().startswith("outturned"):
            rem = f"Outturned {out_d:%d/%m/%Y}"
        out[tab].append(dict(
            sort=(date.max, out_d),                     # after every holding row, by outturn date
            vals=["", "SR", R.coach_type(f), "'" + str(f.get("coachNo")), old.get("coup", ""), "NAC",
                  (R.pdate(f.get("receivedDate")) or "").isoformat() if f.get("receivedDate") else "", "POH",
                  int(pre) if pre else "", R.light_heavy(f), f.get("divisionId") or old.get("divn", ""), "",
                  (f"{f.get('_hqStatus') or 'FND'} - YARD" if P.in_yard(f) else "FND"),     # shop out, waiting in yard
                  pdc.isoformat() if pdc else "", rem]))
    result = {}
    for tab, items in out.items():
        items.sort(key=lambda x: x["sort"])
        rows = []
        for i, it in enumerate(items, 1):
            v = list(it["vals"])
            v[0] = i
            v[11] = f"=TODAY()-G{i + 2}"
            rows.append(v)
        result[tab] = rows
    return result


def preview_lines(new, current):
    lines = []
    for tab, rows in new.items():
        before = {r[3].strip().lstrip("'") for r in current.get(tab, [])[2:] if len(r) > 3 and r[3].strip()}
        after = {r[3].lstrip("'") for r in rows}
        add, gone = sorted(after - before), sorted(before - after)
        nf = [r[3].lstrip("'") for r in rows if str(r[12]).startswith(("FND", "RFD"))]
        lines.append(f"  {tab:6} {len(rows):2} coaches" + (f" (FND/RFD {len(nf)}: {', '.join(nf)})" if nf else "")
                     + (f" | new: {', '.join(add)}" if add else "")
                     + (f" | dropped (despatched/outturn of no ICF FND/returned): {', '.join(gone)}" if gone else ""))
    return lines


def read_current(sh):
    cur = {}
    titles = {w.title: w for w in sh.worksheets()}
    for tab in TABS.values():
        cur[tab] = titles[tab].get_values("A1:O200") if tab in titles else []
    return cur


def apply(sh, new, as_on, log):
    existing = {w.title: w for w in sh.worksheets()}
    for tab, rows in new.items():
        n = len(rows) + 2
        ws = existing.get(tab) or sh.add_worksheet(title=tab, rows=max(n + 10, 30), cols=15)
        sid = ws.id
        if ws.row_count < n + 5:                         # FND rows can make a tab longer than its grid
            ws.add_rows(n + 5 - ws.row_count)
        ws.batch_clear(["A1:O300"])
        sh.batch_update({"requests": [{"unmergeCells": {"range": {"sheetId": sid}}}]})
        vals = [[f"{tab} HOLDING  {as_on:%d/%m/%Y}"] + [""] * 14, HEAD] + rows
        ws.update(range_name="A1", values=vals, value_input_option="USER_ENTERED")

        def rng(r0, r1, c0, c1):
            return {"sheetId": sid, "startRowIndex": r0, "endRowIndex": r1, "startColumnIndex": c0, "endColumnIndex": c1}
        reqs = [
            {"mergeCells": {"range": rng(0, 1, 0, 15), "mergeType": "MERGE_ALL"}},
            {"repeatCell": {"range": rng(0, 1, 0, 15), "cell": {"userEnteredFormat": {"backgroundColor": {"red": 1, "green": 1, "blue": 0},
                "horizontalAlignment": "CENTER", "textFormat": {"bold": True, "fontSize": 11}}},
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)"}},
            {"repeatCell": {"range": rng(1, 2, 0, 15), "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP", "textFormat": {"bold": True}}},
                "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment,wrapStrategy,textFormat)"}},
            {"updateBorders": {"range": rng(0, max(n, 2), 0, 15), **{k: {"style": "SOLID"} for k in
                ("top", "bottom", "left", "right", "innerHorizontal", "innerVertical")}}},
            {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 2}},
                "fields": "gridProperties.frozenRowCount"}},
        ]
        if rows:
            reqs += [
                {"repeatCell": {"range": rng(2, n, 0, 15), "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                    "fields": "userEnteredFormat.horizontalAlignment"}},
                {"repeatCell": {"range": rng(2, n, 6, 7), "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "dd.mm.yy"}}},
                    "fields": "userEnteredFormat.numberFormat"}},
                {"repeatCell": {"range": rng(2, n, 13, 14), "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "dd.mm.yy"}}},
                    "fields": "userEnteredFormat.numberFormat"}},
                {"repeatCell": {"range": rng(2, n, 11, 12), "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "0"}}},
                    "fields": "userEnteredFormat.numberFormat"}},
            ]
        reqs.append({"repeatCell": {"range": rng(2, min(ws.row_count, max(n, 3) + 40), 0, 15), "cell": {"userEnteredFormat": {
            "backgroundColor": {"red": 1, "green": 1, "blue": 1}}}, "fields": "userEnteredFormat.backgroundColor"}})
        for i, r in enumerate(rows):                     # FND / RFD rows light green (green = FND, JIJO colour code)
            if str(r[12]).startswith(("FND", "RFD")):
                reqs.append({"repeatCell": {"range": rng(i + 2, i + 3, 0, 15), "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 0.85, "green": 0.94, "blue": 0.83}}},
                    "fields": "userEnteredFormat.backgroundColor"}})
        reqs.append({"autoResizeDimensions": {"dimensions": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 15}}})
        sh.batch_update({"requests": reqs})
        back = ws.get_values(f"D3:D{n}") if rows else []
        ok = [b[0].lstrip("'") for b in back if b] == [r[3].lstrip("'") for r in rows]
        log(f"  PDC sheet {tab:6} {len(rows):2} coaches - {'verified' if ok else 'CHECK: read-back differs'}")
        if not ok:
            raise RuntimeError(f"PDC sheet tab {tab}: read-back differs - stopped")
