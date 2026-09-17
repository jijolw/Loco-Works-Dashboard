
def is_excluded_status(st='', stage='', tfr_s=''):
    return False
import os
import json
import calendar
from datetime import datetime
from services.type_wise_holding_service import (
    get_type_wise_holding_report_data,
    map_coach_to_category,
    decode_family,
)

def _parse_filter_date(val):
    if not val:
        return None
    val_s = str(val).strip().replace(".", "/")
    if "-" in val_s:
        # Check if YYYY-MM-DD
        parts = val_s.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            try:
                return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            except:
                return None
        elif len(parts) == 3:
            try:
                return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
            except:
                return None
    elif "/" in val_s:
        parts = val_s.split("/")
        if len(parts) == 3:
            try:
                d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                if y < 100: y += 2000
                return datetime(y, m, d)
            except:
                return None
    return None

def get_outturn_data(start_date=None, end_date=None):
    """
    Returns dynamic outturn data derived 100% from ERP for any custom date range or month.
    """
    now = datetime.now()
    st_dt = _parse_filter_date(start_date)
    end_dt = _parse_filter_date(end_date)
    
    if st_dt and not end_dt:
        end_dt = datetime(st_dt.year, st_dt.month, calendar.monthrange(st_dt.year, st_dt.month)[1], 23, 59, 59)
    elif end_dt and not st_dt:
        st_dt = datetime(end_dt.year, end_dt.month, 1)
    elif not st_dt and not end_dt:
        st_dt = datetime(now.year, now.month, 1)
        end_dt = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1], 23, 59, 59)
        
    # Month name and year
    month_name = calendar.month_name[st_dt.month]
    year_val = st_dt.year
    
    # Load caches
    possible_coaches = [
        r"D:\TypeWiseHoldingApp\erp_coaches_cache.json",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "erp_coaches_cache.json"),
        "erp_coaches_cache.json"
    ]
    possible_master = [
        r"D:\TypeWiseHoldingApp\erp_master_cache.json",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "erp_master_cache.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "erp_master_cache.json"),
        "erp_master_cache.json"
    ]
    c_path = next((p for p in possible_coaches if os.path.exists(p)), possible_coaches[0])
    m_path = next((p for p in possible_master if os.path.exists(p)), possible_master[0])
    
    cache_data = {}
    master_data = []
    try:
        with open(c_path, "r", encoding="utf-8") as f: cache_data = json.load(f)
    except: pass
    try:
        with open(m_path, "r", encoding="utf-8") as f: master_data = json.load(f)
    except: pass

    # Merge fresh live Keycloak demands (essential for current month like September 2026)
    try:
        from services.type_wise_holding_service import fetch_live_keycloak_demands, fetch_coach_meta
        live_demands = fetch_live_keycloak_demands()
        known_demands = set(str(m.get("demandid") or "").strip() for m in master_data)
        
        for did_s, itm in live_demands.items():
            disp_raw = itm.get("dispatchDate")
            cno = str(itm.get("coachNo") or "").strip()
            
            # Always ensure live dispatchDate is recorded in cache_data
            if disp_raw and cno:
                desp_str = str(disp_raw).split("T")[0]
                act_str = str(itm.get("actualDispatchDate") or "").split("T")[0] if itm.get("actualDispatchDate") else ""
                
                if did_s not in cache_data:
                    cache_data[did_s] = {}
                cache_data[did_s]["coachno"] = cno
                cache_data[did_s]["desp_date"] = desp_str
                cache_data[did_s]["actualdespdate"] = act_str
                cache_data[did_s]["status"] = itm.get("status") or "Running"
                cache_data[did_s]["repair_type"] = str(itm.get("repairType") or "1")
                
                if str(did_s) not in known_demands:
                    meta = fetch_coach_meta(cno)
                    desc = meta.get("coachTypeDescription") or itm.get("coachDesc") or "GS"
                    divn = meta.get("divisionName") or meta.get("divisionId") or "PGT"
                    master_data.append({
                        "coachno": cno,
                        "demandid": did_s,
                        "coach_desc": desc,
                        "division": divn,
                        "repair_type": str(itm.get("repairType") or "1"),
                        "status": itm.get("status") or "Running"
                    })
                    cache_data[did_s]["coach_desc"] = desc
                    cache_data[did_s]["division"] = divn
    except Exception as e:
        pass

    coaches_list = []
    coach_types_counts = {}
    division_counts = {}
    seen = set()
    physical_count = 0
    fnd_count = 0

    for m in master_data:
        cno = str(m.get("coachno") or "").strip()
        if not cno or cno in seen:
            continue
        did = str(m.get("demandid") or "").strip()
        det = cache_data.get(did, {})
        
        st = str(det.get("status") or m.get("status") or "").strip().upper()
        rep = str(det.get("repair_type") or m.get("repair_type") or "").strip().upper()
        stage = str(det.get("stageid") or m.get("stageid") or "").strip()
        desc = str(det.get("coach_desc") or m.get("coach_desc") or "").strip()
        divn = det.get("division") or m.get("division") or "MAS"
        
        tfr_s = det.get('tfr_date') or m.get('tfr_date') or ''
        if is_excluded_status(st, stage, tfr_s) or rep == '161':
            continue
        # NMG included in NMG category
            
        desp_s = det.get("desp_date") or ""
        act_s = det.get("actualdespdate") or ""
        desp_dt = _parse_filter_date(desp_s)
        act_dt = _parse_filter_date(act_s)
        
        # Check if outturn falls in selected date range
        if desp_dt and (st_dt <= desp_dt <= end_dt):
            seen.add(cno)
            fam = decode_family(desc)
            cat = map_coach_to_category(desc, family=fam, repair_type=rep)
            
            # Physical Despatch
            if act_dt and act_dt <= now:
                physical_count += 1
                c_status = "Despatched"
                act_display = act_s
            else:
                fnd_count += 1
                c_status = "FND"
                act_display = ""

            c_dict = {
                "coachno": cno,
                "coach_desc": desc,
                "category": cat,
                "family": fam,
                "division": divn,
                "desp_date": desp_s,
                "actualdespdate": act_display,
                "status": c_status,
                "pitnum": "DESP" if c_status == "Despatched" else (det.get("pit_num") or "SHOP"),
                "corr_comp": det.get("corr_comp", "")
            }
            coaches_list.append(c_dict)
            coach_types_counts[cat] = coach_types_counts.get(cat, 0) + 1
            division_counts[divn] = division_counts.get(divn, 0) + 1

    total_outturn = len(coaches_list)
    rep_meta = get_type_wise_holding_report_data(month_name, year_val)

    return {
        "coaches": coaches_list,
        "metrics": {
            "total": total_outturn,
            "physical": physical_count,
            "fnd": fnd_count,
            "target": rep_meta["total"]["target"],
            "coach_types": coach_types_counts,
            "divisions": division_counts
        },
        "target": rep_meta["total"]["target"],
        "physical_despatch": physical_count,
        "fnd": fnd_count,
        "total_outturn": total_outturn,
        "categories_breakdown": rep_meta["data"],
        "month": month_name,
        "year": year_val,
        "start_date": st_dt.strftime("%Y-%m-%d"),
        "end_date": end_dt.strftime("%Y-%m-%d")
    }

def get_outturn_report_data(month_name="August", year_val=2026):
    m_idx = list(calendar.month_name).index(str(month_name).capitalize())
    last_d = calendar.monthrange(int(year_val), m_idx)[1]
    st = f"{year_val}-{m_idx:02d}-01"
    end = f"{year_val}-{m_idx:02d}-{last_d:02d}"
    return get_outturn_data(start_date=st, end_date=end)
