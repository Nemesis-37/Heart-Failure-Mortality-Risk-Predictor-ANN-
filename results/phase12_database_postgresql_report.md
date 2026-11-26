# Phase 12 — Database Layer & PostgreSQL Persistence Audit Report

**Project:** Heart Failure Mortality Risk Predictor (CardioPredict Clinical Portal)  
**Execution Date:** November 26, 2026  
**Auditor:** Antigravity Autonomous Engineering Agent  
**Status:** PASS — 100% VERIFIED

---

## 1. Executive Summary

A comprehensive architectural and transaction audit was conducted across the database persistence layer. The application supports dual-mode operation:
- **Production Mode (Render Cloud):** Managed PostgreSQL via `psycopg2-binary`, scoped under the `clinical` schema. Silent SQLite fallback is strictly forbidden and raises a fatal `RuntimeError` if PostgreSQL is offline.
- **Development Sandbox Mode:** Automatic local SQLite fallback (`clinical_local.db`) with Write-Ahead Logging (WAL mode) and immediate TCP socket reachability checks to avoid OS-level connection hangs.

---

## 2. Table Schemas, Constraints & Foreign Key Mappings

All 6 core clinical tables were inspected and verified in `database.models`:

### 1. `clinical.Doctors`
* **Primary Key:** `doctor_id` (String UUID)
* **Unique Constraints:** `email`, `registration_number`
* **Columns:** `full_name`, `email`, `password_hash`, `mobile`, `medical_degree`, `registration_number`, `registration_council`, `email_verified`, `verification_status`, `is_active`, `created_at`, `profile_photo_path`, `document_path`.
* **Verification:** Enforces uniqueness across email and license numbers; handles soft updates for unverified candidates.

### 2. `clinical.DoctorSessions`
* **Primary Key:** `session_id` (String UUID)
* **Foreign Key:** `doctor_id` $\to$ `clinical.Doctors.doctor_id` (`ON DELETE CASCADE`)
* **Indexes:** `IX_DoctorSessions_DoctorId`, `IX_DoctorSessions_ExpiresAt`
* **Columns:** `refresh_token_hash`, `expires_at`, `is_revoked`, `user_agent`, `ip_address`.
* **Verification:** Session revocation and refresh rotation audit trails.

### 3. `clinical.EmailOTP`
* **Primary Key:** `otp_id` (String UUID)
* **Foreign Key:** `doctor_id` $\to$ `clinical.Doctors.doctor_id` (`ON DELETE CASCADE`)
* **Indexes:** `IX_EmailOTP_DoctorId`, `IX_EmailOTP_ExpiresAt`
* **Columns:** `otp_hash`, `expires_at`, `attempts`, `is_used`, `created_at`.
* **Verification:** Zero plaintext storage; tracks verification attempts.

### 4. `clinical.Administrators`
* **Primary Key:** `admin_id` (String UUID)
* **Unique Constraints:** `username`, `email`
* **Columns:** `username`, `email`, `password_hash`, `full_name`, `role`, `is_active`, `created_at`.
* **Verification:** Seeded administrator accounts for medical credential verification.

### 5. `clinical.Assessments`
* **Primary Key:** `id` (String UUID)
* **Unique Constraints:** `assessment_code` (e.g., `ASM-AUDIT-XXXXXX`)
* **Foreign Key:** `doctor_id` $\to$ `clinical.Doctors.doctor_id` (`ON DELETE SET NULL`)
* **Check Constraints:** Enforces clinical bounds on `age` (1–120), `ejection_fraction` (1–100), `serum_creatinine` (0.1–30.0), `serum_sodium` (50–200), `CPK`, `platelets`, and binary indicators (anaemia, diabetes, sex, smoking, high_blood_pressure).
* **Columns:** 11 clinical biomarkers, `patient_reference_id`, `selected_model`, `predicted_class`, `predicted_probability`, `created_at`, `updated_at`.

### 6. `clinical.Predictions`
* **Primary Key:** `id` (String UUID)
* **Foreign Key:** `assessment_id` $\to$ `clinical.Assessments.id` (`ON DELETE CASCADE`)
* **Columns:** `prediction_code`, `model_name`, `predicted_class`, `predicted_probability`, `classification_threshold`, `model_version`, `created_at`.
* **Verification:** Immutable historical record of every model inference.

---

## 3. Database Persistence & Integrity Tests

| Test ID | Objective | Operation Executed | Verification Result | Status |
|:---|:---|:---|:---|:---|
| **T47** | Metadata Validation | Check mapping of all 6 clinical models | All 6 tables present in SQLAlchemy metadata | **PASS** |
| **T48** | Assessment Persistence | Insert synthetic assessment `ASM-AUDIT-XXXX` | Committed with UUID primary key | **PASS** |
| **T49** | Prediction Persistence | Insert prediction record linked to assessment | Foreign key resolved; committed with UUID | **PASS** |
| **T50** | Foreign Key & Data Integrity | Query back assessment and prediction after session expire | Parameters match committed values ($EF = 28.0$, $Age = 67.0$) | **PASS** |

---

## 4. Production Safeguards & Migration Status

1. **Alembic Version Alignment:** 6 migrations in `alembic/versions/` match the SQLAlchemy model attributes.
2. **Search Path Isolation:** PostgreSQL engine sets `search_path=clinical,public` to isolate portal data from default database tables.
3. **No Silent Fallback in Production:** In `database/config.py`:
   ```python
   if engine is None:
       if is_prod:
           raise RuntimeError("FATAL: Production requires PostgreSQL DATABASE_URL. SQLite/MSSQL are strictly forbidden in production.")
   ```
4. **Data Isolation:** Automated test scripts clean up all test records in `finally:` blocks, preserving production physician data and assessment history.
