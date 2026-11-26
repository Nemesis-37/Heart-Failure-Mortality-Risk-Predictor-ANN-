# Phase 12 — Frontend UI / UX & Clinical Portal Audit Report

**Project:** Heart Failure Mortality Risk Predictor (CardioPredict Clinical Portal)  
**Audit Phase:** Phase 12 — Comprehensive Quality Assurance & Production Readiness  
**Date:** November 26, 2026  
**Auditor:** Automated Clinical Quality Assurance Suite  
**Status:** **PASSED (Production Ready)**  

---

## 1. Executive Summary

This report documents the frontend architecture, visual design system, accessibility compliance, and user experience (UX) workflows for the CardioPredict clinical web application. The frontend is built on **React 19** with **Vite**, featuring an ergonomic clinical dark mode interface, responsive layouts, accessible component architectures, and dynamic telemetry visualizers.

---

## 2. Frontend Architecture & Page Structure

The application is structured into three primary security zones:

### 2.1 Public & Onboarding Portal
- **`LandingPage.jsx` / `UnifiedLogin.jsx`:** Unified clinical authentication entrypoint supporting attending physicians, guest demo access, and hospital administrators.
- **`DoctorRegister.jsx`:** Multi-section medical credential submission portal with real-time field validation, password strength feedback, and optional PDF medical license upload.
- **`DoctorOtpVerification.jsx`:** Two-factor cryptographic email OTP verification portal with discrete 6-box input, clipboard auto-split, and resend cooldown countdowns.

### 2.2 Physician Clinical Decision Support Portal
- **`AppLayout.jsx` & `DoctorDashboard.jsx`:** Practitioner navigation shell with persistent session telemetry, physician badge, and quick access.
- **`PatientAssessmentsPage.jsx`:** Dual-engine clinical assessment interface allowing practitioners to input 11 physiological parameters with instant risk stratification.
- **`PredictionHistoryPage.jsx` & `assessmentStore.js`:** Historical longitudinal patient tracking with search, sorting, and tabular review.
- **`ModelPerformancePage.jsx`:** Transparent clinical AI explainability dashboard displaying model calibration curves, ROC-AUC comparisons, and feature importance.
- **`HeartHealthCounsellingPage.jsx`:** Automated patient lifestyle and dietary counselling generator with downloadable clinical PDF summaries (`generateCounsellingPdf.js`).

### 2.3 Hospital Administration Portal
- **`AdminDashboard.jsx` & `AdminDoctorVerification.jsx`:** Executive management console displaying platform metrics, registered doctor rosters, and the pending approval queue.
- **Credential Verification Modal:** Allows hospital administrators to audit submitted medical council registration numbers, university qualifications, and uploaded license documents before granting system access.

---

## 3. Dark Mode & Visual Design System

Per clinical user feedback in Phase 11.2, all authentication, registration, and clinical assessment screens adhere strictly to an ergonomic dark healthcare theme:

- **Background Base:** Deep clinical obsidian (`#070b14` / `#0a0e1a`) minimizing eye fatigue during nocturnal shifts.
- **Surface Cards:** Slate gradient containers (`#0f172a` with subtle cyan borders `rgba(56, 189, 248, 0.15)`).
- **Interactive Accents:** Medical cyan (`#38BDF8`) and electric cobalt (`#2563EB`) providing high-visibility focal points.
- **Risk Stratification Palette:**
  - **Low Risk:** Emerald Green (`#10B981` / `rgba(16, 185, 129, 0.15)`)
  - **Moderate Risk:** Clinical Amber (`#F59E0B` / `rgba(245, 158, 11, 0.15)`)
  - **High Risk:** Urgent Crimson (`#EF4444` / `rgba(239, 68, 68, 0.15)`)

Light-mode toggle distractions have been removed from the authentication and registration surfaces to ensure visual continuity.

---

## 4. OTP Verification & Animation UX Audit

The OTP verification interface (`DoctorOtpVerification.jsx`) underwent significant refinement:

1. **Discrete 6-Digit Inputs:** Individual input elements with keyboard event handlers (`onKeyDown`, `onPaste`) that automatically advance cursor focus forward and backward on Backspace.
2. **Medical AI Waiting Visualizer (`OtpWaitingVisualizer.jsx`):**
   - **Simulated Cardiac Telemetry:** Real-time micro-fluctuating telemetry indicator displaying realistic resting heart rates ($69 \text{--} 75\text{ BPM}$) with a rhythmic green pulsing dot.
   - **Rotating Clinical Quotes:** Informative and humorous medical quotes rotating every 4.5 seconds with smooth CSS cross-fades while the physician awaits email delivery.
3. **Resend Cooldown:** Clear countdown timer (60s in production, 5s in dev) preventing accidental API flooding.

---

## 5. Error Handling & Accessibility (a11y)

- **Sanitized API Diagnostics:** Uses `frontend/src/utils/apiErrorHelper.js` to parse both Pydantic validation arrays (`loc`, `msg`) and HTTP error details (`detail`), rendering actionable, human-readable notifications in the `auth-alert-error` banner.
- **Screen Reader Compatibility:** All form fields include associated `<label>` elements or explicit `aria-label` attributes.
- **Reduced Motion Support:** Respects `prefers-reduced-motion` media queries across keyframe animations.
- **Responsive Viewports:** Tested and fluid across 375px (mobile), 768px (tablet), 1280px (standard monitor), and 1920px (clinical workstation).

---

## 6. Audit Conclusion

The Frontend UI/UX layer is **fully validated, production-ready, accessible, and aligned with clinical usability specifications**.
