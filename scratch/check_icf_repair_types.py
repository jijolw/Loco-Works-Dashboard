from datetime import datetime
from services.erp_service import fetch_master, fetch_single, _parse_date
from services.decoders import decode_family, decode_repair

master = fetch_master()
cutoff_date = datetime(2024, 4, 1)
fy = "2026-27"
count = 0

for r in master:
    recd_str = r.get("recd_date") or r.get("recddate")
    recd_dt = _parse_date(recd_str)
    if not recd_dt or recd_dt < cutoff_date:
        continue
    demandid = r.get("demandid")
    if not demandid:
        continue
    try:
        detail = fetch_single(demandid)
    except Exception:
        continue
    desp_str = detail.get("desp_date") or r.get("desp_date") or detail.get("despdate")
    desp_dt = _parse_date(desp_str)
    if desp_dt:
        y, m = desp_dt.year, desp_dt.month
        coach_fy = f"{y}-{str(y+1)[2:]}" if m >= 4 else f"{y-1}-{str(y)[2:]}"
        if coach_fy == fy:
            desc = (r.get("coach_desc") or r.get("coachdesc") or "").strip().upper()
            family = decode_family(desc)
            if family == "ICF":
                rt = detail.get("repair_type")
                count += 1
                print(f"{count}. Coach: {r.get('coachno')}, RepairType: {rt} ({decode_repair(rt)})")
