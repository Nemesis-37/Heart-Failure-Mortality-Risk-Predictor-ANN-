import sqlite3

for db_name in ["clinical_local.db", "clinical_schema.db"]:
    try:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in c.fetchall()]
        print(f"{db_name} tables:", tables)
        for t in tables:
            c.execute(f"PRAGMA table_info({t})")
            cols = [row[1] for row in c.fetchall()]
            print(f"  {t} columns:", cols)
        conn.close()
    except Exception as e:
        print(f"Error on {db_name}:", e)
