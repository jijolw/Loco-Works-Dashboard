import os

log_path = r"C:\Users\User\.gemini\antigravity\brain\656fe9a0-a710-4d0f-a850-8f48aae9c7b3\.system_generated\tasks\task-2378.log"
if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        print(f.read())
else:
    print("Log file does not exist yet.")
