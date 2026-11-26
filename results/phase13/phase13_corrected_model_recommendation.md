# Phase 13 — Corrected Final Model Recommendation

**Project:** Heart Failure Mortality Risk Predictor — CardioPredict Clinical Portal  
**Phase:** Phase 13 — Re-Evaluated Recommendation Following Methodological Audit  
**Date:** November 26, 2026  
**Action Status:** **RESEARCH ONLY — NO PRODUCTION IMPLEMENTATION PERFORMED**  

---

## 1. Re-Evaluated Conclusion

### Does Logistic Regression Remain the Recommended Candidate?
**YES — Option A (Logistic Regression)** remains the best-supported single fixed production model for this educational clinical prototype, **though with a critically corrected statistical framing**:

1. **What Changed After Methodological Correction:**
   - **Matched Training Sample Size:** When comparing models on strictly identical training partitions (`~191` inner rows: LR AUROC `0.7482` vs ANN `0.7238`; or `~239` outer-train refit rows: LR AUROC `0.7595` vs ANN `0.7425`), the apparent AUROC advantage of LR narrows from `+0.0660` (single Seed-42 outlier) / `+0.0357` (unmatched 5×10 CV) to **`+0.0244`** (matched 191) and **`+0.0170`** (matched 239).
   - **Corrected Statistical Significance:** Under the **Nadeau & Bengio (2003) corrected resampled $t$-test** accounting for repeated-CV overlap ($df = 49$), **NONE of the 5×10 repeated-CV performance differences reach $p < 0.05$** (`AUROC p = 0.118–0.242`, `PR-AUC p = 0.122–0.263`, `Brier p = 0.110–0.270`, `Log Loss p = 0.238–0.555`).
   - Therefore, we **withdraw any claim that LR beats ANN with $p < 0.001$ generalizable statistical significance across splits**; on `N = 299`, cross-validation alone lacks statistical power to separate a `+0.017` to `+0.036` AUROC difference reliably at $\alpha = 0.05$.

2. **Why Logistic Regression Still Remains Better Supported Than ANN or Option D:**
   - **Consistent Descriptive Edge Across All 4 Aggregation Modes & Both Matched Conditions:** LR leads descriptively on AUROC, PR-AUC, Brier Score, Log Loss, Balanced Accuracy, Sensitivity, and F1 in `LR_Outer239 vs ANN_Inner191` (`41/50` AUROC fold wins), `LR_Inner191 vs ANN_Inner191` (`36/50` wins), and `LR_Outer239 vs ANN_RefitOuter239` (`40/50` wins), as well as 10-repeat patient-averaged OOF (`0.7644` vs `0.7525`).
   - **Operational Advantage Without Inner Holdout Penalty:** Because LR does not require reserving 20% of training data for stochastic early stopping, LR naturally leverages 100% of available training records deterministically (`239` in CV; `299` in production).
   - **Decisive Non-Metric Advantages (`Models/ann_model.pth` Failure Modes):**
     - *Calibration Reliability:* Uncalibrated OOF ECE `0.0414` (LR) vs `0.1033` (ANN), slope `0.7509` vs `0.4791`.
     - *Determinism vs Seed Fragility:* LR has zero seed variance; ANN OOF AUROC swings `0.6935–0.7528` across 5 seeds.
     - *Behavioural & Platelet Integrity:* The deployed 2,881-parameter ANN flips sign across profiles on noisy binary flags (`smoking`, `diabetes`, `high_blood_pressure`) and learns opposite platelet risk curves across CV folds (`Fold 1` vs `Fold 2` vs `Fold 4`), whereas LR weights remain smooth, stable, and auditable.
   - **Ensembling Fails:** Blending LR and ANN strictly underperforms pure LR across all weights (`phase13_ensemble_comparison.csv`).

---

## 2. Explicit Scope, Uncertainty & External Validation Disclosures

1. **Non-Significance Disclosure:** On this 299-patient cohort (`96` mortality events), corrected repeated-CV tests do not show $p < 0.05$ discrimination superiority. LR is selected on the strength of consistent directional performance **combined with** superior calibration, determinism, behavioural coherence, parsimony (12 vs 2,881 parameters), and explainability.
2. **External Validation Remains `BLOCKED / NOT AVAILABLE`:** Neither LR nor ANN has been evaluated on an independent external cohort (`phase13_external_validation_report.md`).
3. **Educational Prototype Classification:** Operating sensitivity at `0.50` (`43.1%–47.9%` LR; `36.3%–40.9%` ANN) remains modest due to missing clinical predictors (BNP, NYHA class, etiology, medications) and class imbalance (`32.11%`). Threshold `0.50` vs prevalence-aligned `~0.33` should be reviewed alongside any future production decision.

*(Research verification complete. All production files remain untouched.)*
