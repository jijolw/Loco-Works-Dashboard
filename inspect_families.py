import sys
import os
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from services.erp_service import fetch_master
from services.decoders import decode_family

try:
    master = fetch_master()
    print(f"Fetched {len(master)} coaches.")
    
    desc_counter = Counter()
    family_counter = Counter()
    unmapped_demus = []
    
    for row in master:
        desc = str(row.get("coach_desc", "") or row.get("coachdesc", "")).strip()
        desc_counter[desc] += 1
        
        family = decode_family(desc)
        family_counter[family] += 1
        
        # Check if description seems to be DEMU but decodes to OTHER or something else
        desc_upper = desc.upper()
        if "DEMU" in desc_upper or "DPC" in desc_upper or "DTC" in desc_upper or desc_upper == "TC" or desc_upper.endswith("TC"):
            if family != "DEMU" and family != "MEMU":
                unmapped_demus.append((desc, family))
                
    print("\nDecoded Family Frequencies:")
    for family, count in family_counter.most_common():
        print(f"  {family:<15}: {count}")
        
    print("\nMost Common Coach Descriptions:")
    for desc, count in desc_counter.most_common(30):
        print(f"  {desc:<30}: {count}")
        
    if unmapped_demus:
        print("\nPossible DEMU descriptions that did NOT map to DEMU:")
        for desc, decoded in set(unmapped_demus):
            print(f"  {desc:<30} -> Decoded to: {decoded} (Count: {desc_counter[desc]})")
    else:
        print("\nAll potential DEMU descriptions mapped correctly!")
        
except Exception as e:
    import traceback
    traceback.print_exc()
