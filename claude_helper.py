"""
claude_helper.py - lets the Control Panel talk to Claude Code (the command-line Claude) on this PC.

  python claude_helper.py --setup            check / install Claude Code, open the one-time sign-in window
  python claude_helper.py --ask "question"   ask a question (read-only: Claude may only read files)
  python claude_helper.py --ask "..." --continue   follow-up to the previous question

Read-only on purpose: Claude here can read the notes, scripts and ERP export, but cannot change files,
run commands, touch ERP or Google Sheets. Anything that writes is still done with the Control Panel jobs + YES.
"""
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # D:\Coach_Position_Apps
NOTES = os.path.join(ROOT, "CLAUDE_PROJECT_NOTES.md")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

READ_TOOLS = "Read,Grep,Glob"
BLOCKED = "Bash,PowerShell,Edit,Write,NotebookEdit,WebFetch,WebSearch"
RULES = (
    "You are answering a question typed by LW/PER (Loco Works, Perambur) coach-workshop staff in the "
    "Control Panel of their LWPER app. Before answering, read " + NOTES + " and follow its rules exactly "
    "(outturn = despatch date, FND, exclusions, coach groups, no AC locos). The latest ERP data is "
    + os.path.join(ROOT, "08_Claude_ERP_Export", "data", "erp_demands_latest.json") + ". "
    "You are READ-ONLY here: you cannot change files, ERP or Google Sheets and must not try. If something "
    "needs changing, say which Control Panel job to run or what JIJO should do. Never show passwords or keys. "
    "Answer briefly, in plain English, with figures where asked."
)


def find_claude():
    p = shutil.which("claude")
    if p:
        return p
    for c in (os.path.expandvars(r"%USERPROFILE%\.local\bin\claude.exe"),
              os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\claude.exe")):
        if os.path.exists(c):
            return c
    return None


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


# ------------------------------------------------------------------ setup
def setup():
    exe = find_claude()
    if not exe:
        print("Claude Code is NOT installed on this PC.")
        print("It installs for this Windows user only (no Administrator needed), from Anthropic's official installer.")
        if input("Type YES to install it now: ").strip() != "YES":
            print("Cancelled - nothing installed.")
            return
        tried = []
        if shutil.which("winget"):
            print("\nInstalling with winget (1-3 minutes, no progress shown)...")
            r = run(["winget", "install", "--id", "Anthropic.ClaudeCode", "-e",
                     "--accept-source-agreements", "--accept-package-agreements"])
            print(r.stdout[-1500:] or r.stderr[-1500:])
            tried.append("winget")
        exe = find_claude()
        if not exe:
            print("\nInstalling with the official PowerShell installer (1-3 minutes, no progress shown)...")
            r = run(["powershell", "-NoProfile", "-Command", "irm https://claude.ai/install.ps1 | iex"])
            print(r.stdout[-1500:] or r.stderr[-1500:])
            tried.append("PowerShell installer")
        exe = find_claude()
        if not exe:
            print("\nNOT INSTALLED (" + " and ".join(tried) + " did not work).")
            print("Probably blocked by the office PC security (Trellix / CRIS policy). Ask the system admin to allow")
            print("'Claude Code' from claude.ai (Anthropic) for this user, then run this check again.")
            return
        print("\nInstalled.")
    r = run([exe, "--version"])
    print(f"Claude Code found: {exe}\nVersion: {(r.stdout or r.stderr).strip()}")

    print("\nChecking sign-in with a one-line test question...")
    r = run([exe, "-p", "Reply with the single word OK", "--disallowedTools", BLOCKED], cwd=ROOT, timeout=180,
            stdin=subprocess.DEVNULL)
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 0 and "OK" in out.upper():
        print("Signed in - working. Use the 'Ask Claude' box on the Control Panel.")
        return
    print("Not signed in yet:\n  " + out[-600:].replace("\n", "\n  "))
    print("\nA Claude window will open. Choose the login with your Claude account, finish in the browser,")
    print("then type /exit in that window and run this check again.")
    if input("Type YES to open the sign-in window: ").strip() == "YES":
        flags = 0x00000010 if os.name == "nt" else 0          # CREATE_NEW_CONSOLE
        # cmd /k keeps the window open if Claude stops, so any message stays readable
        cmd = ["cmd", "/k", exe] if os.name == "nt" else [exe]
        subprocess.Popen(cmd, cwd=ROOT, creationflags=flags)
        print("Sign-in window opened.")


# ------------------------------------------------------------------ ask
def _short(inp):
    for k in ("file_path", "pattern", "path", "glob"):
        if inp.get(k):
            return str(inp[k])
    return ""


def ask(question, cont=False):
    exe = find_claude()
    if not exe:
        print("Claude Code is not installed yet - run 'Claude - check / set up' first.")
        sys.exit(1)
    cmd = [exe, "-p", question, "--output-format", "stream-json", "--verbose",
           "--allowedTools", READ_TOOLS, "--disallowedTools", BLOCKED, "--append-system-prompt", RULES]
    if cont:
        cmd.append("--continue")
    print(f"Q: {question}\n(read-only; usually 30 s - 3 min)\n")
    t0 = time.time()
    flags = 0x08000000 if os.name == "nt" else 0               # CREATE_NO_WINDOW
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=flags)
    for raw in p.stdout:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            print(line)
            continue
        typ = ev.get("type")
        if typ == "assistant":
            for b in (ev.get("message") or {}).get("content", []):
                if b.get("type") == "text" and b.get("text", "").strip():
                    print(b["text"].strip() + "\n")
                elif b.get("type") == "tool_use":
                    print(f"  [{b.get('name')}: {_short(b.get('input') or {})}]")
        elif typ == "result":
            if ev.get("is_error"):
                print("ERROR: " + str(ev.get("result") or ev.get("subtype")))
            print(f"(answered in {time.time() - t0:.0f} s)")
    p.wait()
    sys.exit(p.returncode)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--setup"]:
        try:
            setup()
        except Exception as e:
            print(f"ERROR: {e}")
    elif a[:1] == ["--ask"] and len(a) > 1:
        ask(a[1], "--continue" in a[2:])
    else:
        print(__doc__)
