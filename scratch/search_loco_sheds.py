import os

search_dir = r"C:\Users\User\.gemini\antigravity\scratch\ERP"
for root, dirs, files in os.walk(search_dir):
    if "venv" in root or ".git" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith((".py", ".js", ".html", ".css", ".txt", ".json")):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "lgd" in content.lower() or "rpm" in content.lower():
                        print(f"Found in {path}")
            except Exception:
                pass
