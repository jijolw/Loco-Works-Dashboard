import requests
from config import COACH_ERP_BASE_URL, COACH_ERP_USERNAME, COACH_ERP_PASSWORD

sess = requests.Session()
login_url = f"{COACH_ERP_BASE_URL}/coach/login"
payload = {"username": COACH_ERP_USERNAME, "password": COACH_ERP_PASSWORD}

print("Logging in...")
r = sess.post(login_url, data=payload, timeout=10)
print("Login status:", r.status_code)

url = f"{COACH_ERP_BASE_URL}/coach/reports/aerialview/print.html"
print(f"Fetching {url}...")
try:
    r = sess.get(url, timeout=15)
    print("Response status:", r.status_code)
    print("Content length:", len(r.content))
    print("Headers:", dict(r.headers))
    print("HTML Snippet (first 1000 chars):")
    print(r.text[:1000])
    print("HTML Snippet (last 1000 chars):")
    print(r.text[-1000:])
except Exception as e:
    print("Fetch failed:", e)
