# Phase 10 — Prediction API Inference Test Report

**Date:** 2026-11-25 14:29:27 UTC  
**Evaluation:** Direct Python vs FastAPI Endpoint Verification (Tasks A.3 & A.4)

---

## 1. Executive Summary

A comprehensive inference concordance audit was conducted across 5 patient profiles, comparing standalone Python execution (scikit-learn and PyTorch) against the live FastAPI test client endpoints (`/predict` and `/predict-ann`).

- **Total Test Cases:** 5 profiles (4 clinically varied valid inputs + 1 out-of-boundary invalid input).
- **Direct Python vs FastAPI Discrepancy:** **0.000000** across all valid cases.
- **Validation Boundary Enforcement:** 100% rejection rate for out-of-boundary payloads via HTTP 422 Unprocessable Entity.
- **Verification Verdict:** **PASSED (Absolute inference parity confirmed)**.

---

## 2. Quantitative Consistency Matrix

| Case ID | Patient Ref | LR Py Prob | LR API Prob | LR Diff | ANN Py Prob | ANN API Prob | ANN Diff | Verdict |
|---|---|---|---|---|---|---|---|---|
| CASE-1 | PT-2026-001 | 0.3007 | 0.3007 | 0.0000 | 0.1923 | 0.1923 | 0.0000 | **PASSED** |
| CASE-2 | PT-2026-002 | 0.0104 | 0.0104 | 0.0000 | 0.0097 | 0.0097 | 0.0000 | **PASSED** |
| CASE-3 | PT-2026-003 | 0.9760 | 0.9760 | 0.0000 | 0.9489 | 0.9489 | 0.0000 | **PASSED** |
| CASE-4 | PT-2026-004 | 0.9819 | 0.9819 | 0.0000 | 0.9387 | 0.9387 | 0.0000 | **PASSED** |
| CASE-5 | PT-2026-005 | — | HTTP 422 | — | — | HTTP 422 | — | **REJECTED** |

---

## 3. Detailed Case-by-Case Analysis

### CASE-1: Typical intermediate-risk patient (PT-2026-001)
- **Patient Reference ID:** `PT-2026-001`
- **Clinical Profile:** Age 65.0, EF 35.0%, Creatinine 1.3 mg/dL, Sodium 137.0 mEq/L
- **Logistic Regression Inference:**
  - Direct Python: Probability = `0.3007`, Class = `0`
  - FastAPI Endpoint (`/predict`): Probability = `0.3007`, Class = `0` (Status: 200 OK)
  - Absolute Difference: `0.000000` (Exact match: True)
- **ANN Inference:**
  - Direct Python: Probability = `0.1923`, Class = `0`
  - FastAPI Endpoint (`/predict-ann`): Probability = `0.1923`, Class = `0` (Status: 200 OK)
  - Absolute Difference: `0.000000` (Exact match: True)
- **Consistency Verification:** **PASSED (Bit-level concordant)**
### CASE-2: Lower-risk patient (PT-2026-002: young, preserved EF, normal creatinine)
- **Patient Reference ID:** `PT-2026-002`
- **Clinical Profile:** Age 45.0, EF 60.0%, Creatinine 0.8 mg/dL, Sodium 140.0 mEq/L
- **Logistic Regression Inference:**
  - Direct Python: Probability = `0.0104`, Class = `0`
  - FastAPI Endpoint (`/predict`): Probability = `0.0104`, Class = `0` (Status: 200 OK)
  - Absolute Difference: `0.000000` (Exact match: True)
- **ANN Inference:**
  - Direct Python: Probability = `0.0097`, Class = `0`
  - FastAPI Endpoint (`/predict-ann`): Probability = `0.0097`, Class = `0` (Status: 200 OK)
  - Absolute Difference: `0.000000` (Exact match: True)
- **Consistency Verification:** **PASSED (Bit-level concordant)**
### CASE-3: Higher-risk patient (PT-2026-003: elderly, severely reduced EF, renal dysfunction)
- **Patient Reference ID:** `PT-2026-003`
- **Clinical Profile:** Age 75.0, EF 20.0%, Creatinine 3.5 mg/dL, Sodium 130.0 mEq/L
- **Logistic Regression Inference:**
  - Direct Python: Probability = `0.9760`, Class = `1`
  - FastAPI Endpoint (`/predict`): Probability = `0.9760`, Class = `1` (Status: 200 OK)
  - Absolute Difference: `0.000000` (Exact match: True)
- **ANN Inference:**
  - Direct Python: Probability = `0.9489`, Class = `1`
  - FastAPI Endpoint (`/predict-ann`): Probability = `0.9489`, Class = `1` (Status: 200 OK)
  - Absolute Difference: `0.000000` (Exact match: True)
- **Consistency Verification:** **PASSED (Bit-level concordant)**
### CASE-4: Boundary valid patient (PT-2026-004: extreme valid physiological limits)
- **Patient Reference ID:** `PT-2026-004`
- **Clinical Profile:** Age 80.0, EF 15.0%, Creatinine 5.0 mg/dL, Sodium 125.0 mEq/L
- **Logistic Regression Inference:**
  - Direct Python: Probability = `0.9819`, Class = `1`
  - FastAPI Endpoint (`/predict`): Probability = `0.9819`, Class = `1` (Status: 200 OK)
  - Absolute Difference: `0.000000` (Exact match: True)
- **ANN Inference:**
  - Direct Python: Probability = `0.9387`, Class = `1`
  - FastAPI Endpoint (`/predict-ann`): Probability = `0.9387`, Class = `1` (Status: 200 OK)
  - Absolute Difference: `0.000000` (Exact match: True)
- **Consistency Verification:** **PASSED (Bit-level concordant)**
### CASE-5: Invalid input case (PT-2026-005: age=-5, ejection_fraction=120)
- **Patient Reference ID:** `PT-2026-005`
- **Invalid Parameters Injected:** `age = -5.0` (must be $\ge 1$), `ejection_fraction = 120.0` (must be $\le 100$)
- **API Response (`/predict`):** HTTP `422` (Detail: Rejected schema violation)
- **API Response (`/predict-ann`):** HTTP `422` (Detail: Rejected schema violation)
- **Consistency Verification:** **PASSED (Correctly rejected by Pydantic validation boundary)**


---

## 4. Key Engineering Conclusions
1. The FastAPI prediction endpoints (`/predict` and `/predict-ann`) faithfully execute the exact saved weights without intermediate corruption or double-scaling.
2. The model outputs are completely deterministic: running the same patient vector yields identical probabilities regardless of call modality.
3. The Pydantic validation boundary guarantees that invalid inputs are arrested before reaching model tensors, protecting runtime stability.
