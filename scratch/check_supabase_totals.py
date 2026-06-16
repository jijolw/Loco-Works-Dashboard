import requests

SUPABASE_URL = "https://ykksfdiyczolhqnduwkh.supabase.co/rest/v1"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlra3NmZGl5Y3pvbGhxbmR1d2toIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTA3ODk0OCwiZXhwIjoyMDk2NjU0OTQ4fQ.67jORriOLnHf0WGcYtxr4dQkgFPw7JZEJm8xlfysWFM"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Prefer": "count=exact"
}

tables = [
    "erp_active_coaches",
    "google_corrosion",
    "outturn_targets",
    "coach_movements",
    "manual_coach_updates"
]

print("=== Supabase Database Row Counts ===")
for t in tables:
    url = f"{SUPABASE_URL}/{t}?limit=1"
    resp = requests.get(url, headers=headers)
    if resp.ok:
        # Range header looks like: 0-0/12834
        content_range = resp.headers.get("Content-Range", "")
        count = content_range.split("/")[-1] if "/" in content_range else "0"
        print(f"Table '{t}': {count} rows")
    else:
        print(f"Table '{t}': Failed to query ({resp.status_code})")
