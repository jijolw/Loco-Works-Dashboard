import os

base_dir = r"C:\Users\User\.gemini\antigravity\scratch\ERP"

matches = []
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith((".py", ".js", ".html", ".json")):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "acloco" in content.lower() or "ac loco" in content.lower():
                        matches.append(filepath)
            except Exception:
                pass

print(f"Total files with AC Loco: {len(matches)}")
for m in matches:
    print(m)
