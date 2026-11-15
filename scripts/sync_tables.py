import sqlite3

src = sqlite3.connect("clinical_schema.db")
dst = sqlite3.connect("clinical_local.db")

src_tables = [r[0] for r in src.cursor().execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
dst_tables = [r[0] for r in dst.cursor().execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

print("Source tables:", src_tables)
print("Destination tables before:", dst_tables)

for t in src_tables:
    if t not in dst_tables:
        sql = src.cursor().execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{t}'").fetchone()[0]
        dst.cursor().execute(sql)
        print(f"Created table {t} in clinical_local.db")

dst.commit()
print("Destination tables after:", [r[0] for r in dst.cursor().execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])
