# Phase 13 — Dedicated Platelet Count Investigation

**Project:** Heart Failure Mortality Risk Predictor — CardioPredict Clinical Portal  
**Phase:** Phase 13 — Phase 7 Platelet-Specific Investigation (Research-Only)  
**Visualization:** [`fig06_platelet_response_curves.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig06_platelet_response_curves.png)  

---

## 1. Purpose & Reproduction Audit

This report investigates the previously reported anomaly in which changing **only `platelets`** produced opposing probability movements between Logistic Regression (LR) and the Artificial Neural Network (ANN).

### Reproduction Disclosure
The exact user-entered patient vector from the earlier anecdotal observation was not stored in the repository logs or test fixtures; therefore, **that single historical test case cannot be claimed as identically reproduced**. Instead, we systematically evaluated platelet perturbation across:
1. Five representative clinical patient profiles (`Low_Risk_Baseline`, `Cohort_Median_Profile`, `Borderline_Cardiorenal`, `High_Risk_Critical`, `Female_Hypertensive_Moderate`).
2. **All 299 actual dataset patients** when reducing platelets from `350,000` to `150,000 /mcL`.
3. Both the **frozen production checkpoints** (`models/logistic_regression_pipeline.joblib` & `models/ann_model.pth`) and all **5 leak-free CV ANN fold models**.
4. Both the observed training range (`[25,100, 850,000]`) and plausible boundary extensions (`[15,000, 1,000,000]`).

---

## 2. Mathematical Ground Truth in the Dataset & Models

### 2.1 Empirical Dataset Signal (`N = 299`)
In the 299-patient UCI dataset:
- Linear correlation between `platelets` and `DEATH_EVENT`: **$r = -0.0491$** (near zero).
- Cross-correlations with primary predictors: `sex` ($r = -0.1251$), `diabetes` ($r = +0.0922$), `ejection_fraction` ($r = +0.0722$), `serum_sodium` ($r = +0.0621$), `age` ($r = -0.0524$), `serum_creatinine` ($r = -0.0412$).
- **Observed Mortality by Platelet Quartile (Weak Non-Monotonic U-Shape):**
  - **Q1 (`25,100 – 212,500`):** 30 / 75 died (**40.0%**)
  - **Q2 (`212,500 – 262,000`):** 19 / 75 died (**25.3%**)
  - **Q3 (`262,000 – 303,500`):** 21 / 74 died (**28.4%**)
  - **Q4 (`303,500 – 850,000`):** 26 / 75 died (**34.7%**)
- **Out-of-Fold Permutation Importance (AUROC Drop):**
  - **LR:** **`-0.0011 ± 0.0092`**
  - **ANN:** **`-0.0059 ± 0.0150`**
  - *Interpretation:* Across unseen patients, `platelets` carries virtually **no net predictive signal** once primary markers (`ejection_fraction`, `serum_creatinine`, `age`, `serum_sodium`) are known.

### 2.2 Logistic Regression Platelet Behaviour
- **Standardized Coefficient ($\beta_{\text{std}}$):** **`-0.0665`** ($\text{SE} = 0.1546$, Wald $z = -0.43$, **non-significant**).
- **Odds Ratio per 1 SD (`97,641 /mcL`):** **`0.9357`** (95% CI `[0.6911, 1.2668]`).
- **Raw Slope:** `-6.808e-7` log-odds per unit.
- **Implication:** Under the frozen LR model, **reducing platelets mathematically ALWAYS increases predicted probability** (`0 / 299` decreases when dropping `350k -> 150k`, mean $\Delta P_{\text{LR}} = +0.0225$), and increasing platelets always decreases it.

### 2.3 ANN (`11 -> 64 -> 32 -> 1`) Platelet Behaviour & Profile Dependence
Across the 299 patients when platelets are reduced from `350,000 -> 150,000 /mcL`:
- **LR Probability Decreases:** **0 / 299 patients** (always increases).
- **ANN Probability Decreases:** **157 / 299 patients (52.5%)** — **opposite direction to LR!**
- **ANN Probability Increases:** **142 / 299 patients (47.5%)** — same direction as LR, though with wild magnitude swings ranging from **`-0.2956` to `+0.2762`**!

On the `Cohort_Median_Profile` under the frozen production ANN (`models/ann_model.pth`, Fold 4 checkpoint):
- `15,000 /mcL` $\to$ `0.0625`
- `50,000 /mcL` $\to$ `0.0652`
- `150,000 /mcL` $\to$ `0.0757`
- `250,000 /mcL` $\to$ `0.1008`
- `400,000 /mcL` $\to$ `0.1224`
- `650,000 /mcL` $\to$ `0.1388`
- `850,000 /mcL` $\to$ `0.1455`
- `1,000,000 /mcL` $\to$ `0.1415`
Notice that over `[15k, 850k]`, **production ANN slopes UPWARD** (`0.063 -> 0.145`) while **LR slopes DOWNWARD** (`0.156 -> 0.094`), producing clean **opposite directions** whenever platelet count is lowered within clinical ranges on median-risk patients!

---

## 3. Root Cause Proof: Fold-to-Fold Overfitting vs True Biological Signal

Why did the ANN learn an upward slope on some patients and a downward slope on others? Examining the 5 leak-free CV ANN models on `Cohort_Median_Profile` (`results/phase13/phase13_platelet_summary.json` and [`fig06_platelet_response_curves.png`](file:///c:/Users/DELL/OneDrive/Desktop/Heart%20Failure%20Mortality%20Risk%20Predictor/results/phase13/plots/fig06_platelet_response_curves.png) Panel B) reveals the exact answer:

| Model / CV Fold | Curve Shape (`15k -> 1,000k`) on Median Profile | Prob @ `25.1k` | Prob @ `300k` | Prob @ `850k` | Clinical Stability Verdict |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Production LR** | Smooth monotonic decrease | 0.1546 | 0.1317 | 0.0945 | Consistent, near-flat noise effect |
| **CV ANN Fold 1** | Strong monotonic **decrease** | **0.2909** | 0.0991 | **0.0223** | Steeply negative |
| **CV ANN Fold 2** | Strong monotonic **increase** | **0.1433** | 0.1996 | **0.3039** | Steeply positive |
| **CV ANN Fold 3** | Inverted-U peaking at `300k` | 0.1190 | **0.2015** | 0.1127 | Non-monotonic hump |
| **CV ANN Fold 4** *(Prod Basis)* | Inverted-U peaking at `500k` | 0.0456 | 0.1684 | 0.1242 | Opposite to Fold 1! |
| **CV ANN Fold 5** | Mild inverted-U peaking at `500k` | 0.0925 | 0.1400 | 0.1112 | Flat hump |

**Scientific Conclusion:**
The ANN's platelet response is **not a genuine nonlinear physiological interaction** discovered by deep learning. Fold 1 learns a sharp negative slope (`29% -> 2%`), Fold 2 learns a sharp positive slope (`14% -> 30%`), and Folds 3–5 learn inverted-U curves peaking in the middle! Because `platelets` has negligible true predictive power on `N = 299` (OOF permutation drop `-0.0059`) while the 2,881-parameter MLP is heavily over-parameterized relative to `N = 191–239` training samples, each fold's ReLU hyperplanes fit random sample noise along the platelet axis. Consequently:
1. Opposing LR vs ANN directional shifts on platelet perturbation are **profile-dependent** (`52.5%` opposite when dropping `350k -> 150k`, `47.5%` same direction) and driven by **ANN fold-specific variance**.
2. Neither model's platelet slope should be interpreted clinically as establishing that higher or lower platelets causally protect against mortality in heart failure.
