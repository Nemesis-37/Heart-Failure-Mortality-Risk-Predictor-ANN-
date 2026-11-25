# Phase 9.2 — Matched 8-Feature Experiment Audit

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** 9.2 — Matched Feature Experiment Audit  
**Date:** November 2026  
**Focus:** Strict Comparison of Pruned 8-Feature ANN vs Pruned 8-Feature Logistic Regression  

---

## 1. Audit Context & Scientific Question

In Phase 8 Experiment 2, pruning three uninformative biomarkers (`diabetes`, `sex`, `smoking`) raised the Wide & Deep ANN's cross-validation AUROC from 76.59% to **77.68% ± 7.17%**, surpassing the canonical 11-feature Logistic Regression baseline (77.17% ± 5.51%).

This audit investigated the critical scientific question:
> *Did the 8-feature ANN achieve a genuine breakthrough through non-linear feature interaction, or was the improvement purely an artifact of linear feature selection that benefits linear models equally or more?*

---

## 2. Experimental Rigor & Alignment Verification

We verified that the 8-feature ANN (`WD_LBFGS_Ablation_NoNoise`) and the 8-feature Logistic Regression (`LR_Matched_8Feature`) were evaluated under **strictly identical experimental conditions**:

| Audit Parameter | Verification Check | Status | Evidence |
|:---|:---|:---:|:---|
| **Outer Folds** | Identical 5 outer folds | ✅ Verified | StratifiedKFold(n_splits=5, shuffle=True, random_state=42) |
| **Patient Rows** | Exactly identical patient indices | ✅ Verified | Outer test splits identical: Fold 1 (60), Fold 2 (60), Fold 3 (60), Fold 4 (60), Fold 5 (59) |
| **Target Distribution** | Exactly identical death events | ✅ Verified | Fold 1 (20/40), Fold 2 (19/41), Fold 3 (19/41), Fold 4 (19/41), Fold 5 (19/40) |
| **Features Kept** | Identical 8 features | ✅ Verified | `['age', 'anaemia', 'creatinine_phosphokinase', 'ejection_fraction', 'high_blood_pressure', 'platelets', 'serum_creatinine', 'serum_sodium']` |
| **Features Removed** | Identical 3 noise features | ✅ Verified | `['diabetes', 'sex', 'smoking']` removed from both models |
| **Preprocessing Isolation** | Fitted on training folds only | ✅ Verified | Scalers and log transforms fitted on `X_train` only; applied to `X_test` |
| **Evaluation Metrics** | Identical metric aggregation | ✅ Verified | Fold-level AUROC, Brier score, Log Loss, Sensitivity, Specificity computed identically |

---

## 3. Matched Head-to-Head Performance Comparison

### 3.1 Aggregate Performance Across All 5 Folds

| Metric | Logistic Regression (11 Features - Canonical) | Wide & Deep ANN (8 Features - Pruned) | Logistic Regression (8 Features - Pruned) | Winner (8-Feature Space) |
|:---|:---:|:---:|:---:|:---:|
| **AUROC (Mean ± Std)** | 77.17% ± 5.51% | 77.68% ± 7.17% | **78.10% ± 5.85%** | **Logistic Regression (+0.42 pp)** |
| **Brier Score (Mean)** | 0.1777 | 0.1758 | **0.1731** | **Logistic Regression (-0.0027)** |
| **Log Loss (Mean)** | 0.5437 | 0.5320 | **0.5295** | **Logistic Regression (-0.0025)** |
| **Sensitivity (0.50)** | 48.11% | 46.11% | **48.11%** | **Logistic Regression (+2.00 pp)** |
| **Specificity (0.50)** | 88.67% | 87.20% | **89.17%** | **Logistic Regression (+1.97 pp)** |
| **Parameter Count** | 12 | 90 | **9** | **Logistic Regression (10x smaller)** |

### 3.2 Fold-by-Fold Matched Paired Comparison

| Fold | Test Size (Pos/Neg) | LR (11 Features) | ANN (8 Features) | LR (8 Features) | Paired Delta (ANN 8 - LR 8) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **Fold 1** | 60 (20/40) | 70.25% | 71.62% | **72.12%** | -0.50 pp |
| **Fold 2** | 60 (19/41) | 74.71% | 74.20% | **74.84%** | -0.64 pp |
| **Fold 3** | 60 (19/41) | 75.35% | 72.02% | **73.04%** | -1.02 pp |
| **Fold 4** | 60 (19/41) | 83.57% | **87.42%** | 86.80% | +0.62 pp |
| **Fold 5** | 59 (19/40) | 81.97% | 83.16% | **83.68%** | -0.52 pp |
| **Mean** | — | **77.17%** | **77.68%** | **78.10%** | **-0.42 pp** |

---

## 4. Paired Statistical Significance Testing

Wilcoxon signed-rank tests were performed on the paired fold AUROC values across the identical 5 folds:

| Paired Comparison | AUROC Delta | Wilcoxon Statistic | $p$-value | Statistically Significant? | Interpretation |
|:---|:---:|:---:|:---:|:---:|:---|
| **ANN (8 feat) vs LR (11 feat)** | +0.51 pp | $W = 6.0$ | $p = 0.6250$ | ❌ No | Improvement over 11-feat baseline is not statistically significant. |
| **ANN (8 feat) vs LR (8 feat)** | -0.42 pp | $W = 6.0$ | $p = 0.6250$ | ❌ No | In matched 8-feature space, ANN is lower than LR; difference is within noise. |
| **LR (8 feat) vs LR (11 feat)** | +0.93 pp | $W = 5.0$ | $p = 0.4375$ | ❌ No | Feature pruning benefits LR more than ANN, but power at $K=5$ is limited. |

> [!WARNING]
> **Statistical Caution:**
> A non-significant $p$-value ($p = 0.6250$) does **not** prove equivalence or superiority. It proves that the observed performance difference cannot be distinguished from random fold-to-fold variation in a sample of $N=299$. Claims of model superiority cannot be scientifically supported.

---

## 5. Audit Conclusions & Scientific Finding

1. **The Apparent ANN Breakthrough is Refuted:** The 8-feature Wide & Deep ANN (77.68% AUROC) does not outperform Logistic Regression when evaluated under matched feature conditions. Logistic Regression on the same 8 features achieves **78.10% AUROC**, **0.1731 Brier score**, and **0.5295 Log Loss**, beating the ANN across every single metric.
2. **Mechanism of Action:** Pruning `diabetes`, `sex`, and `smoking` increases Events-Per-Variable (EPV) from 8.7 to 12.0 for LR, and from 0.66 to 0.85 for the ANN. This benefits linear regression by reducing estimation variance on uninformative weights. The ANN's non-linear branch adds no incremental predictive value.
3. **Deployment Recommendation:** The 8-feature Wide & Deep ANN remains classified as an **experimental research candidate**. It must **not** be deployed or promoted to replace the established production models.
