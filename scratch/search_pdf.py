import os

print("Searching for PDF references in codebase...")
for root, dirs, files in os.walk('.'):
    # Skip standard folders
    if 'venv' in root or '.git' in root or '__pycache__' in root:
        continue
    for f in files:
        if f.endswith(('.py', '.js', '.html', '.css', '.txt')):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    if 'pdf' in content.lower():
                        print(f"Found 'pdf' in: {path}")
            except Exception as e:
                pass
