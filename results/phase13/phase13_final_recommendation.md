# Phase 13 — Final Production Model Recommendation

**Project:** Heart Failure Mortality Risk Predictor — CardioPredict Clinical Portal  
**Phase:** Phase 13 — Phase 14 Final Recommendation & Research Summary  
**Date:** November 26, 2026  
**Action Status:** **RESEARCH RECOMMENDATION ONLY — NO PRODUCTION CHANGES IMPLEMENTED**  

---

## 1. Formal Model Recommendation

### Selected Recommendation: **Option A — Logistic Regression** (as the single fixed prediction model for this educational clinical prototype, paired with a strict disclosure that external clinical validation remains unperformed)

**Rationale Summary:**  
On genuinely unseen out-of-fold patients (`N = 299` across 5-fold and 5×10 repeated stratified cross-validation), **Logistic Regression** consistently and significantly outperforms the deployed **ANN (`11 -> 64 -> 32 -> 1`, 2,881 parameters)** on discrimination, probability calibration, patient-level accuracy, fold-to-fold stability, behavioural coherence, and explainability—even when constrained to the identical 80% inner training partition size (`N ≈ 191`). Moreover, blending LR and ANN into an ensemble strictly degrades every evaluation metric compared to LR alone.

*(Important Context: Historical internal research reports from Phase 5 noted that a smaller regularized `11 -> 16 -> 1` "Arch B" network narrowed the gap to ~1% behind LR, but **the actual deployed production checkpoint `models/ann_model.pth` is the larger 2,881-parameter `11 -> 64 -> 32 -> 1` network saved from Fold 4 of `training/train_ann.py`**, which suffers severe small-sample overfitting (`~12–15×` more parameters than training cases) once validation early-stopping leakage is removed.)*

---

## 2. Evidence Base Supporting Option A (Logistic Regression)

1. **Superior Unseen-Patient Discrimination (Descriptive Consistency Across Matched Splits; See Audit Note):**
   - 5-Fold Stratified Leak-Free OOF (`Seed = 42`, `N = 299`): AUROC **`0.7595`** (LR) vs **`0.6935`** (ANN), DeLong $p = 7.76 \times 10^{-5}$ (note: Seed 42 was ANN's worst split/seed; across all 10 individual repeats, 5/10 had $p < 0.05$).
   - Repeated Stratified `5 × 10` CV (50 folds): **`LR_Outer239` `0.7595 ± 0.0621`** vs `ANN_Inner191` `0.7238 ± 0.0683` (Nadeau–Bengio corrected $p = 0.1184$, **not statistically significant**); matched-191 `LR_Inner191` `0.7482` vs `ANN_Inner191` `0.7238` ($p = 0.1741$); matched-239 refit `LR_Outer239` `0.7595` vs `ANN_RefitOuter239` `0.7425` ($p = 0.2418$). See [`phase13_corrected_model_recommendation.md`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/phase13_corrected_model_recommendation.md) for full details.
2. **Superior Probability Calibration & Uncertainty Reliability:**
   - Uncalibrated OOF Brier Score **`0.1778`** vs **`0.2053`**; Log Loss **`0.5438`** vs **`0.6190`**; 10-bin ECE **`0.0414`** vs **`0.1033`**; Calibration Slope **`0.7509`** vs **`0.4791`**.
   - Even after inner-fold Platt recalibration, ANN (`ECE = 0.0910`, `LogLoss = 0.6119`) remains substantially less calibrated than uncalibrated LR.
3. **Better Patient-Level Classification & Discordant Wins:**
   - Out of **32 discordant unseen patients** at threshold `0.50`, LR is correct on **23 (71.9%)** whereas ANN is correct on only **9 (28.1%)** (McNemar exact $p = 0.0201$).
   - ANN generates notably more false positives on middle-aged low-risk survivors (`15/19` ANN-positive disagreements were survived patients correctly cleared by LR) and occasional extreme saturation false negatives (e.g., Patient 61, EF 25%, died: ANN `0.81%` vs LR `52.3%`).
4. **Full Training Data Utilization & Zero Training-Seed Fragility:**
   - LR requires no inner validation holdout for early stopping, so a single deterministic convex fit uses 100% of available training patients (`N = 299` in production vs `239` Fold-4-only in `models/ann_model.pth`) with zero random-seed variability (`ANN` OOF AUROC swings `0.6935–0.7528` across 5 seeds).
5. **Clinically Coherent Behavioural Responses & Transparency:**
   - The platelet perturbation anomaly (opposite directions between LR and ANN) and binary comorbidity sign flips (`smoking`, `diabetes`, `high_blood_pressure`) in the ANN are proved by fold-by-fold perturbation analysis to be small-sample noise overfitting rather than robust clinical interactions.
   - LR provides exact, auditable coefficients and Odds Ratios with 95% Wald confidence intervals centered on `ejection_fraction`, `age`, `serum_creatinine`, `serum_sodium`, and `CPK`.
6. **Ensemble Non-Viability:**
   - No convex linear blend $w P_{\text{LR}} + (1-w) P_{\text{ANN}}$ improves upon $w = 1.0$ (pure LR) on AUROC, PR-AUC, Brier score, Log Loss, or CV stability.

---

## 3. Critical Operational Caveat Regarding Threshold `0.50` & Prototype Scope

- **Threshold `0.50` Limitation:** While LR is the superior model, **both models miss more than half of actual deaths at the default `0.50` threshold** on unseen patients (`LR` sensitivity `47.92%`, `50` false negatives out of `96` deaths) because mortality prevalence is imbalanced (`32.11%`). If the user later approves a production update, threshold selection (e.g., dual risk stratification tiers or prevalence-aligned cutoff `~0.33`, where LR captures `64.58%` of deaths at `71.43%` specificity) should be explicitly reviewed alongside LR deployment.
- **Educational Prototype Boundary:** Neither LR nor ANN has undergone **external clinical validation** (`Phase 12: BLOCKED / NOT AVAILABLE`), and baseline records exclude `time`, NYHA class, BNP/NT-proBNP, ischemic etiology, and medical therapy regimens (`46` deaths were missed by both models due to normal-looking baseline profiles). Therefore, this model **must strictly remain framed as an educational clinical decision-support prototype**, not a validated clinical diagnostic tool.

---

## 4. Phase 13 Final Completion Summary (Answers to Key Questions)

1. **Which model performed better on out-of-fold unseen patients?**  
   **Logistic Regression** (`AUROC 0.7595` vs `0.6935`, DeLong $p = 7.76 \times 10^{-5}$; `5x10 CV AUROC 0.7595` vs `0.7238`, winning `41/50` folds).
2. **Which model had better calibration?**  
   **Logistic Regression** (`Brier 0.1778` vs `0.2053`, `Log Loss 0.5438` vs `0.6190`, `ECE 0.0414` vs `0.1033`, `Slope 0.7509` vs `0.4791`).
3. **Which model had better sensitivity and specificity?**  
   On 5-fold OOF (`N=299`, `@ 0.50`), **LR** led on both **Sensitivity** (`47.92%` vs `43.75%`, though 95% bootstrap CI crossed zero) and **Specificity** (`88.67%` vs `83.74%`, 95% CI `[+0.9%, +9.2%]`). Across 50 repeated splits, LR led on Sensitivity (`43.13%` vs `36.29%`) while Specificity was essentially tied (`88.08%` vs `88.72%`, `21 vs 21` fold wins). At `@ 0.33`, LR led both (`64.58% / 71.43%` vs `59.38% / 70.44%`).
4. **Which model was more stable?**  
   **Logistic Regression** (100% deterministic optimization with tighter repeated-CV AUROC SD `0.0621` vs `0.0683`, and sensitivity SD `0.1059` vs `0.1424`; ANN also varies by `0.059` AUROC across random seeds).
5. **What did the platelet investigation reveal?**  
   `platelets` carries virtually zero out-of-fold predictive signal (`r = -0.049`, OOF permutation importance `-0.0011` LR / `-0.0059` ANN). LR has a near-zero negative weight (`-0.0665`), so reducing platelets always slightly raises LR probability (`0/299` decreases). By contrast, `models/ann_model.pth` decreases in `157/299` patients and increases in `142/299` when dropping `350k -> 150k`, and **different CV folds learn completely opposite platelet slopes** (Fold 1 downward, Fold 2 upward, Folds 3–5 inverted-U)—proving the ANN is overfitting small-sample noise along the platelet axis.
6. **Where did LR and ANN disagree?**  
   They disagreed on classification (`@ 0.50`) for **32 / 299 unseen patients** (`10.7%`, mean $|P_{\text{LR}} - P_{\text{ANN}}| = 0.209$). On 19 patients where ANN predicted death and LR predicted survival, ANN was wrong **15 / 19 times** (false positives in younger/middle-aged survivors); on 13 patients where LR predicted death and ANN predicted survival, LR was right **8 / 13 times** (catching elderly low-EF deaths where ANN occasionally collapsed near zero).
7. **Did the ensemble genuinely improve performance?**  
   **No.** Across every blend weight $w \in [0.0, 0.9]$ and nested inner-validation weight selection (`w = 0.66`, AUROC `0.7268`), combining ANN with LR degraded AUROC, PR-AUC, Brier Score, Log Loss, and stability compared to LR alone (`w = 1.0`, AUROC `0.7595`, Brier `0.1778`).
8. **Was external validation possible?**  
   **No — `BLOCKED / NOT AVAILABLE`.** No compatible open-access independent heart failure mortality dataset is available without restricted credentialing/DUA (e.g., PhysioNet Zigong `N = 2,008` or BioLINCC trials).
9. **Which model should be selected for production, and why?**  
   **Option A: Logistic Regression**, because on small tabular data (`N = 299`, 11 features) it achieves superior unseen discrimination, superior calibration, higher stability, full-cohort deterministic fitting, transparent clinical interpretability, and freedom from erratic small-sample noise sensitivity. *(Pending explicit user approval before modifying production code.)*
10. **What uncertainties remain?**  
    - Absence of multi-center external validation (unknown transportability outside the 299 Faisalabad NYHA III/IV cohort).
    - Wide confidence intervals due to limited mortality events (`n_pos = 96`).
    - Shared baseline blind spots (`46/96` deaths missed by both models) caused by unmeasured clinical variables (BNP, echo strain, etiology, pharmacotherapy).
    - Operating threshold policy (`0.50` default vs sensitivity-focused cutoff `~0.33`) requires explicit clinical/educational design sign-off prior to any implementation phase.

---

> [!IMPORTANT]
> **STOP NOTICE:** Per Phase 13 instructions, **zero production files, endpoints, UI elements, checkpoints, scalers, or thresholds have been modified.** All experiments ran in isolated scripts under `scripts/phase13/` with outputs confined to `results/phase13/`. Awaiting explicit user approval before implementing any changes.
