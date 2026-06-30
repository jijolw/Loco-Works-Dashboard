# =====================================================
# services/topology.py
# Workshop Geography & Pit Line Definitions
# LW/PER — Perambur Loco Works
# =====================================================

# ── Zone visual styles (for frontend rendering) ──────
ZONE_STYLES = {
    "PAINT":        "paint",
    "LBR":          "lbr",
    "INCOMING":     "incoming",
    "SPRING":       "spring",
    "AUG":          "aug",
    "DEMU_WASH":    "demu-wash",
    "DEMU":         "demu",
    "STABLING":     "stabling",
    "LCB":          "lcb",
    "CENTRAL_WEST": "hcb",
    "CENTRAL_EAST": "lcb",
    "HCB":          "hcb",
    "AC":           "ac",
    "DESP":         "desp",
    "YARD":         "yard",
}

ZONE_NAMES = {
    "PAINT":        "PAINT SHOP",
    "LBR":          "LBR SHED",
    "INCOMING":     "INCOMING LINE",
    "SPRING":       "SPRING WASHING",
    "AUG":          "AUGMENTED SHOP",
    "DEMU_WASH":    "DEMU WASH (B LINE)",
    "DEMU":         "DEMU SHOP",
    "STABLING":     "STABLING LINES",
    "LCB":          "LCB (LIGHT CORROSION BAY)",
    "CENTRAL_WEST": "CENTRAL LINE (DM/C)",
    "CENTRAL_EAST": "CENTRAL LINE (LCB/C)",
    "HCB":          "HCR (HEAVY CORROSION SHOP)",
    "AC":           "AC LOCO BAY",
    "DESP":         "DESPATCH LINE",
    "YARD":         "YARD / OT",
}

# ── Pit line orders (west → east within each shop) ───
PAINT_ORDER = [
    "PS/P2",
    "PS/L2",
    "PS/L1",
    "PS/P1",
]

LBR_ORDER = [
    "LBR/WP",
    "LBR/L4",
    "LBR/L3",
    "LBR/L2",
    "LBR/P1",
    "LBR/L1",
]

AUG_ORDER = [
    "AS/L6",
    "AS/L5",
    "AS/P4",
    "AS/P3",
    "AS/P2",
    "AS/L1",
]

DEMU_WASH_ORDER = [
    "DM/B",
]

DEMU_ORDER = [
    "DM/L32A",
    "DM/L32",
    "DM/L31",
    "DM/L30",
    "DM/L29",
    "DM/L28",
    "DM/L27",
]

CENTRAL_LINE_PITNUMS = ["DM/C"]
CENTRAL_LINE_PITNUMS_EAST = ["LCB/C"]

LCB_ORDER = [
    "LCB/L16A",
    "LCB/L16",
    "LCB/L15",
    "LCB/P14",
    "LCB/L13",
    "LCB/L12",
    "LCB/L11",
]

HCB_ORDER = [
    "HCB/L26",
    "HCB/L25",
    "HCB/L24",
    "HCB/L23",
    "HCB/L22",
    "HCB/L21",
    "HCB/L20",
    "HCB/L19",
    "HCB/L18",
    "HCB/L17",
]

AC_ORDER = [
    "ACB/P10",
    "ACB/P9",
    "ACB/L8",
    "ACB/L7",
    "ACB/L6",
    "ACB/L5",
    "ACB/L4",
    "ACB/L3",
    "ACB/L2",
    "ACB/L1",
]

INCOMING_PITNUMS = ["OT/IN"]
DESPATCH_PITNUMS = ["HCB/DESP", "OT/DESP", "DESP"]
YARD_PITNUMS = ["OT/YD"]

# ── Lines that hold two coaches per slot ─────────────
TWO_SLOT_LINES = {
    "PS/P2", "PS/L2", "PS/L1", "PS/P1",
    "LBR/WP", "LBR/P1", "LBR/L4", "LBR/L3", "LBR/L2", "LBR/L1",
    "AS/L6", "AS/L5", "AS/P4", "AS/P3", "AS/P2", "AS/L1",
}

# ── Pit number aliases (display overrides) ───────────
PITNUM_ALIASES = {
    "LBR/P2_1": "LBR/P1",
    "LBR/P2_2": "LBR/P1",
    "LBR/P2": "LBR/P1",
    "DM/BL": "DM/B",
}

# ── Master layout definition ────────────────────────
LAYOUT = [
    # Row 1: Paint | Traverser | LBR
    {
        "type":  "row",
        "cols":  [5, 1, 5],
        "zones": [
            {"type": "shop", "zone": "PAINT", "order": PAINT_ORDER},
            {"type": "traverser", "label": "TRAVERSER\nBAY"},
            {"type": "shop", "zone": "LBR",   "order": LBR_ORDER},
        ]
    },

    # Incoming line (full width)
    {
        "type":     "flat",
        "zone":     "INCOMING",
        "pitnums":  INCOMING_PITNUMS,
    },

    # Row 2: Spring+DEMUwash | Traverser | Augmented
    {
        "type":  "row",
        "cols":  [5, 1, 5],
        "zones": [
            {"type": "stack", "zones": [
                {"type": "spring_placeholder", "zone": "SPRING"},
                {"type": "shop", "zone": "DEMU_WASH", "order": DEMU_WASH_ORDER},
            ]},
            {"type": "traverser", "label": "TRAVERSER\nBAY"},
            {"type": "shop", "zone": "AUG", "order": AUG_ORDER},
        ]
    },

    # Row 3: DEMU | Traverser | Stabling+LCB
    {
        "type":  "row",
        "cols":  [5, 1, 5],
        "zones": [
            {"type": "shop", "zone": "DEMU", "order": DEMU_ORDER},
            {"type": "traverser", "label": "TRAVERSER\nBAY\n(VACANT)"},
            {"type": "stack", "zones": [
                {"type": "stabling_placeholder", "zone": "STABLING"},
                {"type": "shop", "zone": "LCB", "order": LCB_ORDER},
            ]},
        ]
    },

    # Central Line — DM/C (west) and LCB/C (east)
    {
        "type":  "row",
        "cols":  [5, 5],
        "zones": [
            {"type": "flat", "zone": "CENTRAL_WEST", "pitnums": CENTRAL_LINE_PITNUMS},
            {"type": "flat", "zone": "CENTRAL_EAST", "pitnums": CENTRAL_LINE_PITNUMS_EAST},
        ]
    },

    # Row 4: HCB | AC (half width each)
    {
        "type":  "row",
        "cols":  [5, 5],
        "zones": [
            {"type": "shop", "zone": "HCB", "order": HCB_ORDER},
            {"type": "shop", "zone": "AC",  "order": AC_ORDER},
        ]
    },

    # Despatch line (full width)
    {
        "type":    "flat",
        "zone":    "DESP",
        "pitnums": DESPATCH_PITNUMS,
    },

    # Yard (full width)
    {
        "type":    "flat",
        "zone":    "YARD",
        "pitnums": YARD_PITNUMS,
    },
]

# ── Collect every known pit prefix for validation ────
ALL_PIT_PREFIXES = (
    PAINT_ORDER
    + LBR_ORDER
    + AUG_ORDER
    + DEMU_WASH_ORDER
    + DEMU_ORDER
    + CENTRAL_LINE_PITNUMS
    + CENTRAL_LINE_PITNUMS_EAST
    + LCB_ORDER
    + HCB_ORDER
    + AC_ORDER
    + INCOMING_PITNUMS
    + DESPATCH_PITNUMS
    + YARD_PITNUMS
)
