# =====================================================
# config.py
# LW/PER Workshop Intelligence System
# Centralized configuration — edit ONLY this file
# =====================================================

# ── Coach ERP (New Keycloak SSO Gateway) ─────────────
COACH_ERP_BASE_URL = "http://10.185.78.45"
COACH_ERP_SSO_URL  = "http://10.185.78.45/oauth2/authorization/keycloak"
COACH_ERP_API_BASE = "http://10.185.78.45/intranet/api"
COACH_ERP_USERNAME = "15713080065"
COACH_ERP_PASSWORD = "80065@jijo"

# ── AC Loco ERP ──────────────────────────────────────
ACLOCO_ERP_BASE_URL = "http://locoworks/acloco"
ACLOCO_ERP_USERNAME = "07602546"
ACLOCO_ERP_PASSWORD = "08041977"

# ── Cache TTL (seconds) ──────────────────────────────
CACHE_TTL_MASTER   = 300    # 5 min — master list
CACHE_TTL_SINGLE   = 300    # 5 min — single coach details
CACHE_TTL_AERIAL   = 120    # 2 min — aerial/AC loco
CACHE_TTL_STATIC   = 3600   # 1 hr  — year_built, coachmaster

# ── Gemini AI ─────────────────────────────────────────
import os
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyACFwclOTLOALZv9MLgrG7OvI8RG0nNNi4")

# ── Supabase ─────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ykksfdiyczolhqnduwkh.supabase.co/rest/v1")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlra3NmZGl5Y3pvbGhxbmR1d2toIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTA3ODk0OCwiZXhwIjoyMDk2NjU0OTQ4fQ.67jORriOLnHf0WGcYtxr4dQkgFPw7JZEJm8xlfysWFM")

# ── Google Sheets ────────────────────────────────────
GOOGLE_SHEET_KEY = os.environ.get("GOOGLE_SHEET_KEY", "17_yzOhhdSy0EQAqLpfuXMPJazsgtlW7QspNvYJLI2Qk")
GOOGLE_CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", r"D:\JIJO\information\Coach Position\credentials.json")

# ── Flask ────────────────────────────────────────────
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5001
FLASK_DEBUG = True

