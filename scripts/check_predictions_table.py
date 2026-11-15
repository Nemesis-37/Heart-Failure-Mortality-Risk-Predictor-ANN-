import sqlite3

conn = sqlite3.connect("clinical_schema.db")
cur = conn.cursor()
cols = [r[1] for r in cur.execute("PRAGMA table_info(Predictions)").fetchall()]
print("Predictions columns:", cols)

cols_doc = [r[1] for r in cur.execute("PRAGMA table_info(Doctors)").fetchall()]
print("Doctors columns:", cols_doc)

cols_asm = [r[1] for r in cur.execute("PRAGMA table_info(Assessments)").fetchall()]
print("Assessments columns:", cols_asm)

cols_adm = [r[1] for r in cur.execute("PRAGMA table_info(Administrators)").fetchall()]
print("Administrators columns:", cols_adm)
