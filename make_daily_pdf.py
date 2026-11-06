"""
make_daily_pdf.py - make the Daily Position report PDF on the office PC from the LAST ERP export (Claude, 04-11-2026).
Same as Daily_Position.exe --no-erp, but the PDF goes to D:\\Coach_Position_Apps and nothing is opened.
Non-ERP items, working days, targets, NMGHS and notes come from the staff's manual-entry Google sheet (06-11-2026).

    python make_daily_pdf.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

from daily_position_exe import make   # noqa: E402

if __name__ == "__main__":
    make(get_erp=False, out_dir=os.path.normpath(os.path.join(HERE, "..", "..")), open_pdf=False)
