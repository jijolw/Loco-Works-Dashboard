import os
import io
import json
import calendar
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from services.erp_service import fetch_master, fetch_single
from services.decoders import decode_family

CREDENTIALS_PATH = "D:\\JIJO\\information\\Coach Position\\credentials.json"
SHEET_KEY = "17_yzOhhdSy0EQAqLpfuXMPJazsgtlW7QspNvYJLI2Qk"

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

def _parse_date_local(dt_str):
    dt_str = str(dt_str).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            pass
    return None

def is_yard_location(p):
    if not p or not p.strip():
        return True
    p = p.strip().upper()
    if "CLI" in p:
        return False
    if p.startswith("OT/YD") or p.startswith("OT/IN") or p.startswith("OT/DESP") or "YD" in p or "IN" in p or "DESP" in p:
        return True
    return False

def get_report_category(code, family):
    if not code:
        return None
    code_upper = code.strip().upper()
    family_upper = family.strip().upper()
    
    if family_upper == "ICF":
        if code_upper == "CN": return "CN"
        if code_upper == "GS": return "GS"
        if code_upper in ("CZ", "CZJ", "CZRJ"): return "CZ"
        if code_upper in ("SLR", "GSLRD", "GSRD"): return "SLR"
        if code_upper in ("ARMV", "VPU", "VPH", "ART CONV", "ART"): return "ART"
    elif family_upper == "LHB":
        if code_upper == "LWSCN": return "LWSCN"
        if code_upper in ("LWS", "LS5", "LS"): return "LWS"
        if code_upper == "LWACCW": return "LWACCW"
        if code_upper in ("LWACCN", "LWCBAC"): return "LWACCN"
    elif family_upper == "EMU":
        if code_upper == "EMU MC": return "EMU MC"
        if code_upper == "EMU TC": return "EMU TC"
    elif family_upper == "MEMU":
        if code_upper == "MEMU MC": return "MEMU MC"
        if code_upper == "MEMU TC": return "MEMU TC"
    elif family_upper == "DEMU":
        if code_upper == "DPC": return "DPC"
        if code_upper == "DEMU TC": return "DEMU TC"
    elif family_upper == "TW":
        if code_upper == "TW4W": return "TW4W"
        if code_upper == "TW8W": return "TW8W"
    elif family_upper == "NMG":
        return "NMG"
    elif family_upper == "SPECIAL":
        if "EMU MC" in code_upper: return "EMU MC"
        if "EMU TC" in code_upper: return "EMU TC"
        if "MEMU MC" in code_upper: return "MEMU MC"
        if "MEMU TC" in code_upper: return "MEMU TC"
        if "DEMU TC" in code_upper: return "DEMU TC"
        if "DPC" in code_upper: return "DPC"
        return "ART"
    return None

def get_type_wise_holding_report_data(month_name, year_val):
    """
    Generate type-wise holdings in yard & attention, targets & achievements.
    Derived in real-time from the Google Sheet worksheets and Internal_Targets.
    """
    import gspread
    from google.oauth2.service_account import Credentials
    
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_KEY)
    
    months_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    month_idx = months_map.get(month_name.lower())
    if not month_idx:
        raise ValueError(f"Invalid month name: {month_name}")
    
    month_start = datetime(int(year_val), month_idx, 1)

    # Define predefined list of categories in the specified order
    ordered_cats = [
        "CN", "GS", "CZ", "SLR", "LWSCN", "LWS", "LWACCN", "LWACCW",
        "EMU MC", "EMU TC", "MEMU MC", "MEMU TC",
        "DPC", "DEMU TC", "TW4W", "TW8W", "NMG", "ART", "OR"
    ]
    
    target_categories_map = {
        cat: {
            "coach_type": cat,
            "target": 0 if cat != "OR" else "-",
            "achieved": 0 if cat != "OR" else "-",
            "in_yard": 0,
            "in_yard_coaches": [],
            "under_attention": 0,
            "under_attention_coaches": [],
            "fnd": 0,
            "fnd_coaches": [],
            "physical_despatch": 0,
            "physical_despatch_coaches": [],
            "prev_fnd": 0,
            "prev_fnd_coaches": [],
            "corrosion_completed": 0,
            "corrosion_completed_coaches": [],
            "corrosion_carry_forward": 0,
            "corrosion_carry_forward_coaches": []
        }
        for cat in ordered_cats
    }
    
    lookup_month = month_name[:3].upper() + " " + str(year_val)
    
    try:
        ws_int = sheet.worksheet("Internal_Targets")
        int_rows = ws_int.get_all_values()
        for r in int_rows[1:]:
            if len(r) >= 10:
                m_val = r[1].strip().upper()
                if m_val == lookup_month:
                    raw_cat = r[5].strip()
                    t_val = r[7].strip()
                    a_val = r[9].strip()
                    target_qty = int(t_val) if t_val.isdigit() else 0
                    achieved_qty = int(a_val) if a_val.isdigit() else 0
                    
                    # Target mapping
                    if raw_cat in target_categories_map:
                        target_categories_map[raw_cat]["target"] = target_qty
                        target_categories_map[raw_cat]["achieved"] = achieved_qty
                    elif raw_cat.upper() == "3-PHASE":
                        # Merged target goes to EMU MC
                        target_categories_map["EMU MC"]["target"] = target_qty
                        target_categories_map["EMU MC"]["achieved"] = achieved_qty
                    elif raw_cat.upper() == "DPC/DTC":
                        # Clubbed target goes to DPC
                        target_categories_map["DPC"]["target"] = target_qty
                        target_categories_map["DPC"]["achieved"] = achieved_qty
                    elif raw_cat.upper() == "LWS":
                        target_categories_map["LWS"]["target"] = target_qty
                        target_categories_map["LWS"]["achieved"] = achieved_qty
    except Exception as e:
        print(f"Error reading Internal_Targets worksheet: {e}")
        
    active_coaches = []
    active_details_map = {}
    target_categories = [target_categories_map[cat] for cat in ordered_cats]

    # A. Get active coaches from ERP (Excluding "Return" status)
    try:
        from services.live_service import get_live_data
        live_res = get_live_data()
        active_coaches = live_res.get("coaches", [])

        for coach in active_coaches:
            status_val = str(coach.get("status") or "").strip().upper()
            repair_type_val = str(coach.get("repair_type") or "").strip().upper()
            if status_val in ("RETURN", "161"):
                continue
                
            cno = coach.get("coachno") or ""
            desc = coach.get("coach_desc") or ""
            family = coach.get("family") or ""
            pitnum = coach.get("pitnum") or ""
            demandid = coach.get("demandid") or ""
            
            # Fetch detail via fetch_single to get the true database value
            # Fetch detail via fetch_single to get the true database value
            try:
                detail = fetch_single(demandid)
            except:
                detail = {}
            if detail:
                active_details_map[str(demandid).strip()] = detail
                desp_str = detail.get("desp_date") or detail.get("despdate") or ""
                if desp_str and _parse_date_local(desp_str):
                    continue

            mapped_code = map_coach_desc_to_code(desc, family) or desc
            cat = get_report_category(mapped_code, family)
            
            cats_to_increment = []
            if repair_type_val == "OR":
                cats_to_increment.append("OR")
            elif cat:
                cats_to_increment.append(cat)
            
            for c_cat in cats_to_increment:
                is_yard = is_yard_location(pitnum)
                for tc in target_categories:
                    if tc["coach_type"] == c_cat:
                        if is_yard:
                            tc["in_yard"] += 1
                            if cno and cno not in tc["in_yard_coaches"]:
                                tc["in_yard_coaches"].append(cno)
                        else:
                            tc["under_attention"] += 1
                            if cno and cno not in tc["under_attention_coaches"]:
                                tc["under_attention_coaches"].append(cno)
                        # Corrosion Completed check for active coaches
                        if detail:
                            corr_comp_str = detail.get("corr_comp") or ""
                            corr_dt = _parse_date_local(corr_comp_str)
                            if corr_dt:
                                if corr_dt.month == month_idx and corr_dt.year == int(year_val):
                                    tc["corrosion_completed"] += 1
                                    if cno and cno not in tc["corrosion_completed_coaches"]:
                                        tc["corrosion_completed_coaches"].append(cno)
                                elif corr_dt < month_start:
                                    tc["corrosion_carry_forward"] += 1
                                    if cno and cno not in tc["corrosion_carry_forward_coaches"]:
                                        tc["corrosion_carry_forward_coaches"].append(cno)
    except Exception as e:
        print("Error parsing active ERP coaches:", e)

    # B. Fetch outturned, FND, and Physical Despatch coaches from ERP
    try:
        # Load cache details
        cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "erp_coaches_cache.json")
        cache_data = {}
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                
        master = fetch_master()
        active_demandids = {str(c.get("demandid")).strip() for c in active_coaches if c.get("demandid")}
        
        for rec in master:
            demandid = rec.get("demandid")
            if not demandid: continue
            
            demandid_str = str(demandid).strip()
            if demandid_str in active_demandids:
                detail = active_details_map.get(demandid_str)
                if not detail or not (detail.get("desp_date") or detail.get("despdate")):
                    continue
            else:
                detail = cache_data.get(demandid_str)
                if not detail or not (detail.get("desp_date") or detail.get("despdate")) or not detail.get("actualdespdate"):
                    try:
                        detail = fetch_single(demandid)
                    except:
                        continue
            if not detail:
                continue
                    
            cno = rec.get("coachno")
            desc = rec.get("coach_desc") or ""
            family = decode_family(desc)
            
            mapped_code = map_coach_desc_to_code(desc, family) or desc
            cat = get_report_category(mapped_code, family)
            
            status_val = str(detail.get("status") or "").strip().upper()
            repair_type_val = str(detail.get("repair_type") or "").strip().upper()
            
            if status_val in ("RETURN", "161"):
                continue
                
            if not cat and repair_type_val != "OR":
                continue
                
            desp_str = detail.get("desp_date") or detail.get("despdate") or ""
            actual_desp_str = detail.get("actualdespdate") or ""
            
            desp_dt = _parse_date_local(desp_str)
            actual_desp_dt = _parse_date_local(actual_desp_str)
            
            last_day = calendar.monthrange(int(year_val), month_idx)[1]
            month_end = datetime(int(year_val), month_idx, last_day, 23, 59, 59)
            
            # Dynamic fiscal year start
            if month_idx in (1, 2, 3):
                fy_start = datetime(int(year_val) - 1, 4, 1)
            else:
                fy_start = datetime(int(year_val), 4, 1)
                
            # Previous month end for Last Month FND calculation
            if month_idx == 1:
                prev_month_idx = 12
                prev_year = int(year_val) - 1
            else:
                prev_month_idx = month_idx - 1
                prev_year = int(year_val)
            last_day_prev = calendar.monthrange(prev_year, prev_month_idx)[1]
            prev_month_end = datetime(prev_year, prev_month_idx, last_day_prev, 23, 59, 59)
            
            # FND: outturned in current month, and actual despatch empty or after current month-end
            is_fnd = (desp_dt and desp_dt.month == month_idx and desp_dt.year == int(year_val) and (not actual_desp_dt or actual_desp_dt > month_end))
            
            # Last Month FND: outturned in previous month(s) (within current FY), and still not physically despatched by current month-end
            is_prev_fnd = (desp_dt and fy_start <= desp_dt <= prev_month_end and (not actual_desp_dt or actual_desp_dt > month_end))
            
            # Physical Despatch: both outturn and actual despatch are in selected month
            is_outturn_july = (desp_dt and desp_dt.month == month_idx and desp_dt.year == int(year_val))
            is_desp_july = (actual_desp_dt and actual_desp_dt.month == month_idx and actual_desp_dt.year == int(year_val))
            is_phys_despatch = (is_outturn_july and is_desp_july)
            
            cats_to_increment = []
            if repair_type_val == "OR":
                cats_to_increment.append("OR")
            elif cat:
                cats_to_increment.append(cat)
                
            for c_cat in cats_to_increment:
                if is_fnd:
                    for tc in target_categories:
                        if tc["coach_type"] == c_cat:
                            if cno and cno not in tc["fnd_coaches"]:
                                tc["fnd_coaches"].append(cno)
                                tc["fnd"] += 1
                if is_prev_fnd:
                    for tc in target_categories:
                        if tc["coach_type"] == c_cat:
                            if cno and cno not in tc["prev_fnd_coaches"]:
                                tc["prev_fnd_coaches"].append(cno)
                                tc["prev_fnd"] += 1
                if is_phys_despatch:
                    for tc in target_categories:
                        if tc["coach_type"] == c_cat:
                            if cno and cno not in tc["physical_despatch_coaches"]:
                                tc["physical_despatch_coaches"].append(cno)
                                tc["physical_despatch"] += 1
                
                # Check corrosion completion date
                corr_comp_str = detail.get("corr_comp") or ""
                corr_dt = _parse_date_local(corr_comp_str)
                
                is_corr_completed = False
                is_corr_carry_forward = False
                if corr_dt and (is_fnd or is_phys_despatch):
                    if corr_dt.month == month_idx and corr_dt.year == int(year_val):
                        is_corr_completed = True
                    elif corr_dt < month_start:
                        is_corr_carry_forward = True
                        
                if is_corr_completed:
                    for tc in target_categories:
                        if tc["coach_type"] == c_cat:
                            tc["corrosion_completed"] += 1
                            if cno and cno not in tc["corrosion_completed_coaches"]:
                                tc["corrosion_completed_coaches"].append(cno)
                                
                if is_corr_carry_forward:
                    for tc in target_categories:
                        if tc["coach_type"] == c_cat:
                            tc["corrosion_carry_forward"] += 1
                            if cno and cno not in tc["corrosion_carry_forward_coaches"]:
                                tc["corrosion_carry_forward_coaches"].append(cno)
    except Exception as e:
        print("Error parsing ERP-only outturns and despatches:", e)

    # Sort all coach lists
    for tc in target_categories:
        tc["in_yard_coaches"] = sorted(list(set(tc["in_yard_coaches"])))
        tc["under_attention_coaches"] = sorted(list(set(tc["under_attention_coaches"])))
        tc["fnd_coaches"] = sorted(list(set(tc["fnd_coaches"])))
        tc["prev_fnd_coaches"] = sorted(list(set(tc["prev_fnd_coaches"])))
        tc["physical_despatch_coaches"] = sorted(list(set(tc["physical_despatch_coaches"])))
        tc["corrosion_completed_coaches"] = sorted(list(set(tc["corrosion_completed_coaches"])))
        tc["corrosion_carry_forward_coaches"] = sorted(list(set(tc["corrosion_carry_forward_coaches"])))

    return {
        "month": month_name,
        "year": year_val,
        "data": target_categories
    }

def generate_type_wise_holding_excel(month_name, year_val):
    """
    Generate styled openpyxl Excel file for type-wise holdings and POH.
    """
    report_data = get_type_wise_holding_report_data(month_name, year_val)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Type-Wise Holding & POH"
    ws.views.sheetView[0].showGridLines = True
    
    # Styles
    font_title = Font(name="Calibri", size=15, bold=True, color="1B4F72")
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
    
    # Title Block
    ws["A1"] = f"TYPE-WISE HOLDING & POH PERFORMANCE REPORT — {month_name.upper()} {year_val}"
    ws["A1"].font = font_title
    ws["A1"].alignment = align_center
    # Title Block
    ws["A1"] = f"TYPE-WISE HOLDING & POH PERFORMANCE REPORT — {month_name.upper()} {year_val}"
    ws["A1"].font = font_title
    ws["A1"].alignment = align_center
    ws.merge_cells("A1:I1")
    ws.row_dimensions[1].height = 25
    
    # Table Header
    headers = [
        "Coach Type", 
        "Target", 
        "Physical Despatch", 
        "FND", 
        "Holding in work area", 
        "Holding at Yard",
        "Last Month FND",
        "Corrosion Carry Forward",
        "Corrosion Completed"
    ]
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
    ws.row_dimensions[4].height = 20
    
    # Table Data
    curr_row = 5
    tot_yard = 0
    tot_att = 0
    tot_fnd = 0
    tot_phys = 0
    tot_target = 0
    tot_prev_fnd = 0
    tot_corr_carry = 0
    tot_corr = 0
    
    for r_data in report_data["data"]:
        # 1. Coach Type
        c_type = ws.cell(row=curr_row, column=1, value=r_data["coach_type"])
        c_type.alignment = align_left
        c_type.border = thin_border
        
        # 2. Target
        t_val = r_data["target"]
        c_target = ws.cell(row=curr_row, column=2, value=t_val)
        c_target.font = font_data
        c_target.alignment = align_center
        c_target.border = thin_border
        if isinstance(t_val, int):
            tot_target += t_val
        elif str(t_val).isdigit():
            tot_target += int(t_val)
            
        # 3. Physical Despatch
        c_phys = ws.cell(row=curr_row, column=3, value=r_data.get("physical_despatch", 0))
        c_phys.font = font_data
        c_phys.alignment = align_center
        c_phys.border = thin_border
        tot_phys += r_data.get("physical_despatch", 0)
        
        # 4. FND
        fnd_val = r_data.get("fnd", 0)
        c_fnd = ws.cell(row=curr_row, column=4, value=fnd_val)
        c_fnd.alignment = align_center
        c_fnd.border = thin_border
        tot_fnd += fnd_val
        
        # 5. Holding in work area (Shop)
        c_att = ws.cell(row=curr_row, column=5, value=r_data["under_attention"])
        c_att.font = font_data
        c_att.alignment = align_center
        c_att.border = thin_border
        tot_att += r_data["under_attention"]
        
        # 6. Holding at Yard (Yard)
        c_yard = ws.cell(row=curr_row, column=6, value=r_data["in_yard"])
        c_yard.font = font_data
        c_yard.alignment = align_center
        c_yard.border = thin_border
        tot_yard += r_data["in_yard"]
        
        # 7. Last Month FND
        c_prev = ws.cell(row=curr_row, column=7, value=r_data.get("prev_fnd", 0))
        c_prev.font = font_data
        c_prev.alignment = align_center
        c_prev.border = thin_border
        tot_prev_fnd += r_data.get("prev_fnd", 0)
        
        # 8. Corrosion Carry Forward
        carry_val = r_data.get("corrosion_carry_forward", 0)
        c_carry = ws.cell(row=curr_row, column=8, value=carry_val)
        c_carry.font = font_data
        c_carry.alignment = align_center
        c_carry.border = thin_border
        tot_corr_carry += carry_val
        
        # 9. Corrosion Completed
        corr_val = r_data.get("corrosion_completed", 0)
        c_corr = ws.cell(row=curr_row, column=9, value=corr_val)
        c_corr.font = font_data
        c_corr.alignment = align_center
        c_corr.border = thin_border
        tot_corr += corr_val
        
        # Apply conditional FND styling (make bold and 1 point larger: size 11)
        if isinstance(fnd_val, int) and fnd_val > 0:
            c_type.font = Font(name="Calibri", size=11, bold=True)
            c_fnd.font = Font(name="Calibri", size=11, bold=True)
        else:
            c_type.font = font_bold
            c_fnd.font = font_data
            
        ws.row_dimensions[curr_row].height = 18
        curr_row += 1
        
    # Total row
    ws.cell(row=curr_row, column=1, value="Total").font = font_bold
    ws.cell(row=curr_row, column=1).fill = fill_summary
    ws.cell(row=curr_row, column=1).border = thin_border
    ws.cell(row=curr_row, column=1).alignment = align_left
    
    # Target Total
    c_tot_target = ws.cell(row=curr_row, column=2, value=tot_target)
    c_tot_target.font = font_bold
    c_tot_target.fill = fill_summary
    c_tot_target.border = thin_border
    c_tot_target.alignment = align_center
    
    # Physical Despatch Total
    c_tot_phys = ws.cell(row=curr_row, column=3, value=tot_phys)
    c_tot_phys.font = font_bold
    c_tot_phys.fill = fill_summary
    c_tot_phys.border = thin_border
    c_tot_phys.alignment = align_center
    
    # FND Total
    c_tot_fnd = ws.cell(row=curr_row, column=4, value=tot_fnd)
    c_tot_fnd.font = font_bold
    c_tot_fnd.fill = fill_summary
    c_tot_fnd.border = thin_border
    c_tot_fnd.alignment = align_center
    
    # Attention (Shop) Total
    c_tot_att = ws.cell(row=curr_row, column=5, value=tot_att)
    c_tot_att.font = font_bold
    c_tot_att.fill = fill_summary
    c_tot_att.border = thin_border
    c_tot_att.alignment = align_center
    
    # Yard Total
    c_tot_yard = ws.cell(row=curr_row, column=6, value=tot_yard)
    c_tot_yard.font = font_bold
    c_tot_yard.fill = fill_summary
    c_tot_yard.border = thin_border
    c_tot_yard.alignment = align_center
    
    # Last Month FND Total
    c_tot_prev = ws.cell(row=curr_row, column=7, value=tot_prev_fnd)
    c_tot_prev.font = font_bold
    c_tot_prev.fill = fill_summary
    c_tot_prev.border = thin_border
    c_tot_prev.alignment = align_center
    
    # Corrosion Carry Forward Total
    c_tot_corr_carry = ws.cell(row=curr_row, column=8, value=tot_corr_carry)
    c_tot_corr_carry.font = font_bold
    c_tot_corr_carry.fill = fill_summary
    c_tot_corr_carry.border = thin_border
    c_tot_corr_carry.alignment = align_center
    
    # Corrosion Completed Total
    c_tot_corr = ws.cell(row=curr_row, column=9, value=tot_corr)
    c_tot_corr.font = font_bold
    c_tot_corr.fill = fill_summary
    c_tot_corr.border = thin_border
    c_tot_corr.alignment = align_center
    
    ws.row_dimensions[curr_row].height = 20
    
    # Auto-adjust column widths (ignoring title row to prevent over-stretching)
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col if cell.row > 1)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 15)
        
    # Set page orientation to Landscape and Fit to Page Width
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
        
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
