"""
daily_position_exe.py - Daily_Position.exe: makes the Daily Position report PDF in one double-click (JIJO 06-11-2026).
Works on any office PC on the railway network, without Python (built with Build_Daily_Position_EXE.bat).

  1. reads the latest data from the Carriage ERP (READ only) + the AC loco bay
  2. reads the staff's manual entries (Google sheet "Daily Position - Manual Entries") and the condemnation list
  3. makes DailyPosition<ddmmyyyy>.pdf (Microsoft Edge / Chrome prints it) and opens it

Needs, in the same folder as the .exe (never inside the .exe, never in chat or Git):
  .env              ERP_USERNAME=...  ERP_PASSWORD=...   (optional PDF_DIR=folder for the PDF)
  credentials.json  the Google service-account key (read-only use) - same file Update_All uses
Run with --no-erp to skip step 1 and use the last ERP data (e.g. when ERP is down).
"""
import os
import subprocess
import sys
import time
import traceback

if not getattr(sys, "frozen", False):
    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, HERE)
    os.chdir(HERE)

import config                                         # noqa: E402

BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]


BW_CSS = """
/* B/W print (JIJO 23-11-2026): FND = white on black, Corr. completed = boxed, condemnation = dashed underline, red -> black */
* { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
body, .red, .hred, span.orr, td, th { color: #000 !important; }
span.fndc, .lg span.fndc { background: #000 !important; color: #fff !important; font-weight: bold; padding: 0 2px; }
span.fndc * { color: #fff !important; }
span.ccc, .lg span.ccc { background: #fff !important; border: 1.3px solid #000; padding: 0 2px; font-weight: bold; }
span.cond, .lg span.cond { text-decoration: underline dashed #000 !important; text-decoration-thickness: 2px !important; text-underline-offset: 2px; }
span.orr { font-weight: bold; text-decoration: underline; }
span.fndc::after { content: "FND"; font-size: 5.6pt; vertical-align: super; margin-left: 2px; font-weight: bold; }
span.ccc::after { content: "CC"; font-size: 5.6pt; vertical-align: super; margin-left: 2px; font-weight: bold; }
span.cond::after { content: "COND"; font-size: 5.6pt; vertical-align: super; margin-left: 2px; font-weight: bold; text-decoration: none; display: inline-block; }
.lg span.fndc::after, .lg span.ccc::after, .lg span.cond::after, .mv span.cond::after { content: none; }
"""


def say(m):
    print(m, flush=True)


def make(get_erp=True, out_dir=None, open_pdf=True):
    from analysis import daily_report as DR
    from core import condemnation, data, daily_inputs as DI, erp_client, manual_sheet
    os.makedirs(os.path.join(config.APP_DIR, "data"), exist_ok=True)
    if get_erp:
        if not (config.ERP_USERNAME and config.ERP_PASSWORD):
            raise SystemExit(f"ERP login missing - put ERP_USERNAME / ERP_PASSWORD in {os.path.join(config.APP_DIR, '.env')}")
        say("1/3 Reading ERP (1-2 minutes)...")
        p = erp_client.build_export()
        say(f"    {p['count']} demands read at {p['exported_at']}")
    from core import physical                       # HQ OUT TURN = physical despatch (JIJO 10-11-2026), read only
    pl, perr = physical.refresh()
    say("    " + (perr or f"HQ OUT TURN read ({len(pl['rows'])} despatch rows)"))
    D, ex = data.load(force=True)
    if not D:
        raise SystemExit("No ERP data - run again with ERP reachable.")
    report_date = ex.date()
    inp = DI.load()
    as_on = DI.position_date(report_date, inp)
    say("2/3 Reading manual entries and condemnation list...")
    m, err = manual_sheet.load(live=True)
    if err:
        say("    NOTE: " + err)
    if m:
        say(f"    Manual entries: updated on {m.get('updated_on') or '?'} (read {m.get('read_at', 'saved copy')})")
    DI_inp = manual_sheet.apply(inp, as_on, m)
    from core import km as _km                      # HQ KM sheet, read only (page 1 KM line, JIJO 12-11-2026)
    try:
        km = _km.refresh()
    except Exception as e:
        km = _km.load()
        say(f"    NOTE: HQ KM sheet not read ({e}) - " + ("saved copy used" if km else "KM line left out"))
    cond, cerr = condemnation.load(live=True)
    if cerr:
        say("    NOTE: " + cerr)
    say("3/3 Making the PDF...")
    html = DR.build(D, ex, DI_inp, DI.working_days(as_on, DI_inp), [r["coach"] for r in cond.get("rows", [])],
                    as_on=as_on, report_date=report_date, back_url="/", km=km)
    html_path = os.path.join(config.APP_DIR, "data", "daily_report_print.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    out_dir = out_dir or config.get("PDF_DIR") or config.APP_DIR
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"DailyPosition{report_date:%d%m%Y}.pdf")
    exe = next((b for b in BROWSERS if os.path.exists(b)), None)
    if not exe:
        raise SystemExit(f"No Edge/Chrome found - open {html_path} and print it to PDF.")
    if os.path.exists(out):
        os.remove(out)
    # own profile folder: with Edge already open, a plain --headless run hands over to it and prints nothing
    prof = os.path.join(config.APP_DIR, "data", "edge_print_profile")
    url = "file:///" + html_path.replace("\\", "/")
    tries = [["--headless=new"], ["--headless=old"], ["--headless"]]
    for i, extra in enumerate(tries, 1):                 # a fresh profile each time: a hung Edge may still hold the last one
        cmd = [exe] + extra + ["--disable-gpu", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={prof}{i}",
                               "--no-pdf-header-footer", "--print-to-pdf-no-header", f"--print-to-pdf={out}", url]
        try:
            subprocess.run(cmd, check=False, timeout=60, capture_output=True)
        except subprocess.TimeoutExpired:
            say(f"    {extra[0]}: Edge did not finish in 60 s - trying the next way")
        for _ in range(10):
            if os.path.exists(out) and os.path.getsize(out) > 0:
                break
            time.sleep(0.5)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            break
    if not (os.path.exists(out) and os.path.getsize(out) > 0):
        # last way: open the report in the browser with the Print window ready - choose "Save as PDF", Save
        pr = html_path.replace(".html", "_print.html")
        with open(pr, "w", encoding="utf-8") as f:
            f.write(html.replace("</body>", "<script>window.addEventListener('load',()=>setTimeout(()=>window.print(),800));</script></body>"))
        say("    Edge could not print by itself - the report is opening; in the Print window choose 'Save as PDF' and Save"
            f" (folder: {out_dir}).")
        if os.name == "nt":
            os.startfile(pr)
        return pr
    if not os.path.exists(out):
        raise SystemExit("PDF not made - check Edge/Chrome.")
    # B/W copy of our 2 pages for a black-and-white printer (JIJO 23-11-2026): FND white on black, Corr. completed boxed
    try:
        bw_html = html_path.replace(".html", "_bw.html")
        with open(bw_html, "w", encoding="utf-8") as f:
            f.write(html.replace("</style>", BW_CSS + "</style>", 1))
        bw_out = out.replace(".pdf", "_BW.pdf")
        if os.path.exists(bw_out):
            os.remove(bw_out)
        bw_url = "file:///" + bw_html.replace("\\", "/")
        for i, extra in enumerate(tries, 1):
            cmd = [exe] + extra + ["--disable-gpu", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={prof}bw{i}",
                                   "--no-pdf-header-footer", "--print-to-pdf-no-header", f"--print-to-pdf={bw_out}", bw_url]
            try:
                subprocess.run(cmd, check=False, timeout=60, capture_output=True)
            except subprocess.TimeoutExpired:
                pass
            for _ in range(10):
                if os.path.exists(bw_out) and os.path.getsize(bw_out) > 0:
                    break
                time.sleep(0.5)
            if os.path.exists(bw_out) and os.path.getsize(bw_out) > 0:
                break
        say(f"B/W PDF (2 pages, for the black-and-white printer): {bw_out}" if os.path.exists(bw_out)
            else "    B/W PDF not made - the colour PDF is fine.")
    except Exception as e:                                   # never stop the colour PDF for the B/W copy
        say(f"    B/W PDF not made ({e}) - the colour PDF is fine.")
    # then ERP's own Daily Position PDF (3-4 pages, JIJO 10-11-2026); our 2 pages stay even if ERP fails
    from core import erp_pdf
    erp_pdf.add_erp_page(out, os.path.join(config.APP_DIR, "data"), say)
    say(f"\nERP data {ex:%d-%m-%Y %H:%M} | report date {report_date:%d-%m-%Y} | position as on {as_on:%d-%m-%Y}")
    say(f"PDF: {out}")
    if open_pdf and os.name == "nt":
        os.startfile(out)
    return out


if __name__ == "__main__":
    try:
        make(get_erp="--no-erp" not in sys.argv)
    except SystemExit as e:
        say(f"\nSTOPPED: {e}")
    except Exception:
        traceback.print_exc()
        say("\nSTOPPED - send a photo of this window to JIJO / Claude.")
    if "--no-pause" not in sys.argv:
        input("\nPress Enter to close...")
