"""
config.py - settings come from the .env file next to this file (never committed to Git)
or from environment variables (Render dashboard). No passwords or keys are written in code.

APP_MODE = local   -> office PC: reads the ERP export, can refresh from ERP and push to Supabase
APP_MODE = online  -> Render: view only, reads the last snapshot from Supabase
"""
import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(APP_DIR, ".env")


def _load_env_file(path=ENV_FILE):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env_file()


def get(key, default=""):
    return os.environ.get(key, default)


# On Render (RENDER env var is always set there) default to online; on the PC default to local
APP_MODE = get("APP_MODE", "online" if os.environ.get("RENDER") else "local").strip().lower()
IS_LOCAL = APP_MODE != "online"

# New Carriage ERP (railway intranet only)
ERP_BASE = get("ERP_BASE", "http://10.185.78.45")
ERP_API = get("ERP_API", ERP_BASE + "/intranet/api")
ERP_SSO = get("ERP_SSO", ERP_BASE + "/oauth2/authorization/keycloak")
ERP_USERNAME = get("ERP_USERNAME")
ERP_PASSWORD = get("ERP_PASSWORD")

# The ERP export file - the same file Claude reads (08_Claude_ERP_Export)
EXPORT_PATH = get("EXPORT_PATH", os.path.normpath(os.path.join(
    APP_DIR, "..", "..", "08_Claude_ERP_Export", "data", "erp_demands_latest.json")))

# Supabase (online copy). SUPABASE_URL = https://<project>.supabase.co  (no /rest/v1)
SUPABASE_URL = get("SUPABASE_URL").replace("/rest/v1", "").rstrip("/")
SUPABASE_KEY = get("SUPABASE_KEY")
SUPABASE_BUCKET = get("SUPABASE_BUCKET", "lwper")

# Google Sheets (targets / Kumbh Mela) - read through public gviz CSV
POSITION_SHEET_KEY = get("POSITION_SHEET_KEY", "17_yzOhhdSy0EQAqLpfuXMPJazsgtlW7QspNvYJLI2Qk")
HQ_KM_SHEET_KEY = get("HQ_KM_SHEET_KEY", "1M3eSBWsa4Lp4NzQhEqRNGiCIxNgmSmdHIW-0N8IhUxk")   # READ ONLY

HOST = get("HOST", "127.0.0.1" if IS_LOCAL else "0.0.0.0")
PORT = int(get("PORT", "5000"))
