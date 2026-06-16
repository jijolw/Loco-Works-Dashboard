import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.erp_service import fetch_master, fetch_clean, fetch_single
from services.live_service import get_live_data
from services.aerial_service import get_aerial_data

master = fetch_master()
print(f"Master total records: {len(master)}")

active_coaches_master = []
active_locos_master = []

for r in master:
    status = str(r.get("status")).strip().upper()
    if status == "AC LOCO":
        active_locos_master.append(r)
    elif status not in ("COND", "BHOPAL", "RETURN", "DESPATCHED", "OUTTURN"):
        # Let's check single details to be sure it's active (not despatched)
        try:
            detail = fetch_single(r.get("demandid"))
            actual_desp = str(detail.get("actualdespdate") or "").strip()
            if not (actual_desp and actual_desp.lower() not in ("none", "null", "nan")):
                active_coaches_master.append(r)
        except Exception:
            pass

print(f"Active Coaches in Master (not despatched): {len(active_coaches_master)}")
print(f"Active AC Locos in Master: {len(active_locos_master)}")

live_data = get_live_data()
live_coaches = live_data.get("coaches", [])
print(f"Live Position Total: {len(live_coaches)}")
print(f"  Standard Coaches in Live: {sum(1 for c in live_coaches if c.get('status') != 'AC LOCO')}")
print(f"  AC Locos in Live: {sum(1 for c in live_coaches if c.get('status') == 'AC LOCO')}")

aerial_data = get_aerial_data()
aerial_coaches = aerial_data.get("coaches", [])
aerial_locos = aerial_data.get("ac_locos", [])
print(f"Aerial Coaches Total: {len(aerial_coaches)}")
print(f"Aerial AC Locos Total: {len(aerial_locos)}")
