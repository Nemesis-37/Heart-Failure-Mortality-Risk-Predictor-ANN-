# Phase 13 — Final Comparative Model Evaluation & Synthesis

**Project:** Heart Failure Mortality Risk Predictor — CardioPredict Clinical Portal  
**Phase:** Phase 13 (Phases 2, 3, 5, 6, 11 & 13 Complete Evaluation — Research-Only)  
**Date:** November 26, 2026  

---

## 1. Leakage & Integrity Audit (Phase 3D)

Before comparing models, a strict forensic audit was conducted on the dataset and both existing training scripts:

1. **Duplicate / Overlap Leakage:** **0 exact duplicates** and **0 11-feature duplicates** across the 299 patients. Outer cross-validation splits share zero overlapping records.
2. **Post-Outcome Variable Leakage (`time`):** Properly excluded in all production pipelines (`save_model.py`, `train_ann.py`, `main.py`). Only baseline predictors (`11` features) are used.
3. **Production Artifact Leakage / Asymmetry Discrepancy (CRITICAL DISCOVERY):**
   - Production LR (`models/logistic_regression_pipeline.joblib`) was trained on all **299 patients** (`n_samples_seen_ = 299`).
   - Production ANN (`models/ann_model.pth`, `models/ann_scaler.joblib`) was **not** trained on all 299 patients. Instead, `training/train_ann.py` ran 5-fold CV where **early stopping monitored outer validation loss directly** (`val_loss < best_val_loss`), and then saved **Fold 4's weights and Fold 4's `StandardScaler` (`n_samples_seen_ = 239`)** because Fold 4 achieved the lowest validation loss (`0.4192`).
   - As a result, `train_ann.py` (`results/ann_5fold_results.csv`, Mean AUROC `0.7606`) suffered from **outer-validation early-stopping leakage**. When evaluated cleanly using nested 80/20 inner splits (`training/ann_cross_validation.py` protocol), ANN's true unseen OOF AUROC drops to **`0.6935`** (Seed 42) / **`0.7238`** (50-fold Repeated CV).
4. **Threshold & Calibration Leakage Audit:** No outer-fold labels were used to tune thresholds (`0.50` fixed baseline; `0.33` prevalence-aligned reference) or post-hoc calibrators / ensemble weights (fitted strictly inside inner validation splits).

---

## 2. Unseen-Patient Generalization: Side-by-Side Comparison (Phases 2 & 3)

### 2.1 Pooled Genuine Out-of-Fold Evaluation (`N = 299` Unseen Patients, Seed 42, Threshold `0.50`)

Visualizations: [`fig01_roc_curves.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig01_roc_curves.png) | [`fig02_pr_curves.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig02_pr_curves.png) | [`fig04_confusion_matrices.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig04_confusion_matrices.png)

| Metric (Threshold `0.50`) | Clinical / Statistical Meaning | Logistic Regression (OOF) | ANN `11->64->32->1` (OOF) | LR − ANN Difference [Bootstrap 95% CI] |
| :--- | :--- | :---: | :---: | :---: |
| **AUROC** | Probability a randomly chosen dying patient scores higher than a survivor | **0.7595** | 0.6935 | **`+0.0660`** `[+0.0349, +0.0998]` *(DeLong $p = 7.76\times 10^{-5}$)* |
| **PR-AUC** | Precision-recall balance under 32.1% class imbalance (baseline = 0.321) | **0.6075** | 0.5270 | **`+0.0797`** `[+0.0313, +0.1282]` |
| **Brier Score** $\downarrow$ | Mean squared probability error across all patients | **0.1778** | 0.2053 | **`-0.0276`** `[-0.0405, -0.0152]` *(lower = better)* |
| **Log Loss** $\downarrow$ | Cross-entropy penalty (penalizes confident wrong predictions heavily) | **0.5438** | 0.6190 | **`-0.0753`** `[-0.1197, -0.0369]` *(lower = better)* |
| **Balanced Accuracy** | Average of sensitivity and specificity under class imbalance | **68.29%** | 63.75% | **`+4.58%`** `[+0.40%, +8.76%]` |
| **Sensitivity (Recall)** | Fraction of 96 mortality events correctly flagged as high risk | **47.92%** (`46/96`) | 43.75% (`42/96`) | `+4.20%` `[-3.03%, +11.24%]` *(CI crosses 0)* |
| **Specificity** | Fraction of 203 survivors correctly cleared (avoids false alarms) | **88.67%** (`180/203`) | 83.74% (`170/203`) | **`+4.97%`** `[+0.94%, +9.18%]` |
| **Precision (PPV)** | Fraction of flagged high-risk patients who actually died | **66.67%** (`46/69`) | 56.00% (`42/75`) | `+10.67%` |
| **F1-Score** | Harmonic mean of precision and sensitivity | **0.5576** | 0.4912 | **`+0.0668`** `[+0.0013, +0.1334]` |
| **Accuracy** | Overall % correct (can mislead under class imbalance) | **75.59%** (`226/299`) | 70.90% (`212/299`) | `+4.68%` |
| **TP / TN / FP / FN** | Exact patient outcomes out of `N = 299` | **46 / 180 / 23 / 50** | 42 / 170 / 33 / 54 | McNemar discordant `23 vs 9` ($p = 0.0201$) |

*(At prevalence-aligned threshold `0.33`: LR achieves Sensitivity **64.58%** `[62/96]` & Specificity **71.43%** `[145/203]` vs ANN Sensitivity **59.38%** `[57/96]` & Specificity **70.44%** `[143/203]`.)*  
*(Matched sample-size control: even when LR is restricted to the exact same 80% inner training split `N ≈ 191` as ANN, LR still outperforms ANN on OOF AUROC `0.7338` vs `0.6935`, Brier `0.1847` vs `0.2053`, and Log Loss `0.5625` vs `0.6190`.)*

### 2.2 Repeated Stratified `5 × 10` Cross-Validation (`50 Folds`) & Corrected Matched-Data Audit

*(Updated following Methodological Audit in [`phase13_methodological_audit.md`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/phase13_methodological_audit.md) & [`phase13_corrected_cv_statistics.csv`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/phase13_corrected_cv_statistics.csv).)*

Visualizations: [`fig11_explainability_and_stability.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig11_explainability_and_stability.png) Panel B

- **Original 50-Fold Comparison (`LR_Outer239` vs `ANN_Inner191` — note asymmetric training size `239` vs `191`):**
  - **AUROC:** LR **`0.7595 ± 0.0621`** vs ANN **`0.7238 ± 0.0683`** (descriptive fold wins: `41 / 50`; Nadeau–Bengio corrected $p = 0.1184$, **not significant**).
  - **PR-AUC:** LR **`0.6284 ± 0.0961`** vs ANN **`0.5832 ± 0.0986`** ($p = 0.1221$).
  - **Brier Score:** LR **`0.1787 ± 0.0238`** vs ANN **`0.1910 ± 0.0227`** ($p = 0.1103$).
  - **Log Loss:** LR **`0.5459 ± 0.0689`** vs ANN **`0.5714 ± 0.0619`** ($p = 0.2434$).
  - **Sensitivity / Specificity (@ 0.50):** LR **`0.4313 ± 0.1059`** / `0.8808 ± 0.0565` vs ANN `0.3629 ± 0.1424` / **`0.8872 ± 0.0621`**.
- **Strictly Matched-Partition Controls (50 Splits Each):**
  - **Identical Inner Split (`~191` rows):** `LR_Inner191` (`AUROC 0.7482 ± 0.0621`, `Brier 0.1828`) vs `ANN_Inner191` (`AUROC 0.7238 ± 0.0683`, `Brier 0.1910`), diff `+0.0244`, Nadeau–Bengio corrected **$p = 0.1741$**.
  - **Matched Outer Refit (`~239` rows):** `LR_Outer239` (`AUROC 0.7595 ± 0.0621`, `Brier 0.1787`) vs `ANN_RefitOuter239` (`AUROC 0.7425 ± 0.0636`, `Brier 0.1869`), diff `+0.0170`, Nadeau–Bengio corrected **$p = 0.2418$**.
- **Single-Seed `Seed = 42` Caveat & ANN Seed Instability:**
  - Repeat 1 (`Seed = 42`) DeLong $p = 7.76 \times 10^{-5}$ (`0.7595` vs `0.6935`) reflects ANN's worst random split/seed; across all 10 repeats, only 5 of 10 DeLong tests had $p < 0.05$ (`Repeat 2: p = 0.4894`, `Repeat 5: p = 0.4569`). Across 5 random seeds on Repeat 1 splits, ANN OOF AUROC swung by **5.93 percentage points** (`0.6935` to `0.7528`).
- **Why `0.7595` Appeared in Both Single-Split OOF and 50-Fold Repeated CV:**
  - `0.759534` (50-fold mean of fold AUROCs) and `0.759493` (Seed-42 pooled `N=299` OOF AUROC) are distinct aggregation modes that coincide to 4 decimal places (`Δ = 0.000041`).

*(Standard deviation across folds reflects finite-sample split variability on `N ≈ 60` validation folds and is **not** a confidence interval for population accuracy; Nadeau–Bengio corrected CIs are reported in `phase13_corrected_cv_statistics.csv`.)*

---

## 3. Behavioural & Interaction Analysis Findings (Phases 5 & 6)

Visualizations: [`fig05_feature_perturbation_curves.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig05_feature_perturbation_curves.png) | [`fig07_feature_interaction_heatmaps.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig07_feature_interaction_heatmaps.png)

1. **Core Continuous Physiological Drivers (`ejection_fraction`, `age`, `serum_creatinine`, `serum_sodium`, `CPK`):**
   - Both models strongly capture directional risk on primary clinical predictors (`ef` decreasing $\to$ higher mortality; `age` & `creatinine` increasing $\to$ higher mortality; `sodium` decreasing $\to$ higher mortality).
   - **Divergence:** On `Cohort_Median_Profile`, LR increases smoothly with `age` (`[0.030, 0.506]`) and `serum_creatinine` (`[0.090, 0.969]`), whereas ANN shows kinked piecewise-linear ReLU slopes (`age` reaching `0.717` at age 95; `max|diff| = 0.211` on age, `0.206` on creatinine).
2. **Noisy Binary Features (`diabetes`, `high_blood_pressure`, `smoking`) — Unstable ANN Sign Flips:**
   - Under LR, binary flags shift log-odds consistently across all profiles (`diabetes +0.070`, `high_blood_pressure +0.195`, `smoking +0.056`, `anaemia +0.199`, `sex -0.178`).
   - Under `models/ann_model.pth`, binary flags **flip signs erratically across profiles**:
     - On `Cohort_Median_Profile`: setting `diabetes=1` **lowers** risk (`0.103 -> 0.070`), setting `high_blood_pressure=1` **lowers** risk (`0.103 -> 0.095`), and setting `smoking=1` **lowers** risk (`0.103 -> 0.086`).
     - Yet on `Female_Hypertensive_Moderate`, setting `smoking=1` **jumps** risk `+0.291` (`0.246 -> 0.538`) and `diabetes=1` jumps risk `+0.175` (`0.246 -> 0.421`)!
     - Because `smoking`, `diabetes`, and `anaemia` have near-zero or negative OOF permutation importance, these erratic jumps represent small-sample interaction memorization in the 2,881-parameter network rather than generalizable clinical subgroups.
3. **2D Interaction Surfaces (`phase13_feature_interaction_results.csv`):**
   - Smooth high-risk agreement appears in the expected clinical corners of `age × ejection_fraction` (older age + low EF) and `ejection_fraction × serum_creatinine` (low EF + high Cr), with moderate agreement (`mean |diff| = 0.052–0.068`).
   - Larger non-additive distortions (`max |diff| = 0.223–0.303`) occur in `age × serum_sodium` and `platelets × serum_creatinine`, where ANN forms sharp local pockets not supported by out-of-fold validation gains.

---

## 4. Ensemble Experiment Synthesis (Phase 11)

Visualization: [`fig10_ensemble_comparison.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig10_ensemble_comparison.png) | Data: [`phase13_ensemble_comparison.csv`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/phase13_ensemble_comparison.csv)

Using strictly leak-free out-of-fold probabilities across $P_{\text{ens}} = w \cdot P_{\text{LR}} + (1-w) \cdot P_{\text{ANN}}$:
- **`ANN_Only (w=0.0)`:** AUROC `0.6935` | PR-AUC `0.5270` | Brier `0.2053` | Log Loss `0.6190` | 5-Fold SD `0.0805`
- **`Equal_50_50 (w=0.5)`:** AUROC `0.7313` | PR-AUC `0.5718` | Brier `0.1883` | Log Loss `0.5673` | 5-Fold SD `0.0657`
- **`Weighted_90LR_10ANN (w=0.9)`:** AUROC `0.7546` | PR-AUC `0.6042` | Brier `0.1794` | Log Loss `0.5470` | 5-Fold SD `0.0562`
- **`Nested_InnerVal_Selected (mean w=0.66)`:** AUROC `0.7268` | PR-AUC `0.5596` | Brier `0.1929` | Log Loss `0.5816` | 5-Fold SD `0.0719`
- **`LR_Only (w=1.0)`:** **AUROC `0.7595` | PR-AUC `0.6075` | Brier `0.1778` | Log Loss `0.5438` | 5-Fold SD `0.0551`**

**Verdict:** Every ensemble blend strictly **underperforms LR alone** on discrimination (AUROC, PR-AUC), probability error (Brier, Log Loss), and cross-validation stability. Even nested inner-validation weighting degraded performance (`0.7268` vs `0.7595`). Blending ANN with LR merely dilutes LR's calibrated probabilities with ANN's higher-variance noise.

---

## 5. Comprehensive Phase 13 Comparative Scorecard

| Evaluation Area | Logistic Regression (LR) | Artificial Neural Network (ANN `11->64->32->1`) | Better-Supported Result |
| :--- | :--- | :--- | :--- |
| **AUROC** *(OOF `N=299` / `5x10` CV)* | **0.7595** OOF / **0.7595 ± 0.0621** (`LR_Inner191`: **0.7482**) | 0.6935 OOF / 0.7238 ± 0.0683 (`Refit239`: 0.7425) | **LR** descriptive lead (`36–41/50` folds); Nadeau–Bengio $p = 0.118\text{--}0.242$ (NS) |
| **PR-AUC** *(OOF `N=299` / `5x10` CV)* | **0.6075** OOF / **0.6284 ± 0.0961** | 0.5270 OOF / 0.5832 ± 0.0986 (`Refit239`: 0.5996) | **LR** descriptive lead (`37–40/50` folds); Nadeau–Bengio $p = 0.122\text{--}0.263$ (NS) |
| **Sensitivity** *(@ `0.50` / @ `0.33`)* | **47.92%** (`0.50`) / **64.58%** (`0.33`); `5x10`: **43.13%** | 43.75% (`0.50`) / 59.38% (`0.33`); `5x10`: 36.29% | **LR** higher point estimate, Nadeau–Bengio $p = 0.40\text{--}0.76$ (NS) |
| **Specificity** *(@ `0.50` / @ `0.33`)* | **88.67%** (`0.50`) / **71.43%** (`0.33`); `5x10`: 88.08% | 83.74% (`0.50`) / 70.44% (`0.33`); `5x10`: **88.72%** | **Tie** (`5x10`: `21 vs 21` folds, $p = 0.79\text{--}0.88$) |
| **Brier Score** *(OOF / `5x10`)* | **0.1778** / **0.1787 ± 0.0238** | 0.2053 / 0.1910 ± 0.0227 (`Refit239`: 0.1869) | **LR** descriptive lead (`36–41/50` folds); Nadeau–Bengio $p = 0.110\text{--}0.270$ (NS) |
| **Log Loss** *(OOF / `5x10`)* | **0.5438** / **0.5459 ± 0.0689** | 0.6190 / 0.5714 ± 0.0619 (`Refit239`: 0.5647) | **LR** descriptive lead (`32–38/50` folds); Nadeau–Bengio $p = 0.238\text{--}0.555$ (NS) |
| **Calibration** *(ECE / Slope / CITL)* | **ECE 0.0414**, **Slope 0.7509**, **CITL -0.0061** | ECE 0.1033, Slope 0.4791, CITL +0.0279 | **LR** (2.5× lower ECE, vastly less overconfidence) |
| **Cross-validation stability** | Deterministic (0 seed SD); `5x10` AUROC SD `0.0621` | Seed-sensitive (`0.6935–0.7528`, SD `0.0238`); `5x10` SD `0.0683` | **LR** (exact convex determinism & tighter CV variance) |
| **Patient-level errors** *(@ `0.50`)* | **226/299 correct**; wins **23 of 32** discordant cases | 212/299 correct; wins 9 of 32 discordant cases | **LR** (McNemar exact $p = 0.0201$) |
| **Feature behaviour** | Smooth, physiologically monotonic curves across profiles | Unstable sign flips on binary comorbidities (`smoking`, `diabetes`, `HBP`) and platelets | **LR** (parsimonious, no erratic sign reversals) |
| **Interaction behaviour** | Purely additive in log-odds (cannot learn synergies) | Captures some high-acuity combinations, but creates noisy pockets on `N=239` | **Mixed / LR preferred for safety** (ANN interactions fail to improve OOF generalization) |
| **Explainability** | Exact closed-form $\beta$, SE, Wald $z$, OR with 95% CIs | Integrated Gradients over-attributes noisy binary flags above `sodium` and `CPK` | **LR** (transparent, statistically verifiable weights) |
| **External validation** | **BLOCKED / NOT AVAILABLE** (No compatible open dataset) | **BLOCKED / NOT AVAILABLE** (No compatible open dataset) | **Neither** (Unresolved gap for both models) |
| **Ensemble contribution** | Best model standalone (`w=1.0`: AUROC `0.7595`, Brier `0.1778`) | Blending degrades LR across every weight `w < 1.0` | **No ensemble justification** (Pure LR strictly dominates) |
