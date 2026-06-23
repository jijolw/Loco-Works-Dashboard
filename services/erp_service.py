# =====================================================
# services/erp_service.py
# LW/PER Workshop Intelligence System (Optimized Supabase version)
# =====================================================

import logging
import requests
import time
from datetime import datetime, timedelta
from collections import OrderedDict

# Project config
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import CACHE_TTL_MASTER, CACHE_TTL_SINGLE, CACHE_TTL_STATIC, SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)


def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

# Cache system
_cache = {}

def _get_cached(key, ttl):
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts > ttl:
        return None
    return data

def _set_cached(key, data):
    _cache[key] = (time.time(), data)

def cache_clear(key=None):
    if key is None:
        _cache.clear()
    else:
        _cache.pop(key, None)

# Stubs for unused session methods in Supabase mode
def get_session():
    class DummySession:
        def close(self): pass
    return DummySession()

def get_ac_session():
    class DummySession:
        def close(self): pass
    return DummySession()

def reset_sessions():
    pass

# Helper parsing functions
def _parse_date(date_str):
    if not date_str or str(date_str).strip() == "":
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except ValueError:
            continue
    return None

def _is_valid_pitnum(pitnum):
    """Check whether a pitnum looks valid (not empty, not just whitespace)."""
    if not pitnum:
        return False
    return str(pitnum).strip() not in ("", "None", "null")

# Populate cache with all required lookup maps
def _populate_batch_cache():
    logger.info("Populating batch cache from Supabase...")
    
    # 1. Fetch all active coaches in chunks of 1000
    active_coaches = []
    limit = 1000
    offset = 0
    while True:
        url_coaches = f"{SUPABASE_URL}/erp_active_coaches?select=*&limit={limit}&offset={offset}"
        try:
            resp = requests.get(url_coaches, headers=get_headers(), timeout=30)
            resp.raise_for_status()
            chunk = resp.json()
            if not chunk:
                break
            active_coaches.extend(chunk)
            if len(chunk) < limit:
                break
            offset += limit
        except Exception as exc:
            logger.error("Failed to fetch erp_active_coaches chunk: %s", exc)
            return False

    # 2. Fetch all manual updates in chunks of 1000
    manual_updates = []
    limit = 1000
    offset = 0
    while True:
        url_manual = f"{SUPABASE_URL}/manual_coach_updates?select=*&limit={limit}&offset={offset}"
        try:
            resp_m = requests.get(url_manual, headers=get_headers(), timeout=30)
            resp_m.raise_for_status()
            chunk = resp_m.json()
            if not chunk:
                break
            manual_updates.extend(chunk)
            if len(chunk) < limit:
                break
            offset += limit
        except Exception as exc:
            logger.error("Failed to fetch manual_coach_updates chunk: %s", exc)
            break

    # 3. Process and map active coaches
    mapped_records = []
    demandid_map = {}
    coachno_map = {}
    
    for r in active_coaches:
        make_raw = r.get("make") or ""
        make = make_raw
        status_val = str(r.get("status") or "").strip().upper()
        
        if status_val == "AC LOCO" or make_raw.startswith("AC LOCO||"):
            # AC Loco mapping
            recd_on = ""
            stripping = ""
            dewheel = ""
            wheeling = ""
            test_trial = ""
            traffic = ""
            super_str = ""
            tm = ""
            ico_tm = ""
            tfr = ""
            
            if "||" in make_raw:
                parts = make_raw.split("||")
                make = parts[0]
                if len(parts) > 1: recd_on = parts[1]
                if len(parts) > 2: stripping = parts[2]
                if len(parts) > 3: dewheel = parts[3]
                if len(parts) > 4: wheeling = parts[4]
                if len(parts) > 5: test_trial = parts[5]
                if len(parts) > 6: traffic = parts[6]
                if len(parts) > 7: super_str = parts[7]
                if len(parts) > 8: tm = parts[8]
                if len(parts) > 9: ico_tm = parts[9]
                if len(parts) > 10: tfr = parts[10]
                
            mapped = {
                "coachno": r.get("coachno"),
                "coachdesc": r.get("coach_desc"),
                "coach_desc": r.get("coach_desc"),
                "demandid": r.get("demandid"),
                "pitnum": r.get("pitnum"),
                "recddate": r.get("recd_date"),
                "recd_date": r.get("recd_date"),
                "status": r.get("status"),
                "pohstatus": r.get("status"),
                "division": r.get("division"),
                "dvnid": r.get("division"),
                "repair_type": r.get("repair_type"),
                "repairid": r.get("repair_type"),
                "year_built": r.get("year_built"),
                "make": make,
                "recd_on": recd_on,
                "stripping": stripping,
                "dewheel": dewheel,
                "wheeling": wheeling,
                "test_trial": test_trial,
                "traffic": traffic,
                "super_str": super_str,
                "tm": tm,
                "ico_tm": ico_tm,
                "tfr": tfr
            }
        else:
            # Standard coach mapping
            presurveyhrs = ""
            finalhrs = ""
            last_poh = ""
            last_pohdate = ""
            tfr_date = ""
            corr_place = ""
            corr_comp = ""
            desp_date = ""
            actualdespdate = ""
            pohdays = ""
            remarks = ""
            noofdays = ""
            corrosion = ""
            if "||" in make_raw:
                parts = make_raw.split("||")
                make = parts[0]
                if len(parts) > 1: presurveyhrs = parts[1]
                if len(parts) > 2: finalhrs = parts[2]
                if len(parts) > 3: last_poh = parts[3]
                if len(parts) > 4: last_pohdate = parts[4]
                if len(parts) > 5: tfr_date = parts[5]
                if len(parts) > 6: corr_place = parts[6]
                if len(parts) > 7: corr_comp = parts[7]
                if len(parts) > 8: desp_date = parts[8]
                if len(parts) > 9: actualdespdate = parts[9]
                if len(parts) > 10: pohdays = parts[10]
                if len(parts) > 11: remarks = parts[11]
                if len(parts) > 12: noofdays = parts[12]
                if len(parts) > 13: corrosion = parts[13]
                
            mapped = {
                "coachno": r.get("coachno"),
                "coachdesc": r.get("coach_desc"),
                "coach_desc": r.get("coach_desc"),
                "demandid": r.get("demandid"),
                "pitnum": r.get("pitnum"),
                "recddate": r.get("recd_date"),
                "recd_date": r.get("recd_date"),
                "status": r.get("status"),
                "pohstatus": r.get("status"),
                "division": r.get("division"),
                "dvnid": r.get("division"),
                "repair_type": r.get("repair_type"),
                "repairid": r.get("repair_type"),
                "year_built": r.get("year_built"),
                "make": make,
                "presurveyhrs": presurveyhrs,
                "finalhrs": finalhrs,
                "last_poh": last_poh,
                "last_pohdate": last_pohdate,
                "tfr_date": tfr_date,
                "corr_place": corr_place,
                "corr_comp": corr_comp,
                "desp_date": desp_date,
                "actualdespdate": actualdespdate,
                "pohdays": pohdays,
                "remarks": remarks,
                "noofdays": noofdays,
                "corrosion": corrosion,
                "corr_repair": corrosion,
                "curheavylow": corrosion
            }
        mapped_records.append(mapped)
        
        demandid = r.get("demandid")
        if demandid:
            demandid_map[str(demandid).strip()] = mapped
            
        coachno = r.get("coachno")
        if coachno:
            coachno_map[str(coachno).strip()] = mapped

    # 4. Map manual updates
    manual_updates_map = {}
    for mu in manual_updates:
        coachno = mu.get("coachno")
        if coachno:
            manual_updates_map[str(coachno).strip()] = mu

    # 5. Store maps in cache
    _set_cached("master_list", mapped_records)
    _set_cached("demandid_map", demandid_map)
    _set_cached("coachno_map", coachno_map)
    _set_cached("manual_updates_map", manual_updates_map)
    logger.info("Batch cache population complete: %d coaches, %d manual updates", len(mapped_records), len(manual_updates_map))
    return True

# 1. fetch_master() - reads erp_active_coaches from Supabase (uses batch cache)
def fetch_master():
    cache_key = "master_list"
    cached = _get_cached(cache_key, CACHE_TTL_MASTER)
    if cached is not None:
        return cached

    success = _populate_batch_cache()
    if not success:
        return []
        
    return _get_cached(cache_key, CACHE_TTL_MASTER) or []

def fetch_master_live_search(coachno):
    """Fetch matching coach records directly from live intranet ERP listdata2.html using search term."""
    try:
        from config import COACH_ERP_BASE_URL, COACH_ERP_USERNAME, COACH_ERP_PASSWORD
        sess = requests.Session()
        # 1. Login to live ERP
        login_url = f"{COACH_ERP_BASE_URL}/coach/login"
        sess.post(login_url, data={
            "username": COACH_ERP_USERNAME,
            "password": COACH_ERP_PASSWORD,
        }, timeout=10)
        
        # 2. Query listdata2.html with search parameter
        url = f"{COACH_ERP_BASE_URL}/coach/pohmaster/listdata2.html"
        payload = {
            "draw": "1",
            "start": "0",
            "length": "25000",
            "search[value]": str(coachno).strip(),
            "search[regex]": "false",
            "order[0][column]": "1",
            "order[0][dir]": "asc",
            "columns[0][data]": "rno",
            "columns[0][searchable]": "true",
            "columns[0][orderable]": "true",
            "columns[1][data]": "coachno",
            "columns[1][searchable]": "true",
            "columns[1][orderable]": "true",
        }
        resp = sess.post(url, data=payload, headers={"X-Requested-With": "XMLHttpRequest"}, timeout=15)
        if resp.ok:
            data = resp.json()
            records = data.get("data", [])
            mapped = []
            for r in records:
                cno = str(r.get("newcoachno") or r.get("coachno") or "").strip()
                # filter exactly or matching prefix
                if str(coachno).strip().lower() in cno.lower():
                    mapped.append({
                        "coachno": cno,
                        "coachdesc": r.get("coachdesc") or r.get("coach_desc") or "",
                        "coach_desc": r.get("coachdesc") or r.get("coach_desc") or "",
                        "demandid": str(r.get("demandid")),
                        "pitnum": r.get("pitnum") or "",
                        "recddate": r.get("recddate") or r.get("recd_date") or "",
                        "recd_date": r.get("recddate") or r.get("recd_date") or "",
                        "status": r.get("status") or "",
                        "pohstatus": r.get("status") or "",
                        "division": r.get("division") or "",
                        "dvnid": r.get("dvnid") or r.get("division") or "",
                        "repair_type": r.get("repair_type") or r.get("repairid") or "",
                        "repairid": r.get("repairid") or r.get("repair_type") or "",
                        "year_built": r.get("year_built") or "",
                        "make": r.get("make") or "",
                        "presurveyhrs": r.get("presurveyhrs") or "",
                        "finalhrs": r.get("finalhrs") or "",
                        "last_poh": r.get("last_poh") or "",
                        "last_pohdate": r.get("last_pohdate") or "",
                        "tfr_date": r.get("tfr_date") or "",
                        "corr_place": r.get("corr_place") or "",
                        "corr_comp": r.get("corr_comp") or "",
                        "desp_date": r.get("desp_date") or r.get("despdate") or "",
                        "actualdespdate": r.get("actualdespdate") or "",
                        "pohdays": r.get("pohdays") or "",
                        "remarks": r.get("remarks") or ""
                    })
            return mapped
    except Exception as e:
        logger.error(f"fetch_master_live_search failed for coachno {coachno}: {e}")
    return []

# 2. fetch_clean() - pre-processed list (uses batch cache)
def fetch_clean():
    cache_key = "clean_master"
    cached = _get_cached(cache_key, CACHE_TTL_MASTER)
    if cached is not None:
        return cached

    from services.decoders import decode_family

    raw = fetch_master()
    manual_updates_map = _get_cached("manual_updates_map", CACHE_TTL_MASTER) or {}
    now = datetime.now()
    cutoff = now - timedelta(days=365)
    cleaned = []
    seen_coaches = OrderedDict()

    for rec in raw:
        # Clone to avoid mutating cached master list items
        item = dict(rec)
        recd_str = item.get("recd_date") or item.get("recddate")
        recd_dt = _parse_date(recd_str)

        # Skip if no received date
        if recd_dt is None:
            continue

        # Check actualdespdate (physically despatched in ERP)
        act_desp = str(item.get("actualdespdate") or "").strip()
        status_val = str(item.get("status") or "").strip().upper()
        has_actual_desp = False
        if act_desp and act_desp.lower() not in ("none", "null", "nan", ""):
            act_desp_dt = _parse_date(act_desp)
            if act_desp_dt and recd_dt:
                if act_desp_dt >= recd_dt:
                    has_actual_desp = True
            else:
                has_actual_desp = True
        elif status_val in ("DESPATCHED", "OUTTURN"):
            has_actual_desp = True
        
        # Check manual update override in Supabase
        coachno = item.get("coachno")
        is_manually_pending = False
        vg_completed = False
        if coachno:
            mu = manual_updates_map.get(str(coachno).strip())
            if mu:
                # Check if manual update is stale (i.e. it was entered for a past visit)
                mu_date_str = mu.get("physical_date") or mu.get("vg_date") or ""
                mu_dt = _parse_date(mu_date_str)
                if not mu_dt and mu.get("updated_at"):
                    try:
                        iso_date = mu.get("updated_at").split('T')[0]
                        mu_dt = datetime.strptime(iso_date, "%Y-%m-%d")
                    except Exception:
                        pass
                
                is_mu_stale = False
                if mu_dt and recd_dt and mu_dt < recd_dt:
                    is_mu_stale = True
                    
                if not is_mu_stale:
                    phys_status = (mu.get("physical_status") or "").strip()
                    if phys_status == "Despatched":
                        has_actual_desp = True
                    elif phys_status == "Pending":
                        is_manually_pending = True
                        has_actual_desp = False
                    
                    if mu.get("vg_status") == "Completed" and mu.get("physical_status") == "Despatched":
                        vg_completed = True
                    
        if has_actual_desp and vg_completed:
            continue

        # Skip stale (>365 days) unless it is manually pending
        if recd_dt < cutoff and not is_manually_pending:
            continue

        # Check paper despatch threshold: if desp_date is set and older than 15 days, treat as physically despatched!
        # ONLY for non-SPECIAL, non-LOCO, and non-TW families
        # UPDATED: Removed 15-day paper despatch cutoff to keep FND coaches inside the workshop until physically despatched.
        # desp_date = item.get("desp_date") or ""
        # if not desp_date and "||" in (item.get("make") or ""):
        #     parts = item.get("make").split("||")
        #     if len(parts) > 8:
        #         desp_date = parts[8]
        #         
        # desp_dt = _parse_date(desp_date)
        # if desp_dt and not is_manually_pending:
        #     family = decode_family(item.get("coach_desc") or item.get("coachdesc") or "")
        #     if family not in ("SPECIAL", "LOCO", "TW"):
        #         if (now - desp_dt).days > 15:
        #             continue

        status_val = str(item.get("status") or "").strip().upper()
        if status_val in _LIVE_INACTIVE_STATUSES:
            continue

        pitnum = item.get("pitnum", "")
        if not _is_valid_pitnum(pitnum):
            if status_val in ("DESPATCHED", "OUTTURN"):
                item["pitnum"] = "DESP"
            else:
                item["pitnum"] = ""

        # Enrich with parsed date and IN_DAYS
        item["recd_date_parsed"] = recd_dt
        item["IN_DAYS"] = (now - recd_dt).days

        coachno = item.get("coachno", "")
        # De-duplicate: keep the latest entry per coachno
        if coachno in seen_coaches:
            existing = seen_coaches[coachno]
            if recd_dt > existing["recd_date_parsed"]:
                seen_coaches[coachno] = item
        else:
            seen_coaches[coachno] = item

    cleaned = list(seen_coaches.values())
    _set_cached(cache_key, cleaned)
    logger.info("fetch_clean: %d records (from %d raw)", len(cleaned), len(raw))
    return cleaned

# 3. fetch_single(demandid) - retrieves details from Supabase (fast in-memory map lookup)
def fetch_single(demandid, bypass_cache=False):
    demandid = str(demandid).strip()
    
    if not bypass_cache:
        # Ensure cache is fresh
        demandid_map = _get_cached("demandid_map", CACHE_TTL_MASTER)
        if demandid_map is None:
            fetch_master()
            demandid_map = _get_cached("demandid_map", CACHE_TTL_MASTER) or {}

        coach = demandid_map.get(demandid)
        if coach:
            coachno = coach.get("coachno")
            
            # Get manual update from cached map
            manual_updates_map = _get_cached("manual_updates_map", CACHE_TTL_MASTER) or {}
            manual_update = manual_updates_map.get(str(coachno).strip()) if coachno else None

            # Construct the mock ERP single coach detail structure
            detail = {
                "demandid": coach.get("demandid"),
                "coachno": coach.get("coachno"),
                "status": coach.get("status"),
                "pohstatus": coach.get("status"),
                "repairid": coach.get("repair_type"),
                "repair_type": coach.get("repair_type"),
                "dvnid": coach.get("division"),
                "outdvnid": coach.get("division"),
                "indvnid": coach.get("division"),
                "corr_place": coach.get("corr_place", ""),
                "corr_comp": coach.get("corr_comp", ""),
                "presurveyhrs": coach.get("presurveyhrs", ""),
                "finalhrs": coach.get("finalhrs", ""),
                "last_poh": coach.get("last_poh", ""),
                "last_pohdate": coach.get("last_pohdate", ""),
                "tfrdate": coach.get("tfr_date", ""),
                "tfr_date": coach.get("tfr_date", ""),
                "despdate": coach.get("desp_date", ""),
                "desp_date": coach.get("desp_date", ""),
                "actualdespdate": coach.get("actualdespdate", ""),
                "pohdays": coach.get("pohdays", ""),
                "remarks": coach.get("remarks", ""),
                "noofdays": coach.get("noofdays", ""),
                "corrosion": coach.get("corrosion", ""),
                "corr_repair": coach.get("corr_repair", ""),
                "curheavylow": coach.get("curheavylow", "")
            }

            # Merge manual updates if they exist and are not stale
            if manual_update:
                recd_dt = _parse_date(coach.get("recd_date") or coach.get("recddate"))
                mu_date_str = manual_update.get("physical_date") or manual_update.get("vg_date") or ""
                mu_dt = _parse_date(mu_date_str)
                if not mu_dt and manual_update.get("updated_at"):
                    try:
                        iso_date = manual_update.get("updated_at").split('T')[0]
                        mu_dt = datetime.strptime(iso_date, "%Y-%m-%d")
                    except Exception:
                        pass
                
                is_mu_stale = False
                if mu_dt and recd_dt and mu_dt < recd_dt:
                    is_mu_stale = True
                    
                if not is_mu_stale:
                    detail["vg_status"] = manual_update.get("vg_status") or ""
                    detail["vg_date"] = manual_update.get("vg_date") or ""
                    detail["physical_status"] = manual_update.get("physical_status") or ""
                    detail["physical_date"] = manual_update.get("physical_date") or ""
                
            return detail

    # Fallback / Direct fetch: Query live intranet ERP directly
    try:
        from config import COACH_ERP_BASE_URL, COACH_ERP_USERNAME, COACH_ERP_PASSWORD
        sess = requests.Session()
        sess.post(f"{COACH_ERP_BASE_URL}/coach/login", data={
            "username": COACH_ERP_USERNAME,
            "password": COACH_ERP_PASSWORD
        }, timeout=5)
        
        resp = sess.post(f"{COACH_ERP_BASE_URL}/coach/pohmaster/singledata.html", data={"demandid": demandid}, headers={"X-Requested-With": "XMLHttpRequest"}, timeout=10)
        if resp.ok:
            detail = resp.json()
            if detail:
                # Map the fields to conform with downstream logic expects
                detail["demandid"] = str(detail.get("demandid") or demandid)
                detail["coachno"] = str(detail.get("coachno") or "")
                detail["presurveyhrs"] = detail.get("presurveyhrs") or ""
                detail["finalhrs"] = detail.get("finalhrs") or ""
                detail["last_poh"] = detail.get("last_poh") or ""
                detail["last_pohdate"] = detail.get("last_pohdate") or ""
                detail["desp_date"] = detail.get("desp_date") or detail.get("despdate") or ""
                detail["actualdespdate"] = detail.get("actualdespdate") or ""
                return detail
    except Exception as e:
        logger.error(f"Fallback live ERP fetch failed for demandid {demandid}: {e}")
    return {}

    coachno = coach.get("coachno")
    
    # Get manual update from cached map
    manual_updates_map = _get_cached("manual_updates_map", CACHE_TTL_MASTER) or {}
    manual_update = manual_updates_map.get(str(coachno).strip()) if coachno else None

    # Construct the mock ERP single coach detail structure
    detail = {
        "demandid": coach.get("demandid"),
        "coachno": coach.get("coachno"),
        "status": coach.get("status"),
        "pohstatus": coach.get("status"),
        "repairid": coach.get("repair_type"),
        "repair_type": coach.get("repair_type"),
        "dvnid": coach.get("division"),
        "outdvnid": coach.get("division"),
        "indvnid": coach.get("division"),
        "corr_place": coach.get("corr_place", ""),
        "corr_comp": coach.get("corr_comp", ""),
        "presurveyhrs": coach.get("presurveyhrs", ""),
        "finalhrs": coach.get("finalhrs", ""),
        "last_poh": coach.get("last_poh", ""),
        "last_pohdate": coach.get("last_pohdate", ""),
        "tfrdate": coach.get("tfr_date", ""),
        "tfr_date": coach.get("tfr_date", ""),
        "despdate": coach.get("desp_date", ""),
        "desp_date": coach.get("desp_date", ""),
        "actualdespdate": coach.get("actualdespdate", ""),
        "pohdays": coach.get("pohdays", ""),
        "remarks": coach.get("remarks", ""),
        "noofdays": coach.get("noofdays", ""),
        "corrosion": coach.get("corrosion", ""),
        "corr_repair": coach.get("corr_repair", ""),
        "curheavylow": coach.get("curheavylow", "")
    }

    # Merge manual updates if they exist
    if manual_update:
        recd_str = coach.get("recd_date") or coach.get("recddate") or ""
        recd_dt = _parse_date(recd_str)
        mu_date_str = manual_update.get("physical_date") or manual_update.get("vg_date") or ""
        mu_dt = _parse_date(mu_date_str)
        if not mu_dt and manual_update.get("updated_at"):
            try:
                iso_date = manual_update.get("updated_at").split('T')[0]
                mu_dt = datetime.strptime(iso_date, "%Y-%m-%d")
            except:
                pass
        
        is_mu_stale = False
        if mu_dt and recd_dt and mu_dt < recd_dt:
            is_mu_stale = True
            
        if is_mu_stale:
            manual_update = None

    if manual_update:
        detail["vg_status"] = manual_update.get("vg_status") or ""
        detail["vg_date"] = manual_update.get("vg_date") or ""
        detail["physical_status"] = manual_update.get("physical_status") or ""
        detail["physical_date"] = manual_update.get("physical_date") or ""
        
        vg_status = manual_update.get("vg_status", "")
        vg_date = manual_update.get("vg_date", "")
        phys_status = manual_update.get("physical_status", "")
        phys_date = manual_update.get("physical_date", "")
        
        # Outturn date (desp_date) prioritizes vg_date
        outturn_date = ""
        if vg_status == "Completed" and vg_date:
            outturn_date = vg_date
        elif phys_status == "Despatched" and phys_date:
            outturn_date = phys_date
            
        # Only override desp_date/despdate if they are empty/vacant in ERP
        erp_desp = str(coach.get("desp_date", "")).strip()
        if (not erp_desp or erp_desp in ("—", "None", "null", "")) and outturn_date:
            detail["desp_date"] = outturn_date
            detail["despdate"] = outturn_date
            
        # Only override actualdespdate if it is empty/vacant in ERP
        erp_act_desp = str(coach.get("actualdespdate", "")).strip()
        if (not erp_act_desp or erp_act_desp in ("—", "None", "null", "")) and phys_status == "Despatched":
            detail["actualdespdate"] = phys_date or datetime.now().strftime("%d/%m/%Y")

    return detail

# 4. fetch_year_built(coachno) - reads make and year_built (fast in-memory map lookup)
def fetch_year_built(coachno):
    coachno = str(coachno).strip()
    
    # Ensure cache is fresh
    coachno_map = _get_cached("coachno_map", CACHE_TTL_MASTER)
    if coachno_map is None:
        fetch_master()
        coachno_map = _get_cached("coachno_map", CACHE_TTL_MASTER) or {}

    coach = coachno_map.get(coachno)
    if coach:
        return {
            "year_built": coach.get("year_built", ""),
            "make": coach.get("make", ""),
            "manufacturing_date": "",
            "dvnid": coach.get("division", "")
        }

    return {}

_INACTIVE_STATUSES = {"COND", "BHOPAL", "RETURN"}
_LIVE_INACTIVE_STATUSES = {"COND", "BHOPAL", "RETURN"}

def get_coach_status(demandid):
    detail = fetch_single(demandid)
    return str(detail.get("status", "")).strip().upper()

def is_active(demandid):
    status = get_coach_status(demandid)
    return status not in _INACTIVE_STATUSES

