import requests
import json

SUPABASE_URL = "https://ykksfdiyczolhqnduwkh.supabase.co/rest/v1"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlra3NmZGl5Y3pvbGhxbmR1d2toIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTA3ODk0OCwiZXhwIjoyMDk2NjU0OTQ4fQ.67jORriOLnHf0WGcYtxr4dQkgFPw7JZEJm8xlfysWFM"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

url = f"{SUPABASE_URL}/erp_active_coaches?status=eq.AC%20LOCO&select=*"
resp = requests.get(url, headers=headers)
if resp.ok:
    locos = resp.json()
    print(f"Retrieved {len(locos)} AC Locos from Supabase.")
    for idx, l in enumerate(locos[:3]):
        print(f"\nLoco {idx+1}: {l.get('coachno')}")
        print(f"  Make field (packed): {l.get('make')}")
else:
    print("Failed to query Supabase:", resp.text)
