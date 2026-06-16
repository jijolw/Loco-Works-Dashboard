import os

aerial_path = r"D:\Information backup\Drive\Drive\deskktop\2026-27\login\Claude\aerial.py"
if os.path.exists(aerial_path):
    print("aerial.py exists")
    with open(aerial_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Let's find lines relating to ac_locos or acloco
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "acloco" in line.lower() or "ac_loco" in line.lower() or "fetch_ac" in line.lower():
            start = max(0, i - 5)
            end = min(len(lines), i + 15)
            print(f"--- MATCH AT LINE {i+1} ---")
            for j in range(start, end):
                print(f"{j+1:4d}: {lines[j]}")
            print()
else:
    print("aerial.py not found")
