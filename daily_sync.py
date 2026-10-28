"""
daily_sync.py - used by D:\\Coach_Position_Apps\\Daily_Run.bat (Claude, 28-10-2026).

SYNC ONLY - safe for staff to run, no YES needed:
 1. Fresh ERP export (read-only)               -> 08_Claude_ERP_Export\\data\\erp_demands_latest.json
 2. Target tabs + HQ KM status (READ only)     -> data\\targets.json, data\\km_status.json, KM summary file
 3. Snapshot for the online website (Supabase) -> same as the app's "Update from ERP" button
NOTHING is written to any Google Sheet or to ERP. Sheet updates stay with Update_All.py (JIJO types YES).
"""
import json
import os
import sys
from datetime import datetime

APP = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(APP, "..", ".."))
REPORTS = os.path.join(ROOT, "10_Claude_Reports")
sys.path.insert(0, APP)
sys.path.insert(1, REPORTS)
os.chdir(APP)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    print(f"LW/PER DAILY SYNC - {datetime.now():%d-%m-%Y %H:%M}  (no Google Sheet is written)")
    from core import setup_env
    env = setup_env.ensure(interactive=False)
    if not env.get("ERP_USERNAME") or not env.get("ERP_PASSWORD"):
        print("ERP login not set on this PC (.env). Ask JIJO to run Run_App.py once.")
        return 1
    import config
    from core import erp_client, targets_store, online_store

    print("1. ERP export (read-only, 1-3 minutes)...")
    p = erp_client.build_export()
    print(f"   {p['count']} demands, exported {p['exported_at']}")

    print("2. Target tabs and HQ KM status (read only)...")
    try:
        tg = targets_store.refresh()
        print("   targets: " + ", ".join(f"{k} {len(v)} rows" for k, v in tg["tabs"].items()))
    except Exception as e:
        print(f"   targets not read ({e}) - last saved copy used")
    km_file = os.path.join(APP, "data", "km_status.json")
    try:
        import urllib.request
        import km_sheet_update as km
        url = (f"https://docs.google.com/spreadsheets/d/{config.HQ_KM_SHEET_KEY}/gviz/tq?tqx=out:csv"
               f"&sheet=LW%2FPER&t={datetime.now():%H%M%S}")
        csv_path = os.path.join(REPORTS, "output", "hq_km_latest.csv")
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(urllib.request.urlopen(url, timeout=30).read().decode("utf-8"))
        hq, upd = km.read_hq(csv_path)
        with open(km_file, "w", encoding="utf-8") as f:
            json.dump({"updated": upd, "read_at": f"{datetime.now():%Y-%m-%d %H:%M}",
                       "coaches": {c: h["st"] for c, h in hq.items()}}, f)
        print(f"   HQ KM status read (HQ updated {upd})")
        # KM summary (same figures as the Update_All preview) -> file for Claude on Drive. READ ONLY.
        try:
            import lwper_rules
            demands_raw, exported = lwper_rules.load_export(config.EXPORT_PATH)
            S, outs, summ, flags = km.compute(hq, demands_raw)
            lines = [f"KM SUMMARY - ERP export {p['exported_at']} - HQ LW/PER tab updated {upd}",
                     f"{'Row':12} {'Total':>6} {'YB>=12':>7} {'KM done':>8} {'KM under':>9} {'Regular':>8}"]
            for r in km.ROWS:
                t = summ[r]
                lines.append(f"{r:12} {t[0]:>6} {t[1]:>7} {t[2]:>8} {t[3]:>9} {t[4]:>8}")
            lines += [f"CHECK: {fl}" for fl in flags]
            with open(os.path.join(REPORTS, "output", "km_summary_latest.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print("   KM summary saved (km_summary_latest.txt)")
        except BaseException as e:
            print(f"   KM summary not made ({e})")
    except Exception as e:
        print(f"   HQ KM status not read ({e}) - last saved copy used")

    if config.SUPABASE_URL and config.SUPABASE_KEY:
        print("3. Online website snapshot (Supabase)...")
        snap = dict(p)
        try:
            with open(km_file, encoding="utf-8") as f:
                snap["km_status"] = json.load(f)
        except Exception:
            pass
        snap["targets"] = targets_store.load()
        online_store.upload_snapshot(snap)
        print("   uploaded - online website now shows this data")
    else:
        print("3. Online snapshot skipped (Supabase not set in .env)")
    print("Daily sync done.")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nSTOPPED: {e}")
        rc = 2
    sys.exit(rc)
