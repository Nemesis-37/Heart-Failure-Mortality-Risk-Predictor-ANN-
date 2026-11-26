# Phase 11.2 — Registration Workflow & State Sequence Audit Report

**Project:** Heart Failure Mortality Risk Predictor (CardioPredict Clinical Portal)  
**Audit Phase:** Phase 11.2 — Multi-Stage Practitioner Onboarding Pipeline  
**Date:** November 26, 2026  
**Status:** **FULLY IMPLEMENTED & AUDITED (ALL TRANSITIONS VERIFIED)**

---

## 1. Executive Summary

This report documents the implementation and architectural validation of the multi-stage physician onboarding workflow in CardioPredict.

The core business rule has been strictly implemented:
> **An unverified physician must NOT appear in the Admin Physician Approval / Credential Review dashboard.**

Email ownership confirmation is a strict prerequisite before medical credentials enter the administrative review queue.

---

## 2. Formal State Transition Diagram

```
[1. Practitioner Registration Submitted]
       │
       ▼
[2. Temporary Record Created]
       │  • Doctor.email_verified = False
       │  • Doctor.verification_status = 'PENDING'
       │  • EmailOTP record created (PBKDF2 salted hash)
       │  • Doctor HIDDEN from Admin queue & directory
       ▼
[3. OTP Generation & Dispatch Attempt]
       │  • If SMTP configured -> Email dispatched (status: SENT)
       │  • If SMTP absent -> Real status returned (status: BLOCKED)
       ▼
[4. Practitioner Submits 6-Digit Code]
       │  • POST /auth/verify-otp
       │  • Validated against PBKDF2 hash using hmac.compare_digest
       │  • Enforces 5-minute expiry & max 5 attempts
       ▼
[5. Email Ownership Confirmed]
       │  • Doctor.email_verified = True
       │  • EmailOTP.is_used = True
       ▼
[6. Credential-Review Request Enters Admin Queue]
       │  • Doctor NOW visible in /admin/doctors/pending
       │  • Counted in /admin/overview pending_doctors
       │  • Accessible in /admin/doctors/{id} detail review
       ▼
[7. Administrative Credential Review]
       │  • Hospital Credentialing Officer inspects license & council proof
       │  • Verifies issuing medical council and registration number
       ▼
[8. Final Account Determination]
       ├── [APPROVED] -> verification_status = 'APPROVED', system username assigned,
       │                 login granted to clinical diagnostic models.
       └── [REJECTED] -> verification_status = 'REJECTED', reason recorded,
                         login denied with formal reason notice.
```

---

## 3. Detailed Component Audit

### 3.1 Stage 1: Form Submission (`POST /auth/register`)
- **Inputs:** `full_name`, `email`, `mobile`, `medical_degree`, `registration_number`, `registration_council`, `password`, `confirm_password`, optional `document` (PDF/JPEG/PNG).
- **Validations:**
  - Full name $\ge 3$ characters.
  - Email format regex `^[^@]+@[^@]+\.[^@]+$`.
  - Mobile $\ge 7$ digits.
  - Password complexity (8+ characters, uppercase, lowercase, digit, exact confirmation).
  - Uniqueness checks for both `email` and `registration_number`.
- **Database Transaction:**
  - Password hashed with Argon2id.
  - Document stored in `storage/medical_documents/`.
  - Doctor record inserted with:
    `email_verified = False`, `verification_status = 'PENDING'`, `is_active = True`.
  - Initial 6-digit OTP generated, hashed via PBKDF2 salt, saved to `clinical.EmailOTP`.
  - Response returns `RegisterSuccessResponse` with `email_delivery_status` (`SENT` or `BLOCKED`).

### 3.2 Stage 2: OTP Verification (`POST /auth/verify-otp`)
- **Inputs:** `email`, `otp` (6 digits).
- **Validations:**
  - Looks up doctor by normalized email.
  - If `doctor.email_verified == True`, returns idempotent `{ status: "already_verified" }` without creating duplicate requests or resetting status.
  - Checks if OTP has expired ($> 5$ minutes).
  - Checks attempts ($\ge 5$ attempts invalidates OTP).
  - Compares hash via `verify_otp_hash`.
- **Promotion to Admin Queue:**
  - Upon valid OTP match:
    ```python
    active_otp.is_used = True
    doctor.email_verified = True
    db.commit()
    ```
  - Crucially: `doctor.verification_status` **remains PENDING**. Email verification does NOT bypass administrative review.

### 3.3 Stage 3: Administrative Credential Review (`/admin/*`)
- **Queries Filtered by `email_verified == True`:**
  - `list_doctors`: Filters `Doctor.email_verified == True`.
  - `list_pending_doctors`: Filters `Doctor.email_verified == True, Doctor.verification_status == 'PENDING'`.
  - `get_admin_overview`: Counts only email-verified doctors.
  - `get_recent_activity`: Includes only email-verified registrations.
  - `get_doctor_detail`: Returns 404 Not Found if `not doctor.email_verified`.
  - `approve_doctor` / `reject_doctor`: Rejects review with HTTP 400 if `not doctor.email_verified`.

### 3.4 Stage 4: Login Authentication Enforcement (`POST /auth/login`)
- **Gate 1:** Credentials match (Argon2id password check).
- **Gate 2:** Account active (`doctor.is_active is True`).
- **Gate 3:** Email verified (`doctor.email_verified is True`). If False, raises 403 Forbidden:
  `"Your professional email address has not been verified. Please enter your 6-digit verification code."`
- **Gate 4:** Administrative approval (`doctor.verification_status == 'APPROVED'`). If PENDING, raises 403 Forbidden:
  `"Login denied. Your medical council registration is pending administrative review and approval."`

---

## 4. Architectural Summary

| Security Gate | Enforcing Endpoint / File | Failure Consequence |
| :--- | :--- | :--- |
| **Input Format & Uniqueness** | `auth/validation.py`, `auth/router.py` | HTTP 400 Bad Request with field highlight |
| **Email Verification** | `auth/router.py` (`/verify-otp`) | Doctor invisible to admin; login blocked (HTTP 403) |
| **Admin Approval Gate** | `auth/router.py` (`/login`) | Unapproved doctor blocked from clinical models (HTTP 403) |
| **Credential Review Authority** | `admin/router.py` (`/approve`, `/reject`) | Verified credentialing officer identity audited |
