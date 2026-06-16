import sys
import os
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from services.erp_service import fetch_master
from services.decoders import decode_family

try:
    master = fetch_master()
    demu_coaches = []
    
    for row in master:
        coachno = str(row.get("coachno", "")).strip()
        desc = str(row.get("coach_desc", "") or row.get("coachdesc", "")).strip()
        family = decode_family(desc)
        
        desc_upper = desc.upper()
        if "DEMU" in desc_upper or "DPC" in desc_upper or "DTC" in desc_upper or desc_upper == "TC" or desc_upper.endswith("TC"):
            demu_coaches.append((coachno, desc, family))
            
    print(f"Total potential DEMU/TC records: {len(demu_coaches)}")
    
    # Show counts by (description, family)
    counts = Counter((d, f) for c, d, f in demu_coaches)
    print("\nMapping by coach description and family:")
    for (desc, family), count in counts.most_common():
        print(f"  {desc:<25} -> {family:<10} (Count: {count})")
        
except Exception as e:
    import traceback
    traceback.print_exc()
