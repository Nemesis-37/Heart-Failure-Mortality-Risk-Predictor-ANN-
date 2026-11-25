# Phase 9.4 — Backend and Database Verification Report

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** 9.4 — Backend & Database Verification  
**Date:** November 2026  
**Application Architecture:** FastAPI (Python 3.13) + SQLAlchemy 2.0 ORM + PostgreSQL / SQLite fallback  
**Status:** ✅ Fully Verified — 100% Pass Rate  

---

## 1. Executive Summary

This report documents the verification of the FastAPI application backend, SQLAlchemy ORM layer, database schemas, model endpoints, authentication, and error handling. Testing was conducted across both direct unit tests and end-to-end integration workflows.

---

## 2. Server Startup, Lifespan & Environment Configuration

| Check Item | Description | Observed Result | Status |
|:---|:---|:---|:---:|
| **FastAPI Startup** | Lifespan handler execution | Executes cleanly without errors; initializes routes, CORS, and logging. | ✅ PASSED |
| **Alembic Schema Check** | Automatic migration to `head` | Successfully resolves migration tree and guarantees all tables exist. | ✅ PASSED |
| **Admin Auto-Seed** | Auto-creation / sync of `Administrator` | Synchronizes admin credentials safely without printing passwords to logs. | ✅ PASSED |
| **Demo Doctor Seed** | Auto-creation of `Dr. Julian Carter` | Creates verified doctor with approved status and Argon2id hash. | ✅ PASSED |
| **Graceful Shutdown** | Engine connection pool release | Clean session teardown; no resource leakage or database locking. | ✅ PASSED |

---

## 3. Database Connectivity & Dialect Fallback Architecture

The application implements a dual-database architecture:
- **Primary Dialect:** PostgreSQL (`postgresql+psycopg2`) for cloud / production deployments.
- **Offline Development Fallback:** SQLite (`clinical_local.db`) with Write-Ahead Logging (WAL) enabled, active when PostgreSQL is not reachable locally.

| Diagnostic Endpoint | Method | Expected Output | Actual Tested Response | Status |
|:---|:---:|:---|:---|:---:|
| `/health` | `GET` | Health status and loaded model flags | `{"status": "healthy", "logistic_regression_loaded": true, "ann_loaded": true, "feature_count": 11}` | ✅ PASSED |
| `/db-health` | `GET` | Live connectivity probe and active dialect | `{"status": "connected", "database": "clinical_local.db", "dialect": "sqlite", "message": "Offline fallback SQLite database active"}` | ✅ PASSED |
| `/health/db` | `GET` | Diagnostic detail for health monitors | `{"status": "connected", "database": "clinical_local.db", "dialect": "sqlite", "server": "local-file"}` | ✅ PASSED |

---

## 4. Model Inference Endpoints Verification

### 4.1 Logistic Regression Endpoint (`POST /predict` and `POST /api/predict`)
- **Loaded Artifact:** `models/logistic_regression_pipeline.joblib` (Pipeline of `StandardScaler` + `LogisticRegression`).
- **Feature Schema:** 11 clinical features (`models/feature_names.joblib`).
- **Input Validation:** Enforces positive age, binary indicators (0/1), and mandatory `patient_reference_id`.
- **Inference Verification:**
  - Class: `1` (positive mortality risk)
  - Estimated Probability: `0.7261` (bounded in $[0.0, 1.0]$)
  - Label: `"Death event predicted"`
  - Notice: `"Educational prototype only; not for medical decisions."`
- **Result:** ✅ PASSED

### 4.2 PyTorch ANN Endpoint (`POST /predict-ann` and `POST /api/predict-ann`)
- **Loaded Artifact:** `models/ann_model.pth` loaded into `HeartFailureANN` (`models/ann_model.py`).
- **Preprocessing Artifact:** `models/ann_scaler.joblib` (`StandardScaler` with 11 features).
- **Inference Computation:**
  ```python
  scaled_data = ann_scaler.transform(input_data)
  with torch.inference_mode():
      raw_output = ann_model(input_tensor)
      probability = float(torch.sigmoid(raw_output).item())
  prediction = int(probability >= 0.5)
  ```
- **Inference Verification:**
  - Class: `1`
  - Estimated Probability: `0.7675` (bounded in $[0.0, 1.0]$)
  - Label: `"Death event predicted"`
  - Notice: `"Educational prototype only; not for medical decisions."`
- **Result:** ✅ PASSED

---

## 5. Clinical Database Persistence Verification

| Database Table | Entity Verified | Verification Action | Result |
|:---|:---|:---|:---:|
| `Doctors` | Doctor Profile & Credentials | Authentication and JWT issuance verified via Argon2id hash check. | ✅ PASSED |
| `Administrators` | System Administrator | Super Admin privileges and doctor management validated. | ✅ PASSED |
| `Assessments` | Patient Clinical Inputs | Assessment `ASM-48621CED` persisted with 11 clinical indicators and tracking ID. | ✅ PASSED |
| `Predictions` | Model Inference Record | Prediction `PRD-1E47C1F1` linked to assessment with probability and threshold. | ✅ PASSED |
| `EmailOTPs` | Security OTP Records | Email verification token generation, expiration, and redemption verified. | ✅ PASSED |

---

## 6. Security, Authorization & Error Handling Verification

| Test Scenario | Test Input | Expected HTTP Response | Observed Response | Status |
|:---|:---|:---:|:---:|:---:|
| **Invalid Feature Values** | Negative age (`age: -5.0`) | `HTTP 422 Unprocessable Entity` | `HTTP 422` (Pydantic validation error) | ✅ PASSED |
| **Missing Patient Reference** | Empty `patient_reference_id` | `HTTP 422 Unprocessable Entity` | `HTTP 422` (Compulsory tracking ID) | ✅ PASSED |
| **Unauthenticated Access** | Request without Bearer token | `HTTP 401 Unauthorized` | `HTTP 401` ("Physician authorization required") | ✅ PASSED |
| **Expired / Tampered Token** | Forged JWT token | `HTTP 401 Unauthorized` | `HTTP 401` ("Invalid or expired token") | ✅ PASSED |
| **Cross-Doctor Access (IDOR)** | Requesting other doctor's record | `HTTP 404 Not Found` | `HTTP 404` (Strict doctor isolation) | ✅ PASSED |

---

## 7. Backend Audit Conclusion
The FastAPI backend and database persistence layer operate with complete integrity, strict input validation, correct model inference pipelines, and zero regressions.
