import sqlite3

conn = sqlite3.connect("clinical_local.db")
cur = conn.cursor()

print("=== Columns of Assessments table in SQLite ===")
cur.execute("PRAGMA table_info(Assessments)")
for col in cur.fetchall():
    print(" ", col)

print("\n=== Actual Assessments Rows ===")
cur.execute("SELECT * FROM Assessments")
rows = cur.fetchall()
col_names = [d[0] for d in cur.description]
print("Columns:", col_names)
for r in rows:
    print(" ", dict(zip(col_names, r)))

conn.close()
