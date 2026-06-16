# =====================================================
# services/poh_service.py
# POH schedule cleanup, wrong selections, and previous workshop metrics
# =====================================================

import logging
from datetime import datetime

from services.erp_service import fetch_master, fetch_single, fetch_year_built, _parse_date
from services.decoders import decode_family, decode_repair, decode_all
from services.corrosion_service import extract_year_built_from_no

logger = logging.getLogger(__name__)

# Standard LHB schedule mappings
LHB_SS1_CODES = {"104"}
LHB_SS2_CODES = {"121", "243", "244"}
LHB_SS3_CODES = {"122", "241", "242"}
CONV_POH_CODES = {"1", "5", "6", "7", "141"}

def get_standard_lhb_schedule(repair_code):
    """Map repair code to standardized LHB schedule."""
    rc = str(repair_code).strip().upper()
    if rc in LHB_SS1_CODES or "SS1" in rc:
        return "SS1"
    elif rc in LHB_SS2_CODES or "SS2" in rc:
        return "SS2"
    elif rc in LHB_SS3_CODES or "SS3" in rc:
        return "SS3"
    elif rc in CONV_POH_CODES or "POH" in rc:
        return "CONV_POH"
    return "OTHER"

def get_weight_band(hrs):
    if hrs is None or hrs <= 0:
        return "Not Filled"
    elif hrs <= 200:
        return "Light"
    elif hrs <= 500:
        return "Medium Light"
    elif hrs <= 1000:
        return "Medium Heavy"
    else:
        return "Very Heavy"

def analyze_poh_performance(fy=None):
    """
    Perform POH analytics:
    1. Previous workshop performance (man-hours and premature return rates, with detailed coach lists)
    2. LHB schedule histories and misclassification checks (yearly schedule metrics)
    """
    master = fetch_master()
    if not master:
        return {"workshops": {}, "lhb_analysis": {"by_fy": {}, "by_type": {}, "coaches": []}}
        
    now = datetime.now()
    wks_data = {} # workshop_code -> statistics
    
    # Restrict previous workshop analysis to coaches received in the selected financial year
    if fy:
        try:
            start_year = int(fy.split("-")[0])
            start_date = datetime(start_year, 4, 1)
            end_date = datetime(start_year + 1, 3, 31, 23, 59, 59)
        except Exception:
            start_date = datetime(2025, 4, 1)
            end_date = now
    else:
        start_date = datetime(2025, 4, 1)
        end_date = now
        
    lhb_by_fy = {}
    lhb_by_type = {}
    lhb_coaches_list = []
    
    # Track coach details for POH and LHB analysis
    for rec in master:
        recd_str = rec.get("recd_date") or rec.get("recddate")
        recd_dt = _parse_date(recd_str)
        if not recd_dt:
            continue
            
        coachno = rec.get("coachno", "")
        coach_desc = rec.get("coach_desc", "") or rec.get("coachdesc", "")
        family = decode_family(coach_desc)
        
        is_in_period = (start_date <= recd_dt <= end_date)
        is_lhb = (family == "LHB")
        
        # Performance optimization: Skip details for old non-LHB coaches
        if not is_in_period and not is_lhb:
            continue
            
        demandid = rec.get("demandid")
        if not demandid:
            continue
            
        try:
            detail = fetch_single(demandid)
        except Exception:
            continue
            
        # Filter out condemned / returned status coaches
        status = str(detail.get("status") or detail.get("pohstatus") or "").strip().upper()
        if status in ("COND", "BHOPAL", "RETURN") or "COND" in status or "RETURN" in status:
            continue
            
        rt = str(detail.get("repairid") or detail.get("repair_type") or rec.get("repairid") or rec.get("repair_type") or "").strip()
        last_poh_wks = str(detail.get("last_poh") or rec.get("last_poh") or "").strip().upper()
        
        # Calculate man hours
        try:
            pre = float(detail.get("presurveyhrs") or 0)
        except (ValueError, TypeError):
            pre = 0.0
        try:
            final = float(detail.get("finalhrs") or 0)
        except (ValueError, TypeError):
            final = 0.0
        eff_hrs = final if final > 0 else pre
        band = get_weight_band(eff_hrs)
        
        # Premature return: repair code is "4" (Out of Course Repair, "OR")
        is_premature = (rt == "4" or rt.upper() == "OR" or decode_repair(rt) == "OR")
        
        # Group by previous workshop (only for coaches received in the selected period)
        if is_in_period and last_poh_wks and last_poh_wks not in ("", "nan", "None", "0"):
            if last_poh_wks not in wks_data:
                wks_data[last_poh_wks] = {
                    "total_count": 0,
                    "premature_count": 0,
                    "man_hours_list": [],
                    "bands": {"Light": 0, "Medium Light": 0, "Medium Heavy": 0, "Very Heavy": 0, "Not Filled": 0},
                    "coaches": []
                }
            
            stats = wks_data[last_poh_wks]
            stats["total_count"] += 1
            if is_premature:
                stats["premature_count"] += 1
            if eff_hrs > 0:
                stats["man_hours_list"].append(eff_hrs)
            stats["bands"][band] += 1
            
            stats["coaches"].append({
                "coachno": coachno,
                "coach_desc": coach_desc,
                "family": family,
                "repair_type": decode_repair(rt),
                "recd_date": recd_str,
                "man_hours": eff_hrs,
                "weight_band": band,
                "is_premature": is_premature
            })
            
        # 2. LHB Schedule classification and history analysis
        if is_lhb:
            sched = get_standard_lhb_schedule(rt)
            
            # Check year built to compute physical age
            cm = fetch_year_built(coachno)
            yb_raw = str(cm.get("year_built", "") or detail.get("year_built", "") or rec.get("year_built", "")).strip()
            
            try:
                yb = int(float(yb_raw))
            except (ValueError, TypeError):
                yb = None
                
            fallback_yb = extract_year_built_from_no(coachno)
            if yb is not None and fallback_yb is not None and abs(yb - fallback_yb) >= 2:
                yb = fallback_yb
            elif yb is None:
                yb = fallback_yb
                
            age = recd_dt.year - yb if yb and recd_dt else None
            
            issue = None
            if sched == "CONV_POH":
                issue = "LHB Coach marked with Conventional POH code (needs SS2/SS3 standard)"
            elif sched == "OTHER" and rt not in ("", "4"): # exclude blank and OR
                issue = f"LHB Coach marked with unknown repair code: {rt}"
            elif age is not None:
                # Age checks for schedule misalignment with conservative buffers
                if age < 1 and sched in ("SS2", "SS3"):
                    issue = f"Coach is too young ({age} years) for selected schedule: {sched}"
                elif age > 10 and sched == "SS1":
                    issue = f"Coach is old ({age} years) for a minor SS1 schedule"
                    
            # Group LHB schedule statistics by Financial Year
            y, m = recd_dt.year, recd_dt.month
            fy = f"{y}-{str(y+1)[2:]}" if m >= 4 else f"{y-1}-{str(y)[2:]}"
            
            if fy not in lhb_by_fy:
                lhb_by_fy[fy] = {"SS1": 0, "SS2": 0, "SS3": 0, "CONV_POH": 0, "OTHER": 0, "TOTAL": 0}
            lhb_by_fy[fy][sched] += 1
            lhb_by_fy[fy]["TOTAL"] += 1
            
            # Group LHB schedule statistics by coach type
            if coach_desc not in lhb_by_type:
                lhb_by_type[coach_desc] = {"SS1": 0, "SS2": 0, "SS3": 0, "CONV_POH": 0, "OTHER": 0, "TOTAL": 0}
            lhb_by_type[coach_desc][sched] += 1
            lhb_by_type[coach_desc]["TOTAL"] += 1
            
            lhb_coaches_list.append({
                "coachno": coachno,
                "coach_desc": coach_desc,
                "repair_type": decode_repair(rt),
                "repair_code": rt,
                "schedule": sched,
                "year_built": yb,
                "age": age,
                "recd_date": recd_str,
                "last_poh_wks": last_poh_wks,
                "issue": issue,
                "fy": fy
            })

    # Summarize workshop stats
    workshops_summary = {}
    for wks, stats in wks_data.items():
        total = stats["total_count"]
        prem_cnt = stats["premature_count"]
        hrs_list = stats["man_hours_list"]
        
        avg_hrs = round(sum(hrs_list) / len(hrs_list), 1) if hrs_list else 0.0
        prem_rate = round((prem_cnt / total) * 100, 1) if total > 0 else 0.0
        
        # Calculate band percentages
        band_pcts = {}
        for b, count in stats["bands"].items():
            band_pcts[b] = round((count / total) * 100, 1) if total > 0 else 0.0
            
        workshops_summary[wks] = {
            "total_count": total,
            "avg_man_hours": avg_hrs,
            "premature_count": prem_cnt,
            "premature_rate": prem_rate,
            "bands": band_pcts,
            "band_counts": stats["bands"],
            "coaches": stats["coaches"]
        }
            
    # Sort workshops by total count descending
    sorted_workshops = dict(sorted(workshops_summary.items(), key=lambda x: x[1]["total_count"], reverse=True))

    return {
        "workshops": sorted_workshops,
        "lhb_analysis": {
            "by_fy": lhb_by_fy,
            "by_type": lhb_by_type,
            "coaches": lhb_coaches_list
        }
    }

def get_targets_vs_achievement(fy):
    """
    Get target vs achievement metrics for a given financial year from the database.
    """
    from services.db_service import get_targets_vs_achievement as rest_get_targets
    try:
        rows = rest_get_targets(fy)
        # Sort months chronologically by Financial Year: April (4) to March (3)
        def sort_key(r):
            m = r["month"]
            m_order = (m - 4) % 12 if m > 0 else 0
            family_name = f"{r['stock_type']} {r['schedule']} {r['ac_nac']}"
            return (m_order, family_name)
            
        sorted_rows = sorted(rows, key=sort_key)
        
        # Map calendar months to names
        month_names = {
            4: "April", 5: "May", 6: "June", 7: "July", 8: "August", 9: "September",
            10: "October", 11: "November", 12: "December", 1: "January", 2: "February", 3: "March"
        }
        
        comparison = []
        for r in sorted_rows:
            m = r["month"]
            st = r["stock_type"]
            sched = r["schedule"]
            ac_nac = r["ac_nac"]
            
            # Combine stock type, schedule, and class (AC/NAC) cleanly
            parts = [st, sched]
            if ac_nac and ac_nac.upper() != "NA":
                parts.append(ac_nac)
            family_name = " ".join(parts)
                
            t = r["target_qty"]
            a = r["achieved_qty"]
            wd = r["working_days"]
            
            comparison.append({
                "type": "monthly" if m > 0 else "yearly",
                "month": m,
                "month_name": month_names.get(m, "Full Year"),
                "family": family_name,
                "target": t,
                "actual": a,
                "variance": a - t,
                "working_days": wd
            })
            
        return comparison
    except Exception as e:
        logger.error(f"Error fetching targets for {fy}: {e}")
        return []
