import sqlite3

conn = sqlite3.connect("C:\\Users\\User\\.gemini\\antigravity\\scratch\\ERP\\db.sqlite")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables in db: {tables}")

for t in tables:
    table_name = t[0]
    cursor.execute(f"PRAGMA table_info({table_name});")
    info = cursor.fetchall()
    print(f"\nTable {table_name} Columns:")
    for col in info:
        print(f"  {col[1]} ({col[2]})")
conn.close()
