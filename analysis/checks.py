"""
analysis/checks.py - the same figure must be the same on every page.
Each check recomputes a figure through every page's own function and compares.
Shown at the bottom of the Report Centre; any mismatch is listed in red.
"""
from datetime import date

from core import rules as R
from analysis import position as P, perf as F, aerial as A


def run(demands, as_on, target_rows=None):
    out = []

    def chk(name, values, tol=0):
        vals = list(values.values())
        ok = all(v is not None for v in vals) and max(vals) - min(vals) <= tol
        out.append(dict(name=name, ok=ok, detail=", ".join(f"{k} {v}" for k, v in values.items())))

    m0 = R.month_start(as_on)
    fy = R.fy_of(as_on)
    f0 = R.fy_start(fy)
    pos = P.month_position(demands, as_on)
    mat = P.outturn_matrix(demands, fy)
    mi = [(m.year, m.month) for m in mat["months"]].index((m0.year, m0.month))
    chk("Outturn this month", {
        "Month Position": pos["total"]["outturn"], "Outturn matrix": mat["totals"][mi],
        "Cycle Time": F.cycle_time(demands, m0, as_on)["total"]["n"] if pos["total"]["outturn"] else 0,
        "Man-hours": F.man_hours(demands, m0, as_on)["total"]["n"] if pos["total"]["outturn"] else 0})

    cyc = F.cycle_time(demands, f0, as_on)
    hrs = F.man_hours(demands, f0, as_on)
    cor = F.corrosion(demands, f0, as_on, as_on)
    prv = F.previous_poh(demands, f0, as_on)
    vals = {"Outturn matrix": mat["grand"], "Cycle Time": cyc["total"]["n"], "Corrosion": cor["total"]["n"],
            "Man-hours": hrs["total"]["n"], "Previous POH": prv["n"],
            "Sum of type rows (cycle)": sum(r["n"] for r in cyc["rows"])}
    if target_rows is not None:
        t = F.targets_vs_actual(demands, fy, as_on, target_rows)
        vals["Target vs Actual (+ untargeted)"] = sum(r["asum"] for r in t["rows"]) + sum(
            sum(v) for v in t["others"].values())
    chk(f"Outturn {fy} to date", vals)

    hs = P.holding_summary(demands, as_on)
    ae = A.aerial(demands, as_on)
    chk("Holding", {"Month Position": pos["total"]["holding"], "Holding page": hs["total"]["total"],
                    "Aerial View": ae["n_hold"]})
    chk("Holding in yard", {"Month Position": pos["total"]["yard"], "Holding page": hs["total"]["yard"],
                            "Aerial yard panel": ae["n_yard"]})
    chk("FND (inside)", {"Month Position": len(pos["fnd_list"]) + len(pos["prev_fnd"]), "Aerial View": ae["n_fnd"]})
    chk("Under corrosion now", {"Corrosion page": len(cor["under"]),
                                "Aerial View": sum(1 for s in ae["shops"].values() for L in s.values()
                                                   for c in L["slots"] + L["extra"] if c and c["corr"] == "under")
                                + sum(1 for c in ae["yard"] + ae["other"] if c["corr"] == "under")})

    # average pre-survey hours: Man-hours page vs weighted average of Previous POH rows
    w = sum(r["pre"] * r["with_pre"] for r in prv["rows"] if r["pre"])
    n = sum(r["with_pre"] for r in prv["rows"])
    chk(f"Avg pre-survey hrs {fy}", {"Man-hours": hrs["total"]["pre"], "Previous POH (weighted)": round(w / n) if n else None}, tol=1)
    chk(f"Heavy coaches {fy}", {"Man-hours": hrs["total"]["heavy"], "Previous POH": sum(r["heavy"] for r in prv["rows"]),
                               "Cycle (coaches with pre hrs)": sum(1 for i in cyc["items"] if i["lh"] == "HEAVY")})
    others = P.others_list(demands, f0)
    out.append(dict(name="Coach types not in coach_groups.csv", ok=not others,
                    detail=", ".join(f"{k}: {len(v)}" for k, v in others.items()) or "none"))
    return out
