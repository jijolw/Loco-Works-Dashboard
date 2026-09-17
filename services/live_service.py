import os
import json
from datetime import datetime
from services.inside_shop_service import get_inside_shop_data

def get_live_data():
    """
    Return clean live active coach data for the Carriage Repair shop floor:
    31 Work Area coaches + 27 Yard coaches + 6 FND coaches.
    """
    data = get_inside_shop_data()
    
    # Safe retrieval supporting both flat keys and nested 'sections'
    if "work_area" in data and isinstance(data["work_area"], list):
        work_area = data["work_area"]
        yard = data.get("yard", [])
        fnd = data.get("fnd", [])
        w_cnt = data.get("work_area_count", len(work_area))
        y_cnt = data.get("yard_count", len(yard))
        f_cnt = data.get("fnd_count", len(fnd))
        t_hold = data.get("total_holding", len(work_area) + len(yard) + len(fnd))
    else:
        sec = data.get("sections", {})
        work_area = sec.get("icf", []) + sec.get("lhb", []) + sec.get("emu_demu", [])
        yard = sec.get("yard", [])
        fnd = sec.get("fnd", [])
        cnts = data.get("counts", {})
        w_cnt = cnts.get("work_area", len(work_area))
        y_cnt = cnts.get("yard", len(yard))
        f_cnt = cnts.get("fnd", len(fnd))
        t_hold = cnts.get("total_inside", len(work_area) + len(yard) + len(fnd))
        
    all_coaches = work_area + yard + fnd
    
    for c in all_coaches:
        c["status_label"] = c.get("status", "Inside")
        c["pitnum"] = c.get("pit", "")
        c["stageid"] = c.get("stage", "")
        
    return {
        "coaches": all_coaches,
        "metrics": {
            "work_area": w_cnt,
            "yard": y_cnt,
            "fnd": f_cnt,
            "total_holding": t_hold
        },
        "suspicious": []
    }

def get_coaches_progress():
    data = get_inside_shop_data()
    if "work_area" in data and isinstance(data["work_area"], list):
        return data["work_area"]
    sec = data.get("sections", {})
    return sec.get("icf", []) + sec.get("lhb", []) + sec.get("emu_demu", [])

def live_cache_clear():
    pass

def _resolve_division(rec, detail):
    return detail.get("division") or rec.get("division") or "MAS"
