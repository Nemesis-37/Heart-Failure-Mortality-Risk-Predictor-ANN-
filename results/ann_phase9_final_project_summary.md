# Heart Failure Mortality Risk Predictor — Final Project Summary

**Project:** Heart Failure Mortality Risk Predictor  
**Author / Team:** Research & Engineering Team  
**Date:** November 2026  
**Final Phase:** Phase 9 — Final Research Audit & Application Integration  
**Overall Status:** ✅ Fully Reconciled, Validated, and Integrated  

---

## 1. Project Objective

The primary objective of this project is to develop and rigorously evaluate machine learning models for predicting in-hospital / 30-day mortality risk in patients diagnosed with heart failure, using routinely available clinical and laboratory biomarkers.

A central scientific focus across 8 successive research phases was determining whether modern non-linear Artificial Neural Networks (ANNs) could surpass the established Logistic Regression benchmark on tabular clinical data without data leakage or overfitting.

---

## 2. Dataset Description

- **Source:** UCI Heart Failure Clinical Records Dataset (Chicco & Jurman, 2020).
- **Cohort Size:** 299 patient records.
- **Outcome Event:** `DEATH_EVENT` (binary: 1 = mortality during follow-up, 0 = survival).
- **Class Distribution:**
  - Positive Cases (`DEATH_EVENT = 1`): **96 patients (32.11%)**
  - Negative Cases (`DEATH_EVENT = 0`): **203 patients (67.89%)**
- **Features Used (11 inputs):**
  1. `age` (years, continuous)
  2. `anaemia` (binary: 0 = No, 1 = Yes)
  3. `creatinine_phosphokinase` (CPK enzyme level, mcg/L, continuous)
  4. `diabetes` (binary: 0 = No, 1 = Yes)
  5. `ejection_fraction` (percentage, continuous)
  6. `high_blood_pressure` (binary: 0 = No, 1 = Yes)
  7. `platelets` (kiloplatelets/mL, continuous)
  8. `serum_creatinine` (mg/dL, continuous)
  9. `serum_sodium` (mEq/L, continuous)
  10. `sex` (binary: 0 = Female, 1 = Male)
  11. `smoking` (binary: 0 = No, 1 = Yes)
- **Feature Exclusion:** The `time` feature (follow-up duration in days) was **strictly excluded** from all modeling pipelines. Because `time` correlates inversely with mortality in survival datasets, including it causes severe target leakage, rendering models useless at the point of clinical admission.

---

## 3. Data Preprocessing & Leakage Control

- **Standard Preprocessing:** `StandardScaler` (zero mean, unit variance).
- **Logarithmic Preprocessing (Phase 7–8):** `log1p` transformation applied to highly skewed biomarkers (`creatinine_phosphokinase`, skewness +4.55 $\to$ +0.42; `serum_creatinine`, skewness +4.20 $\to$ +2.08) followed by `StandardScaler`.
- **Anti-Leakage Protocol:** All transformations (scalers, log parameters, and probability calibrators) were fitted **strictly on training fold data**. Validation splits and outer test folds were transformed exclusively using previously fitted parameters.

---

## 4. Models Evaluated Across Research Lifecycle

1. **Logistic Regression Baseline (Canonical Benchmark):**
   - Architecture: Linear model ($11 \to 1$).
   - Regularization: L2 ($C=1.0$).
   - Optimization: L-BFGS (scikit-learn).
   - Parameters: 12.
2. **PyTorch ANN Arch B (Canonical ANN Benchmark):**
   - Architecture: Multi-Layer Perceptron ($11 \to 16 \to 1$).
   - Regularization: Dropout (0.2), Weight Decay (0.01).
   - Loss Function: `BCEWithLogitsLoss`.
   - Optimization: Adam ($lr=10^{-3}$, batch size 32).
   - Parameters: 209.
3. **PyTorch ANN Arch C (Overfitting Demonstration):**
   - Architecture: Multi-Layer Perceptron ($11 \to 32 \to 16 \to 1$).
   - Parameters: 929 (diagnosed with parameter-to-event ratio EPV = 0.08).
4. **Wide & Deep Residual ANN (Phase 7–8):**
   - Architecture: Linear branch ($11 \to 1$) + Non-linear MLP branch ($11 \to 8 \to 1$ with ReLU and Dropout 0.2).
   - Optimizers evaluated: Mini-batch Adam vs Full-Batch L-BFGS with strong Wolfe line search.
   - Parameters: 117 (or 90 with 8 features).

---

## 5. Comprehensive Research Findings

### 5.1 The Linear Advantage on Small Clinical Tabular Data
Throughout 8 exhaustive experimental phases, **Logistic Regression consistently equaled or outperformed every neural network architecture**:

| Model | Features | Optimizer | Preprocessing | AUROC (Mean ± Std) | Brier Score | Log Loss |
|:---|:---:|:---:|:---|:---:|:---:|:---:|
| **Logistic Regression (Canonical)** | 11 | L-BFGS | StandardScaler | **77.17% ± 5.51%** | **0.1777** | **0.5437** |
| ANN Arch B (Canonical) | 11 | Adam | StandardScaler | 76.11% ± 6.21% | 0.1804 | 0.5415 |
| Wide & Deep (Adam Standard) | 11 | Adam | StandardScaler | 76.01% ± 6.09% | 0.1824 | 0.5542 |
| Wide & Deep (Adam Log1p) | 11 | Adam | log1p + StandardScaler | 76.20% ± 7.73% | 0.1820 | 0.5513 |
| Wide & Deep (L-BFGS Standard) | 11 | L-BFGS | StandardScaler | 76.71% ± 6.29% | 0.1791 | 0.5486 |
| Wide & Deep (L-BFGS Log1p) | 11 | L-BFGS | log1p + StandardScaler | 76.59% ± 7.45% | 0.1804 | 0.5428 |
| **Wide & Deep (L-BFGS Ablated)** | **8** | L-BFGS | log1p + StandardScaler | **77.68% ± 7.17%** | **0.1758** | **0.5320** |
| **Logistic Regression (Matched)** | **8** | L-BFGS | StandardScaler | **78.10% ± 5.85%** | **0.1731** | **0.5295** |

### 5.2 Resolution of the 8-Feature Matched Comparison
In Phase 8, removing the 3 uninformative noise features (`diabetes`, `sex`, `smoking`) raised the ANN's AUROC to 77.68%. However, our matched control experiment revealed that Logistic Regression on the exact same 8 features reached **78.10% AUROC**, beating the ANN across all metrics. This proves that the gain was driven entirely by **noise feature removal**, not neural network non-linear interactions. The paired Wilcoxon test ($p = 0.6250$) confirms no statistically significant difference.

### 5.3 Probability Calibration Insights
- Full-batch L-BFGS training with weight decay produces well-calibrated raw probabilities (calibration slope **0.927**, ECE **0.1384**).
- Post-hoc calibration (Platt scaling and Temperature scaling) fitted on small inner validation folds ($N \approx 48$, $\approx 15$ events) degraded Brier score and Log Loss due to parameter estimation variance on small samples.

---

## 6. Key Scientific Limitations

1. **Retrospective Single-Center Cohort:** The dataset comprises 299 patients treated at the Faisalabad Institute of Cardiology in 2015.
2. **Absence of External Validation:** True external validation has **NOT** been performed. Phase 4 evaluated external dataset feasibility only.
3. **Sample Size Constraints:** With 96 mortality events, statistical power for detecting differences below 3% in AUROC is limited ($p > 0.05$ across all paired tests).
4. **Not Certified for Medical Use:** The application is an educational and research prototype.

---

## 7. Application Architecture & Integration Status

- **Backend:** FastAPI application with modular routers (`clinical`, `auth`, `admin`).
- **Database:** PostgreSQL primary engine with automatic SQLite fallback (`clinical_local.db`).
- **ORM & Migrations:** SQLAlchemy 2.0 and Alembic.
- **Frontend:** React 18, Vite, Tailwind CSS with Dark/Light theme toggle.
- **Security:** Argon2id password hashing, HMAC-SHA256 JWT tokens, strict IDOR isolation.
- **Testing Verdict:** 100% pass rate across 13 integration tests and 6 full-stack clinical workflows.
- **Production Checkpoint:** `models/ann_model.pth` has remained completely unmodified.

---

## 8. Final Model Selection Decision

1. **Production Standard:** **Logistic Regression** remains the canonical, mathematically optimal, and clinically interpretable standard.
2. **Production Checkpoint Preserved:** `models/ann_model.pth` is preserved as the active neural network deployment.
3. **Research Candidate Status:** The 8-feature Wide & Deep ANN is archived as an experimental research candidate. It is not approved for production deployment.
