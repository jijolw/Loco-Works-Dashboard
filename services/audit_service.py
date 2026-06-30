# =====================================================
# services/audit_service.py
# LW/PER Workshop Intelligence System
# Corrosion hours & despatch audit logic
# =====================================================

import logging
from datetime import datetime
from services.erp_service import fetch_master, fetch_clean, fetch_single, _parse_date
from services.decoders import decode_division, decode_family

logger = logging.getLogger(__name__)

def get_audit_data(fy_filter="ALL", family_filter="ALL", type_filter="ALL"):
    """
    Calculate and return filtered data for the Audit & Analysis module:
    1. Previous Workshop Corrosion Rankings (Filtered)
    2. Division Corrosion Rankings (Filtered)
    3. Active Coaches Missing Corrosion Hours (Filtered)
    4. FND (First Despatch, VG & Physical Despatch Pending) Coaches (Filtered)
    """
    # Normalize inputs
    fy_filter = str(fy_filter or "ALL").strip().upper()
    family_filter = str(family_filter or "ALL").strip().upper()
    type_filter = str(type_filter or "ALL").strip().upper()

    master_coaches = fetch_master()
    
    workshop_groups = {}
    division_groups = {}
    missing_hours_list = []
    condemned_returned_list = []
    
    for rec in master_coaches:
        # Exclude locomotives from rankings
        coach_desc = rec.get("coach_desc") or rec.get("coachdesc") or ""
        family = decode_family(coach_desc)
        if family == "LOCO":
            continue
            
        # Exclude condemned / returned / Bhopal status coaches from rankings
        status = str(rec.get("status") or rec.get("pohstatus") or "").strip().upper()
        if status in ("COND", "BHOPAL", "RETURN") or "COND" in status or "RETURN" in status:
            recd_str = rec.get("recd_date") or rec.get("recddate")
            recd_dt = _parse_date(recd_str)
            fy = "UNKNOWN"
            if recd_dt:
                y, m = recd_dt.year, recd_dt.month
                fy = f"{y}-{str(y+1)[2:]}" if m >= 4 else f"{y-1}-{str(y)[2:]}"
                
            # Apply filters
            if fy_filter != "ALL" and fy.upper() != fy_filter:
                continue
            if family_filter != "ALL" and family.upper() != family_filter:
                continue
            if type_filter != "ALL" and coach_desc.strip().upper() != type_filter:
                continue
                
            condemned_returned_list.append({
                "coachno": rec.get("coachno"),
                "coach_desc": coach_desc,
                "family": family,
                "division": decode_division(rec.get("division") or rec.get("dvnid")),
                "last_workshop": str(rec.get("last_poh") or "").strip().upper(),
                "recd_date": rec.get("recd_date") or rec.get("recddate") or "",
                "desp_date": rec.get("desp_date") or rec.get("despdate") or "",
                "actualdespdate": rec.get("actualdespdate") or "",
                "status": rec.get("status") or rec.get("pohstatus") or status,
                "pitnum": rec.get("pitnum") or ""
            })
            continue
            
        # Parse received date to find FY
        recd_str = rec.get("recd_date") or rec.get("recddate")
        recd_dt = _parse_date(recd_str)
        
        fy = "UNKNOWN"
        if recd_dt:
            y, m = recd_dt.year, recd_dt.month
            fy = f"{y}-{str(y+1)[2:]}" if m >= 4 else f"{y-1}-{str(y)[2:]}"
            
        # Apply filters
        if fy_filter != "ALL" and fy.upper() != fy_filter:
            continue
        if family_filter != "ALL" and family.upper() != family_filter:
            continue
        if type_filter != "ALL" and coach_desc.strip().upper() != type_filter:
            continue

        # Parse corrosion hours
        try:
            pre = float(rec.get("presurveyhrs") or 0)
        except (ValueError, TypeError):
            pre = 0.0
        try:
            final = float(rec.get("finalhrs") or 0)
        except (ValueError, TypeError):
            final = 0.0
        eff_hrs = final if final > 0 else pre

        # Corrosion not filled check (shows for selected years across all master coaches)
        if eff_hrs == 0:
            missing_hours_list.append({
                "coachno": rec.get("coachno"),
                "coach_desc": coach_desc,
                "family": family,
                "division": decode_division(rec.get("division") or rec.get("dvnid")),
                "recd_date": rec.get("recd_date") or rec.get("recddate"),
                "status": rec.get("status") or rec.get("pohstatus"),
                "pitnum": rec.get("pitnum") or ""
            })
        
        # Workshop Grouping
        wks = str(rec.get("last_poh") or "").strip().upper()
        if wks and wks not in ("", "NAN", "NONE", "0"):
            if wks not in workshop_groups:
                workshop_groups[wks] = {"total": 0, "with_hours": 0, "total_hours": 0.0, "heavy_count": 0, "max_hours": 0.0, "coaches": []}
            
            w_stats = workshop_groups[wks]
            w_stats["total"] += 1
            w_stats["coaches"].append({
                "coachno": rec.get("coachno"),
                "coach_desc": coach_desc,
                "recd_date": recd_str,
                "corrosion_hours": eff_hrs,
                "status": rec.get("status") or rec.get("pohstatus") or ""
            })
            if eff_hrs > 0:
                w_stats["with_hours"] += 1
                w_stats["total_hours"] += eff_hrs
                if eff_hrs > w_stats["max_hours"]:
                    w_stats["max_hours"] = eff_hrs
                if eff_hrs > 500:
                    w_stats["heavy_count"] += 1
                    
        # Division Grouping
        dvn = str(rec.get("division") or rec.get("dvnid") or "").strip()
        if dvn and dvn not in ("", "NAN", "NONE", "0"):
            dvn_name = decode_division(dvn)
            if dvn_name not in division_groups:
                division_groups[dvn_name] = {"total": 0, "with_hours": 0, "total_hours": 0.0, "heavy_count": 0, "max_hours": 0.0, "coaches": []}
                
            d_stats = division_groups[dvn_name]
            d_stats["total"] += 1
            d_stats["coaches"].append({
                "coachno": rec.get("coachno"),
                "coach_desc": coach_desc,
                "recd_date": recd_str,
                "corrosion_hours": eff_hrs,
                "status": rec.get("status") or rec.get("pohstatus") or ""
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

    # 2. Active Coaches FND Pending List
    active_coaches = fetch_clean()
    fnd_list = []
    
    for c in active_coaches:
        coach_desc = c.get("coach_desc") or c.get("coachdesc") or ""
        family = decode_family(coach_desc)
        if family == "LOCO":
            continue
            
        recd_str = c.get("recd_date") or c.get("recddate")
        recd_dt = _parse_date(recd_str)
        
        fy = "UNKNOWN"
        if recd_dt:
            y, m = recd_dt.year, recd_dt.month
            fy = f"{y}-{str(y+1)[2:]}" if m >= 4 else f"{y-1}-{str(y)[2:]}"

        # Apply same filters
        if fy_filter != "ALL" and fy.upper() != fy_filter:
            continue
        if family_filter != "ALL" and family.upper() != family_filter:
            continue
        if type_filter != "ALL" and coach_desc.strip().upper() != type_filter:
            continue

        demandid = c.get("demandid")
        if not demandid:
            continue
            
        detail = fetch_single(demandid)
        
        # FND / VG Pending List
        actual_desp = str(detail.get("actualdespdate") or "").strip()
        has_actual_desp = actual_desp and actual_desp.lower() not in ("none", "null", "nan", "")
        
        if has_actual_desp:
            vg_status = detail.get("vg_status") or ""
            phys_status = detail.get("physical_status") or ""
            
            if vg_status != "Completed" or phys_status != "Despatched":
                fnd_list.append({
                    "coachno": c.get("coachno"),
                    "coach_desc": coach_desc,
                    "family": family,
                    "pitnum": c.get("pitnum") or "",
                    "recd_date": c.get("recd_date"),
                    "desp_date": desp_date,
                    "vg_status": vg_status,
                    "vg_date": detail.get("vg_date") or "",
                    "physical_status": phys_status,
                    "physical_date": detail.get("physical_date") or ""
                })
                
    return {
        "workshop_rankings": workshop_rankings,
        "division_rankings": division_rankings,
        "missing_hours": missing_hours_list,
        "fnd": fnd_list,
        "condemned_returned": condemned_returned_list
    }
