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


HIDDEN = "--hidden" in sys.argv          # started at Windows login by pythonw: no window, no browser


def _already_running(port):
    import socket
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


if __name__ == "__main__":
    if HIDDEN:                            # pythonw has no console - keep a log instead
        os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
        sys.stdout = sys.stderr = open(os.path.join(HERE, "data", "run_app_hidden.log"), "a", encoding="utf-8", buffering=1)
    try:
        if not HIDDEN:
            check_packages()
        from core import setup_env
        setup_env.ensure(interactive=not HIDDEN)
        import config
        url = f"http://127.0.0.1:{config.PORT}"
        if _already_running(config.PORT):        # app already started (e.g. at login) - just open it
            if not HIDDEN:
                webbrowser.open(url)
            sys.exit(0)
        from app import app
        print(f"{time.strftime('%d-%m-%Y %H:%M')} LW/PER Coach POH app running at {url}")
        if not HIDDEN:
            print("(close this window to stop)")
            threading.Thread(target=lambda: (time.sleep(1.5), webbrowser.open(url)), daemon=True).start()
        app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        if not HIDDEN:
            input(f"\nERROR: {e}\nPress Enter to close.")
