from datetime import datetime
from services.erp_service import fetch_master, fetch_single, _parse_date
from services.decoders import decode_family, decode_repair

master = fetch_master()
cutoff_date = datetime(2024, 4, 1)

for fy in ['2025-26', '2026-27']:
    print(f"=== FY {fy} Non-Standard Outturns ===")
    for rec in master:
        recd_str = rec.get("recd_date") or rec.get("recddate")
        recd_dt = _parse_date(recd_str)
        if not recd_dt or recd_dt < cutoff_date:
            continue
        demandid = rec.get("demandid")
        if not demandid:
            continue
        try:
            detail = fetch_single(demandid)
        except Exception as e:
            continue
        desp_str = detail.get("desp_date") or rec.get("desp_date") or detail.get("despdate")
        desp_dt = _parse_date(desp_str)
        if desp_dt:
            y, m = desp_dt.year, desp_dt.month
            coach_fy = f"{y}-{str(y+1)[2:]}" if m >= 4 else f"{y-1}-{str(y)[2:]}"
            if coach_fy == fy:
                coach_desc = rec.get("coach_desc") or rec.get("coachdesc") or ""
                family = decode_family(coach_desc)
                if family in ["SPECIAL", "TW", "OTHER", "LOCO"]:
                    print(f"Coach: {rec.get('coachno')}, Desc: {coach_desc}, Family: {family}, Desp: {desp_str}, Repair: {decode_repair(detail.get('repairid'))}")
