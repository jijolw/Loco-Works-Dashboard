"""
analysis/perf.py - cycle time, corrosion cycle, man-hours, previous POH, target vs actual.
All based on clean outturns (desp date in period, exclusions applied) - core.rules.
"""
import csv
import io
import statistics
import time
from collections import defaultdict, OrderedDict
from datetime import date

from core import rules as R
from analysis.position import outturns, holding, _groups_sorted, _family_of


def _avg(x):
    x = [v for v in x if v is not None]
    return round(sum(x) / len(x), 1) if x else None


def _med(x):
    x = [v for v in x if v is not None]
    return round(statistics.median(x), 1) if x else None


def _days(a, b):
    return (b - a).days if a and b and b >= a else None


def _grouped(items, demands, build):
    by = defaultdict(list)
    for it in items:
        by[it["group"]].append(it)
    fam = _family_of(demands)
    rows = [dict(group=g, family=fam.get(g, ""), **build(by[g])) for g in _groups_sorted(by.keys(), demands)]
    return rows, build(items) if items else None


# ---------------------------------------------------------------- cycle time
def visit_facts(d):
    rd, dd = R.pdate(d.get("receivedDate")), R.pdate(d.get("dispatchDate"))
    ad, tf = R.pdate(d.get("actualDispatchDate")), R.pdate(d.get("tfr"))
    cs, cc = R.pdate(d.get("corrPlace") or d.get("corrPd")), R.pdate(d.get("corrComp"))
    return dict(d=d, group=d["_group"], coach=d.get("coachNo"), recd=rd, desp=dd, actual=ad, tfr=tf,
                cs=cs, cc=cc, total=_days(rd, dd), physical=_days(rd, ad), attn=_days(tf, dd),
                corr=_days(cs, cc), to_corr=_days(rd, cs), after_corr=_days(cc, dd),
                pre=R.hours(d, "preSurveyHrs"), final=R.hours(d, "finalHrs"), lh=R.light_heavy(d))


def cycle_time(demands, d0, d1):
    items = [visit_facts(d) for d in outturns(demands, d0, d1)]

    def build(L):
        t = [i["total"] for i in L]
        return dict(n=len(L), avg=_avg(t), med=_med(t), min=min([v for v in t if v is not None], default=None),
                    max=max([v for v in t if v is not None], default=None),
                    over30=sum(1 for v in t if v is not None and v > 30),
                    attn=_avg([i["attn"] for i in L]), physical=_avg([i["physical"] for i in L]),
                    light=_avg([i["total"] for i in L if i["lh"] == "LIGHT"]),
                    heavy=_avg([i["total"] for i in L if i["lh"] == "HEAVY"]))
    rows, tot = _grouped(items, demands, build)
    # month trend (avg entry -> outturn) per family
    trend = defaultdict(lambda: defaultdict(list))
    for i in items:
        trend[i["d"]["_family"]][(i["desp"].year, i["desp"].month)].append(i["total"])
    months = sorted({(i["desp"].year, i["desp"].month) for i in items})
    fams = [f for f in R.FAMILY_ORDER if f in trend]
    trend_rows = [dict(family=f, vals=[_avg(trend[f].get(m, [])) for m in months]) for f in fams]
    return dict(rows=rows, total=tot, items=sorted(items, key=lambda i: (i["d"]["_order"], i["desp"])),
                months=[date(y, m, 1) for y, m in months], trend=trend_rows)


# ---------------------------------------------------------------- corrosion
def corrosion(demands, d0, d1, as_on):
    items = [visit_facts(d) for d in outturns(demands, d0, d1)]

    def build(L):
        w = [i for i in L if i["corr"] is not None]
        return dict(n=len(L), with_corr=len(w), corr=_avg([i["corr"] for i in w]), corr_med=_med([i["corr"] for i in w]),
                    to_corr=_avg([i["to_corr"] for i in w]), after=_avg([i["after_corr"] for i in w]),
                    corr_max=max([i["corr"] for i in w], default=None))
    rows, tot = _grouped(items, demands, build)

    # this month: completed in month / carry forward / under corrosion now
    m0 = R.month_start(as_on)
    done = defaultdict(int)
    carry = defaultdict(int)
    for d in demands:
        if R.is_excluded(d):
            continue
        cc, dd = R.pdate(d.get("corrComp")), R.pdate(d.get("dispatchDate"))
        if cc and m0 <= cc <= as_on:
            done[d["_group"]] += 1
        if cc and cc < m0 and dd and m0 <= dd <= as_on:
            carry[d["_group"]] += 1
    under = []
    for h in holding(demands, as_on):
        cs = R.pdate(h.get("corrPlace") or h.get("corrPd"))
        if cs and not h.get("corrComp"):
            under.append(dict(h, _cdays=(as_on - cs).days, _cs=cs))
    fam = _family_of(demands)
    keys = set(done) | set(carry) | {u["_group"] for u in under}
    ucount = defaultdict(int)
    for u in under:
        ucount[u["_group"]] += 1
    month_rows = [dict(group=g, family=fam.get(g, ""), done=done[g], carry=carry[g], under=ucount[g])
                  for g in _groups_sorted(keys, demands)]
    return dict(rows=rows, total=tot, month=m0, month_rows=month_rows,
                under=sorted(under, key=lambda u: -u["_cdays"]),
                items=[i for i in sorted(items, key=lambda i: (i["d"]["_order"], i["desp"])) if i["corr"] is not None])


# ---------------------------------------------------------------- man-hours
def man_hours(demands, d0, d1):
    items = [visit_facts(d) for d in outturns(demands, d0, d1)]

    def build(L):
        p = [i["pre"] for i in L if i["pre"]]
        f = [i["final"] for i in L if i["final"]]
        both = [i for i in L if i["pre"] and i["final"]]
        var = _avg([(i["final"] - i["pre"]) / i["pre"] * 100 for i in both])
        return dict(n=len(L), pre_n=len(p), pre=round(_avg(p)) if p else None, final_n=len(f),
                    final=round(_avg(f)) if f else None, var=var,
                    light=sum(1 for i in L if i["lh"] == "LIGHT"), heavy=sum(1 for i in L if i["lh"] == "HEAVY"),
                    no_final=sum(1 for i in L if not i["final"]))
    rows, tot = _grouped(items, demands, build)
    missing = [i for i in items if not i["final"]]
    return dict(rows=rows, total=tot, missing=sorted(missing, key=lambda i: (i["d"]["_order"], i["desp"])))


# ---------------------------------------------------------------- previous POH
LHB_SCHED = {"104": "SS1", "121": "SS2", "243": "SS2", "244": "SS2", "122": "SS3", "241": "SS3", "242": "SS3"}


def previous_poh(demands, d0, d1, family="ALL"):
    items = [visit_facts(d) for d in outturns(demands, d0, d1)]
    if family != "ALL":
        items = [i for i in items if i["d"]["_family"] == family]
    by = defaultdict(list)
    for i in items:
        by[(i["d"].get("lastPoh") or "Not in ERP").strip().upper()].append(i)
    rows = []
    for wks, L in by.items():
        p = [i["pre"] for i in L if i["pre"]]
        rows.append(dict(wks=wks, n=len(L), pre=round(_avg(p)) if p else None,
                         heavy=sum(1 for i in L if i["lh"] == "HEAVY"), with_pre=len(p),
                         heavy_pct=round(100 * sum(1 for i in L if i["lh"] == "HEAVY") / len(p)) if p else None,
                         final=round(_avg([i["final"] for i in L if i["final"]]) or 0) or None,
                         cycle=_avg([i["total"] for i in L]),
                         gap=_avg([round((i["recd"] - R.pdate(i["d"].get("lastPohDate"))).days / 30.4, 1)
                                   for i in L if i["recd"] and R.pdate(i["d"].get("lastPohDate"))])))
    rows.sort(key=lambda r: -r["n"])
    sched = defaultdict(lambda: OrderedDict(SS1=0, SS2=0, SS3=0, Other=0))
    for i in items:
        if i["d"]["_family"] == "LHB":
            sched[i["group"]][LHB_SCHED.get(str(i["d"].get("repairType")), "Other")] += 1
    return dict(rows=rows, n=len(items), sched=dict(sched))


# ---------------------------------------------------------------- targets (Internal_Targets tab)
# target "Coach Type" -> our groups (checked against the sheet's own Achieved column, May/Jun 2026)
TARGET_MAP = {"CN": ["CN"], "GS": ["GS"], "CZ": ["CZ"], "SLR": ["SLR / GSLRD"], "LWSCN": ["LWSCN"],
              "LWS": ["LWS"], "LWACCN": ["LWACCN"], "LWACCW": ["LWACCW"],
              "3-PHASE": ["MEMU MC", "EMU MC", "MEMU TC", "EMU TC"], "DPC/DTC": ["DEMU DPC", "DEMU TC"],
              "NMG": ["NMG POH"], "ART": ["ART"]}
_tcache = {"t": 0, "rows": None, "err": None}


def load_targets(sheet_key, csv_text=None):
    """Read Internal_Targets (public gviz CSV), cached 30 min."""
    if csv_text is None:
        if _tcache["rows"] is not None and time.time() - _tcache["t"] < 1800:
            return _tcache["rows"], _tcache["err"]
        try:
            import requests
            url = (f"https://docs.google.com/spreadsheets/d/{sheet_key}/gviz/tq?tqx=out:csv"
                   f"&sheet=Internal_Targets&t={int(time.time())}")
            csv_text = requests.get(url, timeout=20).text
        except Exception as e:
            _tcache.update(t=time.time(), rows=[], err=f"Could not read targets sheet: {e}")
            return [], _tcache["err"]
    rows = []
    for r in csv.DictReader(io.StringIO(csv_text)):
        try:
            mon = r.get("Month", "").strip().upper()
            m = date(int(mon[-4:]), ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
                                     "NOV", "DEC"].index(mon[:3]) + 1, 1)
        except (ValueError, IndexError):
            continue
        t = (r.get("Internal Target") or "").strip()
        rows.append(dict(month=m, type=(r.get("Coach Type") or "").strip().upper(),
                         target=int(float(t)) if t.replace(".", "", 1).isdigit() else None))
    _tcache.update(t=time.time(), rows=rows, err=None)
    return rows, None


def targets_vs_actual(demands, fy, as_on, trows):
    d0 = R.fy_start(fy)
    months = [date(d0.year + (m < 4), m, 1) for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)]
    months = [m for m in months if m <= as_on]
    act = defaultdict(int)
    for d in outturns(demands, d0, min(as_on, R.fy_end(fy))):
        dd = R.pdate(d["dispatchDate"])
        act[(d["_group"], dd.year, dd.month)] += 1
    tgt = {(r["type"], r["month"]): r["target"] for r in trows}
    rows = []
    for ttype, groups in TARGET_MAP.items():
        cells = []
        for m in months:
            a = sum(act[(g, m.year, m.month)] for g in groups)
            t = tgt.get((ttype, m))
            cells.append(dict(t=t, a=a, pct=round(100 * a / t) if t else None))
        tsum = sum(c["t"] for c in cells if c["t"] is not None)
        asum_t = sum(c["a"] for c in cells if c["t"] is not None)
        rows.append(dict(type=ttype, groups=", ".join(groups), cells=cells, tsum=tsum,
                         asum_t=asum_t, asum=sum(c["a"] for c in cells),
                         pct=round(100 * asum_t / tsum) if tsum else None))
    covered = {g for gs in TARGET_MAP.values() for g in gs}
    others = defaultdict(lambda: [0] * len(months))
    for (g, y, mo), n in act.items():
        if g not in covered:
            idx = next((i for i, m in enumerate(months) if (m.year, m.month) == (y, mo)), None)
            if idx is not None:
                others[g][idx] += n
    months_with_target = [m for m in months if any(tgt.get((t, m)) is not None for t in TARGET_MAP)]
    return dict(fy=fy, months=months, rows=rows, others=dict(others), months_with_target=months_with_target)
