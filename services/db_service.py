# =====================================================
# services/db_service.py
# Supabase HTTP REST API database interaction helpers
# =====================================================

import requests
import json
import os
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db.sqlite")

def _get_conn():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

SUPABASE_URL = "https://ykksfdiyczolhqnduwkh.supabase.co/rest/v1"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlra3NmZGl5Y3pvbGhxbmR1d2toIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTA3ODk0OCwiZXhwIjoyMDk2NjU0OTQ4fQ.67jORriOLnHf0WGcYtxr4dQkgFPw7JZEJm8xlfysWFM"

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
    """Create local_coach_updates table in SQLite if not exists."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS local_coach_updates (
                coachno TEXT PRIMARY KEY,
                plan_date TEXT,
                corrosion_hours REAL,
                corr_in_date TEXT,
                corr_comp TEXT,
                pdc TEXT,
                remarks TEXT,
                vg_status TEXT,
                vg_date TEXT,
                physical_status TEXT,
                physical_date TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Local SQLite database table local_coach_updates initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing SQLite database: {e}")

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

def save_google_corrosion_local(payload):
    """Write/merge corrosion records into the local SQLite database."""
    conn = _get_conn()
    cursor = conn.cursor()
    try:
        # Create table if not exists (to be safe!)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS google_corrosion (
                coachno TEXT PRIMARY KEY,
                corr_in_date TEXT,
                corrosion_status TEXT,
                bio_tank_status TEXT,
                lowering_status TEXT,
                furnishing_status TEXT,
                despatch_status TEXT,
                pdc TEXT,
                desp_date TEXT,
                remarks TEXT,
                source_tab TEXT
            )
        """)
        for item in payload:
            cursor.execute("""
                INSERT INTO google_corrosion (
                    coachno, corr_in_date, corrosion_status, bio_tank_status,
                    lowering_status, furnishing_status, despatch_status, pdc,
                    desp_date, remarks, source_tab
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(coachno) DO UPDATE SET
                    corr_in_date=excluded.corr_in_date,
                    corrosion_status=excluded.corrosion_status,
                    bio_tank_status=excluded.bio_tank_status,
                    lowering_status=excluded.lowering_status,
                    furnishing_status=excluded.furnishing_status,
                    despatch_status=excluded.despatch_status,
                    pdc=excluded.pdc,
                    desp_date=excluded.desp_date,
                    remarks=excluded.remarks,
                    source_tab=excluded.source_tab
            """, (
                str(item.get("coachno", "")).strip(),
                str(item.get("corr_in_date", "")).strip(),
                str(item.get("corrosion_status", "")).strip(),
                str(item.get("bio_tank_status", "")).strip(),
                str(item.get("lowering_status", "")).strip(),
                str(item.get("furnishing_status", "")).strip(),
                str(item.get("despatch_status", "")).strip(),
                str(item.get("pdc", "")).strip(),
                str(item.get("desp_date", "")).strip(),
                str(item.get("remarks", "")).strip(),
                str(item.get("source_tab", "")).strip()
            ))
        conn.commit()
        logger.info("Saved %d corrosion records to local SQLite.", len(payload))
    except Exception as e:
        logger.error(f"Error saving corrosion records to local SQLite: {e}")
    finally:
        conn.close()

def get_google_corrosion(coachno):
    """Fetch corrosion details for a coach from local SQLite, merging local overrides."""
    coachno = str(coachno).strip()
    digits = "".join(re.findall(r"\d+", coachno))
    
    # 1. Fetch from local overrides
    local_upd = get_manual_coach_update(coachno)
    
    # 2. Fetch from local google_corrosion table
    g_corr = {}
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM google_corrosion WHERE coachno = ?", (coachno,))
        row = cursor.fetchone()
        if not row and digits:
            cursor.execute("SELECT * FROM google_corrosion WHERE coachno LIKE ?", (f"%{digits}%",))
            row = cursor.fetchone()
        conn.close()
        if row:
            g_corr = dict(row)
    except Exception as e:
        logger.error(f"Error fetching google_corrosion from SQLite for {coachno}: {e}")
        
    # If we have local overrides, overlay them on top of GSheet data
    if local_upd:
        if local_upd.get("corr_in_date") is not None and local_upd.get("corr_in_date") != "":
            g_corr["corr_in_date"] = local_upd["corr_in_date"]
        if local_upd.get("corr_comp") is not None and local_upd.get("corr_comp") != "":
            g_corr["corrosion_status"] = local_upd["corr_comp"]
        if local_upd.get("pdc") is not None and local_upd.get("pdc") != "":
            g_corr["pdc"] = local_upd["pdc"]
        if local_upd.get("remarks") is not None and local_upd.get("remarks") != "":
            g_corr["remarks"] = local_upd["remarks"]
        if local_upd.get("physical_status") is not None and local_upd.get("physical_status") != "":
            g_corr["despatch_status"] = local_upd["physical_status"]
        if local_upd.get("physical_date") is not None and local_upd.get("physical_date") != "":
            g_corr["desp_date"] = local_upd["physical_date"]
            
    if g_corr:
        return g_corr
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

def get_last_coach_movement(coachno):
    """Fetch the last movement entry for a coach from Supabase."""
    url = f"{SUPABASE_URL}/coach_movements?coachno=eq.{coachno}&order=id.desc&limit=1"
    resp = requests.get(url, headers=get_headers())
    resp.raise_for_status()
    data = resp.json()
    return data[0] if data else None

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
    """Fetch manually updated coach fields (VG & physical despatch details) from local SQLite."""
    coachno = str(coachno).strip()
    digits = "".join(re.findall(r"\d+", coachno))
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM local_coach_updates WHERE coachno = ?", (coachno,))
        row = cursor.fetchone()
        if not row and digits:
            cursor.execute("SELECT * FROM local_coach_updates WHERE coachno LIKE ?", (f"%{digits}%",))
            row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception as e:
        logger.error(f"Error fetching manual updates from SQLite for {coachno}: {e}")
    return None

def upsert_manual_coach_update(coachno, vg_status, vg_date, physical_status, physical_date,
                               plan_date=None, corrosion_hours=None, corr_in_date=None,
                               corr_comp=None, pdc=None, remarks=None):
    """Upsert manually updated coach fields to local SQLite database."""
    coachno = str(coachno).strip()
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM local_coach_updates WHERE coachno = ?", (coachno,))
        row = cursor.fetchone()
        
        if row:
            p_date = plan_date if plan_date is not None else row["plan_date"]
            c_hours = corrosion_hours if corrosion_hours is not None else row["corrosion_hours"]
            c_in = corr_in_date if corr_in_date is not None else row["corr_in_date"]
            c_comp = corr_comp if corr_comp is not None else row["corr_comp"]
            p_dc = pdc if pdc is not None else row["pdc"]
            rem = remarks if remarks is not None else row["remarks"]
            
            vg_s = vg_status if vg_status is not None else row["vg_status"]
            vg_d = vg_date if vg_date is not None else row["vg_date"]
            phys_s = physical_status if physical_status is not None else row["physical_status"]
            phys_d = physical_date if physical_date is not None else row["physical_date"]
            
            cursor.execute("""
                UPDATE local_coach_updates
                SET plan_date = ?, corrosion_hours = ?, corr_in_date = ?, corr_comp = ?,
                    pdc = ?, remarks = ?, vg_status = ?, vg_date = ?,
                    physical_status = ?, physical_date = ?
                WHERE coachno = ?
            """, (p_date, c_hours, c_in, c_comp, p_dc, rem, vg_s, vg_d, phys_s, phys_d, coachno))
        else:
            cursor.execute("""
                INSERT INTO local_coach_updates (
                    coachno, plan_date, corrosion_hours, corr_in_date, corr_comp,
                    pdc, remarks, vg_status, vg_date, physical_status, physical_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (coachno, plan_date, corrosion_hours, corr_in_date, corr_comp,
                  pdc, remarks, vg_status, vg_date, physical_status, physical_date))
        conn.commit()
        conn.close()
        
        # Clear local cache in erp_service
        try:
            from services.erp_service import cache_clear
            cache_clear()
        except Exception as ex:
            logger.error("Error clearing erp cache: %s", ex)
            
        return True
    except Exception as e:
        logger.error(f"Error upserting manual updates to SQLite for {coachno}: {e}")
        raise e

# --- erp_active_coaches ---

def sync_active_coaches_to_supabase(coaches_list, clear_table=True):
    """Sync active ERP coaches to Supabase (clear or upsert in chunks)."""
    # 1. Clear old entries only if requested (full sync)
    if clear_table:
        logger.info("Clearing erp_active_coaches table for full sync...")
        try:
            url_delete = f"{SUPABASE_URL}/erp_active_coaches?coachno=neq."
            resp = requests.delete(url_delete, headers=get_headers())
            resp.raise_for_status()
            logger.info("Successfully cleared all existing records.")
        except Exception as delete_ex:
            logger.error("Failed to clear erp_active_coaches table: %s", delete_ex)
            raise delete_ex
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
            if resp.status_code >= 400:
                logger.error("Supabase returned %d: %s", resp.status_code, resp.text)
            resp.raise_for_status()
            logger.info("Uploaded chunk of %d records (total synced: %d/%d)", len(chunk), min(i + chunk_size, len(coaches_list)), len(coaches_list))

# Initialize database checks
init_db()


def get_historical_poh_records(coachno):
    """Fetch manual POH history records for a coach from Supabase or local cache."""
    try:
        import config
        import requests
        headers = {
            "apikey": getattr(config, "SUPABASE_KEY", ""),
            "Authorization": f"Bearer {getattr(config, 'SUPABASE_KEY', '')}"
        }
        sb_url = getattr(config, "SUPABASE_URL", "")
        if sb_url and headers["apikey"]:
            url = f"{sb_url}/historical_poh_records?coachno=eq.{coachno}&select=*"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                return res.json()
    except Exception:
        pass
    return []
