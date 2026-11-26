# Phase 13 — External Unseen Data Validation Report

**Project:** Heart Failure Mortality Risk Predictor — CardioPredict Clinical Portal  
**Phase:** Phase 13 — Phase 12 External Unseen Data Validation  
**Status:** **`BLOCKED / NOT AVAILABLE`** (Zero Independent Compatible Cohort Accessible Without Restricted DUA)  
**Date:** November 26, 2026  

---

## 1. Executive Summary

A strict search and repository audit was conducted to determine whether an independent external heart failure mortality cohort with compatible biomarkers and endpoint definitions is available for zero-shot external testing.

**Result:** **External validation is `BLOCKED / NOT AVAILABLE`.**  
No independent, non-duplicate, open-access heart failure mortality dataset containing the required 11 baseline features (`age`, `anaemia`, `creatinine_phosphokinase`, `diabetes`, `ejection_fraction`, `high_blood_pressure`, `platelets`, `serum_creatinine`, `serum_sodium`, `sex`, `smoking`) and `DEATH_EVENT` mortality outcome exists in the repository or in uncredentialed public distribution.

Per strict Phase 13 research rules:
- We **do not** fabricate external validation.
- We **do not** evaluate against Kaggle/UCI mirrors or SMOTE expansions of the same 299-patient Faisalabad dataset (that is circular duplicate leakage).
- We **do not** substitute synthetic records or incompatible Coronary Artery Disease (CAD) stenosis datasets (e.g., Fedesoriano `N=918`, `HeartDisease` target) as external validation.

---

## 2. Candidate Cohort Compatibility & Access Audit

| Cohort / Dataset | Sample Size | Clinical Target | Missing Mandatory Features (Out of 11) | Access / Provenance Status | Phase 13 Verdict |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **UCI / Kaggle Faisalabad Dataset** (`heart_failure_clinical_records_dataset.csv`) | 299 | All-cause HF mortality (`DEATH_EVENT`) | 0 (Source cohort) | Open in `dataset/` | **Internal Source Only** (Used for 5-Fold & 5×10 CV) |
| **Kaggle / GitHub SMOTE / Mirrors** of Heart Failure Clinical Records | 299–5,000 | `DEATH_EVENT` (cloned/oversampled) | 0 | Open online mirrors | **REJECTED** — Exact duplicate / synthetic leakage of source 299 patients |
| **Fedesoriano Heart Failure Prediction** (Cleveland/Hungarian/Long Beach/Zurich/Statlog) | 918 / 1,190 | **CAD Angiographic Stenosis** (`HeartDisease`), **NOT HF Mortality** | **7 missing:** `ejection_fraction`, `serum_creatinine`, `serum_sodium`, `platelets`, `creatinine_phosphokinase`, `anaemia`, `smoking` | Open on Kaggle | **REJECTED** — Incompatible clinical target & missing primary predictors |
| **PhysioNet Zigong Fourth People's Hospital HF EHR** (Zhang et al., 2021) | 2,008 | In-hospital, 28-day, 90-day, post-discharge mortality | **0 missing** (requires unit conversion: creatinine $\mu\text{mol/L} \to \text{mg/dL}$) | **Restricted Credentialed Access** (CITI training + signed DUA required) | **`BLOCKED`** — Clinically ideal cohort, inaccessible without manual DUA |
| **Vanderbilt SUPPORT / SUPPORT2** | 9,105 (3,927 CHF) | In-hospital, 2-mo, 6-mo survival | **4 missing:** `ejection_fraction` (LVEF), `creatinine_phosphokinase`, `platelets`, `smoking` | Open via Vanderbilt Biostat | **REJECTED** — Lacks LVEF & CPK |
| **MIMIC-IV Clinical Demo** | 100 | ICU mortality | LVEF locked in unshared free-text echo notes; CPK rarely ordered | Open Demo (truncated) | **REJECTED** — Insufficient HF records & missing LVEF |
| **NHLBI BioLINCC Trials** (DIG `N=6,800`, TOPCAT `N=3,445`, SOLVD `N=6,797`) | 3,445–6,800 | All-cause mortality | DIG lacks `creatinine_phosphokinase`, `platelets`, `smoking` | **Restricted IRB + DUA** (4–8 week review) | **`BLOCKED`** — Requires formal institutional IRB/BioLINCC agreement |

---

## 3. Clear Distinction Between Validation Regimes

To prevent misinterpretation in clinical or academic reporting, all Phase 13 evaluations are categorized under four non-interchangeable tiers:

1. **Cross-Validation (`5-Fold` & `5x10 Repeated CV`):** Executed in Phase 13 on the 299-patient Faisalabad dataset using strict out-of-fold isolation (`N = 299` OOF patients, 50 repeated splits). Measures *internal* generalization within the Faisalabad hospital distribution.
2. **Held-Out Internal Testing:** Single-split or Fold-4 validation (`N = 60`). High variance on small cohorts ($N=60$ has $\sim 19$ events) and compromised in `models/ann_model.pth` by outer validation early-stopping selection.
3. **Synthetic Scenario Testing:** Executed in Phases 5, 6, and 7 (feature perturbations across 5 clinical profiles and 2D interaction grids). Measures *model functional smoothness, monotonicity, and failure modes*, **not** clinical accuracy or mortality prevalence.
4. **External Validation (`BLOCKED`):** Evaluation of frozen models on a genuinely independent external clinical cohort (different hospital, geography, or time period). **Has not been performed yet.**

---

## 4. Concrete Roadmap Required to Unblock External Validation

1. Obtain PhysioNet researcher credentialing (CITI *Data or Specimens Only Research* certificate) and execute the Data Use Agreement for **Zigong Fourth People's Hospital Heart Failure Database (`N = 2,008`)**.
2. Apply standardized laboratory unit harmonization (`serum_creatinine`: $\mu\text{mol/L} \div 88.42 = \text{mg/dL}$; verify platelet unit scale in $10^3/\mu\text{L}$ vs cells/$\mu\text{L}$).
3. Evaluate the **single frozen selected model** (`Logistic Regression` pipeline trained on the 299 Faisalabad cohort) zero-shot without retraining, reporting AUROC, PR-AUC, Brier Score, Calibration Slope, and Decision Curve net benefit across the 2,008 external patients.
