from services.poh_service import get_targets_vs_achievement

comp = get_targets_vs_achievement("2025-26")
for r in comp:
    if r["family"] in ["ICF", "LHB"]:
        print(f"Period: {r['month_name']}, Family: {r['family']}, Target: {r['target']}, Actual: {r['actual']}, Var: {r['variance']}")
