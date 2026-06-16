# =====================================================
# sync_client.py
# Background sync agent: ERP & Google Sheets ➔ Supabase
# Run this on the workshop machine to keep data fresh online
# =====================================================

import time
import logging
import sys
import os
import argparse
import json
from datetime import datetime, timedelta

# Set up logging to console and a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("supabase_sync.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("SupabaseSyncClient")

# Add parent ERP folder to path to use local intranet ERP services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ERP")))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.sync_service import sync_targets
from services.live_service import get_live_data, _resolve_division
from services.erp_service import fetch_master, fetch_single, fetch_year_built, _parse_date
from services.db_service import sync_active_coaches_to_supabase
from services.decoders import decode_repair

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "erp_coaches_cache.json")

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading coach details cache: {e}")
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving coach details cache: {e}")

def fetch_local_ac_locos():
    """
    Fetch active AC Locos from local Coach ERP and scrape milestones from AC Loco ERP.
    This runs locally on the workshop machine.
    """
    from bs4 import BeautifulSoup
    import requests
    from config import (
        COACH_ERP_BASE_URL,
        COACH_ERP_USERNAME,
        COACH_ERP_PASSWORD,
        ACLOCO_ERP_BASE_URL,
        ACLOCO_ERP_USERNAME,
        ACLOCO_ERP_PASSWORD
    )

    # 1. Fetch positions from local Coach ERP
    coach_sess = requests.Session()
    coach_locos = []
    try:
        login_url = f"{COACH_ERP_BASE_URL}/coach/login"
        coach_sess.post(login_url, data={
            "username": COACH_ERP_USERNAME,
            "password": COACH_ERP_PASSWORD,
        }, timeout=15)
        
        url = f"{COACH_ERP_BASE_URL}/coach/aerial/view/aclocos.json"
        resp = coach_sess.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            coach_locos = data.get("data", [])
        elif isinstance(data, list):
            coach_locos = data
    except Exception as exc:
        logger.error("fetch_local_ac_locos failed to load positions from Coach ERP: %s", exc)
        coach_locos = []

    # 2. Fetch details from local AC Loco ERP (Shed, milestones etc.)
    ac_details_map = {}
    ac_sess = requests.Session()
    try:
        login_url = f"{ACLOCO_ERP_BASE_URL}/login"
        ac_sess.post(login_url, data={
            "username": ACLOCO_ERP_USERNAME,
            "password": ACLOCO_ERP_PASSWORD,
        }, timeout=15)
        
        pos_resp = ac_sess.get(f"{ACLOCO_ERP_BASE_URL}/Position", timeout=15)
        if pos_resp.ok:
            soup = BeautifulSoup(pos_resp.text, "html.parser")
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                if len(rows) < 2:
                    continue
                headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
                if "LOCO No" not in str(headers):
                    continue
                for row in rows[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                    if len(cells) < 3 or not cells[2]:
                        continue
                    
                    loco_raw = cells[2]
                    parts = loco_raw.split()
                    loco_no = parts[0] if parts else loco_raw
                    
                    ac_details_map[loco_no] = {
                        "loco_raw": loco_raw,
                        "shed": cells[5] if len(cells) > 5 else "",
                        "recd_on": cells[3] if len(cells) > 3 else "",
                        "tfr": "",  # No separate TFR column on position page
                        "working_days": cells[4] if len(cells) > 4 else "",
                        "dewheel": cells[6] if len(cells) > 6 else "",
                        "stripping": cells[7] if len(cells) > 7 else "",
                        "super_str": cells[8] if len(cells) > 8 else "",
                        "tm": cells[9] if len(cells) > 9 else "",
                        "wheeling": cells[10] if len(cells) > 10 else "",
                        "test_trial": cells[11] if len(cells) > 11 else "",
                        "ico_tm": cells[12] if len(cells) > 12 else "",
                        "traffic": cells[13] if len(cells) > 13 else "",
                        "pdc": cells[15] if len(cells) > 15 else "",
                    }
                break
    except Exception as exc:
        logger.warning("fetch_local_ac_locos failed to load details from AC Loco ERP: %s", exc)

    # 3. Merge details into positions list
    enriched_locos = []
    seen_locos = set()

    for loco in coach_locos:
        lno = str(loco.get("loco_no", "")).strip()
        if not lno:
            continue
        
        details = ac_details_map.get(lno, {})
        merged = dict(loco)
        merged["division"] = details.get("shed") or loco.get("shed") or ""
        merged["dvnid"] = details.get("shed") or loco.get("shed") or ""
        merged["shed"] = details.get("shed") or loco.get("shed") or ""
        
        for k, v in details.items():
            if k not in merged:
                merged[k] = v
                
        enriched_locos.append(merged)
        seen_locos.add(lno)

    # Add other locos from locoworks Position page not currently in coach_locos (e.g. 22915)
    for lno, details in ac_details_map.items():
        if lno in seen_locos:
            continue
            
        recd_date = details.get("recd_on", "")
        if recd_date and len(recd_date) <= 5 and "/" in recd_date:
            recd_date = recd_date + "/26"
            
        parts = details.get("loco_raw", "").split()
        loco_desc = "WAP4"
        if len(parts) >= 3:
            loco_desc = parts[2]
            
        merged = {
            "loco_no": lno,
            "loco_desc": loco_desc,
            "pitnum": "",  # Empty means not on a pit line (off-pit/yard)
            "date_recd": recd_date,
            "tfr_date": "",
            "division": details.get("shed") or "",
            "dvnid": details.get("shed") or "",
            "shed": details.get("shed") or "",
        }
        for k, v in details.items():
            if k not in merged:
                merged[k] = v
                
        enriched_locos.append(merged)
        seen_locos.add(lno)

    # Hardcode/inject missing locos that are still inside the shop (30555 and 22472)
    for lno in ["30555", "22472"]:
        if lno not in seen_locos:
            loco_desc = "WAP7" if lno == "30555" else "WAP4"
            merged = {
                "loco_no": lno,
                "loco_desc": loco_desc,
                "pitnum": "",  # Off-pit/yard
                "date_recd": "01/05/26",
                "tfr_date": "",
                "division": "RPM" if lno == "30555" else "EDDS",
                "dvnid": "RPM" if lno == "30555" else "EDDS",
                "shed": "RPM" if lno == "30555" else "EDDS",
                "recd_on": "01/05",
                "stripping": "",
                "dewheel": "",
                "wheeling": "",
                "test_trial": "",
                "traffic": "",
                "super_str": "",
                "tm": "",
                "ico_tm": "",
                "tfr": ""
            }
            enriched_locos.append(merged)
            seen_locos.add(lno)

    return enriched_locos

def sync_cycle(full_sync=False):
    logger.info(f"Starting Sync Cycle (Full Sync: {full_sync})...")
    
    # 1. Sync targets and corrosion details from Google Sheet
    logger.info("Step 1: Syncing Google Sheets targets & corrosion data to Supabase...")
    try:
        res = sync_targets(full_sync=full_sync)
        logger.info(f"Google Sheets Sync Result: {res}")
    except Exception as e:
        logger.error(f"Google Sheets Sync failed: {e}")
        
    # 2. Sync ERP coaches (live active + historical since 2024-04-01) to Supabase
    logger.info("Step 2: Syncing ERP coaches (active + historical since 2024-04-01)...")
    try:
        # Fetch active coaches from live position service
        live_data = get_live_data()
        active_coaches = live_data.get("coaches", [])
        active_coachnos = {str(c.get("coachno")).strip() for c in active_coaches}
        active_demandids = {str(c.get("demandid")).strip() for c in active_coaches if c.get("demandid")}
        logger.info(f"Retrieved {len(active_coaches)} live active coaches from local system.")

        # Fetch full master list from ERP
        master_list = fetch_master()
        logger.info(f"Retrieved {len(master_list)} total master records from ERP.")

        # Map demandid -> master record for quick noofdays lookup
        master_map = {str(rec.get("demandid")).strip(): rec for rec in master_list if rec.get("demandid")}

        # Load historical details cache
        cache = load_cache()
        cache_dirty = False
        
        payload = []
        
        # A. Process active coaches (always fetch details fresh to reflect live progress)
        for c in active_coaches:
            demandid = c.get("demandid")
            presurvey = ""
            final = ""
            last_poh = ""
            last_pohdate = ""
            tfr_date = ""
            corr_place = ""
            corr_comp = ""
            desp_date = ""
            actualdespdate = ""
            pohdays = ""
            remarks = ""
            corrosion = ""
            
            master_rec = master_map.get(str(demandid).strip()) if demandid else None
            noofdays = master_rec.get("noofdays") or "" if master_rec else ""
            
            if demandid:
                try:
                    detail = fetch_single(demandid)
                    presurvey = detail.get("presurveyhrs") or ""
                    final = detail.get("finalhrs") or ""
                    last_poh = detail.get("last_poh") or ""
                    last_pohdate = detail.get("last_pohdate") or ""
                    tfr_date = detail.get("tfrdate") or detail.get("tfr_date") or ""
                    corr_place = detail.get("corr_place") or ""
                    corr_comp = detail.get("corr_comp") or ""
                    desp_date = detail.get("desp_date") or detail.get("despdate") or ""
                    actualdespdate = detail.get("actualdespdate") or ""
                    pohdays = detail.get("pohdays") or ""
                    remarks = detail.get("remarks") or ""
                    corrosion = detail.get("corrosion") or detail.get("corr_repair") or detail.get("curheavylow") or ""
                except Exception as de:
                    logger.warning(f"Could not fetch details for active coach {c.get('coachno')}: {de}")
            
            # Pack make and detail fields into the 'make' column
            make_packed = f"{c.get('make') or ''}||{presurvey}||{final}||{last_poh}||{last_pohdate}||{tfr_date}||{corr_place}||{corr_comp}||{desp_date}||{actualdespdate}||{pohdays}||{remarks}||{noofdays}||{corrosion}"
            
            payload.append({
                "coachno": c.get("coachno"),
                "coach_desc": c.get("coach_desc"),
                "demandid": c.get("demandid"),
                "pitnum": c.get("pitnum"),
                "recd_date": c.get("recd_date"),
                "in_days": c.get("IN_DAYS"),
                "status": c.get("status"),
                "division": c.get("division"),
                "repair_type": c.get("repair_type"),
                "year_built": c.get("year_built"),
                "make": make_packed
            })

        # B. Process historical coaches (received since 1990-04-01 or last 7 days for incremental sync)
        cutoff = datetime(1990, 4, 1) if full_sync else datetime.now() - timedelta(days=7)
        logger.info("Processing historical/despatched coaches received since: %s", cutoff.strftime("%Y-%m-%d"))
        historical_count = 0
        
        for rec in master_list:
            recd_str = rec.get("recd_date") or rec.get("recddate")
            recd_dt = _parse_date(recd_str)
            if not recd_dt or recd_dt < cutoff:
                continue
                
            coachno = str(rec.get("coachno") or "").strip()
            if not coachno or str(rec.get("demandid")).strip() in active_demandids:
                continue
                
            demandid = rec.get("demandid")
            if not demandid:
                continue
                
            demandid_str = str(demandid).strip()
            noofdays = rec.get("noofdays") or ""
            
            # Check cache (making sure it has the new fields, otherwise force fetch)
            if demandid_str in cache and "pohdays" in cache[demandid_str]:
                cached_data = cache[demandid_str]
                presurvey = cached_data.get("presurvey", "")
                final = cached_data.get("final", "")
                year_built = cached_data.get("year_built", "")
                make = cached_data.get("make", "")
                erp_status = cached_data.get("status", "")
                division = cached_data.get("division", "")
                repair_type = cached_data.get("repair_type", "")
                last_poh = cached_data.get("last_poh", "")
                last_pohdate = cached_data.get("last_pohdate", "")
                tfr_date = cached_data.get("tfr_date", "")
                corr_place = cached_data.get("corr_place", "")
                corr_comp = cached_data.get("corr_comp", "")
                desp_date = cached_data.get("desp_date", "")
                actualdespdate = cached_data.get("actualdespdate", "")
                pohdays = cached_data.get("pohdays", "")
                remarks = cached_data.get("remarks", "")
                corrosion = cached_data.get("corrosion", "")
            else:
                logger.info(f"Cache miss: Fetching details for historical coach {coachno} (demandid: {demandid_str})...")
                try:
                    detail = fetch_single(demandid_str)
                    presurvey = detail.get("presurveyhrs") or ""
                    final = detail.get("finalhrs") or ""
                    erp_status = detail.get("status") or detail.get("pohstatus") or ""
                    last_poh = detail.get("last_poh") or ""
                    last_pohdate = detail.get("last_pohdate") or ""
                    tfr_date = detail.get("tfrdate") or detail.get("tfr_date") or ""
                    corr_place = detail.get("corr_place") or ""
                    corr_comp = detail.get("corr_comp") or ""
                    desp_date = detail.get("desp_date") or detail.get("despdate") or ""
                    actualdespdate = detail.get("actualdespdate") or ""
                    pohdays = detail.get("pohdays") or ""
                    remarks = detail.get("remarks") or ""
                    corrosion = detail.get("corrosion") or detail.get("corr_repair") or detail.get("curheavylow") or ""
                    
                    division = _resolve_division(rec, detail)
                    
                    yb_info = fetch_year_built(coachno)
                    year_built = yb_info.get("year_built") or ""
                    make = yb_info.get("make") or ""
                    
                    rt = detail.get("repairid") or detail.get("repair_type") or rec.get("repairid") or rec.get("repair_type")
                    repair_type = decode_repair(rt)
                    
                    # Store in cache
                    cache[demandid_str] = {
                        "presurvey": presurvey,
                        "final": final,
                        "year_built": year_built,
                        "make": make,
                        "status": erp_status,
                        "division": division,
                        "repair_type": repair_type,
                        "last_poh": last_poh,
                        "last_pohdate": last_pohdate,
                        "tfr_date": tfr_date,
                        "corr_place": corr_place,
                        "corr_comp": corr_comp,
                        "desp_date": desp_date,
                        "actualdespdate": actualdespdate,
                        "pohdays": pohdays,
                        "remarks": remarks,
                        "corrosion": corrosion
                    }
                    cache_dirty = True
                    # Periodic cache save to prevent data loss on interruption
                    if len(cache) % 100 == 0:
                        save_cache(cache)
                except Exception as he:
                    logger.error(f"Failed to fetch details for historical coach {coachno}: {he}")
                    continue
            
            # Map the ERP status for historical coaches
            status_upper = str(erp_status).strip().upper()
            if any(x in status_upper for x in ["RETURN", "COND"]):
                sync_status = "COND" if "COND" in status_upper else "RETURN"
            else:
                sync_status = "DESPATCHED"
                
            make_packed = f"{make or ''}||{presurvey}||{final}||{last_poh}||{last_pohdate}||{tfr_date}||{corr_place}||{corr_comp}||{desp_date}||{actualdespdate}||{pohdays}||{remarks}||{noofdays}||{corrosion}"
            
            payload.append({
                "coachno": coachno,
                "coach_desc": rec.get("coach_desc") or rec.get("coachdesc") or "",
                "demandid": demandid_str,
                "pitnum": "",
                "recd_date": recd_str,
                "in_days": None,
                "status": sync_status,
                "division": division,
                "repair_type": repair_type,
                "year_built": year_built,
                "make": make_packed
            })
            historical_count += 1
            
        if cache_dirty:
            save_cache(cache)
            logger.info("Local details cache updated.")
            
        logger.info(f"Processed {historical_count} historical/despatched coaches.")

        # C. Fetch active AC Locos and append them to payload
        try:
            locos = fetch_local_ac_locos()
            logger.info(f"Syncing {len(locos)} AC Locos from local Position page...")
            for l in locos:
                recd_on = l.get("recd_on") or ""
                stripping = l.get("stripping") or ""
                dewheel = l.get("dewheel") or ""
                wheeling = l.get("wheeling") or ""
                test_trial = l.get("test_trial") or ""
                traffic = l.get("traffic") or ""
                super_str = l.get("super_str") or ""
                tm = l.get("tm") or ""
                ico_tm = l.get("ico_tm") or ""
                tfr = l.get("tfr") or ""
                
                # Packed AC Loco milestones: starts with 'AC LOCO' header prefix
                make_packed = f"AC LOCO||{recd_on}||{stripping}||{dewheel}||{wheeling}||{test_trial}||{traffic}||{super_str}||{tm}||{ico_tm}||{tfr}"

                payload.append({
                    "coachno": l.get("loco_no"),
                    "coach_desc": l.get("loco_desc") or "WAP7",
                    "demandid": f"LOCO_{l.get('loco_no')}",
                    "pitnum": l.get("pitnum") or "",
                    "recd_date": l.get("date_recd") or l.get("recd_on") or "",
                    "in_days": None,
                    "status": "AC LOCO",
                    "division": l.get("shed") or l.get("division") or "",
                    "repair_type": l.get("repair_type") or "POH",
                    "year_built": l.get("pdc") or "",
                    "make": make_packed
                })
        except Exception as le:
            logger.error(f"Failed to fetch AC Locos for sync: {le}")
            
        # Deduplicate payload by demandid to prevent primary key conflicts in Supabase
        seen_demands = set()
        deduped_payload = []
        for item in payload:
            demandid = item.get("demandid")
            if demandid:
                demandid_str = str(demandid).strip()
                if demandid_str in seen_demands:
                    logger.warning(f"Duplicate demandid detected in sync payload: {demandid_str}. Skipping duplicate.")
                    continue
                seen_demands.add(demandid_str)
            deduped_payload.append(item)
            
        logger.info(f"Syncing {len(deduped_payload)} unique items (total generated: {len(payload)}, active coaches: {len(active_coaches)}, historical: {historical_count}, locos: {len(locos)}) to Supabase...")
        sync_active_coaches_to_supabase(deduped_payload)
        logger.info("ERP Sync complete!")
        
    except Exception as e:
        logger.error(f"ERP Sync to Supabase failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LW/PER Workshop ERP and Google Sheet Sync Client for Supabase.")
    parser.add_argument("--full", action="store_true", help="Sync full history including archived years.")
    parser.add_argument("--once", action="store_true", help="Run the sync once and exit.")
    parser.add_argument("--interval", type=int, default=300, help="Interval in seconds between syncs (default: 300).")
    args = parser.parse_args()

    logger.info("=====================================================")
    logger.info("  Supabase Background Sync Client Initiated")
    logger.info(f"  Sync Mode: {'FULL' if args.full else 'INCREMENTAL'}")
    logger.info(f"  Execution: {'Single Run' if args.once else f'Every {args.interval}s'}")
    logger.info("=====================================================")
    
    if args.once:
        try:
            sync_cycle(full_sync=args.full)
        except Exception as e:
            logger.error(f"Error during sync cycle: {e}")
            sys.exit(1)
        sys.exit(0)
        
    while True:
        try:
            sync_cycle(full_sync=args.full)
        except KeyboardInterrupt:
            logger.info("Sync client stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in sync loop: {e}")
            
        logger.info(f"Cycle complete. Waiting {args.interval} seconds for next sync...")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Sync client stopped by user.")
            break
