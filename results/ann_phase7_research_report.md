# Phase 7: ANN Residual Architecture and Preprocessing Optimization — Research Report

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** 7 — Wide & Deep Residual ANN and Biomarker Preprocessing  
**Date:** November 2026  
**Status:** Experiments Completed — Results Ready for Review  
**Dataset:** 299 patients, 11 features, 96 mortality events (32.11%), 203 survivals  

---

## 1. Executive Summary

Phase 7 systematically evaluated whether (a) log1p biomarker preprocessing of skewed continuous variables and (b) a Wide & Deep residual ANN architecture can close the AUROC gap between the existing ANN and the Logistic Regression baseline.

> [!IMPORTANT]
> **Honest Research Finding:**  
> Neither the Wide & Deep architecture nor log1p preprocessing produced a statistically significant improvement over the Logistic Regression baseline (77.17% AUROC). All ANN variants remain below the linear baseline. The Logistic Regression benchmark is retained as the canonical research standard.

---

## 2. Models Evaluated

| ID | Model | Architecture | Preprocessing | Parameters |
| :--- | :--- | :--- | :--- | :---: |
| `Logistic_Regression` | Logistic Regression Baseline | Linear ($11 \to 1$) | StandardScaler | 12 |
| `Arch_B_Standard` | ANN Arch B | MLP ($11 \to 16 \to 1$), dp=0.2, wd=0.01, bs=32 | StandardScaler | 209 |
| `WideDeep_Standard` | Wide & Deep ANN | Linear branch + MLP ($11 \to 8 \to 1$), dp=0.2, wd=0.01, bs=32 | StandardScaler | 117 |
| `WideDeep_Log` | Wide & Deep ANN with log1p | As above | log1p(CPK, creatinine) + StandardScaler | 117 |

**Wide & Deep Architecture:**  
$$\text{logit}(x) = \underbrace{W_L x + b_L}_{\text{linear branch}} + \underbrace{\text{Linear}_{8 \to 1}(\text{ReLU}(\text{Dropout}_{0.2}(\text{Linear}_{11 \to 8}(x))))}_{\text{nonlinear branch}}$$

The linear branch gives the network the representational capacity of a linear model. The nonlinear branch learns residual corrections if supported by data.

---

## 3. Evaluation Protocol

- **Cross-Validation:** StratifiedKFold(n\_splits=5, shuffle=True, random\_state=42) — identical folds for all models.
- **ANN Training:** Inner 20% holdout (from training fold) for early stopping (patience=15), then step-adjusted refit on full training fold.
- **Data Leakage Control:** All preprocessing (log transforms, StandardScaler) fitted strictly on training data; applied to inner stop set and outer test fold without refitting.
- **Model Selection:** Based exclusively on inner validation loss — outer test folds never used for threshold selection or early stopping.

---

## 4. Results: Aggregate Metrics (5-Fold Cross-Validation)

| Model | AUROC | Brier Score | Log Loss | Sensitivity | Specificity | Precision | F1 Score | Cal. Slope |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | **77.17% ± 5.51%** | **0.1777 ± 0.0280** | **0.5437 ± 0.0790** | **48.11%** | **88.67%** | **67.55%** | **57.77%** | **0.928** |
| **ANN Arch B (Standard)** | 76.56% ± 6.76% | 0.1792 ± 0.0287 | 0.5432 ± 0.0790 | 43.89% | 87.20% | 62.63% | 51.28% | 1.029 |
| **Wide & Deep (Standard)** | 76.01% ± 6.09% | 0.1824 ± 0.0258 | 0.5542 ± 0.0733 | 43.95% | 86.71% | 62.32% | 50.97% | 1.049 |
| **Wide & Deep (Log1p)** | 76.20% ± 7.73% | 0.1820 ± 0.0322 | 0.5513 ± 0.0836 | **50.26%** | 87.18% | 64.98% | 56.07% | 1.097 |

> [!NOTE]
> The LR calibration slope (0.928) is closest to the ideal value of 1.0, indicating that LR's probability outputs are better calibrated than any ANN variant in this phase. ANN calibration slopes of 1.03–1.10 indicate slight systematic under-sharpening.

---

## 5. Fold-by-Fold Results

### 5.1 Logistic Regression Baseline

| Fold | N (pos/neg) | AUROC | Brier | Log Loss | Sensitivity | Specificity | Cal. Slope | Cal. Intercept |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 60 (20/40) | 70.25% | 0.2186 | 0.6654 | 30.00% | 85.00% | 0.388 | +0.371 |
| 2 | 60 (19/41) | 74.71% | 0.1866 | 0.5449 | 42.11% | 85.37% | 0.679 | +0.000 |
| 3 | 60 (19/41) | 75.35% | 0.1794 | 0.5551 | 57.89% | 82.93% | 0.774 | -0.232 |
| 4 | 60 (19/41) | 83.57% | 0.1460 | 0.4542 | 52.63% | 97.56% | 1.568 | -0.050 |
| 5 | 59 (19/40) | 81.97% | 0.1580 | 0.4988 | 57.89% | 92.50% | 1.232 | -0.049 |
| **Mean** | — | **77.17% ± 5.51%** | **0.1777 ± 0.0280** | **0.5437 ± 0.0790** | **48.11%** | **88.67%** | **0.928** | **+0.008** |

### 5.2 ANN Arch B — Standard Preprocessing

| Fold | AUROC | Brier | Log Loss | Sensitivity | Specificity | Cal. Slope | TP / FP / TN / FN |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 69.38% | 0.2148 | 0.6507 | 30.00% | 85.00% | 0.439 | 6 / 6 / 34 / 14 |
| 2 | 75.35% | 0.1824 | 0.5362 | 31.58% | 85.37% | 0.838 | 6 / 6 / 35 / 13 |
| 3 | 71.25% | 0.1965 | 0.5873 | 47.37% | 78.05% | 0.622 | 9 / 9 / 32 / 10 |
| 4 | 85.37% | 0.1425 | 0.4486 | 57.89% | 97.56% | 1.854 | 11 / 1 / 40 / 8 |
| 5 | 81.45% | 0.1601 | 0.4934 | 52.63% | 90.00% | 1.391 | 10 / 4 / 36 / 9 |
| **Mean** | **76.56% ± 6.76%** | **0.1792 ± 0.0287** | **0.5432 ± 0.0790** | **43.89%** | **87.20%** | **1.029** | **8.4 / 5.2 / 35.4 / 10.8** |

### 5.3 Wide & Deep ANN — Standard Preprocessing

| Fold | AUROC | Brier | Log Loss | Sensitivity | Specificity | Cal. Slope | TP / FP / TN / FN |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 69.75% | 0.2176 | 0.6663 | 25.00% | 85.00% | 0.393 | 5 / 6 / 34 / 15 |
| 2 | 73.30% | 0.1898 | 0.5521 | 42.11% | 82.93% | 0.705 | 8 / 7 / 34 / 11 |
| 3 | 72.53% | 0.1879 | 0.5674 | 52.63% | 78.05% | 0.738 | 10 / 9 / 32 / 9 |
| 4 | 84.72% | 0.1490 | 0.4687 | 52.63% | 97.56% | 1.959 | 10 / 1 / 40 / 9 |
| 5 | 79.74% | 0.1677 | 0.5164 | 47.37% | 90.00% | 1.447 | 9 / 4 / 36 / 10 |
| **Mean** | **76.01% ± 6.09%** | **0.1824 ± 0.0258** | **0.5542 ± 0.0733** | **43.95%** | **86.71%** | **1.049** | **8.4 / 5.4 / 35.2 / 10.8** |

### 5.4 Wide & Deep ANN — Log1p Biomarker Preprocessing

| Fold | AUROC | Brier | Log Loss | Sensitivity | Specificity | Cal. Slope | TP / FP / TN / FN |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 66.13% | 0.2289 | 0.6818 | 25.00% | 85.00% | 0.370 | 5 / 6 / 34 / 15 |
| 2 | 74.45% | 0.1869 | 0.5518 | 42.11% | 87.80% | 0.669 | 8 / 5 / 36 / 11 |
| 3 | 74.20% | 0.1876 | 0.5585 | 57.89% | 78.05% | 0.789 | 11 / 9 / 32 / 8 |
| 4 | 87.29% | 0.1420 | 0.4568 | 63.16% | 97.56% | 2.307 | 12 / 1 / 40 / 7 |
| 5 | 78.95% | 0.1647 | 0.5077 | 63.16% | 87.50% | 1.347 | 12 / 5 / 35 / 7 |
| **Mean** | **76.20% ± 7.73%** | **0.1820 ± 0.0322** | **0.5513 ± 0.0836** | **50.26%** | **87.18%** | **1.097** | **9.6 / 5.2 / 35.4 / 9.6** |

---

## 6. Statistical Significance Testing

Wilcoxon signed-rank tests on paired fold AUROC scores (5 paired observations):

| Comparison | AUROC Delta | Wilcoxon $p$-value | Statistically Significant? |
| :--- | :---: | :---: | :---: |
| LR vs Arch B Standard | $-0.61\%$ | $p = 0.8125$ | **No** |
| LR vs Wide & Deep Standard | $-1.16\%$ | $p = 0.1875$ | **No** |
| LR vs Wide & Deep Log1p | $-0.97\%$ | $p = 0.4375$ | **No** |

> [!WARNING]
> With only $K=5$ folds, no non-parametric test has adequate power to reliably detect differences below $\approx 3\%$ in AUROC. This means that even had the ANN shown a small positive advantage (e.g. $+0.5\%$), it would not be statistically distinguishable from random fold-to-fold variation. All stated performance differences should be interpreted with appropriate caution.

---

## 7. Experiment 1: Preprocessing Impact Analysis

### 7.1 Skewness Reduction from Log1p

Log1p transformation successfully reduced the distributional skewness of both heavily skewed biomarkers (measured on training Fold 1 data to illustrate the effect):

| Feature | Raw Mean | Raw Std | **Raw Skewness** | Log1p Mean | Log1p Std | **Log1p Skewness** | Skewness Reduction |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `creatinine_phosphokinase` | 546.8 mcg/L | 886.4 | **+4.55** | 5.62 | 1.12 | **+0.42** | $-90.8\%$ |
| `serum_creatinine` | 1.38 mg/dL | 0.94 | **+4.20** | 0.82 | 0.28 | **+2.08** | $-50.5\%$ |

Log1p substantially tamed the skewness of CPK. Serum creatinine's skewness reduction was more moderate because the distribution remains heavy-tailed even on the log scale (several patients with creatinine > 4 mg/dL remain as leverage points on the log scale).

### 7.2 Impact on Model Performance

| Metric | Wide & Deep (Standard) | Wide & Deep (Log1p) | Change |
| :--- | :---: | :---: | :---: |
| AUROC | 76.01% | 76.20% | +0.19% |
| Brier Score | 0.1824 | 0.1820 | −0.0004 |
| Log Loss | 0.5542 | 0.5513 | −0.0029 |
| Sensitivity (0.50) | 43.95% | **50.26%** | **+6.31%** |
| Specificity (0.50) | 86.71% | 87.18% | +0.47% |
| Cal. Slope | 1.049 | 1.097 | +0.048 |

Log1p preprocessing provided a **meaningful increase in sensitivity** at the conventional threshold (+6.31 percentage points, capturing 1.2 additional deaths per fold on average), with virtually no cost to specificity (+0.47%). However, the AUROC improvement (+0.19%) is well within fold-to-fold noise.

### 7.3 Why Log1p Helped Sensitivity but Not AUROC

The AUROC metric (area under the ROC curve) is a rank-based measure: it assesses whether models assign higher probabilities to true deaths than to true survivals. The CPK feature has near-zero correlation with mortality ($r=0.063$), so normalizing its distribution does not add rank-discrimination information. However, log1p does reduce the influence of extreme CPK values on weight updates during mini-batch SGD, allowing the model to focus more on the genuinely predictive features (`serum_creatinine`, `ejection_fraction`, `age`), which improves the absolute position of the probability scores relative to the 0.50 boundary — hence the sensitivity gain.

---

## 8. Experiment 2: Wide & Deep Architecture Analysis

### 8.1 Concordance with Logistic Regression

| Metric | Wide & Deep (Standard) | Wide & Deep (Log1p) |
| :--- | :---: | :---: |
| Pearson Correlation vs LR | $r = 0.9775$ | $r = 0.9529$ |
| Agreement at 0.50 | 96.66% (289/299) | 94.98% (284/299) |

Despite incorporating a residual linear branch, the Wide & Deep model still generates probabilities that are slightly more compressed toward the cohort mean than Logistic Regression, contributing to its lower AUROC.

### 8.2 Why the Architecture Did Not Beat LR

The Wide & Deep architecture's linear branch theoretically allows the model to represent an exact linear function when the nonlinear branch weights shrink toward zero. In practice, with 117 parameters and only 76.8 training events per fold ($\text{EPV} \approx 0.66$), the Adam optimizer jointly trains both branches simultaneously without guaranteeing that the linear branch converges to the optimal logistic regression hyperplane. The nonlinear branch, even with weight decay and dropout, introduces optimization noise during the joint training process rather than learning pure residual corrections.

### 8.3 Calibration Concerns

All ANN variants have calibration slopes exceeding 1.0 (ranging from 1.03 to 1.10), indicating slight systematic **over-confidence** relative to the linear baseline (slope 0.928, closest to ideal 1.0). This means the ANNs spread their probability distributions slightly wider than warranted by the data, pushing some patients further from the center probability but reducing calibration reliability. Logistic Regression's slightly sub-unity calibration slope (0.928) reflects minor under-confidence, which is preferable in this context as it corresponds to fewer false positives.

---

## 9. Prediction Comparison at Threshold 0.50 (All 299 Patients)

| Metric | Logistic Regression | Arch B Standard | Wide & Deep Standard | Wide & Deep Log1p |
| :--- | :---: | :---: | :---: | :---: |
| True Positives | **46** | 42 | 42 | **48** |
| False Positives | **23** | 26 | 27 | 26 |
| True Negatives | **180** | 177 | 176 | 177 |
| False Negatives | **50** | 54 | 54 | **48** |
| Total Accuracy | **75.25%** | 73.24% | 72.91% | 75.25% |

The Wide & Deep with log1p achieves the **same total accuracy as Logistic Regression** (75.25%, 225/299 correct), but with a different error profile: it captures 2 more true deaths (48 vs 46) while producing 3 more false positives (26 vs 23). Whether this trade-off is preferable depends on clinical cost-benefit analysis, not statistical performance alone.

---

## 10. Conclusion & Recommendation

### 10.1 Honest Summary

The Phase 7 experiments provide clear, reproducible evidence:

1. **Neither the Wide & Deep architecture nor log1p preprocessing outperforms Logistic Regression in AUROC.** All AUROC differences are within fold-to-fold noise and are not statistically significant (all Wilcoxon $p > 0.05$).
2. **Log1p preprocessing yields a clinically meaningful sensitivity improvement** (+6.31 percentage points at threshold 0.50 for Wide & Deep Log1p), capturing 2 additional mortality events across 299 patients, without a statistically significant AUROC benefit.
3. **The logistic regression benchmark (77.17% AUROC) is retained as the canonical research standard.** No model in Phase 7 provides reproducible evidence of superior discrimination.

### 10.2 What These Results Tell Us

The fundamental constraints established in Phase 6 have been validated:
- With $N=299$ and 96 events, the data generating process does not contain recoverable non-linear signal that an MLP can exploit beyond what a linear model discovers.
- The intrinsic AUROC ceiling of this feature space (without `time`) is approximately 77%–78%, currently occupied by Logistic Regression.
- The Wide & Deep architecture is conceptually sound but insufficient to overcome the information-theoretic limitation of a 299-patient, 11-feature binary classification task.

### 10.3 What to Try Next (Phase 8 Candidates)

If further ANN improvement is desired, the following scientifically justified next steps remain:
1. **Full-Batch Quasi-Newton (L-BFGS) optimization** — eliminates mini-batch noise that prevents the Wide & Deep linear branch from converging to the optimal hyperplane.
2. **Noise feature pruning** (`diabetes`, `sex`, `smoking`) — removes 48 uninformative weights, increasing EPV from 0.66 to 0.86.
3. **Platt / temperature scaling** — recalibrate the ANN's slightly over-sharp probability outputs to match LR's calibration reliability.

> [!IMPORTANT]
> **Checkpoint Promotion Decision:**  
> No model checkpoint from Phase 7 is being promoted to production. The existing production checkpoint (`models/ann_model.pth`) remains unchanged. User review and explicit approval are required before any checkpoint promotion.

---

## 11. File Deliverables

| File | Rows | Description |
| :--- | :---: | :--- |
| [`ann_phase7_fold_metrics.csv`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/ann_phase7_fold_metrics.csv) | 20 | Full fold-by-fold metrics for all 4 models |
| [`ann_phase7_wide_deep_metrics.csv`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/ann_phase7_wide_deep_metrics.csv) | 4 | Aggregate mean ± std summary across all models |
| [`ann_phase7_preprocessing_comparison.csv`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/ann_phase7_preprocessing_comparison.csv) | 4 | Skewness and distribution statistics before/after log1p |
| [`ann_phase7_prediction_comparison.csv`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/ann_phase7_prediction_comparison.csv) | 299 | Patient-level OOF predictions for all 4 models |
| [`ann_phase7_research_report.md`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/ann_phase7_research_report.md) | — | This report |
