import sqlite3
import json

conn = sqlite3.connect("clinical_local.db")
cur = conn.cursor()

# Get all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [r[0] for r in cur.fetchall()]
print(f"--- TABLES FOUND IN clinical_local.db ({len(tables)}) ---")

schema_report = {}

for tbl in tables:
    cur.execute(f"SELECT COUNT(*) FROM \"{tbl}\"")
    cnt = cur.fetchone()[0]
    
    cur.execute(f"PRAGMA table_info(\"{tbl}\")")
    cols = cur.fetchall()
    
    cur.execute(f"PRAGMA foreign_key_list(\"{tbl}\")")
    fks = cur.fetchall()
    
    cur.execute(f"PRAGMA index_list(\"{tbl}\")")
    idxs = cur.fetchall()
    
    schema_report[tbl] = {
        "row_count": cnt,
        "columns": [
            {"cid": c[0], "name": c[1], "type": c[2], "notnull": bool(c[3]), "default": c[4], "pk": bool(c[5])}
            for c in cols
        ],
        "foreign_keys": [
            {"id": f[0], "seq": f[1], "table": f[2], "from": f[3], "to": f[4]}
            for f in fks
        ],
        "indexes": [
            {"seq": idx[0], "name": idx[1], "unique": bool(idx[2])}
            for idx in idxs
        ]
    }
    print(f"Table '{tbl}': {cnt} rows, {len(cols)} columns, {len(fks)} foreign keys, {len(idxs)} indexes")

conn.close()

with open("scripts/sqlite_schema_dump.json", "w", encoding="utf-8") as f:
    json.dump(schema_report, f, indent=2)

print("\nSchema dump saved to scripts/sqlite_schema_dump.json")
