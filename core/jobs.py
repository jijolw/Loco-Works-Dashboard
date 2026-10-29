"""
core/jobs.py - the Control Panel's job runner (office PC only).

Runs ONLY the scripts listed in JOBS below, exactly as their .bat files do, with a live console in the browser.
Prompts inside the scripts (Type YES ...) are answered from the page, so every write still needs a typed YES.
One job at a time. Nothing here is available online (Render).
"""
import os
import subprocess
import sys
import threading
import time
from collections import OrderedDict
from datetime import datetime

import config

ROOT = os.path.normpath(os.path.join(config.APP_DIR, "..", ".."))       # D:\Coach_Position_Apps
APP = config.APP_DIR


def _p(*parts):
    return os.path.join(ROOT, *parts)


# key -> (title, description, writes?, [ (folder, script, args) ... ])
JOBS = OrderedDict([
    ("daily", ("Daily sync", "ERP export, targets + KM status (read only), online website, project files to Drive. "
               "No Google Sheet is written.", False,
               [(APP, "daily_sync.py", []), (_p("09_Drive_Sync"), "project_files_to_drive.py", [])])),
    ("update_all", ("Update all sheets", "KM tab, YARD / ICF NAC / LHB, PDC sheet, Achieved columns, online snapshot. "
                    "Shows a preview first - type YES to write.", True, [(APP, "update_all.py", [])])),
    ("letters_preview", ("Letters - preview", "Which new letters would go to Google Drive (nothing copied).", False,
                         [(_p("09_Drive_Sync"), "weekly_letters_sync.py", ["--preview"])])),
    ("letters", ("Monday letters update", "New letter PDFs to Google Drive + rebuild the letters search index.", True,
                 [(_p("09_Drive_Sync"), "weekly_letters_sync.py", []), (_p("12_Letters_Index"), "build_letters_index.py", [])])),
    ("hours_preview", ("Man-hours - preview", "Register in 11_Hours_Entry\\inbox -> preview Excel (nothing written).", False,
                       [(_p("11_Hours_Entry"), "hours_entry.py", [])])),
    ("hours_apply", ("Man-hours - apply to ERP", "Applies the latest preview. YES, first row verified alone, YES again.", True,
                     [(_p("11_Hours_Entry"), "hours_entry.py", ["--apply"])])),
    ("fix_desp_preview", ("Fix actual despatch - preview", "Reads fix_list.txt (below). Nothing written.", False,
                          [(_p("13_Fix_Actual_Despatch"), "fix_actual_desp.py", [])])),
    ("fix_desp_apply", ("Fix actual despatch - apply", "Changes ERP actual despatch dates in fix_list.txt after YES.", True,
                        [(_p("13_Fix_Actual_Despatch"), "fix_actual_desp.py", ["--apply"])])),
    ("fix_status", ("Fix status (Return / Running)", "Reads status_list.txt (below), preview, then YES to change ERP.", True,
                    [(_p("14_Fix_Status"), "fix_status.py", [])])),
    ("claude_setup", ("Claude - check / set up", "Checks Claude Code on this PC; installs it and opens the one-time "
                      "sign-in after YES. Needed only for the 'Ask Claude' box.", False,
                      [(APP, "claude_helper.py", ["--setup"])])),
    # run from the 'Ask Claude' box, not listed in the table
    ("ask", ("Ask Claude", "", False, [(APP, "claude_helper.py", ["--ask"])])),
])
HIDDEN_JOBS = {"ask"}

# text files the page may show and edit (input lists of the tools above)
EDITABLE = OrderedDict([
    ("fix_list", (_p("13_Fix_Actual_Despatch", "fix_list.txt"),
                  "One line per coach: coach, wrong date or BLANK, correct date or BLANK")),
    ("status_list", (_p("14_Fix_Status", "status_list.txt"), "One coach per line; 'coach Return' or coach alone = Running")),
])
HOURS_INBOX = _p("11_Hours_Entry", "inbox")

_lock = threading.Lock()
state = {"job": None, "title": "", "running": False, "out": [], "started": None, "ended": None,
         "rc": None, "proc": None, "waiting": False}


def _append(text):
    if not text:
        return
    if state["out"] and not state["out"][-1].endswith("\n"):
        state["out"][-1] += text
    else:
        state["out"].append(text)
    # keep memory small
    if len(state["out"]) > 4000:
        del state["out"][:1000]


def _reader(proc):
    buf = b""
    while True:
        chunk = proc.stdout.read1(4096) if hasattr(proc.stdout, "read1") else proc.stdout.read(1)
        if not chunk:
            break
        buf += chunk
        try:
            text = buf.decode("utf-8")
            buf = b""
        except UnicodeDecodeError:
            continue
        for part in text.splitlines(keepends=True):
            _append(part)
        state["waiting"] = not text.endswith("\n")


def _run(key, extra_args):
    title, _, _, steps = JOBS[key]
    try:
        for i, (folder, script, args) in enumerate(steps, 1):
            if len(steps) > 1:
                _append(f"\n==== STEP {i} of {len(steps)}: {script} ====\n")
            path = os.path.join(folder, script)
            if not os.path.exists(path):
                _append(f"NOT FOUND: {path}\n")
                state["rc"] = 1
                break
            env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
            flags = 0x08000000 if os.name == "nt" else 0           # CREATE_NO_WINDOW
            py = sys.executable
            if py.lower().endswith("pythonw.exe"):           # app started hidden at login: use python.exe for the console
                py = py[:-len("pythonw.exe")] + "python.exe"
            proc = subprocess.Popen([py, "-u", path] + args + (extra_args if i == 1 else []),
                                    cwd=folder, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, env=env, creationflags=flags)
            state["proc"] = proc
            t = threading.Thread(target=_reader, args=(proc,), daemon=True)
            t.start()
            proc.wait()
            t.join(timeout=5)
            state["rc"] = proc.returncode
            if proc.returncode not in (0, None):
                _append(f"\n(stopped - exit code {proc.returncode})\n")
                break
    except Exception as e:
        _append(f"\nERROR: {e}\n")
        state["rc"] = 1
    finally:
        state.update(running=False, proc=None, waiting=False, ended=datetime.now().strftime("%H:%M:%S"))
        _append(f"\n==== {title} finished at {state['ended']} ====\n")
        _lock.release()


def start(key, extra_args=None):
    if key not in JOBS:
        return False, "Unknown job"
    if not _lock.acquire(blocking=False):
        return False, f"'{state['title']}' is still running - wait or press Stop."
    state.update(job=key, title=JOBS[key][0], running=True, out=[], rc=None, waiting=False,
                 started=datetime.now().strftime("%d-%m-%Y %H:%M:%S"), ended=None)
    _append(f"==== {JOBS[key][0]} started {state['started']} ====\n")
    threading.Thread(target=_run, args=(key, list(extra_args or [])), daemon=True).start()
    return True, "started"


def send(text):
    p = state.get("proc")
    if not p or p.poll() is not None:
        return False
    try:
        p.stdin.write((text + "\n").encode("utf-8"))
        p.stdin.flush()
        _append(text + "\n")
        state["waiting"] = False
        return True
    except Exception:
        return False


def stop():
    p = state.get("proc")
    if p and p.poll() is None:
        p.terminate()
        _append("\n(stopped by user)\n")
        return True
    return False


def snapshot(since=0):
    return dict(job=state["job"], title=state["title"], running=state["running"], waiting=state["waiting"],
                started=state["started"], ended=state["ended"], rc=state["rc"],
                lines=state["out"][since:], total=len(state["out"]))


def inbox_files():
    try:
        return sorted(f for f in os.listdir(HOURS_INBOX) if f.lower().endswith((".xls", ".xlsx")))
    except OSError:
        return []


def read_text(key):
    path = EDITABLE[key][0]
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def save_text(key, text):
    path = EDITABLE[key][0]
    if os.path.exists(path):
        bak = path + ".bak"
        try:
            with open(path, encoding="utf-8") as f, open(bak, "w", encoding="utf-8") as b:
                b.write(f.read())
        except OSError:
            pass
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.replace("\r\n", "\n"))
