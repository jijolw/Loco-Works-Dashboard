import sys
import os

sys.path.insert(0, r"C:\Users\User\.gemini\antigravity\scratch\ERP")

from services.aerial_service import _fetch_ac_locos

locos = _fetch_ac_locos()
print(f"Total locos found: {len(locos)}")
if locos:
    print("Sample Loco 1 Keys & Values:")
    for k, v in sorted(locos[0].items()):
        print(f"  {k}: {repr(v)}")
else:
    print("No locos found.")
