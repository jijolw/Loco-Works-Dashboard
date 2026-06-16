import requests
import json

url = "http://127.0.0.1:5001/api/live"
resp = requests.get(url)
if resp.ok:
    data = resp.json()
    coaches = data.get("coaches", [])
    print(f"Total inside `/api/live`: {len(coaches)}")
    
    # Count by status/family
    from collections import Counter
    status_counts = Counter(c.get("status") for c in coaches)
    family_counts = Counter(c.get("family") for c in coaches)
    make_counts = Counter(c.get("make") for c in coaches)
    
    print("\nCounts by Status:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
        
    print("\nCounts by Family:")
    for family, count in family_counts.items():
        print(f"  {family}: {count}")
        
    print("\nFirst 5 coaches:")
    for c in coaches[:5]:
        print(f"  Coach: {c.get('coachno')}, Family: {c.get('family')}, Status: {c.get('status')}, Pit: {c.get('pitnum')}")
else:
    print("Failed to fetch from live API:", resp.status_code)
