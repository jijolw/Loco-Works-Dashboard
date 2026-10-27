"""
Run_App.py - double-click to start the LW/PER Coach POH app on the office PC.
First run: copies the ERP login and Supabase settings from the old app config into .env
(asks only if not found). .env stays on this PC - never in code, never sent to Git.
"""
import os
import sys
import threading
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)


def check_packages():
    missing = []
    for mod, pkg in (("flask", "flask"), ("requests", "requests"), ("bs4", "beautifulsoup4"),
                     ("openpyxl", "openpyxl")):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("Installing:", ", ".join(missing))
        os.system(f'"{sys.executable}" -m pip install ' + " ".join(missing))


if __name__ == "__main__":
    try:
        check_packages()
        from core import setup_env
        setup_env.ensure()
        import config
        from app import app
        url = f"http://127.0.0.1:{config.PORT}"
        print(f"LW/PER Coach POH app running at {url}  (close this window to stop)")
        threading.Thread(target=lambda: (time.sleep(1.5), webbrowser.open(url)), daemon=True).start()
        app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        input(f"\nERROR: {e}\nPress Enter to close.")
