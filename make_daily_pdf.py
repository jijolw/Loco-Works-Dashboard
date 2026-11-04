"""
make_daily_pdf.py - make the Daily Position report PDF on the office PC without opening any app (Claude, 04-11-2026).

Uses the latest ERP export (run daily_sync.py / Get latest ERP data first), the saved daily items
(data/daily_report.json - typed by staff), the Condemnation_Pipeline copy and the AC Loco Bay from ERP.
Same report as the staff app's "Save & make report" -> printed to PDF with Microsoft Edge (or Chrome) headless.

    python make_daily_pdf.py            -> D:\\Coach_Position_Apps\\DailyPosition<ddmmyyyy>.pdf (report date)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

from analysis import daily_report as DR        # noqa: E402
from core import condemnation, data, daily_inputs as DI   # noqa: E402

BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]


def main():
    D, ex = data.load()
    if not D:
        sys.exit("No ERP export - run daily_sync.py first.")
    report_date = ex.date()
    as_on = DI.position_date(report_date)
    inp = DI.load()
    cond, err = condemnation.load(live=True)
    if err:
        print("NOTE:", err)
    html = DR.build(D, ex, inp, DI.working_days(as_on, inp), [r["coach"] for r in cond.get("rows", [])],
                    as_on=as_on, report_date=report_date, back_url="/")
    html_path = os.path.join(HERE, "data", "daily_report_print.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    out = os.path.normpath(os.path.join(HERE, "..", "..", f"DailyPosition{report_date:%d%m%Y}.pdf"))
    exe = next((b for b in BROWSERS if os.path.exists(b)), None)
    if not exe:
        sys.exit(f"No Edge/Chrome found - open {html_path} and print to PDF by hand.")
    subprocess.run([exe, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                    f"--print-to-pdf={out}", "file:///" + html_path.replace("\\", "/")], check=False, timeout=120)
    if not os.path.exists(out):
        sys.exit("PDF not made - check the browser.")
    print(f"ERP data {ex:%d-%m-%Y %H:%M} | report date {report_date:%d-%m-%Y} | position as on {as_on:%d-%m-%Y}")
    print("PDF:", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
