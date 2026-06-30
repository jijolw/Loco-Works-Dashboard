# =====================================================
# services/aerial_service.py
# LW/PER Workshop Intelligence System
# Aerial view data processing
# =====================================================

"""
Builds the data payload consumed by the aerial-view frontend.

Each coach is enriched with:
- AERIAL_STATUS  (UNDER CORROSION / CORROSION DONE / OUTTURNED / NORMAL)
- Family, repair type, division labels (via decoders)
- IN_DAYS calculated from recd_date

Also fetches AC loco positions and includes the workshop topology
so the frontend can render the full map.
"""

import time
import logging
from datetime import datetime

import requests

from services.erp_service import (
    get_session,
    fetch_master,
    fetch_clean,
    fetch_single,
    _parse_date,
    _LIVE_INACTIVE_STATUSES,
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

# ── Simple cache ──────────────────────────────────────
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
    """Invalidate aerial cache."""
    _aerial_cache.clear()


# =====================================================
# Aerial status logic
# =====================================================

def _compute_aerial_status(coach):
    """
    Determine the aerial status category for a coach.

    Priority order:
    1. Check if physically despatched, returned, or condemned
    2. UNDER CORROSION — corr_place filled AND corr_comp blank
    3. CORROSION DONE  — corr_comp filled
    4. OUTTURNED       — desp_date filled
    5. ROUTINE POH     — everything else
    """
    status = str(coach.get("status") or "").strip().upper()
    physical_status = str(coach.get("physical_status") or "").strip().upper()
    actual_desp = str(coach.get("actualdespdate") or "").strip()
    desp_date = str(coach.get("desp_date") or coach.get("despdate") or "").strip()

    recd_str = coach.get("recd_date") or coach.get("recddate") or ""
    recd_dt = _parse_date(recd_str)
    act_desp_dt = _parse_date(actual_desp) if actual_desp and actual_desp.lower() not in ("none", "null", "nan", "") else None
    
    has_actual_desp = False
    if act_desp_dt:
        if recd_dt:
            if act_desp_dt >= recd_dt:
                has_actual_desp = True
        else:
            has_actual_desp = True

    desp_dt = _parse_date(desp_date) if desp_date and desp_date.lower() not in ("none", "null", "nan", "") else None
    has_desp_date = False
    if desp_dt:
        if recd_dt:
            if desp_dt >= recd_dt:
                has_desp_date = True
        else:
            has_desp_date = True

    is_inactive = (
        (status in ("RETURN", "COND", "CONDEMNED", "BHOPAL")) or
        (physical_status == "DESPATCHED") or
        has_actual_desp or
        (status in ("DESPATCHED", "OUTTURN") and has_desp_date)
    )

    if is_inactive:
        if "COND" in status:
            return "CONDEMNED"
        if "RETURN" in status:
            return "RETURNED"
        if "BHOPAL" in status:
            return "BHOPAL"
        # Check if manual updates are pending for physically despatched coaches, outturned coaches, or manual overrides
        if has_actual_desp or (physical_status == "DESPATCHED") or (status in ("DESPATCHED", "OUTTURN") and has_desp_date):
            vg_status = str(coach.get("vg_status") or "").strip()
            phys_status_man = str(coach.get("physical_status") or "").strip()
            if vg_status != "Completed" or phys_status_man != "Despatched":
                return "DANGER"
        return "DESPATCHED"

    if has_desp_date:
        return "OUTTURNED"

    corr_place = str(coach.get("corr_place", "") or "").strip()
    corr_comp = str(coach.get("corr_comp", "") or "").strip()

    if corr_place and not corr_comp:
        return "UNDER CORROSION"
    if corr_comp:
        return "CORROSION DONE"
    return "ROUTINE POH"


# =====================================================
# AC Loco data
# =====================================================

def _fetch_ac_locos():
    """
    Fetch active AC Locos from the cached master list in Supabase mode.
    """
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
                
                # AC Loco progress milestones
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


# =====================================================
# Main entry point
# =====================================================

def get_aerial_data():
    """
    Build the full aerial-view dataset.

    Returns
    -------
    dict
        {
            "coaches":  [enriched coach dicts ...],
            "ac_locos": [loco dicts ...],
            "metrics":  {total, under_corrosion, corrosion_done,
                         outturned, normal},
            "topology": LAYOUT (from topology.py),
        }
    """
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

    for rec in coaches_records:
        # ── Skip inactive coaches ─────────────────
        status = str(rec.get("status", "") or rec.get("pohstatus", "")).strip().upper()
        if status in _LIVE_INACTIVE_STATUSES:
            continue

        coachno = rec.get("coachno", "")
        coach_desc = rec.get("coach_desc", "") or rec.get("coachdesc", "")
        demandid = rec.get("demandid", "")
        
        pitnum = rec.get("pitnum", "")

        # ── Parse received date & calculate IN_DAYS
        recd_str = rec.get("recd_date", "") or rec.get("recddate", "")
        recd_dt = _parse_date(recd_str)
        in_days = (now - recd_dt).days if recd_dt else None

        # ── Fetch single-coach detail for corrosion / repair fields
        detail = {}
        if demandid:
            try:
                detail = fetch_single(demandid)
            except Exception as exc:
                logger.warning("fetch_single(%s) error: %s", demandid, exc)

        # ── Skip physically/actual despatched coaches completely ────
        actual_desp = str(detail.get("actualdespdate") or "").strip()
        has_actual_desp = actual_desp and actual_desp.lower() not in ("none", "null", "nan", "")
        
        desp_date = str(detail.get("desp_date") or detail.get("despdate") or "").strip()
        status_erp = str(rec.get("status") or "").strip().upper()

        has_desp_date = False
        if desp_date and desp_date.lower() not in ("none", "null", "nan", ""):
            desp_dt = _parse_date(desp_date)
            if desp_dt and recd_dt:
                if desp_dt >= recd_dt:
                    has_desp_date = True
            else:
                has_desp_date = True

        is_physically_desp = (str(detail.get("physical_status") or "").strip() == "Despatched")
        
        if has_actual_desp or is_physically_desp:
            continue

        # ── Fetch year-built info ─────────────────
        yb_info = {}
        if coachno:
            try:
                from services.erp_service import fetch_year_built
                yb_info = fetch_year_built(coachno)
            except Exception as exc:
                logger.warning("fetch_year_built(%s) error: %s", coachno, exc)

        # Enrich with Google Sheets corrosion and stages data if vacant in ERP
        from services.db_service import get_google_corrosion
        google_corr = get_google_corrosion(coachno)
        
        corr_place = detail.get("corr_place", "")
        corr_comp = detail.get("corr_comp", "")
        
        if google_corr:
            g_corr_in = google_corr.get("corr_in_date") or ""
            g_corr_status = google_corr.get("corrosion_status") or ""
            
            if (not corr_place or str(corr_place).strip() in ("", "None", "null", "0")) and g_corr_in:
                corr_place = "GSheet: " + g_corr_in
                
            if (not corr_comp or str(corr_comp).strip() in ("", "None", "null", "0")) and g_corr_status:
                if "completed" in g_corr_status.lower() or "/" in g_corr_status or "-" in g_corr_status:
                    corr_comp = g_corr_status if ("/" in g_corr_status or "-" in g_corr_status) else "Completed"

        # ── Build enriched coach record ───────────
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
            "corrosion_label": decode_corrosion(detail.get("corrosion")) or (google_corr.get("corrosion_status") if google_corr else ""),
            "desp_date": detail.get("desp_date", "") or detail.get("despdate", "") or (google_corr.get("desp_date") if google_corr else ""),
            "status": status,
            "last_poh": detail.get("last_poh", ""),
            "tfr_date": detail.get("tfrdate", "") or detail.get("tfr_date", ""),
            "make": yb_info.get("make", ""),
            "year_built": yb_info.get("year_built", ""),
            "presurveyhrs": detail.get("presurveyhrs", ""),
            "finalhrs": detail.get("finalhrs", ""),
            "lowering_status": google_corr.get("lowering_status", "") if google_corr else "",
            "furnishing_status": google_corr.get("furnishing_status", "") if google_corr else "",
            "despatch_status": google_corr.get("despatch_status", "") if google_corr else "",
            "google_pdc": google_corr.get("pdc", "") if google_corr else "",
            "google_remarks": google_corr.get("remarks", "") if google_corr else "",
            "plan_date": detail.get("plandate") or detail.get("plan_date") or "",
        }

        # Copy other raw fields from detail for print reports
        for k, v in detail.items():
            if k not in coach:
                coach[k] = v
        # Ensure division code is available for print reports
        coach["dvnid"] = detail.get("dvnid") or rec.get("dvnid") or ""

        # ── Aerial status ─────────────────────────
        coach["AERIAL_STATUS"] = _compute_aerial_status(coach)

        # ── Apply full decode_all for extra fields ─
        decode_all(coach, summary_coachno=coachno, summary_desc=coach_desc)

        enriched.append(coach)

        # ── Metrics bookkeeping ───────────────────
        metrics["total"] += 1
        aerial_status = coach["AERIAL_STATUS"]
        if aerial_status == "UNDER CORROSION":
            metrics["under_corrosion"] += 1
        elif aerial_status == "CORROSION DONE":
            metrics["corrosion_done"] += 1
        elif aerial_status == "OUTTURNED":
            metrics["outturned"] += 1
        elif aerial_status == "DANGER":
            metrics["danger"] += 1
        else:
            metrics["normal"] += 1

    # ac_locos are now retrieved from the synced erp_active_coaches table
    ac_locos = ac_locos_list

    # Update metrics to include AC Locomotives (which are considered NORMAL in aerial view)
    metrics["total"] += len(ac_locos)
    metrics["normal"] += len(ac_locos)

    # ── Build topology for frontend ──────────────────
    # The frontend renderLayoutNode expects:
    # - shop type: {type, zone, label, order} (order = pit list)
    # - flat type: {type, zone, label, pitnums}
    # - traverser: {type, label}
    from services.topology import TWO_SLOT_LINES, PITNUM_ALIASES

    # Normalize layout keys for frontend
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
    logger.info(
        "get_aerial_data: %d coaches, %d ac_locos",
        len(enriched), len(ac_locos),
    )
    return result
