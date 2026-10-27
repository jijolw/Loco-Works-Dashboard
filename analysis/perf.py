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
# A target "Coach Type" may name one ERP type, a group, or several joined by "/" (CZ/CZJ/CZRJ, LWS/LS5).
# A group name counts every ERP type of that group (CZ = CZ, CZJ, CZRJ), EXCEPT a type that has its own target
# row in the same month (e.g. LWACCNE given separately in Oct-26 is then not counted under LWACCN).
# Only POH visits: OR and conversions are never counted against these targets.
ALIAS_GROUPS = {"3-PHASE": ["MEMU MC", "EMU MC", "MEMU TC", "EMU TC"], "DPC/DTC": ["DEMU DPC", "DEMU TC"],
                "NMG": ["NMG POH"], "ART": ["ART"]}
TYPE_ALIAS = {"SLR": "SLR / GSLRD", "GSLRD": "SLR / GSLRD"}     # SLR target = SLR + GSLRD + GSRD types
NOT_POH = {"OR", "ART CONVERSION", "ARMV CONVERSION", "NMG CONVERSION"}
_tcache = {"t": 0, "rows": None, "err": None}


def _group_types():
    """group name -> set of ERP coach types (exact rows of coach_groups.csv)."""
    g = defaultdict(set)
    for r in R._load_groups():
        if r["match"] == "exact":
            g[r["group"].upper()].add(r["erp_type"])
    return g


def target_spec(ttype):
    """'CZ/CZJ/CZRJ' -> (frozenset of ERP types, frozenset of groups)."""
    t = ttype.strip().upper()
    if t in ALIAS_GROUPS:
        return frozenset(), frozenset(g.upper() for g in ALIAS_GROUPS[t])
    gt = _group_types()
    types, groups = set(), set()
    for tok in [x.strip() for x in t.split("/") if x.strip()]:
        if tok in TYPE_ALIAS:
            types |= gt[TYPE_ALIAS[tok].upper()]
        elif tok in ALIAS_GROUPS:
            groups |= {g.upper() for g in ALIAS_GROUPS[tok]}
        elif tok in gt:
            types |= gt[tok]
        else:
            types.add(tok)
    return frozenset(types), frozenset(groups)


def _parse_month(mon):
    mon = (mon or "").strip().upper()
    return date(int(mon[-4:]), ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
                                 "NOV", "DEC"].index(mon[:3]) + 1, 1)


def load_targets(sheet_key=None, csv_text=None):
    """Internal_Targets rows -> [{month, type, target, stock, nac}]. From the saved full read (targets_store);
    csv_text only for tests."""
    if csv_text is not None:
        raw = list(csv.DictReader(io.StringIO(csv_text)))
        err = None
    else:
        from core import targets_store
        raw = targets_store.rows("Internal_Targets")
        err = None if raw else "Targets not read yet - run Update_All.py or press Update from ERP (office PC)."
    rows = []
    for r in raw:
        try:
            m = _parse_month(r.get("Month"))
        except (ValueError, IndexError):
            continue
        t = (r.get("Internal Target") or "").strip()
        try:
            tv = int(float(t)) if t else None
        except ValueError:
            tv = None
        rows.append(dict(month=m, type=(r.get("Coach Type") or "").strip().upper(), target=tv,
                         stock=(r.get("Stock Type") or "").strip().upper(), nac=(r.get("NAC/AC") or "").strip().upper()))
    _tcache.update(t=time.time(), rows=rows, err=err)
    return rows, err


def targets_vs_actual(demands, fy, as_on, trows):
    d0 = R.fy_start(fy)
    months = [date(d0.year + (m < 4), m, 1) for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)]
    months = [m for m in months if m <= as_on]
    mkeys = [(m.year, m.month) for m in months]
    visits = defaultdict(list)                                    # month -> outturn visits
    for d in outturns(demands, d0, min(as_on, R.fy_end(fy))):
        dd = R.pdate(d["dispatchDate"])
        visits[(dd.year, dd.month)].append(d)

    fy_rows = [r for r in trows if d0 <= r["month"] <= R.fy_end(fy) and r["type"]]
    # one row per distinct expansion (CZ and CZ/CZJ/CZRJ are the same row), label = longest name used
    specs, label = {}, {}
    for r in fy_rows:
        sp = target_spec(r["type"])
        specs.setdefault(sp, len(specs))
        if len(r["type"]) > len(label.get(sp, "")):
            label[sp] = r["type"]
    tgt = defaultdict(lambda: None)
    explicit = defaultdict(set)                                   # month -> ERP types named on their own
    for r in fy_rows:
        sp = target_spec(r["type"])
        if r["target"] is not None:
            tgt[(sp, (r["month"].year, r["month"].month))] = (tgt[(sp, (r["month"].year, r["month"].month))] or 0) + r["target"]
        if "/" not in r["type"] and r["type"] not in _group_types() and r["type"] not in ALIAS_GROUPS \
                and r["type"] not in TYPE_ALIAS:
            explicit[(r["month"].year, r["month"].month)].add(r["type"])

    gnames = set(_group_types()) | set(ALIAS_GROUPS) | set(TYPE_ALIAS)
    specific = {sp for sp in specs if len(sp[0]) == 1 and not sp[1] and label[sp] not in gnames}

    def matches(d, sp, mk):
        if d["_group"] in NOT_POH:
            return False
        types, groups = sp
        if d["_group"].upper() in groups:
            return True
        ct = R.coach_type(d)
        if ct not in types:
            return False
        if sp in specific:     # own row (e.g. LWACCNE): counts when it has a row that month, or no group row covers it
            return ct in explicit[mk] or not any(ct in o[0] for o in specs if o != sp)
        return ct not in explicit[mk]   # group row (e.g. LWACCN) leaves out a type that has its own row that month

    rows, used = [], defaultdict(set)
    for sp in sorted(specs, key=specs.get):
        cells, parts = [], defaultdict(lambda: [0] * len(mkeys))
        for i, mk in enumerate(mkeys):
            hit = [d for d in visits[mk] if matches(d, sp, mk)]
            used[mk] |= {d["demandId"] for d in hit}
            for d in hit:                                    # individual count inside a combined target
                parts[d["_group"] if sp[1] else R.coach_type(d)][i] += 1
            t = tgt[(sp, mk)]
            cells.append(dict(t=t, a=len(hit), pct=round(100 * len(hit) / t) if t else None))
        tsum = sum(c["t"] for c in cells if c["t"] is not None)
        asum_t = sum(c["a"] for c in cells if c["t"] is not None)
        types, groups = sp
        part_rows = [dict(name=k, vals=v, total=sum(v)) for k, v in sorted(parts.items())] \
            if len(types | groups) > 1 and len(parts) > 1 else []
        rows.append(dict(type=label[sp], spec=sp, groups=", ".join(sorted(types | groups)), cells=cells, tsum=tsum, parts=part_rows,
                         asum_t=asum_t, asum=sum(c["a"] for c in cells),
                         pct=round(100 * asum_t / tsum) if tsum else None))
    others = defaultdict(lambda: [0] * len(months))
    for i, mk in enumerate(mkeys):
        for d in visits[mk]:
            if d["demandId"] not in used[mk]:
                others[d["_group"]][i] += 1
    months_with_target = [m for m, mk in zip(months, mkeys) if any(tgt[(sp, mk)] is not None for sp in specs)]
    return dict(fy=fy, months=months, rows=rows, others=dict(others), months_with_target=months_with_target)
