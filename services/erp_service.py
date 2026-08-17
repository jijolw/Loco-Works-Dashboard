# =====================================================
# services/erp_service.py
# LW/PER Workshop Intelligence System
# Unified ERP data-fetching service (replaces utils.py)
# =====================================================

"""
Provides authenticated HTTP sessions and data-fetching helpers
for the Coach ERP (http://10.185.78.45) and AC Loco ERP
(http://locoworks/acloco).

Caching
-------
A simple dict + timestamp approach is used instead of streamlit
cache.  Each cache entry is a tuple (timestamp, data).  If the
entry is older than the configured TTL it is re-fetched.
"""

import time
import logging
from datetime import datetime, timedelta
from collections import OrderedDict

import requests

# ── Project config ────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import (
    COACH_ERP_BASE_URL,
    COACH_ERP_USERNAME,
    COACH_ERP_PASSWORD,
    ACLOCO_ERP_BASE_URL,
    ACLOCO_ERP_USERNAME,
    ACLOCO_ERP_PASSWORD,
    CACHE_TTL_MASTER,
    CACHE_TTL_SINGLE,
    CACHE_TTL_STATIC,
)

logger = logging.getLogger(__name__)

# =====================================================
# Simple TTL cache
# =====================================================

_cache: dict = {}   # key → (timestamp, data)


def _get_cached(key, ttl):
    """Return cached data if still valid, else None."""
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts > ttl:
        return None
    return data


def _set_cached(key, data):
    """Store data in cache with current timestamp."""
    _cache[key] = (time.time(), data)


def cache_clear(key=None):
    """Invalidate one key or the entire cache."""
    if key is None:
        _cache.clear()
    else:
        _cache.pop(key, None)


# =====================================================
# Session management
# =====================================================

_sessions: dict = {}   # "coach" / "acloco" → requests.Session


def get_session():
    """
    Return a ``requests.Session`` authenticated against Coach ERP.

    The session is created once and reused.  If the login fails the
    function raises ``RuntimeError``.
    """
    if "coach" in _sessions:
        return _sessions["coach"]

    sess = requests.Session()
    login_url = f"{COACH_ERP_BASE_URL}/coach/login"
    payload = {
        "username": COACH_ERP_USERNAME,
        "password": COACH_ERP_PASSWORD,
    }
    try:
        resp = sess.post(login_url, data=payload, timeout=30)
        resp.raise_for_status()
        logger.info("Coach ERP login successful")
    except requests.RequestException as exc:
        logger.error("Coach ERP login failed: %s", exc)
        raise RuntimeError(f"Coach ERP login failed: {exc}") from exc

    _sessions["coach"] = sess
    return sess


def get_ac_session():
    """
    Return a ``requests.Session`` authenticated against AC Loco ERP.
    """
    if "acloco" in _sessions:
        return _sessions["acloco"]

    sess = requests.Session()
    login_url = f"{ACLOCO_ERP_BASE_URL}/login"
    payload = {
        "username": ACLOCO_ERP_USERNAME,
        "password": ACLOCO_ERP_PASSWORD,
    }
    try:
        resp = sess.post(login_url, data=payload, timeout=30)
        resp.raise_for_status()
        logger.info("AC Loco ERP login successful")
    except requests.RequestException as exc:
        logger.error("AC Loco ERP login failed: %s", exc)
        raise RuntimeError(f"AC Loco ERP login failed: {exc}") from exc

    _sessions["acloco"] = sess
    return sess


def reset_sessions():
    """Close and discard all cached sessions (e.g. on auth error)."""
    for key in list(_sessions):
        try:
            _sessions[key].close()
        except Exception:
            pass
    _sessions.clear()


# =====================================================
# Data-fetching helpers
# =====================================================

# Payload template for the DataTables-style listdata2 endpoint
_MASTER_PAYLOAD = {
    "draw": "1",
    "start": "0",
    "length": "25000",
    "search[value]": "",
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

_XHR_HEADERS = {"X-Requested-With": "XMLHttpRequest"}
_is_offline = False


def fetch_master():
    """
    Fetch the full coach master list from pohmaster/listdata2.html.

    Returns
    -------
    list[dict]
        Raw coach records as returned by the ERP.
    """
    global _is_offline
    cache_key = "master_list"
    cached = _get_cached(cache_key, CACHE_TTL_MASTER)
    if cached is not None:
        return cached

    import json
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "erp_master_cache.json")

    if _is_offline:
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    records = json.load(f)
                _set_cached(cache_key, records)
                logger.info("fetch_master: loaded %d records from fallback cache (offline mode active)", len(records))
                return records
            except Exception as e:
                logger.error("Failed to read fallback cache in offline mode: %s", e)
        raise RuntimeError("fetch_master failed: offline mode active and fallback cache missing")

    sess = get_session()
    url = f"{COACH_ERP_BASE_URL}/coach/pohmaster/listdata2.html"
    try:
        resp = sess.post(url, data=_MASTER_PAYLOAD, headers=_XHR_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        records = data.get("data", [])
        
        # Save fresh copy to disk cache
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            logger.error("Failed to write erp_master_cache.json: %s", e)
            
    except Exception as exc:
        _is_offline = True
        logger.error("fetch_master live query failed (switching to offline mode): %s", exc)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    records = json.load(f)
                logger.info("fetch_master: loaded %d records from fallback cache", len(records))
            except Exception as e:
                logger.error("Failed to read erp_master_cache.json: %s", e)
                raise RuntimeError(f"fetch_master failed and fallback unavailable: {exc}") from exc
        else:
            raise RuntimeError(f"fetch_master failed and fallback cache missing: {exc}") from exc

    _set_cached(cache_key, records)
    logger.info("fetch_master: %d records", len(records))
    return records


def _merge_manual_updates(data):
    if not data:
        return data
    try:
        coachno = data.get("coachno")
        if coachno:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db.sqlite")
            import sqlite3
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM local_coach_updates WHERE coachno = ?", (str(coachno).strip(),))
                row = cursor.fetchone()
                if row:
                    local_upd = dict(row)
                    if local_upd.get("corr_in_date"):
                        data["corr_place"] = local_upd["corr_in_date"]
                    if local_upd.get("corr_comp"):
                        data["corr_comp"] = local_upd["corr_comp"]
                    if local_upd.get("pdc"):
                        data["pdc_date"] = local_upd["pdc"]
                        data["plandate"] = local_upd["pdc"]
                    if local_upd.get("remarks"):
                        data["remarks"] = local_upd["remarks"]
                    if local_upd.get("physical_date"):
                        data["actualdespdate"] = local_upd["physical_date"]
                    if local_upd.get("vg_date"):
                        data["desp_date"] = local_upd["vg_date"]
                        data["despdate"] = local_upd["vg_date"]
                    if local_upd.get("physical_status"):
                        data["physical_status"] = local_upd["physical_status"]
                    if local_upd.get("vg_status"):
                        data["vg_status"] = local_upd["vg_status"]
                conn.close()
    except Exception as e:
        logger.error("Failed to merge manual updates in fetch_single: %s", e)
    return data


def fetch_single(demandid, bypass_cache=False):
    """
    Fetch detailed data for a single coach by its demand ID.

    Parameters
    ----------
    demandid : str | int
        The ERP demand ID.
    bypass_cache : bool, optional
        Bypass in-memory cache and fetch from live ERP directly, by default False.

    Returns
    -------
    dict
        Coach detail record, or empty dict on failure.
    """
    global _is_offline
    demandid = str(demandid).strip()
    cache_key = f"single_{demandid}"
    if not bypass_cache:
        cached = _get_cached(cache_key, CACHE_TTL_SINGLE)
        if cached is not None:
            return cached

    sess = get_session()
    url = f"{COACH_ERP_BASE_URL}/coach/pohmaster/singledata.html"
    payload = {"demandid": demandid}
    try:
        if _is_offline:
            raise RuntimeError("Offline mode is active")
        resp = sess.post(url, data=payload, headers=_XHR_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("fetch_single(%s) live fetch failed (trying cache fallback): %s", demandid, exc)
        # Try to load from erp_coaches_cache.json disk cache fallback
        cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "erp_coaches_cache.json")
        if os.path.exists(cache_file):
            try:
                import json
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                if demandid in cache_data:
                    c = cache_data[demandid]
                    data = {
                        "demandid": demandid,
                        "coachno": c.get("coachno", ""),
                        "status": c.get("status", ""),
                        "pohstatus": c.get("status", ""),
                        "repair_type": c.get("repair_type", ""),
                        "repairid": c.get("repair_type", ""),
                        "division": c.get("division", ""),
                        "dvnid": c.get("division", ""),
                        "year_built": c.get("year_built", ""),
                        "make": c.get("make", ""),
                        "presurveyhrs": c.get("presurvey", ""),
                        "finalhrs": c.get("final", ""),
                        "last_poh": c.get("last_poh", ""),
                        "last_pohdate": c.get("last_pohdate", ""),
                        "tfrdate": c.get("tfr_date", ""),
                        "tfr_date": c.get("tfr_date", ""),
                        "corr_place": c.get("corr_place", ""),
                        "corr_comp": c.get("corr_comp", ""),
                        "despdate": c.get("desp_date", ""),
                        "desp_date": c.get("desp_date", ""),
                        "actualdespdate": c.get("actualdespdate", ""),
                        "pohdays": c.get("pohdays", ""),
                        "remarks": c.get("remarks", ""),
                        "corrosion": c.get("corrosion", ""),
                        "plan_date": c.get("plandate", ""),
                        "plandate": c.get("plandate", "")
                    }
                    data = _merge_manual_updates(data)
                    _set_cached(cache_key, data)
                    return data
            except Exception as ce:
                logger.error("Failed to read erp_coaches_cache.json: %s", ce)
        return {}

    data = _merge_manual_updates(data)
    _set_cached(cache_key, data)
    return data


def fetch_year_built(coachno):
    """
    Fetch year-built and manufacturing data from coachmaster.

    Parameters
    ----------
    coachno : str
        The coach number (e.g. '07178 SER CN').

    Returns
    -------
    dict
        Keys: year_built, make, manufacturing_date, or empty dict.
    """
    global _is_offline
    coachno = str(coachno).strip()
    cache_key = f"yearbuilt_{coachno}"
    cached = _get_cached(cache_key, CACHE_TTL_STATIC)
    if cached is not None:
        return cached

    sess = get_session()
    url = f"{COACH_ERP_BASE_URL}/coach/coachmaster/singledata.html"
    payload = {"coachno": coachno}
    try:
        if _is_offline:
            raise RuntimeError("Offline mode is active")
        resp = sess.post(url, data=payload, headers=_XHR_HEADERS, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
        result = {
            "year_built": raw.get("year_built", ""),
            "make": raw.get("make", ""),
            "manufacturing_date": raw.get("manufacturing_date", ""),
            "dvnid": raw.get("dvnid", ""),
        }
    except Exception as exc:
        logger.warning("fetch_year_built(%s) live query failed (trying cache fallback): %s", coachno, exc)
        cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "erp_coaches_cache.json")
        if os.path.exists(cache_file):
            try:
                import json
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                master_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "erp_master_cache.json")
                if os.path.exists(master_file):
                    with open(master_file, "r", encoding="utf-8") as mf:
                        master_records = json.load(mf)
                    for rec in master_records:
                        if str(rec.get("coachno")).strip() == coachno:
                            d_id = rec.get("demandid")
                            if d_id in cache_data:
                                c = cache_data[d_id]
                                result = {
                                    "year_built": c.get("year_built", ""),
                                    "make": c.get("make", ""),
                                    "manufacturing_date": "",
                                    "dvnid": rec.get("dvnid", "")
                                }
                                _set_cached(cache_key, result)
                                return result
            except Exception as ce:
                logger.error("Failed to read fallback for fetch_year_built: %s", ce)
        result = {
            "year_built": "",
            "make": "",
            "manufacturing_date": "",
            "dvnid": "",
        }

    _set_cached(cache_key, result)
    return result


# =====================================================
# Cleaning & enrichment
# =====================================================

def _parse_date(date_str):
    """Try to parse an ERP date string into a datetime. Returns None on failure."""
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


def fetch_clean():
    """
    Fetch master data and apply cleaning rules:

    1. Filter out records with invalid / empty pitnums (except active/despatch-pending ones)
    2. Remove stale records (recd_date > 365 days ago)
    3. De-duplicate by coachno (keep latest)
    4. Parse date fields into datetime objects
    5. Calculate IN_DAYS from recd_date

    Returns
    -------
    list[dict]
        Cleaned coach records.
    """
    cache_key = "clean_master"
    cached = _get_cached(cache_key, CACHE_TTL_MASTER)
    if cached is not None:
        return cached

    from services.decoders import decode_family

    raw = fetch_master()
    now = datetime.now()
    cutoff = now - timedelta(days=365)
    cleaned = []
    seen_coaches = OrderedDict()

    # Fetch manual updates from local SQLite instead of Supabase
    manual_updates_map = {}
    try:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db.sqlite")
        if os.path.exists(db_path):
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Ensure table exists
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
            cursor.execute("SELECT * FROM local_coach_updates")
            for mu in cursor.fetchall():
                coachno = mu["coachno"]
                if coachno:
                    manual_updates_map[str(coachno).strip()] = dict(mu)
            conn.close()
    except Exception as exc:
        logger.warning("Failed to fetch manual updates from local SQLite: %s", exc)

    for rec in raw:
        item = dict(rec)
        # Parse received date
        recd_str = item.get("recd_date", "") or item.get("recddate", "")
        recd_dt = _parse_date(recd_str)

        # Skip if no received date
        if recd_dt is None:
            continue

        # Check actualdespdate (physically despatched in ERP)
        act_desp = str(item.get("actualdespdate") or "").strip()
        has_actual_desp = act_desp and act_desp.lower() not in ("none", "null", "nan", "")
        
        # Check manual update override in Supabase
        coachno = item.get("coachno")
        is_manually_pending = False
        if coachno:
            mu = manual_updates_map.get(str(coachno).strip())
            if mu:
                phys_status = mu.get("physical_status", "")
                if phys_status == "Despatched":
                    has_actual_desp = True
                elif phys_status != "Despatched":
                    is_manually_pending = True
                    
        if has_actual_desp:
            continue

        # Skip stale (>365 days) unless it is manually pending
        if recd_dt < cutoff and not is_manually_pending:
            continue

        # Check paper despatch threshold: if desp_date is set and older than 15 days, treat as physically despatched!
        # ONLY for non-SPECIAL, non-LOCO, and non-TW families
        # UPDATED: Removed 15-day paper despatch cutoff to keep FND coaches inside the workshop until physically despatched.
        # desp_date = item.get("desp_date") or item.get("despdate") or ""
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

        status_val = str(item.get("status") or item.get("pohstatus") or "").strip().upper()
        if status_val in {"COND", "BHOPAL", "RETURN"}:
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

    # Inject manual plan dates and enrich coach fields from SQLite
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db.sqlite")
    if os.path.exists(db_path):
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 1. Load manual_outturn_plans
            cursor.execute("CREATE TABLE IF NOT EXISTS manual_outturn_plans (coachno TEXT PRIMARY KEY, plan_date TEXT)")
            cursor.execute("SELECT coachno, plan_date FROM manual_outturn_plans")
            manual_plans = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 2. Load local_coach_updates plan_date
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
            cursor.execute("SELECT coachno, plan_date FROM local_coach_updates WHERE plan_date IS NOT NULL AND plan_date != ''")
            for row in cursor.fetchall():
                manual_plans[row[0]] = row[1]
                
            conn.close()
            
            # 3. Apply enrichment to cleaned coaches
            for item in cleaned:
                cno = str(item.get("coachno", "")).strip()
                
                # Apply plan date
                if cno in manual_plans:
                    item["plan_date"] = manual_plans[cno]
                    
                # Apply local custom update fields
                if cno in manual_updates_map:
                    upd = manual_updates_map[cno]
                    if upd.get("corrosion_hours") is not None:
                        item["corrosion_hours"] = upd["corrosion_hours"]
                    if upd.get("corr_in_date"):
                        item["corr_place"] = upd["corr_in_date"]
                    if upd.get("corr_comp"):
                        item["corr_comp"] = upd["corr_comp"]
                    if upd.get("remarks"):
                        item["remarks"] = upd["remarks"]
                    if upd.get("pdc"):
                        item["pdc"] = upd["pdc"]
                        
        except Exception as e:
            logger.error("fetch_clean: Error loading manual plans or local updates: %s", e)

    _set_cached(cache_key, cleaned)
    logger.info("fetch_clean: %d records (from %d raw)", len(cleaned), len(raw))
    return cleaned


# =====================================================
# Status helpers
# =====================================================

_INACTIVE_STATUSES = {"COND", "BHOPAL", "RETURN"}


def get_coach_status(demandid):
    """
    Fetch and return the uppercase status string for a coach.

    Returns
    -------
    str
        Status string, e.g. 'POH', 'COND', etc. Empty string on failure.
    """
    detail = fetch_single(demandid)
    status = detail.get("status", "") or detail.get("pohstatus", "")
    return str(status).strip().upper()


def is_active(demandid):
    """
    Return True if the coach is *not* in an inactive state
    (COND / BHOPAL / RETURN).
    """
    status = get_coach_status(demandid)
    return status not in _INACTIVE_STATUSES
