"""
core/data.py - one place that loads the ERP snapshot for every page.

Local : the export file (08_Claude_ERP_Export/data/erp_demands_latest.json)
Online: the same snapshot uploaded to Supabase Storage by the office PC
Every demand gets _family / _group / _order added from core.rules.classify.
"""
import json
import os
import threading
from datetime import datetime

import config
from core import rules
from core import physical      # HQ OUT TURN physical despatch overlay (JIJO 10-11-2026)

_lock = threading.Lock()
_cache = {"stamp": None, "demands": [], "exported_at": None, "loaded": None, "km": {}, "targets": {},
          "phys_checks": []}
KM_FILE = os.path.join(config.APP_DIR, "data", "km_status.json")
ONLINE_TTL = 600  # seconds between Supabase checks


def _enrich(demands):
    for d in demands:
        fam, grp, order = rules.classify(d)
        d["_family"], d["_group"], d["_order"] = fam, grp, order
    return demands


def _parse_stamp(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def load(force=False):
    """-> (demands, exported_at datetime)."""
    with _lock:
        if config.IS_LOCAL:
            try:
                stamp = (os.path.getmtime(config.EXPORT_PATH), os.path.getmtime(rules.GROUPS_CSV), physical.mtime())
            except OSError:
                return [], None
            if force or stamp != _cache["stamp"]:
                with open(config.EXPORT_PATH, encoding="utf-8") as f:
                    p = json.load(f)
                D = _enrich(p.get("demands", []))
                ex = _parse_stamp(p.get("exported_at"))
                # physical despatch = HQ OUT TURN (DESP date / FND / RFD) for the coaches listed there;
                # ERP actualDispatchDate (shop out) kept in _shopOut. Others stay on ERP.
                # JIJO 12-11-2026: ERP ONLY here. HQ OUT TURN is used only in the daily planner (update_all.py
                # applies physical.apply() on its own copy for the Production Plan tabs).
                checks = []
                _cache.update(stamp=stamp, demands=D, exported_at=ex, loaded=datetime.now(), phys_checks=checks)
        else:
            age = (datetime.now() - _cache["loaded"]).total_seconds() if _cache["loaded"] else None
            if force or age is None or age > ONLINE_TTL:
                from core import online_store
                p = online_store.download_snapshot()
                if p:
                    D = _enrich(p.get("demands", []))
                    _cache["phys_checks"] = []              # ERP only (JIJO 12-11-2026)
                    _cache.update(demands=D,
                                  exported_at=_parse_stamp(p.get("exported_at")),
                                  km=p.get("km_status") or {}, targets=p.get("targets") or {})
                _cache["loaded"] = datetime.now()
        return _cache["demands"], _cache["exported_at"]


def phys_checks():
    """CHECK lines from the HQ OUT TURN overlay (coach not in ERP, ERP FND not in HQ, unreadable date...)."""
    load()
    return list(_cache.get("phys_checks") or [])


def as_on():
    return load()[1]


def km_status():
    """HQ Kumbh Mela status by coach (key without leading zeros) - saved by Update_All (HQ sheet read only)."""
    if config.IS_LOCAL:
        try:
            with open(KM_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    load()
    return _cache.get("km") or {}
