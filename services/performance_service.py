import os
import io
import json
import calendar
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from services.type_wise_holding_service import get_type_wise_holding_report_data, STANDARD_TARGETS

def get_performance_report_data(month_name="August", year_val=2026, bypass_cache=False, report_type="target_achievement"):
    """
    100% Pure ERP Performance Report Data (Target vs Achievement & Despatch Summary).
    Single Source of Truth derived from type-wise holding service.
    """
    rep = get_type_wise_holding_report_data(month_name, year_val)
    
    cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "erp_coaches_cache.json")
    if not os.path.exists(cache_file): cache_file = "erp_coaches_cache.json"
    cache_data = {}
    try:
        with open(cache_file, "r", encoding="utf-8") as f: cache_data = json.load(f)
    except: pass
    
    master_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "erp_master_cache.json")
    if not os.path.exists(master_file): master_file = "erp_master_cache.json"
    master_data = []
    try:
        with open(master_file, "r", encoding="utf-8") as f: master_data = json.load(f)
    except: pass

    coach_meta = {}
    for m in master_data:
        cno = str(m.get("coachno") or "").strip()
        if cno:
            did = str(m.get("demandid") or "").strip()
            det = cache_data.get(did, {})
            coach_meta[cno] = {
                "coachno": cno,
                "coach_desc": det.get("coach_desc") or m.get("coach_desc") or "",
                "division": det.get("division") or m.get("division") or "MAS",
                "repair_type": det.get("repair_type") or m.get("repair_type") or "POH",
                "presurveyhrs": det.get("presurvey", ""),
                "finalhrs": det.get("final", ""),
                "last_poh": det.get("last_poh", ""),
                "last_pohdate": det.get("last_pohdate", ""),
                "pohdays": det.get("pohdays", "")
            }

    hq_targets = {cat: STANDARD_TARGETS.get(cat, 0) for cat in STANDARD_TARGETS}
    internal_targets = {cat: STANDARD_TARGETS.get(cat, 0) for cat in STANDARD_TARGETS}
    
    outturns = []
    fnd_outturns = []
    
    for r in rep["data"]:
        cat = r["coach_type"]
        # Physical despatches
        for cno in r["physical_despatch_coaches"]:
            meta = coach_meta.get(cno, {})
            desp_dt = r["physical_despatch_dates"].get(cno, "15/08/2026")
            outturns.append({
                "coachno": cno,
                "coach_desc": meta.get("coach_desc") or cat,
                "family": cat,
                "division": meta.get("division", "MAS"),
                "repair_type": meta.get("repair_type", "POH"),
                "desp_date": desp_dt,
                "erp_desp_date": desp_dt,
                "detail_raw": {
                    "actualdespdate": desp_dt,
                    "presurveyhrs": meta.get("presurveyhrs", ""),
                    "finalhrs": meta.get("finalhrs", ""),
                    "last_poh": meta.get("last_poh", ""),
                    "last_pohdate": meta.get("last_pohdate", ""),
                    "pohdays": meta.get("pohdays", "")
                }
            })
            
        # FND coaches
        for cno in r["fnd_coaches"]:
            meta = coach_meta.get(cno, {})
            fnd_outturns.append({
                "coachno": cno,
                "coach_desc": meta.get("coach_desc") or cat,
                "family": cat,
                "division": meta.get("division", "MAS"),
                "repair_type": meta.get("repair_type", "POH"),
                "desp_date": f"{month_name} {year_val}",
                "erp_desp_date": f"{month_name} {year_val}",
                "detail_raw": {
                    "actualdespdate": "",
                    "presurveyhrs": meta.get("presurveyhrs", ""),
                    "finalhrs": meta.get("finalhrs", ""),
                    "last_poh": meta.get("last_poh", ""),
                    "last_pohdate": meta.get("last_pohdate", ""),
                    "pohdays": meta.get("pohdays", "")
                }
            })

    return {
        "hq_targets": hq_targets,
        "internal_targets": internal_targets,
        "outturns": outturns,
        "fnd_outturns": fnd_outturns,
        "gsheet_outturns": outturns,
        "month": month_name,
        "year": year_val
    }

def generate_performance_excel(month_name="August", year_val=2026, *args, **kwargs):
    from services.type_wise_holding_service import generate_type_wise_holding_excel
    return generate_type_wise_holding_excel(month_name, year_val)
