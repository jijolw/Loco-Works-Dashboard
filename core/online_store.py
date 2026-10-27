"""
core/online_store.py - the online dashboard's data = one snapshot file in Supabase Storage.

The office PC uploads the same ERP export (gzip JSON) after every 'Update from ERP';
Render downloads it. No per-coach tables, no movement history.
Bucket (private) is created automatically on the first upload.
"""
import gzip
import json

import requests

import config

OBJECT = "erp_snapshot.json.gz"


def _h(extra=None):
    h = {"apikey": config.SUPABASE_KEY, "Authorization": f"Bearer {config.SUPABASE_KEY}"}
    h.update(extra or {})
    return h


def _base():
    return f"{config.SUPABASE_URL}/storage/v1"


def ensure_bucket():
    r = requests.get(f"{_base()}/bucket/{config.SUPABASE_BUCKET}", headers=_h(), timeout=20)
    if r.status_code == 200:
        return
    requests.post(f"{_base()}/bucket", headers=_h({"Content-Type": "application/json"}),
                  data=json.dumps({"id": config.SUPABASE_BUCKET, "name": config.SUPABASE_BUCKET,
                                   "public": False}), timeout=20)


def upload_snapshot(payload):
    ensure_bucket()
    body = gzip.compress(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))
    r = requests.post(f"{_base()}/object/{config.SUPABASE_BUCKET}/{OBJECT}",
                      headers=_h({"Content-Type": "application/gzip", "x-upsert": "true"}),
                      data=body, timeout=120)
    r.raise_for_status()


def download_snapshot():
    if not (config.SUPABASE_URL and config.SUPABASE_KEY):
        return None
    try:
        r = requests.get(f"{_base()}/object/{config.SUPABASE_BUCKET}/{OBJECT}", headers=_h(), timeout=60)
        r.raise_for_status()
        return json.loads(gzip.decompress(r.content).decode("utf-8"))
    except Exception:
        return None
