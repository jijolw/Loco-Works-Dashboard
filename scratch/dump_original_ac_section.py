import os

aerial_path = r"D:\Information backup\Drive\Drive\deskktop\2026-27\login\Claude\aerial.py"
out_path = r"C:\Users\User\.gemini\antigravity\scratch\ERP\scratch\original_acloco_section.txt"

if os.path.exists(aerial_path):
    with open(aerial_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = content.split("\n")
    # Grab lines from 480 to 520, and from 1080 to 1250
    with open(out_path, "w", encoding="utf-8") as out:
        out.write("=== LINE 480 to 520 ===\n")
        for j in range(470, min(len(lines), 530)):
            out.write(f"{j+1}: {lines[j]}\n")
            
        out.write("\n=== LINE 1080 to 1250 ===\n")
        for j in range(1070, min(len(lines), 1250)):
            out.write(f"{j+1}: {lines[j]}\n")
    print(f"Written to {out_path}")
else:
    print("aerial.py not found")
