import sqlite3
for f in ['clinical_local.db', 'clinical_schema.db']:
    try:
        conn = sqlite3.connect(f)
        tables = [r[0] for r in conn.cursor().execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"{f}: {tables}")
    except Exception as e:
        print(f"Error {f}: {e}")
