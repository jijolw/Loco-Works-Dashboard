"""
update_all.py - ONE button for the daily update (double-click Update_All.py in D:\\Coach_Position_Apps).

 1. Fresh ERP export (read-only; reused if less than 15 minutes old)
 2. Reads the HQ "2026 KM SPLs" LW/PER tab (READ ONLY - never written)
 3. Prepares, WITHOUT writing anything:
      a. OUR sheet POSITION11092026 tab Kumbh_Mela_Special_Pool  (KM summary + roster)
      b. OUR sheet POSITION11092026 tabs YARD / ICF NAC / LHB     (preview xlsx in 10_Claude_Reports\\output)
      c. JIJO's sheet "PDC for CN GS SLR Coaches" tabs GS / CN / GSLRD / CZ
      d. Online dashboard snapshot (Supabase)
      e. "Achieved" column of Internal_Targets / HQ_Targets / RB_Targets from ERP (targets are typed by JIJO)
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

# Update all step status (JIJO 19-11-2026): every step writes what it did, so the closing summary shows it.
STATUS_FILE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..", "update_all_status.json"))


def step_status(step, state=None, **extra):
    try:
        with open(STATUS_FILE, encoding="utf-8") as fh:
            st = json.load(fh)
    except Exception:
        st = {}
    if state is not None:
        st[step] = {"state": state, "at": datetime.now().strftime("%d-%m-%Y %H:%M")}
    st.update(extra)
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=1)
    except Exception:
        pass
    return st

_lines = []


def _retry(fn, *a, tries=4):
    """Run a sheet writer again if Google drops the connection (09-11: 'Remote end closed connection')."""
    import time
    for n in range(1, tries + 1):
        try:
            return fn(*a)
        except Exception as e:                      # requests ConnectionError / gspread transport errors
            msg = str(e).lower()
            quota = "429" in msg or "quota" in msg          # Google read limit per minute (23-11-2026) - wait and go on
            if n == tries or not ("connection" in msg or quota):
                raise
            wait = 65 if quota else 15
            log(f"    {'Google read limit reached' if quota else 'connection dropped'} ({e.__class__.__name__}) - retry {n} in {wait} s")
            time.sleep(wait)


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
    try:                                              # fresh status for this run (old run's YES must not carry over)
        with open(STATUS_FILE, "w", encoding="utf-8") as fh:
            json.dump({"started": datetime.now().strftime("%d-%m-%Y %H:%M")}, fh)
    except Exception:
        pass
    log(f"LW/PER UPDATE ALL - {datetime.now():%d-%m-%Y %H:%M}")
    payload = step_export()
    import lwper_rules
    demands_raw, exported = lwper_rules.load_export(config.EXPORT_PATH)
    from core import physical                       # HQ OUT TURN - READ ONLY (JIJO 10-11-2026)
    log("1b. HQ OUT TURN (read only) - physical despatch...")
    pl, perr = physical.refresh()
    if perr:
        log("    NOTE: " + perr + (" - saved copy of " + pl["read_at"] + " used" if pl else " - ERP shop-out dates used"))
    D, ex = data.load(force=True)                    # ERP only (JIJO 12-11-2026)
    as_on = ex.date()
    # HQ OUT TURN is used ONLY for the daily planner (Production Plan FND / Despatched col K / Shop Out - Yard),
    # on its own copy DP; HQ PDC, POSITION tabs, targets and checks use ERP (D). JIJO 12-11-2026.
    import copy
    DP = copy.deepcopy(D)
    phys_checks = physical.apply(DP, pl, as_on=as_on) if pl else []
    if pl:
        n, shop_only = physical.summary(DP)
        log(f"    read {pl['read_at']}: {len(pl['rows'])} rows - DESP {n['DESP']}, FND {n['FND']}, RFD {n['RFD']} (planner only)")
        if shop_only:
            log(f"    Shop out in ERP, still in yard per HQ (planner 'Shop Out - Yard'): {', '.join(shop_only)}")
        for c in phys_checks:
            log(f"    CHECK: {c}")

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
        try:
            from core import condemnation
            cond_rows, cond_err = condemnation.load(live=True)
            cond = pdc_hq.pipeline_remarks(cond_rows.get("rows", []))
            if cond_err:
                log("    NOTE: " + cond_err)
        except Exception as e:
            cond = {}
            log(f"    NOTE: Condemnation_Pipeline not read ({e}) - REMARKS kept as typed")
        plan["pdc"] = (sh_pdc, pdc_hq.build(D, as_on, cur, cond))
        log("\n3c. PDC for CN GS SLR Coaches (holding + ICF FND/RFD per HQ OUT TURN):")
        for line in pdc_hq.preview_lines(plan["pdc"][1], cur):
            log("  " + line)
        log(f"    Left out - proposed for condemnation: {len(pdc_hq.LEFT_OUT)} coach(es)"
            + (f" - {', '.join(pdc_hq.LEFT_OUT)}" if pdc_hq.LEFT_OUT else ""))
    except Exception as e:
        problems.append(f"PDC sheet: {e}")
        log(f"\n3c. PDC sheet NOT prepared: {e}")

    # f. Production Plan sheet - FND tab (all FND coaches, sections kept as typed by the shop) - JIJO 04-11-2026
    try:
        from updaters import fnd_tab
        sh_fnd = open_sheet(fnd_tab.SHEET_KEY)
        cur_fnd = fnd_tab.read_current(sh_fnd)
        plan["fnd"] = (sh_fnd, fnd_tab.build(DP, cur_fnd))
        log("\n3f. Production Plan - FND tab (outturned, not yet shop out):")
        for line in fnd_tab.preview_lines(plan["fnd"][1], cur_fnd):
            log(line)
    except Exception as e:
        problems.append(f"FND tab: {e}")
        log(f"\n3f. FND tab NOT prepared: {e}")

    # g. Production Plan sheet - Despatched tab (physically despatched this month; typed rows kept) - JIJO 07-11-2026
    try:
        from updaters import despatched_tab
        sh_desp = open_sheet(despatched_tab.SHEET_KEY)
        plan["desp"] = (sh_desp, despatched_tab.build(DP, despatched_tab.read_current(sh_desp)))
        log("\n3g. Production Plan - Despatched tab (shop out this month; K = physical despatch):")
        for line in despatched_tab.preview_lines(plan["desp"][1]):
            log(line)
    except Exception as e:
        problems.append(f"Despatched tab: {e}")
        log(f"\n3g. Despatched tab NOT prepared: {e}")

    # h. Production Plan sheet - Shop Out - Yard tab (shop out, still in yard per HQ OUT TURN) - JIJO 11-11-2026
    try:
        from updaters import yard_tab
        sh_yard = open_sheet(yard_tab.SHEET_KEY)
        cur_yard = yard_tab.read_current(sh_yard)
        plan["yard"] = (sh_yard, yard_tab.build(DP, cur_yard))
        log("\n3h. Production Plan - Shop Out - Yard tab (rubber / cleaning / VG / KM):")
        for line in yard_tab.preview_lines(plan["yard"][1], cur_yard):
            log(line)
    except Exception as e:
        problems.append(f"Shop Out - Yard tab: {e}")
        log(f"\n3h. Shop Out - Yard tab NOT prepared: {e}")

    # e. Achieved columns of the target tabs (ERP outturn; targets themselves are JIJO's)
    try:
        from updaters import achieved
        from updaters.common import open_sheet as _os
        plan["ach"] = achieved.plan(_os(config.POSITION_SHEET_KEY), D, as_on)
        n = sum(len(v) for v in plan["ach"]["changes"].values())
        log(f"\n3e. Target tabs - Achieved from ERP ({n} cells change; targets not touched):")
        for line in achieved.preview_lines(plan["ach"]):
            log(line)
        if not n:
            plan.pop("ach")
    except Exception as e:
        problems.append(f"Achieved columns: {e}")
        log(f"\n3e. Achieved columns NOT prepared: {e}")

    # targets (all rows of Internal / HQ / RB target tabs, read only - a sheet filter does not hide rows)
    try:
        from core import targets_store
        tg = targets_store.refresh()
        log("\nTargets read (Internal / HQ / RB): " + ", ".join(f"{k} {len(v)} rows" for k, v in tg["tabs"].items()))
    except Exception as e:
        log(f"\nTargets NOT read: {e}")

    # d. online snapshot -------------------------------------------------------
    if config.SUPABASE_URL and config.SUPABASE_KEY:
        plan["online"] = True
        log("\n3d. Online dashboard: snapshot will be uploaded to Supabase.")

    # checks -----------------------------------------------------------------
    from analysis import checks, perf
    trows, _ = perf.load_targets()
    bad = [c for c in checks.run(D, as_on, trows or None) if not c["ok"]]
    log("\nData consistency: " + ("all checks OK" if not bad else f"{len(bad)} MISMATCH"))
    for c in bad:
        log(f"    MISMATCH {c['name']}: {c['detail']}")

    if problems:
        log("\nNot prepared (will be skipped): " + "; ".join(problems))
    if not any(k in plan for k in ("km", "pos", "pdc", "fnd", "desp", "yard", "ach", "online")):
        log("\nNothing to write.")
        step_status("1 Sheets", "nothing to write")
        return
    log("\nNothing has been written yet. The HQ KM sheet (2026 KM SPLs) is only read, never written.")
    log("ONE YES covers step 1 (above) and step 2 (Production Plan plan tabs, its preview prints next).")
    if input("Type YES to write all of the above: ").strip() != "YES":
        log("Cancelled - nothing written.")
        step_status("1 Sheets", "not written (no YES)")
        return
    step_status(None, yes_at=datetime.now().timestamp())

    log("\n4. Writing...")
    if "km" in plan:
        # summary rows 1-6 must not be merged (a merge across A:H hides the headers and the GS row)
        ws_km = open_sheet(km.LOCAL_SHEET_KEY).worksheet(km.TAB)
        ws_km.spreadsheet.batch_update({"requests": [{"unmergeCells": {"range": {
            "sheetId": ws_km.id, "startRowIndex": 0, "endRowIndex": 6, "startColumnIndex": 0, "endColumnIndex": 15}}}]})
        ok = _retry(km.write_sheet, plan["km"])
        log(f"  Kumbh_Mela_Special_Pool - {'verified' if ok else 'CHECK: read-back differs'}")
        if not ok:
            raise RuntimeError("KM tab read-back differs - stopped")
    if "pos" in plan:
        n = pt.apply(plan["pos"][0], plan["pos"][1], lambda m: log("  " + m))
        log(f"  Position tabs - {n} ranges written")
    if "pdc" in plan:
        _retry(pdc_hq.apply, plan["pdc"][0], plan["pdc"][1], as_on, log)
    if "fnd" in plan:
        _retry(fnd_tab.apply, plan["fnd"][0], plan["fnd"][1], log)
    if "desp" in plan:
        _retry(despatched_tab.apply, plan["desp"][0], plan["desp"][1], log)
    if "yard" in plan:
        _retry(yard_tab.apply, plan["yard"][0], plan["yard"][1], log)
    if "ach" in plan:
        _retry(achieved.apply, plan["ach"], log)
    if "online" in plan:
        from core import online_store
        snap = dict(payload)
        try:
            with open(KM_STATUS, encoding="utf-8") as f:
                snap["km_status"] = json.load(f)
        except Exception:
            pass
        from core import targets_store
        snap["targets"] = targets_store.load()
        from core import physical as _ph
        snap["hq_outturn"] = _ph.load()            # physical despatch overlay for the online copy
        _retry(online_store.upload_snapshot, snap)
        log("  Online snapshot uploaded")
    step_status("1 Sheets", "written")
    log(f"\nDONE (step 1 of 2). Log: {LOG}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        if "connection" in str(e).lower():
            log("\nSTOPPED: Google connection kept dropping. Run Update_All again - steps already written show no "
                "change the second time.")
        log("\nSTOPPED:\n" + traceback.format_exc(limit=3))
        step_status("1 Sheets", "STOPPED - error, see above")
    if "--no-pause" not in sys.argv:            # --no-pause: run as step 1 of Update all (12-11-2026)
        input("\nPress Enter to close...")
