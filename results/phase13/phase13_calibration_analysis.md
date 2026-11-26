# Phase 13 — Probability Calibration & Reliability Analysis

**Project:** Heart Failure Mortality Risk Predictor — CardioPredict Clinical Portal  
**Phase:** Phase 13 — Phase 9 Probability Calibration Analysis (Research-Only)  
**Evaluation Regime:** Strict 5-Fold Stratified Leak-Free Out-of-Fold (`N = 299`, `DEATH_EVENT`: 96 deaths / 203 survivors; `SEED = 42`)  

---

## 1. Executive Summary

Across genuinely unseen out-of-fold patients (`N = 299`), **Logistic Regression produces substantially better-calibrated probability estimates than the 2,881-parameter ANN (`11 -> 64 -> 32 -> 1`)**:
- **Brier Score:** LR **`0.1778`** vs ANN **`0.2053`** (paired bootstrap difference $-0.0276$, 95% CI $[-0.0405, -0.0152]$; LR wins in **41 / 50** repeated 5×10 CV folds).
- **Log Loss (Cross-Entropy):** LR **`0.5438`** vs ANN **`0.6190`** (paired bootstrap difference $-0.0753$, 95% CI $[-0.1197, -0.0369]$; LR wins in **38 / 50** repeated folds).
- **Expected Calibration Error (10 bins):** LR **`0.0414`** vs ANN **`0.1033`** (2.5× larger calibration error for ANN).
- **Calibration Slope:** LR **`0.7509`** vs ANN **`0.4791`** (ideal = `1.000`). An ANN slope of `0.479` indicates severe probability overconfidence / extreme logit spread on unseen patients.

Post-hoc inner-fold recalibration (`Platt Scaling` and `Isotonic Regression` fit strictly inside the 20% inner validation splits, `N ≈ 48` per fold) **failed to make ANN competitive** with uncalibrated LR and caused Isotonic Regression to severely overfit and explode out-of-fold Log Loss (`1.1072` for LR, `1.5445` for ANN).

---

## 2. Out-of-Fold Calibration Comparison Table

All metrics computed on concatenated out-of-fold predictions (`N = 299`) with **zero outer-fold calibration leakage**:

| Model / Calibration Strategy | AUROC | Brier Score $\downarrow$ | Log Loss $\downarrow$ | ECE (10-bin) $\downarrow$ | MCE (10-bin) $\downarrow$ | CITL (Ideal 0) | Cal Slope (Ideal 1) | Cal Intercept |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **LR (Uncalibrated, 239 outer-train)** | **0.7595** | **0.1778** | **0.5438** | **0.0414** | 0.2871 | **-0.0061** | **0.7509** | **-0.1612** |
| LR (Uncalibrated, 191 inner-80 train) | 0.7338 | 0.1847 | 0.5625 | 0.0435 | 0.3611 | +0.0287 | 0.6977 | -0.1744 |
| LR + Inner-Fold Platt Scaling | 0.7287 | 0.1904 | 0.5835 | 0.0753 | **0.2457** | -0.0308 | 0.5677 | -0.2951 |
| LR + Inner-Fold Isotonic Regression | 0.7309 | 0.1974 | 1.1072 | 0.1126 | 0.3519 | +0.0943 | 0.1248 | -0.5405 |
| **ANN (Uncalibrated, `11->64->32->1`)** | 0.6935 | 0.2053 | 0.6190 | 0.1033 | 0.2758 | +0.0279 | 0.4791 | -0.3107 |
| ANN + Inner-Fold Platt Scaling | 0.6967 | 0.2059 | 0.6119 | 0.0910 | 0.3573 | -0.0470 | 0.5072 | -0.3388 |
| ANN + Inner-Fold Isotonic Regression | 0.6792 | 0.2243 | 1.5445 | 0.1241 | 0.3789 | -0.0576 | 0.0824 | -0.6921 |

*(Note: CITL = Calibration-In-The-Large; $\downarrow$ indicates lower is better.)*

---

## 3. Clinical & Statistical Interpretation

1. **Calibration-in-the-Large (Mean Risk Alignment):**
   - Observed cohort mortality rate is **32.11%** (`96 / 299`).
   - LR shows virtually zero systematic global bias ($\text{CITL} = -0.0061$).
   - ANN exhibits slight global drift ($\text{CITL} = +0.0279$), but its primary defect lies in **extreme spread (Calibration Slope = `0.4791`)**.

2. **Why Does ANN Have Calibration Slope `0.4791`?**
   - Calibration slope $< 1.0$ means predicted probabilities are too extreme: low-risk predictions are pushed too close to `0.0` and high-risk predictions are pushed too close to `1.0` relative to actual event frequencies.
   - Because `HeartFailureANN` contains **2,881 learnable parameters** fitted on only `~191` inner training samples (after the 20% inner validation holdout), it achieves very low training loss by pushing network logits outward.
   - On unseen patients, those extreme logits generate sharp errors that are heavily penalized by Log Loss (`0.6190` vs LR `0.5438`) and Brier Score (`0.2053` vs LR `0.1778`).

3. **Why Did Inner-Fold Post-Hoc Calibration Fail on `N ≈ 48`?**
   - **Isotonic Regression:** Non-parametric step-function fitting on `~48` inner validation samples (~15 events) memorizes small-sample noise and produces `0.0` or `1.0` boundary predictions for extreme test patients, causing catastrophic out-of-fold Log Loss inflation (`1.1072` for LR, `1.5445` for ANN).
   - **Platt Scaling:** Logistic recalibration on `N ≈ 48` adds parameter estimation noise rather than stabilization; it slightly helps ANN (`ECE 0.1033 -> 0.0910`, `LogLoss 0.6190 -> 0.6119`), yet calibrated ANN still lags uncalibrated LR by `+0.0681` in Log Loss and `+0.0281` in Brier Score.

4. **Visual Evidence:**
   - See [fig03_calibration_curves.png](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig03_calibration_curves.png) for the 8-quantile reliability diagram and predicted probability histograms. Notice LR's predicted probabilities stay concentrated in calibrated mid-ranges aligned with the empirical risk curve, whereas ANN exhibits wide, under-calibrated spread toward the tails.

5. **Production Artifacts Note (Non-Unseen Reference):**
   - On the full cohort (`N=299`), `models/ann_model.pth` reports an optimistic apparent Brier score of `0.1296` and slope of `1.298` strictly because `239` of those patients were its exact training records and the remaining `60` Fold-4 patients guided its early-stopping and checkpoint selection (`training/train_ann.py`). Apparent in-sample calibration metrics do **not** reflect unseen patient reliability.
