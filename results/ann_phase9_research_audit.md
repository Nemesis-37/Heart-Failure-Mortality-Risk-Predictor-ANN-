# Phase 9.1 — Research Results Reconciliation & Historical Audit Report

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** 9.1 — Research Results Reconciliation  
**Date:** November 2026  
**Dataset:** 299 patients · 11 features (excluding `time`) · 96 mortality events (32.11%) · 203 survivals  
**Cross-Validation:** 5-Fold StratifiedKFold(n_splits=5, shuffle=True, random_state=42)  

---

## 1. Objective & Scope

This audit reconciles all experimental metrics, model architectures, training configurations, and artifacts produced across Phases 1 through 8. The goal is to establish an unambiguous, evidence-backed audit trail distinguishing:
1. **The Canonical Logistic Regression Benchmark** (frozen, authoritative production standard).
2. **The Canonical ANN Arch B Benchmark** (Phase 4.1 frozen baseline).
3. **Independently Refitted Experimental ANN Variants** (Phases 1, 2, 7, and 8).
4. **The Experimental Matched 8-Feature Models** (Phase 8 feature ablation candidates).

---

## 2. Cross-Phase Reconciliation Matrix

The table below reconciles all key models across the research lifecycle. All evaluations share the exact same 299 patient records, outer fold boundaries, and target distribution ($N_{\text{pos}}=96, N_{\text{neg}}=203$).

| Phase / Exp ID | Model Architecture | Features | Optimizer & Hyperparameters | Preprocessing | AUROC (Mean ± Std) | Brier Score | Log Loss | Sensitivity (0.50) | Specificity (0.50) | Calibration Slope | Status / Classification |
|:---|:---|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **Canonical LR** | Linear (11 $\to$ 1) | 11 | L-BFGS (sklearn, $C=1.0$) | StandardScaler | **77.17% ± 5.51%** | **0.1777** | **0.5437** | 48.11% | **88.67%** | **0.928** | **CANONICAL_ESTABLISHED_BENCHMARK** |
| **Phase 4.1 Arch B** | MLP (11 $\to$ 16 $\to$ 1) | 11 | Adam ($lr=10^{-3}$, $bs=32$, $wd=0.01$) | StandardScaler | 76.11% ± 6.21% | 0.1804 | 0.5415 | 39.68% | 88.17% | 1.029 | **CANONICAL_ANN_BENCHMARK** |
| **Phase 1 Corrected**| MLP (11 $\to$ 16 $\to$ 1) | 11 | Adam ($lr=10^{-3}$, $bs=32$, $wd=0.01$) | StandardScaler | 75.80% ± 7.02% | 0.1812 | 0.5480 | 42.84% | 88.18% | 1.035 | Historical Refit (PRNG shift noted in 5.1) |
| **Phase 2 Arch C** | MLP (11 $\to$ 32 $\to$ 16 $\to$ 1) | 11 | Adam ($lr=10^{-3}$, $bs=64$, $wd=0.001$)| StandardScaler | 74.87% ± 6.88% | 0.1872 | 0.5712 | 41.84% | 86.71% | 1.140 | Overfitting Diagnosed (EPV=0.08) |
| **Phase 7 WD Standard**| Linear(11,1) + MLP(11 $\to$ 8 $\to$ 1)| 11 | Adam ($lr=10^{-3}$, $bs=32$, $wd=0.01$) | StandardScaler | 76.01% ± 6.09% | 0.1824 | 0.5542 | 43.95% | 86.71% | 1.049 | Experimental Residual Evaluation |
| **Phase 7 WD Log1p** | Linear(11,1) + MLP(11 $\to$ 8 $\to$ 1)| 11 | Adam ($lr=10^{-3}$, $bs=32$, $wd=0.01$) | log1p + StandardScaler | 76.20% ± 7.73% | 0.1820 | 0.5513 | **50.26%** | 87.18% | 1.097 | Skewness Reduction Evaluation |
| **Phase 8 WD L-BFGS**| Linear(11,1) + MLP(11 $\to$ 8 $\to$ 1)| 11 | Full-Batch L-BFGS ($lr=0.5$) | StandardScaler | 76.71% ± 6.29% | 0.1791 | 0.5486 | 47.00% | 86.71% | 0.895 | Best 11-Feature ANN |
| **Phase 8 WD Log L-BFGS**| Linear(11,1) + MLP(11 $\to$ 8 $\to$ 1)| 11 | Full-Batch L-BFGS ($lr=0.5$) | log1p + StandardScaler | 76.59% ± 7.45% | 0.1804 | 0.5428 | 45.05% | 85.73% | 0.927 | Best Calibrated ANN |
| **Phase 8 Ablated ANN**| Linear(8,1) + MLP(8 $\to$ 8 $\to$ 1) | 8 | Full-Batch L-BFGS ($lr=0.5$) | log1p + StandardScaler | **77.68% ± 7.17%** | **0.1758** | **0.5320** | 46.11% | 87.20% | 0.946 | **EXPERIMENTAL_RESEARCH_CANDIDATE** |
| **Phase 8 Matched LR**| Linear (8 $\to$ 1) | 8 | L-BFGS (sklearn, $C=1.0$) | StandardScaler | **78.10% ± 5.85%** | **0.1731** | **0.5295** | 48.11% | **89.17%** | **0.952** | **EXPERIMENTAL_MATCHED_CONTROL** |

---

## 3. Historical Discrepancy Reconciliation

During historical auditing (Phase 4.1 and Phase 5.1), slight numerical discrepancies were identified and fully resolved:

### 3.1 Arch B Sensitivity at Threshold 0.50 (39.68% vs 42.84%)
- **Root Cause:** In Phase 5, mini-batch shuffling was seeded via standard Python/NumPy RNG, whereas Phase 4.1 used PyTorch's native `torch.Generator().manual_seed()`. On a dataset with only 96 positive cases (~19 per fold), a single borderline patient shifting across the 0.50 boundary produces a 5.26 pp change in fold sensitivity ($1 / 19 = 5.26\%$). Across 5 folds, a net shift of 3 patients accounted for the difference.
- **Resolution:** As established in Phase 5.1, the **Phase 4.1 canonical metrics (Sensitivity 39.68%, Specificity 88.17%, AUROC 76.11%)** are frozen as the authoritative baseline for Arch B.

### 3.2 Standard Deviation Metric Reporting (Sample vs Population)
- **Root Cause:** Historical scripts occasionally computed fold standard deviation using `np.std(ddof=0)` (population standard deviation, $\sigma = 4.92\%$) while others used `ddof=1` (sample standard deviation, $s = 5.51\%$).
- **Resolution:** Both figures are recorded. For 5-fold cross-validation, sample standard deviation ($ddof=1$, $s=5.51\%$) is reported throughout Phase 7–9 summaries for conservative scientific reporting.

---

## 4. Methodological Compliance & Anti-Leakage Safeguards

All reconciled experiments strictly adhered to anti-leakage principles:
1. **Outer Folds Untouched:** All scalers (`StandardScaler`), logarithmic transformations (`log1p`), and post-hoc calibration models were fitted **strictly on training fold data**. Outer test folds were transformed using previously fitted parameters.
2. **Early Stopping Isolation:** Neural network early stopping decisions were made using an internal 20% validation split carve-out from the training fold, never touching outer test observations.
3. **Refit Step Calculation:** When models were refit on full training folds, step counts were scaled proportionally ($\text{refit\_steps} = \text{best\_steps} \times N_{\text{train}} / N_{\text{sub}}$) to prevent overfitting.
4. **Deterministic Reproducibility:** Stratified splits used `random_state=42` across all phases.

---

## 5. Audit Deliverable File
The machine-readable metric inventory is persisted in:
[`results/ann_phase9_metric_reconciliation.csv`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/ann_phase9_metric_reconciliation.csv)
