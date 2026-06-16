import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "db.sqlite"))
print(f"Connecting to database at {db_path}...")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT DISTINCT fy, month, family, target_qty FROM outturn_targets ORDER BY fy, month, family")
rows = cursor.fetchall()

print(f"\nUnique targets found (Total: {len(rows)}):")
for r in rows:
    print(f"  FY: {r['fy']}, Month: {r['month']}, Family: {r['family']}, Target: {r['target_qty']}")
    
cursor.execute("SELECT DISTINCT family FROM outturn_targets")
families = [r["family"] for r in cursor.fetchall()]
print(f"\nDistinct families in targets: {families}")

conn.close()
