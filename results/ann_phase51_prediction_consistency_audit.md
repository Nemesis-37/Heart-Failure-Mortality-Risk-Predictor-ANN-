# Phase 5.1: Final Prediction Consistency & Threshold Evaluation Audit

**Project:** Heart Failure Mortality Risk Predictor  
**Date:** November 2026  
**Status:** Audit Completed — Authoritative Research Reconciled  
**Scope:** Forensic Verification of Arch B Prediction Consistency, Threshold Methodology, Data Leakage Assessment, and Aggregation Mathematics  

---

## 1. Executive Summary

This audit evaluates the numerical and methodological consistency between the canonical **Phase 4.1 Cross-Phase Reproducibility Audit** and the **Phase 5 Final Model Selection & Fixed-Threshold Assessment**. 

Specifically, this audit addresses:
1. **The Arch B Threshold 0.50 Discrepancy:** Why Phase 4.1 reported an uncalibrated sensitivity of **39.68%** and specificity of **88.17%**, whereas Phase 5 reported **42.84%** sensitivity and **88.18%** specificity.
2. **Fixed-Threshold Provenance and Leakage:** Whether candidate decision thresholds ($0.30, 0.33, 0.35, 0.40, 0.50$) were derived independently of outer-test labels, and whether their evaluations are truly leakage-safe or exploratory.
3. **Metric Aggregation Audit:** A mathematical reconciliation of fold-averaged metrics versus pooled out-of-fold metrics across all five stratified folds.
4. **Data Integrity:** Verification that ground-truth positive ($N=96$) and negative ($N=203$) patient counts are strictly preserved across every fold and threshold.

---

## 2. Forensic Investigation: Arch B Threshold 0.50 Discrepancy

### 2.1 The Observed Discrepancy

In the canonical Phase 4.1 report (`results/ann_phase41_threshold_audit.csv`), Arch B at threshold 0.50 was reported with:
- **Sensitivity:** $39.68\% \pm 11.24\%$
- **Specificity:** $88.17\% \pm 5.85\%$
- **AUROC:** $76.11\% \pm 6.21\%$
- **Mean TP:** $7.60$, **Mean FP:** $4.80$, **Mean TN:** $35.80$, **Mean FN:** $11.60$

In Phase 5 (`results/ann_phase5_fixed_threshold_assessment.csv`), Arch B at threshold 0.50 was reported with:
- **Sensitivity:** $42.84\% \pm 12.40\%$
- **Specificity:** $88.18\% \pm 7.41\%$
- **AUROC:** $76.42\% \pm 6.23\%$
- **Mean TP:** $8.20$, **Mean FP:** $4.80$, **Mean TN:** $35.80$, **Mean FN:** $11.00$

### 2.2 Forensic Component Verification

Every potential failure mode was systematically audited:

| Audit Dimension | Canonical Phase 4.1 (`training/phase3_optimization.py`) | Phase 5 (`scripts/evaluate_phase5_fixed_thresholds.py`) | Status | Impact on Discrepancy |
| :--- | :--- | :--- | :--- | :--- |
| **Outer Fold Splits** | `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` | `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` | **IDENTICAL** | None (Identical patient indices in all folds) |
| **Logistic Regression Benchmark** | Fold 1: TP=6, FP=6, TN=34, FN=14<br>Fold 2: TP=8, FP=6, TN=35, FN=11<br>Fold 3: TP=11, FP=7, TN=34, FN=8<br>Fold 4: TP=10, FP=1, TN=40, FN=9<br>Fold 5: TP=11, FP=3, TN=37, FN=8<br>**Mean Sens: 48.11%, Spec: 88.67%** | Fold 1: TP=6, FP=6, TN=34, FN=14<br>Fold 2: TP=8, FP=6, TN=35, FN=11<br>Fold 3: TP=11, FP=7, TN=34, FN=8<br>Fold 4: TP=10, FP=1, TN=40, FN=9<br>Fold 5: TP=11, FP=3, TN=37, FN=8<br>**Mean Sens: 48.11%, Spec: 88.67%** | **EXACT 100% MATCH** | None. Proves that dataset loading, CV partitioning, and baseline pipelines are perfectly consistent. |
| **Arch B Model Architecture** | 11 $\to$ 16 $\to$ 1, ReLU, Dropout=0.2 | 11 $\to$ 16 $\to$ 1, ReLU, Dropout=0.2 | **IDENTICAL** | None (209 parameters) |
| **Optimizer & Loss** | Adam (lr=0.001, wd=0.01), BCEWithLogitsLoss | Adam (lr=0.001, wd=0.01), BCEWithLogitsLoss | **IDENTICAL** | None |
| **Preprocessing & Scaling** | `StandardScaler().fit_transform(X_train)` strictly inside outer fold | `StandardScaler().fit_transform(X_train)` strictly inside outer fold | **IDENTICAL** | None (Zero data leakage) |
| **Comparison Operator** | `(probabilities >= threshold).astype(int)` | `(probabilities >= threshold).astype(int)` | **IDENTICAL** | None (Inclusive `>= 0.50` used in both) |
| **Aggregation Formula** | Macro fold-average: $(\sum_{k=1}^5 \text{Metric}_k) / 5$ | Macro fold-average: $(\sum_{k=1}^5 \text{Metric}_k) / 5$ | **IDENTICAL** | None |
| **Mini-batch Generation & Data Slicing** | PyTorch native `DataLoader(..., generator=torch.Generator().manual_seed(seed))` | NumPy manual permutation: `b_idx = np.random.permutation(n_samples)[i:i+batch_size]` | **DIVERGENT** | **ROOT CAUSE OF NUMERICAL SHIFT** |

### 2.3 Detailed Fold-by-Fold Confusion Matrix Comparison

Comparison of fold-by-fold confusion matrix counts for Arch B at threshold 0.50:

| Fold | $N_{\text{pos}}$ | $N_{\text{neg}}$ | Phase 4.1 Canonical [TP, FP, TN, FN] | Phase 5 Refit [TP, FP, TN, FN] | Patient Discrepancy ($\Delta$) | Sensitivity (P4.1 vs P5) | Specificity (P4.1 vs P5) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | 20 | 40 | [6, 6, 34, 14] | [6, 6, 34, 14] | **0 patients** (Identical) | 30.00% vs 30.00% | 85.00% vs 85.00% |
| **Fold 2** | 19 | 41 | [6, 6, 35, 13] | [6, 5, 36, 13] | 1 negative case moved FP $\to$ TN | 31.58% vs 31.58% | 85.37% vs 87.80% |
| **Fold 3** | 19 | 41 | [8, 7, 34, 11] | [10, 9, 32, 9] | 2 positive cases moved FN $\to$ TP;<br>2 negative cases moved TN $\to$ FP | 42.11% vs 52.63% | 82.93% vs 78.05% |
| **Fold 4** | 19 | 41 | [11, 1, 40, 8] | [11, 1, 40, 8] | **0 patients** (Identical) | 57.89% vs 57.89% | 97.56% vs 97.56% |
| **Fold 5** | 19 | 40 | [7, 4, 36, 12] | [8, 3, 37, 11] | 1 positive case moved FN $\to$ TP;<br>1 negative case moved FP $\to$ TN | 36.84% vs 42.11% | 90.00% vs 92.50% |
| **Mean** | **19.2** | **40.6** | **[7.60, 4.80, 35.80, 11.60]** | **[8.20, 4.80, 35.80, 11.00]** | **Net +3 TPs across 299 patients** | **39.68% vs 42.84%** | **88.17% vs 88.18%** |

### 2.4 Root Cause Analysis and Conclusion

1. **Mechanism of Divergence:**
   In small-sample deep learning ($N=239$ training instances per fold), Adam optimization with mini-batch stochastic gradient descent is sensitive to the exact order of samples within mini-batches.
   In Phase 3 / Phase 4.1, mini-batch shuffling was generated via PyTorch's `torch.Generator().manual_seed(seed)`. In Phase 5, mini-batch indices were generated via NumPy's `np.random.permutation(n_samples)`.
   Even though the initial seed was identical (seed 42 + fold), PyTorch's native pseudo-random generator and NumPy's PRNG create different random permutations. This induced slight trajectory differences in the loss surface.
2. **Clinical Significance of Divergence:**
   The difference between 39.68% and 42.84% represents a net shift of only **3 positive patients** ($1.0\%$ of the total cohort of 299 patients) crossing the $0.50$ decision boundary (2 patients in Fold 3, 1 patient in Fold 5).
   Meanwhile, the net number of false positives across the entire dataset remained exactly identical (24 FP total in both runs).
3. **Definitive Canonical Decision:**
   **The canonical Phase 4.1 results remain the frozen, authoritative research benchmark.**
   Phase 5 is formally classified as an independent re-execution audit. It proves that the Arch B architecture is numerically stable within $\pm 3.16\%$ sensitivity and $\pm 0.01\%$ specificity under PRNG variation, but it does **not** replace the canonical Phase 4.1 metrics.

---

## 3. Fixed-Threshold Methodology Audit

### 3.1 Provenance of Candidate Thresholds

Candidate decision thresholds evaluated in Phase 5 ($0.30, 0.33, 0.35, 0.40, 0.50$) were derived as follows:

| Threshold | Name / Type | Derivation Source | Outer Label Leakage? | Methodological Status |
| :---: | :--- | :--- | :---: | :--- |
| **0.50** | Conventional Default | Standard symmetric default cutoff ($P \ge 0.50$). | **No** | Baseline Reference (Pre-specified) |
| **0.33** | Prevalence-Aligned & Youden | Cohort base rate ($96/299 = 32.11\%$) and Phase 3 inner-fold Youden index average (LR = 0.33, Arch B = 0.33). | **No** | Empirical Research Candidate (Prevalence-informed) |
| **0.30** | Sensitivity-Prioritizing Youden | Phase 3 inner-fold Youden index average for Arch C (0.30). | **No** | Exploratory Benchmark Cutoff |
| **0.35** | Harmonic Balance (F1) | Phase 3 inner-fold F1-optimal cutoff average for Arch B (0.35). | **No** | Exploratory Benchmark Cutoff |
| **0.40** | Intermediate Moderate-Risk | Operational midpoint between prevalence-aligned (0.33) and default (0.50). | **No** | Exploratory Benchmark Cutoff |

### 3.2 Leakage-Safe Evaluation vs Exploratory Sweeps

A crucial methodological distinction must be maintained:
- **Truly Leakage-Safe Nested Evaluation:** When a decision threshold is derived strictly inside each training fold (e.g., using inner cross-validation on $X_{\text{train\_inner}}$) and evaluated once on the untouched outer test fold, the evaluation is free of optimistic threshold-selection bias. This was executed in Phase 3.
- **Pre-Specified Fixed-Threshold Evaluation:** When a single threshold (such as 0.50, or a base-rate cutoff of 0.32) is fixed *a priori* before observing test data, applying it to outer test folds is unbiased and leakage-safe.
- **Exploratory Threshold Sweeps:** Evaluating a grid of five candidate thresholds across outer test folds provides an informative empirical characterization of the clinical trade-off curve. However, selecting a "winning" threshold *after* observing the outer test metrics constitutes post-hoc selection. Therefore, Phase 5's fixed-threshold results must be interpreted as an **exploratory operating-curve benchmark**, not as a pre-registered clinical trial endpoint.

---

## 4. Metric Aggregation Audit: Fold-Averaged vs Pooled

Both Phase 3 and Phase 5 evaluated models using 5-fold stratified cross-validation. Metrics can be aggregated in two distinct mathematical ways:
1. **Fold-Averaged (Macro):** Compute the metric on each fold independently, then take the arithmetic mean:
   $$\text{Sens}_{\text{macro}} = \frac{1}{K}\sum_{k=1}^K \text{Sens}_k$$
2. **Pooled (Micro / Out-of-Fold Concatenation):** Concatenate the out-of-fold binary predictions and ground-truth labels across all $N=299$ patients to form a single global confusion matrix:
   $$\text{Sens}_{\text{pooled}} = \frac{\sum_{k=1}^K \text{TP}_k}{\sum_{k=1}^K (\text{TP}_k + \text{FN}_k)} = \frac{\text{TP}_{\text{total}}}{96}$$

### 4.1 Mathematical Comparison Across Models and Thresholds

| Model | Threshold | Execution Source | Fold-Averaged Sensitivity | Pooled Sensitivity | Fold-Averaged Specificity | Pooled Specificity | Pooled Confusion Matrix [TP, FP, TN, FN] |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | **0.30** | Phase 5 Refit | 71.16% | 70.83% | 68.01% | 67.98% | [68, 65, 138, 28] |
| **Logistic Regression** | **0.30** | Canonical Phase 4.1 | 71.16% | 70.83% | 68.01% | 67.98% | [68, 65, 138, 28] |
| **Logistic Regression** | **0.33** | Phase 5 Refit | 64.84% | 64.58% | 71.48% | 71.43% | [62, 58, 145, 34] |
| **Logistic Regression** | **0.35** | Phase 5 Refit | 64.84% | 64.58% | 74.95% | 74.88% | [62, 51, 152, 34] |
| **Logistic Regression** | **0.40** | Phase 5 Refit | 59.63% | 59.38% | 80.83% | 80.79% | [57, 39, 164, 39] |
| **Logistic Regression** | **0.50** | Phase 5 Refit | 48.11% | 47.92% | 88.67% | 88.67% | [46, 23, 180, 50] |
| **Logistic Regression** | **0.50** | Canonical Phase 4.1 | 48.11% | 47.92% | 88.67% | 88.67% | [46, 23, 180, 50] |
| **Arch B (16 $\to$ 1)** | **0.30** | Phase 5 Refit | 74.21% | 73.96% | 66.54% | 66.50% | [71, 68, 135, 25] |
| **Arch B (16 $\to$ 1)** | **0.30** | Canonical Phase 4.1 | 75.16% | 75.00% | 64.56% | 64.53% | [72, 72, 131, 24] |
| **Arch B (16 $\to$ 1)** | **0.33** | Phase 5 Refit | 69.00% | 68.75% | 71.50% | 71.43% | [66, 58, 145, 30] |
| **Arch B (16 $\to$ 1)** | **0.35** | Phase 5 Refit | 62.79% | 62.50% | 72.49% | 72.41% | [60, 56, 147, 36] |
| **Arch B (16 $\to$ 1)** | **0.35** | Canonical Phase 4.1 | 65.89% | 65.62% | 70.99% | 70.94% | [63, 59, 144, 33] |
| **Arch B (16 $\to$ 1)** | **0.40** | Phase 5 Refit | 57.53% | 57.29% | 76.89% | 76.85% | [55, 47, 156, 41] |
| **Arch B (16 $\to$ 1)** | **0.50** | Phase 5 Refit | 42.84% | 42.71% | 88.18% | 88.18% | [41, 24, 179, 55] |
| **Arch B (16 $\to$ 1)** | **0.50** | Canonical Phase 4.1 | **39.68%** | **39.58%** | **88.17%** | **88.18%** | **[38, 24, 179, 58]** |
| **Arch C (32 $\to$ 16 $\to$ 1)** | **0.50** | Phase 5 Refit | 49.21% | 48.96% | 86.20% | 86.21% | [47, 28, 175, 49] |
| **Arch C (32 $\to$ 16 $\to$ 1)** | **0.50** | Canonical Phase 4.1 | 47.11% | 46.88% | 86.18% | 86.21% | [45, 28, 175, 51] |

### 4.2 Aggregation Insights

Because the folds are balanced ($N=60, 60, 60, 60, 59$ and positive cases $N_{\text{pos}}=20, 19, 19, 19, 19$), the difference between fold-averaged and pooled sensitivity is less than **0.33%** across all models and thresholds. 
- For Logistic Regression at 0.50, fold-averaged sensitivity is **48.11%** while pooled sensitivity is **47.92%** ($46/96$).
- For Arch B canonical at 0.50, fold-averaged sensitivity is **39.68%** while pooled sensitivity is **39.58%** ($38/96$).
- Both methods reflect the exact same clinical reality: at threshold 0.50, Arch B misses 58 out of 96 mortality events (a 60.4% false negative rate), which confirms why threshold optimization is clinically essential.

---

## 5. Data Integrity Audit

A comprehensive verification was conducted across all 135 rows in `results/ann_phase51_fold_confusion_matrices.csv`:
1. **Positive Ground Truth Integrity:** In every row, $\text{TP} + \text{FN}$ equals exactly $20$ for Fold 1 and $19$ for Folds 2–5.
2. **Negative Ground Truth Integrity:** In every row, $\text{TN} + \text{FP}$ equals exactly $40$ for Fold 1 and Fold 5, and $41$ for Folds 2–4.
3. **Total Patient Preservation:** Across all 5 folds, $\sum (\text{TP} + \text{FP} + \text{TN} + \text{FN}) = 299$ patients without omission or duplicate entries.

Every entry in the confusion matrix audit passed strict integrity verification.
