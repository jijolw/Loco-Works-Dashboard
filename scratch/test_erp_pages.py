import requests

base_url = "http://10.185.78.45/coach"
endpoints = [
    "/",
    "/login",
    "/aerial/view",
    "/aerial/view/aclocos.json",
    "/pohmaster/listdata2.html"
]

sess = requests.Session()
# Perform login to see if auth is okay
login_url = f"{base_url}/login"
payload = {"username": "admin", "password": "password"} # Fallback, let's read from config
try:
    from config import COACH_ERP_USERNAME, COACH_ERP_PASSWORD
    payload = {"username": COACH_ERP_USERNAME, "password": COACH_ERP_PASSWORD}
except:
    pass

print("Testing ERP login...")
try:
    r = sess.post(login_url, data=payload, timeout=10)
    print(f"Login response: {r.status_code}")
except Exception as e:
    print(f"Login failed: {e}")

for ep in endpoints:
    url = f"{base_url}{ep}"
    print(f"Testing GET {url}...")
    try:
        r = sess.get(url, timeout=10)
        print(f"  Status: {r.status_code}")
        print(f"  Content Type: {r.headers.get('Content-Type')}")
        print(f"  Content length: {len(r.content)} bytes")
        if r.status_code != 200:
            print(f"  Snippet: {r.text[:200]}")
    except Exception as e:
        print(f"  Failed: {e}")
