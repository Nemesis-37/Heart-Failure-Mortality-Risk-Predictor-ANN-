# Heart Failure Mortality Risk Predictor — Live Project Demonstration Guide

**Project:** Heart Failure Mortality Risk Predictor  
**Target Duration:** 5 to 8 Minutes  
**Target Audience:** Academic Evaluators, Machine Learning Engineers, and Clinical Informaticists  
**Date:** November 2026

---

## 1. Demonstration Objective & Narrative Arc

The goal of this live demonstration is to showcase a production-grade, educational clinical decision-support system while transparently articulating the scientific realities of deep learning on small tabular datasets:

1. **The Clinical Challenge:** Heart failure mortality risk stratification using non-invasive admission variables.
2. **The Scientific Finding:** Classical Logistic Regression (12 parameters, AUROC 77.17%) matches or outperforms a deep neural network (2,881 parameters, AUROC 76.22%), debunking the myth that deep learning is inherently superior on small tabular data.
3. **The Software Architecture:** A secure, resilient full-stack deployment featuring FastAPI, React, Argon2id authentication, IDOR protection, and automatic database fallback.

---

## 2. Pre-Demonstration Verification Checklist

Run these quick checks prior to the demonstration:

- [ ] **Backend Service:** Active on `http://localhost:8000` (or Render live URL).
- [ ] **Frontend Application:** Running on `http://localhost:5173` (or via FastAPI `/`).
- [ ] **Health Endpoint:** Verify `curl -s http://localhost:8000/health` returns `{"status":"healthy","logistic_regression_loaded":true,"ann_loaded":true}`.
- [ ] **Database Diagnostics:** Verify `curl -s http://localhost:8000/db-health` returns `{"status":"connected"}`.
- [ ] **Demo Doctor Account:** Email `dr.carter@hospital.org` / Password `demo-doctor-2026`.
- [ ] **Admin Account:** Email `debashish.g333@gmail.com` / Password `admin_debashish123`.

---

## 3. Step-by-Step 5–8 Minute Demonstration Script

### Act 1: Introduction & Clinical Safety (Minute 0:00 – 1:30)
- **Action:** Open application homepage in web browser.
- **Narrative:**  
  *"Welcome. This is the Heart Failure Mortality Risk Predictor, an educational and clinical research prototype. Heart failure is a leading cause of hospital admissions worldwide. Notice immediately the prominent medical safety banner: this system is designed solely for academic and investigational research and must never replace qualified clinical judgement."*
- **Action:** Click "Physician Portal" -> "Quick Demo Login" (or enter `dr.carter@hospital.org` / `demo-doctor-2026`).
- **Narrative:**  
  *"Access is governed by defense-in-depth: Argon2id password hashing, JWT session authorization, and rate limiting against brute-force attacks."*

---

### Act 2: Clinical Assessment & Dual-Model Comparison (Minute 1:30 – 4:00)
- **Action:** Navigate to the "New Patient Assessment" form.
- **Scenario A: Lower-Risk Patient**
  - **Inputs:** Age = `48`, Ejection Fraction = `55%`, Serum Creatinine = `0.8 mg/dL`, Serum Sodium = `141 mEq/L`, CPK = `120`, Platelets = `280,000`, Sex = `Male`, Binary flags = `0`.
  - **Select Model:** `Logistic Regression` -> Click "Calculate Mortality Risk".
  - **Show Result:** Probability ~ `11.8%`, Green "Low Risk" badge.
  - **Narrative:**  
    *"In a patient with preserved left ventricular function and healthy renal clearance, the model appropriately calculates a low 30-day mortality risk."*
- **Scenario B: High-Risk Patient & Dual-Model Comparison**
  - **Inputs:** Age = `76`, Ejection Fraction = `18%`, Serum Creatinine = `3.6 mg/dL`, Serum Sodium = `129 mEq/L`, CPK = `650`, Anaemia = `1`, High Blood Pressure = `1`.
  - **Select Model:** `Logistic Regression` -> Calculate -> Result: Probability ~ `79.4%` (High Risk).
  - **Switch Model:** Toggle to `Artificial Neural Network (PyTorch)` -> Calculate.
  - **Show Result:** Probability ~ `83.1%` (High Risk).
  - **Narrative:**  
    *"Here, both models clearly agree: severe systolic dysfunction (EF 18%) coupled with advanced cardiorenal syndrome (creatinine 3.6) produces high mortality risk. Notice the dual-model toggle: physicians can compare predictions from the interpretable linear baseline against the deep feedforward neural network."*

---

### Act 3: Scientific Audit & Tabular Learning Insights (Minute 4:00 – 6:00)
- **Action:** Open the "Model Insights & Research" tab.
- **Narrative:**  
  *"Our eight research phases yielded a profound scientific insight: on this 299-patient tabular dataset, the 2,881-parameter deep neural network did not outperform the 12-parameter Logistic Regression model (LR AUROC 77.17% vs ANN 76.22%, Wilcoxon p = 0.6250). In small tabular biological data, linear models with strong regularization are robust, whereas deep networks face high parameter variance without dense spatial or sequential priors."*
- **Feature Importance:** Point to ejection fraction and serum creatinine as dominating the decision boundary.

---

### Act 4: Data Persistence & Architecture Resilience (Minute 6:00 – 7:30)
- **Action:** Click "Save Patient Assessment".
- **Action:** Navigate to "History" and "Clinical Dashboard".
- **Narrative:**  
  *"The assessment is securely persisted. All database queries enforce strict Insecure Direct Object Reference (IDOR) prevention: Dr. Carter can only view records authored by Dr. Carter. Furthermore, our backend features an automatic zero-downtime database fallback: in production, it binds to Render's managed PostgreSQL; in local development, it falls back smoothly to SQLite with WAL mode."*

---

### Act 5: Conclusion & Q&A Transition (Minute 7:30 – 8:00)
- **Summary:**  
  *"To summarize: we have verified bit-level inference concordance, hardened security with Argon2id and JWT, enforced leak-free validation, and proved that simpler, transparent models often match complex neural networks in medicine. Thank you, and I welcome your questions."*

---

## 4. Emergency Backup Demonstration Plan

If unexpected environment issues occur during the live presentation:

1. **If Backend Server Stops Running:**
   - Execute: `python main.py` in the workspace root.
   - It will start in < 2 seconds on `http://localhost:8000`.
2. **If Frontend Port Conflict Occurs:**
   - Navigate to `http://localhost:8000/` directly; FastAPI serves the compiled React production build (`frontend/dist`) directly from the backend server!
3. **If Database Fails to Connect:**
   - `clinical_local.db` is already initialized and active in the project root. The backend automatically switches to SQLite within 0.5s if PostgreSQL is offline.
4. **Command-Line Proof of Parity:**
   - Run: `python scripts/execute_phase10_tasks.py`. It runs the full 5-patient test suite and prints bit-level concordance directly to terminal in < 4 seconds.
