"""
core/physical.py - PHYSICAL despatch from JIJO's "HQ OUT TURN" sheet (JIJO 10-11-2026).

Why: ERP actualDispatchDate is only SHOP OUT. A coach then stays inside for cleaning, VG and RPF gate-out.
The real physical despatch is in the despatch block of the newest date-named tab of HQ OUT TURN
(cols Desp / SHOP Desp / V G Desp / physical Despatch date / RFD-FND), kept by JIJO.

Rule (only for coaches listed in that block - ICF, ARMV/NMG and LHB; everything else stays on ERP):
  status DESP      -> physically despatched on the 'physical Despatch date' (fallback: V G Desp, then ERP shop out)
  status FND / RFD -> still physically inside (FND), even if ERP already has an actual despatch date
A coach not in the block keeps ERP's actualDispatchDate.

The sheet is READ ONLY (never written). refresh() saves the parsed block to data/hq_outturn.json;
apply() overlays it on the demands loaded by core.data: actualDispatchDate is replaced, the ERP value is kept
in _shopOut, the HQ status in _hqStatus. So every page / updater that uses actualDispatchDate
(FND, Despatched tab, planner, HQ PDC, Daily Position, flash) follows the HQ sheet without its own code.
"""
import csv
import io
import json
import os
import re
from datetime import date, datetime, timedelta

import config

SHEET_KEY = "1sW8Hp1r6dOh_IQeeJoUWk-KRcYQFwxVW-xXNKBwR1xo"   # HQ OUT TURN - READ ONLY
GID = "805890148"                                            # the daily date-named tab (renamed daily, same id)
FILE = os.path.join(config.APP_DIR, "data", "hq_outturn.json")
STATUSES = ("DESP", "FND", "RFD")


def key(c):
    """Digits only, no leading zeros: 'XA076358' / ';096409' / '096409' -> '96409'-style key."""
    return re.sub(r"\D", "", str(c or "")).lstrip("0")


# ------------------------------------------------------------------ read the sheet
def _download(gid=GID):
    import urllib.request
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_KEY}/export?format=csv" + (f"&gid={gid}" if gid else "")
    return urllib.request.urlopen(url, timeout=30).read().decode("utf-8")


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().upper()


def parse(text):
    """CSV of the date tab -> list of rows dict(coach, key, type, base, recd, desp, shop, vg, phys, status)."""
    rows = list(csv.reader(io.StringIO(text)))
    out, cols = [], None
    for r in rows:
        u = [_norm(c) for c in r]
        st_col = next((j for j, c in enumerate(u) if re.fullmatch(r"RFD ?/ ?FND", c)), None)
        if st_col is not None and any(c.startswith("COACH NO") for c in u[:st_col]):
            # header row of a despatch block: map names in the 10 cells left of RFD/FND
            lo = max(0, st_col - 9)
            name = {j: u[j] for j in range(lo, st_col + 1)}
            pick = lambda f: next((j for j, c in name.items() if f(c)), None)          # noqa: E731
            cols = dict(type=pick(lambda c: c.startswith("TYPE")), coach=pick(lambda c: c.startswith("COACH NO")),
                        base=pick(lambda c: c == "BASE"), recd=pick(lambda c: c.startswith("RECD")),
                        desp=pick(lambda c: c == "DESP"), shop=pick(lambda c: c.startswith("SHOP")),
                        vg=pick(lambda c: c.startswith("V G") or c.startswith("VG")),
                        phys=pick(lambda c: c.startswith("PHYSICAL")), status=st_col)
            continue
        if not cols:
            continue
        g = lambda f: (r[cols[f]].strip() if cols.get(f) is not None and cols[f] < len(r) else "")   # noqa: E731
        k = key(g("coach"))
        if len(k) < 4:                                  # blank / summary rows
            continue
        out.append(dict(coach=g("coach").strip(" ;,.'"), key=k, type=g("type"), base=g("base"), recd=g("recd"),
                        desp=g("desp"), shop=g("shop"), vg=g("vg"), phys=g("phys"), status=_norm(g("status"))))
    return out


def refresh(log=print):
    """Read HQ OUT TURN (read only) -> data/hq_outturn.json. Returns (payload, error text or '')."""
    err = ""
    rows = []
    for gid in (GID, None):                             # the daily tab by id; else the first tab (date tab is first)
        try:
            rows = parse(_download(gid))
            if rows:
                break
        except Exception as e:                          # noqa: BLE001
            err = f"HQ OUT TURN not read ({e})"
    if not rows:
        return load(), err or "HQ OUT TURN: no despatch rows found"
    payload = {"read_at": f"{datetime.now():%Y-%m-%d %H:%M}", "rows": rows}
    try:
        os.makedirs(os.path.dirname(FILE), exist_ok=True)
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1)
    except OSError as e:
        err = f"hq_outturn.json not saved ({e})"
    return payload, err


def load():
    try:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                   # noqa: BLE001
        return None


def mtime():
    try:
        return os.path.getmtime(FILE)
    except OSError:
        return None


# ------------------------------------------------------------------ dates (sheet mixes d/m/y and m/d/y)
def _cands(s):
    s = str(s or "").strip().replace(".", "/").replace("-", "/")
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if not m:
        return []
    a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    y += 2000 if y < 100 else 0
    out = []
    for dd, mm in ((a, b), (b, a)):                     # d/m first (Indian), then m/d
        try:
            out.append(date(y, mm, dd))
        except ValueError:
            pass
    return out


def pdate(s, lo=None, hi=None):
    """Sheet date -> date inside [lo, hi] (d/m preferred), else None."""
    for c in _cands(s):
        if (lo is None or c >= lo) and (hi is None or c <= hi):
            return c
    return None


# ------------------------------------------------------------------ overlay on the ERP demands
def apply(demands, payload=None, as_on=None):
    """Overlay HQ physical despatch on the latest visit of each listed coach. Returns list of CHECK lines."""
    from core import rules as R
    payload = payload if payload is not None else load()
    if not payload or not payload.get("rows"):
        return []
    as_on = as_on or date.today()
    latest = {}
    for d in R.latest_per_coach(demands).values():
        latest[key(d.get("coachNo"))] = d
    checks, seen = [], set()
    for h in payload["rows"]:
        k, st = h["key"], h["status"]
        if k in seen:
            continue
        seen.add(k)
        d = latest.get(k)
        if d is not None and "_hqStatus" in d:           # already applied (e.g. core.data, then position tabs)
            continue
        if d is None:
            checks.append(f"{h['coach']} {h['type']}: in HQ OUT TURN ({st or 'no status'}) but not in ERP")
            continue
        out = R.pdate(d.get("dispatchDate"))
        if not out or R.is_excluded(d):
            checks.append(f"{h['coach']} {h['type']}: in HQ OUT TURN ({st}) but ERP latest visit not outturned")
            continue
        if st not in STATUSES:
            checks.append(f"{h['coach']}: HQ status '{st}' not RFD/FND/DESP - ERP kept")
            continue
        shop = R.pdate(d.get("actualDispatchDate"))
        d["_shopOut"] = d.get("actualDispatchDate")
        d["_hqStatus"] = st
        if st == "DESP":
            hi = as_on + timedelta(days=1)
            pd_ = pdate(h["phys"], out, hi) or pdate(h["vg"], out, hi)
            if not pd_:
                pd_ = shop or as_on
                checks.append(f"{h['coach']}: HQ DESP but physical date '{h['phys']}' not readable - "
                              f"{pd_:%d/%m/%Y} used")
            d["actualDispatchDate"] = pd_.isoformat()
            if not shop:
                checks.append(f"{h['coach']}: HQ DESP {pd_:%d/%m} but ERP has no actual despatch (shop out) date")
        else:
            d["actualDispatchDate"] = None              # RFD / FND -> still inside
    # ERP physical FND (no shop out) of ICF / LHB that HQ does not list - for information
    for k, d in latest.items():
        if k in seen or d.get("_family") not in ("ICF", "LHB"):
            continue
        if R.is_fnd(d):
            checks.append(f"{d.get('coachNo')} {R.coach_type(d)}: FND in ERP but not in HQ OUT TURN")
    return checks


def summary(demands):
    """Small text block for previews: counts by HQ status of the overlaid coaches."""
    n = {"DESP": 0, "FND": 0, "RFD": 0}
    shop_only = []
    for d in demands:
        st = d.get("_hqStatus")
        if st in n:
            n[st] += 1
            if st != "DESP" and d.get("_shopOut"):
                shop_only.append(str(d.get("coachNo")))
    return n, sorted(set(shop_only))


# ------------------------------------------------------------------ shop view vs physical view (JIJO 11-11-2026)
# The SHOP counts a coach despatched at SHOP OUT (ERP actualDispatchDate). Some coaches then wait in the yard
# (rubber, cleaning, VG, Kumbh Mela) until the physical despatch marked in HQ OUT TURN.
#   shop_fnd(d) : outturned, not shop out          -> Production Plan FND tab / plan tabs (shop work pending)
#   in_yard(d)  : shop out, not physically gone   -> Production Plan 'Shop Out - Yard' tab
#   physical    : d['actualDispatchDate'] after apply() -> Daily Position, HQ PDC, flash
def erp_only(demands):
    """Undo the HQ overlay: ERP actualDispatchDate back (JIJO 12-11-2026: the Daily Position and the flash
    screens go by ERP only). Returns new dicts - the shared cache is not changed."""
    return [dict(d, actualDispatchDate=d["_shopOut"], _hqStatus=None) if "_shopOut" in d else d for d in demands]


def shop_out(d):
    """ERP shop-out date (actualDispatchDate as ERP has it, before the HQ overlay)."""
    return d["_shopOut"] if "_shopOut" in d else d.get("actualDispatchDate")


def _outturned(d):
    from core import rules as R
    return bool(R.pdate(d.get("dispatchDate"))) and not R.is_excluded(d)


def shop_fnd(d):
    return _outturned(d) and not shop_out(d)


def in_yard(d):
    return _outturned(d) and bool(shop_out(d)) and not d.get("actualDispatchDate")
