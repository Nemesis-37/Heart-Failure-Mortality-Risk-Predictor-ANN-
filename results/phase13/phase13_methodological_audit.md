# Phase 13 — Final Methodological Audit & Report Verification

**Project:** Heart Failure Mortality Risk Predictor — CardioPredict Clinical Portal  
**Mode:** Research-Only Verification (Zero Production Modifications)  
**Date:** November 26, 2026  

---

## Executive Audit Status Scorecard

| Audit Area | Status | Key Verdict |
| :--- | :---: | :--- |
| **1. Identical Training Conditions** | **FAIL** *(Original)* $\to$ **REMEDIATED** | Original `Repeated_5x10_CV` trained `LR_Outer239` on ~239 rows vs `ANN_Inner191` on ~191 inner rows (+48 early-stopping val rows). Re-executed under two strictly matched controls (`LR_Inner191` vs `ANN_Inner191` on identical 191 rows; and `LR_Outer239` vs `ANN_RefitOuter239` on identical 239 rows). |
| **2. Repeated-CV Statistical Inference** | **FAIL** *(Original)* $\to$ **CORRECTED** | Original `run_cv_and_stats.py` computed a naive paired $t$-test (`ttest_rel`) assuming 50 independent folds and over-relied on single-seed `Repeat 1` (`Seed 42`) DeLong $p = 0.0001$. Under the **Nadeau–Bengio (2003) corrected resampled $t$-test**, no 5×10 CV metric difference is statistically significant ($p = 0.11\text{--}0.85$). |
| **3. Independent Verification of Repeated-CV AUROC** | **PASS** | Direct recomputation across all 50 splits matched prior CSVs to `0.00e+00`. `0.759534` (50-fold mean AUROC) vs `0.759493` (Seed-42 pooled OOF AUROC) is a genuine 4-decimal numerical coincidence (`Δ = 0.000041`). All 4 aggregation modes are separated cleanly below. |
| **4. External Unseen Data Validation** *(Pre-existing)* | **BLOCKED** | Unchanged: no independent compatible open-access heart failure mortality dataset is available without restricted DUA/IRB access. |

---

## 1. Audit Area 1 — Identical Training Conditions (`FAIL` in Original Comparison $\to$ Remediated)

### 1.1 Partition & Leakage Verification (`50 / 50` Splits Checked)
Direct inspection and automated assertion checks in `scripts/phase13/run_methodological_audit.py` across all 50 splits (`RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=42)`) confirmed:
- **Outer Partition Disjointness:** `len(set(outer_tr_idx) & set(test_idx)) == 0` in **50 / 50** splits (`n_outer_train ∈ {239, 240}`, `n_test ∈ {59, 60}`).
- **Inner Partition Disjointness:** `len(set(inner_tr_idx) & set(inner_va_idx)) == 0` in **50 / 50** splits (`n_inner_train ∈ {191, 192}`, `n_inner_val = 48`).
- **Preprocessing & Early-Stopping Isolation:** `StandardScaler` was fitted strictly inside training data; early stopping and checkpoint selection (`best_epoch`) never touched `X_test`.

### 1.2 Asymmetry Discovered in Original Phase 13 Comparison
In the original `Repeated_5x10_CV` (`run_cv_and_stats.py`):
- `Logistic_Regression` (`LR_Outer239`) fit `StandardScaler` + `LogisticRegression` on all **~239** `X_outer_tr` samples.
- `ANN_11_64_32_1` (`ANN_Inner191`) fit `StandardScaler` + network weights on **~191** `X_inner_tr` samples (80% of 239), holding out **48** `X_inner_va` samples solely for early stopping.
- Although `Logistic_Regression_Inner80` (`~191` rows) was run on the single 5-fold (`Seed 42`) split, **it was missing from the 50-fold `5×10` Repeated CV**, and ANN had not been tested with a leak-free full-239 refit.

### 1.3 Corrected Matched-Data 5×10 Repeated CV Comparison (`50` Splits Each)
All four conditions were evaluated on identical `RepeatedStratifiedKFold(5, 10, seed=42)` splits (`results/phase13/phase13_corrected_cv_statistics.csv`):

| Model Condition | Actual Training $N$ per Split | 50-Fold AUROC (Mean ± SD) | 50-Fold PR-AUC (Mean ± SD) | 50-Fold Brier (Mean ± SD) | 50-Fold Log Loss (Mean ± SD) | 50-Fold Sens / Spec (@ 0.50) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`LR_Outer239`** | 239–240 | **0.7595 ± 0.0621** | **0.6284 ± 0.0961** | **0.1787 ± 0.0238** | **0.5459 ± 0.0689** | **43.13%** / 88.08% |
| **`LR_Inner191`** *(Exact match to ANN inner split)* | 191–192 | **0.7482 ± 0.0621** | **0.6140 ± 0.0894** | **0.1828 ± 0.0241** | **0.5580 ± 0.0720** | **41.69%** / 87.83% |
| **`ANN_Inner191`** *(Inner early-stopping)* | 191–192 (+48 val) | 0.7238 ± 0.0683 | 0.5832 ± 0.0986 | 0.1910 ± 0.0227 | 0.5714 ± 0.0619 | 36.29% / **88.72%** |
| **`ANN_RefitOuter239`** *(Inner `best_epoch`, full 239 refit)* | 239–240 | 0.7425 ± 0.0636 | 0.5996 ± 0.0972 | 0.1869 ± 0.0243 | 0.5647 ± 0.0678 | 40.87% / 87.63% |

**Key Finding:** Roughly **32%–52%** of `LR_Outer239`'s original `+0.0357` AUROC lead over `ANN_Inner191` came from LR utilizing all 239 outer training samples (`LR_Outer239 0.7595` vs `LR_Inner191 0.7482` = `+0.0113`), and from ANN suffering when constrained to 191 rows (`ANN_RefitOuter239 0.7425` vs `ANN_Inner191 0.7238` = `+0.0187`). Nevertheless, under **both** strict apples-to-apples controls (`LR_Inner191 vs ANN_Inner191`: `+0.0244`; `LR_Outer239 vs ANN_RefitOuter239`: `+0.0170`), LR retains a higher descriptive mean across AUROC, PR-AUC, Brier Score, Log Loss, Balanced Accuracy, Sensitivity, and F1.

---

## 2. Audit Area 2 — Repeated Cross-Validation Statistical Inference (`FAIL` in Original $\to$ Corrected)

### 2.1 Why Naive Tests & Single-Seed DeLong Were Misleading
1. **Dependence Across Repeated Folds:** In `5×10` CV, all 10 repeats partition the exact same 299 patients. A naive paired $t$-test (`ttest_rel` with $\text{SE} = s_d / \sqrt{50}$) ignores patient overlap across splits and folds, severely underestimating variance and yielding false-positive $p$-values (e.g., naive `p = 4.1e-7` for AUROC!). Likewise, fold win counts (`41 / 50`) are strictly **descriptive**, not 50 independent Bernoulli trials.
2. **Repeat-1 (`Seed = 42`) Outlier Effect:** Inspecting DeLong tests across all 10 individual repeats (`LR_Outer239` vs `ANN_Inner191`) reveals that Repeat 1 (`Seed 42`, ANN `0.6935`) was ANN's worst random split/seed across the entire 10-repeat experiment:
   - Repeat 1: $\Delta = +0.0660$, DeLong **$p = 0.0001$**
   - Repeat 2: $\Delta = +0.0090$, DeLong **$p = 0.4894$**
   - Repeat 3: $\Delta = +0.0476$, DeLong **$p = 0.0007$**
   - Repeat 4: $\Delta = +0.0581$, DeLong **$p = 0.0011$**
   - Repeat 5: $\Delta = +0.0101$, DeLong **$p = 0.4569$**
   - Repeat 6: $\Delta = +0.0463$, DeLong **$p = 0.0165$**
   - Repeat 7: $\Delta = +0.0264$, DeLong **$p = 0.0587$**
   - Repeat 8: $\Delta = +0.0280$, DeLong **$p = 0.0514$**
   - Repeat 9: $\Delta = +0.0552$, DeLong **$p = 0.0011$**
   - Repeat 10: $\Delta = +0.0347$, DeLong **$p = 0.0192$**
   *(Only 5 of 10 individual repeats showed $p < 0.05$; citing only Repeat 1's $p = 7.76 \times 10^{-5}$ overstated statistical certainty.)*

### 2.2 Nadeau & Bengio (2003) / Bouckaert & Frank (2004) Corrected Resampled $t$-Test
To properly account for training/test overlap across $K=5$ folds and $R=10$ repeats ($n_{\text{test}}/n_{\text{train}} = 0.2/0.8 = 0.25$):
$$\text{SE}_{\text{corrected}} = \sqrt{\left(\frac{1}{K \cdot R} + \frac{n_{\text{test}}}{n_{\text{train}}}\right) s_d^2} = \sqrt{0.27 \cdot s_d^2}, \quad df = 49$$

| Paired Comparison | Metric | Mean Diff (A − B) | Fold SD ($s_d$) | Naive $p$ *(INVALID)* | Corrected SE | Corrected $t$ ($df=49$) | **Corrected $p$** | **Corrected 95% CI** | Sig ($\alpha=0.05$)? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`LR_Outer239` vs `ANN_Inner191`** | **AUROC** | `+0.0357` | `0.0432` | `4.1e-7` | `0.0225` | `1.589` | **`0.1184`** | `[-0.0094, +0.0808]` | **No** |
| | **PR-AUC** | `+0.0452` | `0.0553` | `5.1e-7` | `0.0287` | `1.573` | **`0.1221`** | `[-0.0125, +0.1030]` | **No** |
| | **Brier** | `-0.0123` | `0.0146` | `2.5e-7` | `0.0076` | `-1.627` | **`0.1103`** | `[-0.0276, +0.0029]` | **No** |
| | **Log Loss** | `-0.0256` | `0.0417` | `7.2e-5` | `0.0216` | `-1.181` | **`0.2434`** | `[-0.0690, +0.0179]` | **No** |
| **`LR_Inner191` vs `ANN_Inner191`** *(Matched $N \approx 191$)* | **AUROC** | `+0.0244` | `0.0340` | `6.1e-6` | `0.0177` | `1.379` | **`0.1741`** | `[-0.0112, +0.0599]` | **No** |
| | **PR-AUC** | `+0.0308` | `0.0445` | `1.1e-5` | `0.0231` | `1.332` | **`0.1890`** | `[-0.0157, +0.0773]` | **No** |
| | **Brier** | `-0.0083` | `0.0143` | `1.6e-4` | `0.0074` | `-1.115` | **`0.2704`** | `[-0.0232, +0.0066]` | **No** |
| | **Log Loss** | `-0.0134` | `0.0434` | `0.0338` | `0.0226` | `-0.594` | **`0.5549`** | `[-0.0588, +0.0319]` | **No** |
| **`LR_Outer239` vs `ANN_RefitOuter239`** *(Matched $N \approx 239$)* | **AUROC** | `+0.0170` | `0.0276` | `6.8e-5` | `0.0143` | `1.185` | **`0.2418`** | `[-0.0118, +0.0458]` | **No** |
| | **PR-AUC** | `+0.0288` | `0.0490` | `1.3e-4` | `0.0254` | `1.132` | **`0.2632`** | `[-0.0223, +0.0799]` | **No** |
| | **Brier** | `-0.0082` | `0.0107` | `1.7e-6` | `0.0056` | `-1.480` | **`0.1453`** | `[-0.0194, +0.0029]` | **No** |
| | **Log Loss** | `-0.0188` | `0.0303` | `6.0e-5` | `0.0157` | `-1.195` | **`0.2379`** | `[-0.0505, +0.0128]` | **No** |

*(All 27 rows across all 9 metrics are saved in [`phase13_corrected_cv_statistics.csv`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/phase13_corrected_cv_statistics.csv).)*

**Assumptions & Limitations of Nadeau–Bengio Test:**
- The Nadeau–Bengio correction accounts for sample overlap using the variance inflation factor $\frac{1}{K\cdot R} + \frac{n_{\text{test}}}{n_{\text{train}}} = 0.27$, which assumes approximate stationarity across repeats. With only $N = 299$ patients ($n_{\text{pos}} = 96$), the minimum detectable AUROC effect at 80% power exceeds $\sim 0.06\text{--}0.07$. Therefore, **$p > 0.05$ reflects limited small-sample statistical power, NOT proof that LR and ANN perform identically.**

---

## 3. Audit Area 3 — Independent Verification of Repeated-CV AUROC (`PASS`)

Direct recomputation from scratch matched the existing `phase13_cross_validation_results.csv` to **`0.00e+00`** for both LR and ANN across all 50 splits.

### Why `0.7595` Appeared Twice (Genuine Numerical Coincidence)
- **`0.759534`** is the arithmetic mean of the 50 individual fold AUROCs across Repeats 1–10 (`Repeat 1` fold mean = `0.771713`, `Repeats 2–10` fold means range from `0.749296` to `0.765342`).
- **`0.759493`** is the single **Seed-42 Repeat-1 Pooled OOF AUROC** (`N = 299` concatenated across the 5 Seed-42 folds). Pooling probabilities across folds slightly lowers pooled AUROC relative to Repeat 1's fold mean (`0.771713 -> 0.759493`) due to minor cross-fold calibration shifts, and by pure arithmetic coincidence both `0.759534` and `0.759493` round to **`0.7595`** (`Δ = 0.000041`).

### Explicit Separation of All 4 Aggregation Modes

| Model | 1. 50-Fold Mean ± SD (`N ≈ 60`/fold) | 2. 10-Repeat Pooled OOF Mean ± SD (`N = 299`/repeat) | 3. Single Seed-42 Pooled OOF (`N = 299`) | 4. 10-Repeat Patient-Averaged OOF (`N = 299`, Bagged) |
| :--- | :---: | :---: | :---: | :---: |
| **`LR_Outer239`** | **0.759534 ± 0.062064** | **0.759180 ± 0.004480** | **0.759493** | **0.764368** *(Brier 0.1767)* |
| **`LR_Inner191`** | 0.748244 ± 0.062148 | 0.748250 ± 0.010124 | 0.733836 | 0.759955 *(Brier 0.1780)* |
| **`ANN_Inner191`** | 0.723848 ± 0.068275 | 0.721039 ± 0.019839 | 0.693504 | 0.744048 *(Brier 0.1838)* |
| **`ANN_RefitOuter239`** | 0.742544 ± 0.063647 | 0.738711 ± 0.011343 | 0.732964 | 0.752514 *(Brier 0.1810)* |

*(Note how across every single aggregation method—50-fold mean, 10-repeat pooled OOF mean, Seed-42 pooled OOF, and 10-repeat bagged patient OOF—`LR_Outer239` ranks #1 and outperforms both `ANN_Inner191` and `ANN_RefitOuter239`, while `LR_Inner191` beats `ANN_Inner191` in all 4 modes as well!)*
