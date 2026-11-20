import pyodbc

protocols = [
    r"DRIVER={ODBC Driver 18 for SQL Server};SERVER=np:\\.\pipe\MSSQL$SQLEXPRESS\sql\query;DATABASE=HeartMortalityPredictor;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;",
    r"DRIVER={ODBC Driver 18 for SQL Server};SERVER=np:\\.\pipe\SQLEXPRESS\sql\query;DATABASE=HeartMortalityPredictor;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;",
    r"DRIVER={ODBC Driver 18 for SQL Server};SERVER=(local)\SQLEXPRESS;DATABASE=HeartMortalityPredictor;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;",
    r"DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost\SQLEXPRESS;DATABASE=HeartMortalityPredictor;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;",
    r"DRIVER={ODBC Driver 18 for SQL Server};SERVER=127.0.0.1;DATABASE=HeartMortalityPredictor;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;",
    r"DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:localhost;DATABASE=HeartMortalityPredictor;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;",
]

for p in protocols:
    target = [x for x in p.split(";") if x.startswith("SERVER=")][0]
    print(f"Testing {target} ...")
    try:
        conn = pyodbc.connect(p, timeout=2)
        cur = conn.cursor()
        cur.execute("SELECT @@SERVERNAME, DB_NAME()")
        print("  SUCCESS:", cur.fetchone())
        conn.close()
        break
    except Exception as e:
        print(f"  Failed ({type(e).__name__}): {str(e)[:120]}")
