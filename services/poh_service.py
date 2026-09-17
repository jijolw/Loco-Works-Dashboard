# =====================================================
# services/poh_service.py
# POH schedule cleanup, wrong selections, and previous workshop metrics
# =====================================================

import logging
from services.audit_service import get_audit_data, _load_all_records
from services.decoders import decode_family, decode_repair, decode_all
from services.erp_service import _parse_date

logger = logging.getLogger(__name__)

def get_standard_lhb_schedule(repair_code):
    rc = str(repair_code or "").strip().upper()
    if "SS1" in rc or "SS-1" in rc or rc == "104":
        return "SS1"
    elif "SS2" in rc or "SS-2" in rc or rc in {"121", "243", "244"}:
        return "SS2"
    elif "SS3" in rc or "SS-3" in rc or rc in {"122", "241", "242"}:
        return "SS3"
    elif "POH" in rc or rc in {"1", "5", "6", "7", "141"}:
        return "CONV_POH"
    return "OTHER"

def analyze_poh_performance(fy=None, family="ALL"):
    """
    Perform POH analytics with 100% unified mathematical consistency with Audit & Analysis.
    """
    audit_res = get_audit_data(fy_filter=fy, family_filter=family, type_filter="ALL")
    
    # Format workshop map
    wks_data = {}
    for w in audit_res.get("workshop_rankings", []):
        wks_name = w["workshop"]
        wks_data[wks_name] = {
            "workshop": wks_name,
            "total_coaches": w["total_received"],
            "with_hours": w["coaches_with_hours"],
            "total_hours": round(w["avg_hours"] * w["coaches_with_hours"], 1),
            "avg_hours": w["avg_hours"],
            "max_hours": w["max_hours"],
            "heavy_pct": w["heavy_pct"],
            "coaches": w["coaches"]
        }
        
    # LHB Schedule analysis
    master, cache_data = _load_all_records()
    lhb_by_fy = {}
    lhb_by_type = {}
    lhb_coaches_list = []
    
    for rec in master:
        did = str(rec.get("demandid") or rec.get("demandId") or "").strip()
        det = cache_data.get(did, {})
        coach_desc = rec.get("coach_desc") or rec.get("coachdesc") or det.get("coach_desc") or ""
        family_dec = decode_family(coach_desc)
        
        if family_dec == "LHB":
            recd_str = rec.get("recd_date") or rec.get("recddate") or det.get("recd_date") or ""
            recd_dt = _parse_date(recd_str)
            coach_fy = "UNKNOWN"
            if recd_dt:
                y, m = recd_dt.year, recd_dt.month
                coach_fy = f"{y}-{str(y+1)[2:]}" if m >= 4 else f"{y-1}-{str(y)[2:]}"
            elif len(recd_str) >= 4:
                try:
                    parts = recd_str.replace("-", "/").split("/")
                    yr = int(parts[0]) if len(parts[0]) == 4 else (int(parts[2]) if len(parts) > 2 and len(parts[2]) == 4 else (2000 + int(parts[2]) if len(parts) > 2 else 0))
                    mo = int(parts[1]) if len(parts) > 1 else 1
                    if yr >= 2018:
                        coach_fy = f"{yr}-{str(yr+1)[2:]}" if mo >= 4 else f"{yr-1}-{str(yr)[2:]}"
                except Exception:
                    pass
                
            rt = str(det.get("repair_type") or det.get("repairid") or rec.get("repair_type") or "").strip()
            sched = get_standard_lhb_schedule(rt)
            
            if coach_fy not in lhb_by_fy:
                lhb_by_fy[coach_fy] = {"SS1": 0, "SS2": 0, "SS3": 0, "CONV_POH": 0, "OTHER": 0, "TOTAL": 0}
            lhb_by_fy[coach_fy][sched] = lhb_by_fy[coach_fy].get(sched, 0) + 1
            lhb_by_fy[coach_fy]["TOTAL"] += 1
            
            if coach_desc not in lhb_by_type:
                lhb_by_type[coach_desc] = {"SS1": 0, "SS2": 0, "SS3": 0, "CONV_POH": 0, "OTHER": 0, "TOTAL": 0}
            lhb_by_type[coach_desc][sched] = lhb_by_type[coach_desc].get(sched, 0) + 1
            lhb_by_type[coach_desc]["TOTAL"] += 1
            
            if fy is None or fy.upper() == "ALL" or coach_fy.upper() == fy.upper():
                cno = rec.get("coachno") or det.get("coachno") or ""
                last_poh_wks = str(rec.get("last_poh") or det.get("last_poh") or "").strip().upper()
                lhb_coaches_list.append({
                    "coachno": cno,
                    "coach_desc": coach_desc,
                    "recd_date": recd_str,
                    "schedule": sched,
                    "raw_repair_type": rt,
                    "last_poh": last_poh_wks
                })
                
    return {
        "workshops": wks_data,
        "lhb_analysis": {
            "by_fy": lhb_by_fy,
            "by_type": lhb_by_type,
            "coaches": lhb_coaches_list
        }
    }

def get_targets_vs_achievement(fy=None):
    try:
        from services.db_service import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM outturn_targets ORDER BY month_id ASC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        if rows:
            return {"targets": rows}
    except Exception:
        pass
    return {"targets": []}
