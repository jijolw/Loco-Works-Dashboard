# =====================================================
# app.py
# LW/PER Workshop Intelligence System
# Flask application — serves API + frontend
# =====================================================

from flask import Flask, jsonify, request, render_template, send_from_directory
import os, traceback, threading
from datetime import datetime

from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)


@app.route("/")
def landing():
    """Serve the central welcome landing portal."""
    return render_template("landing.html")


@app.route("/cr")
def index():
    """Serve the Carriage Repair (CR) Shop SPA dashboard."""
    return render_template("index.html")



@app.route("/coach/reports/aerialview/print.html")
@app.route("/reports/aerialview/print.html")
def print_aerial():
    return render_template("print_aerial.html")


# =====================================================
# API — Aerial View
# =====================================================

@app.route("/api/aerial")
def api_aerial():
    """Return aerial view data: coaches on pits + topology."""
    try:
        from services.aerial_service import get_aerial_data
        data = get_aerial_data()
        
        # Track active coach movements dynamically
        try:
            from services.sync_service import track_coach_movements
            track_coach_movements()
        except Exception as se:
            print("Background movement tracking error:", se)
            
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =====================================================
# API — Live Position
# =====================================================

@app.route("/api/live")
def api_live():
    """Return live position data for all coaches in workshop."""
    try:
        from services.live_service import get_live_data
        data = get_live_data()
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/coaches/progress")
def api_coaches_progress():
    """Return progress tracker data for coaches under repair."""
    try:
        from services.live_service import get_coaches_progress
        data = get_coaches_progress()
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =====================================================
# API — Coach Search
# =====================================================

@app.route("/api/coach/<coachno>")
def api_coach_search(coachno):
    """Search for a specific coach by number."""
    try:
        from services.erp_service import fetch_master, fetch_single, fetch_year_built, _parse_date
        from services.decoders import (
            decode_repair, decode_division, decode_workshop,
            decode_family, decode_corrosion, decode_all,
        )
        from services.live_service import _resolve_division
        from services.aerial_service import _compute_aerial_status
        from datetime import datetime

        coachno = str(coachno).strip()
        master = fetch_master()

        # Find matching coaches in master list
        matches = []
        for row in master:
            rn = str(row.get("coachno", "")).strip()
            if coachno.lower() in rn.lower():
                matches.append(row)

        if not matches:
            return jsonify({"matches": [], "count": 0})

        # Enrich each match with singledata
        enriched = []
        for row in matches[:20]:  # limit to 20 matches
            demandid = str(row.get("demandid", "")).strip()
            if not demandid or demandid == "nan":
                continue

            d = fetch_single(demandid)
            decoded = decode_all(
                d,
                summary_coachno=str(row.get("coachno", "")),
                summary_desc=str(row.get("coach_desc", "")),
            )

            # Add fields from master
            decoded["demandid"] = demandid
            row_coachno = str(row.get("coachno", "")).strip()
            pitnum = str(row.get("pitnum", "")).strip()
            decoded["pitnum"] = pitnum
            decoded["noofdays"] = row.get("noofdays", "")

            # Calculate IN_DAYS
            recd_str = row.get("recd_date", "") or row.get("recddate", "") or d.get("recd_date", "") or d.get("recddate", "")
            recd_dt = _parse_date(recd_str)
            decoded["IN_DAYS"] = (datetime.now() - recd_dt).days if recd_dt else None

            # Add year_built from coachmaster
            cm = fetch_year_built(coachno)
            decoded["year_built"] = cm.get("year_built", "")
            decoded["make"] = cm.get("make", "")

            # Enrich with Google Sheets corrosion data if vacant in ERP
            from services.db_service import get_google_corrosion
            google_corr = get_google_corrosion(row_coachno)
            if google_corr:
                g_corr_in = google_corr.get("corr_in_date") or ""
                g_corr_status = google_corr.get("corrosion_status") or ""
                
                if (not decoded.get("corr_place") or str(decoded.get("corr_place")).strip() in ("", "None", "null")) and g_corr_in:
                    decoded["corr_place"] = "GSheet: " + g_corr_in
                if (not decoded.get("corr_comp") or str(decoded.get("corr_comp")).strip() in ("", "None", "null")) and g_corr_status:
                    if "completed" in g_corr_status.lower() or "/" in g_corr_status or "-" in g_corr_status:
                        decoded["corr_comp"] = g_corr_status if ("/" in g_corr_status or "-" in g_corr_status) else "Completed"
                
                decoded["bio_tank_status"] = google_corr.get("bio_tank_status", "")
                decoded["lowering_status"] = google_corr.get("lowering_status", "")
                decoded["furnishing_status"] = google_corr.get("furnishing_status", "")
                decoded["despatch_status"] = google_corr.get("despatch_status", "")
                decoded["google_pdc"] = google_corr.get("pdc", "")
                decoded["google_remarks"] = google_corr.get("remarks", "")
                
                if not decoded.get("corrosion_label") or decoded["corrosion_label"] == "":
                    decoded["corrosion_label"] = g_corr_status

            # Enrich with manual updates from Supabase
            try:
                from services.db_service import get_manual_coach_update
                manual_upd = get_manual_coach_update(row_coachno)
                if manual_upd:
                    decoded["vg_status"] = manual_upd.get("vg_status") or ""
                    decoded["vg_date"] = manual_upd.get("vg_date") or ""
                    decoded["physical_status"] = manual_upd.get("physical_status") or ""
                    decoded["physical_date"] = manual_upd.get("physical_date") or ""
                else:
                    decoded["vg_status"] = ""
                    decoded["vg_date"] = ""
                    decoded["physical_status"] = ""
                    decoded["physical_date"] = ""
            except Exception as se:
                print("Failed to load manual updates from Supabase:", se)
                decoded["vg_status"] = ""
                decoded["vg_date"] = ""
                decoded["physical_status"] = ""
                decoded["physical_date"] = ""

            # Resolve division, repair_type, and status to match frontend keys
            decoded["division"] = _resolve_division(row, d)
            decoded["repair_type"] = decoded.get("repair_label", "")
            decoded["AERIAL_STATUS"] = _compute_aerial_status(decoded)

            enriched.append(decoded)

        return jsonify({"matches": enriched, "count": len(enriched)})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =====================================================
# API — Outturn (Phase 2 — placeholder)
# =====================================================

@app.route("/api/outturn")
def api_outturn():
    """Return outturn data for a specific date range."""
    try:
        from services.outturn_service import get_outturn_data
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        data = get_outturn_data(start_date, end_date)
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =====================================================
# API — Corrosion Analysis
# =====================================================

@app.route("/api/corrosion/analysis")
def api_corrosion_analysis():
    """Return corrosion analysis data for selected financial years and coach families."""
    try:
        from services.corrosion_service import get_corrosion_analysis
        
        fys_param = request.args.get("fys", "")
        family = request.args.get("family", "ALL")
        
        fy_list = [f.strip() for f in fys_param.split(",") if f.strip()] if fys_param else None
        
        data = get_corrosion_analysis(fy_list=fy_list, family_filter=family)
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =====================================================
# API — Analytics (Phase 2 — placeholder)
# =====================================================

@app.route("/api/analytics")
def api_analytics():
    """Analytics data — Phase 2."""
    return jsonify({"status": "coming_soon", "module": "Analytics"})


# =====================================================
# API — Corrosion Analysis (Phase 3 — placeholder)
# =====================================================

@app.route("/api/corrosion")
def api_corrosion():
    """Corrosion analysis — Phase 3."""
    return jsonify({"status": "coming_soon", "module": "Corrosion Analysis"})


# =====================================================
# API — POH Analysis & Targets
# =====================================================

@app.route("/api/poh/analysis")
def api_poh_analysis():
    """Return POH performance and schedule misclassifications."""
    try:
        from services.poh_service import analyze_poh_performance
        fy = request.args.get("fy")
        data = analyze_poh_performance(fy)
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/poh/targets")
def api_poh_targets():
    """Return target vs actual outturn comparisons for a given FY."""
    try:
        from services.poh_service import get_targets_vs_achievement
        fy = request.args.get("fy", "2026-27")
        data = get_targets_vs_achievement(fy)
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/coach/<coachno>/movements")
def api_coach_movements(coachno):
    """Return location history timeline for a specific coach."""
    try:
        from services.sync_service import get_coach_movements_history
        data = get_coach_movements_history(coachno)
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/coach/manual_update", methods=["POST"])
def api_coach_manual_update():
    """Upsert manual VG and physical despatch details to Supabase."""
    try:
        from services.db_service import upsert_manual_coach_update
        data = request.json or {}
        coachno = data.get("coachno")
        if not coachno:
            return jsonify({"error": "coachno is required"}), 400
            
        vg_status = data.get("vg_status", "")
        vg_date = data.get("vg_date", "")
        physical_status = data.get("physical_status", "")
        physical_date = data.get("physical_date", "")
        
        upsert_manual_coach_update(coachno, vg_status, vg_date, physical_status, physical_date)
        
        # Clear all memory caches to reflect updates immediately in all modules
        try:
            from services.erp_service import cache_clear
            from services.corrosion_service import corrosion_cache_clear
            from services.live_service import live_cache_clear
            from services.aerial_service import aerial_cache_clear
            cache_clear()
            corrosion_cache_clear()
            live_cache_clear()
            aerial_cache_clear()
        except Exception as ce:
            print("Failed to clear caches:", ce)
            
        return jsonify({"success": True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/audit/data")
def api_audit_data():
    """Return corrosion and despatch audit rankings, missing hours, and FND list."""
    try:
        fy = request.args.get("fy", "ALL")
        family = request.args.get("family", "ALL")
        coach_type = request.args.get("type", "ALL")
        
        from services.audit_service import get_audit_data
        data = get_audit_data(fy_filter=fy, family_filter=family, type_filter=coach_type)
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/audit/batch-despatch", methods=["POST"])
def api_audit_batch_despatch():
    """Batch mark coaches as VG Cleared & Physically Despatched in Supabase."""
    try:
        from services.db_service import upsert_manual_coach_updates_bulk
        from services.erp_service import cache_clear, fetch_master, _parse_date
        from datetime import datetime
        
        data = request.json or {}
        coachnos = data.get("coachnos", [])
        desp_date = data.get("date", "").strip()
        
        if not coachnos:
            return jsonify({"error": "No coaches selected"}), 400

        # Use current date if none provided
        if not desp_date:
            desp_date = datetime.now().strftime("%d/%m/%Y")
            
        payload = []
        for coachno in coachnos:
            payload.append({
                "coachno": str(coachno).strip(),
                "vg_status": "Completed",
                "vg_date": desp_date,
                "physical_status": "Despatched",
                "physical_date": desp_date
            })
            
        upsert_manual_coach_updates_bulk(payload)
        
        # Clear cache to reflect updates immediately
        try:
            from services.erp_service import cache_clear
            from services.corrosion_service import corrosion_cache_clear
            from services.live_service import live_cache_clear
            from services.aerial_service import aerial_cache_clear
            cache_clear()
            corrosion_cache_clear()
            live_cache_clear()
            aerial_cache_clear()
        except Exception as ce:
            print("Failed to clear caches:", ce)
        
        return jsonify({"success": True, "updated_count": len(coachnos)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.route("/api/targets/sync")
def api_targets_sync():
    """Sync targets from Google Sheets."""
    try:
        from services.sync_service import sync_targets
        res = sync_targets()
        return jsonify(res)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =====================================================
# API — AC Loco (Phase 3 — placeholder)
# =====================================================

@app.route("/api/acloco/position")
def api_acloco_position():
    """Return AC Loco live position data."""
    try:
        from services.aerial_service import _fetch_ac_locos
        locos = _fetch_ac_locos()
        return jsonify({"coaches": locos, "count": len(locos)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/acloco/outturn")
def api_acloco_outturn():
    """AC Loco outturn — Phase 3."""
    return jsonify({"status": "coming_soon", "module": "AC Loco Outturn"})


@app.route("/api/acloco/program")
def api_acloco_program():
    """AC Loco program — Phase 3."""
    return jsonify({"status": "coming_soon", "module": "AC Loco Program"})


# =====================================================
# API — Health Check
# =====================================================

@app.route("/api/health")
def api_health():
    """Health check — verify ERP connectivity."""
    result = {"flask": "ok"}
    try:
        from services.erp_service import get_session
        sess = get_session()
        result["coach_erp"] = "ok" if sess else "failed"
    except Exception as e:
        result["coach_erp"] = f"error: {str(e)}"

    try:
        from services.erp_service import get_ac_session
        sess = get_ac_session()
        result["acloco_erp"] = "ok" if sess else "failed"
    except Exception as e:
        result["acloco_erp"] = f"error: {str(e)}"

    return jsonify(result)


# =====================================================
# API — Sync Control (Trigger Sync)
# =====================================================

_sync_lock = threading.Lock()
_sync_status = {
    "status": "idle",
    "mode": None,
    "started_at": None,
    "finished_at": None,
    "error": None,
    "last_success_at": None
}

@app.route("/api/sync/status")
def api_sync_status():
    """Return the status of the background sync process."""
    return jsonify(_sync_status)


@app.route("/api/sync/run", methods=["POST"])
def api_sync_run():
    """Trigger a sync cycle in the background."""
    global _sync_status
    data = request.json or {}
    mode = data.get("mode", "incremental").strip().lower()
    full_sync = (mode == "full")
    
    if _sync_lock.locked():
        return jsonify({"error": "Sync is already running."}), 409
        
    def run_sync_in_thread():
        global _sync_status
        with _sync_lock:
            _sync_status["status"] = "running"
            _sync_status["mode"] = mode
            _sync_status["started_at"] = datetime.now().isoformat()
            _sync_status["finished_at"] = None
            _sync_status["error"] = None
            try:
                import sys
                local_dir = os.path.dirname(os.path.abspath(__file__))
                if local_dir not in sys.path:
                    sys.path.append(local_dir)
                
                from sync_client import sync_cycle
                sync_cycle(full_sync=full_sync)
                _sync_status["status"] = "success"
                _sync_status["finished_at"] = datetime.now().isoformat()
                _sync_status["last_success_at"] = datetime.now().isoformat()
            except Exception as e:
                traceback.print_exc()
                _sync_status["status"] = "failed"
                _sync_status["finished_at"] = datetime.now().isoformat()
                _sync_status["error"] = str(e)
                
    threading.Thread(target=run_sync_in_thread, daemon=True).start()
    return jsonify({"success": True, "message": f"Sync started in mode: {mode}"})


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    print("=" * 50)
    print("  LW/PER Workshop Intelligence System")
    print(f"  Starting on http://{FLASK_HOST}:{FLASK_PORT}")
    print("=" * 50)
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
    )
