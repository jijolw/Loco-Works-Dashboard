import os
import sys

filepath = r"C:\Users\User\Supabase_ERP\static\js\app.js"
if not os.path.exists(filepath):
    filepath = r"C:\Users\User\.gemini\antigravity\scratch\Supabase_ERP\static\js\app.js"

sys.stdout.reconfigure(encoding='utf-8')

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "loadCoachProgress" in line:
        print(f"Line {idx+1}: {line.strip()}")
