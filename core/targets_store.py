"""
core/targets_store.py - the three target tabs of OUR sheet POSITION11092026
(Internal_Targets, HQ_Targets, RB_Targets), read in full through the service account.

Why not the public CSV link: Google sends only the rows a sheet FILTER leaves visible, so a filter on
"October" made April-September disappear (27-10-2026). The service account always reads every row.

Office PC: Update_All and the "Update from ERP" button call refresh(), which saves data/targets.json and the
same copy goes into the online snapshot. Render reads the targets from the snapshot (it has no credentials).
"""
import json
import os
from datetime import datetime

import config

TABS = ["Internal_Targets", "HQ_Targets", "RB_Targets"]
FILE = os.path.join(config.APP_DIR, "data", "targets.json")


def refresh():
    """Read all rows of the three tabs (READ only) and save them. Returns the saved dict."""
    from updaters.common import open_sheet
    sh = open_sheet(config.POSITION_SHEET_KEY)
    out = {"read_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "tabs": {}}
    for t in TABS:
        vals = sh.worksheet(t).get_all_values()
        if not vals:
            out["tabs"][t] = []
            continue
        head = [h.strip() for h in vals[0]]
        out["tabs"][t] = [dict(zip(head, [str(x) for x in r])) for r in vals[1:] if any(str(x).strip() for x in r)]
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(out, f)
    return out


def load():
    """-> {"read_at": ..., "tabs": {tab: [row dicts]}} or {} when not read yet."""
    if config.IS_LOCAL:
        try:
            with open(FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    from core import data
    data.load()
    return data._cache.get("targets") or {}


def rows(tab):
    return (load().get("tabs") or {}).get(tab, [])


def read_at():
    return load().get("read_at", "")
