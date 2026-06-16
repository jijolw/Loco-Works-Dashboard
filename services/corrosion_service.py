# =====================================================
# services/corrosion_service.py
# LW/PER Workshop Intelligence System
# Corrosion analysis processing
# =====================================================

import time
import logging
from datetime import datetime, date

from services.erp_service import (
    fetch_master,
    fetch_clean,
    fetch_single,
    fetch_year_built,
    _parse_date,
    _INACTIVE_STATUSES,
)
from services.decoders import (
    decode_repair,
    decode_family,
    decode_division,
    decode_all,
)
from services.live_service import _resolve_division

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import CACHE_TTL_MASTER

logger = logging.getLogger(__name__)

# POH groups ordering
POH_ORDER = ["1st POH", "2nd POH", "3rd POH", "4th & onwards"]

# Skipped repair codes: OR (4) is excluded from corrosion analysis
SKIP_REPAIR_TYPES = {"4"}

# Workshop codes indicating direct delivery from manufacturer
MANUFACTURER_CODES = {"ICF", "RCF", "MCF", "BEML", "CAF", "ALSTOM", "MEDHA"}

# Cache
_corrosion_cache = {}

def _get_cached(key, ttl):
    entry = _corrosion_cache.get(key)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts > ttl:
        return None
    return data

def _set_cached(key, data):
    _corrosion_cache[key] = (time.time(), data)

def corrosion_cache_clear():
    _corrosion_cache.clear()


# =====================================================
# Helper Extraction & Classification logic
# =====================================================

def extract_year_built_from_no(coachno):
    """
    Extract the year of manufacture from the coach number digits.
    In Indian Railways, the first 2 digits of standard coach numbers represent the year.
    For example:
      - 194043 -> 2019
      - 00201  -> 2000
      - 98142  -> 1998
      - X97123 -> 1997
    """
    if not coachno:
        return None
    
    # Strip spaces and collect only digits from the start of the numeric part
    s = str(coachno).strip()
    digits = []
    started = False
    for char in s:
        if char.isdigit():
            digits.append(char)
            started = True
        elif started:
            break
            
    digits_str = "".join(digits)
    if len(digits_str) >= 5:
        try:
            yr_prefix = int(digits_str[:2])
            if yr_prefix >= 50:
                return 1900 + yr_prefix
            else:
                return 2000 + yr_prefix
        except ValueError:
            pass
    return None


def classify_poh_group(coach_age, family):
    """
    Classify POH group from coach age (recd_year - year_built).
    
    LHB schedule: SS2 = 3 yrs, SS3 = 6 yrs, SS2 = 9 yrs, SS3 = 12 yrs...
    ICF schedule: POH occurs every 1.5 years (18 months).
    
    Subtracts 1 from raw age for a conservative floor (December-manufacturing shift).
    """
    if coach_age is None or coach_age < 0:
        return None, "No valid age"

    age = int(coach_age) - 1

    family_upper = str(family).upper().strip()
    if family_upper == "LHB":
        if 2 <= age <= 3:
            return "1st POH", f"age {coach_age} (floor {age})"
        elif age == 4:
            return None, f"age {coach_age} (floor {age}) — borderline"
        elif 5 <= age <= 6:
            return "2nd POH", f"age {coach_age} (floor {age})"
        elif age == 7:
            return None, f"age {coach_age} (floor {age}) — borderline"
        elif 8 <= age <= 9:
            return "3rd POH", f"age {coach_age} (floor {age})"
        elif age == 10:
            return None, f"age {coach_age} (floor {age}) — borderline"
        elif age >= 11:
            return "4th & onwards", f"age {coach_age} (floor {age})"
        else:
            return None, f"age {coach_age} (floor {age}) — too young (<2)"
    else:
        # ICF and other conventional families (POH cycle approx 1.5 years)
        if 0 <= age <= 1:
            return "1st POH", f"age {coach_age} (floor {age})"
        elif 2 <= age <= 3:
            return "2nd POH", f"age {coach_age} (floor {age})"
        elif 4 <= age <= 5:
            return "3rd POH", f"age {coach_age} (floor {age})"
        elif age >= 6:
            return "4th & onwards", f"age {coach_age} (floor {age})"
        else:
            return None, f"age {coach_age} (floor {age}) — too young (<0)"


def poh_number_from_erp(last_poh, last_pohdate_str, year_built, recd_date, coach_age, family):
    """
    Determine the POH number category based on ERP database properties.
    Priority order:
    1. Direct from manufacturer (last_poh is in MANUFACTURER_CODES) -> 1st POH
    2. Using last_pohdate -> compute age at previous POH -> classify previous + 1
    3. Fallback: classify based on age at current receive date
    """
    BLANK = ("", "nan", "None", "0", None)
    lp = str(last_poh).strip().upper() if last_poh else ""

    if lp in MANUFACTURER_CODES:
        return "1st POH", "Manufacturer→1st POH"

    if last_pohdate_str and str(last_pohdate_str).strip() not in BLANK:
        try:
            lpd = _parse_date(last_pohdate_str)
            if lpd and year_built:
                yb = int(year_built)
                age_at_last = lpd.year - yb
                grp, note = classify_poh_group(age_at_last, family)
                if grp:
                    idx = POH_ORDER.index(grp) if grp in POH_ORDER else -1
                    if idx >= 0 and idx < len(POH_ORDER) - 1:
                        return POH_ORDER[idx + 1], f"from last_pohdate ({note})"
                    else:
                        return "4th & onwards", f"from last_pohdate ({note})"
        except Exception:
            pass

    if coach_age is not None:
        grp, note = classify_poh_group(coach_age, family)
        return grp, f"age-based ({note})"

    return None, "Cannot classify"


def fy_from_date(dt):
    """Return the financial year string (e.g. '2025-26') from a datetime object."""
    if not dt:
        return None
    y, m = dt.year, dt.month
    return f"{y}-{str(y+1)[2:]}" if m >= 4 else f"{y-1}-{str(y)[2:]}"


def get_llhw_band(hrs):
    """Map man-hours to Liluah Workshop (LLHW) style corrosion bands."""
    if hrs is None or hrs <= 0:
        return None
    if hrs < 200:
        return "L"
    elif hrs < 500:
        return "LM"
    elif hrs < 1000:
        return "M"
    else:
        return "H"


# =====================================================
# Main Endpoint Service
# =====================================================

def get_corrosion_analysis(fy_list=None, family_filter=None):
    """
    Fetch and build corrosion analysis data for selected financial years.
    
    Parameters
    ----------
    fy_list : list[str], optional
      List of financial years (e.g. ['2025-26']). If None, defaults to current and previous FYs.
    family_filter : str, optional
      Filter by coach family (e.g. 'LHB', 'ICF', 'ALL'). Defaults to 'ALL'.
    """
    cache_key = f"corrosion_fys_{','.join(sorted(fy_list or []))}_fam_{family_filter or 'ALL'}"
    cached = _get_cached(cache_key, CACHE_TTL_MASTER)
    if cached is not None:
        return cached

    now = datetime.now()
    if not fy_list:
        # Default to last 3 financial years
        current_year = now.year
        fy_list = [
            f"{y}-{str(y+1)[2:]}" 
            for y in range(current_year - 2, current_year + 1)
        ]

    family_filter = str(family_filter or "ALL").strip().upper()

    master = fetch_master()
    if not master:
        return {"coaches": [], "metrics": {}}

    enriched = []
    
    for rec in master:
        demandid = rec.get("demandid")
        if not demandid:
            continue

        recd_str = rec.get("recd_date") or rec.get("recddate")
        recd_dt = _parse_date(recd_str)
        if not recd_dt:
            continue

        # Check financial year match
        fy = fy_from_date(recd_dt)
        if fy not in fy_list:
            continue

        coachno = rec.get("coachno", "")
        coach_desc = rec.get("coach_desc", "") or rec.get("coachdesc", "")
        family = decode_family(coach_desc)

        # Skip locomotives
        if family == "LOCO":
            continue

        # Apply Family filter
        if family_filter != "ALL" and family != family_filter:
            continue

        try:
            detail = fetch_single(demandid)
        except Exception as exc:
            logger.warning("fetch_single(%s) failed: %s", demandid, exc)
            continue

        # Skip Condemned/Returned/Bhopal
        status = str(detail.get("status") or detail.get("pohstatus") or "").strip().upper()
        if any(x in status for x in _INACTIVE_STATUSES):
            continue

        # Skip OR repair types
        rt = str(detail.get("repairid") or detail.get("repair_type") or rec.get("repairid") or rec.get("repair_type") or "").strip().upper()
        if rt in SKIP_REPAIR_TYPES or rt == "OR":
            continue

        # Man Hours calculation
        try:
            pre = float(detail.get("presurveyhrs") or 0)
        except (ValueError, TypeError):
            pre = 0.0
        try:
            final = float(detail.get("finalhrs") or 0)
        except (ValueError, TypeError):
            final = 0.0
        
        eff_hrs = final if final > 0 else pre

        # Year built: try master/detail first, fall back to coach number fallback
        cm = fetch_year_built(coachno)
        yb_raw = str(cm.get("year_built", "") or detail.get("year_built", "") or rec.get("year_built", "")).strip()
        make = str(cm.get("make", "") or detail.get("make", "") or rec.get("make", "")).strip()

        db_yb_missing = False
        try:
            yb = int(float(yb_raw))
            if yb < 1980 or yb > now.year:
                yb = None
                db_yb_missing = True
        except (ValueError, TypeError):
            yb = None
            db_yb_missing = True

        # Extract fallback from coach number
        fallback_yb = extract_year_built_from_no(coachno)

        poh_reason = "ERP Database"
        # Override if ERP year build deviates by >= 2 years from coach number extracted year
        if yb is not None and fallback_yb is not None and abs(yb - fallback_yb) >= 2:
            yb = fallback_yb
            poh_reason = "Coach No. Deviation Fallback"
            yb_raw = f"{yb} (Deviation Fallback)"
        elif yb is None:
            yb = fallback_yb
            if yb is not None:
                poh_reason = "Extracted from Coach No."
                yb_raw = f"{yb} (Fallback)"

        # Calculate coach age at time of receive date
        coach_age = recd_dt.year - yb if yb else None

        # Classify POH group
        last_pohdate_raw = str(detail.get("last_pohdate") or "").strip()
        last_poh = detail.get("last_poh", "") or rec.get("last_poh", "")
        poh_grp, classification_detail = poh_number_from_erp(
            last_poh,
            last_pohdate_raw,
            yb,
            recd_dt,
            coach_age,
            family
        )

        poh_reason_full = f"{poh_reason} | {classification_detail}"

        # Resolve corrosion severity band
        band = get_llhw_band(eff_hrs)

        # Division
        dvnid = str(detail.get("dvnid") or rec.get("dvnid") or "").strip()
        if dvnid in ("", "nan", "None", "0"):
            dvnid = str(detail.get("indvnid") or "").strip()
        
        division = decode_division(dvnid)

        # Suspect coaching checks
        suspect_reasons = []
        if db_yb_missing:
            if yb is None:
                suspect_reasons.append("Missing year built completely")
            else:
                suspect_reasons.append("Missing year built in ERP (using fallback from coach no.)")
        
        if yb is not None:
            if yb < 1970 or yb > now.year:
                suspect_reasons.append(f"Invalid year built: {yb}")
        
        if coach_age is not None:
            if coach_age < 0:
                suspect_reasons.append(f"Negative age: {coach_age} years (recd {recd_dt.year}, built {yb})")
            elif coach_age > 35:
                suspect_reasons.append(f"Age outside normal bounds: {coach_age} years")
        else:
            suspect_reasons.append("Coach age could not be computed")

        if not poh_grp:
            suspect_reasons.append("Could not determine POH Group classification")

        if eff_hrs < 0:
            suspect_reasons.append(f"Negative man-hours: {eff_hrs}")
        elif eff_hrs > 3000:
            suspect_reasons.append(f"Extreme man-hours: {eff_hrs} (verify if data entry error)")
            
        if last_pohdate_raw and last_pohdate_raw not in ("", "nan", "None", "0"):
            try:
                lpd = _parse_date(last_pohdate_raw)
                if lpd:
                    if yb and lpd.year < yb:
                        suspect_reasons.append(f"Last POH date ({last_pohdate_raw}) is before year built ({yb})")
                    if lpd.year > now.year:
                        suspect_reasons.append(f"Last POH date in future: {last_pohdate_raw}")
            except Exception:
                pass

        is_suspect = len(suspect_reasons) > 0

        coach = {
            "demandid": demandid,
            "coachno": coachno,
            "coach_desc": coach_desc,
            "family": family,
            "make": make,
            "repair_type": decode_repair(rt),
            "repair_code": rt,
            "division": division,
            "last_poh": last_poh,
            "recd_date": recd_str,
            "fy": fy,
            "year_built": yb,
            "year_built_raw": yb_raw,
            "coach_age": coach_age,
            "poh_group": poh_grp,
            "presurveyhrs": pre,
            "finalhrs": final,
            "effective_hrs": eff_hrs,
            "band": band,
            "last_pohdate": last_pohdate_raw,
            "last_poh_wks": last_poh,
            "poh_reason": poh_reason_full,
            "hrs_source": "Final" if final > 0 else ("Pre" if pre > 0 else "Not Filled"),
            "is_suspect": is_suspect,
            "suspect_reasons": suspect_reasons,
        }

        # Apply standard decode copies
        decode_all(coach, summary_coachno=coachno, summary_desc=coach_desc)
        enriched.append(coach)

    # Build response packet
    result = {
        "coaches": enriched,
        "metrics": {
            "total": len(enriched),
            "with_age": sum(1 for c in enriched if c["coach_age"] is not None),
            "in_poh_group": sum(1 for c in enriched if c["poh_group"] is not None),
            "hours_filled": sum(1 for c in enriched if c["effective_hrs"] > 0),
            "year_built_missing": sum(1 for c in enriched if c["year_built"] is None),
            "suspect_count": sum(1 for c in enriched if c["is_suspect"]),
        }
    }

    _set_cached(cache_key, result)
    logger.info(
        "get_corrosion_analysis: processed %d coaches for FYs %s",
        len(enriched), fy_list,
    )
    return result
