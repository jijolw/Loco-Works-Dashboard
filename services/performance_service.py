import os
import io
import json
import calendar
import pandas as pd
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from collections import Counter

# Centralized imports from ERP codebase
from services.erp_service import fetch_master, fetch_single, fetch_clean, _parse_date
from services.decoders import decode_family, decode_division, decode_repair

# Centralized Google Sheet config
CREDENTIALS_PATH = "D:\\JIJO\\information\\Coach Position\\credentials.json"
SHEET_KEY = "1xnJmZgqYODnJknNsas6J9k1f5NKp9h4x54nJp7AsOIY"


def map_coach_desc_to_code(desc, family):
    desc = str(desc).strip().upper()
    if family == "ICF":
        if "WGSCN" in desc or "SCN" in desc or "CN" in desc:
            return "CN"
        if "GSLRD" in desc or "GSLR" in desc:
            return "GSLRD"
        if "GSRD" in desc:
            return "GSRD"
        if "SLR" in desc:
            return "SLR"
        if "GS" in desc:
            return "GS"
        if "CZJ" in desc or "SCZJ" in desc:
            return "CZJ"
        if "CZRJ" in desc or "SCZRJ" in desc:
            return "CZRJ"
        if "CZ" in desc or "SCZ" in desc:
            return "CZ"
        if "VPU" in desc:
            return "VPU"
        if "VPH" in desc:
            return "VPH"
        if "ARMV" in desc:
            return "ARMV"
        if "ART" in desc:
            return "ART CONV"
    elif family == "LHB":
        if "LWACCW" in desc:
            return "LWACCW"
        if "LWACCN" in desc:
            return "LWACCN"
        if "LWCBAC" in desc:
            return "LWCBAC"
        if "LWSCN" in desc:
            return "LWSCN"
        if "LWS" in desc:
            return "LWS"
        if "LSLRD" in desc:
            return "LSLRD"
        if "LS5" in desc:
            return "LS5"
        if "LVPH" in desc:
            return "LVPH"
    elif family == "NMG":
        if "NMGHSR" in desc:
            return "NMGHSR CONV"
        if "NMGHS" in desc:
            return "NMGHS"
        if "NMG" in desc:
            return "NMG"
    elif family in ("DEMU", "MEMU", "EMU", "TW", "SPECIAL"):
        if "DEMUTC" in desc or "DEMU TC" in desc:
            return "DEMU TC"
        if "MEMUMC" in desc or "MEMU MC" in desc:
            return "MEMU MC"
        if "MEMUTC" in desc or "MEMU TC" in desc:
            return "MEMU TC"
        if "TW8W" in desc:
            return "TW8W"
        if "TW4W" in desc:
            return "TW4W"
        if "DPC" in desc:
            return "DPC"
        if "SPIC" in desc:
            return "SPIC"
        if "EMUTC" in desc or "EMU TC" in desc or "YSY" in desc or "YSD" in desc or "YFSY" in desc:
            return "EMU TC"
        if "EMUMC" in desc or "EMU MC" in desc or "DMSC" in desc or "YZZS" in desc:
            return "EMU MC"
        if "SPART" in desc:
            return "SPART"
        if desc == "TC":
            if family == "DEMU": return "DEMU TC"
            if family == "MEMU": return "MEMU TC"
            if family == "EMU": return "EMU TC"
    return None

def get_gsheet_outturns(month_name, year_val):
    import gspread
    from google.oauth2.service_account import Credentials
    from datetime import datetime
    
    TRACKER_SHEET_KEY = "1xnJmZgqYODnJknNsas6J9k1f5NKp9h4x54nJp7AsOIY"
    CREDENTIALS_PATH = "D:\\JIJO\\information\\Coach Position\\credentials.json"
    
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scope)
    client = gspread.authorize(creds)
    tracker = client.open_by_key(TRACKER_SHEET_KEY)
    
    outturns = []
    
    def _parse_date_local(dt_str):
        dt_str = str(dt_str).strip()
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                pass
        return None
        
    month_name_upper = str(month_name).upper()
    try:
        month_idx = {
            'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4, 'MAY': 5, 'JUNE': 6,
            'JULY': 7, 'AUGUST': 8, 'SEPTEMBER': 9, 'OCTOBER': 10, 'NOVEMBER': 11, 'DECEMBER': 12
        }[month_name_upper]
    except KeyError:
        month_idx = 6

    from services.erp_service import fetch_master, fetch_single
    try:
        master = fetch_master()
        master_map = {str(rec.get("coachno")).strip(): rec for rec in master if rec.get("coachno")}
    except Exception as me:
        print("Failed to fetch ERP master:", me)
        master_map = {}

    def get_details_for_coach(coachno):
        rec = master_map.get(coachno)
        if rec:
            demandid = rec.get("demandid")
            if demandid:
                try:
                    return fetch_single(demandid)
                except:
                    pass
        return {}

    # 1. ICF NAC
    try:
        ws_icf = tracker.worksheet("ICF NAC")
        rows_icf = ws_icf.get_all_values()
        for r in rows_icf[2:]:
            if len(r) > 12:
                coachno = r[1].strip().replace("'", "")
                code = r[2].strip()
                month_planned = r[4].strip().upper()
                desp_str = r[12].strip()
                desp_dt = _parse_date_local(desp_str)
                if month_planned == month_name_upper:
                    detail_raw = get_details_for_coach(coachno)
                    outturns.append({
                        "coachno": coachno,
                        "coach_desc": code,
                        "family": "ICF",
                        "division": r[3].strip() if len(r) > 3 else "",
                        "repair_type": "POH",
                        "desp_date": desp_dt.strftime("%d/%m/%Y") if desp_dt else desp_str,
                        "desp_dt_parsed": desp_dt,
                        "month_planned": month_planned,
                        "detail_raw": detail_raw
                    })
    except Exception as e:
        print("Error reading ICF NAC worksheet:", e)

    # 2. LHB
    try:
        ws_lhb = tracker.worksheet("LHB")
        rows_lhb = ws_lhb.get_all_values()
        for r in rows_lhb[1:]:
            if len(r) > 13:
                coachno = r[1].strip().replace("'", "")
                code = r[2].strip()
                month_planned = r[5].strip().upper()
                desp_str = r[13].strip()
                desp_dt = _parse_date_local(desp_str)
                if month_planned == month_name_upper:
                    detail_raw = get_details_for_coach(coachno)
                    outturns.append({
                        "coachno": coachno,
                        "coach_desc": code,
                        "family": "LHB",
                        "division": r[3].strip() if len(r) > 3 else "",
                        "repair_type": r[4].strip() if len(r) > 4 else "POH",
                        "desp_date": desp_dt.strftime("%d/%m/%Y") if desp_dt else desp_str,
                        "desp_dt_parsed": desp_dt,
                        "month_planned": month_planned,
                        "detail_raw": detail_raw
                    })
    except Exception as e:
        print("Error reading LHB worksheet:", e)

    # 3. MEMU/EMU TC
    try:
        ws_tc = tracker.worksheet("MEMU/EMU TC")
        rows_tc = ws_tc.get_all_values()
        for r in rows_tc[1:]:
            if len(r) > 12:
                coachno = r[1].strip().replace("'", "")
                code = r[2].strip()
                month_planned = r[3].strip().upper()
                desp_str = r[12].strip()
                desp_dt = _parse_date_local(desp_str)
                if month_planned == month_name_upper:
                    detail_raw = get_details_for_coach(coachno)
                    if "DEMU" in code.upper():
                        fam_decoded = "DEMU"
                    elif "MEMU" in code.upper():
                        fam_decoded = "MEMU"
                    elif "EMU" in code.upper():
                        fam_decoded = "EMU"
                    else:
                        fam_decoded = "MEMU"
                    outturns.append({
                        "coachno": coachno,
                        "coach_desc": code,
                        "family": fam_decoded,
                        "division": "",
                        "repair_type": "POH",
                        "desp_date": desp_dt.strftime("%d/%m/%Y") if desp_dt else desp_str,
                        "desp_dt_parsed": desp_dt,
                        "month_planned": month_planned,
                        "detail_raw": detail_raw
                    })
    except Exception as e:
        print("Error reading MEMU/EMU TC worksheet:", e)

    # 4. DEMU (includes DPC and Motor Cars)
    try:
        ws_demu = tracker.worksheet("DEMU")
        rows_demu = ws_demu.get_all_values()
        if len(rows_demu) > 0:
            headers = [h.strip().upper() for h in rows_demu[0]]
            coach_idx = headers.index("RS NO") if "RS NO" in headers else (headers.index("COACH NO") if "COACH NO" in headers else 3)
            month_idx = headers.index("MONTH") if "MONTH" in headers else (headers.index("MONTH PLANNED") if "MONTH PLANNED" in headers else 4)
            type_idx = headers.index("TYPE") if "TYPE" in headers else 1
            
            desp_col_idx = -1
            for idx, h in enumerate(headers):
                if h in ("DESP DATE", "DESPATCH DATE", "DESP_DATE", "DESPATCH_DATE", "ACTUAL DESPATCH DATE"):
                    desp_col_idx = idx
                    break
                    
            for r in rows_demu[1:]:
                if len(r) > max(coach_idx, month_idx, type_idx):
                    coachno = r[coach_idx].strip().replace("'", "")
                    month_planned = r[month_idx].strip().upper()
                    coach_type = r[type_idx].strip()
                    
                    if month_planned == month_name_upper:
                        detail_raw = get_details_for_coach(coachno)
                        
                        sheet_desp_str = ""
                        if desp_col_idx != -1 and len(r) > desp_col_idx:
                            sheet_desp_str = r[desp_col_idx].strip()
                            
                        if sheet_desp_str:
                            desp_str = sheet_desp_str
                        else:
                            desp_str = detail_raw.get("desp_date") or detail_raw.get("despdate") or ""
                            
                        desp_dt = _parse_date_local(desp_str)
                        if "DEMU" in coach_type.upper() or "DPC" in coach_type.upper():
                            fam_decoded = "DEMU"
                        elif "MEMU" in coach_type.upper():
                            fam_decoded = "MEMU"
                        elif "EMU" in coach_type.upper():
                            fam_decoded = "EMU"
                        else:
                            fam_decoded = "DEMU"
                        outturns.append({
                            "coachno": coachno,
                            "coach_desc": coach_type,
                            "family": fam_decoded,
                            "division": detail_raw.get("dvnid") or "",
                            "repair_type": "POH",
                            "desp_date": desp_dt.strftime("%d/%m/%Y") if desp_dt else desp_str,
                            "desp_dt_parsed": desp_dt,
                            "month_planned": month_planned,
                            "detail_raw": detail_raw
                        })
    except Exception as e:
        print("Error reading DEMU worksheet:", e)

    # 5. NMGHS CONV
    try:
        ws_nmg_conv = tracker.worksheet("NMGHS CONV")
        rows_nmg_conv = ws_nmg_conv.get_all_values()
        for r in rows_nmg_conv[2:]:
            if len(r) > 10:
                coachno = r[1].strip().replace("'", "")
                code = r[2].strip()
                month_planned = r[4].strip().upper()
                desp_str = r[10].strip()
                desp_dt = _parse_date_local(desp_str)
                if month_planned == month_name_upper:
                    detail_raw = get_details_for_coach(coachno)
                    outturns.append({
                        "coachno": coachno,
                        "coach_desc": code,
                        "family": "NMG",
                        "division": detail_raw.get("dvnid") or "",
                        "repair_type": "POH",
                        "desp_date": desp_dt.strftime("%d/%m/%Y") if desp_dt else desp_str,
                        "desp_dt_parsed": desp_dt,
                        "month_planned": month_planned,
                        "detail_raw": detail_raw
                    })
    except Exception as e:
        print("Error reading NMGHS CONV worksheet:", e)

    # 6. NMG POH
    try:
        ws_nmg_poh = tracker.worksheet("NMG POH")
        rows_nmg_poh = ws_nmg_poh.get_all_values()
        for r in rows_nmg_poh[2:]:
            if len(r) > 10:
                coachno = r[1].strip().replace("'", "")
                code = r[2].strip()
                month_planned = r[4].strip().upper()
                desp_str = r[10].strip()
                desp_dt = _parse_date_local(desp_str)
                if month_planned == month_name_upper:
                    detail_raw = get_details_for_coach(coachno)
                    outturns.append({
                        "coachno": coachno,
                        "coach_desc": code,
                        "family": "NMG",
                        "division": detail_raw.get("dvnid") or "",
                        "repair_type": "POH",
                        "desp_date": desp_dt.strftime("%d/%m/%Y") if desp_dt else desp_str,
                        "desp_dt_parsed": desp_dt,
                        "month_planned": month_planned,
                        "detail_raw": detail_raw
                    })
    except Exception as e:
        print("Error reading NMG POH worksheet:", e)
        
    return outturns

def get_performance_report_data(month_name, year_val, bypass_cache=False, report_type="target_achievement"):
    """
    Query target vs actuals data for a given month and year.
    """
    month_name = month_name.capitalize()
    year_val = int(year_val)
    
    # 1. Fetch Targets from old Google Sheet
    hq_targets = []
    int_targets = []
    
    if os.path.exists(CREDENTIALS_PATH):
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_key(SHEET_KEY)
            
            # HQ Targets
            ws_hq = sheet.worksheet("HQ_Targets")
            for r in ws_hq.get_all_values()[1:]:
                if len(r) >= 8:
                    fy = r[0].strip()
                    m_val = r[1].strip()
                    if m_val.lower() == month_name.lower():
                        hq_targets.append({
                            "stock_type": r[4].strip(),
                            "schedule": r[5].strip(),
                            "nac_ac": r[6].strip(),
                            "target": r[7].strip()
                        })
                        
            # Internal Targets
            ws_int = sheet.worksheet("Internal_Targets")
            for r in ws_int.get_all_values()[1:]:
                if len(r) >= 8:
                    fy = r[0].strip()
                    m_val = r[1].strip()
                    expected_m_val = month_name[:3].upper() + " " + str(year_val)
                    if m_val.upper() == expected_m_val:
                        int_targets.append({
                            "stock_type": r[3].strip(),
                            "schedule": r[4].strip(),
                            "sub_type": r[5].strip(),
                            "nac_ac": r[6].strip(),
                            "target": r[7].strip()
                        })
        except Exception as e:
            print("Google sheets query error:", e)

    # 2. Fetch Actual outturns from ERP
    try:
        month_idx = list(calendar.month_name).index(month_name)
    except ValueError:
        month_idx = 6 # fallback to June
        
    start_date = pd.Timestamp(f"{year_val}-{month_idx:02d}-01")
    end_date = start_date + pd.offsets.MonthEnd(0)
    
    # Load coach details cache file
    cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "erp_coaches_cache.json")
    cache_data = {}
    if os.path.exists(cache_file):
        try:
            import json
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except Exception as e:
            pass

    # Fetch live active coaches to filter out active ones from details queries
    active_demandids = set()
    try:
        from services.live_service import get_live_data
        live_res = get_live_data()
        active_demandids = {str(c.get("demandid")).strip() for c in live_res.get("coaches", []) if c.get("demandid")}
    except Exception as e:
        pass

    master = fetch_master()
    erp_outturns_raw = []
    
    # Check all records received since 2025-01-01 or transferred in candidate range
    candidates = []
    for rec in master:
        demandid = str(rec.get("demandid") or "").strip()
        is_candidate = False
        if demandid in cache_data:
            c = cache_data[demandid]
            desp_str = c.get("desp_date") or c.get("despdate") or ""
            desp_dt = _parse_date(desp_str)
            if desp_dt and start_date <= desp_dt <= end_date:
                is_candidate = True
                
        if not is_candidate:
            recd_str = rec.get("recd_date")
            recd_dt = _parse_date(recd_str)
            tfr_str = rec.get("tfr")
            tfr_dt = _parse_date(tfr_str)
            
            if recd_dt and recd_dt >= pd.Timestamp("2025-01-01"):
                is_candidate = True
            elif tfr_dt and (start_date - pd.Timedelta(days=35)) <= tfr_dt <= (end_date + pd.Timedelta(days=35)):
                is_candidate = True
            
        if is_candidate:
            candidates.append(rec)
            
    for rec in candidates:
        demandid = rec.get("demandid")
        if not demandid:
            continue
        demandid_str = str(demandid).strip()
        if demandid_str in active_demandids:
            continue
        try:
            if not bypass_cache and demandid_str in cache_data:
                c = cache_data[demandid_str]
                detail = {
                    "presurveyhrs": c.get("presurvey", ""),
                    "finalhrs": c.get("final", ""),
                    "last_poh": c.get("last_poh", ""),
                    "last_pohdate": c.get("last_pohdate", ""),
                    "tfrdate": c.get("tfr_date", ""),
                    "tfr_date": c.get("tfr_date", ""),
                    "corr_place": c.get("corr_place", ""),
                    "corr_comp": c.get("corr_comp", ""),
                    "despdate": c.get("desp_date", ""),
                    "desp_date": c.get("desp_date", ""),
                    "actualdespdate": c.get("actualdespdate", ""),
                    "pohdays": c.get("pohdays", ""),
                    "remarks": c.get("remarks", ""),
                    "corrosion": c.get("corrosion", ""),
                    "status": c.get("status", "")
                }
            else:
                detail = fetch_single(demandid, bypass_cache=bypass_cache)
        except:
            continue
            
        desp_str = detail.get("desp_date") or detail.get("despdate")
        desp_dt = _parse_date(desp_str)
        
        # Filter out returned, condemned, or Bhopal coaches
        status_val = str(detail.get("status") or detail.get("pohstatus") or rec.get("status") or "").strip().upper()
        if any(x in status_val for x in ["COND", "RETURN", "BHOPAL", "161"]):
            continue
            
        if desp_dt and start_date <= desp_dt <= end_date:
            coachno = rec.get("coachno")
            coach_desc = rec.get("coach_desc") or rec.get("coachdesc") or ""
            family = decode_family(coach_desc)
            division = decode_division(detail.get("dvnid") or rec.get("dvnid"))
            repair_type = decode_repair(detail.get("repairid") or detail.get("repair_type") or rec.get("repairid") or rec.get("repair_type"))
            
            erp_outturns_raw.append({
                "coachno": coachno,
                "coach_desc": coach_desc,
                "family": family,
                "division": division,
                "repair_type": repair_type,
                "desp_date": desp_dt.strftime("%d/%m/%Y"),
                "erp_desp_date": desp_dt.strftime("%d/%m/%Y"),
                "detail_raw": detail
            })
            
    try:
        gsheet_outturns = get_gsheet_outturns(month_name, year_val)
    except Exception as ge:
        print("Failed to fetch gsheet outturns:", ge)
        gsheet_outturns = []

    gsheet_map = {str(c["coachno"]).strip(): c for c in gsheet_outturns}
    
    # Classify using Google Sheet physical despatch dates
    actual_coaches = []
    fnd_coaches = []
    last_day = calendar.monthrange(int(year_val), month_idx)[1]
    
    for c in erp_outturns_raw:
        coachno = str(c["coachno"]).strip()
        gs_rec = gsheet_map.get(coachno)
        
        if gs_rec:
            phys_desp_str = gs_rec.get("desp_date") or ""
            phys_desp_dt = gs_rec.get("desp_dt_parsed")
            month_planned = gs_rec.get("month_planned") or month_name.upper()
            c["detail_raw"] = gs_rec.get("detail_raw") or c["detail_raw"]
        else:
            phys_desp_str = "Not in GSheet"
            phys_desp_dt = None
            month_planned = "ERP Outturn"
            
        # Fallback to ERP actualdespdate if not found or empty in Google Sheet
        if not phys_desp_dt:
            erp_act = c["detail_raw"].get("actualdespdate") or ""
            parsed_erp_act = _parse_date(erp_act)
            if parsed_erp_act:
                phys_desp_dt = parsed_erp_act
                phys_desp_str = erp_act
            
        c["desp_date"] = phys_desp_str
        c["desp_dt_parsed"] = phys_desp_dt
        c["month_planned"] = month_planned
        
        is_actual = False
        if phys_desp_dt and phys_desp_dt.year == int(year_val) and phys_desp_dt.month == month_idx and phys_desp_dt.day < last_day:
            is_actual = True
            
        if is_actual:
            actual_coaches.append(c)
        else:
            fnd_coaches.append(c)

    if report_type == "fnd_performance":
        outturns_to_return = actual_coaches
        fnd_to_return = fnd_coaches
    else:
        for c in erp_outturns_raw:
            c["desp_date"] = c.get("erp_desp_date") or c.get("desp_date")
        outturns_to_return = erp_outturns_raw
        fnd_to_return = []

    return {
        "hq_targets": hq_targets,
        "internal_targets": int_targets,
        "outturns": outturns_to_return,
        "fnd_outturns": fnd_to_return,
        "gsheet_outturns": erp_outturns_raw,
        "month": month_name,
        "year": year_val
    }

def generate_performance_excel(month_name, year_val, bypass_cache=False, report_type="target_achievement"):
    data = get_performance_report_data(month_name, year_val, bypass_cache=bypass_cache, report_type=report_type)
    
    # Get last day of the month
    import calendar
    try:
        month_idx = list(calendar.month_name).index(month_name.title())
    except ValueError:
        month_idx = 6
    last_day = calendar.monthrange(int(year_val), month_idx)[1]
    
    gsheet_outturns = data.get("gsheet_outturns") or []
    
    # Classify gsheet_outturns into physical actual despatches (top side) vs FND / Carry forward (bottom side)
    actual_coaches = []
    fnd_coaches = []
    
    if report_type == "fnd_performance":
        for c in gsheet_outturns:
            dt = c.get("desp_dt_parsed")
            if dt and dt.year == int(year_val) and dt.month == month_idx and dt.day < last_day:
                actual_coaches.append(c)
            else:
                fnd_coaches.append(c)
    else:
        actual_coaches = gsheet_outturns
        fnd_coaches = []
            
    outturns = actual_coaches
    outturn_date_header = "Actual Despatch Date" if report_type == "fnd_performance" else "Outturn Date"
    
    # Segregate outturns
    icf_coaches = [c for c in outturns if c["family"] == "ICF"]
    lhb_coaches = [c for c in outturns if c["family"] == "LHB"]
    demu_coaches = [c for c in outturns if c["family"] == "DEMU"]
    memu_coaches = [c for c in outturns if c["family"] == "MEMU"]
    emu_coaches = [c for c in outturns if c["family"] == "EMU"]
    
    icf_by_type = {"GS": [], "CN": [], "CZ": [], "SLR/GSLRD": []}
    for c in icf_coaches:
        code = map_coach_desc_to_code(c["coach_desc"], "ICF")
        if code in ("GS",):
            icf_by_type["GS"].append(c)
        elif code in ("CN",):
            icf_by_type["CN"].append(c)
        elif code in ("CZ", "CZJ", "CZRJ"):
            icf_by_type["CZ"].append(c)
        elif code in ("GSLRD", "GSRD", "SLR"):
            icf_by_type["SLR/GSLRD"].append(c)
        else:
            icf_by_type["GS"].append(c)
            
    # Separate LWS and LS5
    lhb_by_type = {"LWSCN": [], "LWS": [], "LWACCN": [], "LS5": []}
    for c in lhb_coaches:
        code = map_coach_desc_to_code(c["coach_desc"], "LHB")
        if code == "LWSCN":
            lhb_by_type["LWSCN"].append(c)
        elif code == "LWS":
            lhb_by_type["LWS"].append(c)
        elif code == "LWACCN":
            lhb_by_type["LWACCN"].append(c)
        elif code == "LS5":
            lhb_by_type["LS5"].append(c)
        else:
            if "SCN" in str(c["coach_desc"]).upper():
                lhb_by_type["LWSCN"].append(c)
            elif "AC" in str(c["coach_desc"]).upper():
                lhb_by_type["LWACCN"].append(c)
            elif "LWS" in str(c["coach_desc"]).upper():
                lhb_by_type["LWS"].append(c)
            else:
                lhb_by_type["LS5"].append(c)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # Styles
    font_title = Font(name="Calibri", size=15, bold=True, color="1B4F72")
    font_section = Font(name="Calibri", size=12, bold=True, color="1B4F72")
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=10, bold=False)
    font_bold = Font(name="Calibri", size=10, bold=True)
    fill_header = PatternFill(start_color="1F618D", end_color="1F618D", fill_type="solid")
    fill_summary = PatternFill(start_color="D6EAF8", end_color="D6EAF8", fill_type="solid")
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin', color='BDC3C7'), right=Side(style='thin', color='BDC3C7'),
        top=Side(style='thin', color='BDC3C7'), bottom=Side(style='thin', color='BDC3C7')
    )

    # 1. ICF PERFORMANCE SHEET
    ws_icf = wb.create_sheet(title="ICF Performance")
    ws_icf.views.sheetView[0].showGridLines = True
    
    ws_icf["A1"] = f"ICF TARGET & ACHIEVEMENT REPORT — {month_name.upper()} {year_val}"
    ws_icf["A1"].font = font_title
    ws_icf.row_dimensions[1].height = 25
    
    ws_icf["A3"] = "ICF Outturn Summary Table (Top Side)"
    ws_icf["A3"].font = font_section
    
    headers_sum = ["Coach Type", "Total Target", "Type wise target", "Achieved", "Status"]
    for col_idx, h in enumerate(headers_sum, 1):
        cell = ws_icf.cell(row=4, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
    ws_icf.row_dimensions[4].height = 20
    
    icf_summary_data = [
        ["GS", "—", 14, len(icf_by_type["GS"]), "Short by " + str(14 - len(icf_by_type["GS"])) if len(icf_by_type["GS"]) < 14 else "Met"],
        ["CN", "—", 9, len(icf_by_type["CN"]), "Short by " + str(9 - len(icf_by_type["CN"])) if len(icf_by_type["CN"]) < 9 else "Met"],
        ["CZ", "—", 3, len(icf_by_type["CZ"]), "Short by " + str(3 - len(icf_by_type["CZ"])) if len(icf_by_type["CZ"]) < 3 else "Met"],
        ["SLR/GSLRD", "—", 2, len(icf_by_type["SLR/GSLRD"]), "Met" if len(icf_by_type["SLR/GSLRD"]) >= 2 else "Short by " + str(2 - len(icf_by_type["SLR/GSLRD"]))],
        ["Total ICF POH", 28, 28, len(icf_coaches), "Short by " + str(28 - len(icf_coaches)) if len(icf_coaches) < 28 else "Met"]
    ]
    
    for row_idx, r_data in enumerate(icf_summary_data, 5):
        for col_idx, val in enumerate(r_data, 1):
            cell = ws_icf.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_bold if row_idx == 9 or col_idx == 1 else font_data
            cell.alignment = align_center if col_idx > 1 else align_left
            cell.border = thin_border
            if row_idx == 9:
                cell.fill = fill_summary
        ws_icf.row_dimensions[row_idx].height = 18

    curr_row = 11
    for t_name, list_coaches in icf_by_type.items():
        ws_icf.cell(row=curr_row, column=1, value=f"ICF Type Details: {t_name}").font = font_section
        curr_row += 1
        
        headers_det = ["S.No.", "Coach No", "Description", "Repair Type", "Man Hours", "Division", outturn_date_header]
        for col_idx, h in enumerate(headers_det, 1):
            cell = ws_icf.cell(row=curr_row, column=col_idx, value=h)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center
            cell.border = thin_border
        ws_icf.row_dimensions[curr_row].height = 20
        curr_row += 1
        
        if not list_coaches:
            for col_idx in range(1, 8):
                cell = ws_icf.cell(row=curr_row, column=col_idx, value="—")
                cell.font = font_data
                cell.alignment = align_center
                cell.border = thin_border
            ws_icf.row_dimensions[curr_row].height = 18
            curr_row += 2
        else:
            for s_idx, c in enumerate(list_coaches, 1):
                detail = c["detail_raw"]
                hrs = detail.get("finalhrs") or detail.get("presurveyhrs") or "—"
                row_vals = [s_idx, c["coachno"], c["coach_desc"], c["repair_type"], hrs, c["division"], c["desp_date"]]
                for col_idx, val in enumerate(row_vals, 1):
                    cell = ws_icf.cell(row=curr_row, column=col_idx, value=val)
                    cell.font = font_bold if col_idx == 2 else font_data
                    cell.alignment = align_center if col_idx in (1, 2, 4, 5, 7) else align_left
                    cell.border = thin_border
                ws_icf.row_dimensions[curr_row].height = 18
                curr_row += 1
            curr_row += 1
    # Append FND / Carry Forward ICF coaches at the bottom
    ws_icf.cell(row=curr_row, column=1, value="FND & Rolled Over Coaches (Not physically despatched in June)").font = font_section
    curr_row += 1
    
    headers_fnd = ["S.No.", "Coach No", "Description", "Repair Type", "Target Month", "Division", "Actual Despatch Date", "Status"]
    for col_idx, h in enumerate(headers_fnd, 1):
        cell = ws_icf.cell(row=curr_row, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
    ws_icf.row_dimensions[curr_row].height = 20
    curr_row += 1
    
    icf_fnd_list = [c for c in fnd_coaches if c["family"] == "ICF"]
    if not icf_fnd_list:
        for col_idx in range(1, 9):
            cell = ws_icf.cell(row=curr_row, column=col_idx, value="—")
            cell.font = font_data
            cell.alignment = align_center
            cell.border = thin_border
        ws_icf.row_dimensions[curr_row].height = 18
        curr_row += 2
    else:
        for s_idx, c in enumerate(icf_fnd_list, 1):
            desp_str = c["desp_date"] or "Active"
            status = "FND / Paper Outturn" if c["desp_date"] else "Active / Carry Forward"
            row_vals = [s_idx, c["coachno"], c["coach_desc"], c["repair_type"], c["month_planned"], c["division"], desp_str, status]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_icf.cell(row=curr_row, column=col_idx, value=val)
                cell.font = font_bold if col_idx == 2 else font_data
                cell.alignment = align_center if col_idx in (1, 2, 4, 5, 7, 8) else align_left
                cell.border = thin_border
                cell.fill = PatternFill(start_color="FDEDEC", end_color="FDEDEC", fill_type="solid")
            ws_icf.row_dimensions[curr_row].height = 18
            curr_row += 1
    curr_row += 1
            
    # Page setup to fit A4 Portrait
    ws_icf.page_setup.paperSize = 9
    ws_icf.page_setup.orientation = ws_icf.ORIENTATION_PORTRAIT
    for col in ws_icf.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_icf.column_dimensions[col_letter].width = max(max_len + 4, 14)

    # 2. LHB PERFORMANCE SHEET
    ws_lhb = wb.create_sheet(title="LHB Performance")
    ws_lhb.views.sheetView[0].showGridLines = True
    
    ws_lhb["A1"] = f"LHB TARGET & ACHIEVEMENT REPORT — {month_name.upper()} {year_val}"
    ws_lhb["A1"].font = font_title
    ws_lhb.row_dimensions[1].height = 25
    
    ws_lhb["A3"] = "LHB Outturn Summary Table (Top Side)"
    ws_lhb["A3"].font = font_section
    
    headers_sum_lhb = ["Coach Type", "Total target", "Type wise target", "Achieved", "Status"]
    for col_idx, h in enumerate(headers_sum_lhb, 1):
        cell = ws_lhb.cell(row=4, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
    ws_lhb.row_dimensions[4].height = 20
    
    lhb_summary_data = [
        ["LWSCN", "—", 8, len(lhb_by_type["LWSCN"]), "Short by " + str(8 - len(lhb_by_type["LWSCN"])) if len(lhb_by_type["LWSCN"]) < 8 else "Met"],
        ["LWS", "—", 3, len(lhb_by_type["LWS"]), "Short by " + str(3 - len(lhb_by_type["LWS"])) if len(lhb_by_type["LWS"]) < 3 else "Met"],
        ["LWACCN", "—", 5, len(lhb_by_type["LWACCN"]), "Short by " + str(5 - len(lhb_by_type["LWACCN"])) if len(lhb_by_type["LWACCN"]) < 5 else "Met"],
        ["LS5", "—", "—", len(lhb_by_type["LS5"]), "—"],
        ["Total LHB", 16, 16, len(lhb_coaches), "Short by " + str(16 - len(lhb_coaches)) if len(lhb_coaches) < 16 else "Met"]
    ]
    
    total_row_idx = 5 + len(lhb_summary_data) - 1
    for row_idx, r_data in enumerate(lhb_summary_data, 5):
        for col_idx, val in enumerate(r_data, 1):
            cell = ws_lhb.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_bold if row_idx == total_row_idx or col_idx == 1 else font_data
            cell.alignment = align_center if col_idx > 1 else align_left
            cell.border = thin_border
            if row_idx == total_row_idx:
                cell.fill = fill_summary
        ws_lhb.row_dimensions[row_idx].height = 18

    curr_row = total_row_idx + 2
    for t_name, list_coaches in lhb_by_type.items():
        ws_lhb.cell(row=curr_row, column=1, value=f"LHB Type Details: {t_name}").font = font_section
        curr_row += 1
        
        headers_det_lhb = ["S.No.", "Coach No", "Description", "Type of Repair", "Man Hours", "Division", outturn_date_header]
        for col_idx, h in enumerate(headers_det_lhb, 1):
            cell = ws_lhb.cell(row=curr_row, column=col_idx, value=h)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center
            cell.border = thin_border
        ws_lhb.row_dimensions[curr_row].height = 20
        curr_row += 1
        
        if not list_coaches:
            for col_idx in range(1, 8):
                cell = ws_lhb.cell(row=curr_row, column=col_idx, value="—")
                cell.font = font_data
                cell.alignment = align_center
                cell.border = thin_border
            ws_lhb.row_dimensions[curr_row].height = 18
            curr_row += 2
        else:
            for s_idx, c in enumerate(list_coaches, 1):
                detail = c["detail_raw"]
                hrs = detail.get("finalhrs") or detail.get("presurveyhrs") or "—"
                row_vals = [s_idx, c["coachno"], c["coach_desc"], c["repair_type"], hrs, c["division"], c["desp_date"]]
                for col_idx, val in enumerate(row_vals, 1):
                    cell = ws_lhb.cell(row=curr_row, column=col_idx, value=val)
                    cell.font = font_bold if col_idx == 2 else font_data
                    cell.alignment = align_center if col_idx in (1, 2, 4, 5, 7) else align_left
                    cell.border = thin_border
                ws_lhb.row_dimensions[curr_row].height = 18
                curr_row += 1
            curr_row += 1
    # Append FND / Carry Forward LHB coaches at the bottom
    ws_lhb.cell(row=curr_row, column=1, value="FND & Rolled Over Coaches (Not physically despatched in June)").font = font_section
    curr_row += 1
    
    headers_fnd = ["S.No.", "Coach No", "Description", "Repair Type", "Target Month", "Division", "Actual Despatch Date", "Status"]
    for col_idx, h in enumerate(headers_fnd, 1):
        cell = ws_lhb.cell(row=curr_row, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
    ws_lhb.row_dimensions[curr_row].height = 20
    curr_row += 1
    
    lhb_fnd_list = [c for c in fnd_coaches if c["family"] == "LHB"]
    if not lhb_fnd_list:
        for col_idx in range(1, 9):
            cell = ws_lhb.cell(row=curr_row, column=col_idx, value="—")
            cell.font = font_data
            cell.alignment = align_center
            cell.border = thin_border
        ws_lhb.row_dimensions[curr_row].height = 18
        curr_row += 2
    else:
        for s_idx, c in enumerate(lhb_fnd_list, 1):
            desp_str = c["desp_date"] or "Active"
            status = "FND / Paper Outturn" if c["desp_date"] else "Active / Carry Forward"
            row_vals = [s_idx, c["coachno"], c["coach_desc"], c["repair_type"], c["month_planned"], c["division"], desp_str, status]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_lhb.cell(row=curr_row, column=col_idx, value=val)
                cell.font = font_bold if col_idx == 2 else font_data
                cell.alignment = align_center if col_idx in (1, 2, 4, 5, 7, 8) else align_left
                cell.border = thin_border
                cell.fill = PatternFill(start_color="FDEDEC", end_color="FDEDEC", fill_type="solid")
            ws_lhb.row_dimensions[curr_row].height = 18
            curr_row += 1
    curr_row += 1
            
    # Page setup to fit A4 Portrait
    ws_lhb.page_setup.paperSize = 9
    ws_lhb.page_setup.orientation = ws_lhb.ORIENTATION_PORTRAIT
    for col in ws_lhb.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_lhb.column_dimensions[col_letter].width = max(max_len + 4, 14)

    # 3. OTHER STOCK Performance
    ws_other = wb.create_sheet(title="Other Stock Performance")
    ws_other.views.sheetView[0].showGridLines = True
    
    ws_other["A1"] = f"DEMU / MEMU / EMU / NMG TARGET & ACHIEVEMENT REPORT — {month_name.upper()} {year_val}"
    ws_other["A1"].font = font_title
    ws_other.row_dimensions[1].height = 25
    
    ws_other["A3"] = "DEMU / MEMU / EMU / NMG Summary Table"
    ws_other["A3"].font = font_section
    
    headers_sum_other = ["Stock Type", "HQ Target", "Type Wise target", "Achieved"]
    for col_idx, h in enumerate(headers_sum_other, 1):
        cell = ws_other.cell(row=4, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
    ws_other.row_dimensions[4].height = 20
    
    nmg_count = len([c for c in outturns if c["family"] == "NMG"])
    other_summary_data = [
        ["DEMU/DTC/TC", 5, 5, len(demu_coaches)],
        ["EMU/MEMU", 8, 8, len(memu_coaches) + len(emu_coaches)],
        ["NMGHS / NMG POH", 0, "—", nmg_count]
    ]
    
    for row_idx, r_data in enumerate(other_summary_data, 5):
        for col_idx, val in enumerate(r_data, 1):
            cell = ws_other.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_bold if col_idx == 1 else font_data
            cell.alignment = align_center if col_idx in (2, 3, 4) else align_left
            cell.border = thin_border
        ws_other.row_dimensions[row_idx].height = 18

    # Detail Table
    ws_other["A9"] = "DEMU / MEMU / EMU / NMG Detail Table"
    ws_other["A9"].font = font_section
    
    headers_other_det = ["S.No.", "Coach No", "Description (Sub-Type)", "Family", "Repair Type", "Man Hours", "Division", outturn_date_header]
    for col_idx, h in enumerate(headers_other_det, 1):
        cell = ws_other.cell(row=10, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
    ws_other.row_dimensions[10].height = 20
    
    curr_row = 11
    nmg_coaches = [c for c in outturns if c["family"] == "NMG"]
    other_list = nmg_coaches + demu_coaches + memu_coaches + emu_coaches
    
    for s_idx, c in enumerate(other_list, 1):
        detail = c["detail_raw"]
        hrs = detail.get("finalhrs") or detail.get("presurveyhrs") or "—"
        row_vals = [s_idx, c["coachno"], c["coach_desc"], c["family"], c["repair_type"], hrs, c["division"], c["desp_date"]]
        for col_idx, val in enumerate(row_vals, 1):
            cell = ws_other.cell(row=curr_row, column=col_idx, value=val)
            cell.font = font_bold if col_idx == 2 else font_data
            cell.alignment = align_center if col_idx in (1, 2, 4, 5, 6, 8) else align_left
            cell.border = thin_border
        ws_other.row_dimensions[curr_row].height = 18
        curr_row += 1
    # Append FND / Carry Forward Other Stock coaches at the bottom
    ws_other.cell(row=curr_row, column=1, value="FND & Rolled Over Coaches (Not physically despatched in June)").font = font_section
    curr_row += 1
    
    headers_fnd = ["S.No.", "Coach No", "Description", "Family", "Repair Type", "Target Month", "Division", "Actual Despatch Date", "Status"]
    for col_idx, h in enumerate(headers_fnd, 1):
        cell = ws_other.cell(row=curr_row, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
    ws_other.row_dimensions[curr_row].height = 20
    curr_row += 1
    
    other_fnd_list = [c for c in fnd_coaches if c["family"] not in ("ICF", "LHB")]
    if not other_fnd_list:
        for col_idx in range(1, 10):
            cell = ws_other.cell(row=curr_row, column=col_idx, value="—")
            cell.font = font_data
            cell.alignment = align_center
            cell.border = thin_border
        ws_other.row_dimensions[curr_row].height = 18
        curr_row += 2
    else:
        for s_idx, c in enumerate(other_fnd_list, 1):
            desp_str = c["desp_date"] or "Active"
            status = "FND / Paper Outturn" if c["desp_date"] else "Active / Carry Forward"
            row_vals = [s_idx, c["coachno"], c["coach_desc"], c["family"], c["repair_type"], c["month_planned"], c["division"], desp_str, status]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_other.cell(row=curr_row, column=col_idx, value=val)
                cell.font = font_bold if col_idx == 2 else font_data
                cell.alignment = align_center if col_idx in (1, 2, 4, 5, 6, 8, 9) else align_left
                cell.border = thin_border
                cell.fill = PatternFill(start_color="FDEDEC", end_color="FDEDEC", fill_type="solid")
            ws_other.row_dimensions[curr_row].height = 18
            curr_row += 1
    curr_row += 1

    # Page setup to fit A4 Landscape
    ws_other.page_setup.paperSize = 9
    ws_other.page_setup.orientation = ws_other.ORIENTATION_LANDSCAPE
    for col in ws_other.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_other.column_dimensions[col_letter].width = max(max_len + 4, 14)

    # 4. FND AND OUTTURN PERFORMANCE SHEET
    ws_fnd = wb.create_sheet(title="FND and Outturn Performance")
    ws_fnd.views.sheetView[0].showGridLines = True
    
    # Title
    ws_fnd["A1"] = f"FND & OUTTURN PERFORMANCE REPORT — {month_name.upper()} {year_val}"
    ws_fnd["A1"].font = font_title
    ws_fnd.row_dimensions[1].height = 25
    
    # Get last day of the month
    import calendar
    try:
        month_num = list(calendar.month_name).index(month_name.title())
    except ValueError:
        month_num = 6
    last_day = calendar.monthrange(int(year_val), month_num)[1]
    
    # Classify outturns (using Google Sheet data as source of truth for physical despatches)
    gsheet_outturns = data.get("gsheet_outturns") or []
    
    actual_desps = []
    fnd_outturns = []
    
    for c in gsheet_outturns:
        desp_dt = _parse_date(c["desp_date"])
        if desp_dt and desp_dt.day == last_day:
            fnd_outturns.append(c)
        else:
            actual_desps.append(c)
            
    # Count by family
    def count_by_family(coaches_list):
        counts = {"ICF": 0, "LHB": 0, "Other": 0}
        for c in coaches_list:
            fam = c["family"]
            if fam in ("ICF", "LHB"):
                counts[fam] += 1
            else:
                counts["Other"] += 1
        return counts
        
    actual_counts = count_by_family(actual_desps)
    fnd_counts = count_by_family(fnd_outturns)
    
    # Add Summary Table
    ws_fnd["A3"] = "FND & Outturn Performance Summary"
    ws_fnd["A3"].font = font_section
    
    fnd_headers = ["Outturn Category", "ICF Outturns", "LHB Outturns", "Other Stock (EMU/DEMU/MEMU)", "Grand Total"]
    for col_idx, h in enumerate(fnd_headers, 1):
        cell = ws_fnd.cell(row=4, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
    ws_fnd.row_dimensions[4].height = 20
    
    # Row 5: Actual Despatches
    row5 = [
        "Actual Despatches (Physical outturns before last day)",
        actual_counts["ICF"],
        actual_counts["LHB"],
        actual_counts["Other"],
        len(actual_desps)
    ]
    for col_idx, val in enumerate(row5, 1):
        cell = ws_fnd.cell(row=5, column=col_idx, value=val)
        cell.font = font_bold if col_idx == 1 or col_idx == 5 else font_data
        cell.alignment = align_center if col_idx > 1 else align_left
        cell.border = thin_border
    ws_fnd.row_dimensions[5].height = 18
    
    # Row 6: FND
    row6 = [
        "FND (Paper outturns on last day of month)",
        fnd_counts["ICF"],
        fnd_counts["LHB"],
        fnd_counts["Other"],
        len(fnd_outturns)
    ]
    for col_idx, val in enumerate(row6, 1):
        cell = ws_fnd.cell(row=6, column=col_idx, value=val)
        cell.font = font_bold if col_idx == 1 or col_idx == 5 else font_data
        cell.alignment = align_center if col_idx > 1 else align_left
        cell.border = thin_border
    ws_fnd.row_dimensions[6].height = 18
    
    # Row 7: Grand Total
    row7 = [
        "Total Outturn",
        actual_counts["ICF"] + fnd_counts["ICF"],
        actual_counts["LHB"] + fnd_counts["LHB"],
        actual_counts["Other"] + fnd_counts["Other"],
        len(gsheet_outturns)
    ]
    for col_idx, val in enumerate(row7, 1):
        cell = ws_fnd.cell(row=7, column=col_idx, value=val)
        cell.font = font_bold
        cell.fill = fill_summary
        cell.alignment = align_center if col_idx > 1 else align_left
        cell.border = thin_border
    ws_fnd.row_dimensions[7].height = 20
    
    # Add Detailed Table
    ws_fnd["A9"] = "Detailed Coach-wise Outturn Classification"
    ws_fnd["A9"].font = font_section
    
    det_headers = ["Sl No", "Coach No", "Type (Family)", "Coach Code", "Division", "Repair Type", "Despatch Date", "Classification"]
    for col_idx, h in enumerate(det_headers, 1):
        cell = ws_fnd.cell(row=10, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
    ws_fnd.row_dimensions[10].height = 20
    
    # Combine and sort coaches
    classified_coaches = []
    for c in actual_desps:
        classified_coaches.append((c, "Actual Despatch"))
    for c in fnd_outturns:
        classified_coaches.append((c, "FND (Paper Outturn)"))
        
    classified_coaches.sort(key=lambda x: _parse_date(x[0]["desp_date"]) or pd.Timestamp("1900-01-01"))
    
    curr_row = 11
    for s_idx, (c, cls) in enumerate(classified_coaches, 1):
        row_vals = [s_idx, c["coachno"], c["family"], c["coach_desc"], c["division"], c["repair_type"], c["desp_date"], cls]
        for col_idx, val in enumerate(row_vals, 1):
            cell = ws_fnd.cell(row=curr_row, column=col_idx, value=val)
            cell.font = font_bold if col_idx == 2 or col_idx == 8 else font_data
            if col_idx == 8:
                cell.fill = fill_summary if cls == "Actual Despatch" else PatternFill(start_color="FDEDEC", end_color="FDEDEC", fill_type="solid")
            cell.alignment = align_center if col_idx in (1, 2, 3, 4, 5, 6, 7, 8) else align_left
            cell.border = thin_border
        ws_fnd.row_dimensions[curr_row].height = 18
        curr_row += 1
        
    # Page setup to fit A4 Landscape
    ws_fnd.page_setup.paperSize = 9 # A4
    ws_fnd.page_setup.orientation = ws_fnd.ORIENTATION_LANDSCAPE
    for col in ws_fnd.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_fnd.column_dimensions[col_letter].width = max(max_len + 4, 14)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


# ==============================================================================
# REPORT 2: COACH CODE WISE YEARLY OUTTURN REPORT
# ==============================================================================
