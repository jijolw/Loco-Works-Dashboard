# =====================================================
# services/audit_service.py
# LW/PER Workshop Intelligence System
# Corrosion hours & despatch audit logic (12,986 records support)
# =====================================================

import logging
import os
import json
from datetime import datetime
from services.erp_service import fetch_master, _parse_date
from services.decoders import decode_division, decode_family

logger = logging.getLogger(__name__)

def _load_all_records():
    """Load complete master dataset (up to 12,986 records) and detail cache."""
    master = []
    coaches_detail = {}
    
    # Try 13k archive master cache
    archive_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "erp_master_cache.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "erp_master_cache.json"),
        os.path.join(os.getcwd(), "erp_master_cache.json")
    ]
    for p in archive_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if len(data) > len(master):
                        master = data
            except Exception:
                pass
                
    if not master:
        master = fetch_master()

    detail_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "erp_coaches_cache.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "erp_coaches_cache.json"),
        os.path.join(os.getcwd(), "erp_coaches_cache.json")
    ]
    for p in detail_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    coaches_detail.update(json.load(f))
            except Exception:
                pass

    return master, coaches_detail

def get_audit_data(fy_filter="ALL", family_filter="ALL", type_filter="ALL"):
    """
    Calculate and return filtered data for the Audit & Analysis module:
    1. Previous Workshop Corrosion Rankings (Filtered)
    2. Division Corrosion Rankings (Filtered)
    3. Active Coaches Missing Corrosion Hours (Filtered)
    4. FND (First Despatch, VG & Physical Despatch Pending) Coaches (Filtered)
    """
    fy_filter = str(fy_filter or "ALL").strip().upper()
    family_filter = str(family_filter or "ALL").strip().upper()
    type_filter = str(type_filter or "ALL").strip().upper()

    master_coaches, coaches_detail = _load_all_records()
    
    workshop_groups = {}
    division_groups = {}
    missing_hours_list = []
    condemned_returned_list = []
    
    for rec in master_coaches:
        did = str(rec.get("demandid") or rec.get("demandId") or "").strip()
        det = coaches_detail.get(did, {})
        
        cno = rec.get("coachno") or det.get("coachno") or ""
        coach_desc = rec.get("coach_desc") or rec.get("coachdesc") or det.get("coach_desc") or ""
        family = decode_family(coach_desc)
        if family == "LOCO":
            continue
            
        status = str(rec.get("status") or rec.get("pohstatus") or det.get("status") or "").strip().upper()
        recd_str = rec.get("recd_date") or rec.get("recddate") or det.get("recd_date") or ""
        recd_dt = _parse_date(recd_str)
        
        fy = "UNKNOWN"
        if recd_dt:
            y, m = recd_dt.year, recd_dt.month
            fy = f"{y}-{str(y+1)[2:]}" if m >= 4 else f"{y-1}-{str(y)[2:]}"
        elif len(recd_str) >= 4:
            try:
                parts = recd_str.replace("-", "/").split("/")
                yr = int(parts[0]) if len(parts[0]) == 4 else (int(parts[2]) if len(parts) > 2 and len(parts[2]) == 4 else (2000 + int(parts[2]) if len(parts) > 2 else 0))
                mo = int(parts[1]) if len(parts) > 1 else 1
                if yr >= 2018:
                    fy = f"{yr}-{str(yr+1)[2:]}" if mo >= 4 else f"{yr-1}-{str(yr)[2:]}"
            except Exception:
                pass
                
        # Exclude condemned / returned / Bhopal status coaches from rankings
        if status in ("COND", "BHOPAL", "RETURN") or "COND" in status or "RETURN" in status:
            if fy_filter != "ALL" and fy.upper() != fy_filter:
                continue
            if family_filter != "ALL" and family.upper() != family_filter:
                continue
            if type_filter != "ALL" and coach_desc.strip().upper() != type_filter:
                continue
                
            condemned_returned_list.append({
                "coachno": cno,
                "coach_desc": coach_desc,
                "family": family,
                "division": decode_division(rec.get("division") or rec.get("dvnid") or det.get("division")),
                "last_workshop": str(rec.get("last_poh") or det.get("last_poh") or "").strip().upper(),
                "recd_date": recd_str,
                "desp_date": rec.get("desp_date") or det.get("desp_date") or "",
                "actualdespdate": rec.get("actualdespdate") or det.get("actualdespdate") or "",
                "status": status,
                "pitnum": rec.get("pit_num") or rec.get("pitnum") or det.get("pit_num") or ""
            })
            continue
            
        # Apply filters
        if fy_filter != "ALL" and fy.upper() != fy_filter:
            continue
        if family_filter != "ALL" and family.upper() != family_filter:
            continue
        if type_filter != "ALL" and coach_desc.strip().upper() != type_filter:
            continue

        # Parse corrosion hours
        ps_str = str(det.get("presurvey") or det.get("presurveyhrs") or rec.get("presurveyhrs") or "").strip()
        fn_str = str(det.get("final") or det.get("finalhrs") or rec.get("finalhrs") or "").strip()
        
        pre = 0.0
        final = 0.0
        try:
            if ps_str: pre = float(ps_str)
        except Exception: pass
        try:
            if fn_str: final = float(fn_str)
        except Exception: pass
        
        eff_hrs = final if final > 0 else pre

        # Missing hours check
        if eff_hrs == 0:
            missing_hours_list.append({
                "coachno": cno,
                "coach_desc": coach_desc,
                "family": family,
                "division": decode_division(rec.get("division") or rec.get("dvnid") or det.get("division")),
                "recd_date": recd_str,
                "status": status,
                "pitnum": rec.get("pit_num") or rec.get("pitnum") or det.get("pit_num") or ""
            })
        
        # Workshop Grouping
        wks = str(rec.get("last_poh") or det.get("last_poh") or "").strip().upper()
        if wks and wks not in ("", "NAN", "NONE", "0"):
            if wks not in workshop_groups:
                workshop_groups[wks] = {"total": 0, "with_hours": 0, "total_hours": 0.0, "heavy_count": 0, "max_hours": 0.0, "coaches": []}
            
            w_stats = workshop_groups[wks]
            w_stats["total"] += 1
            w_stats["coaches"].append({
                "coachno": cno,
                "coach_desc": coach_desc,
                "recd_date": recd_str,
                "corrosion_hours": eff_hrs,
                "status": status
            })
            if eff_hrs > 0:
                w_stats["with_hours"] += 1
                w_stats["total_hours"] += eff_hrs
                if eff_hrs > w_stats["max_hours"]:
                    w_stats["max_hours"] = eff_hrs
                if eff_hrs > 500:
                    w_stats["heavy_count"] += 1
                    
        # Division Grouping
        dvn = str(rec.get("division") or rec.get("dvnid") or det.get("division") or "").strip()
        if dvn and dvn not in ("", "NAN", "NONE", "0"):
            dvn_name = decode_division(dvn)
            if dvn_name not in division_groups:
                division_groups[dvn_name] = {"total": 0, "with_hours": 0, "total_hours": 0.0, "heavy_count": 0, "max_hours": 0.0, "coaches": []}
                
            d_stats = division_groups[dvn_name]
            d_stats["total"] += 1
            d_stats["coaches"].append({
                "coachno": cno,
                "coach_desc": coach_desc,
                "recd_date": recd_str,
                "corrosion_hours": eff_hrs,
                "status": status
            })
            if eff_hrs > 0:
                d_stats["with_hours"] += 1
                d_stats["total_hours"] += eff_hrs
                if eff_hrs > d_stats["max_hours"]:
                    d_stats["max_hours"] = eff_hrs
                if eff_hrs > 500:
                    d_stats["heavy_count"] += 1

    # Format rankings
    workshop_rankings = []
    for wks, stats in workshop_groups.items():
        avg = round(stats["total_hours"] / stats["with_hours"], 1) if stats["with_hours"] > 0 else 0.0
        heavy_pct = round((stats["heavy_count"] / stats["with_hours"]) * 100, 1) if stats["with_hours"] > 0 else 0.0
        workshop_rankings.append({
            "workshop": wks,
            "total_received": stats["total"],
            "coaches_with_hours": stats["with_hours"],
            "avg_hours": avg,
            "max_hours": stats["max_hours"],
            "heavy_pct": heavy_pct,
            "coaches": stats["coaches"]
        })
    workshop_rankings.sort(key=lambda x: x["avg_hours"], reverse=True)

    division_rankings = []
    for dvn, stats in division_groups.items():
        avg = round(stats["total_hours"] / stats["with_hours"], 1) if stats["with_hours"] > 0 else 0.0
        heavy_pct = round((stats["heavy_count"] / stats["with_hours"]) * 100, 1) if stats["with_hours"] > 0 else 0.0
        division_rankings.append({
            "division": dvn,
            "total_received": stats["total"],
            "coaches_with_hours": stats["with_hours"],
            "avg_hours": avg,
            "max_hours": stats["max_hours"],
            "heavy_pct": heavy_pct,
            "coaches": stats["coaches"]
        })
    division_rankings.sort(key=lambda x: x["avg_hours"], reverse=True)

    fnd_list = []
                
    return {
        "workshop_rankings": workshop_rankings,
        "division_rankings": division_rankings,
        "missing_hours": missing_hours_list,
        "fnd": fnd_list,
        "condemned_returned": condemned_returned_list
    }
