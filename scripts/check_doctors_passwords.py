import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from auth.security import verify_password, hash_password

conn = sqlite3.connect('clinical_local.db')
cur = conn.cursor()
cur.execute("SELECT doctor_id, email, password_hash, verification_status, is_active, email_verified FROM Doctors")
rows = cur.fetchall()
print(f"Total doctors in DB: {len(rows)}")
for r in rows:
    pws = ["demo-doctor-2026", "DemoDoctor2026!", "DoctorSecure2026!", "password123"]
    matched = None
    for pw in pws:
        if verify_password(pw, r[2]):
            matched = pw
            break
    print(f"Doctor: {r[1]} | Status: {r[3]} | Active: {r[4]} | EmailVerified: {r[5]} | MatchedPW: {matched}")
conn.close()
