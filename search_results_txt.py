with open("excel_search_results.txt", "r", encoding="utf-8") as f:
    content = f.read()
    
blocks = content.split("Checking: ")

print("POH-related Excel files:")
for b in blocks:
    if not b.strip():
        continue
    lines = b.splitlines()
    file_path = lines[0]
    
    if "poh" in file_path.lower():
        print(f"\nFile: {file_path}")
        # Print sheet names and headers
        for line in lines[1:]:
            if "sheets:" in line.lower() or "headers:" in line.lower() or "found keyword" in line.lower():
                print(f"  {line.strip()}")
