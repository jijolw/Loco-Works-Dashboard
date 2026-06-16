# =====================================================
# services/topology.py
# LW/PER Workshop Intelligence System
# Workshop layout data — pit lines, zones, and topology
# =====================================================

"""
Defines the physical layout of LW/PER workshop for the aerial view.
Each entry in LAYOUT represents a visual row in the workshop diagram.

Row types
---------
- shop   : a pit line with named slots
- flat   : a wide area (e.g. paint shop, bogie shop)
- traverser : the traverser between bays
- stack  : multiple sub-rows grouped visually
- placeholder : empty filler for alignment
"""

# ── Zone visual styles (for frontend rendering) ──────
ZONE_STYLES = {
    "PS":  {"bg": "#FFEFD5", "border": "#E8A317"},   # Paint Shop
    "SY":  {"bg": "#E6F3E6", "border": "#228B22"},   # Shell / Body
    "AS":  {"bg": "#E6E6FA", "border": "#6A5ACD"},   # Augmentation
    "DM":  {"bg": "#FFFACD", "border": "#DAA520"},   # DEMU
    "LCB": {"bg": "#E0F0FF", "border": "#4682B4"},   # Light Coach Bay
    "HCB": {"bg": "#FFE4E1", "border": "#CD5C5C"},   # Heavy Coach Bay
    "AC":  {"bg": "#F0FFF0", "border": "#2E8B57"},   # AC Bay
    "OT":  {"bg": "#F5F5F5", "border": "#808080"},   # Other / Yard
}

ZONE_NAMES = {
    "PS":  "Paint Shop",
    "SY":  "Shell / Body Shop",
    "AS":  "Augmentation Shop",
    "DM":  "DEMU Shop",
    "LCB": "Light Coach Bay",
    "HCB": "Heavy Coach Bay",
    "AC":  "AC Bay",
    "OT":  "Other",
}

# ── Pit line orders (west → east within each shop) ───
PAINT_ORDER = ["PS/P2", "PS/L2", "PS/L1", "PS/P1"]
LBR_ORDER   = ["SY/WP", "SY/L4", "SY/L3", "SY/L2", "SY/P1", "SY/L1"]
AUG_ORDER   = ["AS/L6", "AS/L5", "AS/P4", "AS/P3", "AS/P2", "AS/L1"]

DEMU_WASH_ORDER = ["DM/B"]
DEMU_ORDER      = ["DM/L32A", "DM/L32", "DM/L31", "DM/L30", "DM/L29", "DM/L28", "DM/L27"]

CENTRAL_LINE_PITNUMS      = ["DM/C"]
CENTRAL_LINE_PITNUMS_EAST = ["LCB/C"]

LCB_ORDER = ["LCB/L16A", "LCB/L16", "LCB/L15", "LCB/P14", "LCB/L13", "LCB/L12", "LCB/L11"]
HCB_ORDER = ["HCB/L26", "HCB/L25", "HCB/L24", "HCB/L23", "HCB/L22", "HCB/L21", "HCB/L20", "HCB/L19", "HCB/L18", "HCB/L17"]
AC_ORDER  = ["ACB/P10", "ACB/P9", "ACB/L8", "ACB/L7", "ACB/L6", "ACB/L5", "ACB/L4", "ACB/L3", "ACB/L2", "ACB/L1"]

# ── Special locations ────────────────────────────────
INCOMING_PITNUMS = ["OT/IN"]
DESPATCH_PITNUMS = ["HCB/DESP", "OT/DESP", "DESP"]
YARD_PITNUMS     = ["OT/YD"]

# ── Lines that hold two coaches per slot ─────────────
TWO_SLOT_LINES = {
    "PS/P2", "PS/L2", "PS/L1", "PS/P1",
    "SY/WP", "SY/P1", "SY/L4", "SY/L3", "SY/L2", "SY/L1",
    "AS/L6", "AS/L5", "AS/P4", "AS/P3", "AS/P2", "AS/L1",
}

# ── Pit number aliases (display overrides) ───────────
PITNUM_ALIASES = {
    "SY/P2_1": "SY/P1",
    "DM/BL": "DM/B",
}

# ── Master layout definition ────────────────────────
# Each item in LAYOUT represents one visual row.
# The frontend iterates this to build the workshop map.
LAYOUT = [
    # === INCOMING / YARD ===
    {
        "type": "shop",
        "zone": "OT",
        "label": "Incoming",
        "pits": INCOMING_PITNUMS,
    },
    {
        "type": "shop",
        "zone": "OT",
        "label": "Yard",
        "pits": YARD_PITNUMS,
    },
    # === TRAVERSER (West) ===
    {
        "type": "traverser",
        "zone": "OT",
        "label": "Traverser (West)",
    },
    # === PAINT SHOP ===
    {
        "type": "shop",
        "zone": "PS",
        "label": "Paint Shop",
        "pits": PAINT_ORDER,
    },
    # === TRAVERSER (between Paint & Shell) ===
    {
        "type": "traverser",
        "zone": "OT",
        "label": "Traverser",
    },
    # === SHELL / BODY (LBR) ===
    {
        "type": "shop",
        "zone": "SY",
        "label": "Shell / Body Shop",
        "pits": LBR_ORDER,
    },
    # === TRAVERSER (between Shell & Aug) ===
    {
        "type": "traverser",
        "zone": "OT",
        "label": "Traverser",
    },
    # === AUGMENTATION ===
    {
        "type": "shop",
        "zone": "AS",
        "label": "Augmentation Shop",
        "pits": AUG_ORDER,
    },
    # === TRAVERSER (between Aug & DEMU) ===
    {
        "type": "traverser",
        "zone": "OT",
        "label": "Traverser",
    },
    # === DEMU WASH ===
    {
        "type": "shop",
        "zone": "DM",
        "label": "DEMU Wash",
        "pits": DEMU_WASH_ORDER,
    },
    # === DEMU SHOP ===
    {
        "type": "shop",
        "zone": "DM",
        "label": "DEMU Shop",
        "pits": DEMU_ORDER,
    },
    # === CENTRAL LINE (West) ===
    {
        "type": "shop",
        "zone": "DM",
        "label": "Central Line",
        "pits": CENTRAL_LINE_PITNUMS,
    },
    # === CENTRAL LINE (East) ===
    {
        "type": "shop",
        "zone": "LCB",
        "label": "Central Line (East)",
        "pits": CENTRAL_LINE_PITNUMS_EAST,
    },
    # === LCB ===
    {
        "type": "shop",
        "zone": "LCB",
        "label": "Light Coach Bay",
        "pits": LCB_ORDER,
    },
    # === TRAVERSER (between LCB & HCB) ===
    {
        "type": "traverser",
        "zone": "OT",
        "label": "Traverser",
    },
    # === HCB ===
    {
        "type": "shop",
        "zone": "HCB",
        "label": "Heavy Coach Bay",
        "pits": HCB_ORDER,
    },
    # === TRAVERSER (between HCB & AC) ===
    {
        "type": "traverser",
        "zone": "OT",
        "label": "Traverser",
    },
    # === AC BAY ===
    {
        "type": "shop",
        "zone": "AC",
        "label": "AC Bay",
        "pits": AC_ORDER,
    },
    # === DESPATCH ===
    {
        "type": "shop",
        "zone": "OT",
        "label": "Despatch",
        "pits": DESPATCH_PITNUMS,
    },
]

# ── Collect every known pit prefix for validation ────
ALL_PIT_PREFIXES = set()
for row in LAYOUT:
    if row["type"] == "shop":
        for pit in row.get("pits", []):
            prefix = pit.split("/")[0] if "/" in pit else pit
            ALL_PIT_PREFIXES.add(prefix)
