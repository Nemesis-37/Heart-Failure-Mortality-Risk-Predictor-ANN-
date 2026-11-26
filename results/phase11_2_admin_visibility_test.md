# Phase 11.2 — Admin Visibility & Isolation Test Report

**Project:** Heart Failure Mortality Risk Predictor (CardioPredict Clinical Portal)  
**Audit Phase:** Phase 11.2 — Administrative Credential Review Dashboard Visibility Testing  
**Date:** November 26, 2026  
**Status:** **PASSED (100% ISOLATION CONFIRMED)**

---

## 1. Executive Summary

This report documents the verification tests proving that unverified physician registrations are strictly isolated and invisible in the Hospital Administration Portal until email ownership is confirmed via 6-digit OTP verification.

---

## 2. Test Architecture

The isolation tests evaluate five distinct administrative access vectors against an unverified physician account:
1. `GET /admin/doctors/pending` (Pending credential review queue)
2. `GET /admin/doctors` (General physician directory)
3. `GET /admin/doctors/{doctor_id}` (Direct record detail review)
4. `GET /admin/overview` (Aggregated statistics and pending count)
5. `GET /admin/recent-activity` (Recent registrations timeline)

---

## 3. Test Execution Results

Synthetic doctor created: `dr.audit_ab2936@hospital.org` (`08c504ac-2cee-4a57-aede-ead42d859249`).

### 3.1 Phase A: Pre-OTP State (`email_verified == False`)

| Test Vector | Endpoint Evaluated | Expected Behavior | Observed Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Pending Queue** | `GET /admin/doctors/pending` | Doctor ID absent from array | Doctor ID absent from returned list | **PASS** |
| **Directory Search** | `GET /admin/doctors` | Doctor ID absent from directory | Doctor ID absent from returned list | **PASS** |
| **Direct Detail** | `GET /admin/doctors/{id}` | HTTP 404 Not Found | HTTP 404 Not Found (`detail: "Doctor not found or registration is pending email verification."`) | **PASS** |
| **Overview Metrics** | `GET /admin/overview` | `pending_doctors` count excludes unverified doctor | Count strictly tallies `email_verified == True` | **PASS** |
| **Recent Activity** | `GET /admin/recent-activity` | Doctor ID absent from `recent_registrations` | Excluded from recent registrations | **PASS** |
| **Attempted Approval** | `POST /admin/doctors/{id}/approve` | HTTP 400 Bad Request | HTTP 400 (`"Cannot approve doctor: Email address has not been verified."`) | **PASS** |
| **Attempted Rejection** | `POST /admin/doctors/{id}/reject` | HTTP 400 Bad Request | HTTP 400 (`"Cannot review or reject doctor: Email address has not been verified."`) | **PASS** |

### 3.2 Phase B: Post-OTP Verification State (`email_verified == True`)

Upon submitting the valid 6-digit OTP (`778899`) to `/auth/verify-otp`:

| Test Vector | Endpoint Evaluated | Expected Behavior | Observed Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Pending Queue** | `GET /admin/doctors/pending` | Doctor ID now appears in pending list | Doctor ID successfully returned with status `PENDING` | **PASS** |
| **Directory Search** | `GET /admin/doctors` | Doctor ID now listed in directory | Doctor ID found in search results | **PASS** |
| **Direct Detail** | `GET /admin/doctors/{id}` | HTTP 200 with full clinical profile | HTTP 200 OK; profile returned with `email_verified: true` | **PASS** |
| **Overview Metrics** | `GET /admin/overview` | `pending_doctors` incremented | Count reflects verified pending candidate | **PASS** |
| **Recent Activity** | `GET /admin/recent-activity` | Doctor ID present in recent activity | Visible in `recent_registrations` | **PASS** |
| **Approval Action** | `POST /admin/doctors/{id}/approve` | HTTP 200 with system username assigned | Approved; status updated to `APPROVED`, username generated | **PASS** |

---

## 4. Idempotency & Edge Case Analysis

1. **Repeated OTP Verification:**
   When the user submitted the correct OTP multiple times, `/auth/verify-otp` returned:
   ```json
   {
     "status": "already_verified",
     "message": "Your email address is already verified.",
     "email_verified": true,
     "verification_status": "PENDING"
   }
   ```
   No duplicate database records were created, and the doctor's status remained safely anchored in the administrative queue.
2. **Expired OTP Rejection:**
   Backdated OTP tokens were rejected with HTTP 400 (`"Verification code has expired. Please request a new code."`), leaving the physician in the unverified, hidden state.
3. **Attempt Limit Exhaustion:**
   5 consecutive incorrect OTP submissions automatically invalidated the token, requiring a fresh code dispatch.

---

## 5. Conclusion

The critical business rule is 100% verified and effective in the database and router layers. Unverified registrations never leak into the administrative workflow.
