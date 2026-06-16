import requests
from config import COACH_ERP_BASE_URL, COACH_ERP_USERNAME, COACH_ERP_PASSWORD

sess = requests.Session()
login_url = f"{COACH_ERP_BASE_URL}/coach/login"
payload = {"username": COACH_ERP_USERNAME, "password": COACH_ERP_PASSWORD}

print("Logging in...")
r = sess.post(login_url, data=payload, timeout=10)
print("Login status:", r.status_code)

url = f"{COACH_ERP_BASE_URL}/coach/pohmaster/listdata2.html"
headers = {"X-Requested-With": "XMLHttpRequest"}
data = {
    "draw": "1",
    "start": "0",
    "length": "10",  # limit to 10 to check response
    "search[value]": "",
    "search[regex]": "false",
    "order[0][column]": "1",
    "order[0][dir]": "asc",
    "columns[0][data]": "rno",
    "columns[0][searchable]": "true",
    "columns[0][orderable]": "true",
    "columns[1][data]": "coachno",
    "columns[1][searchable]": "true",
    "columns[1][orderable]": "true",
}

print("Sending POST to listdata2.html...")
try:
    r = sess.post(url, data=data, headers=headers, timeout=15)
    print("Response status:", r.status_code)
    print("Content length:", len(r.content))
    if r.status_code == 200:
        json_data = r.json()
        print("Success! Synced coaches count:", len(json_data.get("data", [])))
    else:
        print("Error response text snippet:", r.text[:500])
except Exception as e:
    print("POST failed:", e)
