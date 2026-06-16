import os
import sys

filepath = r"C:\Users\User\.gemini\antigravity\scratch\Supabase_ERP\static\js\app.js"

sys.stdout.reconfigure(encoding='utf-8')

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "filterLiveByType" in line or "filterLiveByDivision" in line:
        print(f"Line {idx+1}: {line.strip()}")
