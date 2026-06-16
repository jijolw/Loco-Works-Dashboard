import sys
import os
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from services.erp_service import fetch_master, fetch_single, _parse_date
from services.decoders import decode_family, decode_repair
from services.poh_service import get_standard_lhb_schedule

try:
    master = fetch_master()
    print(f"Total master coaches: {len(master)}")
    
    # Let's count by year (from recd_date or desp_date)
    # Since we want to know schedules per year, let's check receipt year first
    by_fy = defaultdict(lambda: defaultdict(int))
    coach_types_by_sched = defaultdict(lambda: defaultdict(int))
    
    # We will sample/read detail of LHB coaches to get their repair type (rt)
    lhb_coaches = []
    for row in master:
        desc = str(row.get("coach_desc", "") or row.get("coachdesc", "")).strip()
        if decode_family(desc) == "LHB":
            lhb_coaches.append(row)
            
    print(f"Total LHB coaches found: {len(lhb_coaches)}")
    
    # Let's fetch details for LHB coaches to get their repair type (rt) and outturn date
    # Limit to first 1000 or fetch all if it is fast (since it is cached/fast)
    processed = 0
    for row in lhb_coaches:
        demandid = row.get("demandid")
        if not demandid:
            continue
            
        detail = fetch_single(demandid)
        rt = str(detail.get("repairid") or detail.get("repair_type") or row.get("repairid") or row.get("repair_type") or "").strip()
        sched = get_standard_lhb_schedule(rt)
        
        # Determine year/FY. We can use recd_date or desp_date
        recd_str = row.get("recd_date") or row.get("recddate")
        recd_dt = _parse_date(recd_str)
        
        if recd_dt:
            # Financial Year of receipt
            y, m = recd_dt.year, recd_dt.month
            fy = f"{y}-{str(y+1)[2:]}" if m >= 4 else f"{y-1}-{str(y)[2:]}"
            
            by_fy[fy][sched] += 1
            by_fy[fy]["TOTAL"] += 1
            
            coach_desc = str(row.get("coach_desc", "") or row.get("coachdesc", "")).strip()
            coach_types_by_sched[sched][coach_desc] += 1
            processed += 1
            
    print(f"\nProcessed {processed} LHB coaches with valid dates.")
    print("\nLHB Schedules by Financial Year (Receipt Date):")
    for fy in sorted(by_fy.keys()):
        stats = by_fy[fy]
        print(f"  FY {fy}:")
        for sched in sorted(stats.keys()):
            if sched != "TOTAL":
                print(f"    - {sched:<10}: {stats[sched]}")
        print(f"    - TOTAL     : {stats['TOTAL']}")
        
    print("\nCoach Types under each Schedule:")
    for sched in sorted(coach_types_by_sched.keys()):
        print(f"  Schedule {sched}:")
        for ctype, count in sorted(coach_types_by_sched[sched].items(), key=lambda x: -x[1])[:5]:
            print(f"    - {ctype:<15}: {count}")
            
except Exception as e:
    import traceback
    traceback.print_exc()
