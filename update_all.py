"""
update_all.py - ONE button for the daily update (double-click Update_All.py in D:\\Coach_Position_Apps).

 1. Fresh ERP export (read-only; reused if less than 15 minutes old)
 2. Reads the HQ "2026 KM SPLs" LW/PER tab (READ ONLY - never written)
 3. Prepares, WITHOUT writing anything:
      a. OUR sheet POSITION11092026 tab Kumbh_Mela_Special_Pool  (KM summary + roster)
      b. OUR sheet POSITION11092026 tabs YARD / ICF NAC / LHB     (preview xlsx in 10_Claude_Reports\\output)
      c. JIJO's sheet "PDC for CN GS SLR Coaches" tabs GS / CN / GSLRD / CZ
      d. Online dashboard snapshot (Supabase)
    + the app's data-consistency checks
 4. Shows everything in ONE preview -> you type YES once -> writes in that order, verifies each,
    stops at the first error, logs to 10_Claude_Reports\\output\\update_all_log_*.txt
"""
import json
import os
import sys
import traceback
from datetime import datetime

APP = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(APP, "..", ".."))
REPORTS = os.path.join(ROOT, "10_Claude_Reports")
OUT = os.path.join(REPORTS, "output")
sys.path.insert(0, APP)
sys.path.insert(1, REPORTS)
os.chdir(APP)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core import setup_env                         # noqa: E402
setup_env.ensure()
import config                                     # noqa: E402
from core import data, erp_client                 # noqa: E402
from updaters import pdc_hq                        # noqa: E402
from updaters.common import open_sheet            # noqa: E402

KM_STATUS = os.path.join(APP, "data", "km_status.json")
REUSE_MINUTES = 15

os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, f"update_all_log_{datetime.now():%Y%m%d_%H%M}.txt")
_lines = []


def log(m=""):
    print(m)
    _lines.append(str(m))
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(_lines))


def step_export():
    try:
        age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(config.EXPORT_PATH))).total_seconds() / 60
    except OSError:
        age = 10 ** 6
    if age <= REUSE_MINUTES:
        log(f"1. ERP export: using the one made {age:.0f} min ago.")
        with open(config.EXPORT_PATH, encoding="utf-8") as f:
            return json.load(f)
    log("1. ERP export: reading ERP (1-3 minutes, read-only)...")
    p = erp_client.build_export()
    log(f"   {p['count']} demands, exported {p['exported_at']}")
    return p


def read_hq_km():
    """HQ LW/PER tab as text (READ ONLY)."""
    import urllib.request
    url = (f"https://docs.google.com/spreadsheets/d/{config.HQ_KM_SHEET_KEY}/gviz/tq?tqx=out:csv"
           f"&sheet=LW%2FPER&t={datetime.now():%H%M%S}")
    return urllib.request.urlopen(url, timeout=30).read().decode("utf-8")


def main():
    log(f"LW/PER UPDATE ALL - {datetime.now():%d-%m-%Y %H:%M}")
    payload = step_export()
    import lwper_rules
    demands_raw, exported = lwper_rules.load_export(config.EXPORT_PATH)
    D, ex = data.load(force=True)
    as_on = ex.date()

    log("2. HQ KM sheet (read only)...")
    hq_csv_path = os.path.join(OUT, "hq_km_latest.csv")
    with open(hq_csv_path, "w", encoding="utf-8") as f:
        f.write(read_hq_km())

    plan, problems = {}, []

    # a. KM tab --------------------------------------------------------------
    import km_sheet_update as km
    try:
        hq, upd = km.read_hq(hq_csv_path)
        S, outs, summ, flags = km.compute(hq, demands_raw)
        plan["km"] = km.sheet_rows(S, outs, summ, exported)
        os.makedirs(os.path.dirname(KM_STATUS), exist_ok=True)
        with open(KM_STATUS, "w", encoding="utf-8") as f:
            json.dump({"updated": upd, "read_at": f"{datetime.now():%Y-%m-%d %H:%M}",
                       "coaches": {c: h["st"] for c, h in hq.items()}}, f)
        log(f"\n3a. Kumbh_Mela_Special_Pool (HQ LW/PER updated {upd}) - LW rows to type in HQ:")
        log(f"    {'Row':12} {'Total':>6} {'YB>=12':>7} {'KM done':>8} {'KM under':>9} {'Regular':>8}")
        for r in km.ROWS:
            t = summ[r]
            log(f"    {r:12} {t[0]:>6} {t[1]:>7} {t[2]:>8} {t[3]:>9} {t[4]:>8}")
        for fl in flags:
            log(f"    CHECK: {fl}")
    except BaseException as e:                       # compute() raises SystemExit if totals do not reconcile
        problems.append(f"KM tab: {e}")
        log(f"\n3a. KM tab NOT prepared: {e}")

    # b. YARD / ICF NAC / LHB ------------------------------------------------
    import position_tabs_update as pt
    try:
        sh_pos = open_sheet(pt.SHEET_KEY)
        wb = {t: pt.GridSheet(sh_pos.worksheet(t).get_all_values()) for t in pt.TABS}
        with open(hq_csv_path, encoding="utf-8") as f:
            km_list = pt.hq_km_not_out(f.read())
        plan["pos"] = (sh_pos, pt.build_plan(wb, demands_raw, exported, km_list))
        prev = pt.write_preview(plan["pos"][1], os.path.join(OUT, "position_tabs_preview_latest.xlsx"))
        log(f"\n3b. Position tabs (preview: {prev})")
        for t, v in plan["pos"][1]["tabs"].items():
            log(f"    {t:8}: {len(v['append']):3} new rows, {len(v['updates']):3} cell updates")
        imp = [f for f in plan["pos"][1]["flags"] if not f[3].startswith("Sheet desp")]
        for f in imp:
            log(f"    CHECK {f[0]} {f[1]} {f[2]}: {f[3]}")
    except Exception as e:
        problems.append(f"Position tabs: {e}")
        log(f"\n3b. Position tabs NOT prepared: {e}")

    # c. PDC sheet -----------------------------------------------------------
    try:
        sh_pdc = open_sheet(pdc_hq.SHEET_KEY)
        cur = pdc_hq.read_current(sh_pdc)
        plan["pdc"] = (sh_pdc, pdc_hq.build(D, as_on, cur))
        log("\n3c. PDC for CN GS SLR Coaches (holding only, no FND):")
        for line in pdc_hq.preview_lines(plan["pdc"][1], cur):
            log("  " + line)
    except Exception as e:
        problems.append(f"PDC sheet: {e}")
        log(f"\n3c. PDC sheet NOT prepared: {e}")

    # d. online snapshot -------------------------------------------------------
    if config.SUPABASE_URL and config.SUPABASE_KEY:
        plan["online"] = True
        log("\n3d. Online dashboard: snapshot will be uploaded to Supabase.")

    # checks -----------------------------------------------------------------
    from analysis import checks, perf
    trows, _ = perf.load_targets(config.POSITION_SHEET_KEY)
    bad = [c for c in checks.run(D, as_on, trows or None) if not c["ok"]]
    log("\nData consistency: " + ("all checks OK" if not bad else f"{len(bad)} MISMATCH"))
    for c in bad:
        log(f"    MISMATCH {c['name']}: {c['detail']}")

    if problems:
        log("\nNot prepared (will be skipped): " + "; ".join(problems))
    if not any(k in plan for k in ("km", "pos", "pdc", "online")):
        log("\nNothing to write.")
        return
    log("\nNothing has been written yet. The HQ sheet is never written.")
    if input("Type YES to write all of the above: ").strip() != "YES":
        log("Cancelled - nothing written.")
        return

    log("\n4. Writing...")
    if "km" in plan:
        # summary rows 1-6 must not be merged (a merge across A:H hides the headers and the GS row)
        ws_km = open_sheet(km.LOCAL_SHEET_KEY).worksheet(km.TAB)
        ws_km.spreadsheet.batch_update({"requests": [{"unmergeCells": {"range": {
            "sheetId": ws_km.id, "startRowIndex": 0, "endRowIndex": 6, "startColumnIndex": 0, "endColumnIndex": 15}}}]})
        ok = km.write_sheet(plan["km"])
        log(f"  Kumbh_Mela_Special_Pool - {'verified' if ok else 'CHECK: read-back differs'}")
        if not ok:
            raise RuntimeError("KM tab read-back differs - stopped")
    if "pos" in plan:
        n = pt.apply(plan["pos"][0], plan["pos"][1], lambda m: log("  " + m))
        log(f"  Position tabs - {n} ranges written")
    if "pdc" in plan:
        pdc_hq.apply(plan["pdc"][0], plan["pdc"][1], as_on, log)
    if "online" in plan:
        from core import online_store
        snap = dict(payload)
        try:
            with open(KM_STATUS, encoding="utf-8") as f:
                snap["km_status"] = json.load(f)
        except Exception:
            pass
        online_store.upload_snapshot(snap)
        log("  Online snapshot uploaded")
    log(f"\nDONE. Log: {LOG}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("\nSTOPPED:\n" + traceback.format_exc())
    input("\nPress Enter to close...")
