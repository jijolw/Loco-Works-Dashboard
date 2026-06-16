import os

search_dirs = [
    r"D:\Information backup\Drive\Drive\deskktop\2026-27\login\Claude",
    r"D:\Information backup\Drive\Drive\deskktop\2026-27\login",
]

for sdir in search_dirs:
    if os.path.exists(sdir):
        print(f"Listing directory: {sdir}")
        for file in os.listdir(sdir):
            path = os.path.join(sdir, file)
            if os.path.isdir(path):
                print(f"  [DIR] {file}")
            else:
                print(f"  [FILE] {file} ({os.path.getsize(path)} bytes)")
    else:
        print(f"Directory not found: {sdir}")
