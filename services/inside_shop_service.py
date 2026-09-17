import os
import io
import json
from services.type_wise_holding_service import get_type_wise_holding_report_data
from services.erp_service import fetch_coach_meta

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
    if d in ("PRYJ", "AGC", "JHS", "ALD"): return "NCR"
    if d in ("MAS", "TPJ", "MDU", "TVC", "PGT", "SA"): return "SR"
    return "SR"

def get_inside_shop_data(month="August", year=2026):
    """
    Returns 100% Live Synced ERP coaches currently holding in the workshop boundary.
    """
    rep = get_type_wise_holding_report_data(month, year)
    
    possible_coaches = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "erp_coaches_cache.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "erp_coaches_cache.json"),
        r"D:\TypeWiseHoldingApp\erp_coaches_cache.json",
        "erp_coaches_cache.json"
    ]
    cache_path = next((p for p in possible_coaches if os.path.exists(p)), possible_coaches[0])
    cache_data = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f: cache_data = json.load(f)
        except Exception: pass

    coach_details_by_no = {}
    for did, det in cache_data.items():
        cno = str(det.get("coachno") or "").strip()
        if cno:
            coach_details_by_no[cno] = det

    icf_list = []
    lhb_list = []
    emu_list = []
    yard_list = []
    fnd_list = []

    for r in rep["data"]:
        cat = r["coach_type"]
        
        # 1. Under Attention (Work Area)
        for cno in r.get("under_attention_coaches", []):
            det = coach_details_by_no.get(cno, {})
            desc = det.get("coach_desc") or cat
            pit = det.get("pit_num") or "SHOP"
            stage = det.get("stageid") or "1003"
            
            # Live meta lookup for true division and railway
            meta = fetch_coach_meta(cno)
            divn = meta.get("divisionName") or meta.get("divisionId") or det.get("division") or "TPJ"
            rly = meta.get("railway") or get_true_railway(divn)
            
            fam = "LHB" if ("LW" in desc or "LS" in desc) else ("EMU" if "EMU" in desc else ("DEMU" if "DEMU" in desc or "DPC" in desc else ("VB" if "VB" in desc or "TS" in desc else "ICF")))
            
            c_obj = {
                "coachno": cno,
                "coach_desc": desc,
                "type": desc,
                "category": cat,
                "family": fam,
                "pit": pit,
                "pit_num": pit,
                "stage": stage,
                "stageid": stage,
                "divn": divn,
                "division": divn,
                "rly": rly,
                "recd_date": det.get("recd_date") or "",
                "pdc": det.get("pdc_date") or "",
                "desp_date": "",
                "status": "Work Area"
            }
            if fam == "ICF":
                icf_list.append(c_obj)
            elif fam == "LHB":
                lhb_list.append(c_obj)
            else:
                emu_list.append(c_obj)

        # 2. In Yard
        for cno in r.get("in_yard_coaches", []):
            det = coach_details_by_no.get(cno, {})
            desc = det.get("coach_desc") or cat
            pit = det.get("pit_num") or "OT/YD"
            stage = det.get("stageid") or "1001"
            
            meta = fetch_coach_meta(cno)
            divn = meta.get("divisionName") or meta.get("divisionId") or det.get("division") or "TPJ"
            rly = meta.get("railway") or get_true_railway(divn)
            
            fam = "LHB" if ("LW" in desc or "LS" in desc) else ("EMU" if "EMU" in desc else ("DEMU" if "DEMU" in desc or "DPC" in desc else ("VB" if "VB" in desc or "TS" in desc else "ICF")))
            
            yard_list.append({
                "coachno": cno,
                "coach_desc": desc,
                "type": desc,
                "category": cat,
                "family": fam,
                "pit": pit,
                "pit_num": pit,
                "stage": stage,
                "stageid": stage,
                "divn": divn,
                "division": divn,
                "rly": rly,
                "recd_date": det.get("recd_date") or "",
                "pdc": det.get("pdc_date") or "",
                "desp_date": "",
                "status": "In Yard"
            })

        # 3. FND
        for cno in r.get("fnd_coaches", []):
            det = coach_details_by_no.get(cno, {})
            desc = det.get("coach_desc") or cat
            pit = det.get("pit_num") or "YARD"
            stage = det.get("stageid") or "1004"
            
            meta = fetch_coach_meta(cno)
            divn = meta.get("divisionName") or meta.get("divisionId") or det.get("division") or "TPJ"
            rly = meta.get("railway") or get_true_railway(divn)
            
            fam = "LHB" if ("LW" in desc or "LS" in desc) else ("EMU" if "EMU" in desc else ("DEMU" if "DEMU" in desc or "DPC" in desc else ("VB" if "VB" in desc or "TS" in desc else "ICF")))
            
            fnd_list.append({
                "coachno": cno,
                "coach_desc": desc,
                "type": desc,
                "category": cat,
                "family": fam,
                "pit": pit,
                "pit_num": pit,
                "stage": stage,
                "stageid": stage,
                "divn": divn,
                "division": divn,
                "rly": rly,
                "recd_date": det.get("recd_date") or "",
                "pdc": det.get("pdc_date") or "",
                "desp_date": det.get("desp_date") or "",
                "status": "FND"
            })

    work_area_list = icf_list + lhb_list + emu_list
    total_inside = len(work_area_list) + len(yard_list) + len(fnd_list)

    return {
        "success": True,
        "work_area": work_area_list,
        "yard": yard_list,
        "fnd": fnd_list,
        "work_area_count": len(work_area_list),
        "yard_count": len(yard_list),
        "fnd_count": len(fnd_list),
        "total_holding": total_inside,
        "counts": {
            "work_area": len(work_area_list),
            "yard": len(yard_list),
            "fnd": len(fnd_list),
            "total_inside": total_inside,
            "icf_count": len(icf_list),
            "lhb_count": len(lhb_list),
            "emu_count": len(emu_list)
        },
        "sections": {
            "icf": icf_list,
            "lhb": lhb_list,
            "emu_demu": emu_list,
            "yard": yard_list,
            "fnd": fnd_list
        }
    }
