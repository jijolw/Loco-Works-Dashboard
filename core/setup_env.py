"""
core/setup_env.py - first run on the office PC: create .env without typing, by copying the ERP login and the
Supabase settings from the OLD apps' config.py files (02_ERP_System\\ERP and \\Supabase_ERP), if they exist.
Only asks (hidden input) for what it cannot find. Values stay in .env on this PC - never in code or Git.
"""
import getpass
import os
import runpy

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(APP, ".env")
OLD = [os.path.join(APP, "..", "ERP", "config.py"), os.path.join(APP, "..", "Supabase_ERP", "config.py")]


def read_env():
    d = {}
    if os.path.exists(ENV):
        for line in open(ENV, encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def _from_old():
    found = {}
    for p in OLD:
        if not os.path.exists(p):
            continue
        try:
            g = runpy.run_path(p)
        except Exception:
            continue
        for new, old in (("ERP_USERNAME", "COACH_ERP_USERNAME"), ("ERP_PASSWORD", "COACH_ERP_PASSWORD"),
                         ("SUPABASE_URL", "SUPABASE_URL"), ("SUPABASE_KEY", "SUPABASE_KEY")):
            if g.get(old) and new not in found:
                found[new] = str(g[old])
    return found


def ensure(interactive=True):
    env = read_env()
    need = [k for k in ("ERP_USERNAME", "ERP_PASSWORD", "SUPABASE_URL", "SUPABASE_KEY") if not env.get(k)]
    if not need:
        return env
    old = _from_old()
    for k in need:
        if old.get(k):
            env[k] = old[k]
    if interactive and (not env.get("ERP_USERNAME") or not env.get("ERP_PASSWORD")):
        print("ERP login (stored only in .env on this PC)")
        env["ERP_USERNAME"] = env.get("ERP_USERNAME") or input("  ERP user name: ").strip()
        env["ERP_PASSWORD"] = env.get("ERP_PASSWORD") or getpass.getpass("  ERP password (not shown): ").strip()
    env.setdefault("APP_MODE", "local")
    env["SUPABASE_URL"] = env.get("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
    with open(ENV, "w", encoding="utf-8") as f:
        f.write("# LW/PER app settings - private to this PC, never shared or put in Git\n")
        for k, v in env.items():
            f.write(f"{k}={v}\n")
    took = [k for k in need if old.get(k)]
    if took:
        print("Settings copied from the old app config: " + ", ".join(took))
    return env
