from services.erp_service import fetch_master, fetch_single

master = fetch_master()
for r in master:
    if r.get("coachno") == "076540":
        demandid = r.get("demandid")
        print("Demandid:", demandid)
        detail = fetch_single(demandid)
        print("Detail Keys:", list(detail.keys()))
        print("Detail Values:")
        for k, v in detail.items():
            print(f"  {k}: {v}")
        break
