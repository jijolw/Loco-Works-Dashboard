"""
analysis/position.py - month position, holding, outturn matrix, coach search.
All counts follow core.rules (outturn = desp date; excluded visits never counted).
"""
from collections import defaultdict
from datetime import date

from core import rules as R


def _groups_sorted(keys, demands):
    order = {}
    for d in demands:
        order.setdefault(d["_group"], (R.FAMILY_ORDER.index(d["_family"]) if d["_family"] in R.FAMILY_ORDER else 99,
                                       d["_order"]))
    return sorted(keys, key=lambda g: (order.get(g, (99, 999)), g))


def _family_of(demands):
    return {d["_group"]: d["_family"] for d in demands}


def outturns(demands, d0, d1):
    """Clean outturn visits with desp date in [d0, d1]."""
    seen, out = set(), []
    for d in demands:
        dd = R.pdate(d.get("dispatchDate"))
        if dd and d0 <= dd <= d1 and not R.is_excluded(d) and d["demandId"] not in seen:
            seen.add(d["demandId"])
            out.append(d)
    return out


def holding(demands, as_on):
    rows = []
    for d in R.latest_per_coach(demands).values():
        if R.in_holding(d):
            rd = R.pdate(d.get("receivedDate"))
            rows.append(dict(d, _loc=R.location(d), _days=(as_on - rd).days if rd else None,
                             _lh=R.light_heavy(d)))
    return rows


def not_inside(demands):
    """Coaches data-entered in ERP but not yet taken inside (no pit, no status) - never in holding."""
    return sorted((d for d in R.latest_per_coach(demands).values() if R.not_yet_inside(d)),
                  key=lambda d: (d["_order"], str(d.get("coachNo"))))


def fnd_now(demands):
    """Coaches outturned (desp date) but not physically despatched - one per coach (latest visit).
    The single FND definition used by Month Position, Aerial View and the checks."""
    return [d for d in R.latest_per_coach(demands).values() if R.is_fnd(d)]


def month_position(demands, as_on, month=None):
    """Dashboard: one row per group for the month of `month` (default: as_on)."""
    m0 = R.month_start(month or as_on)
    m1 = date(m0.year + (m0.month == 12), m0.month % 12 + 1, 1)
    end = min(as_on, date.fromordinal(m1.toordinal() - 1))

    rows = defaultdict(lambda: dict(outturn=0, desp=0, fnd=0, yard=0, work=0))
    fnd_list, prev_fnd, prev_fnd_desp = [], [], []
    for d in outturns(demands, m0, end):
        r = rows[d["_group"]]
        r["outturn"] += 1
        if d.get("actualDispatchDate"):
            r["desp"] += 1
        else:
            r["fnd"] += 1
            fnd_list.append(d)
    fnd_ids = {d["demandId"] for d in fnd_now(demands)}
    fnd_list = [d for d in fnd_list if d["demandId"] in fnd_ids]
    for d in fnd_now(demands):
        if R.pdate(d.get("dispatchDate")) < m0:
            prev_fnd.append(d)                       # outturned earlier, still inside
    for d in demands:
        dd, ad = R.pdate(d.get("dispatchDate")), R.pdate(d.get("actualDispatchDate"))
        if dd and dd < m0 and ad and m0 <= ad <= end and not R.is_excluded(d):
            prev_fnd_desp.append(d)                  # shown separately, never this month's outturn
    for h in holding(demands, as_on):
        rows[h["_group"]]["yard" if h["_loc"] == "Yard" else "work"] += 1

    fam = _family_of(demands)
    out = []
    for g in _groups_sorted(rows.keys(), demands):
        r = rows[g]
        out.append(dict(group=g, family=fam.get(g, ""), **r, holding=r["yard"] + r["work"]))
    tot = {k: sum(r[k] for r in out) for k in ("outturn", "desp", "fnd", "yard", "work", "holding")}
    return dict(month=m0, end=end, rows=out, total=tot,
                fnd_list=sorted(fnd_list, key=lambda d: R.pdate(d["dispatchDate"])),
                prev_fnd=sorted(prev_fnd, key=lambda d: R.pdate(d["dispatchDate"])),
                prev_fnd_desp=prev_fnd_desp, outside=not_inside(demands))


AGE_BANDS = [(0, 20, "0-20"), (21, 30, "21-30"), (31, 10 ** 6, ">30")]


def holding_summary(demands, as_on):
    rows = defaultdict(lambda: {"yard": 0, "work": 0, "0-20": 0, "21-30": 0, ">30": 0,
                                "LIGHT": 0, "HEAVY": 0, "max": 0})
    H = holding(demands, as_on)
    for h in H:
        r = rows[h["_group"]]
        r["yard" if h["_loc"] == "Yard" else "work"] += 1
        days = h["_days"] or 0
        r["max"] = max(r["max"], days)
        for lo, hi, lab in AGE_BANDS:
            if lo <= days <= hi:
                r[lab] += 1
        if h["_lh"]:
            r[h["_lh"]] += 1
    fam = _family_of(demands)
    out = [dict(group=g, family=fam.get(g, ""), total=rows[g]["yard"] + rows[g]["work"], **rows[g])
           for g in _groups_sorted(rows.keys(), demands)]
    keys = ["yard", "work", "total", "0-20", "21-30", ">30", "LIGHT", "HEAVY"]
    tot = {k: sum(r[k] for r in out) for k in keys}
    tot["max"] = max([r["max"] for r in out] or [0])
    return dict(rows=out, total=tot, coaches=sorted(H, key=lambda h: (h["_order"], -(h["_days"] or 0))))


def outturn_matrix(demands, fy):
    """Group x month outturn for a financial year."""
    d0, d1 = R.fy_start(fy), R.fy_end(fy)
    months = [date(d0.year + (m < 4), m, 1) for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)]
    cells = defaultdict(lambda: defaultdict(int))
    for d in outturns(demands, d0, d1):
        dd = R.pdate(d["dispatchDate"])
        cells[d["_group"]][(dd.year, dd.month)] += 1
    fam = _family_of(demands)
    rows = []
    for g in _groups_sorted(cells.keys(), demands):
        vals = [cells[g].get((m.year, m.month), 0) for m in months]
        rows.append(dict(group=g, family=fam.get(g, ""), vals=vals, total=sum(vals)))
    totals = [sum(r["vals"][i] for r in rows) for i in range(12)]
    return dict(fy=fy, months=months, rows=rows, totals=totals, grand=sum(totals))


def available_fys(demands):
    s = {R.fy_of(R.pdate(d.get("dispatchDate"))) for d in demands if d.get("dispatchDate")}
    return sorted((f for f in s if f), reverse=True)


def coach_visits(demands, coachno):
    k = str(coachno or "").strip().replace(" ", "").lstrip("0")
    if not k:
        return []
    v = [d for d in demands if R.coach_key(d) == k]
    return sorted(v, key=lambda d: R.pdate(d.get("receivedDate")) or date.min, reverse=True)


def others_list(demands, since):
    """Coach types not in coach_groups.csv (recent visits only) - for JIJO to place."""
    out = {}
    for d in demands:
        if d["_group"] != "OTHERS":
            continue
        rd = R.pdate(d.get("receivedDate"))
        if R.is_excluded(d) or not rd or rd < since:
            continue
        out.setdefault(R.coach_type(d) or "(blank)", []).append(d.get("coachNo"))
    return out
