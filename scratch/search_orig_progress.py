import os
import sys

filepath = r"C:\Users\User\.gemini\antigravity\scratch\ERP\static\js\app.js"

sys.stdout.reconfigure(encoding='utf-8')

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

start = -1
for idx, line in enumerate(lines):
    if "async function loadCoachProgress()" in line:
        start = idx
        break

if start != -1:
    print("Found loadCoachProgress at line:", start + 1)
    for i in range(start, min(len(lines), start + 270)):
        print(f"{i+1}: {lines[i]}", end="")
else:
    print("loadCoachProgress definition not found")
