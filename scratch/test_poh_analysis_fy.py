import urllib.request, json

for fy in ["2025-26", "2026-27"]:
    url = f"http://127.0.0.1:5000/api/poh/analysis?fy={fy}"
    try:
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        wks_count = len(data.get("workshops", {}))
        
        # Sum total coaches across all workshops in the response
        total_coaches = 0
        for wks, s in data.get("workshops", {}).items():
            total_coaches += len(s.get("coaches", []))
            
        print(f"FY {fy} - Workshops: {wks_count}, Total coaches in Previous Workshop Performance: {total_coaches}")
    except Exception as e:
        print(f"Error fetching for FY {fy}: {e}")
