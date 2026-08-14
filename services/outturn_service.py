# =====================================================
# services/outturn_service.py
# LW/PER Workshop Intelligence System (Supabase version)
# =====================================================

import logging
from datetime import datetime, timedelta
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def _process_candidate_outturn(rec, start_date, end_date):
    demandid = rec.get("demandid")
    if not demandid:
        return None

    try:
        detail = fetch_single(demandid)
    except Exception:
        return None

    status_val = str(detail.get("status") or rec.get("status") or "").strip().upper()

    # RULE 3: Return type coaches should NOT be considered anywhere!
    if any(x in status_val for x in ["RETURN", "COND", "BHOPAL", "161"]):
        return None

    # RULE 1: Paper Outturn Date = First Despatch Date (desp_date)
    desp_str = detail.get("desp_date") or detail.get("despdate") or rec.get("desp_date") or rec.get("despdate")
    desp_dt = _parse_date(desp_str)

    # RULE 2: Physical Despatch Date = Actual Despatch Date (actualdespdate)
    act_desp_str = detail.get("actualdespdate") or rec.get("actualdespdate")
    act_desp_dt = _parse_date(act_desp_str)

    # Check if coach was outturned in date range based on Paper Outturn Date or Physical Despatch Date
    is_outturned = False
    target_dt = desp_dt or act_desp_dt

    if target_dt and start_date <= target_dt <= end_date:
        is_outturned = True

    if not is_outturned:
        return None

    coachno = rec.get("coachno", "")
    coach_desc = rec.get("coach_desc", "") or rec.get("coachdesc", "")
    family = decode_family(coach_desc)
    division = decode_division(detail.get("dvnid") or rec.get("dvnid"))
    repair_type = decode_repair(detail.get("repairid") or detail.get("repair_type") or rec.get("repairid"))

    recd_str = rec.get("recd_date", "") or rec.get("recddate", "")
    recd_dt = _parse_date(recd_str)
    turnaround_days = (target_dt - recd_dt).days if (target_dt and recd_dt and target_dt >= recd_dt) else None

    # Resolve/decode all properties for UI compatibility
    coach = {
        "coachno": coachno,
        "coach_desc": coach_desc,
        "demandid": demandid,
        "family": family,
        "division": division,
        "repair_type": repair_type,
        "recd_date": recd_str,
        "desp_date": desp_dt.strftime("%d/%m/%Y") if desp_dt else "",
        "actualdespdate": act_desp_dt.strftime("%d/%m/%Y") if act_desp_dt else "",
        "turnaround_days": turnaround_days,
        "status": status_val,
    }
    decode_all(coach, summary_coachno=coachno, summary_desc=coach_desc)
    return coach


def get_outturn_data(start_date_str=None, end_date_str=None):
    now = datetime.now()

    if not start_date_str:
        start_date = datetime(now.year, now.month, 1)
    else:
        start_date = _parse_date(start_date_str) or datetime(now.year, now.month, 1)

    if not end_date_str:
        end_date = now
    else:
        end_date = _parse_date(end_date_str) or now

    master = fetch_master()
    candidates = []

    for rec in master:
        demandid = rec.get("demandid")
        if not demandid: continue

        recd_str = rec.get("recd_date") or rec.get("recddate")
        recd_dt = _parse_date(recd_str)

        desp_str = rec.get("desp_date") or rec.get("despdate")
        desp_dt = _parse_date(desp_str)

        act_desp_str = rec.get("actualdespdate")
        act_desp_dt = _parse_date(act_desp_str)

        is_candidate = True
        master_dt = desp_dt or act_desp_dt
        if master_dt and not (start_date - timedelta(days=60) <= master_dt <= end_date + timedelta(days=60)):
            is_candidate = False

        if is_candidate:
            candidates.append(rec)

    outturned_coaches = []
    family_counter = Counter()
    division_counter = Counter()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(_process_candidate_outturn, rec, start_date, end_date) for rec in candidates]
        for f in as_completed(futures):
            res = f.result()
            if res:
                outturned_coaches.append(res)
                family_counter[res["family"]] += 1
                division_counter[res["division"]] += 1

    return {
        "coaches": outturned_coaches,
        "metrics": {
            "total": len(outturned_coaches),
            "coach_types": dict(family_counter),
            "divisions": dict(division_counter),
        },
    }
