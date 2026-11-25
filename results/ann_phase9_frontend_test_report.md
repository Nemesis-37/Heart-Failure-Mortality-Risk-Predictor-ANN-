# Phase 9.5 — Frontend Integration Audit Report

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** 9.5 — Frontend Integration Audit  
**Date:** November 2026  
**Technology Stack:** React 18 · Vite · Tailwind CSS · React Router  
**Status:** ✅ Fully Verified — Clinically Calibrated & Communicated Responsibly  

---

## 1. Objective & Scope

This audit inspected the React user interface to verify that:
1. Dual-model architecture options (Logistic Regression and PyTorch ANN) are clearly presented to clinician users.
2. Predictions are accurately displayed as model probabilities rather than diagnostic absolutes.
3. Required disclaimers and educational warnings are prominently displayed across all views.
4. Navigation, patient assessment forms, prediction history, and admin workflows operate seamlessly.

---

## 2. Component & Navigation Inspection

| Page / Component | File Location | Key Capabilities Verified | Status |
|:---|:---|:---|:---:|
| **App Layout** | `frontend/src/layouts/AppLayout.jsx` | Top navigation, theme toggle (Dark/Light mode), sidebar links, responsive collapsible menu. | ✅ Verified |
| **Doctor Dashboard** | `frontend/src/DoctorDashboard.jsx` | 11-feature assessment input form, model selection radio group, live probability display, outcome badge, patient guidance card. | ✅ Verified |
| **Patient Assessments** | `frontend/src/pages/PatientAssessmentsPage.jsx` | CRUD assessment table, search by patient reference, filtering by risk outcome and model, stale prediction warnings. | ✅ Verified |
| **Prediction History** | `frontend/src/pages/PredictionHistoryPage.jsx` | Chronological audit log of all model inferences, sorting, search, model badges (`Logistic Regression` vs `Artificial Neural Network`). | ✅ Verified |
| **Model Performance** | `frontend/src/pages/ModelPerformancePage.jsx` | Benchmark presentation, AUROC, Brier score, ROC curve visualization, clinical calibration metrics. | ✅ Verified |
| **Lifestyle Guidance** | `frontend/src/pages/HeartHealthCounsellingPage.jsx` | Evidence-based lifestyle counselling guide, PDF export utility with exclusion filtering. | ✅ Verified |
| **Admin Doctor Verification**| `frontend/src/AdminDoctorVerification.jsx` | Administrator portal for reviewing pending physician applicants, approving licenses, and auditing registrations. | ✅ Verified |

---

## 3. Dual-Model Architecture Presentation

In `frontend/src/DoctorDashboard.jsx`, the model selector explicitly separates the two architectures:

```html
<!-- Model Selection Radio Cards -->
1. Logistic Regression
   - Label: "Logistic Regression Baseline"
   - Endpoint: "POST /predict"
   - Description: "Linear probabilistic classification model (Canonical Benchmark)"
   
2. Artificial Neural Network
   - Label: "Artificial Neural Network"
   - Endpoint: "POST /predict-ann"
   - Description: "Multi-layer perceptron with dropout regularization"
```

- **Candidate Switching:** Clicking a model dynamically routes the payload to the respective endpoint without altering form inputs.
- **Model Attribution:** Results explicitly display the originating model tag (`result.model`), ensuring the clinician always knows which algorithm generated the score.

---

## 4. Clinical Language & Disclaimer Audit

The frontend was audited against strict medical communication guidelines to ensure no exaggerated or diagnostic claims are made:

| Audit Criterion | Required Clinical Standard | Observed UI Implementation | Compliance |
|:---|:---|:---|:---:|
| **Output Labeling** | Avoid "definitive mortality" | Uses *"Predicted Classification: Death event predicted"* or *"No death event predicted"*. | ✅ COMPLIANT |
| **Probability Display** | Model score, not certainty | Labeled *"Predicted Event Probability (0.00–1.00): Calculated risk score from input biomarkers"*. | ✅ COMPLIANT |
| **Prototype Disclaimer** | Visible educational notice | Clean disclaimer box: *"Educational ML Prototype: This software is a machine-learning research prototype and is not certified for clinical diagnosis, therapeutic decisions, or medical management."* | ✅ COMPLIANT |
| **Global Footer Notice**| Permanent persistent warning | Footer reads: *"Heart Failure Mortality Risk Predictor • Educational Machine Learning Prototype • Not for clinical diagnosis or medical decision-making"*. | ✅ COMPLIANT |
| **Patient Reference** | Mandatory clinical ID | Form marks `Patient Reference ID *` with tooltip *"Mandatory reference identifier for clinical audit"*. | ✅ COMPLIANT |

---

## 5. Responsive Design & Error Handling

- **Form Validation:** Client-side form validation prevents submission if any of the 11 continuous/binary fields are missing or out of valid clinical bounds.
- **Error State Handling:** In case of backend disconnection or HTTP errors, the UI transitions to an inline error state with a clear descriptive message and a `"Retry Prediction"` button.
- **Responsive Layout:** Grid layout cleanly stacks on tablets and mobile screens (`@media (max-width: 768px)`), keeping form inputs and result cards accessible.

---

## 6. Frontend Audit Conclusion
The frontend application accurately communicates model capabilities, clearly differentiates between the two deployed algorithms, provides transparent probability and risk classification outputs, and enforces comprehensive educational disclaimers.
