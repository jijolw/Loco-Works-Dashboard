import requests
from bs4 import BeautifulSoup

AC_BASE = "http://locoworks/acloco"
USERNAME = "07602546"
PASSWORD = "08041977"

try:
    sess = requests.Session()
    sess.post(f"{AC_BASE}/login", data={"username": USERNAME, "password": PASSWORD})
    r = sess.get(f"{AC_BASE}/Position")
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")
    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
    
    print("Columns in Position Page:")
    for idx, h in enumerate(headers):
        print(f"  Col {idx}: {h}")
        
    print("\nRows in Position Page:")
    for row in rows[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if cells:
            print(f"Loco: {cells[2]}")
            for idx, c in enumerate(cells):
                if c:
                    print(f"  Col {idx} ({headers[idx]}): {c}")
except Exception as e:
    print(f"Error: {e}")
