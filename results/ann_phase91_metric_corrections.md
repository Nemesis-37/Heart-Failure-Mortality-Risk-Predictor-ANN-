# Phase 9.1 — Historical Metric Reconciliation & Arch C Clarification Report

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** 9.1 — Final Deployment Consistency Audit  
**Date:** November 2026  
**Subject:** Precise Attribution and Provenance of Historical Arch C Experimental Metrics  

---

## 1. Executive Summary

During Phase 9 audit activities, a discrepancy in reported Arch C metrics was identified between historical Phase 2 and Phase 3 summary tables:
- Some reports cited Arch C with **76.75% AUROC** (Phase 2 best tuned).
- Other tables cited Arch C with **75.35% AUROC** (Phase 2 architecture search baseline).
- Phase 3, Phase 4.1, and Phase 9 tables cited Arch C with **74.87% AUROC**.

This audit examined the original artifact CSVs and training scripts to trace the exact experimental conditions, hyperparameters, and cross-validation procedures for each figure.

---

## 2. Arch C Variant Provenance & Attribution Matrix

All variants below share the identical $11 \to 32 \to 16 \to 1$ layer architecture (**929 parameters**) and 5-fold cross-validation split (seed 42), but differ in hyperparameter tuning and refitting procedures:

| Designation | Exact Experiment File | Hyperparameters | Outer Refit Method | AUROC (Mean ± Std) | Brier Score | Log Loss | Specificity | Role / Provenance |
|:---|:---|:---|:---|:---:|:---:|:---:|:---:|:---|
| **Phase 2 Baseline Arch C** | `results/ann_phase2_architecture_comparison.csv` (Row 2) | $dp=0.2$, $wd=0.001$, $bs=32$, Unweighted | Refit up to inner early stopping steps | **75.35% ± 8.08%** | 0.1910 | — | 88.17% | Phase 2 initial architecture comparison screen |
| **Phase 2 Best Tuned Arch C** | `results/ann_phase2_experiments_summary.csv` (Row 27) | $dp=0.0$, $wd=0.001$, $bs=64$, Unweighted | Refit up to inner early stopping steps | **76.75% ± 9.05%** | 0.1862 | — | 90.66% | Top configuration found during Phase 2 hyperparameter grid search |
| **Phase 3 Evaluated Arch C** | `results/ann_phase3_model_comparison.csv` (Row 4) & `results/ann_phase3_fold_results.csv` | $dp=0.0$, $wd=0.001$, $bs=64$, Unweighted | Refit in `training/phase3_optimization.py` with step matching | **74.87% ± 6.99%** | 0.1859 | 0.5675 | 86.18% | Independent refit evaluated in Phase 3 threshold optimization |

---

## 3. Explanation of the Discrepancy

### 3.1 Why Phase 3 Arch C (74.87%) Differed from Phase 2 Best Tuned (76.75%)
1. **Independent Refit Execution:** Phase 3 re-instantiated and trained the models from scratch (`training/phase3_optimization.py`) rather than loading saved weights from Phase 2.
2. **Small-Batch Gradient Dynamics with Batch Size 64:** With a batch size of 64 on $N_{\text{train}} \approx 239$, there are only **3 to 4 mini-batch updates per epoch**.
3. **Patience & Step Budgeting:** Minor differences in PyTorch data loader shuffling across epochs altered the early stopping point on the inner validation split by 2–3 epochs. In an overparameterized 929-parameter network with zero dropout ($dp=0.0$), small variations in stopping steps caused fold 1 AUROC to settle at 68.75% and fold 3 at 70.22%, pulling the 5-fold mean to 74.87%.
4. **Conclusion:** Both figures are mathematically authentic results of the respective scripts. The 76.75% figure represents an **in-search grid exploration outcome**, while the 74.87% figure represents an **independently refitted evaluation outcome** under Phase 3.

---

## 4. Documentation Corrections Applied to Phase 9

In `results/ann_phase9_metric_reconciliation.csv`, the label for `Arch_C` has been updated to explicitly read:
- **`Arch_C_Phase3_Refit`**: AUROC **74.87% ± 6.99%** (Source: `ann_phase3_model_comparison.csv`).
- A reference row for **`Arch_C_Phase2_BestTuned`** is documented with AUROC **76.75% ± 9.05%** (Source: `ann_phase2_experiments_summary.csv`).

This removes ambiguity and provides a complete audit trail.
