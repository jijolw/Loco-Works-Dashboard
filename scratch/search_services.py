import os

search_dir = r"C:\Users\User\.gemini\antigravity\scratch\ERP\services"
for file in os.listdir(search_dir):
    if file.endswith(".py"):
        path = os.path.join(search_dir, file)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if "ac_session" in content or "acloco" in content:
                print(f"Found match in {file}:")
                for line in content.split("\n"):
                    if "ac_session" in line or "acloco" in line:
                        print(f"  {line.strip()}")
