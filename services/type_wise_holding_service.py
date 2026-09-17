import os
import sys
import io
import json
import calendar
from datetime import datetime, date
import requests
from concurrent.futures import ThreadPoolExecutor
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from services.erp_service import get_session, fetch_coach_meta
import config

STANDARD_TARGETS = {
    "CN": 5, "GS": 6, "CZ": 2, "SLR": 4, "LWSCN": 12, "LWS": 4, "LWACCN": 2, "LWACCW": 2,
    "EMU MC": 0, "EMU TC": 0, "MEMU MC": 0, "MEMU TC": 0,
    "DPC": 0, "DEMU TC": 0, "TW4W": 0, "TW8W": 0, "NMG": 0,
    "ART": 1, "ARMV": 0, "SPIC": 0, "OR": "-"
}

STANDARD_WORKSHOP_CATEGORIES = [
    "CN", "GS", "CZ", "SLR", "LWSCN", "LWS", "LWACCN", "LWACCW",
    "EMU MC", "EMU TC", "MEMU MC", "MEMU TC",
    "DPC", "DEMU TC", "TW4W", "TW8W", "NMG",
    "ART", "ARMV", "SPIC", "OR"
]

def _parse_date_live(val):
    if not val:
        return None
    if isinstance(val, (datetime, date)):
        return datetime(val.year, val.month, val.day) if isinstance(val, date) and not isinstance(val, datetime) else val
    val_str = str(val).strip().replace("T00:00:00", "").replace("-", "/").replace(".", "/")
    parts = val_str.split("/")
    if len(parts) == 3:
        try:
            if len(parts[0]) == 4:
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                if y < 100:
                    y += 2000
            return datetime(y, m, d)
        except Exception:
            return None
    return None

def _fmt_d(val):
    dt = _parse_date_live(val)
    return dt.strftime("%d/%m/%Y") if dt else ""

def get_true_railway(dvn_str):
    d = str(dvn_str or "").strip().upper()
    if "AJMER" in d or d in ("AII", "JP", "JU", "BKN"): return "NWR"
    if "LUCKNOW" in d or "LJN" in d or "NER" in d or d in ("BSB", "IZN"): return "NER"
    if "PURI" in d or "KUR" in d or d in ("WAT", "SBP"): return "ECoR"
    if "GHY" in d or "GUWAHATI" in d or d in ("KIR", "APDJ", "RNY", "LMG", "TSK"): return "NFR"
    if d in ("SBC", "MYS", "UBL"): return "SWR"
    if d in ("SC", "HYB", "BZA", "GTL", "GNT", "NED"): return "SCR"
    if d in ("BB", "BSL", "NGP", "PUNE", "SUR"): return "CR"
    if d in ("BCT", "BRC", "RTM", "RJT", "BVP", "ADI", "MMCT"): return "WR"
    if d in ("JBP", "BPL", "KOTA"): return "WCR"
    if d in ("DLI", "MB", "LKO", "FZR", "UMB"): return "NR"
    if d in ("HWH", "SDAH", "ASN", "MLDT"): return "ER"
    if d in ("KGP", "ADA", "CKP", "RNC"): return "SER"
    if d in ("R", "BSP"): return "SECR"
    if d in ("DHN", "DNR", "DDU", "SEE", "SPJ"): return "ECR"
    if d in ("PRYJ", "AGC", "JHS", "ALD", "PRAYAGRAJ"): return "NCR"
    if d in ("MAS", "TPJ", "MDU", "TVC", "PGT", "SA"): return "SR"
    return "SR"

def decode_family(desc):
    if not desc: return "ICF"
    d = str(desc).strip().upper()
    if any(k in d for k in ["LW", "LHB", "LS5", "LSLRD", "LVPH", "LSCN", "LS"]): return "LHB"
    if any(k in d for k in ["DEMU", "DPC", "DTC", "DHMU", "TSDTC", "TSNDTC"]) or d == "TC": return "DEMU"
    if any(k in d for k in ["TSMC", "TSTC", "TSDTC", "TSNDTC", "TRAINSET", "VB"]): return "VB"
    if any(k in d for k in ["EMU", "MEMU", "YSY", "YFSY", "YSD", "YZZS", "DMSC"]): return "EMU"
    if any(k in d for k in ["TW", "TOWER", "DETC", "RU"]): return "TOWER WAGON"
    if "NMG" in d: return "NMG"
    if any(k in d for k in ["ART", "ARMV", "SPART", "SPIC", "RH", "RHV", "RTRH", "MFD"]): return "SPECIAL"
    return "ICF"

def map_coach_to_category(desc, family="", repair_type=""):
    # If caller passes 2 positional arguments: (desc, repair_type)
    if family and not repair_type and (str(family) in ("1", "2", "3", "4", "7", "OR") or "repair" in str(family).lower()):
        repair_type = family
        family = ""
        
    rep_str = str(repair_type).strip().upper()
    if rep_str in ("4", "OR") or "OR" in (desc or "").upper():
        return "OR"
        
    d = (desc or "").upper().strip()
    
    if "NMG" in d: return "NMG"
    if "TW8W" in d or ("8W" in d and "TW" in d) or "DETC" in d: return "TW8W"
    if "TW4W" in d or ("4W" in d and "TW" in d) or d.startswith("TW") or d.startswith("RU"): return "TW4W"
    if "SPIC" in d: return "SPIC"
    if "ARMV" in d: return "ARMV"
    if any(k in d for k in ["ART", "SPART", "RH", "RHV", "RTRH", "MFD", "CAMPING", "RR", "WDS"]): return "ART"
    if any(k in d for k in ["DEMU TC", "DEMUTC", "DTC", "TSDTC", "TSNDTC"]) or d == "TC": return "DEMU TC"
    if any(k in d for k in ["DPC", "DHMU"]): return "DPC"
    if any(k in d for k in ["MEMU MC", "MEMUMC", "TSMC"]): return "MEMU MC"
    if any(k in d for k in ["MEMU TC", "MEMUTC", "TSTC"]): return "MEMU TC"
    if any(k in d for k in ["EMU MC", "EMUMC", "DMSC", "YZZS"]): return "EMU MC"
    if any(k in d for k in ["EMU TC", "EMUTC", "YSY", "YFSY", "YSD"]): return "EMU TC"
    if any(k in d for k in ["LWLRRM", "LSLRD", "LVPH"]): return "SLR"
    if "LWSCN" in d or "LSCN" in d: return "LWSCN"
    if "LWACCW" in d or ("2AC" in d and "LW" in d): return "LWACCW"
    if "LWACCN" in d or ("3AC" in d and "LW" in d) or "LWCBAC" in d or "LWFCWAC" in d: return "LWACCN"
    if "LWS" in d or "LS5" in d or "LS" in d: return "LWS"
    if any(k in d for k in ["CN", "WGSCN", "SCN", "GSN", "GSCN"]): return "CN"
    if any(k in d for k in ["CZ", "CZJ", "CZRJ", "SCZ", "SCZJ", "SCZRJ", "WGCZ", "WGCZRJ", "CC"]): return "CZ"
    if any(k in d for k in ["SLR", "GSLRD", "SLRD", "SRD"]): return "SLR"
    if any(k in d for k in ["GS", "WGACC", "WGC", "G"]): return "GS"
    return "GS"

import threading

_LIVE_DEMANDS_CACHE = {}
_LAST_CACHE_TIME = None
_DEMANDS_LOCK = threading.Lock()

def fetch_demands_from_supabase():
    """
    Fetch coaches directly from Supabase erp_active_coaches table.
    Used when running off-site, working from home, or in cloud deployment (Render).
    """
    import requests
    headers = {
        "apikey": config.SUPABASE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_KEY}"
    }
    demands = {}
    try:
        # Fetch current and surrounding years outturns
        for yr in ("2026", "2027", "2025"):
            url = f"{config.SUPABASE_URL}/erp_active_coaches?make=like.*{yr}*&select=*"
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                for c in r.json():
                    did = str(c.get("demandid") or c.get("coachno")).strip()
                    if did:
                        demands[did] = c

        # Fetch active coaches in shop / yard
        for url in [
            f"{config.SUPABASE_URL}/erp_active_coaches?pitnum=not.eq.&select=*",
            f"{config.SUPABASE_URL}/erp_active_coaches?status=in.(Work%20Area,In%20Yard,FND,Running,SHOP)&order=updated_at.desc&limit=500"
        ]:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                for c in r.json():
                    did = str(c.get("demandid") or c.get("coachno")).strip()
                    if did and did not in demands:
                        demands[did] = c
    except Exception as e:
        print(f"Warning: Failed to fetch demands from Supabase: {e}")

    formatted = {}
    for did, c in demands.items():
        cno = str(c.get("coachno") or "").strip()
        parts = (c.get("make") or "").split("||")
        tfr_date = parts[5] if len(parts) > 5 else ""
        corr_comp = parts[7] if len(parts) > 7 else ""
        desp_date = parts[8] if len(parts) > 8 else ""
        actualdespdate = parts[9] if len(parts) > 9 else ""

        formatted[did] = {
            "coachNo": cno, "coachno": cno,
            "coachDesc": c.get("coach_desc") or "", "coach_desc": c.get("coach_desc") or "",
            "demandId": did, "demandid": did,
            "pitNum": c.get("pitnum") or "", "pit_num": c.get("pitnum") or "",
            "receivedDate": c.get("recd_date") or "", "recd_date": c.get("recd_date") or "",
            "status": c.get("status") or "Running",
            "division": c.get("division") or "",
            "repairType": c.get("repair_type") or "1", "repair_type": c.get("repair_type") or "1",
            "tfr": tfr_date, "tfr_date": tfr_date,
            "corrComp": corr_comp, "corr_comp": corr_comp,
            "dispatchDate": desp_date, "desp_date": desp_date,
            "actualDispatchDate": actualdespdate, "actualdespdate": actualdespdate,
        }
    return formatted


def fetch_live_keycloak_demands(bypass_cache=False):
    """
    Direct live HTTP stream from Keycloak REST API when on local workshop intranet,
    or instant fallback to remote Supabase when off-site/cloud.
    """
    global _LIVE_DEMANDS_CACHE, _LAST_CACHE_TIME
    now = datetime.now()
    if not bypass_cache and _LIVE_DEMANDS_CACHE and _LAST_CACHE_TIME and (now - _LAST_CACHE_TIME).total_seconds() < 300:
        return _LIVE_DEMANDS_CACHE

    with _DEMANDS_LOCK:
        if not bypass_cache and _LIVE_DEMANDS_CACHE and _LAST_CACHE_TIME and (now - _LAST_CACHE_TIME).total_seconds() < 300:
            return _LIVE_DEMANDS_CACHE

        sess = get_session()
        if not sess:
            # Running off-site / in cloud: fetch from Supabase
            live_demands = fetch_demands_from_supabase()
            _LIVE_DEMANDS_CACHE = live_demands
            _LAST_CACHE_TIME = datetime.now()
            return live_demands

        api_base = config.COACH_ERP_API_BASE
        live_demands = {}
        max_did = 76700
        
        # 1. Fetch active open demands
        try:
            r = sess.get(f"{api_base}/locos/masters/coach-receipts", timeout=15)
            if r.status_code == 200:
                for it in r.json():
                    did = str(it.get("demandId") or "")
                    cno = str(it.get("coachNo") or "").strip()
                    if did and cno:
                        live_demands[did] = it
                        try:
                            max_did = max(max_did, int(did))
                        except:
                            pass
        except Exception as e:
            print(f"Warning: Live coach-receipts query error: {e}")

        # 2. Parallel scan of recent demands directly from Keycloak (covering full FY 2026-27 + new entries)
        demands_range = list(range(67000, max(max_did + 50, 77500)))
        to_query = [d for d in demands_range if str(d) not in live_demands]
        
        def _fetch_single(did):
            try:
                r = sess.get(f"{api_base}/locos/masters/coach-receipts/{did}", timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    if data and data.get("coachNo"):
                        return str(did), data
            except Exception:
                pass
            return str(did), None

        try:
            with ThreadPoolExecutor(max_workers=60) as ex:
                results = list(ex.map(_fetch_single, to_query))
            for did, data in results:
                if data:
                    live_demands[did] = data
        except Exception as e:
            print(f"Warning: Parallel demand fetch error: {e}")

        # If live scan returned nothing, fallback to Supabase
        if not live_demands:
            live_demands = fetch_demands_from_supabase()

        _LIVE_DEMANDS_CACHE = live_demands
        _LAST_CACHE_TIME = datetime.now()
        return live_demands

def get_type_wise_holding_report_data(month_name="September", year_val=2026, bypass_cache=False):
    """
    100% Direct Live ERP Engine with Strict Workshop Rules:
    1. Outturn: dispatchDate filled in month alone.
    2. Physical Despatch: For current month outturned coaches with actualDispatchDate filled.
    3. FND: Current month outturned coaches with actualDispatchDate empty.
    4. Previous Month FND: Separated.
    5. Active Holding: Only active Running stock (Strict exclusion of Return, Condemned, Scrap & past despatches).
    6. Corrosion Carry Forward: Coaches with corrosion completed BEFORE this month that were NOT outturned in previous months (available at hand for this month's target).
    """
    months_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    month_idx = months_map.get(str(month_name).lower(), 9)
    month_start = datetime(int(year_val), month_idx, 1)
    last_day = calendar.monthrange(int(year_val), month_idx)[1]
    month_end = datetime(int(year_val), month_idx, last_day, 23, 59, 59)
    
    target_categories_map = {
        cat: {
            "coach_type": cat,
            "target": STANDARD_TARGETS.get(cat, 0),
            "achieved": 0 if cat != "OR" else "-",
            "in_yard": 0,
            "in_yard_coaches": [],
            "under_attention": 0,
            "under_attention_coaches": [],
            "fnd": 0,
            "fnd_coaches": [],
            "physical_despatch": 0,
            "physical_despatch_coaches": [],
            "physical_despatch_dates": {},
            "prev_fnd": 0,
            "prev_fnd_coaches": [],
            "corrosion_completed": 0,
            "corrosion_completed_coaches": [],
            "corrosion_completed_dates": {},
            "corrosion_carry_forward": 0,
            "corrosion_carry_forward_coaches": [],
            "corrosion_carry_forward_dates": {}
        }
        for cat in STANDARD_WORKSHOP_CATEGORIES
    }

    # Load targets from Supabase if available
    try:
        from services.query_service import fetch_supabase_targets_for_month, map_targets_to_categories
        sb_targets = fetch_supabase_targets_for_month(month_name, year_val)
        if sb_targets:
            cat_targets = map_targets_to_categories(sb_targets)
            for cat, tgt_val in cat_targets.items():
                if cat in target_categories_map:
                    target_categories_map[cat]["target"] = tgt_val
    except Exception:
        pass

    live_demands = fetch_live_keycloak_demands(bypass_cache=bypass_cache)

    for did, item in live_demands.items():
        cno = str(item.get("coachNo") or item.get("coachno") or "").strip()
        if not cno:
            continue

        recd_dt = _parse_date_live(item.get("receivedDate") or item.get("recd_date"))
        tfr_dt = _parse_date_live(item.get("tfr") or item.get("tfr_date"))
        corr_dt = _parse_date_live(item.get("corrComp") or item.get("corr_comp"))
        desp_dt = _parse_date_live(item.get("dispatchDate") or item.get("desp_date"))
        act_desp_dt = _parse_date_live(item.get("actualDispatchDate") or item.get("actualdespdate"))
        pit_num = str(item.get("pitNum") or item.get("pit_num") or "").strip()
        status_str = str(item.get("status") or "").strip().upper()
        repair_type = str(item.get("repairType") or item.get("repair_type") or "1").strip()

        # Strict Return / Condemned / Scrap filter:
        is_return_condemn = any(x in status_str for x in ["RETURN", "CONDEMN", "SCRAP", "SURVEY", "TO BHOPAL"]) or cno in ["096617", "106620", "091047"]
        if is_return_condemn:
            # Outturns must never include return/condemn stock
            # Holding only includes if placed on active floor work pits
            if not (pit_num and pit_num.startswith(("AS/", "HCB/", "LCB/", "LBR/", "PS/", "DM/")) and not desp_dt):
                continue

        meta = fetch_coach_meta(cno)
        desc = meta.get("coachTypeDescription") or item.get("coachDesc") or item.get("coach_desc") or "GS"
        cat = map_coach_to_category(desc, repair_type=repair_type)
        if cat not in target_categories_map:
            cat = "GS"

        cat_data = target_categories_map[cat]

        # 1. Total Monthly Outturn (dispatchDate in current month - strictly for non-return stock)
        if desp_dt and month_start <= desp_dt <= month_end and not is_return_condemn:
            if act_desp_dt and act_desp_dt >= desp_dt:
                if cno not in cat_data["physical_despatch_coaches"]:
                    cat_data["physical_despatch"] += 1
                    cat_data["physical_despatch_coaches"].append(cno)
                    cat_data["physical_despatch_dates"][cno] = act_desp_dt.strftime("%d/%m/%Y")
            else:
                if cno not in cat_data["fnd_coaches"]:
                    cat_data["fnd"] += 1
                    cat_data["fnd_coaches"].append(cno)

        # 2. Previous Month FND Despatch (dispatchDate before month, actualDispatchDate in month)
        elif act_desp_dt and month_start <= act_desp_dt <= month_end:
            if desp_dt and desp_dt < month_start:
                if cno not in cat_data["prev_fnd_coaches"]:
                    cat_data["prev_fnd"] += 1
                    cat_data["prev_fnd_coaches"].append(cno)

        # 3. Active Workshop Holding (Available for Work / In Pits / In Yard)
        else:
            if recd_dt and recd_dt <= month_end:
                if not desp_dt or desp_dt > month_end:
                    is_in_shop = bool(pit_num and pit_num.startswith(("AS/", "HCB/", "LCB/", "LBR/", "PS/", "DM/")))
                    if is_in_shop:
                        if cno not in cat_data["under_attention_coaches"]:
                            cat_data["under_attention"] += 1
                            cat_data["under_attention_coaches"].append(cno)
                    else:
                        if cno not in cat_data["in_yard_coaches"]:
                            cat_data["in_yard"] += 1
                            cat_data["in_yard_coaches"].append(cno)

        # 4. Corrosion Section Performance:
        # A. Completed in month:
        if corr_dt and month_start <= corr_dt <= month_end:
            if cno not in cat_data["corrosion_completed_coaches"]:
                cat_data["corrosion_completed"] += 1
                cat_data["corrosion_completed_coaches"].append(cno)
                cat_data["corrosion_completed_dates"][cno] = corr_dt.strftime("%d/%m/%Y")
        # B. Carry Forward: Completed BEFORE this month, BUT coach was NOT outturned in previous months (available in hand!)
        elif corr_dt and corr_dt < month_start:
            if not desp_dt or desp_dt >= month_start:
                if cno not in cat_data["corrosion_carry_forward_coaches"]:
                    cat_data["corrosion_carry_forward"] += 1
                    cat_data["corrosion_carry_forward_coaches"].append(cno)
                    cat_data["corrosion_carry_forward_dates"][cno] = corr_dt.strftime("%d/%m/%Y")

    report_rows = []
    total_target = 0
    total_achieved = 0
    total_physical = 0
    total_fnd = 0
    total_prev_fnd = 0
    total_corr = 0
    total_cf = 0
    total_ua = 0
    total_yard = 0

    for cat in STANDARD_WORKSHOP_CATEGORIES:
        r = target_categories_map[cat]
        ach = r["physical_despatch"] + r["fnd"]
        r["achieved"] = ach if cat != "OR" else "-"
        report_rows.append(r)

        tgt = r["target"]
        if isinstance(tgt, int):
            total_target += tgt
        total_physical += r["physical_despatch"]
        total_fnd += r["fnd"]
        total_prev_fnd += r["prev_fnd"]
        total_achieved += ach
        total_corr += r["corrosion_completed"]
        total_cf += r["corrosion_carry_forward"]
        total_ua += r["under_attention"]
        total_yard += r["in_yard"]

    total_summary = {
        "coach_type": "Total",
        "target": total_target,
        "achieved": total_achieved,
        "physical_despatch": total_physical,
        "fnd": total_fnd,
        "prev_fnd": total_prev_fnd,
        "corrosion_completed": total_corr,
        "corrosion_carry_forward": total_cf,
        "under_attention": total_ua,
        "in_yard": total_yard
    }

    return {
        "month": month_name,
        "year": year_val,
        "data": report_rows,
        "total": total_summary
    }

def generate_type_wise_holding_excel(month_name, year_val):
    rep = get_type_wise_holding_report_data(month_name, year_val)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Type-Wise Holding & POH"
    
    # 1. Page Setup for Clean A4 Landscape Printing
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.horizontalCentered = True
    
    # Styles
    title_font = Font(name="Calibri", size=13, bold=True, color="1F497D")
    sub_font = Font(name="Calibri", size=9, italic=True, color="595959")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    total_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    total_font = Font(name="Calibri", size=10, bold=True, color="000000")
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    
    headers = [
        "S.No", "Coach Type", "Target", "Physical Despatch", "FND", "Total Outturn Achieved",
        "Corrosion Completed", "Corrosion Carry Forward", "Under Attention (Pits)", "In Yard", "Total Holding"
    ]
    num_cols = len(headers)
    last_col_letter = get_column_letter(num_cols)
    
    # Row 1: Merged Title
    ws.merge_cells(f"A1:{last_col_letter}1")
    ws["A1"] = f"CARRIAGE WORKSHOP, PERAMBUR — TYPE-WISE HOLDING & POH PERFORMANCE ({str(month_name).upper()} {year_val})"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24
    
    # Row 2: Merged Report Date & Subtitle
    ws.merge_cells(f"A2:{last_col_letter}2")
    ws["A2"] = f"Report Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}  |  Source: Carriage Workshop ERP Live System  |  Unit: Full Coaching Shells"
    ws["A2"].font = sub_font
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 18
    
    # Row 3: Headers
    for col_idx, h in enumerate(headers, 1):
        c = ws.cell(row=3, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[3].height = 28
    
    # Rows 4+: Data
    row_idx = 4
    for idx, r in enumerate(rep["data"], 1):
        phys = r["physical_despatch"]
        fnd = r["fnd"]
        ach = phys + fnd
        ua = r["under_attention"]
        yd = r["in_yard"]
        
        vals = [
            idx, r["coach_type"], r["target"], phys, fnd, ach if r["coach_type"] != "OR" else "-",
            r["corrosion_completed"], r["corrosion_carry_forward"], ua, yd, ua + yd
        ]
        for col_idx, v in enumerate(vals, 1):
            c = ws.cell(row=row_idx, column=col_idx, value=v)
            c.border = thin_border
            c.alignment = Alignment(horizontal="center" if col_idx != 2 else "left", vertical="center")
        ws.row_dimensions[row_idx].height = 19
        row_idx += 1
        
    # Total Row
    tot = rep["total"]
    tot_vals = [
        "", "Total", tot["target"], tot["physical_despatch"], tot["fnd"], tot["achieved"],
        tot["corrosion_completed"], tot["corrosion_carry_forward"], tot["under_attention"], tot["in_yard"],
        tot["under_attention"] + tot["in_yard"]
    ]
    for col_idx, v in enumerate(tot_vals, 1):
        c = ws.cell(row=row_idx, column=col_idx, value=v)
        c.fill = total_fill
        c.font = total_font
        c.border = thin_border
        c.alignment = Alignment(horizontal="center" if col_idx != 2 else "left", vertical="center")
    ws.row_dimensions[row_idx].height = 22
    
    # Auto-fit Column Widths (ignoring merged Rows 1 and 2 to avoid huge Column A)
    for col_idx in range(1, num_cols + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for r_i in range(3, row_idx + 1):
            val = str(ws.cell(row=r_i, column=col_idx).value or "")
            if len(val) > max_len:
                max_len = len(val)
        
        if col_idx == 1:
            ws.column_dimensions[col_letter].width = 6
        elif col_idx == 2:
            ws.column_dimensions[col_letter].width = max(max_len + 3, 13)
        else:
            ws.column_dimensions[col_letter].width = max(max_len + 3, 11)
        
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
