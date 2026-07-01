# =====================================================
# services/pdf_service.py
# In-memory PDF report generator using ReportLab
# =====================================================

import io
import pandas as pd
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from services.aerial_service import get_aerial_data
from services.erp_service import fetch_master, _parse_date

# ---------------------------------------------------------------------------
# TOPOLOGY & CONFIG
# ---------------------------------------------------------------------------
PAINT_ORDER = ["PS/P2", "PS/L2", "PS/L1", "PS/P1"]
LBR_ORDER = [
    ("LBR/WP",  "LBR Pit 2"),
    ("LBR/L4",  "LBR/L4"),
    ("LBR/L3",  "LBR/L3"),
    ("LBR/L2",  "LBR/L2"),
    ("LBR/P1",  "LBR Pit 1"),
    ("LBR/L1",  "LBR/L1"),
]
AUG_ORDER = ["AS/L6", "AS/L5", "AS/P4", "AS/P3", "AS/P2", "AS/L1"]
DEMU_WASH = ["DM/B"]
DEMU_ORDER = ["DM/L32A", "DM/L32", "DM/L31", "DM/L30", "DM/L29", "DM/L28", "DM/L27", "DM/C"]
LCB_ORDER = ["LCB/L16A", "LCB/L16", "LCB/L15", "LCB/P14", "LCB/L13", "LCB/L12", "LCB/L11", "LCB/C"]
HCB_ORDER = ["HCB/L26", "HCB/L25", "HCB/L24", "HCB/L23", "HCB/L22",
             "HCB/L21", "HCB/L20", "HCB/L19", "HCB/L18", "HCB/L17"]
AC_ORDER = ["ACB/P10", "ACB/P9", "ACB/L8", "ACB/L7", "ACB/L6",
            "ACB/L5", "ACB/L4", "ACB/L3", "ACB/L2", "ACB/L1"]

PITNUM_ALIASES = {
    "LBR/P2_1": "LBR/P1",
    "LBR/P2_2": "LBR/P1",
    "LBR/P2":   "LBR/P1",
    "YD/YD":    "OT/YD",
    "DM/BL":    "DM/B",
}

TWO_SLOT_LINES = {
    "PS/P2", "PS/L2", "PS/L1", "PS/P1",
    "LBR/WP", "LBR/P1", "LBR/L4", "LBR/L3", "LBR/L2", "LBR/L1",
    "AS/L6", "AS/L5", "AS/P4", "AS/P3", "AS/P2", "AS/L1",
}

EXCLUDED_COACHES = {
    "190027",
}

SHOPS = [
    ("PAINT SHOP", PAINT_ORDER, "#9B2226"),
    ("LBR SHED", LBR_ORDER, "#1B4F72"),
    ("AUGMENTED SHOP", AUG_ORDER, "#6C3483"),
    ("DEMU WASH (B LINE)", DEMU_WASH, "#7D5A1E"),
    ("DEMU SHOP", DEMU_ORDER, "#117864"),
    ("LCB (LIGHT CORROSION BAY)", LCB_ORDER, "#1A5276"),
    ("HCR (HEAVY CORROSION SHOP)", HCB_ORDER, "#7B241C"),
    ("AC LOCO BAY", AC_ORDER, "#4A235A"),
]

FLAT_LINES = [
    ("INCOMING LINE", ["OT/IN"], "#145A32"),
    ("DESPATCH LINE", ["HCB/DESP", "OT/DESP", "DESP"], "#9C640C"),
    ("YARD / OT", ["OT/YD"], "#145A32"),
]

# Color codes
GREEN      = "#1A6B2F"   # outturn taken
DARK       = "#222222"   # corrosion completed
GREY       = "#444444"   # normal process
BLUE       = "#0066CC"   # tomorrow's plan
ORANGE     = "#A04000"   # today's plan

def _clean_cno(val):
    val_str = str(val).strip().upper()
    digits = "".join([c for c in val_str if c.isdigit()])
    if len(digits) >= 4:
        return digits
    return val_str

BG_OUTTURN      = "#FFD700"   # yellow
BG_CORR         = "#FFF9C4"   # light yellow
BG_PLAN         = "#B3D9FF"   # blue
BG_TODAY_PLAN   = "#FDEBD0"   # light orange
BG_NORMAL       = "#FFFFFF"   # white

BODY_BG    = "#FFFFFF"
GRID_COLOR = "#BBBBBB"
EMPTY_COLOR = "#888888"
AC_LOCO_TITLE = "AC LOCO BAY"
# Column headers shared by every pit's body rows
MINI_TABLE_HEADERS = ("Coach No / Code", "Div / TFR / Corr In", "Days", "D.PDC/C.PDC", "Hrs")
PRE_ONLY_HEADERS    = ("Coach No / Code", "Hrs")

# ReportLab styles setup
styles = getSampleStyleSheet()
cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=9, leading=11, textColor=colors.black)
label_style = ParagraphStyle("label", parent=styles["Normal"], fontSize=6.5, leading=8,
                              textColor=colors.HexColor("#1A6B2F"), fontName="Helvetica-Bold", alignment=1)
tiny_style = ParagraphStyle("tiny", parent=styles["Normal"], fontSize=7, leading=8, textColor=colors.black)
tiny_header_style = ParagraphStyle("tiny_hdr", parent=styles["Normal"], fontSize=7, leading=8.5,
                                    textColor=colors.black, fontName="Helvetica-Bold", alignment=1)
_TINY_SUB = ParagraphStyle("tiny_sub", parent=styles["Normal"], fontSize=5.5, leading=6.5, textColor=colors.black)
_TINY_SUB_W = ParagraphStyle("tiny_sub_w", parent=styles["Normal"], fontSize=5.5, leading=6.5, textColor=colors.white)

# ---------------------------------------------------------------------------
# DATA LOADERS & DATA MAPPING
# ---------------------------------------------------------------------------

def load_data() -> pd.DataFrame:
    """Construct a pandas DataFrame matching generate_aerial_pdf's format from live cached data."""
    data = get_aerial_data()
    coaches = data.get("coaches", [])
    ac_locos = data.get("ac_locos", [])
    
    rows = []
    for c in coaches:
        rows.append({
            "coachno": str(c.get("coachno", "")).strip(),
            "coach_desc": str(c.get("coach_desc", "") or c.get("family", "")).strip(),
            "pitnum": str(c.get("pitnum", "")).strip().upper(),
            "recd_date": c.get("recd_date", ""),
            "desp_date": c.get("desp_date", ""),
            "corr_comp": c.get("corr_comp", ""),
            "pdc_date": c.get("pdc_date", ""),
            "presurveyhrs": c.get("corrosion_hours") if (c.get("corrosion_hours") is not None and str(c.get("corrosion_hours")).strip() not in ("", "None", "nan")) else c.get("presurveyhrs", ""),
            "dvnid": c.get("dvnid", "") or c.get("division", ""),
            "tfr": c.get("tfr_date", "") or c.get("tfr", ""),
            "corr_place": c.get("corr_place", ""),
            "plan_date": c.get("plan_date", ""),
            "corrpd": c.get("corrpd", ""),
            "actualdespdate": c.get("actualdespdate", ""),
            "caldays": c.get("IN_DAYS", "—"),
            "wisecd": c.get("wisecd", ""),
            "wisewd": c.get("wisewd", ""),
            "lowering_status": c.get("lowering_status", ""),
            "furnishing_status": c.get("furnishing_status", ""),
            "despatch_status": c.get("despatch_status", ""),
            "google_remarks": c.get("google_remarks", "") or c.get("remarks", "")
        })
        
    for l in ac_locos:
        rows.append({
            "coachno": str(l.get("loco_no", "")).strip(),
            "coach_desc": str(l.get("loco_desc", "") or "WAP7").strip(),
            "pitnum": str(l.get("pitnum", "")).strip().upper(),
            "recd_date": l.get("date_recd", ""),
            "desp_date": "",
            "corr_comp": "",
            "pdc_date": "",
            "presurveyhrs": "",
            "dvnid": l.get("shed", "") or l.get("division", ""),
            "tfr": l.get("tfr", ""),
            "corr_place": "",
            "plan_date": "",
            "corrpd": "",
            "actualdespdate": "",
            "caldays": l.get("IN_DAYS", "—"),
            "wisecd": "",
            "wisewd": ""
        })
        
    df = pd.DataFrame(rows)
    if not df.empty:
        # Apply PITNUM_ALIASES and drop exclusions
        df["pitnum"] = df["pitnum"].map(lambda p: PITNUM_ALIASES.get(p, p))
        df = df[~df["coachno"].isin(EXCLUDED_COACHES)]
        df = df.drop_duplicates(subset=["coachno"], keep="first")
    return df

def load_despatch_data() -> pd.DataFrame:
    """Fetch recently despatched coaches in the last 7 days from the master list."""
    raw = fetch_master()
    cutoff = datetime.now() - timedelta(days=7)
    rows = []
    
    for rec in raw:
        dd_str = str(rec.get("desp_date") or "").strip()
        aad_str = str(rec.get("actualdespdate") or "").strip()
        status_erp = str(rec.get("status") or "").strip().upper()
        
        make_raw = str(rec.get("make") or "").strip()
        if "||" in make_raw:
            parts = make_raw.split("||")
            if len(parts) > 8 and not dd_str:
                dd_str = parts[8]
            if len(parts) > 9 and not aad_str:
                aad_str = parts[9]
                
        keep = False
        for date_str in (dd_str, aad_str):
            if date_str and date_str.lower() not in ("none", "null", "nan", ""):
                dt = _parse_date(date_str)
                if dt and dt >= cutoff:
                    keep = True
                    break
                    
        if keep:
            item = dict(rec)
            item["desp_date"] = dd_str
            item["actualdespdate"] = aad_str
            item["plan_date"] = rec.get("plan_date") or ""
            recd_str = rec.get("recd_date") or ""
            recd_dt = _parse_date(recd_str)
            item["caldays"] = str((datetime.now() - recd_dt).days) if recd_dt else "—"
            rows.append(item)
            
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# ---------------------------------------------------------------------------
# FORMATTERS & STATUS HELPERS
# ---------------------------------------------------------------------------

def _val(x):
    s = str(x).strip()
    return s if s and s not in ("nan", "None") else "—"

def fmt_date(val):
    if not val or str(val) in ("", "nan", "None"):
        return "—"
    try:
        d = pd.to_datetime(val, errors="coerce", dayfirst=True)
        if pd.isna(d):
            return str(val)[:10]
        return d.strftime("%d/%m")
    except:
        return str(val)[:5]

def fmt_days(val):
    if not val or str(val) in ("", "nan", "None"):
        return "—"
    try:
        return str(int(float(val)))
    except:
        return str(val)

def format_stage_status(val) -> str:
    if not val or str(val).strip() in ("", "nan", "None", "—"):
        return '<font color="#A04000"><b>Pending</b></font>'
    s = str(val).strip().lower()
    if s in ("pending", "no", "false", "null", "0"):
        return '<font color="#A04000"><b>Pending</b></font>'
    if s in ("completed", "complete", "done", "yes", "y", "comp"):
        return '<font color="#1A6B2F"><b>Completed</b></font>'
    return f'<font color="#1A6B2F"><b>{str(val).strip()}</b></font>'

def _get_ist_today() -> pd.Timestamp:
    try:
        return pd.Timestamp.now(tz='Asia/Kolkata').tz_localize(None).normalize()
    except:
        return pd.Timestamp.today().normalize()

def _is_tomorrow(val) -> bool:
    try:
        s = str(val).strip()
        if not s or s in ("", "nan", "None"):
            return False
        d = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.isna(d):
            return False
        tomorrow = _get_ist_today() + pd.Timedelta(days=1)
        return d.normalize() == tomorrow
    except:
        return False

def _is_today(val) -> bool:
    try:
        s = str(val).strip()
        if not s or s in ("", "nan", "None"):
            return False
        d = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if pd.isna(d):
            return False
        return d.normalize() == _get_ist_today()
    except:
        return False

def _last_working_day() -> pd.Timestamp:
    yesterday = _get_ist_today() - pd.Timedelta(days=1)
    if yesterday.weekday() == 6:  # Sunday -> back to Saturday
        yesterday -= pd.Timedelta(days=1)
    return yesterday

def coach_style(row) -> tuple:
    desp      = str(row.get("desp_date",  "")).strip()
    act_desp  = str(row.get("actualdespdate", "")).strip()
    corr_comp = str(row.get("corr_comp",  "")).strip()
    plan_date = row.get("plan_date", "")
    _blank    = ("", "nan", "None")

    for d_str in (desp, act_desp):
        if d_str and d_str not in _blank:
            try:
                d = pd.to_datetime(d_str, errors="coerce", dayfirst=True)
                if not pd.isna(d):
                    return GREEN, BG_OUTTURN
            except:
                pass

    if corr_comp and corr_comp not in _blank:
        if _is_today(plan_date):
            font = ORANGE
        elif _is_tomorrow(plan_date):
            font = BLUE
        else:
            font = DARK
        return font, BG_CORR

    if _is_today(plan_date):
        return ORANGE, BG_TODAY_PLAN

    if _is_tomorrow(plan_date):
        return BLUE, BG_PLAN

    return GREY, BG_NORMAL

def is_under_corrosion(row) -> bool:
    place = str(row.get("corr_place", "")).strip()
    comp = str(row.get("corr_comp", "")).strip()
    has_place = place and place not in ("", "nan", "None")
    has_comp = comp and comp not in ("", "nan", "None")
    return bool(has_place and not has_comp)

# ---------------------------------------------------------------------------
# REPORTLAB DRAWING HELPERS
# ---------------------------------------------------------------------------

def get_coaches(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    p = prefix.upper()
    pit = df["pitnum"]
    mask = (pit == p) | pit.str.startswith(p + "_")
    alias_pitnums = [k for k, v in PITNUM_ALIASES.items() if v == p]
    if alias_pitnums:
        mask = mask | df["pitnum"].isin(alias_pitnums)
    aliased_away = [k for k, v in PITNUM_ALIASES.items() if v != p]
    if aliased_away:
        mask = mask & ~df["pitnum"].isin(aliased_away)
    return df[mask]

def get_coach_at_slot(df: pd.DataFrame, prefix: str, slot: int):
    p = f"{prefix.upper()}_{slot}"
    pit = df["pitnum"]
    rows = df[pit == p]
    if not rows.empty:
        return rows.iloc[0]
    if slot == 1:
        rows = df[pit == prefix.upper()]
        if not rows.empty:
            return rows.iloc[0]
    for alias, canonical in PITNUM_ALIASES.items():
        if canonical.upper() == prefix.upper():
            alias_slot = alias.split("_")[-1] if "_" in alias else ""
            if alias_slot == str(slot):
                rows = df[pit == alias.upper()]
                if not rows.empty:
                    return rows.iloc[0]
    return None

def mini_table_header(col_widths, headers):
    header = [Paragraph(f"<b>{h}</b>", tiny_header_style) for h in headers]
    t = Table([header], colWidths=list(col_widths))
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#E8E8E8")),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor(GRID_COLOR)),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING",   (0, 0), (-1, -1), 1),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 1),
    ]))
    return t

def _coachno_code_cell(r):
    font_hex, _ = coach_style(r)
    coachno = _val(r.get("coachno"))
    code    = str(r.get("coach_desc") or "").strip()
    is_plan_colour = font_hex in (BLUE, ORANGE)
    cn_tag = f'<u>{coachno}</u>' if is_plan_colour else coachno
    return Paragraph(
        f'<font color="{font_hex}"><b>{cn_tag}</b></font> '
        f'<font size="6" color="#555555">{code}</font>',
        tiny_style,
    )

def _div_tfr_corrin_cell(r):
    div     = _val(r.get("dvnid"))
    tfr     = fmt_date(r.get("tfr"))
    corr_in = fmt_date(r.get("corr_place")) if is_under_corrosion(r) else "—"
    plan    = fmt_date(r.get("plan_date", ""))
    pl_part = f" &nbsp;Pl:{plan}" if plan != "—" else ""
    return Paragraph(
        f"D:{div} &nbsp;T:{tfr} &nbsp;Dt:{corr_in}{pl_part}",
        _TINY_SUB,
    )

def _pdc_cell(r):
    corr_comp = str(r.get("corr_comp", "")).strip()
    _blank    = ("", "nan", "None")
    corr_done = corr_comp and corr_comp not in _blank

    if corr_done or not is_under_corrosion(r):
        d_pdc = fmt_date(r.get("pdc_date", ""))
        return Paragraph(f"<b>D:</b>{d_pdc}", _TINY_SUB)
    else:
        c_pdc = fmt_date(r.get("corrpd", ""))
        return Paragraph(f"<b>C:</b>{c_pdc}", _TINY_SUB)

def mini_table(coach_rows, col_widths):
    data       = []
    row_bgs    = []
    real_rows = [r for r in coach_rows if r is not None]
    
    if not real_rows:
        data.append([Paragraph(f'<font color="{EMPTY_COLOR}"><i>EMPTY</i></font>', tiny_style), "", "", "", ""])
        row_bgs.append(BG_NORMAL)
    else:
        for r in coach_rows:
            if r is None:
                data.append([Paragraph("—", tiny_style), "", "", "", ""])
                row_bgs.append(BG_NORMAL)
                continue
            _, bg = coach_style(r)
            row_bgs.append(bg)
            data.append([
                _coachno_code_cell(r),
                _div_tfr_corrin_cell(r),
                Paragraph(fmt_days(r.get("caldays")), tiny_style),
                _pdc_cell(r),
                Paragraph(fmt_days(r.get("presurveyhrs")), tiny_style),
            ])

    style_cmds = [
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor(GRID_COLOR)),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0.3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 1),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 1),
    ]
    for i, bg in enumerate(row_bgs):
        if bg != BG_NORMAL:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(bg)))

    t = Table(data, colWidths=list(col_widths))
    t.setStyle(TableStyle(style_cmds))
    return t

def mini_table_pre_only(coach_rows, col_widths):
    data    = []
    row_bgs = []

    real_rows = [r for r in coach_rows if r is not None]
    if not real_rows:
        data.append([
            Paragraph(f'<font color="{EMPTY_COLOR}"><i>EMPTY</i></font>', tiny_style),
            Paragraph("—", tiny_style),
        ])
        row_bgs.append(BG_NORMAL)
    else:
        for r in coach_rows:
            if r is None:
                data.append([Paragraph("—", tiny_style), Paragraph("—", tiny_style)])
                row_bgs.append(BG_NORMAL)
                continue
            _, bg = coach_style(r)
            row_bgs.append(bg)
            data.append([
                _coachno_code_cell(r),
                Paragraph(fmt_days(r.get("presurveyhrs")), tiny_style),
            ])

    style_cmds = [
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor(GRID_COLOR)),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0.3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 1),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 1),
    ]
    for i, bg in enumerate(row_bgs):
        if bg != BG_NORMAL:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(bg)))

    t = Table(data, colWidths=list(col_widths))
    t.setStyle(TableStyle(style_cmds))
    return t

def mini_table_loco_only(coach_rows, col_widths):
    header = [Paragraph("<b>Loco No</b>", tiny_header_style)]
    data = [header]
    row_bgs = []
    real_rows = [r for r in coach_rows if r is not None]
    if not real_rows:
        data.append([Paragraph(f'<font color="{EMPTY_COLOR}"><i>EMPTY</i></font>', tiny_style)])
        row_bgs.append(BG_NORMAL)
    else:
        for r in coach_rows:
            if r is None:
                data.append([Paragraph("—", tiny_style)])
                row_bgs.append(BG_NORMAL)
                continue
            font_hex, bg = coach_style(r)
            row_bgs.append(bg)
            data.append([
                Paragraph(f'<font color="{font_hex}"><b>{_val(r.get("coachno"))}</b></font>', tiny_style),
            ])

    t = Table(data, colWidths=list(col_widths))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(GRID_COLOR)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 0.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1),
    ] + [("BACKGROUND", (0, i+1), (-1, i+1), colors.HexColor(bg))
         for i, bg in enumerate(row_bgs) if bg != BG_NORMAL]))
    return t

def shop_single_table(title, order, header_hex, df, total_w=97 * mm):
    is_ac_loco = (title.upper() == AC_LOCO_TITLE)
    CELL_PAD   = 3 * mm
    label_w    = 13 * mm
    content_w  = total_w - label_w
    mini_w     = content_w - CELL_PAD
    _p = mini_w / 100
    mc = (_p*26, _p*40, _p*11, _p*12, _p*11)

    all_rows = [[
        Paragraph(f"<b>{title}</b>", ParagraphStyle(
            "sh_hdr", parent=styles["Normal"], fontSize=10,
            textColor=colors.HexColor("#1A6B2F"), alignment=1)),
        "",
    ]]

    if is_ac_loco:
        all_rows.append(["", mini_table_header((mini_w,), ("Loco No",))])
    else:
        all_rows.append(["", mini_table_header(mc, MINI_TABLE_HEADERS)])

    for item in order:
        line, lbl = item if isinstance(item, tuple) else (item, item)
        if is_ac_loco:
            coaches    = get_coaches(df, line)
            coach_rows = [r for _, r in coaches.iterrows()]
            content    = mini_table_loco_only(coach_rows, col_widths=(mini_w,))
        elif line.upper() in TWO_SLOT_LINES:
            c1 = get_coach_at_slot(df, line, 1)
            c2 = get_coach_at_slot(df, line, 2)
            content = mini_table([c1, c2], col_widths=mc)
        else:
            coaches    = get_coaches(df, line)
            coach_rows = [r for _, r in coaches.iterrows()]
            content    = mini_table(coach_rows, col_widths=mc)
        all_rows.append([
            Paragraph(f"<b>{lbl}</b>", label_style),
            content,
        ])

    t = Table(all_rows, colWidths=[label_w, content_w])
    t.setStyle(TableStyle([
        ("SPAN",          (0, 0), (1, 0)),
        ("BACKGROUND",    (0, 0), (1, 0),  colors.HexColor("#E8F5E9")),
        ("TOPPADDING",    (0, 0), (1, 0),  2),
        ("BOTTOMPADDING", (0, 0), (1, 0),  2),
        ("SPAN",          (0, 1), (0, 1)),
        ("BACKGROUND",    (0, 1), (0, 1),  colors.HexColor("#F2F2F2")),
        ("BACKGROUND",    (0, 2), (0, -1), colors.HexColor("#FFFFFF")),
        ("BACKGROUND",    (1, 1), (1, -1), colors.HexColor(BODY_BG)),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor(GRID_COLOR)),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 1), (-1, -1), 0.5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 0.5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 2),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
    ]))
    return t

def _get_pit_coaches(prefixes, df):
    masks = []
    for p in prefixes:
        pu = p.upper()
        masks.append(df["pitnum"] == pu)
        masks.append(df["pitnum"].str.startswith(pu + "_"))
    combined = masks[0]
    for m in masks[1:]:
        combined = combined | m
    return [r for _, r in df[combined].iterrows()]

def flat_table_side(title, prefixes, header_hex, df, total_w):
    coach_rows = _get_pit_coaches(prefixes, df)
    inner_w = total_w - 4 * mm
    pre_widths = (inner_w * 0.62, inner_w * 0.38)
    header = mini_table_header(pre_widths, PRE_ONLY_HEADERS)
    content = mini_table_pre_only(coach_rows, col_widths=pre_widths)
    t = Table(
        [
            [Paragraph(f"<b>{title}</b>", ParagraphStyle(
                "fhdr2", parent=styles["Normal"], fontSize=11,
                textColor=colors.white, alignment=1))],
            [header],
            [content],
        ],
        colWidths=[total_w],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#E8F5E9")),
        ("BACKGROUND",    (0, 1), (-1, -1), colors.HexColor(BODY_BG)),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor(GRID_COLOR)),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 2),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    return t

def yard_grid_table(coach_rows, cols, total_w):
    FIELDS = 4
    per  = total_w / cols
    cn_w = per * 0.34
    cd_w = per * 0.20
    rd_w = per * 0.28
    ph_w = per * 0.20
    col_widths = [cn_w, cd_w, rd_w, ph_w] * cols

    hdr = []
    for _ in range(cols):
        hdr += [
            Paragraph("<b>Coach No</b>", tiny_header_style),
            Paragraph("<b>Days</b>",     tiny_header_style),
            Paragraph("<b>Recd</b>",     tiny_header_style),
            Paragraph("<b>Pre Hrs</b>",  tiny_header_style),
        ]
    data = [hdr]

    padded = list(coach_rows)
    while len(padded) % cols:
        padded.append(None)

    bg_grid = []
    if not padded:
        empty = [Paragraph(f'<font color="{EMPTY_COLOR}"><i>EMPTY</i></font>', tiny_style)]
        empty += [Paragraph("", tiny_style)] * (cols * FIELDS - 1)
        data.append(empty)
        bg_grid.append([BG_NORMAL] * cols)
    else:
        for i in range(0, len(padded), cols):
            row  = []
            bgs  = []
            for r in padded[i:i + cols]:
                if r is None:
                    row += [Paragraph("", tiny_style)] * FIELDS
                    bgs.append(BG_NORMAL)
                else:
                    _, bg = coach_style(r)
                    bgs.append(bg)
                    row += [
                        _coachno_code_cell(r),
                        Paragraph(fmt_days(r.get("caldays")),      tiny_style),
                        Paragraph(fmt_date(r.get("recd_date")),    tiny_style),
                        Paragraph(fmt_days(r.get("presurveyhrs")), tiny_style),
                    ]
            data.append(row)
            bg_grid.append(bgs)

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor(GRID_COLOR)),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING",   (0, 0), (-1, -1), 1),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 1),
    ]
    for ri, bgs in enumerate(bg_grid):
        tbl_row = ri + 1
        for ci, bg in enumerate(bgs):
            if bg != BG_NORMAL:
                col_start = ci * FIELDS
                col_end   = col_start + FIELDS - 1
                style.append(("BACKGROUND", (col_start, tbl_row), (col_end, tbl_row),
                               colors.HexColor(bg)))
    for gi in range(1, cols):
        col_idx = gi * FIELDS - 1
        style.append(("LINEAFTER", (col_idx, 0), (col_idx, -1), 1.2, colors.HexColor("#999999")))

    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(style))
    return t

def yard_flat_table(title, prefixes, header_hex, df, total_w, cols=4):
    coach_rows = _get_pit_coaches(prefixes, df)
    content = yard_grid_table(coach_rows, cols=cols, total_w=total_w - 4 * mm)
    header = Table(
        [[Paragraph(f"<b>{title}</b>", ParagraphStyle(
            "yhdr", parent=styles["Normal"], fontSize=12,
            textColor=colors.white, alignment=1))]],
        colWidths=[total_w],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#E8F5E9")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    body = Table([[content]], colWidths=[total_w])
    body.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor(BODY_BG)),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor(GRID_COLOR)),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 2),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
    ]))
    return [header, body]

def _count_shop(order, df):
    cnt = 0
    for item in order:
        line = item[0] if isinstance(item, tuple) else item
        if line.upper() in TWO_SLOT_LINES:
            for slot in (1, 2):
                if get_coach_at_slot(df, line, slot) is not None:
                    cnt += 1
        else:
            cnt += len(get_coaches(df, line))
    return cnt

def build_shop_count_table(df: pd.DataFrame, width) -> Table:
    SHOP_SUMMARY = [
        ("Paint Shop",  PAINT_ORDER,        "shop"),
        ("LBR Shed",    LBR_ORDER,           "shop"),
        ("Aug Shop",    AUG_ORDER,           "shop"),
        ("DEMU Wash",   DEMU_WASH,           "shop"),
        ("DEMU Shop",   DEMU_ORDER,          "shop"),
        ("LCB",         LCB_ORDER,           "shop"),
        ("HCR",         HCB_ORDER,           "shop"),
        ("Incoming",    ["OT/IN"],            "flat"),
        ("Despatch",    ["HCB/DESP", "OT/DESP", "DESP"], "flat"),
        ("Yard / OT",   ["OT/YD"],            "flat"),
    ]
    counts, grand = [], 0
    for name, order, kind in SHOP_SUMMARY:
        n = (_count_shop(order, df) if kind == "shop"
             else len(_get_pit_coaches(order, df)))
        counts.append((name, n))
        grand += n

    sm  = ParagraphStyle("sm2",  parent=styles["Normal"], fontSize=6, leading=7.5)
    smb = ParagraphStyle("smb2", parent=styles["Normal"], fontSize=6, leading=7.5,
                          fontName="Helvetica-Bold")
    smw = ParagraphStyle("smw2", parent=styles["Normal"], fontSize=8, leading=10,
                          fontName="Helvetica-Bold", textColor=colors.white, alignment=1)

    cnt_rows = [[Paragraph("<b>Shop</b>", smb), Paragraph("<b>In Pits</b>", smb)]]
    for name, n in counts:
        cnt_rows.append([Paragraph(name, sm), Paragraph(str(n), sm)])
    cnt_rows.append([Paragraph("<b>TOTAL</b>", smb), Paragraph(f"<b>{grand}</b>", smb)])

    cw = [width * 0.55, width * 0.45]
    cnt_tbl = Table(cnt_rows, colWidths=cw)
    cnt_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,  0), (-1,  0), colors.HexColor("#D5D8DC")),
        ("BACKGROUND",    (0, -1), (-1, -1), colors.HexColor("#BFC9CA")),
        ("GRID",          (0,  0), (-1, -1), 0.4, colors.HexColor(GRID_COLOR)),
        ("VALIGN",        (0,  0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0,  0), (-1, -1), 0.3),
        ("BOTTOMPADDING", (0,  0), (-1, -1), 0.3),
        ("LEFTPADDING",   (0,  0), (-1, -1), 2),
        ("RIGHTPADDING",  (0,  0), (-1, -1), 2),
    ]))

    summary = Table([[Paragraph("DAILY SUMMARY", smw)], [cnt_tbl]], colWidths=[width])
    summary.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1A5276")),
        ("TOPPADDING",    (0, 0), (-1, 0), 2),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 0),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor(GRID_COLOR)),
    ]))
    return summary

def build_plan_table(df: pd.DataFrame, total_w, desp_df: pd.DataFrame = None,
                     m_today_plan: str = "", m_tmrw_plan: str = "",
                     m_today_out: str = "", m_wise_desp: str = "") -> Table:
    today    = pd.Timestamp.today().normalize()
    tomorrow = today + pd.Timedelta(days=1)

    # "Yesterday", skipping Sunday
    outturn_ref = today - pd.Timedelta(days=1)
    if outturn_ref.weekday() == 6:   # 6 = Sunday
        outturn_ref = outturn_ref - pd.Timedelta(days=1)

    outturn_refs = [outturn_ref]
    if today.weekday() == 0:  # Monday
        # Include Friday and Thursday outturn as well
        friday = today - pd.Timedelta(days=3)
        thursday = today - pd.Timedelta(days=4)
        outturn_refs.append(friday)
        outturn_refs.append(thursday)

    # Source df for outturn/despatch rows (includes no-pitnum coaches)
    dfs_to_concat = []
    if df is not None and not df.empty:
        dfs_to_concat.append(df)
    if desp_df is not None and not desp_df.empty:
        dfs_to_concat.append(desp_df)
    _ddf = pd.concat(dfs_to_concat, ignore_index=True) if dfs_to_concat else pd.DataFrame()

    def _parse(v):
        if not v or str(v).strip() in ("", "nan", "None"):
            return pd.NaT
        return pd.to_datetime(v, errors="coerce", dayfirst=True)

    def _match(v, dts):
        d = _parse(v)
        if pd.isna(d):
            return False
        if isinstance(dts, list):
            return any(d.normalize() == dt for dt in dts)
        return d.normalize() == dts

    def _coach_list(src_df, col, dt):
        """Return list of 'coachno TYPE' strings matching date in col."""
        matched = src_df[src_df[col].apply(lambda v: _match(v, dt))]
        result = []
        for _, r in matched.iterrows():
            cn   = str(r.get("coachno", "")).strip()
            code = str(r.get("coach_desc", "")).strip()
            if code and code.lower() not in ("nan", "none", ""):
                result.append(f"{cn} ({code})")
            else:
                result.append(cn)
        return result

    def _format_with_desc(cno_list, src_df):
        res = []
        for cno in cno_list:
            clean_c = _clean_cno(cno)
            if src_df is not None and not src_df.empty and 'coachno' in src_df.columns:
                matched = src_df[src_df['coachno'].apply(_clean_cno) == clean_c]
                if not matched.empty:
                    r = matched.iloc[0]
                    cn = str(r.get("coachno", "")).strip()
                    code = str(r.get("coach_desc", "") or "").strip()
                    if code and code.lower() not in ("nan", "none", ""):
                        res.append(f"{cn} ({code})")
                        continue
            res.append(cno)
        return res

    if m_today_plan:
        raw_list = [x.strip() for x in m_today_plan.split(",") if x.strip()]
        today_plan = _format_with_desc(raw_list, df)
    else:
        today_plan = _coach_list(df,    "plan_date",     today)

    if m_tmrw_plan:
        raw_list = [x.strip() for x in m_tmrw_plan.split(",") if x.strip()]
        tmrw_plan = _format_with_desc(raw_list, df)
    else:
        tmrw_plan  = _coach_list(df,    "plan_date",     tomorrow)

    if m_today_out:
        raw_list = [x.strip() for x in m_today_out.split(",") if x.strip()]
        today_out = _format_with_desc(raw_list, _ddf)
    else:
        today_out  = _coach_list(_ddf,  "desp_date",     outturn_refs)

    if m_wise_desp:
        raw_list = [x.strip() for x in m_wise_desp.split(",") if x.strip()]
        all_desp = _format_with_desc(raw_list, _ddf)
    else:
        all_desp   = _coach_list(_ddf,  "actualdespdate", outturn_refs)
        if not all_desp and "wisecd" in _ddf.columns:
            all_desp = _coach_list(_ddf, "wisecd", outturn_refs)

    def _fl(lst): return ", ".join(lst) if lst else "Nil"

    # ── Styles ──────────────────────────────────────────────────────────────
    sm   = ParagraphStyle("sm3",   parent=styles["Normal"], fontSize=6.5, leading=8)
    smb  = ParagraphStyle("smb3",  parent=styles["Normal"], fontSize=6.5, leading=8,
                          fontName="Helvetica-Bold")
    smw  = ParagraphStyle("smw3",  parent=styles["Normal"], fontSize=8,   leading=10,
                          fontName="Helvetica-Bold", textColor=colors.white, alignment=1)

    sm_plan  = ParagraphStyle("sm_plan",  parent=styles["Normal"], fontSize=6.5, leading=8,
                               fontName="Helvetica-Bold",
                               textColor=colors.HexColor("#A04000"))
    sm_tmrw  = ParagraphStyle("sm_tmrw",  parent=styles["Normal"], fontSize=6.5, leading=8,
                               fontName="Helvetica-Bold",
                               textColor=colors.HexColor("#1A4F9C"))
    sm_out   = ParagraphStyle("sm_out",   parent=styles["Normal"], fontSize=6.5, leading=8,
                               fontName="Helvetica-Bold",
                               textColor=colors.HexColor(GREEN))
    sm_desp  = ParagraphStyle("sm_desp",  parent=styles["Normal"], fontSize=6.5, leading=8,
                               fontName="Helvetica-Bold",
                               textColor=colors.HexColor("#145A32"))

    sm_plan_v = ParagraphStyle("sm_plan_v", parent=styles["Normal"], fontSize=6.5, leading=8,
                                textColor=colors.HexColor("#784212"))
    sm_tmrw_v = ParagraphStyle("sm_tmrw_v", parent=styles["Normal"], fontSize=6.5, leading=8,
                                textColor=colors.HexColor("#1A4F9C"))
    sm_out_v  = ParagraphStyle("sm_out_v",  parent=styles["Normal"], fontSize=6.5, leading=8,
                                fontName="Helvetica-Bold",
                                textColor=colors.HexColor(GREEN))
    sm_desp_v = ParagraphStyle("sm_desp_v", parent=styles["Normal"], fontSize=6.5, leading=8,
                                fontName="Helvetica-Bold",
                                textColor=colors.HexColor("#145A32"))

    dt_str  = today.strftime("%d-%b-%Y")
    tm_str  = tomorrow.strftime("%d-%b")
    
    if today.weekday() == 0:  # Monday
        thursday = today - pd.Timedelta(days=4)
        out_str = f"{thursday.strftime('%d')}-{outturn_ref.strftime('%d-%b-%Y')}"
    else:
        out_str = outturn_ref.strftime("%d-%b-%Y")

    rhs_rows = [
        [Paragraph("<b>Category</b>",  smb),  Paragraph("<b>Coach No (Type)</b>", smb)],
        [Paragraph(f"Today's Planned Outturn ({dt_str})",    sm_plan),  Paragraph(_fl(today_plan),  sm_plan_v)],
        [Paragraph(f"Tomorrow's Plan ({tm_str})",  sm_tmrw),  Paragraph(_fl(tmrw_plan),   sm_tmrw_v)],
        [Paragraph(f"Yesterday's Outturn ({out_str})", sm_out),   Paragraph(_fl(today_out),   sm_out_v)],
        [Paragraph(f"Yesterday's WISE Despatch ({out_str})", sm_desp),    Paragraph(_fl(all_desp),    sm_desp_v)],
    ]
    rw = [total_w * 0.22, total_w * 0.78]
    rhs_tbl = Table(rhs_rows, colWidths=rw)
    rhs_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#D5D8DC")),
        ("BACKGROUND",    (0, 3), (-1, 3),  colors.HexColor(BG_OUTTURN)),
        ("BACKGROUND",    (0, 4), (-1, 4),  colors.HexColor("#D5F5E3")),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor(GRID_COLOR)),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 2),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
    ]))

    plan = Table([[Paragraph("DESPATCH PLAN", smw)], [rhs_tbl]], colWidths=[total_w])
    plan.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1A5276")),
        ("TOPPADDING",    (0, 0), (-1, 0), 2),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 0),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor(GRID_COLOR)),
    ]))
    return plan

# ---------------------------------------------------------------------------
# MAIN PDF GENERATION LOGIC
# ---------------------------------------------------------------------------

def generate_pdf_bytes(today_plan: str = "", tmrw_plan: str = "",
                       today_out: str = "", wise_desp: str = "") -> bytes:
    """Generate the full 2-page PDF report in-memory and return its bytes."""
    df = load_data()
    desp_df = load_despatch_data()

    # ── Override Processing (In-Memory) ─────────────────────────────────────
    today_dt = pd.Timestamp.today().normalize()
    tomorrow_dt = today_dt + pd.Timedelta(days=1)
    
    # Calculate outturn reference range (Friday, Saturday, and Thursday for Mondays)
    outturn_ref = today_dt - pd.Timedelta(days=1)
    if outturn_ref.weekday() == 6:  # Sunday -> Saturday
        outturn_ref = outturn_ref - pd.Timedelta(days=1)
        
    outturn_refs = [outturn_ref]
    if today_dt.weekday() == 0:  # Monday
        friday = today_dt - pd.Timedelta(days=3)
        thursday = today_dt - pd.Timedelta(days=4)
        outturn_refs.append(friday)
        outturn_refs.append(thursday)

    def _parse_override_date(val):
        if not val or str(val).strip() in ("", "nan", "None"):
            return pd.NaT
        return pd.to_datetime(val, errors="coerce", dayfirst=True)

    def _match_date_range(date_val, target_dates):
        d = _parse_override_date(date_val)
        if pd.isna(d):
            return False
        return d.normalize() in target_dates

    # 1. Today's Plan override
    if today_plan:
        # Clear plan_date for active coaches whose plan_date is today
        if 'plan_date' in df.columns:
            df.loc[df['plan_date'].apply(lambda v: _match_date_range(v, [today_dt])), 'plan_date'] = ""
        # Set today's date for manually specified coaches
        manual_today = [x.strip() for x in today_plan.split(",") if x.strip()]
        for cno in manual_today:
            clean_c = _clean_cno(cno)
            if 'coachno' in df.columns:
                df.loc[df['coachno'].apply(_clean_cno) == clean_c, 'plan_date'] = today_dt.strftime('%d-%m-%Y')

    # 2. Tomorrow's Plan override
    if tmrw_plan:
        # Clear plan_date for active coaches whose plan_date is tomorrow
        if 'plan_date' in df.columns:
            df.loc[df['plan_date'].apply(lambda v: _match_date_range(v, [tomorrow_dt])), 'plan_date'] = ""
        # Set tomorrow's date for manually specified coaches
        manual_tmrw = [x.strip() for x in tmrw_plan.split(",") if x.strip()]
        for cno in manual_tmrw:
            clean_c = _clean_cno(cno)
            if 'coachno' in df.columns:
                df.loc[df['coachno'].apply(_clean_cno) == clean_c, 'plan_date'] = tomorrow_dt.strftime('%d-%m-%Y')

    # 3. Today's Outturn override
    if today_out:
        # Clear desp_date for active coaches whose desp_date is in the outturn range
        if 'desp_date' in df.columns:
            df.loc[df['desp_date'].apply(lambda v: _match_date_range(v, outturn_refs)), 'desp_date'] = ""
        if desp_df is not None and not desp_df.empty and 'desp_date' in desp_df.columns:
            desp_df.loc[desp_df['desp_date'].apply(lambda v: _match_date_range(v, outturn_refs)), 'desp_date'] = ""
            
        # Set outturn date (yesterday/today_dt) for manually specified coaches
        manual_out = [x.strip() for x in today_out.split(",") if x.strip()]
        for cno in manual_out:
            clean_c = _clean_cno(cno)
            if 'coachno' in df.columns:
                df.loc[df['coachno'].apply(_clean_cno) == clean_c, 'desp_date'] = outturn_ref.strftime('%d-%m-%Y')
                df.loc[df['coachno'].apply(_clean_cno) == clean_c, 'plan_date'] = ""
            if desp_df is not None and not desp_df.empty and 'coachno' in desp_df.columns and 'desp_date' in desp_df.columns:
                desp_df.loc[desp_df['coachno'].apply(_clean_cno) == clean_c, 'desp_date'] = outturn_ref.strftime('%d-%m-%Y')

    # 4. WISE Despatch override
    if wise_desp:
        # Clear actualdespdate for active coaches whose actualdespdate is in the outturn range
        if desp_df is not None and not desp_df.empty:
            for col in ['actualdespdate', 'wisecd']:
                if col in desp_df.columns:
                    desp_df.loc[desp_df[col].apply(lambda v: _match_date_range(v, outturn_refs)), col] = ""
            
        # Set actualdespdate for manually specified coaches
        manual_desp = [x.strip() for x in wise_desp.split(",") if x.strip()]
        for cno in manual_desp:
            clean_c = _clean_cno(cno)
            if desp_df is not None and not desp_df.empty and 'coachno' in desp_df.columns and 'actualdespdate' in desp_df.columns:
                desp_df.loc[desp_df['coachno'].apply(_clean_cno) == clean_c, 'actualdespdate'] = outturn_ref.strftime('%d-%m-%Y')
            if 'coachno' in df.columns:
                df.loc[df['coachno'].apply(_clean_cno) == clean_c, 'plan_date'] = ""
                df.loc[df['coachno'].apply(_clean_cno) == clean_c, 'actualdespdate'] = outturn_ref.strftime('%d-%m-%Y')
                df.loc[df['coachno'].apply(_clean_cno) == clean_c, 'desp_date'] = outturn_ref.strftime('%d-%m-%Y')

    buffer = io.BytesIO()
    PAGE_WIDTH, PAGE_HEIGHT = A4
    doc = SimpleDocTemplate(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
                             topMargin=2 * mm, bottomMargin=2 * mm,
                             leftMargin=3 * mm, rightMargin=3 * mm)
    story = []

    # Title + timestamp
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=11, leading=13, spaceAfter=0)
    ts_style    = ParagraphStyle("ts",    parent=styles["Normal"], fontSize=8, leading=10)
    story.append(Paragraph("Workshop Aerial View — Snapshot", title_style))
    story.append(Paragraph(f"Generated: {pd.Timestamp.now():%d-%b-%Y %H:%M}", ts_style))

    SHOP_W  = 101 * mm
    TOTAL_W = SHOP_W * 2

    # ── Legend ──────────────────────────────────────────────────────────────
    _lsb = ParagraphStyle("lsb", parent=styles["Normal"], fontSize=7, leading=9, fontName="Helvetica-Bold")
    SW, LW = 5 * mm, 37 * mm

    def _swatch(bg, font_col, sample_text):
        return Paragraph(
            f'<font color="{font_col}"><b>{sample_text}</b></font>',
            ParagraphStyle("sw", parent=styles["Normal"], fontSize=7, leading=9,
                           textColor=colors.HexColor(font_col), alignment=1))

    _leg_col_w = [SW, LW, SW, LW, SW, LW, SW, LW, SW, LW]
    legend = Table([
        [
            _swatch(BG_OUTTURN,    GREEN,  "196252"),
            Paragraph("<b>Outturn taken</b>",        _lsb),
            _swatch(BG_CORR,       DARK,   "195492"),
            Paragraph("<b>Corrosion complete</b>",   _lsb),
            _swatch(BG_TODAY_PLAN, ORANGE, "136234"),
            Paragraph("<b>Today's plan</b>",         _lsb),
            _swatch(BG_PLAN,       BLUE,   "116470"),
            Paragraph("<b>Tomorrow's plan</b>",      _lsb),
            _swatch(BG_NORMAL,     GREY,   "136233"),
            Paragraph("<b>Normal / in process</b>",  _lsb),
        ],
    ], colWidths=_leg_col_w)
    legend.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), colors.HexColor(BG_OUTTURN)),
        ("BACKGROUND",    (2, 0), (2, 0), colors.HexColor(BG_CORR)),
        ("BACKGROUND",    (4, 0), (4, 0), colors.HexColor(BG_TODAY_PLAN)),
        ("BACKGROUND",    (6, 0), (6, 0), colors.HexColor(BG_PLAN)),
        ("BACKGROUND",    (8, 0), (8, 0), colors.HexColor(BG_NORMAL)),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor(GRID_COLOR)),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING",   (0, 0), (-1, -1), 2),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
    ]))

    # Unpack shops & flat lines
    paint_t, paint_o, paint_h = SHOPS[0]
    lbr_t,   lbr_o,   lbr_h  = SHOPS[1]
    aug_t,   aug_o,   aug_h   = SHOPS[2]
    dw_t,    dw_o,    dw_h    = SHOPS[3]
    demu_t,  demu_o,  demu_h  = SHOPS[4]
    lcb_t,   lcb_o,   lcb_h   = SHOPS[5]
    hcr_t,   hcr_o,   hcr_h   = SHOPS[6]

    inc_title,  inc_pfx,  inc_col  = FLAT_LINES[0]
    dep_title,  dep_pfx,  dep_col  = FLAT_LINES[1]
    yard_title, yard_pfx, yard_col = FLAT_LINES[2]

    # Left column stack
    left_col = Table(
        [[shop_single_table(paint_t, paint_o, paint_h, df, total_w=SHOP_W)],
         [flat_table_side(inc_title,  inc_pfx,  inc_col,  df, SHOP_W)],
         [shop_single_table(dw_t,    dw_o,    dw_h,    df, total_w=SHOP_W)],
         [shop_single_table(demu_t,  demu_o,  demu_h,  df, total_w=SHOP_W)],
         [shop_single_table(hcr_t,   hcr_o,   hcr_h,   df, total_w=SHOP_W)],
         [flat_table_side(dep_title,  dep_pfx,  dep_col,  df, SHOP_W)],
         [build_shop_count_table(df, SHOP_W)]],
        colWidths=[SHOP_W],
    )
    left_col.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 6), (0, 6), 1 * mm),
    ]))

    # Right column stack
    yard_pieces = yard_flat_table(yard_title, yard_pfx, yard_col, df, total_w=SHOP_W, cols=3)
    yard_tbl = Table([[p] for p in yard_pieces], colWidths=[SHOP_W])
    yard_tbl.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    right_col = Table(
        [[shop_single_table(lbr_t,  lbr_o,  lbr_h,  df, total_w=SHOP_W)],
         [shop_single_table(aug_t,  aug_o,  aug_h,  df, total_w=SHOP_W)],
         [shop_single_table(lcb_t,  lcb_o,  lcb_h,  df, total_w=SHOP_W)],
         [yard_tbl]],
        colWidths=[SHOP_W],
    )
    right_col.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # Two-column row
    shops_row = Table([[left_col, right_col]], colWidths=[SHOP_W, SHOP_W])
    shops_row.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    plan = build_plan_table(
        df,
        TOTAL_W,
        desp_df=desp_df,
        m_today_plan=today_plan,
        m_tmrw_plan=tmrw_plan,
        m_today_out=today_out,
        m_wise_desp=wise_desp
    )

    # Compile Page 1 outer wrapper
    outer = Table(
        [[shops_row],
         [plan],
         [legend]],
        colWidths=[TOTAL_W],
    )
    outer.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (0,  0),  1),
        ("BOTTOMPADDING", (0, 1), (0,  1),  1),
        ("BOTTOMPADDING", (0, 2), (0,  2),  0),
    ]))
    story.append(outer)

    # ── PAGE 2: COACHES PENDING STAGES AFTER CORROSION ──────────────────────
    story.append(PageBreak())
    
    page2_title_style = ParagraphStyle(
        "page2_title", parent=styles["Title"], fontSize=14, leading=16,
        textColor=colors.HexColor("#1A5276"), spaceAfter=10, alignment=0
    )
    story.append(Paragraph("Coaches Pending Stages after Corrosion Complete", page2_title_style))
    story.append(Paragraph(f"Generated: {pd.Timestamp.now():%d-%b-%Y %H:%M}", ts_style))
    story.append(Spacer(1, 4 * mm))

    # Identify pending coaches
    pending_coaches = []
    for _, r in df.iterrows():
        corr_comp = str(r.get("corr_comp") or "").strip()
        actual_desp = str(r.get("actualdespdate") or "").strip()
        
        has_corr_comp = corr_comp and corr_comp.lower() not in ("none", "null", "nan", "", "0")
        has_actual_desp = actual_desp and actual_desp.lower() not in ("none", "null", "nan", "")
        
        if has_corr_comp and not has_actual_desp:
            pending_coaches.append(r)

    # Build stage details table
    headers = [
        Paragraph("<b>Coach No / Code</b>", ParagraphStyle("hdr_c", parent=tiny_header_style, textColor=colors.white)),
        Paragraph("<b>Pit</b>", ParagraphStyle("hdr_p", parent=tiny_header_style, textColor=colors.white)),
        Paragraph("<b>Days</b>", ParagraphStyle("hdr_d", parent=tiny_header_style, textColor=colors.white)),
        Paragraph("<b>Recd / Corr Comp</b>", ParagraphStyle("hdr_dt", parent=tiny_header_style, textColor=colors.white)),
        Paragraph("<b>Lowering</b>", ParagraphStyle("hdr_l", parent=tiny_header_style, textColor=colors.white)),
        Paragraph("<b>Furnishing</b>", ParagraphStyle("hdr_f", parent=tiny_header_style, textColor=colors.white)),
        Paragraph("<b>Despatch</b>", ParagraphStyle("hdr_dp", parent=tiny_header_style, textColor=colors.white)),
        Paragraph("<b>Remarks</b>", ParagraphStyle("hdr_r", parent=tiny_header_style, textColor=colors.white)),
    ]
    
    table_data = [headers]
    for c in pending_coaches:
        coachno = c.get("coachno", "")
        code = str(c.get("coach_desc") or "").strip()
        pit = c.get("pitnum", "")
        days = str(c.get("caldays", "—"))
        recd = fmt_date(c.get("recd_date"))
        corr_comp = fmt_date(c.get("corr_comp"))
        lowering = format_stage_status(c.get("lowering_status"))
        furnishing = format_stage_status(c.get("furnishing_status"))
        despatch = format_stage_status(c.get("despatch_status"))
        remarks = c.get("google_remarks", "") or "—"
        
        row_cells = [
            Paragraph(f"<b>{coachno}</b> <font size='6.5' color='#555555'>{code}</font>", tiny_style),
            Paragraph(pit, tiny_style),
            Paragraph(days, tiny_style),
            Paragraph(f"R:{recd}<br/>C:{corr_comp}", _TINY_SUB),
            Paragraph(lowering, tiny_style),
            Paragraph(furnishing, tiny_style),
            Paragraph(despatch, tiny_style),
            Paragraph(remarks, tiny_style),
        ]
        table_data.append(row_cells)

    t2 = Table(table_data, colWidths=[28*mm, 18*mm, 13*mm, 28*mm, 27*mm, 27*mm, 27*mm, 34*mm])
    t2_style = [
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1A5276")),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor(GRID_COLOR)),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(table_data)):
        bg = colors.HexColor("#F9F9F9") if i % 2 == 1 else colors.HexColor("#FFFFFF")
        t2_style.append(("BACKGROUND", (0, i), (-1, i), bg))
        
    t2.setStyle(TableStyle(t2_style))
    story.append(t2)

    doc.build(story)
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
