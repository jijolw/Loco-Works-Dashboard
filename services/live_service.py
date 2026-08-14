# =====================================================
# services/live_service.py
# LW/PER Workshop Intelligence System
# Live position data processing
# =====================================================

import time
import logging
from datetime import datetime
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.erp_service import (
    fetch_clean,
    fetch_single,
    fetch_year_built,
    _LIVE_INACTIVE_STATUSES,
    _parse_date,
)
from services.decoders import (
    decode_division,
    decode_family,
    decode_repair,
    decode_all,
    decode_corrosion,
    DIVISION_MAP,
)

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import CACHE_TTL_MASTER

logger = logging.getLogger(__name__)

_live_cache: dict = {}


def _get_cached(key, ttl):
    entry = _live_cache.get(key)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts > ttl:
        return None
    return data


def _set_cached(key, data):
    _live_cache[key] = (time.time(), data)


def live_cache_clear():
    _live_cache.clear()


LONG_STAY_DAYS = 365


def _resolve_division(rec, detail):
    dvnid = (detail.get("dvnid") or detail.get("outdvnid") or detail.get("indvnid") or "").strip()
    if dvnid and dvnid in DIVISION_MAP:
        return decode_division(dvnid)

    dvnid = (rec.get("dvnid") or "").strip()
    if dvnid and dvnid in DIVISION_MAP:
        return decode_division(dvnid)

    coachno = rec.get("coachno", "")
    if coachno:
        cm = fetch_year_built(coachno)
        dvnid = (cm.get("dvnid") or "").strip()
        if dvnid:
            return decode_division(dvnid)

    return ""


def _process_live_coach(rec, now):
    status = str(rec.get("status", "") or rec.get("pohstatus", "")).strip().upper()
    
    # RULE 3: Exclude Return coaches completely!
    if status in _LIVE_INACTIVE_STATUSES or status in ("DESPATCHED", "OUTTURN", "COMPLETED", "INACTIVE") or status == "AC LOCO" or "RETURN" in status or status == "161":
        return None

    coachno = rec.get("coachno", "")
    coach_desc = rec.get("coach_desc", "") or rec.get("coachdesc", "")
    demandid = rec.get("demandid", "")

    detail = {}
    if demandid:
        try:
            detail = fetch_single(demandid)
        except Exception:
            pass

    status_erp = str(detail.get("status") or "").strip().upper()
    if "RETURN" in status_erp or status_erp == "161":
        return None

    actual_desp = str(detail.get("actualdespdate") or "").strip()
    recd_str = rec.get("recd_date", "") or rec.get("recddate", "")
    recd_dt = _parse_date(recd_str)
    
    is_desp = False
    if actual_desp and actual_desp.lower() not in ("none", "null", "nan", ""):
        act_desp_dt = _parse_date(actual_desp)
        if act_desp_dt and recd_dt:
            if act_desp_dt >= recd_dt:
                is_desp = True
        else:
            is_desp = True
            
    if is_desp:
        return None

    division = _resolve_division(rec, detail)

    yb_info = {}
    if coachno:
        try:
            yb_info = fetch_year_built(coachno)
        except Exception:
            pass

    in_days = rec.get("IN_DAYS")
    if in_days is None:
        in_days = (now - recd_dt).days if recd_dt else None

    family = decode_family(coach_desc)
    repair_type = decode_repair(detail.get("repairid") or detail.get("repair_type") or rec.get("repairid") or rec.get("repair_type"))

    pitnum = rec.get("pitnum", "")
    corr_place = detail.get("corr_place", "")
    corr_comp = detail.get("corr_comp", "")

    is_fnd = False
    desp_date = detail.get("desp_date") or detail.get("despdate") or ""
    desp_dt = _parse_date(desp_date)
    has_desp_date = False
    if desp_dt:
        if recd_dt:
            if desp_dt >= recd_dt:
                has_desp_date = True
        else:
            has_desp_date = True

    if status in ("DESPATCHED", "OUTTURN") or has_desp_date:
        is_fnd = True

    coach = {
        "coachno": coachno,
        "coach_desc": coach_desc,
        "demandid": demandid,
        "pitnum": pitnum,
        "recd_date": recd_str,
        "IN_DAYS": in_days,
        "family": family,
        "repair_type": repair_type,
        "division": division,
        "corr_place": corr_place,
        "corr_comp": corr_comp,
        "corrosion_label": decode_corrosion(detail.get("corrosion")),
        "desp_date": desp_date,
        "status": status,
        "last_poh": detail.get("last_poh", ""),
        "tfr_date": detail.get("tfrdate") or detail.get("tfr_date") or "",
        "make": yb_info.get("make", ""),
        "year_built": yb_info.get("year_built", ""),
        "presurveyhrs": detail.get("presurveyhrs", ""),
        "finalhrs": detail.get("finalhrs", ""),
        "is_fnd": is_fnd,
    }

    decode_all(coach, summary_coachno=coachno, summary_desc=coach_desc)
    return coach


def get_live_data():
    cache_key = "live_full"
    cached = _get_cached(cache_key, CACHE_TTL_MASTER)
    if cached is not None:
        return cached

    now = datetime.now()
    records = fetch_clean()

    enriched = []
    suspicious = []
    family_counter = Counter()
    division_counter = Counter()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(_process_live_coach, rec, now) for rec in records]
        for f in as_completed(futures):
            res = f.result()
            if res:
                enriched.append(res)
                family_counter[res["family"]] += 1
                division_counter[res["division"]] += 1
                if res["IN_DAYS"] is not None and res["IN_DAYS"] > LONG_STAY_DAYS:
                    suspicious.append(res)

    result = {
        "coaches": enriched,
        "metrics": {
            "total": len(enriched),
            "filtered": len(enriched),
            "coach_types": dict(family_counter),
            "divisions": dict(division_counter),
            "long_stay": len(suspicious),
        },
        "suspicious": suspicious,
    }

    _set_cached(cache_key, result)
    return result


def get_coaches_progress():
    """
    Get progress stepper data for coaches under repair from Google Sheets
    matched against live positions from ERP.
    """
    # 1. Fetch live coaches from ERP
    live_data = get_live_data()
    live_map = {c["coachno"]: c for c in live_data["coaches"]}
    
    # 2. Query not-despatched coaches from google_corrosion Supabase table
    from services.db_service import get_not_despatched_corrosion
    rows = get_not_despatched_corrosion()
    
    coaches_progress = []
    
    for r in rows:
        coachno = r["coachno"]
        source_tab = r["source_tab"]
        
        # Match with live ERP coach
        live_coach = live_map.get(coachno, {})
        
        # Get recd_date and pitnum
        recd_date = r["corr_in_date"] or live_coach.get("recd_date", "")
        pitnum = live_coach.get("pitnum", "")
        
        # Build milestones/stepper progress
        stages = []
        
        corr_stat = str(r["corrosion_status"] or "").strip().upper()
        bio_stat = str(r["bio_tank_status"] or "").strip().upper()
        low_stat = str(r["lowering_status"] or "").strip().upper()
        furn_stat = str(r["furnishing_status"] or "").strip().upper()
        desp_stat = str(r["despatch_status"] or "").strip().upper()
        
        # Arrived stage is always completed
        stages.append({
            "name": "Arrived",
            "status": "COMPLETED",
            "date": live_coach.get("recd_date", "")
        })
        
        # Helper to determine if a stage has been started or completed
        def is_active_or_completed(stat):
            if not stat:
                return False
            su = stat.strip().upper()
            if su in ("—", "NIL", "NA", "", "YET TO BE TAKEN", "YET TO START", "YET"):
                return False
            return True

        # Helper to determine step status
        def get_step_status(current_stat, next_active):
            if not current_stat:
                return "PENDING"
            curr_upper = current_stat.strip().upper()
            if curr_upper in ("—", "NIL", "NA", "", "YET TO BE TAKEN", "YET TO START", "YET"):
                return "PENDING"
            if "DONE" in curr_upper or "COMP" in curr_upper or "OK" in curr_upper or "DESP" in curr_upper or "FND" in curr_upper or next_active:
                return "COMPLETED"
            if "PROG" in curr_upper or "WIP" in curr_upper or "PROGRESS" in curr_upper:
                return "IN_PROGRESS"
            return "PENDING"
            
        # Determine active next stages
        is_desp_active = is_active_or_completed(desp_stat)
        is_furn_active = is_active_or_completed(furn_stat) or is_desp_active
        is_low_active = is_active_or_completed(low_stat) or is_furn_active
        is_bio_active = is_active_or_completed(bio_stat) or is_low_active
        
        corr_step = get_step_status(corr_stat, is_bio_active)
        # If corr_in_date is filled, but status is empty, it means it is at least in progress
        if corr_step == "PENDING" and r["corr_in_date"]:
            corr_step = "IN_PROGRESS" if not is_bio_active else "COMPLETED"
            
        bio_step = get_step_status(bio_stat, is_low_active)
        low_step = get_step_status(low_stat, is_furn_active)
        furn_step = get_step_status(furn_stat, is_desp_active)
        desp_step = get_step_status(desp_stat, False)
        
        # Propagate completion backwards
        if desp_step in ("IN_PROGRESS", "COMPLETED"):
            furn_step = "COMPLETED"
            low_step = "COMPLETED"
            bio_step = "COMPLETED"
            corr_step = "COMPLETED"
        elif furn_step in ("IN_PROGRESS", "COMPLETED"):
            low_step = "COMPLETED"
            bio_step = "COMPLETED"
            corr_step = "COMPLETED"
        elif low_step in ("IN_PROGRESS", "COMPLETED"):
            bio_step = "COMPLETED"
            corr_step = "COMPLETED"
        elif bio_step in ("IN_PROGRESS", "COMPLETED"):
            corr_step = "COMPLETED"
            
        stages.append({
            "name": "Corrosion",
            "status": corr_step,
            "detail": r["corrosion_status"] or "",
            "date": r["corr_in_date"] or ""
        })
        stages.append({
            "name": "Bio Tank Loading",
            "status": bio_step,
            "detail": r["bio_tank_status"] or ""
        })
        stages.append({
            "name": "Lowering",
            "status": low_step,
            "detail": r["lowering_status"] or ""
        })
        stages.append({
            "name": "Furnishing",
            "status": furn_step,
            "detail": r["furnishing_status"] or ""
        })
        stages.append({
            "name": "Despatch",
            "status": desp_step,
            "detail": r["despatch_status"] or ""
        })
        
        # Determine current active stage index
        current_step_idx = 0
        for idx, s in enumerate(stages):
            if s["status"] in ("IN_PROGRESS", "COMPLETED"):
                current_step_idx = idx
                
        coaches_progress.append({
            "coachno": coachno,
            "coach_desc": live_coach.get("coach_desc", ""),
            "family": live_coach.get("family", decode_family(coachno)),
            "repair_type": live_coach.get("repair_type", ""),
            "pitnum": pitnum,
            "in_days": live_coach.get("IN_DAYS", None),
            "source_tab": source_tab,
            "pdc": r["pdc"] or "",
            "remarks": r["remarks"] or "",
            "stages": stages,
            "current_step_idx": current_step_idx
        })
        
    return coaches_progress
