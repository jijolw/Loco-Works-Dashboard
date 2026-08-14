import os
import sys
import re
import json
from datetime import datetime
import requests

# Add parent path for imports if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SUPABASE_URL, SUPABASE_KEY
from services.decoders import decode_family

# Optional imports for LLM / LangChain
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False


# ---------------------------------------------------------
# Helper functions for Supabase Queries
# ---------------------------------------------------------

def _parse_date_local(dt_str):
    if not dt_str:
        return None
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
        if code_upper in ("LWACCN", "LWACCW", "LWCBAC"): return "LWACCN"
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

def fetch_relevant_coaches_from_supabase(month_name, year_val):
    months_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    m_idx = months_map.get(month_name.lower(), 7)
    m_str = f"{m_idx:02d}"
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    # We fetch active ones
    url_active = f"{SUPABASE_URL}/erp_active_coaches?in_days=not.is.null"
    r_act = requests.get(url_active, headers=headers, timeout=20)
    r_act.raise_for_status()
    coaches = r_act.json()
    
    # We also fetch records matching the target month/year in 'make'
    patterns = [
        f"like.*/{m_str}/{year_val}*",
        f"like.*/{m_idx}/{year_val}*",
        f"like.*-{m_str}-{year_val}*",
        f"like.*{year_val}-{m_str}*"
    ]
    
    seen_ids = {c["demandid"] for c in coaches if c.get("demandid")}
    
    for pat in patterns:
        url_pat = f"{SUPABASE_URL}/erp_active_coaches?make={pat}"
        try:
            r_pat = requests.get(url_pat, headers=headers, timeout=20)
            if r_pat.ok:
                for c in r_pat.json():
                    did = c.get("demandid")
                    if did and did not in seen_ids:
                        coaches.append(c)
                        seen_ids.add(did)
        except Exception as e:
            pass
            
    return coaches

def fetch_supabase_targets_for_month(month_name, year_val):
    months_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    m_idx = months_map.get(month_name.lower(), 7)
    
    # Financial year calculation
    fy_year = year_val if m_idx >= 4 else year_val - 1
    fy_str = f"{fy_year}-{str(fy_year + 1)[2:]}"
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    url = f"{SUPABASE_URL}/outturn_targets?month=eq.{m_idx}&fy=eq.{fy_str}&select=*"
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching targets: {e}")
        return []

def map_targets_to_categories(targets_list):
    ordered_cats = [
        "CN", "GS", "CZ", "SLR", "LWSCN", "LWS", "LWACCN",
        "EMU MC", "EMU TC", "MEMU MC", "MEMU TC",
        "DPC", "DEMU TC", "TW4W", "TW8W", "NMG", "ART", "OR"
    ]
    target_map = {cat: 0 for cat in ordered_cats}
    
    for t in targets_list:
        st = t.get("stock_type", "").upper()
        qty = t.get("target_qty", 0)
        
        if "AC LOCO" in st:
            continue
            
        if st == "ICF":
            target_map["GS"] += int(qty * 0.4)
            target_map["CN"] += int(qty * 0.4)
            target_map["SLR"] += int(qty * 0.2)
        elif st == "LHB":
            target_map["LWS"] += int(qty * 0.4)
            target_map["LWSCN"] += int(qty * 0.3)
            target_map["LWACCN"] += int(qty * 0.3)
        elif st == "NMGHS":
            target_map["NMG"] += qty
        elif st == "EMU/MEMU":
            target_map["EMU MC"] += int(qty * 0.25)
            target_map["EMU TC"] += int(qty * 0.25)
            target_map["MEMU MC"] += int(qty * 0.25)
            target_map["MEMU TC"] += int(qty * 0.25)
        elif st == "DEMU/DTC/TC":
            target_map["DPC"] += int(qty * 0.3)
            target_map["DEMU TC"] += int(qty * 0.7)
        elif st == "TW 4W":
            target_map["TW4W"] += qty
        elif st == "TW 8W":
            target_map["TW8W"] += qty
        elif st in ("ART", "SPART", "SPIC"):
            target_map["ART"] += qty
            
    return target_map


# ---------------------------------------------------------
# Domain Tools (Supabase REST Driven)
# ---------------------------------------------------------

def tool_get_corrosion_summary(month: str = "July", year: int = 2026, coach_type: str = "") -> dict:
    """
    Get corrosion completion status and coach lists for the specified month/year from Supabase.
    Optionally filter by coach_type (e.g. 'CN', 'GS', 'LWSCN', 'LWS').
    """
    coaches = fetch_relevant_coaches_from_supabase(month, year)
    
    months_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    m_idx = months_map.get(month.lower(), 7)
    
    total_corr = 0
    all_corr_coaches = []
    category_map = {}
    
    for c in coaches:
        coach_desc = c.get("coach_desc") or ""
        family = decode_family(coach_desc)
        code = map_coach_desc_to_code(coach_desc, family)
        cat = get_report_category(code, family)
        if not cat:
            continue
            
        if coach_type and coach_type.upper() != cat.upper():
            continue
            
        make_packed = c.get("make") or ""
        parts = make_packed.split("||")
        corr_comp = parts[7] if len(parts) > 7 else ""
        
        dt = _parse_date_local(corr_comp)
        if dt and dt.month == m_idx and dt.year == int(year):
            total_corr += 1
            all_corr_coaches.append(c.get("coachno"))
            
            if cat not in category_map:
                category_map[cat] = []
            category_map[cat].append(c.get("coachno"))
            
    breakdown = []
    for cat, cnos in category_map.items():
        breakdown.append({
            "Coach Type": cat,
            "Corrosion Completed": len(cnos),
            "Coaches": sorted(cnos)
        })
        
    filter_label = f" ({coach_type.upper()})" if coach_type else ""
    return {
        "title": f"Corrosion Completed in {month} {year}{filter_label}",
        "total_count": total_corr,
        "coaches": sorted(list(set(all_corr_coaches))),
        "breakdown": breakdown,
        "answer_summary": f"A total of {total_corr} coach(es){filter_label} have completed corrosion in {month} {year} (verified from Supabase)."
    }


def tool_get_coaches_at_hand(coach_type: str = "", location: str = "all") -> dict:
    """
    Get available floor stock at hand (Holding in work area / Holding at Yard) for current active stock from Supabase.
    Optionally filter by coach_type (e.g. 'CN', 'GS', 'SLR') or location ('shop', 'yard', 'all').
    """
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    url = f"{SUPABASE_URL}/erp_active_coaches?in_days=not.is.null"
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    coaches = resp.json()
    
    total_shop = 0
    total_yard = 0
    shop_coaches = []
    yard_coaches = []
    category_map = {}
    
    for c in coaches:
        status_val = str(c.get("status") or "").strip().upper()
        if status_val in ("RETURN", "COND", "161"):
            continue
            
        make_packed = c.get("make") or ""
        parts = make_packed.split("||")
        desp_date = parts[8] if len(parts) > 8 else ""
        actualdespdate = parts[9] if len(parts) > 9 else ""
        
        # If there's any despatch date, it's not at hand
        if desp_date.strip() or actualdespdate.strip():
            continue
            
        coach_desc = c.get("coach_desc") or ""
        family = decode_family(coach_desc)
        code = map_coach_desc_to_code(coach_desc, family)
        cat = get_report_category(code, family)
        if not cat:
            continue
            
        if coach_type and coach_type.upper() != cat.upper():
            continue
            
        pit = c.get("pitnum") or ""
        is_yard = is_yard_location(pit)
        
        if is_yard:
            total_yard += 1
            yard_coaches.append(c.get("coachno"))
        else:
            total_shop += 1
            shop_coaches.append(c.get("coachno"))
            
        if cat not in category_map:
            category_map[cat] = {"shop": [], "yard": []}
            
        if is_yard:
            category_map[cat]["yard"].append(c.get("coachno"))
        else:
            category_map[cat]["shop"].append(c.get("coachno"))
            
    breakdown = []
    for cat, data in category_map.items():
        breakdown.append({
            "Coach Type": cat,
            "Under Attention (Shop)": len(data["shop"]),
            "Shop Coaches": sorted(data["shop"]),
            "Holding at Yard": len(data["yard"]),
            "Yard Coaches": sorted(data["yard"]),
            "Total Available": len(data["shop"]) + len(data["yard"])
        })
        
    filter_label = f" ({coach_type.upper()})" if coach_type else ""
    all_at_hand = sorted(list(set(shop_coaches + yard_coaches)))
    total_at_hand = total_shop + total_yard
    
    summary_text = (
        f"There are currently {total_at_hand} coach(es){filter_label} available at hand: "
        f"{total_shop} under attention in work area (shop) and {total_yard} holding in yard (verified from Supabase)."
    )
    
    return {
        "title": f"Coaches Available at Hand{filter_label}",
        "total_count": total_at_hand,
        "shop_count": total_shop,
        "yard_count": total_yard,
        "coaches": all_at_hand,
        "shop_coaches": sorted(list(set(shop_coaches))),
        "yard_coaches": sorted(list(set(yard_coaches))),
        "breakdown": breakdown,
        "answer_summary": summary_text
    }


def tool_get_type_wise_holdings(month: str = "July", year: int = 2026) -> dict:
    """
    Get full type-wise holdings and POH performance summary table for specified month/year from Supabase.
    """
    coaches = fetch_relevant_coaches_from_supabase(month, year)
    targets_list = fetch_supabase_targets_for_month(month, year)
    targets_map = map_targets_to_categories(targets_list)
    
    months_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    m_idx = months_map.get(month.lower(), 7)
    
    ordered_cats = [
        "CN", "GS", "CZ", "SLR", "LWSCN", "LWS", "LWACCN",
        "EMU MC", "EMU TC", "MEMU MC", "MEMU TC",
        "DPC", "DEMU TC", "TW4W", "TW8W", "NMG", "ART", "OR"
    ]
    
    cat_data = {
        cat: {
            "coach_type": cat,
            "target": targets_map.get(cat, 0) if cat != "OR" else "-",
            "physical_despatch": 0,
            "fnd": 0,
            "corrosion_completed": 0,
            "under_attention": 0,
            "in_yard": 0
        }
        for cat in ordered_cats
    }
    
    for c in coaches:
        coach_desc = c.get("coach_desc") or ""
        family = decode_family(coach_desc)
        code = map_coach_desc_to_code(coach_desc, family)
        cat = get_report_category(code, family)
        if not cat or cat not in cat_data:
            continue
            
        status = c.get("status") or ""
        make_packed = c.get("make") or ""
        parts = make_packed.split("||")
        corr_comp = parts[7] if len(parts) > 7 else ""
        desp_date = parts[8] if len(parts) > 8 else ""
        actualdespdate = parts[9] if len(parts) > 9 else ""
        
        dt_corr = _parse_date_local(corr_comp)
        if dt_corr and dt_corr.month == m_idx and dt_corr.year == int(year):
            cat_data[cat]["corrosion_completed"] += 1
            
        final_desp = actualdespdate or desp_date
        dt_desp = _parse_date_local(final_desp)
        
        # If despatched in a different month, skip from active/outturn counts of this month
        if dt_desp and (dt_desp.month != m_idx or dt_desp.year != int(year)):
            continue
            
        if status == "DESPATCHED" or (dt_desp and dt_desp.month == m_idx and dt_desp.year == int(year)):
            if dt_desp and dt_desp.month == m_idx and dt_desp.year == int(year):
                cat_data[cat]["physical_despatch"] += 1
        else:
            pit = c.get("pitnum") or ""
            if is_yard_location(pit):
                cat_data[cat]["in_yard"] += 1
            else:
                cat_data[cat]["under_attention"] += 1
                
    breakdown = []
    tot_target = 0
    tot_phys = 0
    tot_fnd = 0
    tot_corr = 0
    tot_att = 0
    tot_yard = 0
    
    for cat in ordered_cats:
        item = cat_data[cat]
        t_val = item["target"]
        if isinstance(t_val, int):
            tot_target += t_val
            
        tot_phys += item["physical_despatch"]
        tot_fnd += item["fnd"]
        tot_corr += item["corrosion_completed"]
        tot_att += item["under_attention"]
        tot_yard += item["in_yard"]
        
        breakdown.append({
            "Coach Type": cat,
            "Target": t_val,
            "Physical Despatch": item["physical_despatch"],
            "FND": item["fnd"],
            "Corrosion Completed": item["corrosion_completed"],
            "Holding in Shop": item["under_attention"],
            "Holding at Yard": item["in_yard"]
        })
        
    summary_text = (
        f"Type-Wise Holding Report for {month} {year}: "
        f"Total Target = {tot_target}, Physical Despatches = {tot_phys}, FND = {tot_fnd}, "
        f"Corrosion Completed = {tot_corr}, Shop Holding = {tot_att}, Yard Holding = {tot_yard} "
        f"(verified from Supabase)."
    )
    
    return {
        "title": f"Type-Wise Holding & POH Performance ({month} {year})",
        "total_target": tot_target,
        "total_physical_despatch": tot_phys,
        "total_fnd": tot_fnd,
        "total_corrosion_completed": tot_corr,
        "total_shop": tot_att,
        "total_yard": tot_yard,
        "breakdown": breakdown,
        "answer_summary": summary_text
    }


def tool_get_monthly_performance(month: str = "July", year: int = 2026) -> dict:
    """
    Get workshop monthly outturn target vs physical despatch performance from Supabase.
    """
    coaches = fetch_relevant_coaches_from_supabase(month, year)
    targets_list = fetch_supabase_targets_for_month(month, year)
    
    months_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    m_idx = months_map.get(month.lower(), 7)
    
    tot_target = sum(t.get("target_qty", 0) for t in targets_list if t.get("stock_type", "") != "AC LOCO")
    tot_despatch = 0
    outturn_coaches = []
    
    for c in coaches:
        status = c.get("status") or ""
        make_packed = c.get("make") or ""
        parts = make_packed.split("||")
        desp_date = parts[8] if len(parts) > 8 else ""
        actualdespdate = parts[9] if len(parts) > 9 else ""
        
        final_desp = actualdespdate or desp_date
        dt_desp = _parse_date_local(final_desp)
        
        if dt_desp and dt_desp.month == m_idx and dt_desp.year == int(year):
            coach_desc = c.get("coach_desc") or ""
            family = decode_family(coach_desc)
            if family != "LOCO":
                tot_despatch += 1
                outturn_coaches.append(c.get("coachno"))
                
    return {
        "title": f"Workshop Performance Report ({month} {year})",
        "target": tot_target,
        "physical_despatch": tot_despatch,
        "fnd": 0,
        "coaches": sorted(list(set(outturn_coaches))),
        "answer_summary": (
            f"In {month} {year}, workshop physical despatches stand at {tot_despatch} "
            f"coaches against a total target of {tot_target} (verified from Supabase)."
        )
    }


# ---------------------------------------------------------
# Query Processing Engine
# ---------------------------------------------------------

class QueryEngine:
    def __init__(self, api_key=None):
        if not api_key:
            try:
                import config
                api_key = getattr(config, "GEMINI_API_KEY", "")
            except ImportError:
                api_key = ""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        
    def process_query(self, query_text, month="July", year=2026):
        query_text = (query_text or "").strip()
        if not query_text:
            return {
                "query": query_text,
                "answer": "Please enter a question or query.",
                "data": {}
            }
            
        # Try LLM Execution if API key is present
        if self.api_key and HAS_GENAI:
            try:
                return self._process_with_llm(query_text, month, year)
            except Exception as e:
                print(f"LLM Query execution error: {e}, falling back to pattern parser.")
                
        # Fallback to Intent Pattern Parser
        return self._process_with_intent_parser(query_text, month, year)
        
    def _process_with_intent_parser(self, query_text, month, year):
        q_lower = query_text.lower()
        
        # Detect coach types in query
        coach_types = ["CN", "GS", "CZ", "SLR", "LWSCN", "LWS", "LWACCN", "EMU MC", "EMU TC", "MEMU MC", "MEMU TC", "DPC", "DEMU TC", "TW4W", "TW8W", "NMG", "ART", "OR"]
        matched_type = None
        
        # Match longer coach types first
        for ct in sorted(coach_types, key=lambda x: len(x), reverse=True):
            pattern = r'\b' + re.escape(ct.lower()) + r'\b'
            if re.search(pattern, q_lower):
                matched_type = ct
                break

        # 1. Corrosion Queries ("corrosion", "corr", "released", "completed")
        if any(w in q_lower for w in ["corrosion", "corr", "rust"]):
            res = tool_get_corrosion_summary(month, year, coach_type=matched_type)
            return {
                "query": query_text,
                "answer": res["answer_summary"],
                "intent": "corrosion_summary",
                "data": res
            }

        # 2. Coaches at Hand / Availability / Stock Queries ("at hand", "available", "holding", "in shop", "in yard", "under attention", "floor")
        if any(w in q_lower for w in ["at hand", "available", "holding", "stock", "in shop", "in yard", "under attention", "on floor", "present"]):
            res = tool_get_coaches_at_hand(coach_type=matched_type)
            return {
                "query": query_text,
                "answer": res["answer_summary"],
                "intent": "coaches_at_hand",
                "data": res
            }

        # 3. Monthly Outturns / Performance ("outturn", "outturned", "despatch", "despatched", "performance", "target")
        if any(w in q_lower for w in ["outturn", "despatch", "target", "produced"]):
            res = tool_get_monthly_performance(month, year)
            return {
                "query": query_text,
                "answer": res["answer_summary"],
                "intent": "monthly_performance",
                "data": res
            }

        # Default: Full Type-Wise Holdings Summary
        res = tool_get_type_wise_holdings(month, year)
        return {
            "query": query_text,
            "answer": res["answer_summary"],
            "intent": "type_wise_holdings",
            "data": res
        }

    def _process_with_llm(self, query_text, month, year):
        client = genai.Client(api_key=self.api_key)
        
        system_instruction = (
            "You are the LW/PER Workshop Operations Intelligence Assistant. "
            "Use the provided tools to fetch real-time workshop data and answer operational queries accurately. "
            "Always state exact counts and list coach numbers when available. Default report period is July 2026."
        )
        
        tools_map = {
            "tool_get_corrosion_summary": tool_get_corrosion_summary,
            "tool_get_coaches_at_hand": tool_get_coaches_at_hand,
            "tool_get_type_wise_holdings": tool_get_type_wise_holdings,
            "tool_get_monthly_performance": tool_get_monthly_performance,
            "get_corrosion_summary": tool_get_corrosion_summary,
            "get_coaches_at_hand": tool_get_coaches_at_hand,
            "get_type_wise_holdings": tool_get_type_wise_holdings,
            "get_monthly_performance": tool_get_monthly_performance
        }
        
        tools_list = [tool_get_corrosion_summary, tool_get_coaches_at_hand, tool_get_type_wise_holdings, tool_get_monthly_performance]
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=query_text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=tools_list,
                temperature=0.1
            )
        )
        
        if response.function_calls:
            fc = response.function_calls[0]
            func_name = fc.name
            func_args = dict(fc.args) if fc.args else {}
            
            if func_name in tools_map:
                res_data = tools_map[func_name](**func_args)
                return {
                    "query": query_text,
                    "answer": res_data.get("answer_summary", "Query processed."),
                    "intent": func_name,
                    "data": res_data
                }
                
        try:
            answer_text = response.text or "Query processed successfully."
        except Exception:
            answer_text = "Query executed via AI tools."
            
        structured = self._process_with_intent_parser(query_text, month, year)
        structured["answer"] = answer_text
        return structured
