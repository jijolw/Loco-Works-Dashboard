import os

search_dir = r"C:\Users\User"
print(f"Searching for 'claude' folders or 'dailyposition' files...")
matches = []

for root, dirs, files in os.walk(search_dir):
    # Check current directory
    dir_name = os.path.basename(root).lower()
    if "claude" in dir_name:
        print(f"Found 'claude' folder: {root}")
        matches.append(root)
        
    for file in files:
        if "dailyposition" in file.lower() or "daily_position" in file.lower():
            path = os.path.join(root, file)
            # Only print if it's in a 'claude' folder or not in Downloads
            if "telegram" not in path.lower() and "downloads" not in path.lower():
                print(f"Found other dailyposition file: {path}")
                matches.append(path)

print(f"Search complete. Total matches: {len(matches)}")
