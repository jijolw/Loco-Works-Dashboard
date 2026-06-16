import os

search_dir = r"C:\Users\User"
print(f"Searching for 'dailyposition' files in {search_dir}...")
matches = []

exclude_dirs = {".git", ".venv", "myenv", "Local Settings", "node_modules", "__pycache__", "AppData", ".gemini"}

for root, dirs, files in os.walk(search_dir):
    # Prune directory search to speed it up
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    
    for file in files:
        if "dailyposition" in file.lower() or "daily_position" in file.lower():
            path = os.path.join(root, file)
            print(f"Found file: {path}")
            matches.append(path)
            
    # Also print if 'claude' folder is found
    if "claude" in os.path.basename(root).lower():
        print(f"Found 'claude' directory: {root}")
        matches.append(root)

print(f"Search complete. Total matches: {len(matches)}")
