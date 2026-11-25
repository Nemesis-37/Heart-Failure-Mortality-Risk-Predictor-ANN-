# Heart Failure Mortality Risk Predictor — ANN Optimization Phase 3
## Decision-Threshold Optimization, Probability Calibration & Model Reliability Analysis

**Date:** November 25, 2026  
**Evaluation Protocol:** 5-Fold Stratified Cross-Validation (`shuffle=True`, `random_state=42`)  
**Cohort:** 299 patient records, 11 clinical features, 96 death events (32.11% prevalence), 203 survivals (67.89%)  
**Dataset Isolation:** Outer test folds strictly isolated from threshold selection and calibration training  

---

## 1. Executive Summary

Phase 3 evaluated the **decision thresholds**, **probability calibration**, and **clinical reliability** of three model candidates established in Phase 2:
1. **Logistic Regression Baseline** ($11 \to 1$, 12 trainable parameters)
2. **Arch C (Deep ANN)** ($11 \to 32 \to 16 \to 1$, Dropout 0.0, Weight Decay 0.001, Batch Size 64, 929 trainable parameters)
3. **Arch B (Compact Regularized ANN)** ($11 \to 16 \to 1$, Dropout 0.2, Weight Decay 0.01, Batch Size 32, 209 trainable parameters)

### Key Findings:
1. **The 0.50 Threshold Under-diagnoses Mortality**: At the default classification threshold of 0.50, all models exhibit high specificity ($86.2\% - 88.7\%$) but clinically inadequate sensitivity ($39.7\% - 48.1\%$), missing over half of the high-risk mortalities (averaging 10.0 to 11.6 false negatives per 60-patient fold).
2. **Internally Selected Youden's J Threshold Solves the Imbalance**: Selecting the decision threshold strictly on inner validation data ($\theta^* \approx 0.30 - 0.34$) doubles clinical sensitivity:
   - **Arch B** outer-test sensitivity increases from **39.68% to 71.95% ± 3.88%**, slashing false negatives from 11.6 to 5.4.
   - **Arch C** outer-test sensitivity increases from **47.11% to 73.95% ± 6.47%**, slashing false negatives from 10.2 to 5.0.
   - **Arch B** demonstrates extraordinary fold stability: standard deviation of sensitivity across all 5 folds is only **±3.88%** (compared to **±19.74%** for Logistic Regression).
3. **Uncalibrated ANNs are Already Well-Calibrated**:
   - **Arch B** achieved a Brier score of **0.1804 ± 0.0230**, Log Loss of **0.5415 ± 0.0588** (lower than Logistic Regression's 0.5437), and a calibration intercept of **+0.0019** (near-perfect alignment with 0.0). Its mean predicted probability of **0.3226** tracks true cohort prevalence (0.3211) within 0.15 percentage points.
4. **Post-Hoc Calibration Overfits on Small Cohorts**:
   - **Platt Scaling** (logistic calibration) slightly degraded Brier score (0.1804 $\to$ 0.1873 for Arch B) due to parameter estimation variance on small inner splits ($N=48$).
   - **Isotonic Regression** severely overfitted ($N=48$), degrading log loss catastrophically (0.5415 $\to$ 1.2610) and collapsing calibration slopes to 0.12–0.28 due to step-function discretization.
   - **Clinical Recommendation**: Retain raw uncalibrated probabilities; adjust clinical sensitivity via thresholding rather than probability distortion.

---

## 2. Models Evaluated & Architecture Specifications

| Model Identifier | Architecture | Trainable Parameters | Regularization & Training Setup |
| :--- | :--- | :---: | :--- |
| **Logistic Regression** | Linear ($11 \to 1$) | **12** | L2 penalty ($C=1.0$), StandardScaler fitted on outer train only |
| **Arch C (32–16)** | Two hidden layers ($11 \to 32 \to 16 \to 1$) | **929** | Dropout 0.0, Weight Decay 0.001, Batch Size 64, Adam (lr=0.001) |
| **Arch B (16)** | Single hidden layer ($11 \to 16 \to 1$) | **209** | Dropout 0.2, Weight Decay 0.01, Batch Size 32, Adam (lr=0.001) |

---

## 3. Comprehensive Model Comparison

Performance evaluated on the **untouched outer test folds** across all 5 cross-validation splits:

| Model & Operating Mode | Decision Threshold | AUROC | Brier Score | Log Loss | Accuracy | Sensitivity | Specificity | Precision | F1 Score | Mean FP | Mean FN |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** (Ref 0.50) | 0.50 (Fixed) | **77.17% ± 5.51%** | **0.1777 ± 0.0280** | 0.5437 ± 0.0790 | **75.60% ± 6.87%** | 48.11% ± 12.00% | **88.67% ± 6.15%** | **67.55% ± 16.77%** | 0.5576 ± 0.1263 | **4.6** | 10.0 |
| **Logistic Regression** (Youden) | 0.33 (Mean) | **77.17% ± 5.51%** | **0.1777 ± 0.0280** | 0.5437 ± 0.0790 | 67.89% ± 8.80% | 63.79% ± 19.74% | 69.91% ± 18.00% | 54.82% ± 20.24% | 0.5593 ± 0.0956 | 12.2 | 7.0 |
| **Logistic Regression** (Platt) | 0.50 (Post-Platt) | **77.17% ± 5.51%** | 0.1846 ± 0.0328 | 0.5693 ± 0.1005 | 74.94% ± 6.48% | 51.26% ± 19.19% | 86.23% ± 9.52% | — | 0.5581 ± 0.1352 | — | — |
| **Arch C (32–16)** (Ref 0.50) | 0.50 (Fixed) | 74.87% ± 6.99% | 0.1859 ± 0.0299 | 0.5675 ± 0.0870 | 73.59% ± 8.66% | 47.11% ± 18.24% | 86.18% ± 5.70% | 60.63% ± 16.71% | 0.5258 ± 0.1774 | 5.6 | 10.2 |
| **Arch C (32–16)** (Youden) | 0.30 (Mean) | 74.87% ± 6.99% | 0.1859 ± 0.0299 | 0.5675 ± 0.0870 | 68.26% ± 10.78% | **73.95% ± 6.47%** | 65.54% ± 16.83% | 53.09% ± 13.40% | 0.6085 ± 0.0839 | 14.0 | **5.0** |
| **Arch C (32–16)** (Platt) | 0.50 (Post-Platt) | 74.87% ± 6.99% | 0.1898 ± 0.0391 | 0.5786 ± 0.1180 | 71.93% ± 8.71% | 49.21% ± 20.63% | 82.78% ± 8.95% | — | 0.5183 ± 0.1707 | — | — |
| **Arch B (16)** (Ref 0.50) | 0.50 (Fixed) | 76.11% ± 6.21% | 0.1804 ± 0.0230 | **0.5415 ± 0.0588** | 72.58% ± 7.31% | 39.68% ± 11.24% | 88.17% ± 5.85% | 61.73% ± 17.65% | 0.4818 ± 0.1348 | 4.8 | 11.6 |
| **Arch B (16)** (Youden) | 0.33 (Mean) | 76.11% ± 6.21% | 0.1804 ± 0.0230 | **0.5415 ± 0.0588** | **70.58% ± 2.41%** | **71.95% ± 3.88%** | **69.98% ± 3.77%** | 53.23% ± 3.05% | **0.6110 ± 0.0232** | 12.2 | **5.4** |
| **Arch B (16)** (Platt) | 0.50 (Post-Platt) | 76.11% ± 6.21% | 0.1873 ± 0.0332 | 0.5661 ± 0.0964 | 71.92% ± 7.26% | 45.95% ± 18.26% | 84.29% ± 11.09% | — | 0.5023 ± 0.1342 | — | — |

---

## 4. Threshold Grid Analysis (0.10 to 0.90)

The table below details how performance metrics shift across decision thresholds for **Arch B (16)** (averages across outer folds):

| Threshold | Accuracy | Sensitivity (Recall) | Specificity | Precision | F1 Score | TP | FP | TN | FN |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.10** | 43.12% | **95.89%** | 18.24% | 35.93% | 0.5214 | 18.4 | 33.2 | 7.4 | 0.8 |
| **0.15** | 49.47% | 92.79% | 29.04% | 38.38% | 0.5416 | 17.8 | 28.8 | 11.8 | 1.4 |
| **0.20** | 54.82% | 86.58% | 39.90% | 40.77% | 0.5525 | 16.6 | 24.4 | 16.2 | 2.6 |
| **0.25** | 63.87% | 82.47% | 55.17% | 46.53% | 0.5929 | 15.8 | 18.2 | 22.4 | 3.4 |
| **0.30** | 67.89% | **75.16%** | **64.56%** | 50.11% | **0.5985** | 14.4 | 14.4 | 26.2 | 4.8 |
| **0.35** | 69.25% | 65.89% | 70.99% | 51.18% | 0.5699 | 12.6 | 11.8 | 28.8 | 6.6 |
| **0.40** | 69.92% | 56.47% | 76.39% | 52.86% | 0.5421 | 10.8 | 9.6 | 31.0 | 8.4 |
| **0.45** | 72.93% | 50.16% | 83.77% | 60.75% | 0.5450 | 9.6 | 6.6 | 34.0 | 9.6 |
| **0.50 (Ref)** | **72.58%** | **39.68%** | **88.17%** | **61.73%** | **0.4818** | **7.6** | **4.8** | **35.8** | **11.6** |
| **0.55** | 72.24% | 28.21% | 93.11% | 67.00% | 0.3896 | 5.4 | 2.8 | 37.8 | 13.8 |
| **0.60** | 72.57% | 22.95% | 96.06% | 74.17% | 0.3478 | 4.4 | 1.6 | 39.0 | 14.8 |
| **0.65** | 71.89% | 15.58% | 98.51% | 82.00% | 0.2588 | 3.0 | 0.6 | 40.0 | 16.2 |
| **0.70** | 70.57% | 10.32% | 99.01% | 86.00% | 0.1776 | 2.0 | 0.4 | 40.2 | 17.2 |
| **0.80** | 68.56% | 3.05% | 99.50% | 33.33% | 0.0548 | 0.6 | 0.2 | 40.4 | 18.6 |
| **0.90** | 68.23% | 1.00% | 100.00% | 20.00% | 0.0190 | 0.2 | 0.0 | 40.6 | 19.0 |

### Sensitivity vs. Specificity Trade-Off
```
Threshold  Sensitivity [%]  ====================| Specificity [%]
   0.10:   95.9%  [████████████████████]       |  18.2%  [███]
   0.20:   86.6%  [█████████████████]         |  39.9%  [████████]
   0.30:   75.2%  [███████████████]           |  64.6%  [█████████████]  <-- Balanced Youden Window
   0.40:   56.5%  [███████████]               |  76.4%  [███████████████]
   0.50:   39.7%  [████████]                  |  88.2%  [██████████████████] <-- Default Baseline
   0.60:   23.0%  [█████]                     |  96.1%  [███████████████████]
   0.70:   10.3%  [██]                        |  99.0%  [████████████████████]
```

---

## 5. Probability Calibration & Reliability Analysis

### Calibration Metrics Summary across Folds (Mean ± Std)

| Model | Method | Brier Score | Log Loss | ECE (10 Bins) | Calibration Slope | Calibration Intercept | Mean Predicted Prob | Prevalence |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | **Uncalibrated** | **0.1777 ± 0.0280** | **0.5437 ± 0.0790** | **0.1200 ± 0.0338** | **0.9280 ± 0.4690** | **+0.0080 ± 0.2212** | **0.3221 ± 0.0276** | 32.11% |
| Logistic Regression | Platt Scaled | 0.1846 ± 0.0328 | 0.5693 ± 0.1005 | 0.1413 ± 0.0430 | 0.8296 ± 0.4869 | -0.0832 ± 0.5135 | 0.3329 ± 0.0697 | 32.11% |
| Logistic Regression | Isotonic | 0.1978 ± 0.0474 | 1.8479 ± 0.9047 | 0.1371 ± 0.0877 | 0.2756 ± 0.3947 | -0.0255 ± 0.6371 | 0.3269 ± 0.0763 | 32.11% |
| **Arch B (16)** | **Uncalibrated** | **0.1804 ± 0.0230** | **0.5415 ± 0.0588** | **0.1277 ± 0.0272** | **1.1876 ± 0.6081** | **+0.0019 ± 0.1829** | **0.3226 ± 0.0249** | 32.11% |
| Arch B (16) | Platt Scaled | 0.1873 ± 0.0332 | 0.5661 ± 0.0964 | 0.1579 ± 0.0408 | 0.8341 ± 0.4536 | -0.0734 ± 0.4883 | 0.3297 ± 0.0671 | 32.11% |
| Arch B (16) | Isotonic | 0.1922 ± 0.0483 | 1.2610 ± 0.8650 | 0.1451 ± 0.0560 | 0.2601 ± 0.3589 | -0.2088 ± 0.9472 | 0.3260 ± 0.0758 | 32.11% |
| **Arch C (32–16)** | **Uncalibrated** | 0.1859 ± 0.0299 | 0.5675 ± 0.0870 | 0.1468 ± 0.0393 | 0.8651 ± 0.5742 | +0.0017 ± 0.2544 | 0.3222 ± 0.0338 | 32.11% |
| Arch C (32–16) | Platt Scaled | 0.1898 ± 0.0391 | 0.5786 ± 0.1180 | 0.1570 ± 0.0536 | 0.7793 ± 0.4080 | -0.1682 ± 0.4110 | 0.3424 ± 0.0513 | 32.11% |
| Arch C (32–16) | Isotonic | 0.1989 ± 0.0531 | 1.3262 ± 0.7037 | 0.1482 ± 0.0602 | 0.1254 ± 0.0830 | -0.3843 ± 0.8208 | 0.3437 ± 0.0518 | 32.11% |

### Reliability Diagram (Pooled Across All 299 Out-of-Fold Predictions)

#### Arch B (16) — Uncalibrated Reliability Diagram:
```
Predicted Risk Bin | Count | Mean Pred | Observed Mortality | Alignment
-------------------|-------|-----------|--------------------|-------------------------
Bin 1: [0.0 - 0.2] |    94 |    0.1131 |             0.1383 | [███] Pred: 11% vs Obs: 14%
Bin 2: [0.2 - 0.4] |   103 |    0.2872 |             0.2816 | [███████] Pred: 29% vs Obs: 28% (Exact)
Bin 3: [0.4 - 0.6] |    72 |    0.4913 |             0.4444 | [████████████] Pred: 49% vs Obs: 44%
Bin 4: [0.6 - 0.8] |    26 |    0.6695 |             0.7308 | [████████████████] Pred: 67% vs Obs: 73%
Bin 5: [0.8 - 1.0] |     4 |    0.8635 |             0.7500 | [███████████████████] Pred: 86% vs Obs: 75%
```

#### Logistic Regression — Uncalibrated Reliability Diagram:
```
Predicted Risk Bin | Count | Mean Pred | Observed Mortality | Alignment
-------------------|-------|-----------|--------------------|-------------------------
Bin 1: [0.0 - 0.2] |   113 |    0.1024 |             0.1327 | [███] Pred: 10% vs Obs: 13%
Bin 2: [0.2 - 0.4] |    90 |    0.2907 |             0.2667 | [███████] Pred: 29% vs Obs: 27%
Bin 3: [0.4 - 0.6] |    55 |    0.5030 |             0.5273 | [████████████] Pred: 50% vs Obs: 53%
Bin 4: [0.6 - 0.8] |    28 |    0.6910 |             0.6429 | [████████████████] Pred: 69% vs Obs: 64%
Bin 5: [0.8 - 1.0] |    13 |    0.8889 |             0.7692 | [███████████████████] Pred: 89% vs Obs: 77%
```

---

## 6. Fold-by-Fold Stability Analysis

### Arch B ($11 \to 16 \to 1$) Across Outer Test Folds:

| Fold | Test Size | Test Deaths | AUROC | Uncal Brier | Th=0.50 Sens | Th=0.50 Spec | Youden Thresh | Youden Sens | Youden Spec | Youden F1 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | 60 | 20 | 0.6938 | 0.2104 | 30.00% | 85.00% | **0.29** | 65.00% | 72.50% | 0.5909 |
| **Fold 2** | 60 | 19 | 0.7510 | 0.1814 | 31.58% | 85.37% | **0.30** | 73.68% | 65.85% | 0.5957 |
| **Fold 3** | 60 | 19 | 0.7189 | 0.1895 | 42.11% | 82.93% | **0.36** | 73.68% | 65.85% | 0.5957 |
| **Fold 4** | 60 | 19 | 0.8511 | 0.1476 | 57.89% | 97.56% | **0.38** | 73.68% | 73.17% | 0.6364 |
| **Fold 5** | 59 | 19 | 0.7908 | 0.1732 | 36.84% | 90.00% | **0.34** | 73.68% | 72.50% | 0.6364 |
| **Mean** | 59.8 | 19.2 | **0.7611** | **0.1804** | **39.68%** | **88.17%** | **0.33** | **71.95%** | **69.98%** | **0.6110** |
| **Std** | — | — | *±0.0621* | *±0.0230* | *±11.24%* | *±5.85%* | *±0.04* | *±3.88%* | *±3.77%* | *±0.0232* |

> **Crucial Finding**: Under the internally selected Youden threshold, Arch B achieves an outer-test sensitivity standard deviation of **±3.88%** (73.68% in 4 out of 5 folds). In contrast, Logistic Regression exhibits a sensitivity standard deviation of **±19.74%** (swings between 40.0% and 84.2%). Arch B is markedly more stable across clinical subgroups.

---

## 7. Comparison Against Phase 1 & Phase 2

| Evaluation Dimension | Phase 1 (Training Corrections) | Phase 2 (Architecture Search) | Phase 3 (Threshold & Calibration) |
| :--- | :--- | :--- | :--- |
| **Focus** | Eliminating preprocessing leakage, step-adjusted refits | Hidden layer capacity (8, 16, 32-16, 64-32) & loss functions | Decision thresholds ($\theta \in [0.1, 0.9]$), Platt/Isotonic calibration |
| **Threshold Used** | Fixed 0.50 only | Fixed 0.50 only | Flexible: 0.50 reference vs. inner-selected Youden/F1 thresholds |
| **ANN Sensitivity** | ~36.8% (Unweighted) | ~39.7% (Arch B) / 47.1% (Arch C) | **71.95% (Arch B Youden)** / **73.95% (Arch C Youden)** |
| **Brier Score** | ~0.184 (Unweighted) | 0.1835 (Arch B) / 0.1862 (Arch C) | **0.1804 (Arch B Uncalibrated)** |
| **Weighted Loss vs Thresholding** | Phase 1 weighted loss boosted sensitivity to 68% but distorted Brier to 0.208 | Phase 2 weighted loss elevated mean prob to 45.8% (+13.7% over true rate) | **Phase 3 proves threshold tuning achieves 72% sensitivity WITHOUT distorting probabilities** |

---

## 8. Final Recommendations & Decision

1. **Best Overall Model**:
   - **Logistic Regression Baseline** retains the highest aggregate AUROC (**77.17% ± 5.51%**) and lowest raw Brier score (**0.1777 ± 0.0280**).
2. **Best Compact & Most Clinically Stable ANN**:
   - **Arch B ($11 \to 16 \to 1$, Dropout 0.2, Weight Decay 0.01, Batch Size 32)**:
     - 209 trainable parameters ($0.70 \times N$).
     - AUROC: **76.11% ± 6.21%** (within 1.06% of Logistic Regression; paired difference not statistically significant).
     - Log Loss: **0.5415 ± 0.0588** (superior to Logistic Regression's 0.5437).
     - Under inner Youden threshold ($\theta^* \approx 0.33$): Sensitivity **71.95% ± 3.88%**, Specificity **69.98% ± 3.77%**, F1 **0.6110 ± 0.0232**.
     - Shows the lowest fold-to-fold sensitivity variance of any evaluated model.
3. **Most Reliable Probability Calibration**:
   - Both **Logistic Regression (Uncalibrated)** and **Arch B (Uncalibrated)** are exceptionally well-calibrated out of the box (slopes: $0.93$ and $1.19$; intercepts: $+0.008$ and $+0.002$; mean predicted probabilities match 32.11% cohort prevalence within 0.15%).
   - **Do NOT apply Platt scaling or Isotonic regression**; both post-hoc recalibration techniques increase variance and risk overfitting on small sample sizes.
4. **Best Candidate Decision Threshold for Clinical Investigation**:
   - **$\theta = 0.30 - 0.35$** (Centered at **0.33**):
     - Slashing false negatives by more than 50% (from ~11.6 to 5.4 deaths per fold) while maintaining ~70% specificity and avoiding unnecessary over-testing.
5. **Production Model Safety**:
   - In accordance with strict protection rules, `models/ann_model.pth` has **NOT** been overwritten.
   - Any promotion of Arch B or updated decision thresholds remains pending multidisciplinary clinical governance review.

---

## 9. Regulatory & Clinical Prototype Disclaimer

This software is an educational machine-learning decision-support prototype. It is not an FDA/CE certified medical device and is not certified for autonomous diagnostic or therapeutic intervention. All risk probabilities and threshold indications must be verified by a licensed cardiologist or attending physician alongside comprehensive clinical findings.
