# =====================================================
# config.py
# LW/PER Workshop Intelligence System
# Centralized configuration — edit ONLY this file
# =====================================================

import os

# Try to load .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    base_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(base_dir, ".env"))
except ImportError:
    pass

# ── Coach ERP ─────────────────────────────────────────
COACH_ERP_BASE_URL = os.environ.get("COACH_ERP_BASE_URL", "http://10.185.78.45")
COACH_ERP_USERNAME = os.environ.get("COACH_ERP_USERNAME", "07602546")
COACH_ERP_PASSWORD = os.environ.get("COACH_ERP_PASSWORD", "08041977")

# ── AC Loco ERP ──────────────────────────────────────
ACLOCO_ERP_BASE_URL = os.environ.get("ACLOCO_ERP_BASE_URL", "http://locoworks/acloco")
ACLOCO_ERP_USERNAME = os.environ.get("ACLOCO_ERP_USERNAME", "07602546")
ACLOCO_ERP_PASSWORD = os.environ.get("ACLOCO_ERP_PASSWORD", "08041977")

# ── Cache TTL (seconds) ──────────────────────────────
CACHE_TTL_MASTER   = int(os.environ.get("CACHE_TTL_MASTER", 300))
CACHE_TTL_SINGLE   = int(os.environ.get("CACHE_TTL_SINGLE", 300))
CACHE_TTL_AERIAL   = int(os.environ.get("CACHE_TTL_AERIAL", 120))
CACHE_TTL_STATIC   = int(os.environ.get("CACHE_TTL_STATIC", 3600))

# ── Flask ────────────────────────────────────────────
FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5001))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

# ── Supabase ─────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ykksfdiyczolhqnduwkh.supabase.co/rest/v1")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlra3NmZGl5Y3pvbGhxbmR1d2toIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTA3ODk0OCwiZXhwIjoyMDk2NjU0OTQ4fQ.67jORriOLnHf0WGcYtxr4dQkgFPw7JZEJm8xlfysWFM")

# ── Google Sheets ────────────────────────────────────
GOOGLE_SHEET_KEY = os.environ.get("GOOGLE_SHEET_KEY", "17_yzOhhdSy0EQAqLpfuXMPJazsgtlW7QspNvYJLI2Qk")
GOOGLE_CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "D:\\JIJO\\information\\Coach Position\\credentials.json")


