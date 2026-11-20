import pyodbc

conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=.\\SQLEXPRESS;"
    "DATABASE=HeartMortalityPredictor;"
    "Trusted_Connection=yes;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    cursor.execute("SELECT @@SERVERNAME, DB_NAME()")
    result = cursor.fetchone()

    print("CONNECTED SUCCESSFULLY!")
    print("Server:", result[0])
    print("Database:", result[1])

    conn.close()

except Exception as e:
    print("CONNECTION FAILED:", e)




    