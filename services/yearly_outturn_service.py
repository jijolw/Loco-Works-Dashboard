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

def get_yearly_outturn_data(fy_str, bypass_cache=False):
    try:
        start_year = int(fy_str.split("-")[0])
        end_year = start_year + 1
    except:
        start_year = 2026
        end_year = 2027
        
    fy_months = [
        (4, start_year, "APR"), (5, start_year, "MAY"), (6, start_year, "JUN"),
        (7, start_year, "JUL"), (8, start_year, "AUG"), (9, start_year, "SEP"),
        (10, start_year, "OCT"), (11, start_year, "NOV"), (12, start_year, "DEC"),
        (1, end_year, "JAN"), (2, end_year, "FEB"), (3, end_year, "MAR")
    ]
    
    fy_start = pd.Timestamp(f"{start_year}-04-01")
    fy_end = pd.Timestamp(f"{end_year}-03-31")
    
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
    
    # Fetch details for candidate outturns
    candidates = []
    for rec in master:
        demandid = str(rec.get("demandid") or "").strip()
        is_candidate = False
        if demandid in cache_data:
            c = cache_data[demandid]
            desp_str = c.get("desp_date") or c.get("despdate") or ""
            desp_dt = _parse_date(desp_str)
            if desp_dt and fy_start <= desp_dt <= fy_end:
                is_candidate = True
                
        if not is_candidate:
            recd_str = rec.get("recd_date")
            recd_dt = _parse_date(recd_str)
            tfr_str = rec.get("tfr")
            tfr_dt = _parse_date(tfr_str)
            
            if recd_dt and recd_dt >= pd.Timestamp(f"{start_year - 1}-01-01"):
                is_candidate = True
            elif tfr_dt and (fy_start - pd.Timedelta(days=35)) <= tfr_dt <= (fy_end + pd.Timedelta(days=35)):
                is_candidate = True
            
        if is_candidate:
            candidates.append(rec)
            
    outturned_coaches = []
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
            
        # Filter out returned, condemned, or Bhopal coaches
        status_val = str(detail.get("status") or detail.get("pohstatus") or rec.get("status") or "").strip().upper()
        if status_val in ("RETURN", "COND", "BHOPAL", "161"):
            continue
            
        desp_str = detail.get("desp_date") or detail.get("despdate")
        desp_dt = _parse_date(desp_str)
            
        if desp_dt and fy_start <= desp_dt <= fy_end:
            coach_desc = str(rec.get("coach_desc") or rec.get("coachdesc") or "").strip().upper()
            family = decode_family(coach_desc)
            outturned_coaches.append({
                "coachno": rec.get("coachno"),
                "coach_desc": coach_desc,
                "family": family,
                "month": desp_dt.month,
                "year": desp_dt.year
            })

    # De-duplicate by coachno keeping the earliest outturn date in the fiscal year
    from datetime import datetime as dt_class
    unique_coaches = {}
    for c in outturned_coaches:
        cno = str(c["coachno"]).strip()
        if not cno:
            continue
        if cno not in unique_coaches:
            unique_coaches[cno] = c
        else:
            existing = unique_coaches[cno]
            existing_dt = dt_class(existing["year"], existing["month"], 1)
            current_dt = dt_class(c["year"], c["month"], 1)
            if current_dt < existing_dt:
                unique_coaches[cno] = c
                
    outturned_coaches = list(unique_coaches.values())

    # Exact codes defined in user template
    sections = {
        "NON AC COACH": ["CN", "GS", "CZ", "CZJ", "CZRJ", "GSLRD", "GSRD", "SLR", "VPU", "VPH", "ARMV", "ART CONV"],
        "LHB AC COACH": ["LWACCW", "LWACCN", "LWCBAC"],
        "LHB NON AC COACH": ["LWSCN", "LWS", "LSLRD", "LS5", "LVPH"],
        "NMG & NMGHS CONV": ["NMGHS", "NMGHSR CONV", "NMG"],  # Put NMGHS first so it matches before NMG
        "DEMU SHOP ": ["DEMU TC", "MEMU MC", "MEMU TC", "TW8W", "TW4W", "DPC", "SPIC", "EMU TC", "EMU MC", "SPART"]
    }
    
    # Initialize grid
    grid = {}
    for sect_name, codes in sections.items():
        grid[sect_name] = {}
        for c in codes:
            grid[sect_name][c] = [0] * 12 # 12 months

    # Populate grid counts
    for c in outturned_coaches:
        desc = c["coach_desc"]
        month = c["month"]
        year = c["year"]
        family = c["family"]
        
        # Find which index in fiscal year this matches
        month_idx = None
        for i, (m, y, _) in enumerate(fy_months):
            if m == month and y == year:
                month_idx = i
                break
                
        if month_idx is None:
            continue
            
        code = map_coach_desc_to_code(desc, family)
        if code:
            for sect_name, codes in sections.items():
                if code in codes:
                    grid[sect_name][code][month_idx] += 1
                    break
                
    return {
        "fy": fy_str,
        "months": [m[2] for m in fy_months],
        "grid": grid
    }

def generate_yearly_outturn_excel(fy_str):
    data = get_yearly_outturn_data(fy_str)
    grid = data["grid"]
    months = data["months"]
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = fy_str
    ws.views.sheetView[0].showGridLines = True
    
    # Styles
    font_title = Font(name="Calibri", size=15, bold=True, color="1B4F72")
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_section = Font(name="Calibri", size=10, bold=True, color="1B4F72")
    font_data = Font(name="Calibri", size=10, bold=False)
    font_bold = Font(name="Calibri", size=10, bold=True)
    fill_header = PatternFill(start_color="1F618D", end_color="1F618D", fill_type="solid")
    fill_section = PatternFill(start_color="EAEDED", end_color="EAEDED", fill_type="solid")
    fill_summary = PatternFill(start_color="D6EAF8", end_color="D6EAF8", fill_type="solid")
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin', color='BDC3C7'), right=Side(style='thin', color='BDC3C7'),
        top=Side(style='thin', color='BDC3C7'), bottom=Side(style='thin', color='BDC3C7')
    )
    
    ws["A1"] = f"COACH OUTTURN {fy_str}"
    ws["A1"].font = font_title
    ws.row_dimensions[1].height = 25
    
    headers = ["TRANSCODE"] + [f"{m} - {fy_str.split('-')[0][-2:]}" if i < 9 else f"{m} - {fy_str.split('-')[1]}" for i, m in enumerate(months)] + ["TOTAL"]
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
    ws.row_dimensions[2].height = 20
    
    curr_row = 3
    sect_rows = []
    for sect_name, codes in grid.items():
        sect_rows.append(curr_row)
        cell_sect = ws.cell(row=curr_row, column=1, value=sect_name)
        cell_sect.font = font_section
        cell_sect.fill = fill_section
        cell_sect.border = thin_border
        
        sect_start = curr_row + 1
        sect_end = curr_row + len(codes)
        
        for col_idx in range(2, 14):
            col_letter = get_column_letter(col_idx)
            cell_formula = ws.cell(row=curr_row, column=col_idx, value=f"=SUM({col_letter}{sect_start}:{col_letter}{sect_end})")
            cell_formula.font = font_bold
            cell_formula.fill = fill_section
            cell_formula.alignment = align_center
            cell_formula.border = thin_border
            
        cell_tot = ws.cell(row=curr_row, column=14, value=f"=SUM(B{curr_row}:M{curr_row})")
        cell_tot.font = font_bold
        cell_tot.fill = fill_section
        cell_tot.alignment = align_center
        cell_tot.border = thin_border
        ws.row_dimensions[curr_row].height = 18
        curr_row += 1
        
        for code, m_counts in codes.items():
            cell_code = ws.cell(row=curr_row, column=1, value=code)
            cell_code.font = font_bold
            cell_code.alignment = align_left
            cell_code.border = thin_border
            
            for m_idx, val in enumerate(m_counts):
                cell_val = ws.cell(row=curr_row, column=m_idx + 2, value=val if val > 0 else "")
                cell_val.font = font_data
                cell_val.alignment = align_center
                cell_val.border = thin_border
                
            cell_row_tot = ws.cell(row=curr_row, column=14, value=f"=SUM(B{curr_row}:M{curr_row})")
            cell_row_tot.font = font_bold
            cell_row_tot.alignment = align_center
            cell_row_tot.border = thin_border
            ws.row_dimensions[curr_row].height = 18
            curr_row += 1
            
    cell_gt = ws.cell(row=curr_row, column=1, value="GRAND TOTAL")
    cell_gt.font = font_bold
    cell_gt.fill = fill_summary
    cell_gt.border = thin_border
    
    for col_idx in range(2, 15):
        col_letter = get_column_letter(col_idx)
        sum_str = "+".join([f"{col_letter}{r}" for r in sect_rows])
        cell_gt_val = ws.cell(row=curr_row, column=col_idx, value=f"={sum_str}")
        cell_gt_val.font = font_bold
        cell_gt_val.fill = fill_summary
        cell_gt_val.alignment = align_center
        cell_gt_val.border = thin_border
    ws.row_dimensions[curr_row].height = 20

    ws.page_setup.paperSize = 9
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


# ==============================================================================
# REPORT 3: COACHES INSIDE SHOP REPORT
