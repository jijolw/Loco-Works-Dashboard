# =====================================================
# services/decoders.py
# LW/PER Workshop Intelligence System
# Central mapping & decoder functions
# =====================================================

"""
Maps raw ERP codes to human-readable labels.
All decode functions return a string; unknown codes fall back
to the raw value or a sensible default.
"""

# ── Repair-type map (repairid → label) ────────────────
REPAIR_MAP = {
    "1": "POH",
    "3": "IOH",
    "4": "OR",
    "5": "POH/CORR-MLR",
    "6": "POH/CORR-RF",
    "7": "POH/CORR",
    "104": "SS1",
    "121": "SS2",
    "122": "SS3",
    "141": "POH+CONV",
    "181": "NMGHS/CONV",
    "182": "NMGH/POH",
    "201": "ART/Conv",
    "241": "SS3-POH",
    "242": "SS3-POH/CORR",
    "243": "SS2-POH",
    "244": "SS2-POH/CORR",
}

# ── Division map (dvnid → division name) ─────────────
DIVISION_MAP = {
    "TVC": "Trivandrum",
    "MAS": "Chennai",
    "PGT": "Palakkad",
    "SA": "Salem",
    "TPJ": "Tiruchchirappalli",
    "MDU": "Madurai",
    "MAQ": "Mangalore",
    "NCJ": "Nagercoil",
    "ED": "Erode",
    "CBE": "Coimbatore",
    "SRR": "Shoranur",
    "VM": "Villupuram",
    "SC": "Secunderabad",
    "JP": "Jaipur",
    "GOC": "Golden Rock",
}

# ── Workshop map (wkid → workshop label) ─────────────
WORKSHOP_MAP = {
    "PWL": "LW/PER",
    "PWP": "CW/PER",
    "GOC": "GOC",
    "ICF": "ICF",
    "AVD": "AVD",
}

# ── Family map (coach_desc prefix → family) ──────────
# UPDATED — user-confirmed 2026-05-30
FAMILY_MAP = {
    # ICF family
    "CN":      "ICF",
    "GS":      "ICF",
    "CZ":      "ICF",
    "SLR":     "ICF",
    "CZJ":     "ICF",
    "GSLRD":   "ICF",
    "GSRD":    "ICF",
    "CZRJ":    "ICF",
    "WCB":     "ICF",
    "TC":      "DEMU",

    # LHB family
    "LWSCN":   "LHB",
    "LWACCN":  "LHB",
    "LWS":     "LHB",
    "LWSCZ":   "LHB",
    "LWACCW":  "LHB",
    "LS5":     "LHB",
    "LS":      "LHB",
    "LWSCNA":  "LHB",
    "LWFCWAC": "LHB",
    "LWCBAC":  "LHB",
    "LSLRD":   "LHB",
    "LSCN":    "LHB",
    "LVPH":    "LHB",

    # NMG family
    "NMG":     "NMG",
    "NMGHS":   "NMG",
    "NMGH":    "NMG",
    "NMGHS_Conv": "NMG",
    "NMGHSR":  "NMG",

    # DEMU family
    "DEMU":    "DEMU",
    "DEMUTC":  "DEMU",
    "DPC":     "DEMU",
    "DTC":     "DEMU",
    "DTCS":    "DEMU",

    # TW family
    "TW":      "TW",
    "TW4W":    "TW",
    "TW8W":    "TW",

    # MEMU family
    "MEMUTC":  "MEMU",
    "MEMUMC":  "MEMU",

    # EMU family
    "YSY":     "EMU",
    "YSD":     "EMU",
    "YFSY":    "EMU",
    "YZZS":    "EMU",
    "DMSC":    "EMU",

    # VB family
    "TSMC":    "VB",
    "TSMC2":   "VB",
    "TSTC":    "VB",
    "TSDTC":   "VB",
    "TSNDTC":  "VB",
    "TSNDTC2": "VB",

    # SPECIAL family
    "ART":     "SPECIAL",
    "ARMV":    "SPECIAL",
    "SPART":   "SPECIAL",
    "SPIC":    "SPECIAL",
    "ARTConv": "SPECIAL",
    "VPH":     "SPECIAL",
    "VPU":     "SPECIAL",

    # LOCO family
    "WAP4":    "LOCO",
    "WAP7":    "LOCO",
    "WAG7":    "LOCO",

    # OTHER family
    "RS":      "OTHER",
    "RHV":     "OTHER",
    "RTTV":    "OTHER",
    "RTSV":    "OTHER",
    "RTRH":    "OTHER",
    "RH":      "OTHER",
    "RR":      "OTHER",
    "MFD":     "OTHER",
    "WDS":     "OTHER",
    "BOGIE":   "OTHER",
    "BOXN":    "OTHER",
    "CAMPING": "OTHER",
}

# Build a sorted list of prefixes longest-first for greedy matching
_FAMILY_PREFIXES = sorted(FAMILY_MAP.keys(), key=len, reverse=True)

# ── Corrosion severity ────────────────────────────────
CORROSION_MAP = {"H": "HEAVY", "L": "LIGHT"}

# ── Hours threshold for highlighting ─────────────────
HRS_THRESHOLD = 500


# =====================================================
# Decode functions
# =====================================================

def decode_repair(code):
    """Convert repair-type ID to label. Returns raw code if unknown."""
    if code is None:
        return ""
    return REPAIR_MAP.get(str(code).strip(), str(code).strip())


def decode_division(code):
    """Convert division ID to full name. Returns raw code if unknown."""
    if code is None:
        return ""
    return DIVISION_MAP.get(str(code).strip(), str(code).strip())


def decode_workshop(code):
    """Convert workshop ID to label. Returns raw code if unknown."""
    if code is None:
        return ""
    return WORKSHOP_MAP.get(str(code).strip(), str(code).strip())


def decode_family(coach_desc):
    """
    Determine coach family from the coach description string.
    Uses longest-prefix-first matching against FAMILY_MAP keys.
    Returns 'OTHER' if no match is found.
    """
    if not coach_desc:
        return "OTHER"
    desc = str(coach_desc).strip().upper()
    # Try each prefix (longest first) for a greedy match
    for prefix in _FAMILY_PREFIXES:
        if desc.upper().startswith(prefix.upper()):
            return FAMILY_MAP[prefix]
    return "OTHER"


def decode_corrosion(code):
    """Convert corrosion severity code (H/L) to label."""
    if code is None:
        return ""
    return CORROSION_MAP.get(str(code).strip().upper(), str(code).strip())


def decode_hrs_category(hrs):
    """
    Categorise hours worked as 'HIGH' (≥ threshold) or 'NORMAL'.
    Returns empty string for None/invalid input.
    """
    if hrs is None:
        return ""
    try:
        return "HIGH" if float(hrs) >= HRS_THRESHOLD else "NORMAL"
    except (ValueError, TypeError):
        return ""


def effective_hours(presurveyhrs, finalhrs):
    """
    Return the best available hours figure.
    Prefers finalhrs; falls back to presurveyhrs.
    """
    if finalhrs is not None and str(finalhrs).strip() != "":
        try:
            return float(finalhrs)
        except (ValueError, TypeError):
            pass
    if presurveyhrs is not None and str(presurveyhrs).strip() != "":
        try:
            return float(presurveyhrs)
        except (ValueError, TypeError):
            pass
    return None


def hrs_source(presurveyhrs, finalhrs):
    """
    Indicate which hours field was used.
    Returns 'FINAL', 'PRESURVEY', or 'NONE'.
    """
    if finalhrs is not None and str(finalhrs).strip() != "":
        try:
            float(finalhrs)
            return "FINAL"
        except (ValueError, TypeError):
            pass
    if presurveyhrs is not None and str(presurveyhrs).strip() != "":
        try:
            float(presurveyhrs)
            return "PRESURVEY"
        except (ValueError, TypeError):
            pass
    return "NONE"


def decode_all(d, summary_coachno=None, summary_desc=None):
    """
    Apply all decoders to a single coach dict *in place*.

    Parameters
    ----------
    d : dict
        The raw coach record from ERP.
    summary_coachno : str, optional
        Override coach number (for summary views).
    summary_desc : str, optional
        Override coach description (for summary views).

    Returns
    -------
    dict
        The same dict, enriched with decoded fields.
    """
    coachno = summary_coachno or d.get("coachno", "")
    desc = summary_desc or d.get("coach_desc", "") or d.get("coachdesc", "")

    # Decoded fields
    repair_val = d.get("repairid") or d.get("repair_type") or d.get("repairtype")
    d["repair_label"] = decode_repair(repair_val)
    d["division_label"] = decode_division(d.get("dvnid"))
    d["workshop_label"] = decode_workshop(d.get("wkid"))
    d["family"] = decode_family(desc)

    # Resolve corrosion severity (can be in corrosion, corr_repair, or curheavylow)
    corr_val = d.get("corrosion")
    if not corr_val:
        corr_val = d.get("corr_repair")
    if not corr_val:
        corr_val = d.get("curheavylow")
    d["corrosion_label"] = decode_corrosion(corr_val) if corr_val else ""

    # Hours
    pre = d.get("presurveyhrs")
    fin = d.get("finalhrs")
    d["eff_hours"] = effective_hours(pre, fin)
    d["hrs_source"] = hrs_source(pre, fin)
    d["hrs_category"] = decode_hrs_category(d["eff_hours"])

    # Convenience copies for frontend
    d["coachno"] = coachno
    d["coach_desc"] = desc
    d["effective_hours"] = d["eff_hours"]
    d["man_hours"] = d["eff_hours"]

    return d
