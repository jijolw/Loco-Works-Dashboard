"""
analysis/daily_report.py - the 2-page Daily Position report (agreed with JIJO 31-10-2026).

Page 1: shops in the same places as the old Daily Progress print (left: Paint, Incoming, DEMU, Heavy Corr Bay;
        right: LBR, Augmentation, Light Corr Bay, AC Loco Bay), every line shown ("-" = empty), yard in halves
        (3 columns above 30), the day's outturn / physical despatch, weekly plan with status, ICF stock (HQ format),
        ICF by pre-survey hours, LHB by coach type incl. OR.
        Coach no. green = FND, yellow = corrosion completed, red underline = proposed for condemnation
        (Condemnation_Pipeline tab, only coaches still in holding).
Page 2: the ORIGINAL Daily Position table (same rows/columns, red as before), figures from the export.
        CORR COMPL = month outturn + coaches inside with corrosion completed.
Typed (non-ERP) items come from core.daily_inputs (the Daily Report form).
The page shrinks itself to one A4 sheet when printing (Ctrl+P -> Save as PDF).
"""
from collections import Counter, OrderedDict, defaultdict
from datetime import date, timedelta

from analysis import position as P
from analysis.aerial import PREFIX_SHOP, SHOPS, _split_pit
from core import rules as R

CAT = {"GS": "ICF", "CN": "ICF", "SLR / GSLRD": "ICF", "CZ": "ICF", "VPH": "ICF", "VPU": "ICF", "VPUX": "ICF",
       "NMG POH": "NMG", "NMG CONVERSION": "NMG", "ART CONVERSION": "ARTC", "ARMV CONVERSION": "ARTC", "ARMV": "ARTC",
       "ART": "ARTC",
       "LWSCN": "LHBN", "LWS": "LHBN", "LSLRD": "LHBN", "LVPH": "LHBN", "LWCBAC (Pantry)": "LHBN",
       "LWACCN": "LHBA", "LWACCW": "LHBA",
       "MEMU MC": "EMU", "MEMU TC": "EMU", "EMU MC": "EMU", "EMU TC": "EMU",
       "DEMU DPC": "DEMU", "DEMU TC": "DEMU", "SPART": "SPART", "SPIC": "SPART", "TW4W": "TW4", "TW8W": "TW8", "OR": "OR"}
ORDER = ["GS", "CN", "CZ", "CZJ", "CZRJ", "SLR", "GSLRD"]
BANDS = [("<500", 0, 500), ("500–999", 500, 1000), ("1000–1499", 1000, 1500), ("1500–1999", 1500, 2000),
         ("≥2000", 2000, 10 ** 9)]
FAM_ORDER = {"ICF": 0, "LHB": 1, "DEMU Shop": 2, "TC family": 3, "Special": 4}


def esc(s):
    return str(s if s is not None else "").replace("&", "&amp;").replace("<", "&lt;")


def f(d_):
    return d_.strftime("%d/%m") if d_ else ""


def _num(v, default=0.0):
    try:
        return float(str(v).split()[0])
    except (ValueError, IndexError):
        return default


def build(D, exported, inp, wd, condemned=(), as_on=None, report_date=None):
    """-> full HTML document. D = enriched demands, exported = export datetime, inp = daily_inputs.load(),
    wd = daily_inputs.working_days(...), condemned = coach keys proposed for condemnation."""
    report_date = report_date or exported.date()
    as_on = as_on or (report_date - timedelta(days=1))
    pd_ = R.pdate
    cond = {R.coach_key({"coachNo": c}) for c in condemned}

    H = P.holding(D, as_on)
    F = P.fnd_now(D)
    fnd_ids = {x["demandId"] for x in F}
    inside = [dict(h) for h in H] + [dict(x, _loc="FND") for x in F]

    def area(d):
        pit = str(d.get("pitNum") or "").upper()
        if pit.startswith("OT/IN"):
            return "Incoming"
        line, _ = _split_pit(pit)
        shop = PREFIX_SHOP.get(line.split("/")[0]) if line else None
        return shop or "Yard"

    def corr(d):
        cc, cs = pd_(d.get("corrComp")), pd_(d.get("corrPlace"))
        if d["demandId"] in fnd_ids:
            return ""
        return f"CC {f(cc)}" if cc else (f"UC {f(cs)}" if cs else "")

    def row(d):
        rd = pd_(d.get("receivedDate"))
        hrs = R.hours(d, "preSurveyHrs")
        rem = []
        if d["demandId"] in fnd_ids:
            rem.append(f"FND {f(pd_(d.get('dispatchDate')))}")
        elif pd_(d.get("pdcDate")):
            rem.append(f"PDC {f(pd_(d.get('pdcDate')))}")
        elif pd_(d.get("corrPd")) and not pd_(d.get("corrComp")):
            rem.append(f"C-PDC {f(pd_(d.get('corrPd')))}")
        if str(d.get("repairType")) == "4":
            rem.append("OR")
        return dict(type=R.coach_type(d), no=d.get("coachNo"), div=d.get("divisionId") or "", recd=f(rd),
                    days=(as_on - rd).days if rd else None, hrs=int(hrs) if hrs else "", corr=corr(d),
                    rem="; ".join(rem), fnd=d["demandId"] in fnd_ids,
                    cc=bool(pd_(d.get("corrComp"))) and d["demandId"] not in fnd_ids,
                    cond=R.coach_key(d) in cond and d["demandId"] not in fnd_ids, fam=d["_family"])

    def coach_cell(r):
        cls = " ".join(c for c in ("fndc" if r["fnd"] else ("ccc" if r["cc"] else ""), "cond" if r["cond"] else "") if c)
        return f'<td class="c">{esc(r["type"])} <span class="{cls}">{esc(r["no"])}</span></td>'

    def days_cell(r):
        d = r["days"]
        return f'<b>{d}</b>' if d and d > 30 and not r["fnd"] else ("" if d is None else d)

    by_area = defaultdict(list)
    for d in inside:
        by_area[area(d)].append(d)

    NICE = {"WP": "Pit 2", "Wash B": "B Line", "Central": "C. Line", "DESP": "Desp. Line"}

    def nice(lab):
        lab = NICE.get(lab, lab)
        if lab[:1] == "L" and lab[1:2].isdigit():
            return "Line " + lab[1:]
        if lab[:1] == "P" and lab[1:2].isdigit():
            return "Pit " + lab[1:]
        return lab

    def shop_rows(shop):
        lines = OrderedDict((ln, []) for ln, lab, n in SHOPS[shop])
        labels = {ln: lab for ln, lab, n in SHOPS[shop]}
        for d in by_area[shop]:
            line, slot = _split_pit(d.get("pitNum"))
            line = {"DM/CLI": "DM/C"}.get(line, line)
            lines.setdefault(line, []).append((slot or 0, d))
            labels.setdefault(line, line.split("/", 1)[-1])
        out = []
        for ln, items in lines.items():
            if items:
                for slot, d in sorted(items, key=lambda x: x[0]):
                    out.append((nice(labels[ln]) + (f" /{slot}" if slot else ""), row(d)))
            else:
                out.append((nice(labels[ln]), None))
        if shop == "LBR Shed":
            out.append(("Train Lighting", None))
        if shop == "Heavy Coach Bay" and not any(lb.startswith("Desp. Line") for lb, _ in out):
            out.append(("Desp. Line", None))
        return out

    def shop_table(shop, title=None):
        occ = shop_rows(shop)
        n = sum(1 for _, r in occ if r)
        h = [f'<div class="box"><div class="bh"><b>{esc(title or shop)}</b><span>{n} coach{"es" if n != 1 else ""}</span></div>'
             '<table class="t"><tr><th>Line</th><th>Coach</th><th>Div</th><th>Recd</th><th class="r">Days</th>'
             '<th class="r">Hrs</th><th>Corr</th><th>Remarks</th></tr>']
        for ln, r in occ:
            if r is None:
                h.append(f'<tr class="emp"><td>{esc(ln)}</td><td colspan=7>–</td></tr>')
                continue
            h.append(f'<tr><td>{esc(ln)}</td>{coach_cell(r)}<td>{esc(r["div"])}</td><td>{r["recd"]}</td>'
                     f'<td class="r">{days_cell(r)}</td><td class="r">{r["hrs"]}</td><td>{r["corr"]}</td>'
                     f'<td class="rem">{esc(r["rem"])}</td></tr>')
        h.append("</table></div>")
        return "".join(h)

    def list_table(rows, title):
        h = [f'<div class="box"><div class="bh"><b>{title}</b><span>{len(rows)}</span></div>'
             '<table class="t"><tr><th>#</th><th>Coach</th><th>Div</th><th>Recd</th><th class="r">Days</th><th class="r">Hrs</th>'
             '<th>Corr</th><th>Remarks</th></tr>']
        for i, r in enumerate(rows, 1):
            h.append(f'<tr><td>{i}</td>{coach_cell(r)}<td>{esc(r["div"])}</td><td>{r["recd"]}</td>'
                     f'<td class="r">{days_cell(r)}</td><td class="r">{r["hrs"]}</td><td>{r["corr"]}</td>'
                     f'<td class="rem">{esc(r["rem"])}</td></tr>')
        h.append("</table></div>")
        return "".join(h)

    def yard_part(rows, start):
        h = ['<table class="t"><tr><th>#</th><th>Coach</th><th>Div</th><th>Recd</th><th class="r">Days</th>'
             '<th class="r">Hrs</th><th>Remarks</th></tr>']
        for i, r in enumerate(rows, start):
            h.append(f'<tr><td>{i}</td>{coach_cell(r)}<td>{esc(r["div"])}</td><td>{r["recd"]}</td>'
                     f'<td class="r">{days_cell(r)}</td><td class="r">{r["hrs"]}</td><td class="rem">{esc(r["rem"])}</td></tr>')
        h.append("</table>")
        return "".join(h)

    # ---- movements of the day and the weekly plan
    def on(d, k):
        return pd_(d.get(k)) == as_on and not R.is_excluded(d)

    out_day = sorted((d for d in D if on(d, "dispatchDate")), key=lambda d: d["_order"])
    desp_day = sorted((d for d in D if on(d, "actualDispatchDate")), key=lambda d: d["_order"])
    latest = R.latest_per_coach(D)

    def plan_status(no, pdc):
        d = latest.get(R.coach_key({"coachNo": no}))
        if not d:
            return "not found", False
        dd, ad = pd_(d.get("dispatchDate")), pd_(d.get("actualDispatchDate"))
        if R.is_excluded(d):
            return "Returned", False
        if ad:
            return f"Despatched {f(ad)}", False
        if dd:
            return f"Outturned {f(dd)} - FND", False
        p = pd_(pdc)
        if p and p <= as_on:
            return "OVERDUE", True
        return "Due", False

    # ---- statistics for page 2
    fy0 = R.fy_start(R.fy_of(as_on))
    m0 = R.month_start(as_on)
    stat = defaultdict(Counter)
    for d in D:
        if R.is_excluded(d):
            continue
        dd, ad = pd_(d.get("dispatchDate")), pd_(d.get("actualDispatchDate"))
        for k in {CAT.get(d["_group"], "OTH"), d["_group"]}:
            if dd and fy0 <= dd < m0:
                stat[k]["sep"] += 1
                stat[k]["sepd"] += bool(ad and ad <= as_on)
            if dd and fy0 <= dd <= as_on:
                stat[k]["fy"] += 1
                stat[k]["fyd"] += bool(ad and ad <= as_on)
            if dd and m0 <= dd <= as_on:
                stat[k]["m"] += 1
                stat[k]["md"] += bool(ad and ad <= as_on)
                stat[k]["cc"] += 1                       # every outturn of the month = corrosion completed
            if dd == as_on:
                stat[k]["day"] += 1
    for d in H:
        for k in {CAT.get(d["_group"], "OTH"), d["_group"]}:
            stat[k]["yard" if d["_loc"] == "Yard" else "shop"] += 1
            if pd_(d.get("corrComp")):                   # + coaches still inside with corrosion completed
                stat[k]["cc"] += 1

    slip, lhb, hb = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    for d in H:
        t = R.coach_type(d)
        loc = "Y" if d["_loc"] == "Yard" else "W"
        if d["_family"] == "ICF":
            yb, hrs = d.get("_yearBuilt"), R.hours(d, "preSurveyHrs")
            old = bool(yb) and report_date.year - int(yb) > 13
            slip[t][(("A" if (hrs or 0) > 1300 else "B") if old else "C") + loc] += 1
            hb[t]["NS" if hrs is None else next(b for b, lo, hi in BANDS if lo <= hrs < hi)] += 1
        elif R.classify(dict(d, repairType=None))[0] == "LHB":       # by coach type - OR coaches included
            lhb[t][loc] += 1
            lhb[t]["OR"] += str(d.get("repairType")) == "4"

    # ================================================================ page 1
    p1 = [f'''<div class="page"><div class="top"><div><h1>LW/PER – DAILY COACH POSITION</h1>
<div style="font-size:8.5pt">Position as on <b>{as_on:%d-%m-%Y}</b> (end of day)</div></div>
<div class="sub"><div class="lg"><span class="fndc">FND coaches</span><span class="ccc">Corr. completed</span><span class="cond">Condemnation proposed</span></div>
Report date {report_date:%d-%m-%Y} · data at {exported:%H:%M} · Page 1 of 2</div></div>''']

    ac = ['<div class="box"><div class="bh"><b>AC Loco Bay</b><span>{n} locos</span></div><table class="t">'
          '<tr><th>Line</th><th>Loco</th><th>Repair</th><th>Shed</th><th>Date</th><th class="r">Days</th></tr>']
    n_loco = 0
    for b in inp.get("ac_bay", []):
        if not (b.get("loco") or "").strip():
            ac.append(f'<tr class="emp"><td>{esc(b.get("line"))}</td><td colspan=5>–</td></tr>')
            continue
        n_loco += 1
        dt = pd_(b.get("date"))
        days = (as_on - dt).days if dt else ""
        dd = f"<b>{days}</b>" if days != "" and days > 30 else days
        ac.append(f'<tr><td>{esc(b.get("line"))}</td><td class="c">{esc(b.get("type"))} {esc(b.get("loco"))}</td>'
                  f'<td>{esc(b.get("repair"))}</td><td>{esc(b.get("shed"))}</td><td>{f(dt)}</td><td class="r">{dd}</td></tr>')
    ac.append("</table></div>")
    ac[0] = ac[0].replace("{n}", str(n_loco))

    inc_rows = sorted((row(d) for d in by_area["Incoming"]), key=lambda r: (r["type"], -(r["days"] or 0)))
    p1 += ['<div class="grid2"><div class="col">', shop_table("Paint Shop"), list_table(inc_rows, "Incoming (OT/IN)"),
           shop_table("DEMU Shop"), shop_table("Heavy Coach Bay", "Heavy Corrosion Bay"), '</div><div class="col">',
           shop_table("LBR Shed"), shop_table("Augmentation Shop"), shop_table("Light Coach Bay", "Light Corrosion Bay"),
           "".join(ac), '</div></div>']

    yard_rows = sorted((row(d) for d in by_area["Yard"]),
                       key=lambda r: (FAM_ORDER.get(r["fam"], 9), r["type"], -(r["days"] or 0)))
    ncol = 2 if len(yard_rows) <= 30 else 3
    per = max(1, -(-len(yard_rows) // ncol))
    cols = "".join(f'<div style="{"border-right:1px solid #000" if c < ncol - 1 else ""}">'
                   f'{yard_part(yard_rows[c * per:(c + 1) * per], c * per + 1)}</div>' for c in range(ncol))
    p1.append(f'<div class="box" style="margin-top:5px"><div class="bh"><b>Yard (OT/YD)</b><span>{len(yard_rows)} coaches</span></div>'
              f'<div style="display:grid;grid-template-columns:repeat({ncol},minmax(0,1fr))">{cols}</div></div>')

    key_t = lambda x: ORDER.index(x) if x in ORDER else 99
    o_txt = ", ".join(f"{R.coach_type(d)} {d['coachNo']}" for d in out_day) or "nil"
    d_txt = ", ".join(f"{R.coach_type(d)} {d['coachNo']}" for d in desp_day) or "nil"
    cond_in = [h for h in H if R.coach_key(h) in cond]
    by_t = Counter(R.coach_type(h) for h in cond_in)
    cond_txt = (f' ({", ".join(f"{t} {n}" for t, n in sorted(by_t.items(), key=lambda x: (key_t(x[0]), x[0])))})' if cond_in else "")
    p1.append(f'<div class="mv"><b>Outturn {as_on:%d/%m} ({len(out_day)}):</b> {o_txt} &nbsp;&nbsp; '
              f'<b>Physical despatch ({len(desp_day)}):</b> {d_txt}<br>'
              f'<b>Holding {len(H)}</b> &nbsp;·&nbsp; <span class="cond">Proposed for condemnation</span> <b>{len(cond_in)}</b>{cond_txt}'
              f' &nbsp;·&nbsp; <b>Balance holding {len(H) - len(cond_in)}</b></div>')

    plan = [p for p in inp.get("plan", []) if (p.get("coach") or "").strip()]

    def plan_part(rows, start):
        h = ['<table class="t"><tr><th>#</th><th>Coach</th><th>Corr PDC</th><th>Desp PDC</th><th>Status</th></tr>']
        for i, p in enumerate(rows, start):
            s, ov = plan_status(p["coach"].split()[-1], p.get("desp_pdc"))
            h.append(f'<tr><td>{i}</td><td class="c">{esc(p["coach"])}</td><td>{f(pd_(p.get("corr_pdc")))}</td>'
                     f'<td>{f(pd_(p.get("desp_pdc")))}</td><td{" class=ov" if ov else ""}>{s}</td></tr>')
        h.append("</table>")
        return "".join(h)

    if plan:
        ph = (len(plan) + 1) // 2
        p1.append(f'<div class="box"><div class="bh"><b>Weekly plan (despatch PDC)</b><span>{len(plan)} coaches</span></div>'
                  f'<div class="grid2" style="gap:0"><div style="border-right:1px solid #000">{plan_part(plan[:ph], 1)}</div>'
                  f'<div>{plan_part(plan[ph:], ph + 1)}</div></div></div>')

    s1 = ['<table class="p s"><tr><th rowspan=2 style="text-align:left">ICF</th><th colspan=3>&gt;13 yrs &amp; &gt;1300 hrs</th>'
          '<th colspan=3>&gt;13 yrs &amp; ≤1300 hrs</th><th colspan=3>≤13 yrs</th><th rowspan=2>Total</th></tr>'
          '<tr>' + "<th>Y</th><th>W</th><th>T</th>" * 3 + '</tr>']
    tt = Counter()
    for t in sorted(slip, key=key_t):
        c, cells = slip[t], []
        for k in "ABC":
            y, w = c[k + "Y"], c[k + "W"]
            tt[k + "Y"] += y
            tt[k + "W"] += w
            cells.append(f"<td>{y}</td><td>{w}</td><td><b>{y + w}</b></td>")
        s1.append(f'<tr><td class="l">{t}</td>{"".join(cells)}<td><b>{sum(c.values())}</b></td></tr>')
    s1.append('<tr class="tot"><td class="l">Total</td>' + "".join(
        f"<td>{tt[k + 'Y']}</td><td>{tt[k + 'W']}</td><td>{tt[k + 'Y'] + tt[k + 'W']}</td>" for k in "ABC")
        + f"<td>{sum(tt.values())}</td></tr></table>")
    s2 = ['<table class="p s"><tr><th style="text-align:left">ICF – pre-survey hrs</th>'
          + "".join(f"<th>{b}</th>" for b, _, _ in BANDS) + '<th>No<br>hrs</th><th>Total</th></tr>']
    ht = Counter()
    for t in sorted(hb, key=key_t):
        c = hb[t]
        ht.update(c)
        s2.append(f'<tr><td class="l">{t}</td>' + "".join(f"<td>{c[b] or ''}</td>" for b, _, _ in BANDS)
                  + f'<td>{c["NS"] or ""}</td><td><b>{sum(c.values())}</b></td></tr>')
    s2.append('<tr class="tot"><td class="l">Total</td>' + "".join(f"<td>{ht[b]}</td>" for b, _, _ in BANDS)
              + f'<td>{ht["NS"]}</td><td>{sum(ht.values())}</td></tr></table>')
    s3 = ['<table class="p s lhb"><tr><th style="text-align:left">LHB</th><th>Yard</th><th>Work</th><th>Total</th><th>of which OR</th></tr>']
    lt = Counter()
    for t in sorted(lhb):
        c = lhb[t]
        lt.update({"Y": c["Y"], "W": c["W"], "OR": c["OR"]})
        s3.append(f'<tr><td class="l">{t}</td><td>{c["Y"]}</td><td>{c["W"]}</td><td><b>{c["Y"] + c["W"]}</b></td><td>{c["OR"] or ""}</td></tr>')
    s3.append(f'<tr class="tot"><td class="l">Total</td><td>{lt["Y"]}</td><td>{lt["W"]}</td><td>{lt["Y"] + lt["W"]}</td><td>{lt["OR"]}</td></tr></table>')
    p1.append('<div class="strip"><div>' + "".join(s1) + '</div><div>' + "".join(s2) + '</div><div>' + "".join(s3) + '</div></div>')
    p1.append('</div>')

    # ================================================================ page 2 (original format)
    pm = wd["month_completed"] / wd["month_total"] if wd["month_total"] else 0
    py = wd["year_completed"] / wd["year_total"] if wd["year_total"] else 0
    MON = f"{as_on:%b}-{as_on:%y}"
    PREV = f"{m0 - timedelta(days=1):%b - %y}"
    T = inp.get("targets", {})

    def tg(k, field, default=""):
        return (T.get(k) or {}).get(field, default)

    def od(k, a="fy", b="fyd"):
        return f"{stat[k][a]}/{stat[k][b]}"

    def hold(k):
        return stat[k]["yard"] + stat[k]["shop"]

    def splits(parts, a, b):
        if not any(stat[g][a] or stat[g][b] for _, g in parts):
            return "0"
        return " ".join(f"{lab}-{stat[g][a]}/{stat[g][b]}" for lab, g in parts)

    def sumk(keys, fld):
        return sum(stat[k][fld] for k in keys)

    rows = []

    def add(key, label, sep, todate, mon, day, hld, cc, rb_rowspan=1, skip_rb=False):
        hq = _num(tg(key, "hq", 0))
        basis = _num(tg(key, "basis", 0))
        rows.append(dict(label=label, rb=tg(key, "rb", "-") or "-", prop=(f"{basis * py:.2f}" if basis else "-"),
                         sep=sep, todate=todate, hq=f"{hq:g}", mprop=f"{hq * pm:.2f}" if hq else "0", mon=mon, day=day,
                         hold=hld, cc=cc, rb_rowspan=rb_rowspan, skip_rb=skip_rb))

    MEMU = [("TC", "MEMU TC"), ("MC", "MEMU MC")]
    EMU = [("MC", "EMU MC"), ("TC", "EMU TC")]
    DEMUp = [("DPC", "DEMU DPC"), ("TC", "DEMU TC")]
    emu_k, memu_k = ["EMU MC", "EMU TC"], ["MEMU MC", "MEMU TC"]
    add("ICF", "ICF NAC Coach POH", od("ICF", "sep", "sepd"), od("ICF"), od("ICF", "m", "md"), stat["ICF"]["day"], hold("ICF"), stat["ICF"]["cc"])
    add("NMG", "ICF - NMG POH/Conv",
        f'{stat["NMG"]["sep"]}/{stat["NMG"]["sepd"]} ({stat["NMG POH"]["sep"]:02d}NMGHS POH+{stat["NMG CONVERSION"]["sep"]:02d}NMGHS Conv)',
        od("NMG"), od("NMG", "m", "md"), stat["NMG"]["day"], hold("NMG"), stat["NMG"]["cc"])
    add("ARTC", "ARMV/Conv", od("ARTC", "sep", "sepd"), od("ARTC"), od("ARTC", "m", "md"), stat["ARTC"]["day"],
        f'{hold("ARTC")} ARMV/Conv' if hold("ARTC") else 0, stat["ARTC"]["cc"])
    add("LHBN", "LHB NAC POH", od("LHBN", "sep", "sepd"), od("LHBN"), od("LHBN", "m", "md"), stat["LHBN"]["day"], hold("LHBN"), stat["LHBN"]["cc"])
    add("LHBA", "LHB AC POH", od("LHBA", "sep", "sepd"), od("LHBA"), od("LHBA", "m", "md"), stat["LHBA"]["day"], hold("LHBA"), stat["LHBA"]["cc"])
    add("EMUONLY", "EMU", splits(EMU, "sep", "sepd"), splits(EMU, "fy", "fyd"), splits(EMU, "m", "md"),
        sumk(emu_k, "day"), f'{hold("EMU MC")}MC+{hold("EMU TC")}TC', sumk(emu_k, "cc"), rb_rowspan=2)
    rows[-1].update(rb=tg("EMU", "rb", "-"), prop=f'{_num(tg("EMU", "basis", 0)) * py:.2f}' if _num(tg("EMU", "basis", 0)) else "-")
    add("EMU", "MEMU DMC/TC-POH", f'{sumk(memu_k, "sep")}/{sumk(memu_k, "sepd")} ({splits(MEMU, "sep", "sepd")})',
        f'{sumk(memu_k, "fy")}/{sumk(memu_k, "fyd")} ({splits(MEMU, "fy", "fyd")})',
        splits([("MC", "MEMU MC"), ("TC", "MEMU TC")], "m", "md"), sumk(memu_k, "day"),
        f'{hold("MEMU MC")} MC+{hold("MEMU TC")}TC', sumk(memu_k, "cc"), skip_rb=True)
    add("DEMU", "DEMU DPC/TC", f'{stat["DEMU"]["sep"]}/{stat["DEMU"]["sepd"]} ({splits(DEMUp, "sep", "sepd")})',
        f'{stat["DEMU"]["fy"]}/{stat["DEMU"]["fyd"]} ({splits(DEMUp, "fy", "fyd")})', splits(DEMUp, "m", "md"),
        " ".join(f'{stat[g]["day"]}{lab}' for lab, g in DEMUp if stat[g]["day"]) or 0,
        f'{hold("DEMU DPC")}DPC+{hold("DEMU TC")} TC', stat["DEMU"]["cc"])
    add("SPART", "SPART/Spic SWR/POH", od("SPART", "sep", "sepd"), od("SPART"), od("SPART", "m", "md"), stat["SPART"]["day"], hold("SPART"), stat["SPART"]["cc"])
    add("TW4", "TW -4W", od("TW4", "sep", "sepd"), od("TW4"), od("TW4", "m", "md"),
        f'{stat["TW4"]["day"]} TW 4W' if stat["TW4"]["day"] else 0, hold("TW4"), stat["TW4"]["cc"])
    add("TW8", "TW -8W", od("TW8", "sep", "sepd"), od("TW8"), od("TW8", "m", "md"), stat["TW8"]["day"], hold("TW8"), stat["TW8"]["cc"])
    or_lhb = sum(1 for d in H if str(d.get("repairType")) == "4" and R.classify(dict(d, repairType=None))[0] == "LHB")
    add("OR", "OR", od("OR", "sep", "sepd"), od("OR"), od("OR", "m", "md"), stat["OR"]["day"],
        f'{hold("OR")} (OR){" LHB" if or_lhb and or_lhb == hold("OR") else ""}', stat["OR"]["cc"])

    KEYS = ["ICF", "NMG", "ARTC", "LHBN", "LHBA", "EMU", "DEMU", "SPART", "TW4", "TW8", "OR"]
    tot = {k2: sum(stat[k][k2] for k in KEYS) for k2 in ("sep", "sepd", "fy", "fyd", "m", "md", "day", "cc")}
    tot_hold = sum(hold(k) for k in KEYS)
    basis_total = sum(_num(tg(k, "basis", 0)) for k in KEYS)
    hq_total = sum(_num(tg(k, "hq", 0)) for k in KEYS + ["EMUONLY"])

    def red(v):
        return f'<span class="red">{v}</span>'

    p2 = [f'''<div class="page p2"><div class="ttl">Daily Position as on - {report_date:%d/%m/%Y}</div>
<table class="o"><tr><td rowspan=4 class="b" style="width:30%">No of Working Days</td><td rowspan=2 class="b">For the Month</td>
<th>Available</th><th>Completed</th><th>Total</th></tr>
<tr><td>{wd["month_total"] - wd["month_completed"]:g}</td><td>{wd["month_completed"]:g}</td><td>{wd["month_total"]:g}</td></tr>
<tr><td rowspan=2 class="b">For the Year</td><th>Available</th><th>Completed</th><th>Total</th></tr>
<tr><td>{wd["year_total"] - wd["year_completed"]:g}</td><td>{wd["year_completed"]:g}</td><td>{wd["year_total"]:g}</td></tr></table>
<table class="o main"><tr><th>Activities</th><th>Yearly RB Target {R.fy_of(as_on)}</th><th>Prop target till date</th>
<th>Cumulative Out turn/Desp upto {PREV}</th><th>Out turn till date/ Desp</th><th>Monthly HQ Target {MON}</th>
<th>Proportionate target till Date {MON}</th><th>Out turn till date {as_on:%b}/ Desp</th><th>Out turn on last working day</th>
<th>Holding as on date</th><th>CORR COMPL</th></tr>''']
    for r in rows:
        rs = " rowspan=2" if r["rb_rowspan"] == 2 else ""
        rb = "" if r["skip_rb"] else f'<td class="b"{rs}>{esc(r["rb"])}</td>'
        prop = "" if r["skip_rb"] else f'<td{rs}>{red(r["prop"]) if r["prop"] != "-" else "-"}</td>'
        p2.append(f'<tr><td class="l b">{r["label"]}</td>{rb}{prop}<td>{r["sep"]}</td><td>{red(r["todate"])}</td>'
                  f'<td class="b">{r["hq"]}</td><td>{r["mprop"]}</td><td>{red(r["mon"])}</td><td class="b">{r["day"]}</td>'
                  f'<td class="b">{r["hold"]}</td><td>{r["cc"] or ""}</td></tr>')
    p2.append(f'<tr class="tot"><td class="l">Total</td><td>{esc(inp.get("rb_total_text", ""))}</td><td>{red(f"{basis_total * py:.2f}")}</td>'
              f'<td>{tot["sep"]}/{tot["sepd"]}</td><td>{red(str(tot["fy"]) + "/" + str(tot["fyd"]))}</td><td>{hq_total:g}</td>'
              f'<td>{hq_total * pm:.2f}</td><td>{red(str(tot["m"]) + "/" + str(tot["md"]))}</td><td>{tot["day"]}</td>'
              f'<td>{tot_hold}</td><td>{tot["cc"]}</td></tr>')
    for t in inp.get("typed", []):
        if not (t.get("label") or "").strip():
            continue
        v = [esc(t.get(k, "")) for k in ("rb", "prop", "sep", "todate", "hq", "mprop", "mon", "day", "hold")]
        p2.append(f'<tr class="ty"><td class="l">{esc(t["label"])}</td><td>{v[0]}</td><td>{red(v[1]) if v[1] not in ("", "-") else v[1]}</td>'
                  f'<td class="b">{v[2]}</td><td>{red(v[3])}</td><td>{v[4]}</td><td>{v[5]}</td><td>{red(v[6])}</td>'
                  f'<td class="b">{v[7]}</td><td>{v[8]}</td><td></td></tr>')
    p2.append('</table>')
    nm = inp.get("nmghs") or {}
    if any(str(nm.get(k, "")).strip() for k in ("balance", "actual", "to_achieve")):
        p2.append(f'<table class="o nm"><tr><td class="b">NMGHS Conv.</td><td>{esc(nm.get("label", "Balance Target"))}</td>'
                  '<td colspan=2>Cumulative Actuals upto till date</td><td colspan=2>Balance to achieve target</td></tr>'
                  f'<tr><td class="b">NMGHS Conv.</td><td>{esc(nm.get("balance"))}</td><td colspan=2>{esc(nm.get("actual"))}</td>'
                  f'<td colspan=2>{esc(nm.get("to_achieve"))}</td></tr></table>')
    notes = [ln for ln in (inp.get("notes") or "").splitlines() if ln.strip()]
    if notes:
        p2.append('<div class="fn">' + "<br>".join(esc(n) for n in notes) + '</div>')
    p2.append('</div>')

    return (f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>DailyPosition{report_date:%d%m%Y}</title>"
            f"<style>{CSS}</style></head><body><div class='noprint bar'><button onclick='window.print()'>Print / Save as PDF</button> "
            f"<a href='/daily'>Back to the form</a> <span>In the print box choose “Save as PDF”, A4, margins default.</span></div>"
            f"{''.join(p1)}{''.join(p2)}{FIT_JS}</body></html>")


FIT_JS = """<script>
(function(){const MM=96/25.4, H=279*MM-6;
 function fit(){document.body.classList.add('measure');document.querySelectorAll('.page').forEach(pg=>{pg.style.zoom=1;
   const h=pg.getBoundingClientRect().height;if(h>H){pg.style.zoom=(H/h).toFixed(3);}});document.body.classList.remove('measure');}
 window.addEventListener('beforeprint',fit);window.addEventListener('load',fit);})();
</script>"""

CSS = """
@page { size: A4; margin: 9mm; }
* { box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 7.3pt; color: #000; margin: 0; background: #fff; }
@media screen { body { width: 192mm; margin: 10px auto; } .page { border-bottom: 1px dashed #999; padding-bottom: 8px; margin-bottom: 14px; } }
@media print { .noprint { display: none !important; } }
.bar { font-size: 10pt; padding: 6px 0 10px; } .bar button { font-size: 11pt; padding: 5px 14px; margin-right: 10px; cursor: pointer; }
.bar span { color: #555; font-size: 9pt; margin-left: 10px; }
.page { page-break-after: always; width: 99.5%; }
.page:last-child { page-break-after: auto; }
.top { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #000; padding-bottom: 3px; margin-bottom: 5px; }
.top h1 { font-size: 12pt; margin: 0; letter-spacing: .3px; }
.top .sub { font-size: 8pt; text-align: right; line-height: 1.35; }
.grid2 { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 5px; align-items: start; }
.col { display: flex; flex-direction: column; gap: 5px; }
.box { border: 1px solid #000; overflow: hidden; }
.bh { display: flex; justify-content: space-between; background: #e6e6e6; padding: 1.5px 4px; border-bottom: 1px solid #000; font-size: 8pt; }
table.t { width: 100%; border-collapse: collapse; }
table.t th { font-size: 6.6pt; text-align: left; font-weight: bold; border-bottom: 1px solid #000; padding: 1px 3px; }
tr.emp td { color: #555; font-size: 6.4pt; padding-top: 0 !important; padding-bottom: 0 !important; }
table.t td { padding: 0.6px 3px; border-bottom: 0.5px solid #bbb; vertical-align: top; white-space: nowrap; }
table.t td.rem { font-size: 6.4pt; white-space: normal; line-height: 1.05; }
table.t td.c { font-weight: bold; }
.r { text-align: right; }
span.fndc { background: #8fe000; padding: 0 2px; }
span.ccc { background: #ffff00; padding: 0 2px; }
span.cond { text-decoration: underline; text-decoration-color: #e00000; text-decoration-thickness: 2px; text-underline-offset: 2px; }
.mv { border: 1px solid #000; padding: 2px 5px; margin: 5px 0; line-height: 1.4; }
.ov { font-weight: bold; text-decoration: underline; }
.lg { margin-bottom: 3px; } .lg span { display: inline-block; font-weight: bold; font-size: 7.5pt; padding: 2px 8px; margin-left: 6px; border: 0.6px solid #000; }
.lg span.fndc { background: #8fe000; } .lg span.ccc { background: #ffff00; } .lg span.cond { background: #fff; }
.lg2 { font-size: 6.6pt; margin-top: 3px; }
table.p { width: 100%; border-collapse: collapse; font-size: 7.4pt; }
table.p th, table.p td { border: 0.6px solid #000; padding: 2px 3px; }
table.p th { background: #e6e6e6; font-size: 6.8pt; text-align: center; vertical-align: bottom; }
table.p td { text-align: right; }
table.p td.l { text-align: left; }
table.p tr.tot td { font-weight: bold; border-top: 1.5px solid #000; }
.strip { display: grid; grid-template-columns: 1.15fr 1.1fr 0.75fr; gap: 5px; margin-top: 5px; align-items: start; }
table.p.s { font-size: 6.8pt; table-layout: fixed; }
table.p.s td:first-child, table.p.s th:first-child { width: 17%; }
table.p.s.lhb td:first-child, table.p.s.lhb th:first-child { width: 32%; }
table.p.s th, table.p.s td { padding: 1px 2px; }
.p2 { font-size: 9pt; }
.p2 .ttl { text-align: center; font-weight: bold; font-size: 11pt; margin: 3mm 0 4mm; }
table.o { width: 99.5%; border-collapse: collapse; margin-bottom: 4mm; table-layout: fixed; }
table.o.main th:nth-child(1) { width: 12%; } table.o.main th:nth-child(4) { width: 13%; } table.o.main th:nth-child(5) { width: 9%; }
table.o.main th:nth-child(8) { width: 9%; } table.o.main th:nth-child(10) { width: 11%; }
table.o th, table.o td { border: 0.8px solid #000; padding: 4px 3px; overflow-wrap: anywhere; text-align: center; vertical-align: middle; }
table.o th { font-weight: bold; font-size: 8.2pt; }
table.o td.l { text-align: left; }
table.o .b, table.o tr.tot td { font-weight: bold; }
.red { color: #d00000; font-weight: bold; }
.fn { font-size: 8.5pt; margin-top: 3mm; line-height: 1.5; }
"""
