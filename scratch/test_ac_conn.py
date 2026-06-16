import requests
from bs4 import BeautifulSoup

AC_BASE = "http://locoworks/acloco"
USERNAME = "07602546"
PASSWORD = "08041977"

try:
    sess = requests.Session()
    login_resp = sess.post(
        f"{AC_BASE}/login",
        data={"username": USERNAME, "password": PASSWORD},
        timeout=10
    )
    print(f"Login status: {login_resp.status_code}")
    
    pos_resp = sess.get(f"{AC_BASE}/Position", timeout=10)
    print(f"Position status: {pos_resp.status_code}")
    if pos_resp.ok:
        soup = BeautifulSoup(pos_resp.text, "html.parser")
        tables = soup.find_all("table")
        print(f"Found {len(tables)} tables")
        for i, table in enumerate(tables):
            rows = table.find_all("tr")
            print(f"Table {i} has {len(rows)} rows")
            if len(rows) > 1:
                headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
                print(f"Headers: {headers}")
                for row in rows[1:3]:
                    cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                    print(f"  Row: {cells}")
except Exception as e:
    print(f"Connection error: {e}")
