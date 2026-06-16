import requests
import json

try:
    resp = requests.get("http://127.0.0.1:5000/api/aerial")
    if resp.ok:
        data = resp.json()
        ac_locos = data.get("ac_locos", [])
        print(f"Total ac_locos: {len(ac_locos)}")
        if ac_locos:
            print(json.dumps(ac_locos[0], indent=2))
        else:
            print("No ac_locos in API response")
    else:
        print(f"Failed to fetch: {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")
