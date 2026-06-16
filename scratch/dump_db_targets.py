import sqlite3

conn = sqlite3.connect("db.sqlite")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM outturn_targets")
rows = cursor.fetchall()
for r in rows:
    print(dict(r))
conn.close()
