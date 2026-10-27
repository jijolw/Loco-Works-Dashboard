"""
analysis/stock_targets.py - Target vs Actual by STOCK TYPE (ICF NAC, LHB NAC / AC, EMU/MEMU, DEMU ...),
targets from OUR sheet POSITION11092026 tabs HQ_Targets (monthly), RB_Targets (annual) and Internal_Targets
(rolled up). Actual = ERP outturn (desp date), same rules as every other page. AC locos never shown.
ICF IOH, LHB SS1 and Vande Bharat are not in the coach ERP -> target shown, actual "not in ERP".
"""
import csv
import io
import time
from collections import defaultdict
from datetime import date

from core import rules as R
from analysis.position import outturns

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# (key, label, groups counted as actual or None = not in coach ERP, extra filter)
CATS = [
    ("ICF|POH|NAC", "ICF POH (NAC)", ["GS", "CN", "SLR / GSLRD", "CZ", "VPH", "VPU", "VPUX"]),
    ("ICF|IOH|NAC", "ICF IOH (NAC)", None),
    ("LHB|SS2/SS3|NAC", "LHB SS2/SS3 (NAC)", ["LWSCN", "LWS", "LSLRD", "LVPH", "LWCBAC (Pantry)"]),
    ("LHB|SS2/SS3|AC", "LHB SS2/SS3 (AC)", ["LWACCN", "LWACCW"]),
    ("LHB|SS1|NAC", "LHB SS1 (NAC)", None),
    ("LHB|SS1|AC", "LHB SS1 (AC)", None),
    ("EMU/MEMU|POH|NA", "EMU / MEMU", ["MEMU MC", "EMU MC", "MEMU TC", "EMU TC"]),
    ("DEMU/DTC/TC|POH|NA", "DEMU / DTC / TC", ["DEMU DPC", "DEMU TC"]),
    ("NMGHS|CONV/POH|NA", "NMGHS (POH + Conv)", ["NMG POH", "NMG CONVERSION"]),
    ("ART|CONV|NA", "ART / ARMV Conversion", ["ART CONVERSION", "ARMV CONVERSION"]),
    ("SPART|POH|NA", "SPART", ["SPART"]),
    ("SPIC|POH|NA", "SPIC", ["SPIC"]),
    ("TW 4W|POH|NA", "Tower Wagon 4W", ["TW4W"]),
    ("TW 8W|POH|NA", "Tower Wagon 8W", ["TW8W"]),
    ("VB|SS1|AC", "Vande Bharat SS1", None),
    ("VB|SS2|AC", "Vande Bharat SS2", None),
]
# RB sheet names -> category key
RB_ALIAS = {"4W TW|POH|NA": "TW 4W|POH|NA", "8W TW|POH|NA": "TW 8W|POH|NA",
            "VB SS1|POH|NA": "VB|SS1|AC", "VB SS2|POH|NA": "VB|SS2|AC"}
# Internal target coach types -> category key (SS2/SS3 only)
INTERNAL = {"CN": "ICF|POH|NAC", "GS": "ICF|POH|NAC", "CZ": "ICF|POH|NAC", "SLR": "ICF|POH|NAC",
            "LWSCN": "LHB|SS2/SS3|NAC", "LWS": "LHB|SS2/SS3|NAC", "LWACCN": "LHB|SS2/SS3|AC",
            "LWACCW": "LHB|SS2/SS3|AC", "3-PHASE": "EMU/MEMU|POH|NA", "DPC/DTC": "DEMU/DTC/TC|POH|NA",
            "NMG": "NMGHS|CONV/POH|NA"}
SKIP = ("AC LOCO", "ELECTRIC LOCO")


def _key(stock, sched, nac):
    return f"{stock.strip().upper()}|{sched.strip().upper()}|{nac.strip().upper()}"


def _num(v):
    v = (v or "").strip()
    try:
        return float(v) if "." in v else int(v)
    except ValueError:
        return None


def _month(fy, name):
    i = MONTHS.index(name.strip().upper()[:3]) + 1
    y = int(fy[:4]) + (1 if i < 4 else 0)
    return date(y, i, 1)


_cache = {}


def load_tab(sheet_key, tab, csv_text=None):
    """Public gviz CSV of one tab of OUR sheet, cached 30 min."""
    if csv_text is None:
        c = _cache.get(tab)
        if c and time.time() - c[0] < 1800:
            return c[1]
        import requests
        url = (f"https://docs.google.com/spreadsheets/d/{sheet_key}/gviz/tq?tqx=out:csv"
               f"&sheet={tab}&t={int(time.time())}")
        csv_text = requests.get(url, timeout=20).text
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    _cache[tab] = (time.time(), rows)
    return rows


def build(demands, fy, as_on, hq_rows, rb_rows, internal_rows):
    d0 = R.fy_start(fy)
    months = [date(d0.year + (m < 4), m, 1) for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)]
    months = [m for m in months if m <= as_on]
    act = defaultdict(int)
    for d in outturns(demands, d0, min(as_on, R.fy_end(fy))):
        dd = R.pdate(d["dispatchDate"])
        g = d["_group"]
        if g == "OR":            # HQ counts an OR coach under its own coach type (e.g. LWSCN -> LHB NAC)
            g = R.classify(dict(d, repairType=None))[1]
        act[(g, dd.year, dd.month)] += 1

    hq = {}
    for r in hq_rows:
        if (r.get("FY") or "").strip() != fy or (r.get("Stock Type") or "").strip().upper() in SKIP:
            continue
        try:
            m = _month(fy, r.get("Month", ""))
        except (ValueError, IndexError):
            continue
        hq[(_key(r.get("Stock Type", ""), r.get("Schedule", ""), r.get("NAC/AC", "")), m)] = _num(r.get("HQ Target"))
    rb = {}
    for r in rb_rows:
        if (r.get("FY") or "").strip() != fy or (r.get("Stock Type") or "").strip().upper() in SKIP:
            continue
        k = _key(r.get("Stock Type", ""), r.get("Schedule", ""), r.get("NAC/AC", ""))
        rb[RB_ALIAS.get(k, k)] = (_num(r.get("RB Annual Target")), _num(r.get("RB Monthly Target")))
    internal = defaultdict(lambda: None)
    for r in internal_rows:
        if r["month"] in months and r["target"] is not None and r["type"] in INTERNAL:
            k = (INTERNAL[r["type"]], r["month"])
            internal[k] = (internal[k] or 0) + r["target"]

    rows = []
    for key, label, groups in CATS:
        cells = []
        for m in months:
            a = None if groups is None else sum(act[(g, m.year, m.month)] for g in groups)
            cells.append(dict(t=hq.get((key, m)), a=a, i=internal.get((key, m))))
        t_set = [c for c in cells if c["t"] is not None]
        hq_t = sum(c["t"] for c in t_set) if t_set else None
        hq_a = sum(c["a"] for c in t_set) if t_set and groups is not None else None
        a_all = sum(c["a"] for c in cells) if groups is not None else None
        i_set = [c for c in cells if c["i"] is not None]
        i_t = sum(c["i"] for c in i_set) if i_set else None
        i_a = sum(c["a"] for c in i_set) if i_set and groups is not None else None
        rba, rbm = rb.get(key, (None, None))
        rb_todate = rbm * len(months) if rbm else None
        rows.append(dict(key=key, label=label, groups=", ".join(groups) if groups else "not in coach ERP",
                         in_erp=groups is not None, cells=cells, hq_t=hq_t, hq_a=hq_a,
                         hq_pct=round(100 * hq_a / hq_t) if hq_t and hq_a is not None else None,
                         i_t=i_t, i_a=i_a, i_pct=round(100 * i_a / i_t) if i_t and i_a is not None else None,
                         a_all=a_all, rb_annual=rba, rb_todate=rb_todate,
                         rb_pct=round(100 * a_all / rb_todate) if rb_todate and a_all is not None else None,
                         rb_annual_pct=round(100 * a_all / rba) if rba and a_all is not None else None))
    covered = {g for _, _, gs in CATS if gs for g in gs}
    others = defaultdict(int)
    for (g, y, mo), n in act.items():
        if g not in covered:
            others[g] += n
    return dict(fy=fy, months=months, rows=rows, others=dict(others))
