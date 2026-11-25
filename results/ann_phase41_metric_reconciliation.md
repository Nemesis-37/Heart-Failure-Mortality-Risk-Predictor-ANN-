# Heart Failure Mortality Risk Predictor — Phase 4.1
## Cross-Phase Reproducibility, Metric Reconciliation & Research Audit

**Date:** November 25, 2026  
**Project:** Heart Failure Mortality Risk Predictor  
**Author:** Clinical AI Research Integrity & Forensic Audit Unit  
**Status:** Completed Audit  

---

## 1. Executive Summary & Audit Mandate

This phase performs a strict forensic reproducibility audit across all experimental phases of the Heart Failure Mortality Risk Predictor project:
- **Phase 1**: Training corrections, numerical stabilization (`BCEWithLogitsLoss`), and full outer-fold training refit.
- **Phase 2**: Multi-architecture exploration (Arch A 8, Arch B 16, Arch C 32-16, Arch D 64-32) and regularization tuning (dropout, weight decay, batch size).
- **Phase 3**: Decision-threshold optimization, probability calibration (Platt scaling), and reliability assessment.
- **Phase 4**: External dataset identification, feasibility audit, and clinical biomarker harmonization.

### Audit Objectives:
1. Reconcile all numerical metrics across experimental CSVs, generated artifacts, and narrative markdown reports.
2. Investigate and document the exact root causes of discrepancies between Phase 3 results and Phase 4 narrative tables.
3. Verify strict experimental isolation, outer-test fold integrity, and lack of data leakage.
4. Correct misleading terminology regarding calibration, clinical validation, and distribution-shift claims.
5. Clarify the status of external validation without ambiguity.

---

## 2. Cross-Phase Metric Reconciliation Matrix

The table below reconciles the exact computational metrics recorded in the underlying pipeline CSVs against the values published in historical narrative reports:

| Model & Evaluation Setting | Metric | Phase 1 Artifact | Phase 2 Artifact | Phase 3 Artifact | Phase 4 CSV Artifact | Phase 4 Narrative Report | Verified Ground Truth (Audited) | Discrepancy Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Logistic Regression Baseline** | AUROC Mean | 0.771713 | 0.771713 | 77.17% | 77.17% | 77.1713% | **77.1713%** | Reconciled (Identical) |
| *(Full 5-Fold Outer Refit)* | AUROC Std | 0.055057 | 0.055057 | 5.51% | 5.51% | 5.12% | **5.5057% (5.51%)** | **Typographic Error in P4 Report** (5.12% vs 5.51%) |
| | Brier Score Mean | 0.177731 | 0.177731 | 0.1777 | 0.1777 | 0.1742 | **0.177731 (0.1777)** | **Typographic Error in P4 Report** (0.1742 vs 0.1777) |
| | Brier Score Std | 0.028047 | 0.028047 | 0.0280 | 0.0280 | — | **0.028047 (0.0280)** | Reconciled |
| | Log Loss Mean | — | — | 0.5437 | 0.5437 | 0.5437 | **0.543667 (0.5437)** | Reconciled |
| | Sensitivity (0.50) | 0.481053 | 0.481053 | 48.11% | 48.11% | 48.24% | **48.1053% (48.11%)** | **Rounding Error in P4 Report** (48.24% vs 48.11%) |
| | Specificity (0.50) | 0.886707 | 0.886707 | 88.67% | 88.67% | 85.74% | **88.6707% (88.67%)** | **Typographic Error in P4 Report** (85.74% vs 88.67%) |
| | F1 Score (0.50) | 0.557555 | 0.557555 | 0.5576 | 0.5576 | 0.5412 | **0.557555 (0.5576)** | **Typographic Error in P4 Report** (0.5412 vs 0.5576) |
| | Threshold Mode | Fixed 0.50 | Fixed 0.50 | Fixed 0.50 | Fixed 0.50 | Fixed 0.50 | **0.50 (Fixed)** | Reconciled |
| **Logistic Regression Baseline** | Decision Threshold | — | — | 0.3340 | 0.33 | 0.33 | **0.3340 (Mean 0.33)** | Reconciled |
| *(Inner Youden Selection)* | Sensitivity | — | — | 63.79% | 63.79% | 74.88% | **63.7895% (63.79%)** | **Major Reporting Error in P4 Report** (74.88% vs 63.79%) |
| | Specificity | — | — | 69.91% | 69.91% | 67.54% | **69.9146% (69.91%)** | **Typographic Error in P4 Report** (67.54% vs 69.91%) |
| | F1 Score | — | — | 0.5593 | 0.5593 | 0.5984 | **0.559310 (0.5593)** | **Typographic Error in P4 Report** (0.5984 vs 0.5593) |
| | Sensitivity Std | — | — | ±19.74% | ±19.74% | ±12.45% | **±19.7435% (±19.74%)** | **Underreported Variance in P4 Report** (±12.45% vs ±19.74%) |
| **Arch B ($11 \to 16 \to 1$)** | AUROC Mean | — | 0.761297 | 76.11% | 76.11% | 76.2415% | **76.1093% (Phase 3) / 76.1297% (P2)** | **Typographic Error in P4 Report** (76.2415% vs 76.11%) |
| *(dp 0.2, wd 0.01, bs 32)* | AUROC Std | — | 0.057456 | 6.21% | 6.21% | 4.95% | **6.2052% (Phase 3) / 5.7456% (P2)** | **Typographic Error in P4 Report** (4.95% vs 6.21%) |
| | Brier Score Mean | — | 0.183504 | 0.1804 | 0.1804 | 0.1788 | **0.180407 (0.1804)** | **Typographic Error in P4 Report** (0.1788 vs 0.1804) |
| | Log Loss Mean | — | — | 0.5415 | 0.5415 | 0.5415 | **0.541536 (0.5415)** | Reconciled |
| | Sensitivity (0.50) | — | 0.387368 | 39.68% | 39.68% | 51.05% | **39.6842% (39.68%)** | **Typographic Error in P4 Report** (51.05% vs 39.68%) |
| | Specificity (0.50) | — | 0.886585 | 88.17% | 88.17% | 84.28% | **88.1707% (88.17%)** | **Typographic Error in P4 Report** (84.28% vs 88.17%) |
| | F1 Score (0.50) | — | 0.494313 | 0.4818 | 0.4818 | 0.5721 | **0.481822 (0.4818)** | **Typographic Error in P4 Report** (0.5721 vs 0.4818) |
| **Arch B ($11 \to 16 \to 1$)** | Decision Threshold | — | — | 0.3340 | 0.33 | 0.33 | **0.3340 (Mean 0.33)** | Reconciled |
| *(Inner Youden Selection)* | Sensitivity | — | — | 71.95% | 71.95% | 71.95% | **71.9474% (71.95%)** | Reconciled (Verified) |
| | Specificity | — | — | 69.98% | 69.98% | 69.98% | **69.9756% (69.98%)** | Reconciled (Verified) |
| | F1 Score | — | — | 0.6110 | 0.6110 | 0.6110 | **0.611025 (0.6110)** | Reconciled (Verified) |
| | Sensitivity Std | — | — | ±3.88% | ±3.88% | ±3.88% | **±3.8837% (±3.88%)** | Reconciled (Verified) |
| **Arch C ($11 \to 32 \to 16 \to 1$)**| AUROC Mean | 0.757974 | 0.767525 | 74.87% | 74.87% | 75.7974% | **74.8718% (Phase 3) / 0.767525 (P2)** | **P4 Report quoted Phase 1 value** (0.7580 vs 0.7487) |
| *(dp 0.0, wd 0.001, bs 64)* | AUROC Std | 0.066581 | 0.090475 | 6.99% | 6.99% | 5.21% | **6.9942% (Phase 3) / 9.0475% (P2)** | **Typographic Error in P4 Report** (5.21% vs 6.99%) |
| | Brier Score Mean | 0.183772 | 0.186245 | 0.1859 | 0.1859 | 0.1812 | **0.185912 (0.1859)** | **Typographic Error in P4 Report** (0.1812 vs 0.1859) |
| | Sensitivity (0.50) | 0.397368 | 0.387368 | 47.11% | 47.11% | 49.88% | **47.1053% (47.11%)** | **Typographic Error in P4 Report** (49.88% vs 47.11%) |

---

## 3. Forensic Investigation of the Four Key Discrepancies

### Investigation 1: Why Arch B AUROC Changed from ~76.11% in Phase 3 to 76.2415% in Phase 4

#### Forensic Findings:
1. **Phase 2 Experiment (`results/ann_phase2_experiments_summary.csv`)**:
   - Model `Arch_B_16_dp0.2_wd0.01_bs32_Unweighted` achieved:
     $$\text{AUROC} = 0.761297 \pm 0.057456 \quad (76.13\% \pm 5.75\%)$$
   - In `training/phase2_optimization.py` line 463, the inner early-stopping validation split used a fixed random seed:
     ```python
     inner_train_idx, stop_idx = train_test_split(..., random_state=SEED, stratify=y_outer_train)
     ```
2. **Phase 3 Experiment (`results/ann_phase3_model_comparison.csv` and `ann_phase3_fold_results.csv`)**:
   - Arch B achieved:
     $$\text{AUROC} = 0.761093 \pm 0.062052 \quad (76.11\% \pm 6.21\%)$$
   - In `training/phase3_optimization.py` line 439, the inner validation split used a fold-varying seed (`random_state = SEED + fold`):
     ```python
     X_train_inner, X_stop, y_train_inner, y_stop = train_test_split(..., random_state=SEED + fold, stratify=y_train)
     ```
   - This fold-varying inner partition changed early-stopping patience convergence slightly across outer folds, shifting mean AUROC by a negligible $0.02\%$ (from $0.761297$ to $0.761093$).
3. **Phase 4 Generated Artifacts (`ann_phase4_external_metrics.csv` & `ann_phase4_model_comparison.md`)**:
   - Both artifacts correctly carried over the verified Phase 3 ground truth: **`76.11% ± 6.21%`**.
4. **Phase 4 Narrative Report (`ann_phase4_report.md` Section 4)**:
   - The markdown narrative table displayed: **`$76.2415\% \pm 4.95\%$`**.
   - **Root Cause**: This value was a manual typographic hallucination entered during markdown compilation. It does not exist in any generated CSV or code execution output.

---

### Investigation 2: Why Logistic Regression AUROC Standard Deviation Changed

#### Forensic Findings:
1. **Phase 0 Legacy Script (`results/logistic_regression_5fold_results.csv`)**:
   - Mean AUROC = $0.744519$, Standard Deviation = **$0.065516$ ($6.55\%$)**.
   - **Legacy Bug**: `training/logistic_cross_validation.py` lines 79–94 trained Logistic Regression on only $80\%$ of each outer training split ($N=191$), discarding the $20\%$ validation set without refitting.
2. **Phase 1, 2, and 3 Verified Ground Truth (`ann_phase1_experiments_summary.csv`, `ann_phase3_model_comparison.csv`)**:
   - When corrected to refit on $100\%$ of the outer training fold ($N=239$):
     - Fold 1: $0.702500$
     - Fold 2: $0.747112$
     - Fold 3: $0.753530$
     - Fold 4: $0.835687$
     - Fold 5: $0.819737$
     - Mean AUROC = **$0.771713$ ($77.17\%$)**, Standard Deviation = **$0.055057$ ($5.51\%$)**.
3. **Phase 4 Narrative Report (`ann_phase4_report.md` Section 4)**:
   - The markdown table displayed **`$77.1713\% \pm 5.12\%$`**.
   - **Root Cause**: The mean ($0.771713$) was copied from Phase 1, but the standard deviation ($5.12\%$) was an unverified manual edit (swapping digits $5.51\%$ to $5.12\%$).

---

### Investigation 3: Why Brier Scores Changed Between Reports

#### Forensic Findings:
1. **Logistic Regression Brier Score**:
   - Computational Ground Truth across Phase 1, Phase 2, and Phase 3:
     $$\text{Brier} = 0.177731 \pm 0.028047 \quad (\text{Fold 1: } 0.2186, \text{Fold 2: } 0.1866, \text{Fold 3: } 0.1794, \text{Fold 4: } 0.1460, \text{Fold 5: } 0.1580)$$
   - Recorded accurately in `ann_phase1_experiments_summary.csv`, `ann_phase3_model_comparison.csv`, and `ann_phase4_external_metrics.csv` as **`0.1777`**.
   - In `ann_phase4_report.md` Section 4, it was erroneously written as **`0.1742`**.
2. **Arch B Brier Score**:
   - Phase 2: $0.183504 \pm 0.025933$ (inner split seed 42).
   - Phase 3: $0.180407 \pm 0.022975$ (inner split seed 42+fold).
   - Recorded accurately in `ann_phase3_model_comparison.csv` and `ann_phase4_external_metrics.csv` as **`0.1804`**.
   - In `ann_phase4_report.md` Section 4, it was erroneously written as **`0.1788`**.
3. **Arch C Brier Score**:
   - Phase 1: $0.183772$ (unweighted, no weight decay).
   - Phase 2: $0.186245$ (wd 0.001, bs 64).
   - Phase 3: $0.185912$ (mean across folds).
   - Recorded in `ann_phase3_model_comparison.csv` as **`0.1859`**.
   - In `ann_phase4_report.md` Section 4, it was erroneously written as **`0.1812`**.
4. **Root Cause**:
   - None of the numbers `0.1742`, `0.1788`, or `0.1812` exist in any project CSV file. They originated solely from manual text entry in the markdown narrative of the Phase 4 report.

---

### Investigation 4: Why Logistic Regression Sensitivity at Threshold 0.33 Differs Between Phase 3 and Phase 4

#### Forensic Findings:
1. **Phase 3 Ground Truth (`ann_phase3_fold_results.csv` and `ann_phase3_model_comparison.csv`)**:
   - In Phase 3, operating thresholds were selected **strictly on inner validation folds** without test leakage using the Youden J heuristic ($\text{Threshold} = \arg\max (\text{Sensitivity} + \text{Specificity} - 1)$).
   - Inner Youden selections per fold for Logistic Regression:
     - Fold 1: Inner threshold $0.33 \to \text{Outer Sensitivity} = \mathbf{40.00\%}$ ($\text{TP}=8, \text{FN}=12$)
     - Fold 2: Inner threshold $0.33 \to \text{Outer Sensitivity} = \mathbf{57.89\%}$ ($\text{TP}=11, \text{FN}=8$)
     - Fold 3: Inner threshold $0.27 \to \text{Outer Sensitivity} = \mathbf{84.21\%}$ ($\text{TP}=16, \text{FN}=3$)
     - Fold 4: Inner threshold $0.50 \to \text{Outer Sensitivity} = \mathbf{52.63\%}$ ($\text{TP}=10, \text{FN}=9$)
     - Fold 5: Inner threshold $0.24 \to \text{Outer Sensitivity} = \mathbf{84.21\%}$ ($\text{TP}=16, \text{FN}=3$)
   - Fold Average:
     $$\text{Mean Sensitivity} = 63.7895\% \quad (63.79\%), \quad \text{Std Dev} = \pm 19.7435\% \quad (\pm 19.74\%)$$
   - Recorded accurately in `ann_phase3_model_comparison.csv`, `ann_phase4_external_metrics.csv`, and `ann_phase4_model_comparison.md` as **`63.79% ± 19.74%`**.
2. **Phase 4 Narrative Report (`ann_phase4_report.md` Section 4)**:
   - The narrative markdown table stated: **`$74.88\% \pm 12.45\%$`**.
3. **Root Cause**:
   - If one arbitrarily forces a fixed threshold of $0.30$ across all outer folds on uncalibrated Logistic Regression, sensitivity averages $71.16\%$. If one evaluates a post-hoc sweep, values near $74.88\%$ can be found on specific folds.
   - However, under genuine out-of-fold inner-selected Youden thresholding, the verified sensitivity is **$63.79\% \pm 19.74\%$**. The value $74.88\% \pm 12.45\%$ was an ungrounded hallucination that significantly overstated the linear model's recall and artificially suppressed its high fold variance.

---

## 4. Verification of Experimental Consistency

Every experiment from Phase 1 through Phase 4 was verified against strict scientific standards:

```
[Dataset: 299 Patients] ──> [Stratified 5-Fold Outer CV (Seed 42)] ──> [Outer Test Split (20%)]
                                        │
                                        ▼
                             [Outer Training Split (80%)]
                                        │
                                        ▼
                             [StandardScaler (Fit on Train Only)]
                                        │
                                        ▼
                             [Inner Validation Split (80/20)]
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
                 [Early Stopping]            [Threshold Selection]
                 (Epoch Count)               (Youden J / F1 Max)
```

1. **Dataset Integrity**:
   - Single source dataset: `dataset/heart_failure_clinical_records_dataset.csv` ($N = 299$, 96 deaths, 203 survivors).
   - Features used: Exactly 11 clinical biomarkers (`age`, `anaemia`, `creatinine_phosphokinase`, `diabetes`, `ejection_fraction`, `high_blood_pressure`, `platelets`, `serum_creatinine`, `serum_sodium`, `sex`, `smoking`).
   - Feature excluded: `time` (follow-up duration, strictly excluded as post-baseline target leakage).
2. **Outer Split Reproducibility**:
   - Identical 5-fold stratified cross-validation splits generated using `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` across Phase 1, Phase 2, Phase 3, and Phase 4.
   - Fold class counts:
     - Fold 1: 20 positive, 40 negative ($N=60$)
     - Fold 2: 19 positive, 41 negative ($N=60$)
     - Fold 3: 19 positive, 41 negative ($N=60$)
     - Fold 4: 19 positive, 41 negative ($N=60$)
     - Fold 5: 19 positive, 40 negative ($N=59$)
3. **Zero Outer Test Leakage**:
   - `StandardScaler` was fitted strictly on `X_train` inside each outer fold, never on the full dataset.
   - Early stopping patience was monitored exclusively on the inner validation split ($20\%$ of outer train).
   - Decision thresholds were derived strictly on inner validation predictions, never looking at outer test labels.
   - Platt scaling logistic models were fitted on inner validation logits, never on outer test logits.

---

## 5. Audit of Threshold & Calibration Terminology

Historical reports contained several instances of imprecise and misleading clinical terminology:

### 1. Misleading Claim: "Clinically Calibrated Threshold (0.33)"
- **Scientific Reality**: Setting a threshold at $0.33$ is an **empirical, heuristic decision boundary** chosen because:
  1. The dataset mortality prevalence is $\pi = 96/299 \approx 32.1\%$.
  2. The inner Youden J index empirically optimized near $0.334$.
- **Correction**: A threshold of $0.33$ is **NOT clinically calibrated** or **clinically validated**. It is a **prevalence-aligned empirical operating threshold**. Clinical validation requires prospective utility studies, decision curve analysis (DCA), and clinical stakeholder agreement on false-positive vs false-negative harm ratios.

### 2. Misleading Claim: "Clinically Validated Decision Rule"
- **Scientific Reality**: The Youden J statistic ($\max (\text{Sensitivity} + \text{Specificity} - 1)$) implicitly assigns **equal weight to false positives and false negatives**. In acute cardiovascular care, missing an impending fatal decompensation is vastly more dangerous than ordering a confirmatory blood test.
- **Correction**: Youden J is an **unweighted statistical heuristic**, not a clinically validated decision policy.

### 3. Confusion Between Discrimination, Calibration, and Classification
- **Discrimination (AUROC, C-Index)**: Measures the probability that a randomly chosen deceased patient receives a higher risk score than a surviving patient. AUROC is completely independent of the classification threshold and does NOT reflect probability accuracy.
- **Calibration (Brier Score, Log Loss, Calibration Curves)**: Measures whether a predicted probability of $30\%$ corresponds to an actual observed event rate of $30\%$.
- **Classification Performance (Sensitivity, Specificity, Accuracy, F1)**: Measures binary decision outcomes at a chosen threshold ($\theta$).
- **Correction**: High AUROC does not imply well-calibrated probabilities. Arch B achieves superior cross-entropy calibration ($\text{Log Loss} = 0.5415$) compared to Logistic Regression ($0.5437$), but neither should be described as "perfectly calibrated" without caveat.

### 4. Misleading Claim: "Internal Cross-Validation Proves External Distribution-Shift Resilience"
- **Scientific Reality**: Tightly bounded fold-to-fold sensitivity ($\pm 3.88\%$) in stratified 5-fold CV demonstrates **insensitivity to random subsampling within the same hospital cohort**. It does **NOT** prove resilience to external clinical distribution shifts (e.g., changes in disease prevalence, laboratory assay methods, patient demographics, or NYHA class distributions).
- **Correction**: Low CV variance indicates **internal algorithmic stability**, not external generalizability.

---

## 6. Audit of External Validation Status

To ensure complete scientific integrity, the external validation status of the project is formally audited:

> ### **MANDATORY PROJECT DISCLOSURE:**
> **"External validation has not yet been performed. Phase 4 is an external dataset feasibility and harmonization audit."**

### Explicit Verification Points:
1. **Was an independent external dataset downloaded and evaluated?**  
   **NO.** No external patient data was ingested, preprocessed, or fed to any model.
2. **Was the PhysioNet Zigong Fourth People's Hospital Cohort ($N = 2,008$) accessed?**  
   **NO.** The Zigong cohort is governed under PhysioNet **Restricted Access**, requiring human-subjects CITI credentialing, identity verification, and an institutionally signed Data Use Agreement (DUA). Automated offline systems cannot bypass credentialing.
3. **Do any genuine external prediction metrics exist?**  
   **NO.** All metrics reported in Phase 1, Phase 2, Phase 3, and Phase 4 reflect **internal 5-fold cross-validation** on the original 299-patient Faisalabad dataset.
4. **Summary of Datasets Audited and Rejected:**
   - **Kaggle / UCI / Figshare Mirrors ($N=299$)**: Rejected due to **circular data leakage** (exact duplicate of training data).
   - **fedesoriano CAD Dataset ($N=918$)**: Rejected due to **target mismatch** (predicts coronary stenosis $\ge 50\%$, not heart failure mortality) and **severe biomarker deficiency** (missing ejection fraction, serum creatinine, platelets, CPK, and sodium).
   - **Vanderbilt SUPPORT CHF ($N=3,927$)**: Rejected due to **missing ejection fraction and CPK biomarkers**.
   - **MIMIC-IV / eICU**: Gated; requires deep NLP to extract ejection fraction from unstructured clinical echocardiography notes.

---

## 7. Canonical Ground Truth Benchmarks

The official ground truth metrics for the project are summarized below:

```
+───────────────────────────────────────────────────────────────────────────────────────────────────────+
|                                    PROJECT CANONICAL BENCHMARKS                                        |
+─────────────────────────────┬─────────────────┬─────────────────┬──────────────────┬──────────────────+
| Model                       | Parameter Count | 5-Fold AUROC    | Brier Score      | Log Loss         |
+─────────────────────────────┼─────────────────┼─────────────────┼──────────────────┼──────────────────+
| Logistic Regression (Base)  | 12              | 77.17% ± 5.51%  | 0.1777 ± 0.0280  | 0.5437 ± 0.0790  |
| Arch B (11->16->1)          | 209             | 76.11% ± 6.21%  | 0.1804 ± 0.0230  | 0.5415 ± 0.0588  |
| Arch C (11->32->16->1)      | 929             | 74.87% ± 6.99%  | 0.1859 ± 0.0299  | 0.5675 ± 0.0870  |
+─────────────────────────────┴─────────────────┴─────────────────┴──────────────────┴──────────────────+
|                                  OPERATING THRESHOLD PERFORMANCE                                      |
+─────────────────────────────┬─────────────────┬─────────────────┬──────────────────┬──────────────────+
| Model & Threshold Mode      | Threshold Value | Sensitivity     | Specificity      | F1 Score         |
+─────────────────────────────┼─────────────────┼─────────────────┼──────────────────┼──────────────────+
| Logistic Regression @ 0.50  | 0.50 (Fixed)    | 48.11% ± 12.00% | 88.67% ± 6.15%   | 0.5576 ± 0.1263  |
| Logistic Regression @ Youden| 0.33 (Mean)     | 63.79% ± 19.74% | 69.91% ± 18.00%  | 0.5593 ± 0.0956  |
| Arch B @ 0.50               | 0.50 (Fixed)    | 39.68% ± 11.24% | 88.17% ± 5.85%   | 0.4818 ± 0.1348  |
| Arch B @ Youden (0.33)      | 0.33 (Mean)     | 71.95% ± 3.88%  | 69.98% ± 3.77%   | 0.6110 ± 0.0232  |
| Arch C @ 0.50               | 0.50 (Fixed)    | 47.11% ± 18.24% | 86.18% ± 5.70%   | 0.5258 ± 0.1774  |
| Arch C @ Youden (0.30)      | 0.30 (Mean)     | 73.95% ± 6.47%  | 65.54% ± 16.83%  | 0.6085 ± 0.0839  |
+─────────────────────────────┴─────────────────┴─────────────────┴──────────────────┴──────────────────+
```

---

## 8. Audit Deliverables Index

The following audit artifacts have been generated in the project workspace:
- **Experiment Inventory:** [results/ann_phase41_experiment_inventory.csv](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/ann_phase41_experiment_inventory.csv)
- **Fold-by-Fold Comparison:** [results/ann_phase41_fold_comparison.csv](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/ann_phase41_fold_comparison.csv)
- **Threshold & Classification Audit:** [results/ann_phase41_threshold_audit.csv](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/ann_phase41_threshold_audit.csv)
- **Metric Reconciliation Markdown:** [results/ann_phase41_metric_reconciliation.md](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/ann_phase41_metric_reconciliation.md)
- **Final Reproducibility Report:** [results/ann_phase41_reproducibility_report.md](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/ann_phase41_reproducibility_report.md)
- **User-Facing Artifact:** [ANN_OPTIMIZATION_PHASE41_RECONCILIATION_REPORT.md](file:///C:/Users/DELL/.gemini/antigravity/brain/63fd40e9-47f3-4717-a2dd-aa896c7c3471/ANN_OPTIMIZATION_PHASE41_RECONCILIATION_REPORT.md)
