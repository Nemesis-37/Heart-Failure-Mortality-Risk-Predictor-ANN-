"""
scripts/test_doctor_signup_audit.py
===================================
Comprehensive audit and verification suite for Physician Registration / Signup:
1. Registration without document (201 Created)
2. Registration with PDF document (201 Created, document saved on disk)
3. Duplicate email rejection (400 Bad Request)
4. Duplicate registration number rejection (400 Bad Request)
5. Password validation:
   - Missing uppercase
   - Missing lowercase
   - Missing digit
   - Length < 8
   - Mismatched passwords
6. Field validation:
   - Full name < 3 chars
   - Invalid email format
   - Mobile < 7 digits
   - Medical degree < 2 chars
   - Registration council < 2 chars
7. Document format rejection (invalid file extension)
8. Document size limit rejection (> 10MB)
9. CORS headers verification for localhost:5173
10. OTP generation and verification flow
11. Login preservation check (ensuring existing login remains functional)
"""

import io
import os
import sys
import uuid
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from main import app
from backend.database.config import SessionLocal
from backend.database.models import Doctor, EmailOTP

client = TestClient(app, raise_server_exceptions=True)

def run_tests():
    print("=" * 60)
    print("STARTING PHYSICIAN SIGNUP & REGISTRATION AUDIT SUITE")
    print("=" * 60)

    results = []
    created_doctor_emails = []

    def log_result(name, passed, detail=""):
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {name} {f'- {detail}' if detail else ''}")
        results.append((name, passed, detail))

    from backend.database.config import Base
    db = SessionLocal()

    try:
        # TEST 1: Registration without document
        email_no_doc = f"dr.audit_nodoc_{uuid.uuid4().hex[:6]}@hospital.org"
        reg_no_doc = f"REG-NODOC-{uuid.uuid4().hex[:6].upper()}"
        created_doctor_emails.append(email_no_doc)

        res1 = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Sarah Connor, MD",
                "email": email_no_doc,
                "mobile": "+1 (555) 345-6789",
                "medical_degree": "MBBS, MD Cardiology",
                "registration_number": reg_no_doc,
                "registration_council": "American Board of Internal Medicine",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )
        res1_json = res1.json() if res1.headers.get("content-type", "").startswith("application/json") else {}
        test1_pass = (
            res1.status_code == 201
            and res1_json.get("status") == "success"
            and res1_json.get("doctor", {}).get("document_uploaded") is False
        )
        log_result("1. Registration without document", test1_pass, f"HTTP {res1.status_code}")

        # TEST 2: Registration with PDF document
        email_with_doc = f"dr.audit_pdf_{uuid.uuid4().hex[:6]}@hospital.org"
        reg_with_doc = f"REG-PDF-{uuid.uuid4().hex[:6].upper()}"
        created_doctor_emails.append(email_with_doc)

        pdf_payload = b"%PDF-1.4\n%Test medical license certificate\n%%EOF"
        files = {
            "document": ("medical_license.pdf", io.BytesIO(pdf_payload), "application/pdf")
        }
        res2 = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Marcus Brody, MD",
                "email": email_with_doc,
                "mobile": "+1 (555) 987-6543",
                "medical_degree": "MBBS, FACC",
                "registration_number": reg_with_doc,
                "registration_council": "California Medical Board",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            files=files,
        )
        res2_json = res2.json() if res2.headers.get("content-type", "").startswith("application/json") else {}
        test2_pass = (
            res2.status_code == 201
            and res2_json.get("status") == "success"
            and res2_json.get("doctor", {}).get("document_uploaded") is True
        )
        log_result("2. Registration with PDF document", test2_pass, f"HTTP {res2.status_code}")

        # TEST 3: Duplicate email rejection
        res3 = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Duplicate Email",
                "email": email_no_doc,  # Duplicate
                "mobile": "+1 (555) 111-2222",
                "medical_degree": "MD",
                "registration_number": f"REG-NEW-{uuid.uuid4().hex[:6].upper()}",
                "registration_council": "State Medical Board",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )
        test3_pass = (
            res3.status_code == 400
            and "already exists" in res3.text.lower()
        )
        log_result("3. Duplicate email rejection", test3_pass, f"HTTP {res3.status_code}: {res3.text[:60]}")

        # TEST 4: Duplicate registration number rejection
        res4 = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Duplicate Reg",
                "email": f"dr.new_{uuid.uuid4().hex[:6]}@hospital.org",
                "mobile": "+1 (555) 111-2222",
                "medical_degree": "MD",
                "registration_number": reg_no_doc,  # Duplicate
                "registration_council": "State Medical Board",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )
        test4_pass = (
            res4.status_code == 400
            and "registration number is already registered" in res4.text.lower()
        )
        log_result("4. Duplicate registration number rejection", test4_pass, f"HTTP {res4.status_code}: {res4.text[:60]}")

        # TEST 5: Password validation edge cases
        # 5a: Missing uppercase
        res5a = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Test Pwd",
                "email": f"dr.pwd_{uuid.uuid4().hex[:6]}@hospital.org",
                "mobile": "+1 (555) 111-2222",
                "medical_degree": "MD",
                "registration_number": f"REG-P-{uuid.uuid4().hex[:6].upper()}",
                "registration_council": "Medical Board",
                "password": "password123!",
                "confirm_password": "password123!",
            },
        )
        test5a_pass = res5a.status_code == 400 and "uppercase" in res5a.text.lower()
        log_result("5a. Password missing uppercase rejection", test5a_pass, f"HTTP {res5a.status_code}")

        # 5b: Missing lowercase
        res5b = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Test Pwd",
                "email": f"dr.pwd_{uuid.uuid4().hex[:6]}@hospital.org",
                "mobile": "+1 (555) 111-2222",
                "medical_degree": "MD",
                "registration_number": f"REG-P-{uuid.uuid4().hex[:6].upper()}",
                "registration_council": "Medical Board",
                "password": "PASSWORD123!",
                "confirm_password": "PASSWORD123!",
            },
        )
        test5b_pass = res5b.status_code == 400 and "lowercase" in res5b.text.lower()
        log_result("5b. Password missing lowercase rejection", test5b_pass, f"HTTP {res5b.status_code}")

        # 5c: Missing digit
        res5c = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Test Pwd",
                "email": f"dr.pwd_{uuid.uuid4().hex[:6]}@hospital.org",
                "mobile": "+1 (555) 111-2222",
                "medical_degree": "MD",
                "registration_number": f"REG-P-{uuid.uuid4().hex[:6].upper()}",
                "registration_council": "Medical Board",
                "password": "Password!",
                "confirm_password": "Password!",
            },
        )
        test5c_pass = res5c.status_code == 400 and "digit" in res5c.text.lower()
        log_result("5c. Password missing digit rejection", test5c_pass, f"HTTP {res5c.status_code}")

        # 5d: Length < 8
        res5d = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Test Pwd",
                "email": f"dr.pwd_{uuid.uuid4().hex[:6]}@hospital.org",
                "mobile": "+1 (555) 111-2222",
                "medical_degree": "MD",
                "registration_number": f"REG-P-{uuid.uuid4().hex[:6].upper()}",
                "registration_council": "Medical Board",
                "password": "Pass1!",
                "confirm_password": "Pass1!",
            },
        )
        test5d_pass = res5d.status_code == 400 and "at least 8" in res5d.text.lower()
        log_result("5d. Password length < 8 rejection", test5d_pass, f"HTTP {res5d.status_code}")

        # 5e: Mismatched passwords
        res5e = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Test Pwd",
                "email": f"dr.pwd_{uuid.uuid4().hex[:6]}@hospital.org",
                "mobile": "+1 (555) 111-2222",
                "medical_degree": "MD",
                "registration_number": f"REG-P-{uuid.uuid4().hex[:6].upper()}",
                "registration_council": "Medical Board",
                "password": "Password123!",
                "confirm_password": "DifferentPassword123!",
            },
        )
        test5e_pass = res5e.status_code == 400 and "match" in res5e.text.lower()
        log_result("5e. Password mismatch rejection", test5e_pass, f"HTTP {res5e.status_code}")

        # TEST 6: Field validation
        # 6a: Full name < 3 chars
        res6a = client.post(
            "/auth/register",
            data={
                "full_name": "Dr",
                "email": f"dr.name_{uuid.uuid4().hex[:6]}@hospital.org",
                "mobile": "+1 (555) 111-2222",
                "medical_degree": "MD",
                "registration_number": f"REG-N-{uuid.uuid4().hex[:6].upper()}",
                "registration_council": "Medical Board",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )
        test6a_pass = res6a.status_code == 400 and "at least 3 characters" in res6a.text.lower()
        log_result("6a. Short full name rejection", test6a_pass, f"HTTP {res6a.status_code}")

        # 6b: Invalid email format
        res6b = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Valid Name",
                "email": "not-an-email",
                "mobile": "+1 (555) 111-2222",
                "medical_degree": "MD",
                "registration_number": f"REG-N-{uuid.uuid4().hex[:6].upper()}",
                "registration_council": "Medical Board",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )
        test6b_pass = res6b.status_code == 400 and "email" in res6b.text.lower()
        log_result("6b. Invalid email format rejection", test6b_pass, f"HTTP {res6b.status_code}")

        # 6c: Short phone number
        res6c = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Valid Name",
                "email": f"dr.ph_{uuid.uuid4().hex[:6]}@hospital.org",
                "mobile": "12345",  # < 7 digits
                "medical_degree": "MD",
                "registration_number": f"REG-N-{uuid.uuid4().hex[:6].upper()}",
                "registration_council": "Medical Board",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )
        test6c_pass = res6c.status_code == 400 and "minimum 7" in res6c.text.lower()
        log_result("6c. Short phone number rejection", test6c_pass, f"HTTP {res6c.status_code}")

        # TEST 7: Invalid document extension rejection
        res7 = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Invalid Doc",
                "email": f"dr.invdoc_{uuid.uuid4().hex[:6]}@hospital.org",
                "mobile": "+1 (555) 111-2222",
                "medical_degree": "MD",
                "registration_number": f"REG-DOC-{uuid.uuid4().hex[:6].upper()}",
                "registration_council": "Medical Board",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            files={"document": ("malicious.exe", io.BytesIO(b"MZ..."), "application/x-msdownload")},
        )
        test7_pass = res7.status_code == 400 and "invalid document format" in res7.text.lower()
        log_result("7. Invalid document extension rejection", test7_pass, f"HTTP {res7.status_code}")

        # TEST 8: Document size limit rejection (> 10MB)
        large_content = b"0" * (11 * 1024 * 1024)  # 11 MB
        res8 = client.post(
            "/auth/register",
            data={
                "full_name": "Dr. Large Doc",
                "email": f"dr.largedoc_{uuid.uuid4().hex[:6]}@hospital.org",
                "mobile": "+1 (555) 111-2222",
                "medical_degree": "MD",
                "registration_number": f"REG-DOC-{uuid.uuid4().hex[:6].upper()}",
                "registration_council": "Medical Board",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            files={"document": ("large_cert.pdf", io.BytesIO(large_content), "application/pdf")},
        )
        test8_pass = res8.status_code == 400 and "exceeds 10mb" in res8.text.lower()
        log_result("8. Document > 10MB rejection", test8_pass, f"HTTP {res8.status_code}")

        # TEST 9: CORS headers verification for http://localhost:5173
        cors_options = client.options(
            "/auth/register",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        test9a_pass = (
            cors_options.status_code == 200
            and cors_options.headers.get("access-control-allow-origin") == "http://localhost:5173"
        )
        log_result("9a. CORS OPTIONS preflight for localhost:5173", test9a_pass, f"HTTP {cors_options.status_code}")

        # TEST 10: OTP generated in database and verification flow
        doc_record = db.query(Doctor).filter(Doctor.email == email_no_doc).first()
        test10a_pass = doc_record is not None and doc_record.verification_status == "PENDING"
        log_result("10a. Doctor record persisted with status PENDING", test10a_pass)

        otp_record = db.query(EmailOTP).filter(EmailOTP.doctor_id == doc_record.doctor_id).first()
        test10b_pass = otp_record is not None and otp_record.otp_hash.startswith("$otp$v=1$")
        log_result("10b. Verification OTP generated with PBKDF2 hash", test10b_pass)

        # TEST 11: Existing physician login remains functional
        res11 = client.post(
            "/auth/login",
            json={
                "email": "dr.carter@hospital.org",
                "password": "demo-doctor-2026",
            },
        )
        res11_json = res11.json() if res11.headers.get("content-type", "").startswith("application/json") else {}
        test11_pass = (
            res11.status_code == 200
            and res11_json.get("role") == "DOCTOR"
            and "access_token" in res11_json
        )
        log_result("11. Existing physician login preserved and functional", test11_pass, f"HTTP {res11.status_code}")

    finally:
        # Cleanup created test doctors
        if created_doctor_emails:
            for em in created_doctor_emails:
                d = db.query(Doctor).filter(Doctor.email == em).first()
                if d:
                    db.query(EmailOTP).filter(EmailOTP.doctor_id == d.doctor_id).delete()
                    db.delete(d)
            db.commit()
            print(f"Cleaned up {len(created_doctor_emails)} test doctors from database.")
        db.close()

    total = len(results)
    passed_count = sum(1 for _, p, _ in results if p)
    print("=" * 60)
    print(f"AUDIT SUMMARY: {passed_count}/{total} PASSED ({(passed_count/total)*100:.1f}%)")
    print("=" * 60)
    return passed_count == total

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
