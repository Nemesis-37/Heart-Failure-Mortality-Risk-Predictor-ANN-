import sys
from pathlib import Path
sys.path.insert(0, str(Path('.')))
from auth.security import _hasher, verify_password
import sqlite3

conn = sqlite3.connect('clinical_local.db')
cur = conn.cursor()
cur.execute("SELECT password_hash FROM Doctors WHERE email='dr.carter@hospital.org'")
h = cur.fetchone()[0]
conn.close()

print('Hash:', h)
try:
    print('Hasher verify demo-doctor-2026:', _hasher.verify(h, 'demo-doctor-2026'))
except Exception as e:
    print('Hasher verify failed:', type(e).__name__, e)
