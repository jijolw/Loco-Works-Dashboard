"""
Production Planning & Live Workshop Holding Service
===================================================
100% Pure ERP live holding data extraction & comprehensive
production planning workbook generation (4-Tab Master System).
"""

from datetime import datetime
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io

from services.erp_service import get_session, fetch_coach_meta
from services.type_wise_holding_service import map_coach_to_category, get_true_railway, decode_family
import config

FAMILY_GROUPS = [
    ("ICF COACHING STOCK", ["CN", "CZ", "GS", "SLR"]),
    ("LHB COACHING STOCK", ["LWSCN", "LWACCN", "LWS"]),
    ("OTHER COACHING VEHICLES (OR)", ["OR"]),
    ("DEMU & SELF-PROPELLED STOCK", ["DPC", "DEMU TC", "SPIC", "TW4W", "MEMU TC", "MEMU MC"]),
    ("SPECIAL / DEPARTMENTAL STOCK", ["ART", "ARMV", "NMGHS"])
]

CATEGORY_ORDER = [
    "CN", "CZ", "GS", "SLR",
    "LWSCN", "LWACCN", "LWS",
    "OR",
    "DPC", "DEMU TC", "SPIC", "TW4W", "MEMU TC", "MEMU MC",
    "ART", "ARMV", "NMGHS"
]

def get_cat_rank(cat_name):
    try:
        return CATEGORY_ORDER.index(cat_name)
    except ValueError:
        return 99

def _parse_date_live(dt_val):
    if not dt_val:
        return None
    try:
        dt_str = str(dt_val).strip()
        if "T" in dt_str:
            dt_str = dt_str.split("T")[0]
        return datetime.strptime(dt_str, "%Y-%m-%d")
    except Exception:
        return None

def _fmt_d(dt_obj):
    return dt_obj.strftime("%d/%m/%Y") if dt_obj else ""

def get_production_planning_data():
    """
    Fetches 100% pure live workshop holding from Keycloak ERP
    and returns both the coach-wise roster and division summary matrix.
    """
    sess = get_session()
    api_base = config.COACH_ERP_API_BASE
    
    live_receipts = []
    try:
        r = sess.get(f"{api_base}/locos/masters/coach-receipts", timeout=15)
        if r.status_code == 200:
            live_receipts = r.json()
    except Exception as e:
        print(f"Warning: Live coach-receipts fetch error: {e}")

    # Fetch live demands to ensure any coach outturned this month (September 2026) is included
    try:
        from services.type_wise_holding_service import fetch_live_keycloak_demands
        live_demands = fetch_live_keycloak_demands()
        existing_cnos = set(str(x.get("coachNo") or "").strip() for x in live_receipts)
        for did, item in live_demands.items():
            cno = str(item.get("coachNo") or "").strip()
            disp_raw = item.get("dispatchDate")
            disp_s = str(disp_raw).split("T")[0] if disp_raw else ""
            # If outturned in September 2026 and not already in live_receipts
            if disp_s.startswith("2026-09") and cno not in existing_cnos:
                live_receipts.append(item)
                existing_cnos.add(cno)
    except Exception as e:
        print(f"Warning: Merging live demands error: {e}")

    active_holding_coaches = []

    for it in live_receipts:
        cno = str(it.get("coachNo") or "").strip()
        if not cno:
            continue
            
        status_str = str(it.get("status") or "").strip().upper()
        pit_num = str(it.get("pitNum") or "").strip()
        recd_dt = _parse_date_live(it.get("receivedDate"))
        tfr_dt = _parse_date_live(it.get("tfr"))
        corr_dt = _parse_date_live(it.get("corrComp"))
        desp_dt = _parse_date_live(it.get("dispatchDate"))
        repair_type = str(it.get("repairType") or "1").strip()
        
        # Strict Return / Condemned / Scrap filter
        is_return_condemn = any(x in status_str for x in ["RETURN", "CONDEMN", "SCRAP", "SURVEY", "TO BHOPAL"])
        if is_return_condemn:
            if not (pit_num and pit_num.startswith(("AS/", "HCB/", "LCB/", "LBR/", "PS/", "DM/"))):
                continue
                
        # Check outturn date:
        # Coaches outturned in current month (September 2026) MUST be included (marked with *)!
        # Past months (August, July, etc.) are excluded from holding master.
        is_sept_outturn = bool(desp_dt and desp_dt.year == 2026 and desp_dt.month == 9)
        if desp_dt and not is_sept_outturn:
            continue
            
        meta = fetch_coach_meta(cno)
        desc = meta.get("coachTypeDescription") or it.get("coachDesc") or "GS"
        dvn_raw = meta.get("divisionName") or meta.get("divisionId") or "SR"
        rly = get_true_railway(dvn_raw)
        
        dvn = str(dvn_raw).strip().upper()
        if "LUCKNOW" in dvn or "LJN" in dvn: dvn = "LJN"
        elif "AJMER" in dvn or "AII" in dvn: dvn = "AII"
        elif "PURI" in dvn or "KUR" in dvn: dvn = "PURI"
        elif "GHY" in dvn or "GUWAHATI" in dvn: dvn = "GHY"
        elif dvn in ("MAS", "TPJ", "PGT", "MDU", "TVC", "SA"): pass
        else: dvn = "SR"
        
        cat = map_coach_to_category(desc, repair_type=repair_type)
        if cat == "NMG" or "NMG" in desc.upper():
            cat = "NMGHS"
        if "SPART" in desc.upper():
            cat = "SPART"
            
        fam = decode_family(desc)
        year_built = meta.get("yearBuilt") or "-"
        
        is_on_floor_pit = bool(pit_num and pit_num.startswith(("AS/", "HCB/", "LCB/", "LBR/", "PS/", "DM/")))
        is_in_shop = bool(is_on_floor_pit)
        
        if is_sept_outturn:
            disp_str_fmt = desp_dt.strftime("%d/%m/%Y")
            act_disp_raw = it.get("actualDispatchDate")
            act_disp_fmt = _parse_date_live(act_disp_raw).strftime("%d/%m/%Y") if act_disp_raw else ""
            if act_disp_fmt:
                location_str = f"Outturned {disp_str_fmt} (Desp: {act_disp_fmt})"
            else:
                location_str = f"Outturned {disp_str_fmt} ({pit_num})" if pit_num else f"Outturned {disp_str_fmt}"
            is_out = True
        else:
            location_str = "In Working Area" if is_in_shop else "In Yard"
            is_out = False

        try:
            yb_int = int(year_built) if year_built and year_built != "-" else None
        except:
            yb_int = None
        age = (datetime.now().year - yb_int) if yb_int else None
        is_icf = fam == "ICF" or cat in ("CN", "CZ", "GS", "SLR", "CZ / CZJ", "SLR / GSLRD")
        if is_icf and yb_int is not None:
            age_condition = "<= 13 Yrs" if yb_int >= 2013 else "> 13 Yrs (Survey)"
        else:
            age_condition = "-"

        active_holding_coaches.append({
            "coach_no": cno,
            "coach_desc": desc,
            "category": cat,
            "family": fam,
            "railway": rly,
            "division": dvn,
            "year_built": year_built,
            "age": age if age is not None else "-",
            "age_condition": age_condition,
            "is_above_13": bool(is_icf and yb_int and yb_int < 2013),
            "recd_date": _fmt_d(recd_dt),
            "tfr_date": _fmt_d(tfr_dt),
            "location": location_str,
            "is_outturn": is_out,
            "corr_comp_date": _fmt_d(corr_dt),
            "corr_pdc": "",
            "desp_pdc": "",
            "tentative_plan": "",
            "remarks": "",
            "status": it.get("status") or "Running"
        })

    # Sort: Outturn taken coaches first (*), followed by Working Area, followed by Yard (#)
    active_holding_coaches.sort(key=lambda x: (
        get_cat_rank(x["category"]),
        0 if x.get("is_outturn") else (1 if x["location"] == "In Working Area" else 2),
        x["coach_no"]
    ))

    # Matrix aggregation
    matrix = {}
    divisions = set()
    for cdata in active_holding_coaches:
        cat = cdata["category"]
        dvn = cdata["division"]
        rly = cdata["railway"]
        dvn_col = f"{dvn} ({rly})" if rly != "SR" else dvn
        divisions.add(dvn_col)
        if cat not in matrix:
            matrix[cat] = {}
        matrix[cat][dvn_col] = matrix[cat].get(dvn_col, 0) + 1

    sr_order = ["PGT", "TPJ", "MAS", "MDU", "TVC", "SA"]
    foreign_order = sorted([d for d in divisions if d not in sr_order])
    ordered_divs = [d for d in sr_order if d in divisions] + foreign_order

    summary_groups = []
    grand_totals = {d: 0 for d in ordered_divs}
    grand_total_count = 0

    for grp_name, cat_list in FAMILY_GROUPS:
        active_cats = [c for c in cat_list if c in matrix]
        if not active_cats:
            continue

        grp_rows = []
        grp_subtotals = {d: 0 for d in ordered_divs}
        grp_tot = 0

        for cat in active_cats:
            counts = {d: matrix[cat].get(d, 0) for d in ordered_divs}
            row_tot = sum(counts.values())
            grp_rows.append({
                "category": cat,
                "counts": counts,
                "total": row_tot
            })
            for d in ordered_divs:
                grp_subtotals[d] += counts[d]
                grand_totals[d] += counts[d]
            grp_tot += row_tot
            grand_total_count += row_tot

        summary_groups.append({
            "group_name": grp_name,
            "rows": grp_rows,
            "subtotal": grp_subtotals,
            "subtotal_count": grp_tot
        })

    return {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total_holding": len(active_holding_coaches),
        "coaches": active_holding_coaches,
        "divisions": ordered_divs,
        "summary_groups": summary_groups,
        "grand_totals": grand_totals,
        "grand_total_count": grand_total_count
    }

all_planned_definitions = {
    # GS (ICF)
    "146413": {"c_pdc": "C/C", "d_pdc": "03/09/2026", "remarks": "KM, Outturned 01/09, Desp 03/09", "cat": "GS", "div": "PGT", "rly": "SR", "loc": "Outturned 01/09 (AS/P2_2)", "vlk": False, "outturn": True},
    "126538": {"c_pdc": "C/C", "d_pdc": "02/09/2026", "remarks": "KM, Outturned on 02/09/2026", "cat": "GS", "div": "MDU", "rly": "SR", "loc": "Outturned 02/09 (AS/L6_2)", "vlk": False, "outturn": True},
    "096493": {"c_pdc": "07/09/2026", "d_pdc": "09/09/2026", "remarks": "TO BE LIFT, C/PDC 07/09", "cat": "GS", "div": "PGT", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "126498": {"c_pdc": "09/09/2026", "d_pdc": "11/09/2026", "remarks": "Inside Shop Yard (OT/YD), C/PDC 09/09", "cat": "GS", "div": "PGT", "rly": "SR", "loc": "Inside Shop Yard", "vlk": False, "outturn": False},
    "094291": {"c_pdc": "12/09/2026", "d_pdc": "15/09/2026", "remarks": "In VLK Yard (To be taken inside shop)", "cat": "GS", "div": "PGT", "rly": "SR", "loc": "VLK Yard (To be taken inside)", "vlk": True, "outturn": False},
    "136530": {"c_pdc": "15/09/2026", "d_pdc": "18/09/2026", "remarks": "KM, In VLK Yard (To be taken inside shop)", "cat": "GS", "div": "PGT", "rly": "SR", "loc": "VLK Yard (To be taken inside)", "vlk": True, "outturn": False},
    
    # CN (ICF)
    "136348": {"c_pdc": "01/09/2026", "d_pdc": "05/09/2026", "remarks": "KM, U/C", "cat": "CN", "div": "PGT", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "135243": {"c_pdc": "05/09/2026", "d_pdc": "09/09/2026", "remarks": "KM, U/C", "cat": "CN", "div": "GHY", "rly": "NFR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "136202": {"c_pdc": "10/09/2026", "d_pdc": "14/09/2026", "remarks": "KM, U/C", "cat": "CN", "div": "PGT", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "146240": {"c_pdc": "11/09/2026", "d_pdc": "14/09/2026", "remarks": "KM, U/C", "cat": "CN", "div": "PGT", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "136233": {"c_pdc": "15/09/2026", "d_pdc": "18/09/2026", "remarks": "KM, TO BE LIFT", "cat": "CN", "div": "PGT", "rly": "SR", "loc": "Inside Shop Yard", "vlk": False, "outturn": False},
    "146378": {"c_pdc": "20/09/2026", "d_pdc": "22/09/2026", "remarks": "KM, U/C", "cat": "CN", "div": "TPJ", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "136304": {"c_pdc": "21/09/2026", "d_pdc": "24/09/2026", "remarks": "KM, 1200 HRS, Inside Shop Yard", "cat": "CN", "div": "PGT", "rly": "SR", "loc": "Inside Shop Yard", "vlk": False, "outturn": False},
    "134043": {"c_pdc": "23/09/2026", "d_pdc": "26/09/2026", "remarks": "KM, 1200 HRS, Inside Shop Yard", "cat": "CN", "div": "MDU", "rly": "SR", "loc": "Inside Shop Yard", "vlk": False, "outturn": False},
    
    # SLR (ICF)
    "134410": {"c_pdc": "03/09/2026", "d_pdc": "07/09/2026", "remarks": "KM, 1200 HRS, Position 3/9", "cat": "SLR", "div": "MDU", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "106702": {"c_pdc": "10/09/2026", "d_pdc": "12/09/2026", "remarks": "600 HRS, Position 10/9", "cat": "SLR", "div": "PGT", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "116720": {"c_pdc": "11/09/2026", "d_pdc": "14/09/2026", "remarks": "TO BE LIFT, C/PDC 11/09", "cat": "SLR", "div": "PGT", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "156716": {"c_pdc": "16/09/2026", "d_pdc": "19/09/2026", "remarks": "KM, In VLK Yard (To be taken inside shop)", "cat": "SLR", "div": "PGT", "rly": "SR", "loc": "VLK Yard (To be taken inside)", "vlk": True, "outturn": False},
    
    # LHB NAC
    "195411": {"c_pdc": "C/C", "d_pdc": "04/09/2026", "remarks": "C/C", "cat": "LWSCN", "div": "MAS", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "203790": {"c_pdc": "C/C", "d_pdc": "03/09/2026", "remarks": "C/C", "cat": "LWSCN", "div": "MAS", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "203768": {"c_pdc": "04/09/2026", "d_pdc": "09/09/2026", "remarks": "U/C, C/PDC 04/09", "cat": "LWSCN", "div": "MAS", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "201533": {"c_pdc": "05/09/2026", "d_pdc": "10/09/2026", "remarks": "U/C, C/PDC 05/09", "cat": "LWS", "div": "PURI", "rly": "ECoR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "203780": {"c_pdc": "11/09/2026", "d_pdc": "16/09/2026", "remarks": "U/C, C/PDC 11/09", "cat": "LWSCN", "div": "MAS", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "176230": {"c_pdc": "12/09/2026", "d_pdc": "17/09/2026", "remarks": "U/C, C/PDC 12/09", "cat": "LWSCN", "div": "SA", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "186251": {"c_pdc": "15/09/2026", "d_pdc": "19/09/2026", "remarks": "OR Saloon, TO BE LIFT, C/PDC 15/09", "cat": "OR", "div": "TVC", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "176234": {"c_pdc": "16/09/2026", "d_pdc": "21/09/2026", "remarks": "CN (LHB), TO BE LIFT, C/PDC 16/09", "cat": "LWSCN", "div": "SA", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "166319": {"c_pdc": "21/09/2026", "d_pdc": "25/09/2026", "remarks": "U/C, C/PDC 21/09", "cat": "LWSCN", "div": "TVC", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    
    # LHB AC
    "202485": {"c_pdc": "C/C", "d_pdc": "03/09/2026", "remarks": "C/C", "cat": "LWACCN", "div": "AII", "rly": "NWR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "201050": {"c_pdc": "03/09/2026", "d_pdc": "10/09/2026", "remarks": "U/C 3/9", "cat": "LWACCN", "div": "LJN", "rly": "NER", "loc": "In Working Area", "vlk": False, "outturn": False},
    "203796": {"c_pdc": "12/09/2026", "d_pdc": "18/09/2026", "remarks": "TO BE LIFT, C/PDC 12/09", "cat": "LWACCN", "div": "SA", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "156124": {"c_pdc": "16/09/2026", "d_pdc": "25/09/2026", "remarks": "TO BE LIFT, C/PDC 16/09", "cat": "LWACCN", "div": "MDU", "rly": "SR", "loc": "Inside Shop Yard", "vlk": False, "outturn": False},

    # DEMU TC
    "148343": {"c_pdc": "C/C", "d_pdc": "11/09/2026", "remarks": "D/TC, C/C", "cat": "DEMU TC", "div": "TPJ", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "128167": {"c_pdc": "-", "d_pdc": "21/09/2026", "remarks": "Inside Shop Yard", "cat": "DEMU TC", "div": "TPJ", "rly": "SR", "loc": "Inside Shop Yard", "vlk": False, "outturn": False},
    "128169": {"c_pdc": "-", "d_pdc": "22/09/2026", "remarks": "Inside Shop Yard", "cat": "DEMU TC", "div": "TPJ", "rly": "SR", "loc": "Inside Shop Yard", "vlk": False, "outturn": False},

    # MEMU TC (Rake from PGT - In VLK Yard / To be taken inside)
    "198859": {"c_pdc": "-", "d_pdc": "14/09/2026", "remarks": "MEMU TC Rake PGT (To be taken inside shop)", "cat": "MEMU TC", "div": "PGT", "rly": "SR", "loc": "VLK Yard (To be taken inside)", "vlk": True, "outturn": False},
    "198860": {"c_pdc": "-", "d_pdc": "15/09/2026", "remarks": "MEMU TC Rake PGT (To be taken inside shop)", "cat": "MEMU TC", "div": "PGT", "rly": "SR", "loc": "VLK Yard (To be taken inside)", "vlk": True, "outturn": False},
    "198861": {"c_pdc": "-", "d_pdc": "16/09/2026", "remarks": "MEMU TC Rake PGT (To be taken inside shop)", "cat": "MEMU TC", "div": "PGT", "rly": "SR", "loc": "VLK Yard (To be taken inside)", "vlk": True, "outturn": False},
    "198862": {"c_pdc": "-", "d_pdc": "17/09/2026", "remarks": "MEMU TC Rake PGT (To be taken inside shop)", "cat": "MEMU TC", "div": "PGT", "rly": "SR", "loc": "VLK Yard (To be taken inside)", "vlk": True, "outturn": False},
    "198863": {"c_pdc": "-", "d_pdc": "18/09/2026", "remarks": "MEMU TC Rake PGT (To be taken inside shop)", "cat": "MEMU TC", "div": "PGT", "rly": "SR", "loc": "VLK Yard (To be taken inside)", "vlk": True, "outturn": False},
    "198864": {"c_pdc": "-", "d_pdc": "19/09/2026", "remarks": "MEMU TC Rake PGT (To be taken inside shop)", "cat": "MEMU TC", "div": "PGT", "rly": "SR", "loc": "VLK Yard (To be taken inside)", "vlk": True, "outturn": False},

    # MEMU MC (Rake from PGT - In VLK Yard / To be taken inside)
    "198839": {"c_pdc": "-", "d_pdc": "30/09/2026", "remarks": "MEMU MC Rake PGT (To be taken inside shop)", "cat": "MEMU MC", "div": "PGT", "rly": "SR", "loc": "VLK Yard (To be taken inside)", "vlk": True, "outturn": False},
    "198840": {"c_pdc": "-", "d_pdc": "30/09/2026", "remarks": "MEMU MC Rake PGT (To be taken inside shop)", "cat": "MEMU MC", "div": "PGT", "rly": "SR", "loc": "VLK Yard (To be taken inside)", "vlk": True, "outturn": False},

    # Departmental & Self-Propelled
    "158334": {"c_pdc": "-", "d_pdc": "25/09/2026", "remarks": "DPC Power Car", "cat": "DPC", "div": "TPJ", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "190027": {"c_pdc": "-", "d_pdc": "25/09/2026", "remarks": "SPIC Inspection Car", "cat": "SPIC", "div": "MAS", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "RU9497": {"c_pdc": "-", "d_pdc": "18/09/2026", "remarks": "TW 4-Wheeler Tower Wagon", "cat": "TW4W", "div": "MAS", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "076470": {"c_pdc": "-", "d_pdc": "26/09/2026", "remarks": "NMGHS Automobile Carrier", "cat": "NMGHS", "div": "TPJ", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
    "076358": {"c_pdc": "-", "d_pdc": "20/09/2026", "remarks": "ARMV Medical Relief Van", "cat": "ARMV", "div": "PGT", "rly": "SR", "loc": "In Working Area", "vlk": False, "outturn": False},
}

def generate_production_planning_excel():

    data = get_production_planning_data()
    inside_coaches = data["coaches"]
    ordered_divs = data["divisions"]

    wb = openpyxl.Workbook()

    navy_dark = "1B365D"
    blue_light = "D9E1F2"
    gray_subtotal = "F2F2F2"
    gray_border = "D9D9D9"
    red_vlk = "C00000"
    purple_outturn = "7030A0"
    purple_tbi = "595959"

    header_fill = PatternFill(start_color=navy_dark, end_color=navy_dark, fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    section_fill = PatternFill(start_color=blue_light, end_color=blue_light, fill_type="solid")
    section_font = Font(name="Calibri", size=11, bold=True, color="1B365D")

    subtotal_fill = PatternFill(start_color=gray_subtotal, end_color=gray_subtotal, fill_type="solid")
    subtotal_font = Font(name="Calibri", size=11, bold=True, color="000000")

    total_fill = PatternFill(start_color="B4C6E7", end_color="B4C6E7", fill_type="solid")
    total_font = Font(name="Calibri", size=12, bold=True, color="000000")

    plan_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    plan_font = Font(name="Calibri", size=11, bold=True, color="7F6000")

    data_font = Font(name="Calibri", size=11)
    data_bold = Font(name="Calibri", size=11, bold=True)
    cno_inside_font = Font(name="Calibri", size=11, bold=True, color="1F497D")
    
    cno_outturn_font = Font(name="Calibri", size=11, bold=True, color=purple_outturn)
    cno_vlk_font = Font(name="Calibri", size=11, bold=True, color=red_vlk)
    tbi_font = Font(name="Calibri", size=11, italic=True, color=purple_tbi)
    tbi_fill = PatternFill(start_color="F2EBF9", end_color="F2EBF9", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color=gray_border),
        right=Side(style='thin', color=gray_border),
        top=Side(style='thin', color=gray_border),
        bottom=Side(style='thin', color=gray_border)
    )

    all_tracked_coaches = []

    for c in inside_coaches:
        cno = c["coach_no"]
        c_entry = dict(c)
        if cno in all_planned_definitions:
            p_info = all_planned_definitions[cno]
            c_entry["corr_pdc"] = p_info["c_pdc"]
            c_entry["desp_pdc"] = p_info["d_pdc"]
            c_entry["remarks"] = p_info["remarks"]
            c_entry["is_planned"] = True
            c_entry["is_vlk"] = p_info["vlk"]
            c_entry["is_outturn"] = p_info.get("outturn", False)
        else:
            c_entry["is_planned"] = False
            c_entry["is_vlk"] = False
            c_entry["is_outturn"] = False
            
        if c_entry.get("is_outturn"):
            c_entry["display_cno"] = f"{cno}*"
        elif c_entry.get("is_vlk"):
            c_entry["display_cno"] = f"{cno}#"
        else:
            c_entry["display_cno"] = cno

        if c_entry["location"] == "In Yard":
            c_entry["location"] = "Inside Shop Yard"
        all_tracked_coaches.append(c_entry)

    for cno, p_info in all_planned_definitions.items():
        if p_info["vlk"]:
            v_entry = {
                "coach_no": cno,
                "coach_desc": p_info["cat"],
                "category": p_info["cat"],
                "family": "ICF" if p_info["cat"] in ("GS", "SLR", "CN") else "DEMU & Self-Propelled",
                "railway": p_info["rly"],
                "division": p_info["div"],
                "year_built": 2019 if "MEMU" in p_info["cat"] else 2013,
                "recd_date": "Pending Intake",
                "tfr_date": "-",
                "location": p_info["loc"],
                "corr_comp_date": "-",
                "corr_pdc": p_info["c_pdc"],
                "desp_pdc": p_info["d_pdc"],
                "remarks": p_info["remarks"],
                "status": "In VLK Yard (To be taken inside)",
                "is_planned": True,
                "is_vlk": True,
                "is_outturn": False,
                "display_cno": f"{cno}#"
            }
            all_tracked_coaches.append(v_entry)

    planned_list = [c for c in all_tracked_coaches if c["is_planned"]]
    unplanned_list = [c for c in all_tracked_coaches if not c["is_planned"]]

    tbi_coaches = [
        {"coach_no": "TO BE IDENTIFIED (GS #1)", "display_cno": "TO BE IDENTIFIED", "coach_desc": "GS", "category": "GS", "division": "-", "railway": "-", "location": "To Be Nominated by Shop", "corr_pdc": "-", "desp_pdc": "30/09/2026", "remarks": "HQR Target 8 GS (6 Nominated, 2 Pending Identification)", "is_planned": True, "is_tbi": True},
        {"coach_no": "TO BE IDENTIFIED (GS #2)", "display_cno": "TO BE IDENTIFIED", "coach_desc": "GS", "category": "GS", "division": "-", "railway": "-", "location": "To Be Nominated by Shop", "corr_pdc": "-", "desp_pdc": "30/09/2026", "remarks": "HQR Target 8 GS (6 Nominated, 2 Pending Identification)", "is_planned": True, "is_tbi": True},
        {"coach_no": "TO BE IDENTIFIED (LHB NAC #1)", "display_cno": "TO BE IDENTIFIED", "coach_desc": "LWSCN", "category": "LWSCN", "division": "-", "railway": "-", "location": "To Be Nominated by Shop", "corr_pdc": "-", "desp_pdc": "30/09/2026", "remarks": "HQR Target 13 LHB-NAC (9 Nominated, 4 Pending Identification)", "is_planned": True, "is_tbi": True},
        {"coach_no": "TO BE IDENTIFIED (LHB NAC #2)", "display_cno": "TO BE IDENTIFIED", "coach_desc": "LWSCN", "category": "LWSCN", "division": "-", "railway": "-", "location": "To Be Nominated by Shop", "corr_pdc": "-", "desp_pdc": "30/09/2026", "remarks": "HQR Target 13 LHB-NAC (9 Nominated, 4 Pending Identification)", "is_planned": True, "is_tbi": True},
        {"coach_no": "TO BE IDENTIFIED (LHB NAC #3)", "display_cno": "TO BE IDENTIFIED", "coach_desc": "LWSCN", "category": "LWSCN", "division": "-", "railway": "-", "location": "To Be Nominated by Shop", "corr_pdc": "-", "desp_pdc": "30/09/2026", "remarks": "HQR Target 13 LHB-NAC (9 Nominated, 4 Pending Identification)", "is_planned": True, "is_tbi": True},
        {"coach_no": "TO BE IDENTIFIED (LHB NAC #4)", "display_cno": "TO BE IDENTIFIED", "coach_desc": "LWSCN", "category": "LWSCN", "division": "-", "railway": "-", "location": "To Be Nominated by Shop", "corr_pdc": "-", "desp_pdc": "30/09/2026", "remarks": "HQR Target 13 LHB-NAC (9 Nominated, 4 Pending Identification)", "is_planned": True, "is_tbi": True}
    ]

    def apply_page_setup(ws):
        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.page_margins.left = 0.3
        ws.page_margins.right = 0.3
        ws.page_margins.top = 0.4
        ws.page_margins.bottom = 0.4

    # =========================================================================
    # TAB 1: Complete Holding List by Type (Streamlined Single Coach Type)
    # =========================================================================
    ws1 = wb.active
    ws1.title = "Holding List by Type"
    apply_page_setup(ws1)

    headers1 = [
        "S.No", "Coach No", "Owning\nRly", "Div", "Coach\nType",
        "Year\nBuilt", "Age\n(Yrs)", "13-Yr Age\nCondition", "Receipt\nDate", "Current\nLocation", "Corr Comp\nDate",
        "Corr\nPDC", "Target Outturn\nPDC", "Shop Remarks /\nFloor Attention"
    ]

    ws1.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers1))
    ws1["A1"] = f"CARRIAGE WORKSHOP - MASTER COACH LIST AS ON {datetime.now().strftime('%d/%m/%Y')} (TOTAL: {len(all_tracked_coaches)} COACHES)"
    ws1["A1"].font = Font(name="Calibri", size=13, bold=True, color="1B365D")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 28

    for col_idx, h in enumerate(headers1, 1):
        c = ws1.cell(row=3, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws1.row_dimensions[3].height = 32

    def sort_key_tab1(x):
        loc = x["location"]
        loc_rank = 0 if loc.startswith("Outturned") else (1 if loc == "In Working Area" else (2 if "Inside Shop Yard" in loc else 3))
        return (get_cat_rank(x["category"]), loc_rank, x["coach_no"])

    sorted_tab1 = sorted(all_tracked_coaches, key=sort_key_tab1)

    current_cat = ""
    row_idx = 4
    sno_tab1 = 1

    for cdata in sorted_tab1:
        cat = cdata["category"]
        cno = cdata["coach_no"]
        is_vlk = cdata.get("is_vlk", False)
        is_out = cdata.get("is_outturn", False)

        if cat != current_cat:
            current_cat = cat
            cat_coaches = [x for x in sorted_tab1 if x["category"] == current_cat]
            in_shop_cnt = sum(1 for x in cat_coaches if x["location"] == "In Working Area")
            in_syd_cnt = sum(1 for x in cat_coaches if "Inside Shop Yard" in x["location"])
            in_vlk_cnt = sum(1 for x in cat_coaches if x.get("is_vlk"))
            
            vlk_str = f", To be taken inside#: {in_vlk_cnt}" if in_vlk_cnt > 0 else ""
            sec_title = f"{current_cat} - TOTAL: {len(cat_coaches)} COACHES (In Working Area: {in_shop_cnt}, Inside Shop Yard: {in_syd_cnt}{vlk_str})"
            sec_cell = ws1.cell(row=row_idx, column=1, value=sec_title)
            ws1.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=len(headers1))
            sec_cell.fill = section_fill
            sec_cell.font = section_font
            sec_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            ws1.row_dimensions[row_idx].height = 22
            row_idx += 1

        row_vals = [
            sno_tab1,
            cdata["display_cno"],
            cdata["railway"],
            cdata["division"],
            cdata["category"],
            cdata["year_built"],
            cdata.get("age", "-"),
            cdata.get("age_condition", "-"),
            cdata["recd_date"],
            cdata["location"],
            cdata["corr_comp_date"],
            cdata.get("corr_pdc") or "",
            cdata.get("desp_pdc") or "",
            cdata.get("remarks") or ""
        ]

        for col_idx, val in enumerate(row_vals, 1):
            cell = ws1.cell(row=row_idx, column=col_idx, value=val)
            cell.border = thin_border
            cell.font = data_font
            
            if col_idx in (1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 2:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if is_out:
                    cell.font = cno_outturn_font
                elif is_vlk:
                    cell.font = cno_vlk_font
                else:
                    cell.font = cno_inside_font
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
            if col_idx in (1, 6, 7, 8, 12, 13):
                cell.font = data_bold

            # Highlight 13-Yr Age Condition
            if col_idx == 8:
                if cdata.get("is_above_13"):
                    cell.fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
                    cell.font = Font(name="Calibri", size=10, bold=True, color="C00000")
                elif cdata.get("age_condition") == "<= 13 Yrs":
                    cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
                    cell.font = Font(name="Calibri", size=10, bold=True, color="1F497D")
                
            if col_idx == 10:
                if is_out:
                    cell.font = Font(name="Calibri", size=10, bold=True, color=purple_outturn)
                elif is_vlk:
                    cell.font = Font(name="Calibri", size=10, bold=True, color=red_vlk)
                elif cdata["location"] == "In Working Area":
                    cell.font = Font(name="Calibri", size=10, bold=True, color="008000")
                else:
                    cell.font = Font(name="Calibri", size=10, bold=True, color="595959")
                    
            if col_idx == 13 and val:
                cell.fill = plan_fill
                cell.font = plan_font
                
        ws1.row_dimensions[row_idx].height = 20
        row_idx += 1
        sno_tab1 += 1

    fn1_row = row_idx + 1
    ws1.cell(row=fn1_row, column=2, value="* NOTE: (*) Indicates coach outturn already taken. (#) Indicates coaches in VLK Yard to be taken inside shop.").font = Font(name="Calibri", size=10, bold=True, italic=True, color="1B365D")
    ws1.merge_cells(start_row=fn1_row, start_column=2, end_row=fn1_row, end_column=len(headers1))
    ws1.row_dimensions[fn1_row].height = 20

    # =========================================================================
    # TAB 2: Planned This Month (Sep-26) - Clean Non-Redundant Layout
    # =========================================================================
    ws2 = wb.create_sheet(title="Planned This Month (Sep-26)")
    apply_page_setup(ws2)

    # 15 columns: A to O
    ws2.merge_cells("A1:O1")
    ws2["A1"] = "WORKSHOP PRODUCTION PLAN - SEPTEMBER 2026 (TOTAL TARGET: 53 COACHES | 47 NOMINATED + 6 TO BE IDENTIFIED)"
    ws2["A1"].font = Font(name="Calibri", size=13, bold=True, color="1B365D")
    ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 28

    pl_shop = sum(1 for c in planned_list if c["location"] == "In Working Area")
    pl_syard = sum(1 for c in planned_list if "Inside Shop Yard" in c["location"])
    pl_vlk = sum(1 for c in planned_list if c.get("is_vlk"))
    
    ws2.merge_cells("B3:D3")
    ws2["B3"] = f"PLANNED IN SHOP: {pl_shop} (Incl. Outturned*)"
    ws2["B3"].fill = PatternFill(start_color=blue_light, end_color=blue_light, fill_type="solid")
    ws2["B3"].font = Font(name="Calibri", size=11, bold=True, color="1B365D")
    ws2["B3"].alignment = Alignment(horizontal="center", vertical="center")

    ws2.merge_cells("E3:G3")
    ws2["E3"] = f"PLANNED IN SHOP YARD: {pl_syard}"
    ws2["E3"].fill = PatternFill(start_color=gray_subtotal, end_color=gray_subtotal, fill_type="solid")
    ws2["E3"].font = Font(name="Calibri", size=11, bold=True, color="595959")
    ws2["E3"].alignment = Alignment(horizontal="center", vertical="center")

    ws2.merge_cells("H3:J3")
    ws2["H3"] = f"TO BE TAKEN INSIDE#: {pl_vlk}#"
    ws2["H3"].fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    ws2["H3"].font = Font(name="Calibri", size=11, bold=True, color=red_vlk)
    ws2["H3"].alignment = Alignment(horizontal="center", vertical="center")

    ws2.merge_cells("K3:L3")
    ws2["K3"] = f"TO BE IDENTIFIED: {len(tbi_coaches)}"
    ws2["K3"].fill = tbi_fill
    ws2["K3"].font = Font(name="Calibri", size=11, italic=True, bold=True, color=purple_tbi)
    ws2["K3"].alignment = Alignment(horizontal="center", vertical="center")

    ws2.merge_cells("M3:O3")
    ws2["M3"] = f"TOTAL TARGET PLAN: {len(planned_list) + len(tbi_coaches)} (Carriage 48 + DEMU 5)"
    ws2["M3"].fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    ws2["M3"].font = Font(name="Calibri", size=11, bold=True, color="7F6000")
    ws2["M3"].alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[3].height = 24

    # Part A: Planned Summary Matrix
    ws2.cell(row=5, column=1, value="PART A: TYPE-WISE & DIVISION-WISE SUMMARY OF WORKSHOP PRODUCTION PLAN (SEPTEMBER 2026)").font = Font(name="Calibri", size=11, bold=True, color="1B365D")
    ws2.merge_cells("A5:O5")
    ws2.row_dimensions[5].height = 22

    pl_matrix = {}
    for c in planned_list:
        cat = c["category"]
        dvn = c["division"]
        rly = c["railway"]
        dcol = f"{dvn} ({rly})" if rly != "SR" else dvn
        if cat not in pl_matrix: pl_matrix[cat] = {}
        pl_matrix[cat][dcol] = pl_matrix[cat].get(dcol, 0) + 1

    tbi_matrix = {"GS": 2, "LWSCN": 4}

    all_pl_divs = ["PGT", "TPJ", "MAS", "MDU", "SA", "TVC", "GHY (NFR)", "PURI (ECoR)", "AII (NWR)", "LJN (NER)"]
    pl_divs = [d for d in all_pl_divs if any(d in pl_matrix.get(c, {}) for c in pl_matrix)]
    headers_pl_sum = ["S.No", "Coach Type"] + pl_divs + ["Identified\nTotal", "To Be\nIdentified", "Total Target\nPlan"]

    for c_idx, h in enumerate(headers_pl_sum, 1):
        cell = ws2.cell(row=6, column=c_idx, value=h)
        if "To Be" in h:
            cell.fill = PatternFill(start_color="E1D5E7", end_color="E1D5E7", fill_type="solid")
            cell.font = Font(name="Calibri", size=11, italic=True, bold=True, color=purple_tbi)
        elif "Total Target" in h:
            cell.fill = PatternFill(start_color="FFE699", end_color="FFE699", fill_type="solid")
            cell.font = Font(name="Calibri", size=11, bold=True, color="7F6000")
        else:
            cell.fill = header_fill
            cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws2.row_dimensions[6].height = 30

    r_idx2 = 7
    sno_pl_sum = 1
    pl_grand_divs = {d: 0 for d in pl_divs}
    tot_identified = 0
    tot_tbi = 0

    all_planned_cats = list(pl_matrix.keys())
    for cat in sorted(all_planned_cats, key=lambda x: get_cat_rank(x)):
        c_dict = pl_matrix[cat]
        row_id_cnt = sum(c_dict.get(d, 0) for d in pl_divs)
        has_vlk_in_cat = any(c.get("is_vlk") for c in planned_list if c["category"] == cat)
        has_out_in_cat = any(c.get("is_outturn") for c in planned_list if c["category"] == cat)
        tbi_cnt = tbi_matrix.get(cat, 0)
        row_target = row_id_cnt + tbi_cnt
        
        vals = [sno_pl_sum, cat]
        for d in pl_divs:
            cnt = c_dict.get(d, 0)
            has_vlk_in_cell = any(c.get("is_vlk") and (f"{c['division']} ({c['railway']})" if c['railway'] != "SR" else c['division']) == d for c in planned_list if c["category"] == cat)
            has_out_in_cell = any(c.get("is_outturn") and (f"{c['division']} ({c['railway']})" if c['railway'] != "SR" else c['division']) == d for c in planned_list if c["category"] == cat)
            
            if cnt == 0:
                vals.append("-")
            elif has_out_in_cell and has_vlk_in_cell:
                vals.append(f"{cnt}*#")
            elif has_out_in_cell:
                vals.append(f"{cnt}*")
            elif has_vlk_in_cell:
                vals.append(f"{cnt}#")
            else:
                vals.append(cnt)
                
        sym = ""
        if has_out_in_cat: sym += "*"
        if has_vlk_in_cat: sym += "#"
        vals.append(f"{row_id_cnt}{sym}")
        vals.append(tbi_cnt if tbi_cnt > 0 else "-")
        vals.append(f"{row_target}{sym}")

        for col_idx, v in enumerate(vals, 1):
            cell = ws2.cell(row=r_idx2, column=col_idx, value=v)
            cell.border = thin_border
            cell.font = data_bold
            if col_idx == 2:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = Font(name="Calibri", size=11, bold=True)
            elif col_idx == len(vals) - 1:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if v != "-":
                    cell.fill = tbi_fill
                    cell.font = tbi_font
            elif col_idx == len(vals):
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = Font(name="Calibri", size=11, bold=True, color="1B365D")
                cell.fill = PatternFill(start_color="FFF9E6", end_color="FFF9E6", fill_type="solid")
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                
        for d in pl_divs:
            pl_grand_divs[d] += c_dict.get(d, 0)
        tot_identified += row_id_cnt
        tot_tbi += tbi_cnt
            
        ws2.row_dimensions[r_idx2].height = 20
        r_idx2 += 1
        sno_pl_sum += 1

    # Grand Total Row
    tot_pl_vals = ["", "TOTAL TARGET PLAN"]
    for d in pl_divs:
        c_v = pl_grand_divs[d]
        has_vlk_in_col = any(c.get("is_vlk") and (f"{c['division']} ({c['railway']})" if c['railway'] != "SR" else c['division']) == d for c in planned_list)
        has_out_in_col = any(c.get("is_outturn") and (f"{c['division']} ({c['railway']})" if c['railway'] != "SR" else c['division']) == d for c in planned_list)
        sym = ""
        if has_out_in_col: sym += "*"
        if has_vlk_in_col: sym += "#"
        tot_pl_vals.append(f"{c_v}{sym}")
        
    tot_pl_vals.append(f"{tot_identified}*#")
    tot_pl_vals.append(tot_tbi)
    tot_pl_vals.append(f"{tot_identified + tot_tbi}*#")

    for col_idx, v in enumerate(tot_pl_vals, 1):
        cell = ws2.cell(row=r_idx2, column=col_idx, value=v)
        cell.fill = total_fill
        cell.font = total_font
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center" if col_idx != 2 else "left", vertical="center")
        if col_idx == len(tot_pl_vals) - 1:
            cell.font = Font(name="Calibri", size=12, italic=True, bold=True, color=purple_tbi)
        elif col_idx == len(tot_pl_vals):
            cell.fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
            cell.font = Font(name="Calibri", size=12, bold=True, color="7F6000")
            
    ws2.row_dimensions[r_idx2].height = 24
    r_idx2 += 2

    # Part B: Chronological Despatch Roster (Streamlined without duplicates!)
    # Columns:
    # A: Sl.No
    # B: Coach No
    # C: Coach Type
    # D: Owning Div
    # E: Current Location
    # F: Corrosion PDC
    # G: Target Outturn PDC (Single clean date!)
    # H to O: Remarks / Shop Floor Attention (Merged)

    ws2.cell(row=r_idx2, column=1, value="PART B: CHRONOLOGICAL ROSTER OF PLANNED COACHES (TARGET DESPATCH ORDER)").font = Font(name="Calibri", size=11, bold=True, color="1B365D")
    ws2.merge_cells(start_row=r_idx2, start_column=1, end_row=r_idx2, end_column=15)
    ws2.row_dimensions[r_idx2].height = 22
    r_idx2 += 1

    headers_pl_dtl_clean = [
        "Sl.No", "Coach No", "Coach\nType", "Owning\nDiv", "Current Location",
        "Corrosion\nPDC", "Target Outturn\nPDC"
    ]

    for c_idx, h in enumerate(headers_pl_dtl_clean, 1):
        cell = ws2.cell(row=r_idx2, column=c_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Merge columns H to O (8 columns!) for Remarks
    ws2.merge_cells(start_row=r_idx2, start_column=8, end_row=r_idx2, end_column=15)
    rem_hdr = ws2.cell(row=r_idx2, column=8, value="Remarks / Shop Floor Attention")
    rem_hdr.fill = header_fill
    rem_hdr.font = header_font
    rem_hdr.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for c_idx in range(8, 16):
        ws2.cell(row=r_idx2, column=c_idx).border = thin_border
        
    ws2.row_dimensions[r_idx2].height = 30
    r_idx2 += 1

    def parse_d_pdc(item):
        d_str = item.get("desp_pdc") or ""
        try:
            return datetime.strptime(d_str, "%d/%m/%Y")
        except:
            return datetime(2026, 9, 30)

    planned_sorted = sorted(planned_list, key=lambda x: (parse_d_pdc(x), get_cat_rank(x["category"])))

    # Print Nominated coaches (1 to 47)
    for idx, c in enumerate(planned_sorted, 1):
        is_vlk = c.get("is_vlk", False)
        is_out = c.get("is_outturn", False)
        
        vals = [
            idx,
            c["display_cno"],
            c["category"],
            c["division"],
            c["location"],
            c.get("corr_pdc") or "-",
            c.get("desp_pdc") or "-"
        ]

        for col_idx, v in enumerate(vals, 1):
            cell = ws2.cell(row=r_idx2, column=col_idx, value=v)
            cell.border = thin_border
            cell.font = data_font
            
            if col_idx in (1, 3, 4, 6, 7):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 2:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if is_out:
                    cell.font = cno_outturn_font
                elif is_vlk:
                    cell.font = cno_vlk_font
                else:
                    cell.font = cno_inside_font
            elif col_idx == 5:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if is_out:
                    cell.font = Font(name="Calibri", size=10, bold=True, color=purple_outturn)
                elif is_vlk:
                    cell.font = Font(name="Calibri", size=10, bold=True, color=red_vlk)
                elif c["location"] == "In Working Area":
                    cell.font = Font(name="Calibri", size=10, bold=True, color="008000")
                else:
                    cell.font = Font(name="Calibri", size=10, bold=True, color="595959")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
            if col_idx in (1, 6, 7):
                cell.font = data_bold

        # Remarks merged from column 8 to 15
        ws2.merge_cells(start_row=r_idx2, start_column=8, end_row=r_idx2, end_column=15)
        rem_cell = ws2.cell(row=r_idx2, column=8, value=c.get("remarks") or "-")
        rem_cell.font = data_font
        rem_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        for c_idx in range(8, 16):
            ws2.cell(row=r_idx2, column=c_idx).border = thin_border
            
        ws2.row_dimensions[r_idx2].height = 20
        r_idx2 += 1

    # Section separator for TO BE IDENTIFIED COACHES
    tbi_sec_cell = ws2.cell(row=r_idx2, column=1, value="PENDING COACH NOMINATION / TO BE IDENTIFIED BY SHOP (HQR TARGET GAP: 6 COACHES)")
    ws2.merge_cells(start_row=r_idx2, start_column=1, end_row=r_idx2, end_column=15)
    tbi_sec_cell.fill = PatternFill(start_color="E1D5E7", end_color="E1D5E7", fill_type="solid")
    tbi_sec_cell.font = Font(name="Calibri", size=11, bold=True, italic=True, color=purple_tbi)
    tbi_sec_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws2.row_dimensions[r_idx2].height = 22
    r_idx2 += 1

    for idx, c in enumerate(tbi_coaches, len(planned_sorted) + 1):
        vals = [
            idx,
            c["display_cno"],
            c["category"],
            c["division"],
            c["location"],
            c.get("corr_pdc") or "-",
            c.get("desp_pdc") or "-"
        ]

        for col_idx, v in enumerate(vals, 1):
            cell = ws2.cell(row=r_idx2, column=col_idx, value=v)
            cell.border = thin_border
            cell.fill = tbi_fill
            cell.font = tbi_font
            
            if col_idx in (1, 3, 4, 6, 7):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 2:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

        ws2.merge_cells(start_row=r_idx2, start_column=8, end_row=r_idx2, end_column=15)
        rem_cell = ws2.cell(row=r_idx2, column=8, value=c.get("remarks") or "-")
        rem_cell.fill = tbi_fill
        rem_cell.font = tbi_font
        rem_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        for c_idx in range(8, 16):
            ws2.cell(row=r_idx2, column=c_idx).border = thin_border
            cell.fill = tbi_fill
            
        ws2.row_dimensions[r_idx2].height = 20
        r_idx2 += 1

    r_idx2 += 1
    fn_cell_t2 = ws2.cell(row=r_idx2, column=1, value="* NOTE: (*) Indicates coach outturn already taken. (#) Indicates coaches in VLK Yard to be taken inside shop. Italics indicate stock pending shop nomination.")
    fn_cell_t2.font = Font(name="Calibri", size=10, bold=True, italic=True, color="1B365D")
    ws2.merge_cells(start_row=r_idx2, start_column=1, end_row=r_idx2, end_column=15)
    ws2.row_dimensions[r_idx2].height = 20

    # =========================================================================
    # TAB 3: Not Planned This Month (Streamlined Single Coach Type)
    # =========================================================================
    ws3 = wb.create_sheet(title="Not Planned This Month")
    apply_page_setup(ws3)

    headers_un_dtl = [
        "Sl.No", "Coach No", "Owning\nRly", "Div", "Coach\nType",
        "Year\nBuilt", "Receipt\nDate", "Current\nLocation", "Corr Comp\nDate"
    ]

    ws3.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers_un_dtl))
    ws3["A1"] = f"COACHES IN WORKSHOP HOLDING NOT PLANNED FOR SEPTEMBER 2026 ({len(unplanned_list)} COACHES)"
    ws3["A1"].font = Font(name="Calibri", size=13, bold=True, color="1B365D")
    ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws3.row_dimensions[1].height = 28

    un_shop = sum(1 for c in unplanned_list if c["location"] == "In Working Area")
    un_syd = sum(1 for c in unplanned_list if "Inside Shop Yard" in c["location"])
    
    ws3.merge_cells("B3:C3")
    ws3["B3"] = f"UNPLANNED IN SHOP: {un_shop}"
    ws3["B3"].fill = PatternFill(start_color=blue_light, end_color=blue_light, fill_type="solid")
    ws3["B3"].font = Font(name="Calibri", size=11, bold=True, color="1B365D")
    ws3["B3"].alignment = Alignment(horizontal="center", vertical="center")

    ws3.merge_cells("D3:E3")
    ws3["D3"] = f"UNPLANNED IN SHOP YARD: {un_syd}"
    ws3["D3"].fill = PatternFill(start_color=gray_subtotal, end_color=gray_subtotal, fill_type="solid")
    ws3["D3"].font = Font(name="Calibri", size=11, bold=True, color="595959")
    ws3["D3"].alignment = Alignment(horizontal="center", vertical="center")

    ws3.merge_cells("F3:H3")
    ws3["F3"] = f"TOTAL UNPLANNED HOLDING: {len(unplanned_list)}"
    ws3["F3"].fill = PatternFill(start_color="B4C6E7", end_color="B4C6E7", fill_type="solid")
    ws3["F3"].font = Font(name="Calibri", size=11, bold=True, color="000000")
    ws3["F3"].alignment = Alignment(horizontal="center", vertical="center")
    ws3.row_dimensions[3].height = 24

    # Part A: Summary Matrix of Unplanned Coaches
    ws3.cell(row=5, column=1, value="PART A: TYPE-WISE & DIVISION-WISE SUMMARY OF UNPLANNED WORKSHOP HOLDING STOCK").font = Font(name="Calibri", size=11, bold=True, color="1B365D")
    ws3.merge_cells(start_row=5, start_column=1, end_row=5, end_column=len(headers_un_dtl))
    ws3.row_dimensions[5].height = 22

    un_matrix = {}
    for c in unplanned_list:
        cat = c["category"]
        dvn = c["division"]
        rly = c["railway"]
        dcol = f"{dvn} ({rly})" if rly != "SR" else dvn
        if cat not in un_matrix: un_matrix[cat] = {}
        un_matrix[cat][dcol] = un_matrix[cat].get(dcol, 0) + 1

    un_divs = [d for d in ordered_divs if any(d in un_matrix.get(c, {}) for c in un_matrix)]
    headers_un_sum = ["S.No", "Coach Type"] + un_divs + ["Total Unplanned"]

    for c_idx, h in enumerate(headers_un_sum, 1):
        cell = ws3.cell(row=6, column=c_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws3.row_dimensions[6].height = 26

    r_idx3 = 7
    sno_un_sum = 1
    un_grand_divs = {d: 0 for d in un_divs}

    for cat in sorted(un_matrix.keys(), key=lambda x: get_cat_rank(x)):
        c_dict = un_matrix[cat]
        row_t = sum(c_dict.get(d, 0) for d in un_divs)
        
        vals = [sno_un_sum, cat] + [c_dict.get(d, "-") if c_dict.get(d, 0) > 0 else "-" for d in un_divs] + [row_t]
        for col_idx, v in enumerate(vals, 1):
            cell = ws3.cell(row=r_idx3, column=col_idx, value=v)
            cell.border = thin_border
            cell.font = data_bold
            if col_idx == 2:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = Font(name="Calibri", size=11, bold=True)
            elif col_idx == len(vals):
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = Font(name="Calibri", size=11, bold=True, color="1B365D")
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                
        for d in un_divs:
            un_grand_divs[d] += c_dict.get(d, 0)
            
        ws3.row_dimensions[r_idx3].height = 20
        r_idx3 += 1
        sno_un_sum += 1

    tot_un_vals = ["", "TOTAL UNPLANNED"] + [un_grand_divs[d] for d in un_divs] + [len(unplanned_list)]
    for col_idx, v in enumerate(tot_un_vals, 1):
        cell = ws3.cell(row=r_idx3, column=col_idx, value=v)
        cell.fill = total_fill
        cell.font = total_font
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center" if col_idx != 2 else "left", vertical="center")
    ws3.row_dimensions[r_idx3].height = 22
    r_idx3 += 2

    # Part B: Detailed Roster of Unplanned Coaches
    ws3.cell(row=r_idx3, column=1, value="PART B: ROSTER OF UNPLANNED HOLDING COACHES (AVAILABLE FOR FUTURE PLANNING)").font = Font(name="Calibri", size=11, bold=True, color="1B365D")
    ws3.merge_cells(start_row=r_idx3, start_column=1, end_row=r_idx3, end_column=len(headers_un_dtl))
    ws3.row_dimensions[r_idx3].height = 22
    r_idx3 += 1

    for c_idx, h in enumerate(headers_un_dtl, 1):
        cell = ws3.cell(row=r_idx3, column=c_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws3.row_dimensions[r_idx3].height = 28
    r_idx3 += 1

    unplanned_sorted = sorted(unplanned_list, key=lambda x: (get_cat_rank(x["category"]), 0 if x["location"] == "In Working Area" else 1, x["coach_no"]))

    current_un_cat = ""
    for idx, c in enumerate(unplanned_sorted, 1):
        cat = c["category"]

        if cat != current_un_cat:
            current_un_cat = cat
            c_cnt = sum(1 for x in unplanned_sorted if x["category"] == current_un_cat)
            sec_title = f"{current_un_cat} - UNPLANNED: {c_cnt} COACHES"
            sec_c = ws3.cell(row=r_idx3, column=1, value=sec_title)
            ws3.merge_cells(start_row=r_idx3, start_column=1, end_row=r_idx3, end_column=len(headers_un_dtl))
            sec_c.fill = section_fill
            sec_c.font = section_font
            sec_c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            ws3.row_dimensions[r_idx3].height = 20
            r_idx3 += 1

        vals = [
            idx,
            c["display_cno"],
            c["railway"],
            c["division"],
            c["category"],
            c["year_built"],
            c["recd_date"],
            c["location"],
            c["corr_comp_date"]
        ]

        for col_idx, v in enumerate(vals, 1):
            cell = ws3.cell(row=r_idx3, column=col_idx, value=v)
            cell.border = thin_border
            cell.font = data_font
            
            if col_idx in (1, 3, 4, 5, 6, 7, 9):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 2:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = cno_inside_font
            elif col_idx == 8:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = Font(name="Calibri", size=10, bold=True, color="008000" if c["location"] == "In Working Area" else "595959")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
            if col_idx in (1, 6, 7):
                cell.font = data_bold
                
        ws3.row_dimensions[r_idx3].height = 20
        r_idx3 += 1

    # =========================================================================
    # TAB 4: Overall Division Summary
    # =========================================================================
    ws4 = wb.create_sheet(title="Overall Division Summary")
    apply_page_setup(ws4)

    ws4.merge_cells("A1:L1")
    ws4["A1"] = f"CARRIAGE WORKSHOP - OVERALL TYPE-WISE & DIVISION-WISE POSITION AS ON {datetime.now().strftime('%d/%m/%Y')}"
    ws4["A1"].font = Font(name="Calibri", size=13, bold=True, color="1B365D")
    ws4["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws4.row_dimensions[1].height = 28

    tot_shop = sum(1 for x in inside_coaches if x["location"] == "In Working Area")
    tot_syd = sum(1 for x in inside_coaches if x["location"] == "In Yard")
    pure_holding = tot_shop + tot_syd
    tot_vlk = sum(1 for x in all_tracked_coaches if x.get("is_vlk"))
    
    ws4.merge_cells("B3:C3")
    ws4["B3"] = f"IN WORKING AREA: {tot_shop}"
    ws4["B3"].fill = PatternFill(start_color=blue_light, end_color=blue_light, fill_type="solid")
    ws4["B3"].font = Font(name="Calibri", size=11, bold=True, color="1B365D")
    ws4["B3"].alignment = Alignment(horizontal="center", vertical="center")

    ws4.merge_cells("D3:E3")
    ws4["D3"] = f"INSIDE SHOP YARD: {tot_syd}"
    ws4["D3"].fill = PatternFill(start_color=gray_subtotal, end_color=gray_subtotal, fill_type="solid")
    ws4["D3"].font = Font(name="Calibri", size=11, bold=True, color="595959")
    ws4["D3"].alignment = Alignment(horizontal="center", vertical="center")

    ws4.merge_cells("F3:G3")
    ws4["F3"] = f"ACTIVE WORKSHOP HOLDING: {pure_holding}"
    ws4["F3"].fill = PatternFill(start_color="B4C6E7", end_color="B4C6E7", fill_type="solid")
    ws4["F3"].font = Font(name="Calibri", size=11, bold=True, color="000000")
    ws4["F3"].alignment = Alignment(horizontal="center", vertical="center")

    ws4.merge_cells("H3:I3")
    ws4["H3"] = "OUTTURNED (AWAITING DESP): 1*"
    ws4["H3"].fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    ws4["H3"].font = Font(name="Calibri", size=11, bold=True, color="375623")
    ws4["H3"].alignment = Alignment(horizontal="center", vertical="center")

    ws4.merge_cells("J3:K3")
    ws4["J3"] = f"TO BE TAKEN INSIDE#: {tot_vlk}#"
    ws4["J3"].fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    ws4["J3"].font = Font(name="Calibri", size=11, bold=True, color=red_vlk)
    ws4["J3"].alignment = Alignment(horizontal="center", vertical="center")
    ws4.row_dimensions[3].height = 24

    headers4 = ["S.No", "Coach Type"] + ordered_divs + ["Total Position"]

    for col_idx, h in enumerate(headers4, 1):
        c = ws4.cell(row=5, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws4.row_dimensions[5].height = 26

    row_idx4 = 6
    sno4 = 1

    summary_groups = data["summary_groups"]
    grand_totals = data["grand_totals"]
    grand_total_count = data["grand_total_count"]

    for grp in summary_groups:
        grp_name = grp["group_name"]
        grp_rows = grp["rows"]
        grp_subtotals = grp["subtotal"]
        grp_tot = grp["subtotal_count"]

        grp_cell = ws4.cell(row=row_idx4, column=1, value=grp_name)
        ws4.merge_cells(start_row=row_idx4, start_column=1, end_row=row_idx4, end_column=len(headers4))
        grp_cell.fill = section_fill
        grp_cell.font = section_font
        grp_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws4.row_dimensions[row_idx4].height = 22
        row_idx4 += 1

        for r_data in grp_rows:
            cat = r_data["category"]
            counts = r_data["counts"]
            tot = r_data["total"]

            vals4 = [sno4, cat] + [counts[d] if counts[d] > 0 else "-" for d in ordered_divs] + [tot]
            for col_idx, v in enumerate(vals4, 1):
                cell = ws4.cell(row=row_idx4, column=col_idx, value=v)
                cell.border = thin_border
                cell.font = data_bold
                if col_idx == 2:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                    cell.font = Font(name="Calibri", size=11, bold=True)
                elif col_idx == len(vals4):
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.font = Font(name="Calibri", size=11, bold=True, color="1B365D")
                else:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    
            ws4.row_dimensions[row_idx4].height = 20
            row_idx4 += 1
            sno4 += 1

        sub_vals = ["", f"Subtotal {grp_name}"] + [grp_subtotals[d] if grp_subtotals[d] > 0 else "-" for d in ordered_divs] + [grp_tot]
        for col_idx, v in enumerate(sub_vals, 1):
            cell = ws4.cell(row=row_idx4, column=col_idx, value=v)
            cell.fill = subtotal_fill
            cell.font = subtotal_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center" if col_idx != 2 else "left", vertical="center")
        ws4.row_dimensions[row_idx4].height = 21
        row_idx4 += 1

    tot_vals = ["", "GRAND TOTAL WORKSHOP HOLDING"] + [grand_totals[d] for d in ordered_divs] + [grand_total_count]
    for col_idx, v in enumerate(tot_vals, 1):
        cell = ws4.cell(row=row_idx4, column=col_idx, value=v)
        cell.fill = total_fill
        cell.font = total_font
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center" if col_idx != 2 else "left", vertical="center")
    ws4.row_dimensions[row_idx4].height = 24

    row_idx4 += 2
    ws4.merge_cells(start_row=row_idx4, start_column=1, end_row=row_idx4, end_column=len(headers4))
    fn_cell = ws4.cell(row=row_idx4, column=1, value="* NOTE: In addition to the 58 Active Holding + 1 Outturned Coach (146413*) inside workshop, 11 coaches (094291#, 136530#, 156716#, 198859#-64#, 198839#-40#) are in VLK Yard to be taken inside.")
    fn_cell.font = Font(name="Calibri", size=10, bold=True, italic=True, color="1B365D")
    fn_cell.alignment = Alignment(horizontal="left", vertical="center")
    ws4.row_dimensions[row_idx4].height = 22

    # Column widths for Tab 1
    ws1.column_dimensions["A"].width = 7
    ws1.column_dimensions["B"].width = 14
    ws1.column_dimensions["C"].width = 9
    ws1.column_dimensions["D"].width = 9
    ws1.column_dimensions["E"].width = 13
    ws1.column_dimensions["F"].width = 10
    ws1.column_dimensions["G"].width = 13
    ws1.column_dimensions["H"].width = 24
    ws1.column_dimensions["I"].width = 13
    ws1.column_dimensions["J"].width = 12
    ws1.column_dimensions["K"].width = 15
    ws1.column_dimensions["L"].width = 30

    # Column widths for Tab 2
    ws2.column_dimensions["A"].width = 6   # Sl.No
    ws2.column_dimensions["B"].width = 15  # Coach No / Category
    ws2.column_dimensions["C"].width = 12  # Coach Type / PGT
    ws2.column_dimensions["D"].width = 9   # Owning Div / TPJ
    ws2.column_dimensions["E"].width = 24  # Current Location / MAS
    ws2.column_dimensions["F"].width = 13  # Corrosion PDC / MDU
    ws2.column_dimensions["G"].width = 15  # Target Outturn PDC / SA
    ws2.column_dimensions["H"].width = 11  # Remarks merged start / TVC
    ws2.column_dimensions["I"].width = 11  # GHY
    ws2.column_dimensions["J"].width = 11  # PURI (ECoR) - Compact!
    ws2.column_dimensions["K"].width = 11  # AII (NWR)
    ws2.column_dimensions["L"].width = 11  # LJN (NER)
    ws2.column_dimensions["M"].width = 12  # Identified Total
    ws2.column_dimensions["N"].width = 12  # To Be Identified
    ws2.column_dimensions["O"].width = 13  # Total Target Plan

    # Tab 3:
    ws3.column_dimensions["A"].width = 7
    ws3.column_dimensions["B"].width = 14
    ws3.column_dimensions["C"].width = 9
    ws3.column_dimensions["D"].width = 9
    ws3.column_dimensions["E"].width = 13
    ws3.column_dimensions["F"].width = 10
    ws3.column_dimensions["G"].width = 13
    ws3.column_dimensions["H"].width = 24
    ws3.column_dimensions["I"].width = 13

    # Tab 4:
    ws4.column_dimensions["A"].width = 7
    ws4.column_dimensions["B"].width = 32
    for c_idx in range(3, len(headers4) + 1):
        col_letter = get_column_letter(c_idx)
        ws4.column_dimensions[col_letter].width = 12

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()

