"""
core/erp_client.py - READ-ONLY pull from the New Carriage ERP (railway intranet).

Writes the export in the SAME format as 08_Claude_ERP_Export/export_erp.py, so Claude's
reports, the KM / position-tab scripts and this app all read one file:
    08_Claude_ERP_Export/data/erp_demands_latest.json  (+ .xlsx, + archive - last 10 kept)
Coach type / year built are cached in data/coach_meta_cache.json, so only new coaches are looked up.
Nothing is ever written to ERP from here.
"""
import glob
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests

import config

META_CACHE = os.path.join(config.APP_DIR, "data", "coach_meta_cache.json")
ARCHIVE_KEEP = 10

status = {"running": False, "step": "", "done_at": None, "error": None, "count": 0}
_run_lock = threading.Lock()


# ---------------------------------------------------------------- login
def get_session():
    from bs4 import BeautifulSoup
    if not (config.ERP_USERNAME and config.ERP_PASSWORD):
        raise RuntimeError("ERP user name / password not set in .env (run Run_App.py once to enter them).")
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LWPER-App"
    r = s.get(config.ERP_SSO, allow_redirects=True, timeout=15)
    form = BeautifulSoup(r.text, "html.parser").find("form")
    if not form:
        raise RuntimeError("ERP login page not found - are you on the railway network?")
    r = s.post(form.get("action"), data={"username": config.ERP_USERNAME,
                                         "password": config.ERP_PASSWORD, "credentialId": ""},
               allow_redirects=True, timeout=15)
    r.raise_for_status()
    x = s.cookies.get("XSRF-TOKEN")
    if x:
        s.headers["X-XSRF-TOKEN"] = x
    return s


# ---------------------------------------------------------------- legacy category (kept identical to the
# old ERP app so _category in the export does not change for the other scripts)
def legacy_category(desc, repair_type=""):
    rep = str(repair_type).strip().upper()
    d = (desc or "").upper().strip()
    if rep in ("4", "OR") or "OR" in d:
        return "OR"
    if "NMG" in d: return "NMG"
    if "TW8W" in d or ("8W" in d and "TW" in d) or "DETC" in d: return "TW8W"
    if "TW4W" in d or ("4W" in d and "TW" in d) or d.startswith("TW") or d.startswith("RU"): return "TW4W"
    if "SPIC" in d: return "SPIC"
    if "ARMV" in d: return "ARMV"
    if any(k in d for k in ["ART", "SPART", "RH", "RHV", "RTRH", "MFD", "CAMPING", "RR", "WDS"]): return "ART"
    if any(k in d for k in ["DEMU TC", "DEMUTC", "DTC", "TSDTC", "TSNDTC"]) or d == "TC": return "DEMU TC"
    if any(k in d for k in ["DPC", "DHMU"]): return "DPC"
    if any(k in d for k in ["MEMU MC", "MEMUMC", "TSMC"]): return "MEMU MC"
    if any(k in d for k in ["MEMU TC", "MEMUTC", "TSTC"]): return "MEMU TC"
    if any(k in d for k in ["EMU MC", "EMUMC", "DMSC", "YZZS"]): return "EMU MC"
    if any(k in d for k in ["EMU TC", "EMUTC", "YSY", "YFSY", "YSD"]): return "EMU TC"
    if any(k in d for k in ["LWLRRM", "LSLRD", "LVPH"]): return "SLR"
    if "LWSCN" in d or "LSCN" in d: return "LWSCN"
    if "LWACCW" in d or ("2AC" in d and "LW" in d): return "LWACCW"
    if "LWACCN" in d or ("3AC" in d and "LW" in d) or "LWCBAC" in d or "LWFCWAC" in d: return "LWACCN"
    if "LWS" in d or "LS5" in d or "LS" in d: return "LWS"
    if any(k in d for k in ["CN", "WGSCN", "SCN", "GSN", "GSCN"]): return "CN"
    if any(k in d for k in ["CZ", "CZJ", "CZRJ", "SCZ", "SCZJ", "SCZRJ", "WGCZ", "WGCZRJ", "CC"]): return "CZ"
    if any(k in d for k in ["SLR", "GSLRD", "SLRD", "SRD"]): return "SLR"
    return "GS"


# ---------------------------------------------------------------- fetch
def fetch_all_demands(sess):
    api = config.ERP_API
    out, max_did = {}, 76700
    r = sess.get(f"{api}/locos/masters/coach-receipts", timeout=30)
    r.raise_for_status()
    for it in r.json():
        did, cno = str(it.get("demandId") or ""), str(it.get("coachNo") or "").strip()
        if did and cno:
            out[did] = it
            try:
                max_did = max(max_did, int(did))
            except ValueError:
                pass
    status["step"] = f"Open list: {len(out)} demands. Reading closed demands..."
    todo = [d for d in range(67000, max(max_did + 50, 77500)) if str(d) not in out]

    def one(did):
        try:
            r = sess.get(f"{api}/locos/masters/coach-receipts/{did}", timeout=5)
            if r.status_code == 200:
                j = r.json()
                if j and j.get("coachNo"):
                    return str(did), j
        except Exception:
            pass
        return str(did), None

    with ThreadPoolExecutor(max_workers=60) as ex:
        for did, j in ex.map(one, todo):
            if j:
                out[did] = j
    return out


def _load_meta():
    try:
        with open(META_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fetch_meta(sess, coaches):
    meta = _load_meta()
    new = [c for c in coaches if c not in meta]
    status["step"] = f"Coach type for {len(new)} new coaches..."

    def one(c):
        try:
            r = sess.get(f"{config.ERP_API}/locos/masters/coaches/{c}", timeout=10)
            if r.status_code == 200:
                return c, r.json() or {}
        except Exception:
            pass
        return c, None

    with ThreadPoolExecutor(max_workers=30) as ex:
        for c, m in ex.map(one, new):
            if m is not None:
                meta[c] = {k: m.get(k) for k in ("coachTypeDescription", "yearBuilt", "yearOfBuilt",
                                                  "builtYear", "railway", "ownRly")}
    os.makedirs(os.path.dirname(META_CACHE), exist_ok=True)
    with open(META_CACHE, "w", encoding="utf-8") as f:
        json.dump(meta, f)
    return meta


def build_export():
    """Full read-only export. Returns the payload written."""
    sess = get_session()
    status["step"] = "Logged in. Reading ERP demands (1-3 minutes)..."
    demands = fetch_all_demands(sess)
    if not demands:
        raise RuntimeError("ERP returned no demands.")
    coaches = sorted({str(d.get("coachNo") or "").strip() for d in demands.values()} - {""})
    meta = fetch_meta(sess, coaches)

    rows = []
    for did, it in demands.items():
        cno = str(it.get("coachNo") or "").strip()
        m = meta.get(cno) or {}
        desc = m.get("coachTypeDescription") or it.get("coachDesc") or ""
        rec = dict(it)
        rec["demandId"] = str(it.get("demandId") or did)
        rec["_coachTypeDescription"] = desc
        rec["_category"] = legacy_category(desc, it.get("repairType") or "") if desc else ""
        rec["_yearBuilt"] = m.get("yearBuilt") or m.get("yearOfBuilt") or m.get("builtYear") or ""
        rec["_railway"] = m.get("railway") or m.get("ownRly") or ""
        rows.append(rec)

    stamp = datetime.now()
    payload = {"exported_at": stamp.strftime("%Y-%m-%d %H:%M:%S"), "count": len(rows), "demands": rows}
    out_dir = os.path.dirname(config.EXPORT_PATH)
    arch = os.path.join(out_dir, "archive")
    os.makedirs(arch, exist_ok=True)
    tmp = config.EXPORT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, default=str)
    os.replace(tmp, config.EXPORT_PATH)
    with open(os.path.join(arch, f"erp_demands_{stamp:%Y%m%d_%H%M}.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, default=str)
    for old in sorted(glob.glob(os.path.join(arch, "erp_demands_*.json")))[:-ARCHIVE_KEEP]:
        try:
            os.remove(old)
        except OSError:
            pass
    _write_xlsx(rows, os.path.join(out_dir, "erp_demands_latest.xlsx"))
    return payload


def _write_xlsx(rows, path):
    try:
        import openpyxl
        cols = ["demandId", "coachNo", "_category", "_coachTypeDescription", "repairType", "status",
                "receivedDate", "tfr", "corrPlace", "corrComp", "dispatchDate", "actualDispatchDate",
                "pitNum", "remarks"]
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(cols)
        for r in rows:
            ws.append([None if r.get(c) is None else str(r.get(c)) for c in cols])
        wb.save(path)
    except Exception:
        pass


def refresh_in_background(push_online=True):
    """Used by the 'Update from ERP' button."""
    if not _run_lock.acquire(blocking=False):
        return False

    def run():
        t0 = time.time()
        status.update(running=True, error=None, step="Connecting to ERP...")
        try:
            p = build_export()
            status["count"] = p["count"]
            try:
                status["step"] = "Reading target tabs..."
                from core import targets_store
                targets_store.refresh()
            except Exception as e:                      # targets are optional for the ERP refresh
                status["error"] = f"Targets not refreshed: {e}"
            if push_online and config.SUPABASE_URL and config.SUPABASE_KEY:
                status["step"] = "Uploading snapshot to the online dashboard..."
                from core import online_store
                snap = dict(p)
                try:
                    with open(os.path.join(config.APP_DIR, "data", "km_status.json"), encoding="utf-8") as f:
                        snap["km_status"] = json.load(f)
                except Exception:
                    pass
                from core import targets_store
                snap["targets"] = targets_store.load()
                online_store.upload_snapshot(snap)
            status["step"] = f"Done - {p['count']} demands in {time.time() - t0:.0f}s"
            status["done_at"] = datetime.now().strftime("%d-%m-%Y %H:%M")
        except Exception as e:
            status["error"] = str(e)
            status["step"] = "Failed"
        finally:
            status["running"] = False
            _run_lock.release()

    threading.Thread(target=run, daemon=True).start()
    return True


if __name__ == "__main__":       # python -m core.erp_client  -> same as Export_ERP_for_Claude
    p = build_export()
    print(f"DONE: {p['count']} demands -> {config.EXPORT_PATH}")
