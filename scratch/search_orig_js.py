import os

filepath = r"C:\Users\User\.gemini\antigravity\scratch\ERP\static\js\app.js"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Let's find any occurrences of "coaches/progress" or "fetchProgressData" or "AC LOCO" or "progress" in relation to AC Locos
lines = content.splitlines()
print(f"Total lines in original app.js: {len(lines)}")

# Search for progress tracker tabs, let's search for "loadCoachProgress"
start = -1
for idx, line in enumerate(lines):
    if "loadCoachProgress" in line:
        start = idx
        break

if start != -1:
    print("Found loadCoachProgress around line:", start + 1)
    for i in range(max(0, start - 5), min(len(lines), start + 80)):
        print(f"{i+1}: {lines[i]}")
