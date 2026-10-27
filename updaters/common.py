"""updaters/common.py - Google Sheets access for the update tools (service account on the office PC)."""
import os

CRED_PATHS = [r"D:\JIJO\information\Coach Position\credentials.json", r"D:\TypeWiseHoldingApp\credentials.json"]
HQ_KM_SHEET_KEY = "1M3eSBWsa4Lp4NzQhEqRNGiCIxNgmSmdHIW-0N8IhUxk"     # HQ 2026 KM SPLs - READ ONLY, never opened for writing


def open_sheet(key):
    """Open one of OUR sheets for writing. Refuses the HQ sheet."""
    if key == HQ_KM_SHEET_KEY:
        raise SystemExit("Refused: the HQ KM sheet is never written.")
    import gspread
    from google.oauth2.service_account import Credentials
    last = None
    for p in CRED_PATHS:
        if not os.path.exists(p):
            continue
        try:
            creds = Credentials.from_service_account_file(p, scopes=["https://www.googleapis.com/auth/spreadsheets"])
            return gspread.authorize(creds).open_by_key(key)
        except Exception as e:
            last = e
    raise RuntimeError(f"No service-account credentials could open sheet {key}: {last}")
