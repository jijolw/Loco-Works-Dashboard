import sys

file_path = r"C:\Users\User\.gemini\antigravity\scratch\ERP\static\js\aerial.js"
out_path = r"C:\Users\User\.gemini\antigravity\scratch\ERP\scratch\search_aerial_output.txt"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

queries = ["csv", "button", "buildFilterControls"]

with open(out_path, "w", encoding="utf-8") as out:
    for q in queries:
        out.write(f"=== Matches for '{q}' ===\n")
        for idx, line in enumerate(lines):
            if q.lower() in line.lower():
                out.write(f"{idx+1}: {line.strip()}\n")
print("Done writing results.")
