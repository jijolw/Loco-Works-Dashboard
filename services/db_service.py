# =====================================================
# services/db_service.py
# Supabase HTTP REST API database interaction helpers
# =====================================================

import requests
import json
import os
import logging
import re
import time
from datetime import datetime

logger = logging.getLogger(__name__)

from config import SUPABASE_URL, SUPABASE_KEY


def get_headers(prefer=None):
    """Return headers required for Supabase REST requests."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers

def init_db():
    """No-op for HTTP-based Supabase setup since schema is created in SQL editor."""
    logger.info("Supabase database REST layers initialized successfully.")

# --- outturn_targets ---

def delete_all_outturn_targets():
    """Clear all outturn targets from Supabase."""
    url = f"{SUPABASE_URL}/outturn_targets?id=gt.0"
    resp = requests.delete(url, headers=get_headers())
    resp.raise_for_status()

def delete_outturn_targets_by_fy(fy):
    """Clear outturn targets for a specific financial year from Supabase."""
    url = f"{SUPABASE_URL}/outturn_targets?fy=eq.{fy}"
    resp = requests.delete(url, headers=get_headers())
    resp.raise_for_status()

def insert_outturn_targets_bulk(payload):
    """Insert multiple target rows to Supabase in a single batch."""
    url = f"{SUPABASE_URL}/outturn_targets"
    resp = requests.post(url, data=json.dumps(payload), headers=get_headers())
    resp.raise_for_status()

def get_targets_vs_achievement(fy):
    """Fetch target vs achievement comparisons for a FY from Supabase."""
    url = f"{SUPABASE_URL}/outturn_targets?fy=eq.{fy}&select=month,stock_type,schedule,ac_nac,target_qty,achieved_qty,working_days"
    resp = requests.get(url, headers=get_headers())
    resp.raise_for_status()
    return resp.json()

# --- google_corrosion ---

def delete_all_google_corrosion():
    """Clear all corrosion records from Supabase."""
    url = f"{SUPABASE_URL}/google_corrosion?coachno=neq."
    resp = requests.delete(url, headers=get_headers())
    resp.raise_for_status()

def upsert_google_corrosion_bulk(payload):
    """Upsert multiple corrosion records to Supabase in a single batch."""
    url = f"{SUPABASE_URL}/google_corrosion"
    resp = requests.post(url, data=json.dumps(payload), headers=get_headers(prefer="resolution=merge-duplicates"))
    resp.raise_for_status()

_corrosion_cache = {}

def get_google_corrosion(coachno):
    """Fetch corrosion details for a coach from Supabase (optimized caching)."""
    coachno = str(coachno).strip()
    
    # Check if cache is expired or not populated
    cache_entry = _corrosion_cache.get("all_corrosion")
    now_ts = time.time()
    
    if not cache_entry or (now_ts - cache_entry["ts"] > 120): # 2 min TTL
        try:
            url = f"{SUPABASE_URL}/google_corrosion?select=*"
            resp = requests.get(url, headers=get_headers(), timeout=30)
            resp.raise_for_status()
            rows = resp.json()
            
            # Map by coachno
            corrosion_map = {}
            for r in rows:
                cno = str(r.get("coachno") or "").strip()
                if cno:
                    corrosion_map[cno] = r
            
            _corrosion_cache["all_corrosion"] = {
                "ts": now_ts,
                "map": corrosion_map
            }
        except Exception as e:
            logger.error(f"Error pre-fetching all google corrosion records: {e}")
            # Keep cached version even if expired if fetch fails
            if not cache_entry:
                return None
            
    # Lookup in cache
    cache_entry = _corrosion_cache.get("all_corrosion")
    if cache_entry and coachno in cache_entry["map"]:
        return cache_entry["map"][coachno]
        
    # Digits fallback lookup in cached map
    digits = "".join(re.findall(r"\d+", coachno))
    if digits and cache_entry:
        for cno, r in cache_entry["map"].items():
            if digits in cno:
                return r
                
    return None

def get_not_despatched_corrosion():
    """Fetch all active (not despatched) corrosion entries from Supabase."""
    url = f"{SUPABASE_URL}/google_corrosion"
    resp = requests.get(url, headers=get_headers())
    resp.raise_for_status()
    rows = resp.json()
    
    # Filter not-despatched coaches in python
    filtered = []
    for r in rows:
        desp_date = str(r.get("desp_date") or "").strip()
        desp_status = str(r.get("despatch_status") or "").strip().lower()
        if (not desp_date or desp_date in ("", "—")) and (not desp_status or "despatched" not in desp_status):
            filtered.append(r)
    return filtered

# --- coach_movements ---

_movements_cache = {}

def prefetch_last_movements():
    """Prefetch the last movement for all coaches in one query and cache them."""
    now_ts = time.time()
    cache_entry = _movements_cache.get("all_movements")
    if cache_entry and (now_ts - cache_entry["ts"] < 60):  # 60s TTL
        return cache_entry["map"]

    try:
        # Fetch the latest 3000 movements in descending order to avoid pagination cutoff
        url = f"{SUPABASE_URL}/coach_movements?select=coachno,from_location,to_location,timestamp&order=id.desc&limit=3000"
        resp = requests.get(url, headers=get_headers(), timeout=30)
        resp.raise_for_status()
        rows = resp.json()

        movements_map = {}
        for r in rows:
            cno = str(r.get("coachno") or "").strip()
            if cno and cno not in movements_map:
                # Keep the first seen (latest) record for each coach
                movements_map[cno] = r

        _movements_cache["all_movements"] = {
            "ts": now_ts,
            "map": movements_map
        }
        return movements_map
    except Exception as e:
        logger.error(f"Error pre-fetching coach movements: {e}")
        if cache_entry:
            return cache_entry["map"]
        return {}

def get_last_coach_movement(coachno):
    """Fetch the last movement entry for a coach from cached prefetched movements."""
    coachno = str(coachno).strip()
    movements_map = prefetch_last_movements()
    return movements_map.get(coachno)

def insert_coach_movement(coachno, from_loc, to_loc, timestamp):
    """Insert a coach movement entry to Supabase."""
    url = f"{SUPABASE_URL}/coach_movements"
    payload = {
        "coachno": coachno,
        "from_location": from_loc,
        "to_location": to_loc,
        "timestamp": timestamp
    }
    resp = requests.post(url, data=json.dumps(payload), headers=get_headers())
    resp.raise_for_status()

def get_coach_movements_history(coachno):
    """Fetch the complete movement timeline of a coach from Supabase."""
    url = f"{SUPABASE_URL}/coach_movements?coachno=eq.{coachno}&select=from_location,to_location,timestamp&order=id.asc"
    resp = requests.get(url, headers=get_headers())
    resp.raise_for_status()
    return resp.json()

# --- manual_coach_updates ---

def get_manual_coach_update(coachno):
    """Fetch manually updated coach fields (VG & physical despatch details) from Supabase."""
    coachno = str(coachno).strip()
    url = f"{SUPABASE_URL}/manual_coach_updates?coachno=eq.{coachno}&select=vg_status,vg_date,physical_status,physical_date"
    try:
        resp = requests.get(url, headers=get_headers())
        resp.raise_for_status()
        rows = resp.json()
        return rows[0] if rows else None
    except Exception as e:
        logger.error(f"Error fetching manual updates for coach {coachno}: {e}")
        return None

def upsert_manual_coach_update(coachno, vg_status, vg_date, physical_status, physical_date):
    """Upsert manually updated coach fields to Supabase."""
    url = f"{SUPABASE_URL}/manual_coach_updates"
    payload = {
        "coachno": str(coachno).strip(),
        "vg_status": vg_status,
        "vg_date": vg_date,
        "physical_status": physical_status,
        "physical_date": physical_date
    }
    resp = requests.post(url, data=json.dumps(payload), headers=get_headers(prefer="resolution=merge-duplicates"))
    resp.raise_for_status()
    return True

def upsert_manual_coach_updates_bulk(payload):
    """Upsert multiple manual coach updates to Supabase in a single batch."""
    url = f"{SUPABASE_URL}/manual_coach_updates"
    resp = requests.post(url, data=json.dumps(payload), headers=get_headers(prefer="resolution=merge-duplicates"))
    resp.raise_for_status()
    return True


# --- erp_active_coaches ---

def sync_active_coaches_to_supabase(coaches_list, clear_table=True):
    """Sync active ERP coaches to Supabase (clear or upsert in chunks)."""
    # 1. Clear old entries only if requested (full sync)
    if clear_table:
        logger.info("Clearing erp_active_coaches table for full sync...")
        url_delete = f"{SUPABASE_URL}/erp_active_coaches?coachno=neq."
        resp = requests.delete(url_delete, headers=get_headers())
        resp.raise_for_status()
    else:
        logger.info("Incremental sync: keeping existing table, upserting recent records...")
    
    # 2. Insert/upsert new entries in chunks of 1000
    if coaches_list:
        chunk_size = 1000
        url_insert = f"{SUPABASE_URL}/erp_active_coaches"
        headers = get_headers(prefer="resolution=merge-duplicates" if not clear_table else None)
        for i in range(0, len(coaches_list), chunk_size):
            chunk = coaches_list[i : i + chunk_size]
            resp = requests.post(url_insert, data=json.dumps(chunk), headers=headers)
            resp.raise_for_status()
            logger.info("Uploaded chunk of %d records (total synced: %d/%d)", len(chunk), min(i + chunk_size, len(coaches_list)), len(coaches_list))

# --- historical_poh_records ---

def get_historical_poh_records(coachno):
    """Fetch manual historical POH records for a coach from Supabase."""
    coachno = str(coachno).strip()
    url = f"{SUPABASE_URL}/historical_poh_records?coachno=eq.{coachno}&select=*&order=poh_date.desc"
    try:
        resp = requests.get(url, headers=get_headers())
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Error fetching historical POH records for coach {coachno}: {e}")
        return []

def add_historical_poh_record(coachno, poh_date, workshop, corrosion_hours, remarks):
    """Insert a new manual historical POH record to Supabase."""
    url = f"{SUPABASE_URL}/historical_poh_records"
    payload = {
        "coachno": str(coachno).strip(),
        "poh_date": poh_date,
        "workshop": str(workshop).strip(),
        "corrosion_hours": float(corrosion_hours),
        "remarks": str(remarks or "").strip()
    }
    resp = requests.post(url, data=json.dumps(payload), headers=get_headers(prefer="return=representation"))
    resp.raise_for_status()
    res_data = resp.json()
    if isinstance(res_data, list) and len(res_data) > 0:
        return res_data[0]
    return res_data

def delete_historical_poh_record(record_id):
    """Delete a manual historical POH record from Supabase."""
    url = f"{SUPABASE_URL}/historical_poh_records?id=eq.{record_id}"
    resp = requests.delete(url, headers=get_headers())
    resp.raise_for_status()
    return True

# Initialize database checks
init_db()
