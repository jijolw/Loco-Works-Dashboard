"""
app.py - LW/PER Coach POH Workshop app (one codebase, local PC and online).

Local  (office PC) : python Run_App.py  -> http://127.0.0.1:5000
Online (Render)    : gunicorn app:app   with APP_MODE=online
"""
from datetime import date, datetime

from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for, abort

import config
from analysis import position as P
from core import data, rules as R

app = Flask(__name__)

NAV = [
    ("Position", [("dashboard", "Month Position"), ("holding", "Holding"), ("outturn", "Outturn")]),
    ("Analysis", [("cycle", "Cycle Time"), ("corrosion", "Corrosion Cycle"), ("hours", "Man-hours"),
                  ("prev_poh", "Previous POH"), ("targets", "Target vs Actual")]),
    ("Workshop", [("aerial", "Aerial View"), ("coach", "Coach Search"), ("reports", "Report Centre")]),
]
READY = {"dashboard", "holding", "outturn", "coach", "cycle", "corrosion", "hours", "prev_poh", "targets", "reports", "aerial"}


@app.context_processor
def _ctx():
    _, ex = data.load()
    return dict(NAV=NAV, READY=READY, IS_LOCAL=config.IS_LOCAL, as_on=ex,
                fmt=R.fmt, pdate=R.pdate, page=request.endpoint)


def _as_on():
    D, ex = data.load()
    if not D:
        abort(503, "No ERP data yet - press 'Update from ERP' (office PC).")
    return D, (ex.date() if ex else date.today())


# ---------------------------------------------------------------- pages
@app.route("/")
def dashboard():
    D, a = _as_on()
    mon = request.args.get("month")
    m = R.pdate(mon + "-01") if mon else None
    pos = P.month_position(D, a, m)
    return render_template("dashboard.html", pos=pos, others=P.others_list(D, date(a.year - 1, 4, 1)))


@app.route("/holding")
def holding():
    D, a = _as_on()
    return render_template("holding.html", h=P.holding_summary(D, a), bands=P.AGE_BANDS)


@app.route("/outturn")
def outturn():
    D, a = _as_on()
    fys = P.available_fys(D)
    fy = request.args.get("fy") or R.fy_of(a)
    return render_template("outturn.html", x=P.outturn_matrix(D, fy), fys=fys)


@app.route("/coach")
def coach():
    D, a = _as_on()
    q = (request.args.get("q") or "").strip()
    return render_template("coach.html", q=q, visits=P.coach_visits(D, q) if q else [],
                           is_excluded=R.is_excluded, location=R.location)


def _period(a):
    d0 = R.pdate(request.args.get("from")) or R.fy_start(R.fy_of(a))
    d1 = R.pdate(request.args.get("to")) or a
    return d0, min(d1, a)


@app.route("/cycle")
def cycle():
    from analysis import perf
    D, a = _as_on()
    d0, d1 = _period(a)
    c = perf.cycle_time(D, d0, d1)
    longest = sorted(c["items"], key=lambda i: -(i["total"] or 0))[:15]
    return render_template("cycle.html", c=c, d0=d0, d1=d1, longest=longest)


@app.route("/corrosion")
def corrosion():
    from analysis import perf
    D, a = _as_on()
    d0, d1 = _period(a)
    return render_template("corrosion.html", k=perf.corrosion(D, d0, d1, a), d0=d0, d1=d1)


@app.route("/hours")
def hours():
    from analysis import perf
    D, a = _as_on()
    d0, d1 = _period(a)
    return render_template("hours.html", h=perf.man_hours(D, d0, d1), d0=d0, d1=d1)


@app.route("/prev_poh")
def prev_poh():
    from analysis import perf
    D, a = _as_on()
    d0, d1 = _period(a)
    fam = request.args.get("family", "ALL")
    return render_template("prev_poh.html", p=perf.previous_poh(D, d0, d1, fam), d0=d0, d1=d1, family=fam,
                           families=[f for f in R.FAMILY_ORDER if f != "Others"])


def _targets(D, a, fy):
    from analysis import perf
    rows, err = perf.load_targets()
    return perf.targets_vs_actual(D, fy, a, rows), err


def _stock_targets(D, a, fy):
    from analysis import perf, stock_targets as S
    try:
        hq, rb = S.load_tab("HQ_Targets"), S.load_tab("RB_Targets")
        if not hq and not rb:
            return None, "Targets not read yet - run Update_All.py or press Update from ERP (office PC)."
        it, _ = perf.load_targets()
        return S.build(D, fy, a, hq, rb, it), None
    except Exception as e:
        return None, f"Could not read HQ_Targets / RB_Targets: {e}"


@app.route("/targets")
def targets():
    D, a = _as_on()
    fy = request.args.get("fy") or R.fy_of(a)
    t, err = _targets(D, a, fy)
    st, s_err = _stock_targets(D, a, fy)
    from core import targets_store
    return render_template("targets.html", t=t, err=err, s=st, s_err=s_err, fys=P.available_fys(D),
                           targets_read=targets_store.read_at())


REPORTS = [("dashboard", "Month Position (current month)"), ("holding", "Type-wise Holding"),
           ("outturn", "Month-wise Outturn (current FY)"), ("cycle", "POH Cycle Time + coach-wise"),
           ("corrosion", "Corrosion Cycle + month position"), ("hours", "Man-hours + final hours missing"),
           ("prev_poh", "Previous POH analysis"), ("targets", "Target vs Actual (current FY)")]
REPORT_DESC = {
    "dashboard": "Outturn, despatched, FND, holding yard/work by type; FND coach list",
    "holding": "Holding by type with yard/work, age bands and light/heavy",
    "outturn": "Group x month outturn by desp date",
    "cycle": "Avg/median/min/max entry->outturn, TFR->outturn, entry->physical; coach-wise sheet",
    "corrosion": "Corrosion days by type; completed / carry forward / under corrosion this month",
    "hours": "Pre-survey vs final hours, light/heavy, coaches with final hours missing",
    "prev_poh": "Outturns by workshop of last POH; LHB SS1/SS2/SS3",
    "targets": "Internal_Targets vs ERP outturn; months without target shown as '-'"}


@app.route("/reports")
def reports():
    D, a = _as_on()
    d0, d1 = _period(a)
    from analysis import checks, perf
    trows, _ = perf.load_targets()
    return render_template("reports.html", items=REPORTS, desc=REPORT_DESC, d0=d0, d1=d1,
                           checks=checks.run(D, a, trows or None))


@app.route("/reports/go")
def report_go():
    return redirect(url_for("download", what=request.args.get("what", "dashboard"),
                            **{"from": request.args.get("from", ""), "to": request.args.get("to", "")}))


@app.route("/next/<name>")
def soon(name):
    return render_template("soon.html", name=dict(i for _, items in NAV for i in items).get(name, name))


@app.route("/aerial")
def aerial():
    from analysis import aerial as A
    D, a = _as_on()
    return render_template("aerial.html", x=A.aerial(D, a, data.km_status()))


# ---------------------------------------------------------------- Excel downloads
@app.route("/download/<what>")
def download(what):
    from analysis import excel
    D, a = _as_on()
    if what == "dashboard":
        mon = request.args.get("month")
        bio, name = excel.month_position(P.month_position(D, a, R.pdate(mon + "-01") if mon else None), a)
    elif what == "holding":
        bio, name = excel.holding(P.holding_summary(D, a), a)
    elif what == "outturn":
        bio, name = excel.outturn(P.outturn_matrix(D, request.args.get("fy") or R.fy_of(a)), a)
    elif what in ("cycle", "corrosion", "hours", "prev_poh"):
        from analysis import perf
        d0, d1 = _period(a)
        if what == "cycle":
            bio, name = excel.cycle(perf.cycle_time(D, d0, d1), d0, d1, a)
        elif what == "corrosion":
            bio, name = excel.corrosion(perf.corrosion(D, d0, d1, a), d0, d1, a)
        elif what == "hours":
            bio, name = excel.hours(perf.man_hours(D, d0, d1), d0, d1, a)
        else:
            bio, name = excel.prev_poh(perf.previous_poh(D, d0, d1, request.args.get("family", "ALL")), d0, d1, a)
    elif what == "targets":
        fy = request.args.get("fy") or R.fy_of(a)
        t, _ = _targets(D, a, fy)
        st, _ = _stock_targets(D, a, fy)
        bio, name = excel.targets(t, a, st)
    else:
        abort(404)
    return send_file(bio, as_attachment=True, download_name=name,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ---------------------------------------------------------------- update (office PC only)
@app.route("/update", methods=["POST"])
def update():
    if not config.IS_LOCAL:
        abort(403)
    from core import erp_client
    started = erp_client.refresh_in_background(push_online=True)
    return jsonify(started=started, **erp_client.status)


@app.route("/update/status")
def update_status():
    if not config.IS_LOCAL:
        return jsonify(running=False)
    from core import erp_client
    return jsonify(**erp_client.status)


@app.route("/health")
def health():
    D, ex = data.load()
    return jsonify(mode=config.APP_MODE, demands=len(D), as_on=str(ex))


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False)
