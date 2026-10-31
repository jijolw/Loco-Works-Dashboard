"""
core/condemnation.py - coaches proposed for condemnation, from OUR sheet POSITION11092026,
tab Condemnation_Pipeline (JIJO keeps it by hand - full record of proposed / condemned coaches).
READ only, through the service account. A saved copy (data/condemnation.json) is used when the sheet
cannot be read. The Daily Position report underlines in red only the coaches that are still in holding;
when JIJO sets a coach to Return in ERP it leaves holding and drops off the report by itself.
"""
import json
import os
from datetime import datetime

import config

TAB = "Condemnation_Pipeline"
FILE = os.path.join(config.APP_DIR, "data", "condemnation.json")


def refresh():
    from updaters.common import open_sheet
    vals = open_sheet(config.POSITION_SHEET_KEY).worksheet(TAB).get_all_values()
    head_i = next((i for i, r in enumerate(vals) if any("coach" in str(c).lower() for c in r)), None)
    rows = []
    if head_i is not None:
        head = [str(h).strip() for h in vals[head_i]]
        ci = next(i for i, h in enumerate(head) if "coach" in h.lower())
        for r in vals[head_i + 1:]:
            r = list(r) + [""] * (len(head) - len(r))
            if str(r[ci]).strip():
                rows.append({h or f"col{i}": str(r[i]).strip() for i, h in enumerate(head)} | {"coach": str(r[ci]).strip()})
    out = {"read_at": datetime.now().strftime("%d-%m-%Y %H:%M"), "rows": rows}
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    return out


def load(live=True):
    """-> (data, error). Tries the sheet first (office PC), falls back to the saved copy."""
    err = None
    if live and config.IS_LOCAL:
        try:
            return refresh(), None
        except Exception as e:
            err = f"Condemnation_Pipeline not read ({e}) - last saved copy used"
    try:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f), err
    except Exception:
        return {"read_at": "", "rows": []}, err or "Condemnation_Pipeline not read yet"
