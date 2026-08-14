# =====================================================
# services/sync_service.py
# Sync targets from Google Sheet and track coach movements via Supabase REST API
# =====================================================

import os
import logging
from datetime import datetime

from services.erp_service import fetch_clean, _parse_date
from services.decoders import decode_family
from services.db_service import (
    delete_all_outturn_targets,
    insert_outturn_targets_bulk,
    delete_all_google_corrosion,
    upsert_google_corrosion_bulk,
    get_last_coach_movement,
    insert_coach_movement,
    get_coach_movements_history
)

logger = logging.getLogger(__name__)

from config import GOOGLE_SHEET_KEY as SHEET_KEY, GOOGLE_CREDENTIALS_PATH as CREDENTIALS_PATH


def sync_corrosion_from_sheet(old_gsheet):
    """
    Sync corrosion and stage data disabled as requested.
    """
    logger.info("Sync corrosion from progress sheet is disabled.")
    return
    
    import json
    import gspread
    from google.oauth2.service_account import Credentials
    from services.live_service import get_live_data
    from services.erp_service import fetch_master, fetch_single, _parse_date
    from services.decoders import decode_division, decode_repair, decode_family
    
    # 1. Connect to the new tracker spreadsheet
    TRACKER_SHEET_KEY = "1mtde30SYHvSMEmk9OVUWdVX-wDBZEMXwJki0nTXyAU8"
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scope)
        client = gspread.authorize(creds)
        tracker_sheet = client.open_by_key(TRACKER_SHEET_KEY)
    except Exception as e:
        logger.error(f"Failed to open new tracker spreadsheet {TRACKER_SHEET_KEY}: {e}")
        return
        
    try:
        ws_active = tracker_sheet.worksheet("Active Coaches")
        ws_desp = tracker_sheet.worksheet("Corrosion completed coaches")
    except Exception as e:
        logger.error(f"Failed to load worksheets: {e}")
        return

    # 2. Read active floor coaches from ERP to auto-populate
    try:
        live_data = get_live_data()
        erp_active = live_data.get("coaches", [])
        logger.info(f"Loaded {len(erp_active)} live active coaches from local ERP.")
    except Exception as e:
        logger.error(f"Failed to fetch live active coaches from ERP: {e}")
        erp_active = []
        
    try:
        erp_master = fetch_master()
        erp_master_map = {str(r.get("coachno")).strip(): r for r in erp_master if r.get("coachno")}
    except Exception as e:
        logger.error(f"Failed to fetch ERP master records: {e}")
        erp_master_map = {}

    # 3. Read current rows from Google Sheet
    try:
        rows_active = ws_active.get_all_values()
        rows_desp = ws_desp.get_all_values()
    except Exception as e:
        logger.error(f"Failed to read cells from worksheets: {e}")
        return

    headers_new = [
        "Sl No", "Coach No", "Coach Code", "Division", "Type of Repair", "Type",
        "Corrosion", "Bio Toilet", "Carpentry", "Trimming", "Air Brake",
        "Under Frame", "Train Lighting", "Water Service", "Lowering",
        "Painting", "Final Cleaning", "Despatch"
    ]

    # Parse active coaches currently in the sheet
    active_coach_rows = []
    active_coachnos = set()
    if len(rows_active) > 0:
        active_coach_rows = rows_active[1:]
        for r in active_coach_rows:
            if len(r) > 1 and r[1].strip():
                active_coachnos.add(r[1].strip().lower())
                
    # Parse despatched coaches in the sheet
    desp_coachnos = set()
    if len(rows_desp) > 0:
        for r in rows_desp[1:]:
            if len(r) > 1 and r[1].strip():
                desp_coachnos.add(r[1].strip().lower())

    # 4. Auto-populate missing active coaches
    sheet_modified = False
    new_rows_added = 0
    sl_idx = len(active_coach_rows) + 1
    
    for c in erp_active:
        cno = str(c.get("coachno", "")).strip()
        if not cno:
            continue
            
        cno_lower = cno.lower()
        # Only add if not already in active or despatched sheet
        if cno_lower not in active_coachnos and cno_lower not in desp_coachnos:
            # Check if recently despatched in ERP
            master_rec = erp_master_map.get(cno) or {}
            erp_status = str(master_rec.get("status") or "").strip().upper()
            act_desp = master_rec.get("actualdespdate")
            
            if erp_status in ("DESPATCHED",) or (act_desp and str(act_desp).strip().lower() not in ("none", "null", "nan", "")):
                continue # Skip already despatched
                
            # Get metadata
            coach_code = c.get("coach_desc") or c.get("coachdesc") or master_rec.get("coach_desc") or ""
            division = decode_division(c.get("division") or master_rec.get("dvnid"))
            repair_type = decode_repair(c.get("repair_type") or master_rec.get("repair_type") or master_rec.get("repairid"))
            type_family = decode_family(coach_code)
            
            new_row = [str(sl_idx), cno, coach_code, division, repair_type, type_family] + [""] * 12
            active_coach_rows.append(new_row)
            active_coachnos.add(cno_lower)
            sl_idx += 1
            new_rows_added += 1
            sheet_modified = True

    if new_rows_added > 0:
        logger.info(f"Auto-populated {new_rows_added} new active coaches from ERP.")

    # 5. Archive despatched coaches & auto-fill dates from ERP
    despatched_to_move = []
    remaining_active_rows = []
    
    for row in active_coach_rows:
        # Pad row to 18 columns if somehow shorter
        if len(row) < 18:
            row = row + [""] * (18 - len(row))
            
        cno = str(row[1]).strip()
        if cno:
            master_rec = erp_master_map.get(cno)
            if master_rec:
                demandid = master_rec.get("demandid")
                if demandid:
                    try:
                        # Fetch single detail record which contains actualdespdate, desp_date, and corr_comp
                        detail = fetch_single(demandid)
                    except Exception as e:
                        logger.error(f"Failed to fetch ERP detail for coach {cno}: {e}")
                        detail = {}
                        
                    # A. Auto-fill corrosion completion date if empty in sheet
                    if not str(row[6]).strip():
                        erp_corr_comp = detail.get("corr_comp") or detail.get("corrosion") or master_rec.get("corr_comp") or master_rec.get("corrosion")
                        if erp_corr_comp and str(erp_corr_comp).strip().lower() not in ("none", "null", "nan", "", "0"):
                            dt = _parse_date(erp_corr_comp)
                            if dt:
                                row[6] = dt.strftime("%d/%m/%Y")
                                sheet_modified = True
                                
                    # B. Auto-fill despatch date if empty in sheet
                    if not str(row[17]).strip():
                        erp_desp = detail.get("actualdespdate")
                        if erp_desp and str(erp_desp).strip().lower() not in ("none", "null", "nan", "", "0"):
                            dt = _parse_date(erp_desp)
                            if dt:
                                row[17] = dt.strftime("%d/%m/%Y")
                                sheet_modified = True
            
        corr_val = str(row[6]).strip()
        # If Corrosion column is not empty, move to Corrosion completed coaches
        if corr_val:
            despatched_to_move.append(row)
            sheet_modified = True
        else:
            remaining_active_rows.append(row)

    if despatched_to_move:
        logger.info(f"Moving {len(despatched_to_move)} corrosion-completed coaches to Corrosion completed coaches worksheet.")
        try:
            ws_desp.append_rows(despatched_to_move)
        except Exception as e:
            logger.error(f"Failed to append to Corrosion completed coaches worksheet: {e}")

    # 6. Save back active sheet if changed
    if sheet_modified:
        try:
            ws_active.clear()
            ws_active.append_row(headers_new)
            if remaining_active_rows:
                ws_active.append_rows(remaining_active_rows)
            logger.info("Updated Active Coaches worksheet.")
        except Exception as e:
            logger.error(f"Failed to update Active Coaches worksheet: {e}")

    # 7. Prepare database payload from remaining active and recent despatched coaches
    db_payload = []
    
    def process_rows_for_db(rows_list, is_despatched_list=False):
        for r in rows_list:
            if len(r) < 18:
                r = r + [""] * (18 - len(r))
                
            cno = str(r[1]).strip()
            if not cno:
                continue
                
            corr_val = str(r[6]).strip()
            bio_val = str(r[7]).strip()
            low_val = str(r[14]).strip()
            desp_val = str(r[17]).strip()
            
            # Map statuses
            corr_status = "Completed" if corr_val else "Pending"
            low_status = "Completed" if low_val else "Pending"
            desp_status = "Completed" if desp_val or is_despatched_list else "Pending"
            
            # Count completed furnishing sub-sections
            completed_furn = 0
            for idx in [8, 9, 10, 11, 12, 13, 15, 16]:
                if str(r[idx]).strip():
                    completed_furn += 1
                    
            if completed_furn == 8:
                furn_status = "Completed"
            elif completed_furn > 0:
                furn_status = "Under progress"
            else:
                furn_status = "Yet to be taken"
                
            # Serialize granular dates into remarks JSON
            section_data = {
                "corrosion": corr_val,
                "bio_toilet": bio_val,
                "carpentry": str(r[8]).strip(),
                "trimming": str(r[9]).strip(),
                "air_brake": str(r[10]).strip(),
                "under_frame": str(r[11]).strip(),
                "train_lighting": str(r[12]).strip(),
                "water_service": str(r[13]).strip(),
                "lowering": low_val,
                "painting": str(r[15]).strip(),
                "final_cleaning": str(r[16]).strip(),
                "despatch": desp_val
            }
            remarks_json = json.dumps(section_data)
            
            db_payload.append({
                "coachno": cno,
                "corr_in_date": corr_val,
                "corrosion_status": corr_status,
                "bio_tank_status": bio_val,
                "lowering_status": low_status,
                "furnishing_status": furn_status,
                "despatch_status": desp_status,
                "pdc": "",
                "desp_date": desp_val,
                "remarks": remarks_json,
                "source_tab": str(r[5]).strip()
            })

    # Process remaining active rows
    process_rows_for_db(remaining_active_rows, is_despatched_list=False)
    
    # Process the last 50 archived rows to update their DB status to despatched
    recent_desp_rows = rows_desp[1:][-50:] if len(rows_desp) > 1 else []
    process_rows_for_db(recent_desp_rows, is_despatched_list=True)

    # 8. Clear and upsert to database (online)
    if db_payload:
        unique_payload = {}
        for item in db_payload:
            unique_payload[item["coachno"]] = item
        deduped = list(unique_payload.values())
        
        # A. Clear old corrosion records to prevent outdated list buildup
        try:
            delete_all_google_corrosion()
        except Exception as e:
            logger.error(f"Error clearing google_corrosion table: {e}")
            
        # B. Upsert online (Supabase)
        try:
            upsert_google_corrosion_bulk(deduped)
            logger.info(f"Upserted {len(deduped)} rows to Supabase.")
        except Exception as e:
            logger.error(f"Failed to upsert to Supabase: {e}")
            
        # C. Save offline (SQLite) - optional / mock if imported
        try:
            from services.db_service import save_google_corrosion_local
            save_google_corrosion_local(deduped)
            logger.info(f"Saved {len(deduped)} rows to local SQLite.")
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to save to local SQLite: {e}")

def sync_targets(full_sync=False):
    """
    Sync outturn targets from Google Sheet to Supabase:
    - Current year (2026-27): month-wise from 'HQ_Targets' worksheet.
    - Historical years: yearly from 'Archive_Targets' worksheet.
    """
    logger.info("Starting Google Sheets targets sync to Supabase...")
    
    # Check dependencies and credentials
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        logger.error("gspread or google-auth not installed. Cannot sync targets.")
        return {"success": False, "error": "gspread or google-auth libraries are missing"}
        
    if not os.path.exists(CREDENTIALS_PATH):
        logger.error("Credentials file not found at %s", CREDENTIALS_PATH)
        return {"success": False, "error": f"Credentials file not found at {CREDENTIALS_PATH}"}

    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets",
                 "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scope)
        client = gspread.authorize(creds)
        gsheet = client.open_by_key("17_yzOhhdSy0EQAqLpfuXMPJazsgtlW7QspNvYJLI2Qk")
        
        parsed_hq = {}
        parsed_archive = {}
        
        # 1. Fetch & Parse HQ_Targets (current month-wise targets & achievements)
        try:
            ws_hq = gsheet.worksheet("HQ_Targets")
            hq_rows = ws_hq.get_all_values()
            
            # Map Month_Idx (1-12 starting in April) to calendar month (4-12, 1-3)
            def map_month_idx(idx_str):
                try:
                    idx = int(idx_str)
                    return (idx + 2) % 12 + 1
                except (ValueError, TypeError):
                    return None
                    
            if len(hq_rows) > 0:
                headers = [h.strip().upper() for h in hq_rows[0]]
                
                fy_idx = headers.index("FY") if "FY" in headers else 0
                stock_idx = headers.index("STOCK TYPE") if "STOCK TYPE" in headers else 4
                sched_idx = headers.index("SCHEDULE") if "SCHEDULE" in headers else 5
                nac_ac_idx = headers.index("NAC/AC") if "NAC/AC" in headers else 6
                target_idx = headers.index("HQ TARGET") if "HQ TARGET" in headers else 7
                achieved_idx = headers.index("ACHIEVED") if "ACHIEVED" in headers else 8
                month_idx_idx = headers.index("MONTH_IDX") if "MONTH_IDX" in headers else 9
                working_days_idx = headers.index("WORKING DAYS") if "WORKING DAYS" in headers else -1
                
                for row in hq_rows[1:]:
                    if len(row) > max(fy_idx, stock_idx, sched_idx, nac_ac_idx, target_idx, achieved_idx, month_idx_idx):
                        fy = row[fy_idx].strip()
                        stock_type = row[stock_idx].strip()
                        schedule = row[sched_idx].strip()
                        ac_nac = row[nac_ac_idx].strip()
                        target_str = row[target_idx].strip()
                        achieved_str = row[achieved_idx].strip()
                        month_idx_str = row[month_idx_idx].strip()
                        working_days_str = row[working_days_idx].strip() if working_days_idx != -1 and len(row) > working_days_idx else "0"
                        
                        month = map_month_idx(month_idx_str)
                        if not fy or not stock_type or not schedule or month is None:
                            continue
                            
                        try:
                            t_qty = int(target_str)
                        except ValueError:
                            t_qty = 0
                            
                        try:
                            a_qty = int(achieved_str)
                        except ValueError:
                            a_qty = 0

                        try:
                            w_days = int(working_days_str)
                        except ValueError:
                            w_days = 0
                            
                        key = (fy, month, stock_type, schedule, ac_nac)
                        if key not in parsed_hq:
                            parsed_hq[key] = {"target": 0, "achieved": 0, "working_days": 0}
                        parsed_hq[key]["target"] += t_qty
                        parsed_hq[key]["achieved"] += a_qty
                        parsed_hq[key]["working_days"] = w_days
                        
            logger.info("Parsed %d monthly targets from HQ_Targets in memory", len(parsed_hq))
            
        except Exception as e:
            logger.error("Error parsing HQ_Targets worksheet: %s", e)
            return {"success": False, "error": f"Error parsing HQ_Targets worksheet: {str(e)}"}
            
        # 2. Fetch & Parse Archive_Targets (historical yearly targets & achievements)
        try:
            ws_archive = gsheet.worksheet("Archive_Targets")
            archive_rows = ws_archive.get_all_values()
            
            if len(archive_rows) > 0:
                headers = [h.strip().upper() for h in archive_rows[0]]
                
                fy_idx = -1
                stock_idx = -1
                sched_idx = -1
                nac_ac_idx = -1
                target_idx = -1
                achieved_idx = -1
                
                for idx, h in enumerate(headers):
                    if h in ("FY", "FINANCIAL YEAR", "YEAR"):
                        fy_idx = idx
                    elif h in ("STOCK TYPE", "TYPE", "STOCK"):
                        stock_idx = idx
                    elif h in ("SCHEDULE", "SCHED"):
                        sched_idx = idx
                    elif h in ("NAC/AC", "AC/NAC", "CLASS"):
                        nac_ac_idx = idx
                    elif h in ("TARGET", "ANNUAL TARGET", "TARGET_QTY"):
                        target_idx = idx
                    elif h in ("ACHIEVED", "ANNUAL ACHIEVED", "ACHIEVED_QTY", "OUTTURN"):
                        achieved_idx = idx
                        
                if fy_idx == -1: fy_idx = 0
                if stock_idx == -1: stock_idx = 1
                if sched_idx == -1: sched_idx = 2
                if nac_ac_idx == -1: nac_ac_idx = 3
                if target_idx == -1: target_idx = 4
                if achieved_idx == -1: achieved_idx = 5
                
                for row in archive_rows[1:]:
                    if len(row) > max(fy_idx, stock_idx, sched_idx, nac_ac_idx, target_idx, achieved_idx):
                        fy = row[fy_idx].strip()
                        stock_type = row[stock_idx].strip()
                        schedule = row[sched_idx].strip()
                        ac_nac = row[nac_ac_idx].strip()
                        target_str = row[target_idx].strip()
                        achieved_str = row[achieved_idx].strip()
                        
                        if not fy or not stock_type or not schedule:
                            continue
                            
                        try:
                            t_qty = int(target_str)
                        except ValueError:
                            t_qty = 0
                            
                        try:
                            a_qty = int(achieved_str)
                        except ValueError:
                            a_qty = 0
                            
                        key = (fy, 0, stock_type, schedule, ac_nac)
                        if key not in parsed_archive:
                            parsed_archive[key] = {"target": 0, "achieved": 0}
                        parsed_archive[key]["target"] += t_qty
                        parsed_archive[key]["achieved"] += a_qty
                        
            logger.info("Parsed %d yearly archive target records from Archive_Targets in memory", len(parsed_archive))
            
        except gspread.exceptions.WorksheetNotFound:
            logger.warning("Archive_Targets worksheet not found in Google Sheet. Skipping historical targets.")
        except Exception as e:
            logger.error("Error parsing Archive_Targets worksheet: %s", e)
            return {"success": False, "error": f"Error parsing Archive_Targets worksheet: {str(e)}"}
            
        # 3. Write to Supabase using HTTP REST queries
        try:
            # Clear old targets
            delete_all_outturn_targets()
            
            targets_payload = []
            for (fy, month, stock_type, schedule, ac_nac), qtys in parsed_hq.items():
                targets_payload.append({
                    "fy": fy,
                    "month": month,
                    "stock_type": stock_type,
                    "schedule": schedule,
                    "ac_nac": ac_nac,
                    "target_qty": qtys["target"],
                    "achieved_qty": qtys["achieved"],
                    "working_days": qtys.get("working_days", 0)
                })
                
            for (fy, month, stock_type, schedule, ac_nac), qtys in parsed_archive.items():
                targets_payload.append({
                    "fy": fy,
                    "month": month,
                    "stock_type": stock_type,
                    "schedule": schedule,
                    "ac_nac": ac_nac,
                    "target_qty": qtys["target"],
                    "achieved_qty": qtys["achieved"],
                    "working_days": 0
                })
                
            if targets_payload:
                insert_outturn_targets_bulk(targets_payload)
                
            # Sync google corrosion data from worksheets
            try:
                sync_corrosion_from_sheet(gsheet)
            except Exception as ce:
                logger.error("Failed to sync corrosion data: %s", ce)

            logger.info("Successfully synced targets and corrosion data to Supabase.")
            
        except Exception as db_err:
            logger.error("Supabase write failed: %s", db_err)
            return {"success": False, "error": f"Supabase write error: {str(db_err)}"}
            
        return {
            "success": True,
            "hq_records": len(parsed_hq),
            "archive_records": len(parsed_archive)
        }
        
    except Exception as e:
        logger.error("Failed to connect to Google Sheet: %s", e)
        return {"success": False, "error": f"Google Sheet connection error: {str(e)}"}

def track_coach_movements():
    """
    Query the active coaches in workshop and check if they have changed locations.
    Write movement logs to Supabase via HTTP REST.
    """
    logger.info("Running active coach movement tracker...")
    try:
        coaches = fetch_clean()
    except Exception as e:
        logger.error("fetch_clean failed in track_coach_movements: %s", e)
        return 0
        
    movements_logged = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for coach in coaches:
        coachno = coach.get("coachno")
        current_loc = coach.get("pitnum")
        
        if not coachno or not current_loc:
            continue
            
        coachno = str(coachno).strip()
        current_loc = str(current_loc).strip()
        
        try:
            # Get last known location from movements
            row = get_last_coach_movement(coachno)
            
            if row is None:
                # First time logging location for this coach - log arrival using recd_date from ERP
                recd_str = coach.get("recd_date") or coach.get("recddate") or ""
                recd_dt = _parse_date(recd_str)
                recd_now_str = recd_dt.strftime("%Y-%m-%d 00:00:00") if recd_dt else now_str
                insert_coach_movement(coachno, "ARRIVED", current_loc, recd_now_str)
                movements_logged += 1
            else:
                last_loc = row.get("to_location")
                if last_loc != current_loc:
                    # Coach has moved!
                    insert_coach_movement(coachno, last_loc, current_loc, now_str)
                    movements_logged += 1
                    logger.info("Coach %s moved from %s to %s", coachno, last_loc, current_loc)
        except Exception as exc:
            logger.error(f"Error tracking movement for coach {coachno}: {exc}")
                
    if movements_logged > 0:
        logger.info("Log complete: %d coach movements logged", movements_logged)
    return movements_logged
