#!/usr/bin/env python3
"""
Standalone Daily Report Generator
==================================
Generates the "Type-Wise Holding & POH Performance Report" Excel file
WITHOUT needing the full Flask Workshop Intelligence System to be running.

USAGE
-----
    python generate_daily_report.py
    python generate_daily_report.py --month July --year 2026
    python generate_daily_report.py --outdir "D:\\JIJO\\Reports"

If no --month/--year is given, it defaults to the CURRENT month/year.
On Windows, you can also just double-click run_report.bat.

FOLDER LAYOUT EXPECTED
-----------------------
This script must sit in the same folder as your existing project root,
i.e. next to config.py and the services/ folder:

    <project_root>/
        config.py                          <- your existing ERP settings
        generate_daily_report.py           <- THIS FILE
        run_report.bat                     <- double-click launcher (Windows)
        services/
            __init__.py                    <- must exist (can be empty)
            erp_service.py
            decoders.py
            type_wise_holding_service.py
        reports/                           <- auto-created, xlsx files saved here

Nothing else (db_service.py, performance_service.py, your Flask app.py, etc.)
is required for this report specifically.
"""

import sys
import os
import argparse
import traceback
from datetime import datetime

# Make sure this folder is on sys.path so `services.*` imports resolve,
# regardless of where the script is launched from (double-click, cmd, etc.)
# Ensure this folder is on sys.path so `services.*` imports resolve.
# When frozen into an .exe by PyInstaller, __file__ points inside a temp
# extraction folder, not where the .exe actually sits -- so we must use
# sys.executable instead in that case, to keep the reports/ folder (and
# credentials.json lookup) next to the .exe itself.
if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "reports")

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def parse_args():
    today = datetime.now()
    parser = argparse.ArgumentParser(
        description="Generate the Type-Wise Holding & POH Performance Report (xlsx)."
    )
    parser.add_argument(
        "--month", default=MONTHS[today.month - 1],
        help="Month name, e.g. July (default: current month)"
    )
    parser.add_argument(
        "--year", default=today.year, type=int,
        help="Year, e.g. 2026 (default: current year)"
    )
    parser.add_argument(
        "--outdir", default=DEFAULT_OUTPUT_DIR,
        help=f"Folder to save the report into (default: {DEFAULT_OUTPUT_DIR})"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    month_name = args.month.strip().capitalize()
    year_val = args.year

    if month_name not in MONTHS:
        print(f"ERROR: '{args.month}' is not a valid month name.")
        print(f"       Use one of: {', '.join(MONTHS)}")
        sys.exit(1)

    print(f"Generating Type-Wise Holding & POH report for {month_name} {year_val} ...")

    # --- Import check ---
    try:
        from services.type_wise_holding_service import generate_type_wise_holding_excel
    except ModuleNotFoundError as e:
        print("\nERROR: Could not import services.type_wise_holding_service")
        print(f"       Details: {e}")
        print("\nCheck that:")
        print("  1. This script sits in the SAME folder as your 'services' folder.")
        print("  2. 'services' contains: erp_service.py, decoders.py, type_wise_holding_service.py")
        print("  3. 'services' has an __init__.py file (even an empty one) so Python treats it as a package.")
        print("  4. 'config.py' (with COACH_ERP_BASE_URL etc.) exists next to this script.")
        sys.exit(1)
    except ImportError as e:
        print("\nERROR: A dependency failed to import (check config.py / requests / gspread are installed).")
        print(f"       Details: {e}")
        sys.exit(1)

    # --- Generate the report ---
    try:
        excel_bytes = generate_type_wise_holding_excel(month_name, year_val)
    except FileNotFoundError as e:
        print("\nERROR: A required file was not found.")
        print(f"       Details: {e}")
        print("       This is most likely the Google service-account credentials.json")
        print("       (CREDENTIALS_PATH is hardcoded in type_wise_holding_service.py).")
        sys.exit(1)
    except Exception:
        print("\nERROR: Report generation failed. Full details below:\n")
        traceback.print_exc()
        sys.exit(1)

    # --- Save the file ---
    os.makedirs(args.outdir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"TypeWise_Holding_POH_{month_name.upper()}_{year_val}_{timestamp}.xlsx"
    filepath = os.path.join(args.outdir, filename)

    with open(filepath, "wb") as f:
        f.write(excel_bytes)

    print(f"\nDone. Report saved to:\n  {filepath}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("\nFATAL UNHANDLED ERROR:")
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
