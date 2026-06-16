import sys
from services.erp_service import fetch_master
from services.decoders import decode_family

master = fetch_master()
print("Checking all ICF-decoded coaches for special patterns...")
icf_coaches = []
for r in master:
    desc = (r.get("coach_desc") or r.get("coachdesc") or "").strip().upper()
    coachno = r.get("coachno")
    fam = decode_family(desc)
    if fam == "ICF":
        # Check if there are other terms in description that could mean special, tower wagon, camping, bogie, etc.
        for special_term in ["TW", "ART", "ARMV", "SPART", "SPIC", "BOGIE", "CAMPING"]:
            if special_term in desc:
                print(f"Coach: {coachno}, Desc: {desc}, matched to ICF but contains {special_term}")
