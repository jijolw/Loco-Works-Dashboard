"""
staff_app.py - Daily Position Report app for staff (JIJO 31-10-2026).

A separate small app on the office PC: http://127.0.0.1:5050
Only the Daily Position form (daily items) + the report + a 'Get latest ERP data' button (read-only export).
No menu, no Control Panel, no Update_All, no Google Sheet or ERP writing.
Holidays and monthly targets are changed only in JIJO's app (Office PC > Daily Report).
Same saved inputs (data/daily_report.json) as JIJO's app, so both make the same report.

Start: double-click D:\\Coach_Position_Apps\\Daily_Position_Report.pyw (starts this hidden and opens the browser).
"""
from datetime import timedelta

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

import config
from analysis import position as P
from core import data, rules as R

PORT = 5050
app = Flask(__name__)


@app.before_request
def _only_this_pc():
    if request.remote_addr not in ("127.0.0.1", "::1"):
        abort(403)


def _ctx():
    D, ex = data.load()
    if not D:
        return None, None, None, None
    report_date = ex.date()
    return D, ex, report_date, report_date - timedelta(days=1)


@app.route("/", methods=["GET", "POST"])
def form():
    from core import daily_inputs as DI
    inp = DI.load()
    if request.method == "POST":
        inp = DI.save(DI.from_form(request.form, inp, staff=True))
        if request.form.get("action") == "report":
            return redirect(url_for("report"))
        return redirect(url_for("form", saved=1))
    D, ex, report_date, as_on = _ctx()
    wd = DI.working_days(as_on, inp) if as_on else None
    plan_status = {}
    if D:
        latest = R.latest_per_coach(D)
        for i, p in enumerate(inp.get("plan", [])):
            d = latest.get(R.coach_key({"coachNo": (p.get("coach") or "x").split()[-1]}))
            if not d:
                plan_status[i] = "not found in ERP"
            elif d.get("actualDispatchDate"):
                plan_status[i] = "Despatched " + R.fmt(R.pdate(d["actualDispatchDate"]))
            elif d.get("dispatchDate"):
                plan_status[i] = "Outturned " + R.fmt(R.pdate(d["dispatchDate"])) + " - FND"
            elif R.pdate(p.get("desp_pdc")) and R.pdate(p.get("desp_pdc")) <= as_on:
                plan_status[i] = "OVERDUE"
    return render_template("staff_daily.html", inp=inp, wd=wd, exported=ex, report_date=report_date, as_on=as_on,
                           saved=request.args.get("saved"), typed_fields=DI.TYPED_FIELDS, plan_status=plan_status)


@app.route("/report")
def report():
    from analysis import daily_report as DR
    from core import condemnation, daily_inputs as DI
    D, ex, report_date, as_on = _ctx()
    if not D:
        abort(503, "No ERP data yet - press 'Get latest ERP data'.")
    inp = DI.load()
    cond, _ = condemnation.load(live=True)
    return DR.build(D, ex, inp, DI.working_days(as_on, inp), [r["coach"] for r in cond.get("rows", [])],
                    as_on=as_on, report_date=report_date, back_url="/")


@app.route("/erp", methods=["POST"])
def erp_refresh():
    from core import erp_client
    started = erp_client.refresh_in_background(push_online=False)     # read-only export; no online upload
    return jsonify(started=started, **erp_client.status)


@app.route("/erp/status")
def erp_status():
    from core import erp_client
    return jsonify(**erp_client.status)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
