from services.poh_service import get_targets_vs_achievement
import json

comp = get_targets_vs_achievement("2026-27")
for r in comp:
    if r["family"] in ["ICF", "LHB"]:
        print(f"Period: {r['month_name']}, Family: {r['family']}, Target: {r['target']}, Actual: {r['actual']}, Var: {r['variance']}")
