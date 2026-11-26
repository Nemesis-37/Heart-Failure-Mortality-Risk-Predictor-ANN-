# Phase 13 — Explainability & Attribution Analysis Report

**Project:** Heart Failure Mortality Risk Predictor — CardioPredict Clinical Portal  
**Phase:** Phase 13 — Phase 8 Explainability Analysis (Research-Only)  
**Visualization:** [`fig11_explainability_and_stability.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig11_explainability_and_stability.png)  

---

## 1. Methodology & Safeguards

To compare how Logistic Regression (LR) and the Artificial Neural Network (`11 -> 64 -> 32 -> 1`) arrive at predictions without leakage or post-hoc rationalization:
1. **Logistic Regression Structural Inference:** Extracted exact standardized weights ($\beta_{\text{std}}$), Fisher-information Wald standard errors, $z$-statistics, and Odds Ratios ($\text{OR} = \exp(\beta_{\text{std}})$ per 1 SD change) from `models/logistic_regression_pipeline.joblib` (`N = 299`).
2. **Leak-Free OOF Permutation Importance:** Computed the mean AUROC drop across **30 random permutations × 5 untouched outer CV test folds** for both models, strictly preserving unseen-patient isolation.
3. **ANN Integrated Gradients (IG):** Computed 50–64 step trapezoidal Integrated Gradients from the cohort-mean standardized baseline ($z = 0$) to each patient's feature vector in standardized input space, matching `models/ann_scaler.joblib` and `models/ann_model.pth`.

> [!NOTE]
> **Causal Disclaimer:** Feature importance, odds ratios, and Integrated Gradients quantify **statistical association within a model's learned function**, not causal biological effects. Unmeasured confounders, treatment effects, and small-sample variance (`N = 299`) affect all attributions.

---

## 2. Global Feature Importance Comparison

| Feature | LR $\beta_{\text{std}}$ ($\pm \text{SE}$) | LR Wald $z$ | LR Odds Ratio / 1 SD [95% CI] | LR OOF Perm AUROC Drop | ANN OOF Perm AUROC Drop | ANN Global Mean $|IG_{\text{logit}}|$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`ejection_fraction`** | **$-0.800 \pm 0.170$** | **$-4.70$** | `0.449` `[0.322, 0.628]` | **`+0.1213`** *(Rank 1)* | **`+0.0871`** *(Rank 1)* | `0.6125` *(Rank 2)* |
| **`age`** | **$+0.639 \pm 0.152$** | **$+4.20$** | `1.895` `[1.406, 2.553]` | **`+0.0747`** *(Rank 2)* | **`+0.0407`** *(Rank 3)* | **`0.6717`** *(Rank 1)* |
| **`serum_creatinine`** | **$+0.660 \pm 0.173$** | **$+3.81$** | `1.936` `[1.379, 2.718]` | **`+0.0696`** *(Rank 3)* | **`+0.0727`** *(Rank 2)* | `0.4283` *(Rank 3)* |
| **`serum_sodium`** | $-0.247 \pm 0.144$ | $-1.71$ | `0.781` `[0.589, 1.037]` | `+0.0140` *(Rank 5)* | `+0.0095` *(Rank 4)* | `0.1496` *(Rank 10)* |
| **`creatinine_phosphokinase`** | $+0.270 \pm 0.136$ | $+1.99$ | `1.310` `[1.004, 1.710]` | `+0.0198` *(Rank 4)* | `+0.0039` *(Rank 5)* | `0.1302` *(Rank 11)* |
| **`anaemia`** | $+0.199 \pm 0.146$ | $+1.36$ | `1.220` `[0.916, 1.624]` | `-0.0003` | `-0.0068` | `0.3307` *(Rank 4!)* |
| **`high_blood_pressure`** | $+0.195 \pm 0.143$ | $+1.36$ | `1.215` `[0.917, 1.609]` | `+0.0053` | `-0.0003` | `0.2926` *(Rank 5!)* |
| **`sex`** | $-0.178 \pm 0.163$ | $-1.09$ | `0.837` `[0.607, 1.152]` | `+0.0042` | `-0.0009` | `0.2171` *(Rank 7)* |
| **`diabetes`** | $+0.070 \pm 0.144$ | $+0.49$ | `1.073` `[0.809, 1.423]` | `-0.0000` | `-0.0171` | `0.1709` *(Rank 8)* |
| **`platelets`** | $-0.066 \pm 0.155$ | $-0.43$ | `0.936` `[0.691, 1.267]` | `-0.0011` | `-0.0059` | `0.1081` *(Rank 9)* |
| **`smoking`** | $+0.056 \pm 0.159$ | $+0.35$ | `1.058` `[0.775, 1.445]` | `-0.0064` | `-0.0155` | `0.2262` *(Rank 6!)* |

### Critical Findings Across Global Explanations:
1. **Agreement on Top 3 Dominant Drivers:** Both LR and ANN agree that **`ejection_fraction`**, **`serum_creatinine`**, and **`age`** dominate out-of-fold mortality discrimination (`AUROC drop +0.041 to +0.121`), consistent with clinical cardiorenal physiology and Chicco & Jurman (2020).
2. **Noise Over-Attribution in ANN:**
   - Look closely at **`smoking`**, **`diabetes`**, **`anaemia`**, and **`high_blood_pressure`**:
   - Their OOF permutation AUROC drops are **zero or strongly negative** (`smoking: -0.0155`, `diabetes: -0.0171`, `anaemia: -0.0068`) — permuting them actually *improves* ANN out-of-fold AUROC because the ANN overfits spurious binary rules!
   - Yet inside `models/ann_model.pth`, Integrated Gradients shows large internal logit attributions to those exact noisy binary flags (`anaemia |IG| = 0.331`, `high_blood_pressure |IG| = 0.293`, `smoking |IG| = 0.226`), **larger than genuine biomarkers like `serum_sodium` (`0.150`) and `creatinine_phosphokinase` (`0.130`)**!
3. **LR Regularized Parsimony:** LR assigns large Wald-$z$ weights to the true core predictors (`ef z=-4.70`, `age z=4.20`, `cr z=3.81`, `cpk z=1.99`, `na z=-1.71`) and small weights to weak predictors (`diabetes +0.070`, `platelets -0.066`, `smoking +0.056`).

---

## 3. Local Explanation Case Studies (Integrated Gradients vs LR Log-Odds)

Comparing exact feature contributions (in log-odds units relative to cohort baseline) across representative patient profiles (`results/phase13/phase13_explainability_summary.json`):

1. **`Cohort_Median_Profile`** (`LR Prob = 0.135`, `ANN Prob = 0.103`):
   - Both models stay comfortably low-risk; `anaemia=0` (`LR -0.173`, `ANN IG -0.335`) and `serum_creatinine=1.1` (`LR -0.188`, `ANN IG -0.210`) pull risk below the 32.1% cohort base rate.
2. **`Borderline_Cardiorenal`** (`LR Prob = 0.669`, `ANN Prob = 0.712`):
   - **LR top risk contributors:** `ejection_fraction=30%` (`+0.547`), `age=70` (`+0.493`), `high_blood_pressure=1` (`+0.264`), `anaemia=1` (`+0.228`), `serum_sodium=134` (`+0.147`), `serum_creatinine=1.6` (`+0.132`).
   - **ANN IG discrepancy:** While ANN captures `age` (`+0.691`) and `ef` (`+0.687`), notice `smoking=0` gets `-0.317` logit push and `high_blood_pressure=1` gets `+0.429` (nearly `3x` `serum_creatinine=1.6`'s `+0.142`!).
3. **`Female_Hypertensive_Moderate`** (`LR Prob = 0.337`, `ANN Prob = 0.246`):
   - **Notable ANN sign flip:** On this female profile (`diabetes=0, smoking=0`), ANN assigns **`anaemia=1` a massive `+0.626` logit boost** (`2.5x` LR's `+0.228`), while assigning `diabetes=0` `-0.240` and `smoking=0` `-0.374`. When `smoking` switches from `0 -> 1` on this profile, ANN mortality risk leaps by **`+29.1 percentage points`** (`0.246 -> 0.538`), compared to a **decrease** (`0.103 -> 0.086`) on the median male profile!
4. **`High_Risk_Critical`** (`LR Prob = 0.932`, `ANN Prob = 0.911`):
   - Both models strongly flag acute cardiorenal decompensation (`ef=20%`: `LR +1.224`, `ANN IG +1.155`; `age=75`: `LR +0.763`, `ANN IG +0.698`; `cr=2.5`: `LR +0.707`, `ANN IG +0.342`). Notice ANN under-weights `serum_creatinine=2.5` relative to `smoking=1` (`+0.395`)!

---

## 4. Limitations of Both Explainability Paradigms

- **LR Linear Assumption:** LR enforces global additivity in log-odds space and cannot directly represent true synergistic clinical thresholds (e.g., severe EF reduction combined with acute kidney injury) unless interaction terms are explicitly engineered.
- **ANN Attribution Instability:** Because `HeartFailureANN` is over-parameterized (`2,881` params for `N ≈ 200`), Integrated Gradients attributions shift substantially with random initialization seeds and small sample perturbations, inflating noisy binary comorbidities (`smoking`, `diabetes`, `anaemia`) above continuous physiological markers (`serum_sodium`, `CPK`).
