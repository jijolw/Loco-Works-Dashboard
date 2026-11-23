"""
core/erp_pdf.py - ERP's own "Daily Position PDF" (Outturn Reports -> PDF Reports) added after our 2 pages (JIJO 10-11-2026).
READ ONLY (GET). Address from JIJO's browser (DevTools, 10-11-2026):
  {ERP_API}/direct-reports/coach-position/pdf?reportPath=locos/coachposition   -> the whole 3-4 page report
(The Aerial View PDF's last page was used first by mistake - not wanted.)
Needs pypdf (Build_Daily_Position_EXE.bat installs and bundles it).
"""
import os
import shutil

import config

PATH = "/direct-reports/coach-position/pdf"
PARAMS = {"reportPath": "locos/coachposition"}


def fetch_report(sess, data_dir):
    """Download ERP's Daily Position PDF (all pages) -> path."""
    r = sess.get(config.ERP_API.rstrip("/") + PATH, params=PARAMS, timeout=120)
    if not r.ok or r.content[:4] != b"%PDF":
        raise RuntimeError(f"ERP answered {r.status_code} ({r.headers.get('content-type', '')}, {len(r.content)} bytes)")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "erp_daily_position.pdf")
    with open(path, "wb") as f:
        f.write(r.content)
    return path


def append(main_pdf, extra_pdf):
    """Add the pages of extra_pdf at the end of main_pdf (in place)."""
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter()
    for p in PdfReader(main_pdf).pages:
        w.add_page(p)
    for p in PdfReader(extra_pdf).pages:
        w.add_page(p)
    tmp = main_pdf + ".tmp"
    with open(tmp, "wb") as f:
        w.write(f)
    shutil.move(tmp, main_pdf)


def add_erp_page(main_pdf, data_dir, say=print):
    """Best effort: ERP's Daily Position PDF after our 2 pages. Our 2 pages always stay, whatever happens here."""
    if not (config.ERP_USERNAME and config.ERP_PASSWORD):
        say("    ERP Daily Position skipped - no ERP login in .env")
        return False
    try:
        from core import erp_client
        rep = fetch_report(erp_client.get_session(), data_dir)
        from pypdf import PdfReader
        n = len(PdfReader(rep).pages)
        append(main_pdf, rep)
        say(f"    ERP Daily Position PDF added after our 2 pages ({n} pages)")
        return True
    except ImportError:
        say("    ERP Daily Position skipped - pypdf not installed (run Build_Daily_Position_EXE.bat / pip install pypdf)")
    except Exception as e:
        say(f"    ERP Daily Position not added ({e}) - report has our 2 pages")
    return False
