import re

path = r"C:\Users\User\.gemini\antigravity\scratch\ERP\scratch\acloco_page_text.txt"

with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Let's extract lines that look like loco rows, e.g. starting with priority numbers
# and listing dates and sheds
lines = text.split("\n")
rows = []
current_row = []

for line in lines:
    line = line.strip()
    if not line:
        continue
    # If line starts with digit + space + month (e.g. "1 MAY")
    if re.match(r"^\d+\s+[A-Z]{3}", line):
        if current_row:
            rows.append(" ".join(current_row))
        current_row = [line]
    elif current_row:
        # Check if we hit the next table header or next section
        if "details of lhb" in line.lower() or "type-wise break-up" in line.lower():
            break
        current_row.append(line)

if current_row:
    rows.append(" ".join(current_row))

print(f"Parsed {len(rows)} rows of AC Locos:")
for r in rows:
    print(r)
