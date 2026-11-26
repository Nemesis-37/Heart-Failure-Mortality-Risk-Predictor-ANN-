# Phase 13 — Patient-Level Comparison & Model Disagreement Analysis

**Project:** Heart Failure Mortality Risk Predictor — CardioPredict Clinical Portal  
**Phase:** Phase 13 — Phases 4 & 10 Patient-Level Evaluation & Disagreement Audit  
**Dataset Scope:** Genuine Leak-Free 5-Fold Out-of-Fold (`N = 299` untouched patients, Threshold = `0.50`)  
**Visualizations:** [`fig08_disagreement_distribution.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig08_disagreement_distribution.png) | [`fig09_patient_level_comparison.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig09_patient_level_comparison.png)  

---

## 1. Overall Patient-Level OOF Partitioning (`N = 299`, Threshold `0.50`)

All 299 patient records were evaluated strictly out-of-fold (exported in [`phase13_oof_patient_predictions.csv`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/phase13_oof_patient_predictions.csv) and [`phase13_patient_level_comparison.csv`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/phase13_patient_level_comparison.csv)).  
*(Production artifact in-sample / Fold-4 predictions are strictly separated in those CSVs and are never counted as unseen generalization.)*

| Outcome / Comparison Group (@ `0.50`) | Patient Count | % of Cohort | Mean Age | Mean EF (%) | Mean Cr (mg/dL) | Mean Na (mEq/L) | Mean $P_{\text{LR}}$ | Mean $P_{\text{ANN}}$ | Mean $|P_{\text{LR}} - P_{\text{ANN}}|$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Both Models Correct** | **203** | 67.89% | 59.75 | 39.94 | 1.34 | 136.87 | 0.281 | 0.279 | 0.052 |
| **2. Both False Negative** *(Predict Survive, Actual Death)* | **46** | 15.38% | 60.17 | 36.96 | 1.31 | 136.30 | 0.258 | 0.205 | 0.068 |
| **3. Both False Positive** *(Predict Death, Actual Survive)* | **18** | 6.02% | 64.44 | 29.56 | 2.29 | 133.11 | 0.664 | 0.725 | 0.089 |
| **4. LR Correct, ANN Wrong** | **23** | 7.69% | 63.99 | 32.87 | 1.38 | 137.35 | 0.465 | 0.493 | **0.202** |
| **5. ANN Correct, LR Wrong** | **9** | 3.01% | 73.33 | 32.33 | 1.28 | 137.89 | 0.533 | 0.480 | **0.227** |
| **6. Total Classification Disagreements** | **32** | 10.70% | — | — | — | — | — | — | **0.209** |
| **7. Substantial Prob Diff ($\ge 0.15$) w/ Same Class** | **20** | 6.69% | — | — | — | — | — | — | — |

### Key Aggregate Disagreement Statistics (`N = 299`):
- **Mean Absolute Probability Difference ($|P_{\text{LR}} - P_{\text{ANN}}|$):** **`0.0735`** (Max = **`0.6567`**)
- **Probability Correlation ($r$):** **`0.865`**
- **Directional Bias:** $P_{\text{LR}} > P_{\text{ANN}}$ in **159 / 299 (53.2%)** patients; $P_{\text{ANN}} > P_{\text{LR}}$ in **140 / 299 (46.8%)**.
- **McNemar's Paired Classification Test (@ `0.50`):** Out of **32 discordant patients**, LR was right on **23 (71.9%)** while ANN was right on only **9 (28.1%)**, exact **$p = 0.0201$**.

---

## 2. Directional Disagreement Breakdown

### A. Disagreement Subgroups (@ `0.50`)
1. **LR Predicts Mortality (`1`), ANN Predicts Survival (`0`) — `n = 13` patients:**
   - **LR Correct:** **8 / 13 (61.5%)** | **ANN Correct:** 5 / 13 (38.5%)
   - **Clinical Profile:** Predominantly **older patients with moderately reduced EF** (`mean age ~ 70+`, `EF ~ 25–35%`, normal creatinine `~1.0 mg/dL`) where LR's steady linear age + EF penalty identifies high risk, while the ANN collapses to very low probabilities.
   - *Extreme Case — Patient 73* (`age=85, EF=35%, Cr=1.0`, **Died**): $P_{\text{LR}} = 0.8371$ (**correct**) vs $P_{\text{ANN}} = 0.1804$ (`-0.657` discrepancy!).
   - *Extreme Case — Patient 61* (`age=45, EF=25%, Cr=1.0, Plt=390k`, **Died**): $P_{\text{LR}} = 0.5230$ (**correct**) vs $P_{\text{ANN}} = 0.0081$ (`0.81%` near-zero probability saturation on a fatal EF=25% case!).

2. **ANN Predicts Mortality (`1`), LR Predicts Survival (`0`) — `n = 19` patients:**
   - **ANN Correct:** Only **4 / 19 (21.1%)** | **LR Correct:** **15 / 19 (78.9%)**!
   - **Clinical Profile:** Often younger/middle-aged survivors (`age 47–55, Cr 0.5–1.0 mg/dL`) with `EF 25–38%` whom ANN sharply over-predicts into false-positive alarm territory (`0.54–0.81`).
   - *Case — Patient 140* (`age=50, EF=30%, Cr=0.8`, **Survived**): $P_{\text{LR}} = 0.2844$ (**correct**) vs $P_{\text{ANN}} = 0.6971$ (false positive).
   - *Case — Patient 251* (`age=50, EF=30%, Cr=0.5`, **Survived**): $P_{\text{LR}} = 0.2956$ (**correct**) vs $P_{\text{ANN}} = 0.5798$ (false positive).
   - *Counter-Example — Patient 2* (`age=55, EF=38%, Cr=1.1`, **Died** — extreme CPK outlier `7861`): $P_{\text{ANN}} = 0.8184$ (**correct**) vs $P_{\text{LR}} = 0.4227$ (missed; linear CPK capped below threshold).

3. **Same Classification, Large Probability Gap ($|P_{\text{LR}} - P_{\text{ANN}}| \ge 0.15$) — `n = 20` patients:**
   - **13 agreed on Survival (`< 0.50`)**, **7 agreed on Mortality (`>= 0.50`)**, observed cohort death rate in this group = **45.0%**.
   - Demonstrates that even when binary labels agree at `0.50`, ANN's overconfident calibration slope (`0.479`) pushes predicted risks far away from LR (`0.01` vs `0.25`, or `0.97` vs `0.72`), which would yield mismatched clinical risk tiers in a decision-support UI.

---

## 3. Shared Blind Spots (Both Models Wrong)

1. **Shared False Negatives (`n = 46`, 47.9% of all 96 deaths!):**
   - Average profile closely mimics survivors: `mean age = 60.2`, `mean EF = 37.0%`, `mean Cr = 1.31`, `mean Na = 136.3`.
   - At the baseline evaluation date without follow-up duration (`time` excluded), these 46 patients lacked severe systolic or renal failure markers yet died during follow-up—highlighting **missing clinical variables** (NYHA functional class, BNP/NT-proBNP, ischemic etiology, medication regimens) rather than an optimization defect.
   - Note: Lowering threshold from `0.50 -> 0.33` cuts LR false negatives from `50 -> 34` (raising sensitivity `47.9% -> 64.6%`) at the expense of raising false positives (`23 -> 58`).

2. **Shared False Positives (`n = 18`):**
   - High-acuity profile (`mean age = 64.4`, `mean EF = 29.6%`, `mean Cr = 2.29`, `mean Na = 133.1`) — clinically very sick patients who nonetheless survived the observation window. Both models behave plausibly here given their elevated biomarkers.
