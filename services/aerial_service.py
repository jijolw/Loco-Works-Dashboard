# =====================================================
# services/aerial_service.py
# LW/PER Workshop Intelligence System
# Aerial view data processing
# =====================================================

import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

from services.erp_service import (
    get_session,
    fetch_master,
    fetch_clean,
    fetch_single,
    fetch_year_built,
    _parse_date,
    _INACTIVE_STATUSES,
)
from services.decoders import (
    decode_repair,
    decode_family,
    decode_division,
    decode_corrosion,
    decode_all,
    REPAIR_MAP,
)
from services.topology import LAYOUT

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import (
    COACH_ERP_BASE_URL,
    CACHE_TTL_AERIAL,
)

logger = logging.getLogger(__name__)

_aerial_cache: dict = {}


def _get_cached(key, ttl):
    entry = _aerial_cache.get(key)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts > ttl:
        return None
    return data


def _set_cached(key, data):
    _aerial_cache[key] = (time.time(), data)


def aerial_cache_clear():
    _aerial_cache.clear()


def _compute_aerial_status(coach):
    corr_place = str(coach.get("corr_place", "") or "").strip()
    corr_comp = str(coach.get("corr_comp", "") or "").strip()
    desp_date = str(coach.get("desp_date", "") or coach.get("despdate", "") or "").strip()

    if desp_date:
        return "OUTTURNED"
    if corr_place and not corr_comp:
        return "UNDER CORROSION"
    if corr_comp:
        return "CORROSION DONE"
    return "ROUTINE POH"


def _fetch_ac_locos():
    from services.erp_service import fetch_master
    master = fetch_master()
    locos = []
    for r in master:
        if str(r.get("status")).strip().upper() == "AC LOCO":
            tfr_date = str(r.get("tfr") or "").strip()
            locos.append({
                "loco_no": r.get("coachno"),
                "loco_desc": r.get("coach_desc") or "WAP7",
                "pitnum": r.get("pitnum"),
                "date_recd": r.get("recd_date"),
                "shed": r.get("division"),
                "repair_type": r.get("repair_type") or "POH",
                "pdc": r.get("year_built") or "",
                "recd_on": r.get("recd_on") or "",
                "stripping": r.get("stripping") or "",
                "dewheel": r.get("dewheel") or "",
                "wheeling": r.get("wheeling") or "",
                "test_trial": r.get("test_trial") or "",
                "traffic": r.get("traffic") or "",
                "super_str": r.get("super_str") or "",
                "tm": r.get("tm") or "",
                "ico_tm": r.get("ico_tm") or "",
                "tfr": tfr_date
            })
    return locos


def _process_aerial_coach(rec, now):
    status = str(rec.get("status", "") or rec.get("pohstatus", "")).strip().upper()
    
    # RULE 3: Exclude Return coaches completely!
    if status in _INACTIVE_STATUSES or status in ("DESPATCHED", "OUTTURN", "COMPLETED", "INACTIVE") or "RETURN" in status or status == "161":
        return None

    coachno = rec.get("coachno", "")
    coach_desc = rec.get("coach_desc", "") or rec.get("coachdesc", "")
    demandid = rec.get("demandid", "")
    pitnum = rec.get("pitnum", "")

    recd_str = rec.get("recd_date", "") or rec.get("recddate", "")
    recd_dt = _parse_date(recd_str)
    in_days = (now - recd_dt).days if recd_dt else None

    detail = {}
    if demandid:
        try:
            detail = fetch_single(demandid)
        except Exception:
            pass

    status_erp = str(detail.get("status") or "").strip().upper()
    if "RETURN" in status_erp or status_erp in ("COND", "BHOPAL", "161"):
        return None

    actual_desp = str(detail.get("actualdespdate") or "").strip()
    if actual_desp and actual_desp.lower() not in ("none", "null", "nan", ""):
        return None

    yb_info = {}
    if coachno:
        try:
            yb_info = fetch_year_built(coachno)
        except Exception:
            pass

    corr_place = detail.get("corr_place", "")
    corr_comp = detail.get("corr_comp", "")

    coach = {
        "coachno": coachno,
        "coach_desc": coach_desc,
        "demandid": demandid,
        "pitnum": pitnum,
        "recd_date": recd_str,
        "IN_DAYS": in_days,
        "family": decode_family(coach_desc),
        "repair_type": decode_repair(
            detail.get("repairid") or detail.get("repair_type") or rec.get("repairid") or rec.get("repair_type")
        ),
        "division": decode_division(
            detail.get("dvnid") or rec.get("dvnid")
        ),
        "corr_place": corr_place,
        "corr_comp": corr_comp,
        "corrosion_label": decode_corrosion(detail.get("corrosion")),
        "desp_date": detail.get("desp_date", "") or detail.get("despdate", ""),
        "status": status,
        "last_poh": detail.get("last_poh", ""),
        "tfr_date": detail.get("tfrdate", "") or detail.get("tfr_date", ""),
        "make": yb_info.get("make", ""),
        "year_built": yb_info.get("year_built", ""),
        "presurveyhrs": detail.get("presurveyhrs", ""),
        "finalhrs": detail.get("finalhrs", ""),
        "plan_date": detail.get("plandate") or detail.get("plan_date") or "",
    }

    for k, v in detail.items():
        if k not in coach:
            coach[k] = v

    coach["dvnid"] = detail.get("dvnid") or rec.get("dvnid") or ""
    coach["AERIAL_STATUS"] = _compute_aerial_status(coach)
    decode_all(coach, summary_coachno=coachno, summary_desc=coach_desc)

    return coach


def get_aerial_data():
    cache_key = "aerial_full"
    cached = _get_cached(cache_key, CACHE_TTL_AERIAL)
    if cached is not None:
        return cached

    now = datetime.now()
    raw_records = fetch_clean()

    coaches_records = []
    for r in raw_records:
        make_val = str(r.get("make") or "").strip()
        status_val = str(r.get("status") or "").strip().upper()
        if make_val == "AC LOCO" or status_val == "AC LOCO":
            continue
        coaches_records.append(r)

    ac_locos_list = _fetch_ac_locos()

    enriched = []
    metrics = {
        "total": 0,
        "under_corrosion": 0,
        "corrosion_done": 0,
        "outturned": 0,
        "normal": 0,
        "danger": 0,
    }

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(_process_aerial_coach, rec, now) for rec in coaches_records]
        for f in as_completed(futures):
            res = f.result()
            if res:
                enriched.append(res)
                metrics["total"] += 1
                st = res["AERIAL_STATUS"]
                if st == "UNDER CORROSION":
                    metrics["under_corrosion"] += 1
                elif st == "CORROSION DONE":
                    metrics["corrosion_done"] += 1
                elif st == "OUTTURNED":
                    metrics["outturned"] += 1
                elif st == "DANGER":
                    metrics["danger"] += 1
                else:
                    metrics["normal"] += 1

    ac_locos = ac_locos_list
    metrics["total"] += len(ac_locos)
    metrics["normal"] += len(ac_locos)

    from services.topology import TWO_SLOT_LINES, PITNUM_ALIASES

    normalized_layout = []
    for entry in LAYOUT:
        node = dict(entry)
        if node.get("type") == "shop" and "pits" in node:
            node["order"] = node.pop("pits")
        normalized_layout.append(node)

    result = {
        "coaches": enriched,
        "ac_locos": ac_locos,
        "metrics": metrics,
        "topology": normalized_layout,
        "two_slot_lines": list(TWO_SLOT_LINES),
        "pitnum_aliases": PITNUM_ALIASES,
    }

    _set_cached(cache_key, result)
    return result
