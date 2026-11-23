"""
core/flash.py - Comprehensive JSON summary endpoint for Chrome Extension and Desktop HUD.
Operates 100% in-memory from erp_demands_latest.json snapshot.
NEVER contacts the live ERP server.
"""
from datetime import date, datetime
import json
import os

from core import data, rules as R, condemnation
from analysis import position as P

KM_FILE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                                       "10_Claude_Reports", "output", "km_summary_latest.txt"))
TARGET_KEYS = ["ICF", "NMGP", "NMGC", "ARTC", "ARTP", "LHBN", "LHBA", "EMU", "DEMU", "SPART", "TW4", "TW8", "OR", "EMUONLY"]


def _num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _targets(as_on):
    """(monthly HQ target total, FY proportionate target till as_on) - SAME source and sum as the Daily Position page 2
    (staff Targets tab via data/manual_sheet.json, else the typed form). None when not set (Claude 09-11-2026)."""
    try:
        from core import daily_inputs as DI
        inp = DI.load()
        try:
            from core import manual_sheet
            # saved copy, refreshed from the staff sheet when missing or older than 1 hour (the app PC had no
            # saved copy -> old typed form targets were used: 59 instead of 64, 09-11-2026)
            try:
                age = datetime.now().timestamp() - os.path.getmtime(manual_sheet.FILE)
            except OSError:
                age = None
            m, _ = manual_sheet.load(live=age is None or age > 3600)
            manual_sheet.apply(inp, as_on, m)
        except Exception:
            pass
        T = inp.get("targets", {})
        hq = sum(_num((T.get(k) or {}).get("hq")) for k in TARGET_KEYS)
        wd = DI.working_days(as_on, inp)
        py = wd["year_completed"] / wd["year_total"] if wd.get("year_total") else 0
        prop = sum(_num((T.get(k) or {}).get("basis")) for k in TARGET_KEYS if k != "EMUONLY") * py
        return (round(hq) or None), (round(prop) or None)
    except Exception:
        return None, None


def _pill(counts, n=5):
    """{'GS': 3, ...} -> 'GS: 3 | CN: 1' (largest first)."""
    return " | ".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:n] if v)


def _km_summary():
    """Parse km_summary_latest.txt (written by Daily_Run / Update_All from the HQ KM sheet + ERP, HQ rule)."""
    rows, checks, title = [], [], ""
    try:
        with open(KM_FILE, encoding="utf-8") as f:
            lines = [l.rstrip() for l in f if l.strip()]
    except Exception:
        return rows, checks, title, []
    for l in lines:
        if l.startswith("KM SUMMARY"):
            title = l
        elif l.startswith("CHECK:"):
            checks.append(l[6:].strip())
        else:
            p = l.split()
            if len(p) == 6 and p[1].isdigit():
                rows.append({"type": p[0], "total": int(p[1]), "yb_ge_12": int(p[2]), "km_done": int(p[3]),
                             "km_under": int(p[4]), "regular": int(p[5])})
    return rows, checks, title, lines

def get_flash_data():
    demands, exported_at = data.load()
    from core import physical as _ph                 # flash screens = ERP only, same as the Daily Position (12-11-2026)
    demands = _ph.erp_only(demands)
    as_on = exported_at.date() if exported_at else date.today()

    # Use standard month_position from analysis.position
    pos = P.month_position(demands, as_on)
    tot = pos["total"]
    
    # 1. Month POH Outturns (dispatchDate in month)
    # Correct Workshop Logic:
    # Outturned this month = tot["outturn"] (6)
    # Physically Despatched of this month's outturn = tot["desp"] (0)
    # Balance (FND of this month) = tot["fnd"] (6)
    month_outturn_list = []
    for d in pos["fnd_list"]:
        grp = d.get("_group", "OTHERS")
        fam = d.get("_family", "Others")
        cno = str(d.get("coachNo") or "").strip()
        month_outturn_list.append({
            "coachNo": cno,
            "type": R.coach_type(d),
            "group": grp,
            "family": fam,
            "div": d.get("divisionId") or d.get("inDivisionId") or "",
            "rly": d.get("_railway") or "SR",
            "despDate": R.fmt(R.pdate(d.get("dispatchDate"))),
            "actualDespDate": R.fmt(R.pdate(d.get("actualDispatchDate"))),
            "status": "FND (In Shop/Yard)",
            "pit": d.get("pitNum") or ""
        })

    # Group-wise breakdown of this month's outturn
    month_by_group = []
    for r in pos["rows"]:
        if r["outturn"] > 0 or r["desp"] > 0 or r["fnd"] > 0:
            month_by_group.append({
                "group": r["group"],
                "outturn": r["outturn"],
                "desp": r["desp"],
                "fnd": r["fnd"]
            })

    # 2. Previous Month FND Despatched (October FNDs physically despatched in Nov)
    prev_fnd_desp_list = []
    prev_fnd_by_group = {}
    for d in pos.get("prev_fnd_desp", []):
        grp = d.get("_group", "OTHERS")
        fam = d.get("_family", "Others")
        cno = str(d.get("coachNo") or "").strip()
        prev_fnd_desp_list.append({
            "coachNo": cno,
            "type": R.coach_type(d),
            "group": grp,
            "family": fam,
            "div": d.get("divisionId") or d.get("inDivisionId") or "",
            "despDate": R.fmt(R.pdate(d.get("dispatchDate"))),
            "actualDespDate": R.fmt(R.pdate(d.get("actualDispatchDate"))),
            "pit": d.get("pitNum") or "",
            "status": "Oct FND Despatched"
        })
        prev_fnd_by_group[grp] = prev_fnd_by_group.get(grp, 0) + 1

    # 3. Cumulative FY outturn
    m0 = R.month_start(as_on)
    m1 = date(m0.year + (m0.month == 12), m0.month % 12 + 1, 1)
    end_m = min(as_on, date.fromordinal(m1.toordinal() - 1))
    fy_s = date(as_on.year if as_on.month >= 4 else as_on.year - 1, 4, 1)
    cum_ots = P.outturns(demands, fy_s, end_m)
    cum_by_family = {}
    cum_by_group = {}
    for d in cum_ots:
        fam = d.get("_family", "Others")
        grp = d.get("_group", "OTHERS")
        cum_by_family[fam] = cum_by_family.get(fam, 0) + 1
        cum_by_group[grp] = cum_by_group.get(grp, 0) + 1

    # 4. Holding
    h_list = P.holding(demands, as_on)

    # Condemnation map
    cond_data, _ = condemnation.load(live=False)
    condem_map = {}
    for r in cond_data.get("rows", []):
        c = str(r.get("coach") or r.get("Coach No") or "").strip().lstrip("0")
        if c:
            condem_map[c] = r

    # Process holding coaches & >30 days
    holding_details = []
    icf_holding = []
    icf_above_30_condem = []
    icf_above_30_regular = []
    icf_below_30_condem = []

    for d in h_list:
        cno = str(d.get("coachNo") or "").strip()
        c_key = cno.lstrip("0")
        fam = d.get("_family", "Others")
        grp = d.get("_group", "OTHERS")
        days = d.get("_days") or 0
        recd_str = R.fmt(R.pdate(d.get("receivedDate")))
        pit = d.get("pitNum") or "Shop Yard"
        loc = d.get("_loc") or "Yard"
        div = d.get("divisionId") or d.get("inDivisionId") or ""
        rly = d.get("_railway") or "SR"
        pre_hrs = d.get("preSurveyHrs") or ""

        c_info = condem_map.get(c_key, {})
        c_status = c_info.get("Current Survey Status", "")
        is_prop_condem = "proposed" in c_status.lower()
        condem_reason = c_info.get("Remarks / Reason", "")

        coach_obj = {
            "coachNo": cno,
            "type": R.coach_type(d),
            "group": grp,
            "family": fam,
            "div": div,
            "rly": rly,
            "recdDate": recd_str,
            "days": days,
            "pit": pit,
            "location": loc,
            "preHrs": pre_hrs,
            "isProposedCondemnation": is_prop_condem,
            "condemStatus": c_status,
            "condemReason": condem_reason
        }
        holding_details.append(coach_obj)

        if fam == "ICF":
            icf_holding.append(coach_obj)
            if days > 30:
                if is_prop_condem:
                    icf_above_30_condem.append(coach_obj)
                else:
                    icf_above_30_regular.append(coach_obj)
            else:
                if is_prop_condem:
                    icf_below_30_condem.append(coach_obj)

    icf_above_30_condem.sort(key=lambda x: -x["days"])
    icf_above_30_regular.sort(key=lambda x: -x["days"])
    icf_below_30_condem.sort(key=lambda x: -x["days"])

    # KM - status from the HQ sheet (km_status.json): HQ decides physical presence of KM coaches (JIJO rule)
    KM_STATUS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "km_status.json")
    km_dict, km_updated = {}, ""
    try:
        with open(KM_STATUS_FILE, "r", encoding="utf-8") as f:
            kj = json.load(f)
        km_dict, km_updated = kj.get("coaches", {}), kj.get("updated", "")
    except Exception:
        pass
    km_out = [c for c, st in km_dict.items() if st == "OUT"]
    km_done = [c for c, st in km_dict.items() if "DONE" in st]
    km_under = [c for c, st in km_dict.items() if "UNDER" in st]
    km_rows, km_checks, km_title, km_lines = _km_summary()

    # targets - same as the Daily Position page 2
    hq_target, prop_target = _targets(as_on)

    # warnings worth showing on every screen
    warnings = []
    if exported_at and exported_at.date() < date.today():
        warnings.append(f"Data is from {exported_at:%d-%m-%Y %H:%M} - run Daily sync")
    others = sorted({f"{d.get('coachNo')} {R.coach_type(d)}" for d in h_list + cum_ots if d.get("_group") == "OTHERS"})
    if others:
        warnings.append("New coach type not in the list (not counted in a row): " + ", ".join(others))
    if hq_target is None:
        warnings.append("Monthly HQ target not entered in the staff Targets tab")

    fam_short = {"ICF": "ICF", "LHB": "LHB", "TC family": "TC", "DEMU Shop": "DEMU", "Special": "Special"}
    # ICF holding split like the Daily Position: balance + in Condemnation_Pipeline (JIJO 09-11-2026)
    icf_cond = sum(1 for c in icf_holding if c["coachNo"].lstrip("0") in condem_map)
    hold_fam = {
        "ICF": len(icf_holding),
        "LHB": sum(1 for d in h_list if d.get("_family") == "LHB"),
        "TC": sum(1 for d in h_list if d.get("_family") == "TC family"),
        "DEMU": sum(1 for d in h_list if d.get("_family") == "DEMU Shop"),
        "Special": sum(1 for d in h_list if d.get("_family") == "Special"),
    }
    by_grp_month = {r["group"]: r["outturn"] for r in month_by_group}

    return {
        "status": "success",
        "as_on": str(as_on),
        "as_on_fmt": as_on.strftime("%d-%m-%Y"),
        "exported_at": str(exported_at) if exported_at else "",
        "month_label": as_on.strftime("%B %Y"),
        "month_short": as_on.strftime("%b").upper(),
        "prev_month_short": date.fromordinal(m0.toordinal() - 1).strftime("%b").upper(),
        "warnings": warnings,
        "month_outturn": {
            "total": tot["outturn"],
            "desp": tot["desp"],
            "fnd": tot["fnd"],
            "target": hq_target,            # staff Targets tab (None = not entered) - was typed 64
            "by_group": month_by_group,
            "pill": _pill(by_grp_month),
            "coaches": month_outturn_list
        },
        "prev_month_fnd_despatched": {
            "total": len(prev_fnd_desp_list),
            "by_group": prev_fnd_by_group,
            "pill": _pill(prev_fnd_by_group),
            "coaches": prev_fnd_desp_list
        },
        "cumulative_fy": {
            "total": len(cum_ots),
            "fy_label": R.fy_of(as_on),
            "prop_target": prop_target,
            "by_family": cum_by_family,
            "by_group": cum_by_group,
            "pill": _pill({fam_short.get(k, k): v for k, v in cum_by_family.items()})
        },
        "holding": {
            "total": len(h_list),
            "yard": tot["yard"],
            "work_area": tot["work"],
            "by_family": hold_fam,
            "pill": _pill(hold_fam).replace(f"ICF: {len(icf_holding)}",
                                            f"ICF: {len(icf_holding) - icf_cond}+{icf_cond} cond" if icf_cond else f"ICF: {len(icf_holding)}"),
            "icf_cond": icf_cond,
            "icf_balance": len(icf_holding) - icf_cond,
            "icf_total": len(icf_holding),
            "icf_above_30_count": len(icf_above_30_condem) + len(icf_above_30_regular),
            "icf_above_30_condem_count": len(icf_above_30_condem),
            "icf_above_30_regular_count": len(icf_above_30_regular),
            "icf_above_30_condem_coaches": icf_above_30_condem,
            "icf_above_30_regular_coaches": icf_above_30_regular,
            "icf_below_30_condem_coaches": icf_below_30_condem,
            "all_coaches": holding_details
        },
        "kumbh_mela": {
            "hq_updated": km_updated,
            "summary_title": km_title,
            "summary_lines": km_lines[:8],
            "total_nominated": len(km_dict),
            "despatched": len(km_out),
            "done": len(km_done),
            "under_poh": len(km_under),
            "inshop_screw_holding": sum(r["total"] for r in km_rows),
            "regular": sum(r["regular"] for r in km_rows),
            "despatched_coaches": km_out,
            "done_coaches": km_done,
            "under_poh_coaches": km_under,
            "details": km_rows,
            "audit_flags": km_checks
        }
    }
