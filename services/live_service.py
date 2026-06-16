# =====================================================
# services/live_service.py
# LW/PER Workshop Intelligence System
# Live position data processing
# =====================================================

"""
Produces the dataset for the live-position view.

Each coach is enriched with:
- Division (from singledata → dvnid → DIVISION_MAP, fallback to coachmaster)
- Year built / manufacturer (from coachmaster)
- Family (from FAMILY_MAP via decoders)
- IN_DAYS (from recd_date)

Long-stay coaches (IN_DAYS > 365) are flagged as suspicious.
"""

import time
import logging
from datetime import datetime
from collections import Counter

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
    DIVISION_MAP,
)

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import CACHE_TTL_MASTER

logger = logging.getLogger(__name__)

# ── Simple cache ──────────────────────────────────────
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
    """Invalidate live-position cache."""
    _live_cache.clear()


# ── Long-stay threshold ──────────────────────────────
LONG_STAY_DAYS = 365


# =====================================================
# Division resolution
# =====================================================

def _resolve_division(rec, detail):
    """
    Resolve division label for a coach.

    Priority:
    1. dvnid, outdvnid, or indvnid from single-coach detail (pohmaster/singledata)
    2. dvnid from master record
    3. dvnid from coachmaster/singledata (fallback)
    """
    # Try detail first (check dvnid, outdvnid, and indvnid)
    dvnid = (detail.get("dvnid") or detail.get("outdvnid") or detail.get("indvnid") or "").strip()
    if dvnid and dvnid in DIVISION_MAP:
        return decode_division(dvnid)

    # Try master record
    dvnid = (rec.get("dvnid") or "").strip()
    if dvnid and dvnid in DIVISION_MAP:
        return decode_division(dvnid)

    # Fallback: coachmaster
    coachno = rec.get("coachno", "")
    if coachno:
        cm = fetch_year_built(coachno)
        dvnid = (cm.get("dvnid") or "").strip()
        if dvnid:
            return decode_division(dvnid)

    return ""


# =====================================================
# Main entry point
# =====================================================

def get_live_data():
    """
    Build the full live-position dataset.

    Returns
    -------
    dict
        {
            "coaches":    [enriched coach dicts ...],
            "metrics":    {total, filtered, coach_types, divisions, long_stay},
            "suspicious": [coaches with IN_DAYS > 365 ...],
        }
    """
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

    for rec in records:
        # ── Skip inactive coaches and AC Locos (handled separately) ─────────────────
        status = str(rec.get("status", "") or rec.get("pohstatus", "")).strip().upper()
        if status in _LIVE_INACTIVE_STATUSES or status == "AC LOCO":
            continue

        coachno = rec.get("coachno", "")
        coach_desc = rec.get("coach_desc", "") or rec.get("coachdesc", "")
        demandid = rec.get("demandid", "")

        # ── Fetch single detail for division ──────
        detail = {}
        if demandid:
            try:
                detail = fetch_single(demandid)
            except Exception as exc:
                logger.warning("fetch_single(%s) error: %s", demandid, exc)

        # ── Skip physically despatched coaches ────
        actual_desp = str(detail.get("actualdespdate") or "").strip()
        if actual_desp and actual_desp.lower() not in ("none", "null", "nan"):
            continue

        # ── Resolve division ──────────────────────
        division = _resolve_division(rec, detail)

        # ── Fetch year-built info ─────────────────
        yb_info = {}
        if coachno:
            try:
                yb_info = fetch_year_built(coachno)
            except Exception as exc:
                logger.warning("fetch_year_built(%s) error: %s", coachno, exc)

        # ── Calculate IN_DAYS ─────────────────────
        in_days = rec.get("IN_DAYS")
        if in_days is None:
            recd_str = rec.get("recd_date", "") or rec.get("recddate", "")
            recd_dt = _parse_date(recd_str)
            in_days = (now - recd_dt).days if recd_dt else None

        # ── Family & repair ───────────────────────
        family = decode_family(coach_desc)
        repair_type = decode_repair(detail.get("repairid") or detail.get("repair_type") or rec.get("repairid") or rec.get("repair_type"))

        pitnum = rec.get("pitnum", "")

        # ── Build enriched record ─────────────────
        coach = {
            "coachno": coachno,
            "coach_desc": coach_desc,
            "demandid": demandid,
            "pitnum": pitnum,
            "recd_date": rec.get("recd_date", "") or rec.get("recddate", ""),
            "IN_DAYS": in_days,
            "division": division,
            "family": family,
            "repair_type": repair_type,
            "year_built": yb_info.get("year_built", ""),
            "make": yb_info.get("make", ""),
            "status": status,
        }

        # ── Apply full decode_all ─────────────────
        decode_all(coach, summary_coachno=coachno, summary_desc=coach_desc)

        enriched.append(coach)

        # ── Bookkeeping ──────────────────────────
        family_counter[family] += 1
        if division:
            division_counter[division] += 1

        # ── Flag suspicious long-stay ────────────
        if in_days is not None and in_days > LONG_STAY_DAYS:
            suspicious.append(coach)

    # ── Process active AC Locos ─────────────────
    try:
        from services.aerial_service import _fetch_ac_locos
        ac_locos = _fetch_ac_locos()
        for l in ac_locos:
            coachno = l.get("loco_no")
            coach_desc = l.get("loco_desc") or "WAP7"
            pitnum = l.get("pitnum") or ""
            recd_date = l.get("date_recd") or l.get("recd_on") or ""
            
            # Calculate IN_DAYS
            recd_dt = _parse_date(recd_date)
            in_days = (now - recd_dt).days if recd_dt else None
            
            coach = {
                "coachno": coachno,
                "coach_desc": coach_desc,
                "demandid": f"LOCO_{coachno}",
                "pitnum": pitnum,
                "recd_date": recd_date,
                "IN_DAYS": in_days,
                "division": l.get("shed") or "",
                "family": "LOCO",
                "repair_type": l.get("repair_type") or "POH",
                "year_built": l.get("pdc") or "",
                "make": "AC LOCO",
                "status": "AC LOCO",
            }
            
            # Apply decode_all
            decode_all(coach, summary_coachno=coachno, summary_desc=coach_desc)
            enriched.append(coach)
            
            family_counter["LOCO"] += 1
            if coach["division"]:
                division_counter[coach["division"]] += 1
                
            if in_days is not None and in_days > LONG_STAY_DAYS:
                suspicious.append(coach)
    except Exception as exc:
        logger.error("Error enriching AC Locos in get_live_data: %s", exc)

    # ── Build metrics ─────────────────────────────────
    metrics = {
        "total": len(enriched),
        "filtered": len(enriched),
        "coach_types": dict(family_counter.most_common()),
        "divisions": dict(division_counter.most_common()),
        "long_stay": len(suspicious),
    }

    result = {
        "coaches": enriched,
        "metrics": metrics,
        "suspicious": suspicious,
    }

    _set_cached(cache_key, result)
    logger.info(
        "get_live_data: %d coaches (%d suspicious)",
        len(enriched), len(suspicious),
    )
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
