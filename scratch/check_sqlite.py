import sqlite3

def check():
    conn = sqlite3.connect('../ERP/db.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    print('Tables in ERP/db.sqlite:', tables)
    cursor.execute("SELECT * FROM coach_movements WHERE coachno='111143'")
    rows = cursor.fetchall()
    print("Movements for 111143 in db.sqlite:")
    for r in rows:
        print(r)

check()
