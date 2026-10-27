"""
updaters/achieved.py - fill the "Achieved" column from ERP in OUR sheet POSITION11092026 (JIJO 27-10-2026:
targets are typed by JIJO, achievement comes from ERP automatically).

  Internal_Targets  col "Achieved"                     = ERP outturn of that coach type / month (same rule as the app)
  HQ_Targets        col "Achieved"                     = ERP outturn of that stock type / month
  RB_Targets        col "Achieved (ERP, FY to date)"   = ERP outturn of that stock type, FY to date (column added once)

Only months up to the ERP date of the current FY. Rows ERP cannot count (ICF IOH, LHB SS1, Vande Bharat,
AC / Electric loco) are left exactly as typed. Only cells whose value changes are written.
"""
from datetime import date

from core import rules as R
from analysis import perf, stock_targets as S

RB_COL = "Achieved (ERP, FY to date)"


def _col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _dicts(vals):
    head = [h.strip() for h in vals[0]] if vals else []
    return head, [(i + 2, dict(zip(head, [str(x) for x in r]))) for i, r in enumerate(vals[1:]) if any(str(x).strip() for x in r)]


def _same(old, new):
    o = (old or "").strip()
    try:
        return float(o) == float(new)
    except ValueError:
        return False


def plan(sh, demands, as_on):
    fy = R.fy_of(as_on)
    ws = {t: sh.worksheet(t) for t in ("Internal_Targets", "HQ_Targets", "RB_Targets")}
    vals = {t: w.get_all_values() for t, w in ws.items()}
    changes = {t: [] for t in ws}                     # (a1, old, new, label)

    # ---- Internal
    head, rows = _dicts(vals["Internal_Targets"])
    ach = head.index("Achieved") + 1 if "Achieved" in head else None
    parsed = []
    for rn, r in rows:
        try:
            m = perf._parse_month(r.get("Month"))
        except (ValueError, IndexError):
            continue
        t = (r.get("Internal Target") or "").strip()
        parsed.append(dict(rn=rn, fy=r.get("FY", "").strip(), month=m, type=(r.get("Coach Type") or "").strip().upper(),
                           target=int(float(t)) if t.replace(".", "", 1).isdigit() else None,
                           stock=(r.get("Stock Type") or "").strip().upper(), nac=(r.get("NAC/AC") or "").strip().upper(),
                           old=r.get("Achieved", "")))
    tva = perf.targets_vs_actual(demands, fy, as_on, parsed)
    by_spec = {row["spec"]: row for row in tva["rows"]}
    mkeys = [(m.year, m.month) for m in tva["months"]]
    if ach:
        for p in parsed:
            if p["fy"] != fy or (p["month"].year, p["month"].month) not in mkeys or not p["type"]:
                continue
            row = by_spec.get(perf.target_spec(p["type"]))
            if not row:
                continue
            a = row["cells"][mkeys.index((p["month"].year, p["month"].month))]["a"]
            if not _same(p["old"], a):
                changes["Internal_Targets"].append((f"{_col(ach)}{p['rn']}", p["old"], a, f"{p['month']:%b-%y} {p['type']}"))

    # ---- HQ + RB (stock type)
    hhead, hrows = _dicts(vals["HQ_Targets"])
    rhead, rrows = _dicts(vals["RB_Targets"])
    st = S.build(demands, fy, as_on, [r for _, r in hrows], [r for _, r in rrows], parsed)
    cat = {r["key"]: r for r in st["rows"]}
    smonths = [(m.year, m.month) for m in st["months"]]
    hach = hhead.index("Achieved") + 1 if "Achieved" in hhead else None
    if hach:
        for rn, r in hrows:
            if r.get("FY", "").strip() != fy:
                continue
            key = S._key(r.get("Stock Type", ""), r.get("Schedule", ""), r.get("NAC/AC", ""))
            c = cat.get(key)
            try:
                m = S._month(fy, r.get("Month", ""))
            except (ValueError, IndexError):
                continue
            if not c or not c["in_erp"] or (m.year, m.month) not in smonths:
                continue
            a = c["cells"][smonths.index((m.year, m.month))]["a"]
            if not _same(r.get("Achieved"), a):
                changes["HQ_Targets"].append((f"{_col(hach)}{rn}", r.get("Achieved", ""), a, f"{m:%b-%y} {c['label']}"))
    rcol = rhead.index(RB_COL) + 1 if RB_COL in rhead else len(rhead) + 1
    add_header = RB_COL not in rhead
    for rn, r in rrows:
        if r.get("FY", "").strip() != fy:
            continue
        key = S._key(r.get("Stock Type", ""), r.get("Schedule", ""), r.get("NAC/AC", ""))
        c = cat.get(S.RB_ALIAS.get(key, key))
        if not c or not c["in_erp"]:
            continue
        if not _same(r.get(RB_COL), c["a_all"]):
            changes["RB_Targets"].append((f"{_col(rcol)}{rn}", r.get(RB_COL, ""), c["a_all"], c["label"]))
    if add_header and changes["RB_Targets"]:
        changes["RB_Targets"].insert(0, (f"{_col(rcol)}1", "", RB_COL, "header"))
    return dict(ws=ws, changes=changes)


def preview_lines(p):
    out = []
    for t, ch in p["changes"].items():
        out.append(f"    {t:17} {len(ch):3} cells")
        for a1, old, new, lab in ch[:6]:
            out.append(f"        {a1:6} {lab:32} {old or '(blank)':>8} -> {new}")
        if len(ch) > 6:
            out.append(f"        ... {len(ch) - 6} more")
    return out


def apply(p, log):
    for t, ch in p["changes"].items():
        if not ch:
            continue
        w = p["ws"][t]
        w.batch_update([{"range": a1, "values": [[new]]} for a1, _, new, _ in ch], value_input_option="USER_ENTERED")
        back = w.batch_get([a1 for a1, *_ in ch])
        ok = all((str(b[0][0]) if b and b[0] else "") == str(new) for b, (_, _, new, _) in zip(back, ch))
        log(f"  {t}: {len(ch)} Achieved cells - {'verified' if ok else 'CHECK: read-back differs'}")
        if not ok:
            raise RuntimeError(f"{t}: Achieved read-back differs - stopped")
