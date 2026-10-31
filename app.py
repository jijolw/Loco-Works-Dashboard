"""
app.py - LW/PER Coach POH Workshop app (one codebase, local PC and online).

Local  (office PC) : python Run_App.py  -> http://127.0.0.1:5000
Online (Render)    : gunicorn app:app   with APP_MODE=online
"""
import os
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
    ("Office PC", [("daily", "Daily Report"), ("tools", "Control Panel")]),
]
READY = {"dashboard", "holding", "outturn", "coach", "cycle", "corrosion", "hours", "prev_poh", "targets", "reports", "aerial", "tools",
         "daily"}


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
    from analysis import charts as C
    if not request.args.get("from"):                 # two financial years by default - bigger sample per workshop
        d0 = R.fy_start(R.fy_of(date(a.year - 1, a.month, 1)))
    p = perf.previous_poh(D, d0, d1, fam)
    wm = [w for w in perf.workmanship(D, d0, d1) if w["family"] in ("ICF", "LHB")]   # only these are also done elsewhere
    if fam != "ALL":
        wm = [w for w in wm if w["family"] == fam]
    for w in wm:
        w["chart"] = C.hbars([dict(label=r["wks"] + (" (ours)" if r["own"] else ""), value=r["pre"], own=r["own"],
                                   note=f"{r['gap']} mo · heavy {r['heavy_pct']}%") for r in w["rows"] if r["pre"]],
                             unit=" hrs")
    top = [r for r in p["rows"] if r["n"] >= 3][:12]
    ch = dict(count=C.hbars([dict(label=r["wks"], value=r["n"], note=f"{round(100 * r['n'] / p['n'])}%") for r in top]),
              hours=C.hbars([dict(label=r["wks"], value=r["pre"], note=f"heavy {r['heavy_pct']}%" if r["heavy_pct"] is not None else "")
                             for r in top if r["pre"]], unit=" hrs"),
              cycle=C.hbars([dict(label=r["wks"], value=r["cycle"]) for r in top if r["cycle"] is not None], unit=" days"))
    return render_template("prev_poh.html", p=p, ch=ch, wm=wm, own=", ".join(perf.OWN_SHOPS), d0=d0, d1=d1, family=fam,
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
    from analysis import charts as C
    ch = {}
    if st:
        erp = [r for r in st["rows"] if r["in_erp"]]
        ch["hq"] = C.bullets([dict(label=r["label"], actual=r["hq_a"], target=r["hq_t"]) for r in erp if r["hq_t"]])
        ch["rb"] = C.bullets([dict(label=r["label"], actual=r["a_all"], target=r["rb_todate"], band=r["rb_annual"],
                                   note=f"(annual {r['rb_annual']})") for r in erp if r["rb_annual"]])
        main = ["ICF|POH|NAC", "LHB|SS2/SS3|NAC", "LHB|SS2/SS3|AC", "EMU/MEMU|POH|NA", "DEMU/DTC/TC|POH|NA"]
        ch["monthly"] = C.monthly(st["months"], [dict(label=r["label"], actual=[c["a"] for c in r["cells"]],
                                                      target=[c["t"] for c in r["cells"]])
                                                 for k in main for r in st["rows"] if r["key"] == k])
    return render_template("targets.html", t=t, err=err, s=st, s_err=s_err, fys=P.available_fys(D),
                           targets_read=targets_store.read_at(), ch=ch)


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


# ---------------------------------------------------------------- Control Panel (office PC only)
def _local_only():
    if not config.IS_LOCAL or request.remote_addr not in ("127.0.0.1", "::1"):
        abort(403)


@app.route("/tools")
def tools():
    _local_only()
    from core import jobs
    return render_template("tools.html", jobs=jobs.JOBS, editable={k: (v[1], jobs.read_text(k)) for k, v in jobs.EDITABLE.items()},
                           inbox=jobs.inbox_files(), hidden=jobs.HIDDEN_JOBS)


@app.route("/tools/run/<key>", methods=["POST"])
def tools_run(key):
    _local_only()
    from core import jobs
    extra = []
    if key == "hours_preview":
        f = (request.form.get("file") or "").strip()
        if f and f in jobs.inbox_files():
            extra.append(os.path.join(jobs.HOURS_INBOX, f))
        if request.form.get("field") == "presurveyhrs":
            extra += ["--field", "presurveyhrs"]
    if key == "ask":
        q = (request.form.get("q") or "").strip()[:2000]
        if not q:
            return jsonify(ok=False, msg="Type a question first.")
        extra = [q] + (["--continue"] if request.form.get("cont") == "1" else [])
    ok, msg = jobs.start(key, extra)
    return jsonify(ok=ok, msg=msg)


@app.route("/tools/status")
def tools_status():
    _local_only()
    from core import jobs
    return jsonify(jobs.snapshot(int(request.args.get("since", 0))))


@app.route("/tools/input", methods=["POST"])
def tools_input():
    _local_only()
    from core import jobs
    return jsonify(ok=jobs.send((request.json or {}).get("text", "")))


@app.route("/tools/stop", methods=["POST"])
def tools_stop():
    _local_only()
    from core import jobs
    return jsonify(ok=jobs.stop())


@app.route("/tools/save/<key>", methods=["POST"])
def tools_save(key):
    _local_only()
    from core import jobs
    if key not in jobs.EDITABLE:
        abort(404)
    jobs.save_text(key, request.form.get("text", ""))
    return redirect(url_for("tools") + "#lists")


# ---------------------------------------------------------------- Daily Position report (office PC only)
def _daily_context():
    from datetime import timedelta
    D, ex = data.load()
    if not D:
        abort(503, "No ERP data yet - press 'Update from ERP'.")
    report_date = ex.date()
    from core import daily_inputs as DI
    return D, ex, report_date, DI.position_date(report_date)


@app.route("/daily", methods=["GET", "POST"])
def daily():
    _local_only()
    from core import condemnation, daily_inputs as DI
    inp = DI.load()
    if request.method == "POST":
        inp = DI.save(DI.from_form(request.form, inp))
        if request.form.get("action") == "report":
            return redirect(url_for("daily_report"))
        return redirect(url_for("daily", saved=1))
    D, ex, report_date, as_on = _daily_context()
    wd = DI.working_days(as_on, inp)
    cond, cond_err = condemnation.load(live=True)
    hold = {R.coach_key(h): h for h in P.holding(D, as_on)}
    status_col = lambda r: next((v for k, v in r.items() if "status" in k.lower()), "")
    cond_rows = []
    for r in cond.get("rows", []):
        k = R.coach_key({"coachNo": r["coach"]})
        h = hold.get(k)
        cond_rows.append(dict(coach=r["coach"], type=r.get("Type", ""), status=status_col(r), inside=bool(h),
                              hrs=int(R.hours(h, "preSurveyHrs") or 0) or "" if h else ""))
    listed = {R.coach_key({"coachNo": r["coach"]}) for r in cond.get("rows", [])}
    heavy = []
    for k, h in hold.items():
        hrs = R.hours(h, "preSurveyHrs")
        if h["_family"] == "ICF" and hrs and hrs >= 1000:
            rd = R.pdate(h.get("receivedDate"))
            heavy.append(dict(no=h.get("coachNo"), type=R.coach_type(h), div=h.get("divisionId") or "", yb=h.get("_yearBuilt") or "",
                              hrs=int(hrs), days=(as_on - rd).days if rd else "", listed=k in listed))
    heavy.sort(key=lambda c: -c["hrs"])
    latest = R.latest_per_coach(D)
    plan_status = {}
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
    return render_template("daily.html", inp=inp, wd=wd, fy=R.fy_of(as_on), as_on=as_on, report_date=report_date,
                           saved=request.args.get("saved"), target_rows=DI.TARGET_ROWS, typed_fields=DI.TYPED_FIELDS,
                           cond=cond, cond_err=cond_err, cond_rows=cond_rows, heavy=heavy, plan_status=plan_status)


@app.route("/daily/report")
def daily_report():
    _local_only()
    from analysis import daily_report as DR
    from core import condemnation, daily_inputs as DI
    D, ex, report_date, as_on = _daily_context()
    inp = DI.load()
    cond, _ = condemnation.load(live=True)
    html = DR.build(D, ex, inp, DI.working_days(as_on, inp), [r["coach"] for r in cond.get("rows", [])],
                    as_on=as_on, report_date=report_date)
    return html


@app.route("/health")
def health():
    D, ex = data.load()
    return jsonify(mode=config.APP_MODE, demands=len(D), as_on=str(ex))


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False)
