"""
updaters/pdc_hq.py - JIJO's sheet "PDC for CN GS SLR Coaches" (HQ / CW-PER holding format), tabs GS, CN, GSLRD, CZ.
Rules (JIJO 22-10 / 26-10 / 27-10-2026):
 - Rows = ICF coaches under process or in yard only (holding: received, no desp date, not excluded). No FND.
 - STATUS: CORROSION COMPLETED (corrComp) > UNDER CORROSION (corrPlace, or TFR, or pit HCB/LCB) > YARD.
 - PDC = ERP pdcDate; the sheet value is kept only when ERP is blank. REMARKS, COUP kept from the sheet.
 - DIVN = ERP divisionId, else the sheet value. LIGHT / HEAVY: pre-survey hrs >= 500 HEAVY.
 - NO OF DAYS = formula =TODAY()-G<row>. Sorted by PDC (blank last), then receipt date.
"""
from datetime import date, datetime

from core import rules as R
from analysis.position import holding

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


def build(demands, as_on, current):
    """current = {tab: [rows as read from the sheet]} -> {tab: [value rows]} + notes."""
    keep = {}
    for tab, rows in current.items():
        for r in rows[2:]:
            r = list(r) + [""] * 15
            k = r[3].strip().lstrip("'").lstrip("0")
            if k:
                keep[k] = dict(coup=r[4].strip(), divn=r[10].strip(), pdc=_sheet_date(r[13]), rem=r[14].strip())
    out = {t: [] for t in TABS.values()}
    for h in holding(demands, as_on):
        tab = TABS.get(h["_group"])
        if not tab:
            continue
        k = R.coach_key(h)
        old = keep.get(k, {})
        pdc = R.pdate(h.get("pdcDate")) or old.get("pdc")
        pre = R.hours(h, "preSurveyHrs")
        out[tab].append(dict(
            sort=(pdc or date.max, R.pdate(h.get("receivedDate")) or date.max),
            vals=["", "SR", R.coach_type(h), "'" + str(h.get("coachNo")), old.get("coup", ""), "NAC",
                  (R.pdate(h.get("receivedDate")) or "").isoformat() if h.get("receivedDate") else "", "POH",
                  int(pre) if pre else "", R.light_heavy(h), h.get("divisionId") or old.get("divn", ""), "",
                  status(h), pdc.isoformat() if pdc else "", old.get("rem", "")]))
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
        lines.append(f"  {tab:6} {len(rows):2} coaches" + (f" | new: {', '.join(add)}" if add else "")
                     + (f" | dropped (outturned/returned): {', '.join(gone)}" if gone else ""))
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
        reqs.append({"autoResizeDimensions": {"dimensions": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 15}}})
        sh.batch_update({"requests": reqs})
        back = ws.get_values(f"D3:D{n}") if rows else []
        ok = [b[0].lstrip("'") for b in back if b] == [r[3].lstrip("'") for r in rows]
        log(f"  PDC sheet {tab:6} {len(rows):2} coaches - {'verified' if ok else 'CHECK: read-back differs'}")
        if not ok:
            raise RuntimeError(f"PDC sheet tab {tab}: read-back differs - stopped")
