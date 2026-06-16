# =====================================================
# services/outturn_service.py
# LW/PER Workshop Intelligence System (Pure Supabase version)
# =====================================================

import logging
from datetime import datetime, timedelta
from collections import Counter

from services.erp_service import (
    fetch_master,
    fetch_single,
    _parse_date,
)
from services.decoders import (
    decode_repair,
    decode_family,
    decode_division,
    decode_all,
)

logger = logging.getLogger(__name__)

def get_outturn_data(start_date_str=None, end_date_str=None):
    """
    Get coaches outturned (despatched) between start_date and end_date.
    
    Parameters
    ----------
    start_date_str : str, optional (YYYY-MM-DD or DD/MM/YYYY)
    end_date_str : str, optional (YYYY-MM-DD or DD/MM/YYYY)
    
    Returns
    -------
    dict
        {
            "coaches": [enriched outturned coach dicts ...],
            "metrics": {total, coach_types, divisions},
        }
    """
    now = datetime.now()
    
    # Default start_date to 1st of current month, end_date to today
    if not start_date_str:
        start_date = datetime(now.year, now.month, 1)
    else:
        start_date = _parse_date(start_date_str) or datetime(now.year, now.month, 1)
        
    if not end_date_str:
        end_date = now
    else:
        end_date = _parse_date(end_date_str) or now
        
    logger.info("get_outturn_data (Supabase): filtering from %s to %s", start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    
    # Candidate coaches: entry date should be before end_date,
    # and no earlier than 365 days before start_date (buffer for long-stay)
    cutoff_start = start_date - timedelta(days=365)
    
    master = fetch_master()
    candidates = []
    
    for rec in master:
        demandid = rec.get("demandid")
        if not demandid:
            continue
            
        recd_str = rec.get("recd_date") or rec.get("recddate")
        recd_dt = _parse_date(recd_str)
        if not recd_dt:
            continue
            
        if cutoff_start <= recd_dt <= end_date:
            candidates.append(rec)
            
    logger.info("get_outturn_data (Supabase): found %d candidate records based on entry date", len(candidates))
    
    outturned_coaches = []
    family_counter = Counter()
    division_counter = Counter()
    
    # Fetch details for candidates to check actual despatch date
    for rec in candidates:
        demandid = rec["demandid"]
        try:
            detail = fetch_single(demandid)
        except Exception as exc:
            logger.warning("fetch_single(%s) failed: %s", demandid, exc)
            continue
            
        # Filter out Condemned, Return, and Bhopal statuses
        status_upper = str(detail.get("status") or detail.get("pohstatus") or "").strip().upper()
        if any(x in status_upper for x in ["COND", "RETURN", "BHOPAL"]):
            continue

        # Check despatch date, correcting for obvious database typos where desp_date < recd_date
        recd_str = rec.get("recd_date") or rec.get("recddate")
        recd_dt = _parse_date(recd_str)
        
        desp_str = detail.get("desp_date") or detail.get("despdate")
        desp_dt = _parse_date(desp_str)
        
        act_desp_str = detail.get("actualdespdate")
        act_desp_dt = _parse_date(act_desp_str)
        
        # If desp_dt is invalid (e.g., before recd_dt) but we have a valid actualdespdate, use actualdespdate
        if recd_dt and desp_dt and desp_dt < recd_dt and act_desp_dt and act_desp_dt >= recd_dt:
            desp_dt = act_desp_dt
            desp_str = act_desp_str
        elif not desp_dt:
            desp_dt = act_desp_dt or _parse_date(desp_str)
            if act_desp_dt:
                desp_str = act_desp_str
                
        # Fallback to google corrosion sheet desp_date if not present in ERP/manual update
        coachno = rec.get("coachno", "")
        if not desp_dt:
            if not desp_str or str(desp_str).strip() in ("", "None", "null", "—"):
                try:
                    from services.db_service import get_google_corrosion
                    g_corr = get_google_corrosion(coachno)
                    if g_corr:
                        desp_str = g_corr.get("desp_date") or ""
                        desp_dt = _parse_date(desp_str)
                except Exception:
                    pass
                    
        if not desp_dt:
            continue
            
        # Check if within selected date range
        if start_date <= desp_dt <= end_date:
            coach_desc = rec.get("coach_desc") or rec.get("coachdesc") or ""
            
            family = decode_family(coach_desc)
            repair_type = decode_repair(detail.get("repairid") or detail.get("repair_type") or rec.get("repairid") or rec.get("repair_type"))
            division = decode_division(detail.get("dvnid") or rec.get("dvnid"))
            
            coach = {
                "coachno": coachno,
                "coach_desc": coach_desc,
                "demandid": demandid,
                "recd_date": rec.get("recd_date") or rec.get("recddate") or "",
                "desp_date": desp_str,
                "family": family,
                "repair_type": repair_type,
                "division": division,
                "year_built": detail.get("year_built", "") or rec.get("year_built", ""),
                "make": detail.get("make", "") or rec.get("make", ""),
                "status": "OUTTURN",
            }
            
            decode_all(coach, summary_coachno=coachno, summary_desc=coach_desc)
            outturned_coaches.append(coach)
            
            family_counter[family] += 1
            if division:
                division_counter[division] += 1
                
    # Sort outturned coaches by despatch date descending
    outturned_coaches.sort(key=lambda c: _parse_date(c["desp_date"]) or datetime.min, reverse=True)
    
    result = {
        "coaches": outturned_coaches,
        "metrics": {
            "total": len(outturned_coaches),
            "coach_types": dict(family_counter.most_common()),
            "divisions": dict(division_counter.most_common()),
        }
    }
    
    logger.info("get_outturn_data (Supabase): found %d outturned coaches", len(outturned_coaches))
    return result
