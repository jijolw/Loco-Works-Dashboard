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


def sync_corrosion_from_sheet(gsheet):
    """
    Sync corrosion and stage data from LHB, ICF NAC, and MEMU/EMU TC worksheets.
    """
    logger.info("Syncing corrosion and stages data from Google Sheet worksheets...")
    
    # 1. Clear old records in Supabase
    try:
        delete_all_google_corrosion()
    except Exception as e:
        logger.error(f"Error clearing google_corrosion table: {e}")
        
    tabs = [
        {"name": "LHB", "header_row": 0},
        {"name": "ICF NAC", "header_row": 1},
        {"name": "MEMU/EMU TC", "header_row": 0},
        {"name": "NMGHS CONV", "header_row": 1},
        {"name": "NMG POH", "header_row": 1},
        {"name": "DEMU", "header_row": 0}
    ]
    
    for tab in tabs:
        tab_name = tab["name"]
        header_row_idx = tab["header_row"]
        try:
            ws = gsheet.worksheet(tab_name)
            rows = ws.get_all_values()
            if len(rows) > header_row_idx:
                # Map headers to lower case
                headers = [h.strip().lower() for h in rows[header_row_idx]]
                
                c_idx = -1
                for idx, h in enumerate(headers):
                    if h in ("coach no", "rs no", "rs. no"):
                        c_idx = idx
                        break
                        
                if c_idx == -1:
                    logger.warning("Worksheet %s missing coach number column (coach no or rs no). Skipping.", tab_name)
                    continue
                    
                corr_in_idx = -1
                for idx, h in enumerate(headers):
                    if h in ("corr in date", "corrosion in date"):
                        corr_in_idx = idx
                        break
                        
                corr_idx = -1
                for idx, h in enumerate(headers):
                    if h in ("corrosion", "cr corrosion"):
                        corr_idx = idx
                        break
                        
                bio_tank_idx = headers.index("bio tank loaded") if "bio tank loaded" in headers else -1
                
                lowering_idx = -1
                for idx, h in enumerate(headers):
                    if h in ("lowering", "bogie wheeling"):
                        lowering_idx = idx
                        break
                
                # Furnishing column
                furn_idx = -1
                for idx, h in enumerate(headers):
                    if h.startswith("furnishing"):
                        furn_idx = idx
                        break
                        
                # Despatch status column
                desp_status_idx = -1
                for idx, h in enumerate(headers):
                    if h.startswith("despatch"):
                        desp_status_idx = idx
                        break
                        
                # PDC column
                pdc_idx = -1
                for idx, h in enumerate(headers):
                    if "pdc" in h:
                        pdc_idx = idx
                        break
                        
                desp_date_idx = -1
                for idx, h in enumerate(headers):
                    if "desp date" in h or "despatch date" in h or h == "tfr on":
                        desp_date_idx = idx
                        break
                        
                remarks_idx = headers.index("remarks") if "remarks" in headers else -1
                
                payload = []
                for row in rows[header_row_idx+1:]:
                    if len(row) > c_idx:
                        c_no = str(row[c_idx]).strip()
                        if not c_no or c_no.lower() in ("coach no", "sl no", "slno", ""):
                            continue
                        
                        corr_in = str(row[corr_in_idx]).strip() if corr_in_idx != -1 and len(row) > corr_in_idx else ""
                        corr_stat = str(row[corr_idx]).strip() if corr_idx != -1 and len(row) > corr_idx else ""
                        bio_tank = str(row[bio_tank_idx]).strip() if bio_tank_idx != -1 and len(row) > bio_tank_idx else ""
                        lowering = str(row[lowering_idx]).strip() if lowering_idx != -1 and len(row) > lowering_idx else ""
                        furn = str(row[furn_idx]).strip() if furn_idx != -1 and len(row) > furn_idx else ""
                        desp_stat = str(row[desp_status_idx]).strip() if desp_status_idx != -1 and len(row) > desp_status_idx else ""
                        pdc = str(row[pdc_idx]).strip() if pdc_idx != -1 and len(row) > pdc_idx else ""
                        desp_date = str(row[desp_date_idx]).strip() if desp_date_idx != -1 and len(row) > desp_date_idx else ""
                        rem = str(row[remarks_idx]).strip() if remarks_idx != -1 and len(row) > remarks_idx else ""
                        
                        payload.append({
                            "coachno": c_no,
                            "corr_in_date": corr_in,
                            "corrosion_status": corr_stat,
                            "bio_tank_status": bio_tank,
                            "lowering_status": lowering,
                            "furnishing_status": furn,
                            "despatch_status": desp_stat,
                            "pdc": pdc,
                            "desp_date": desp_date,
                            "remarks": rem,
                            "source_tab": tab_name
                        })
                
                if payload:
                    upsert_google_corrosion_bulk(payload)
                    logger.info("Synced %s rows: %d", tab_name, len(payload))
        except Exception as e:
            logger.error("Error syncing worksheet %s: %s", tab_name, e)

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
        gsheet = client.open_by_key(SHEET_KEY)
        
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
