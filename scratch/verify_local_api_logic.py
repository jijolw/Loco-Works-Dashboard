import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.aerial_service import _fetch_ac_locos
from services.erp_service import fetch_master, cache_clear

# Clear cache to force load from Supabase
cache_clear()

locos = _fetch_ac_locos()
print(f"Loaded {len(locos)} AC Locos from API logic.")
for idx, l in enumerate(locos[:3]):
    print(f"\nLoco {idx+1}: {l.get('loco_no')}")
    print(f"  Description: {l.get('loco_desc')}")
    print(f"  Shed (division): {l.get('shed')}")
    print(f"  Arrived (recd_on): {l.get('recd_on')}")
    print(f"  Dewheeled (dewheel): {l.get('dewheel')}")
    print(f"  Wheeling Done (wheeling): {l.get('wheeling')}")
    print(f"  Test Trial (test_trial): {l.get('test_trial')}")
    print(f"  Ready/Despatch (traffic): {l.get('traffic')}")
