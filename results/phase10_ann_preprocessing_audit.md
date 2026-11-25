# Phase 10 — Production Preprocessing and Input Schema Audit

**Date:** 2026-11-25 14:29:26 UTC  
**Evaluation:** Final Production Verification (Task A.2)

---

## 1. Feature Sequence & Dimensionality Verification

The production inference pipeline enforces strict 11-feature dimensionality matching the UCI Heart Failure Clinical Records dataset without the leakage-prone `time` feature:

- **Logistic Regression Features (`models/feature_names.joblib`):**  
  `['age', 'anaemia', 'creatinine_phosphokinase', 'diabetes', 'ejection_fraction', 'high_blood_pressure', 'platelets', 'serum_creatinine', 'serum_sodium', 'sex', 'smoking']`
- **ANN Features (`models/ann_feature_names.joblib`):**  
  `['age', 'anaemia', 'creatinine_phosphokinase', 'diabetes', 'ejection_fraction', 'high_blood_pressure', 'platelets', 'serum_creatinine', 'serum_sodium', 'sex', 'smoking']`
- **Exact Sequence Match:** **CONFIRMED IDENTICAL** (11 features in identical lexicographical order).

---

## 2. Standard Scaler Artifact (`models/ann_scaler.joblib`)

The production ANN utilizes scikit-learn's `StandardScaler`, fitted exclusively on the 11 clinical features during training:

| Index | Feature Name | Fitted Mean ($\mu$) | Fitted Scale ($\sigma$) | Fitted Variance ($\sigma^2$) |
|---|---|---|---|---|
| 1 | `age` | 60.5509 | 11.7873 | 138.9410 |
| 2 | `anaemia` | 0.4226 | 0.4940 | 0.2440 |
| 3 | `creatinine_phosphokinase` | 603.5607 | 1038.2580 | 1077979.7777 |
| 4 | `diabetes` | 0.4310 | 0.4952 | 0.2452 |
| 5 | `ejection_fraction` | 37.8661 | 11.6590 | 135.9319 |
| 6 | `high_blood_pressure` | 0.3556 | 0.4787 | 0.2292 |
| 7 | `platelets` | 265837.9105 | 95181.3317 | 9059485903.1720 |
| 8 | `serum_creatinine` | 1.4115 | 1.0982 | 1.2060 |
| 9 | `serum_sodium` | 136.6360 | 4.4914 | 20.1729 |
| 10 | `sex` | 0.6527 | 0.4761 | 0.2267 |
| 11 | `smoking` | 0.3054 | 0.4606 | 0.2121 |

### Single Transformation Guarantee
Inspection of `main.py` lines 571–580 confirms:
1. `prepare_input(patient, ann_feature_names)` orders raw input into a 1-row pandas DataFrame matching `ann_feature_names`.
2. `ann_scaler.transform(input_data)` is invoked **exactly once**.
3. No intermediate or accidental transformations (such as `log1p`, polynomial expansions, or secondary normalization) occur.
4. Input tensor is created with `torch.tensor(scaled_data, dtype=torch.float32)`.

---

## 3. Pydantic Input Validation Schema (`PatientData`)

The API enforces strict validation rules via Pydantic v2 in `main.py`:

| Field Name | Type | Range / Constraints | Description | HTTP 422 Violation Example |
|---|---|---|---|---|
| `patient_reference_id` | `str` | Compulsory string, non-empty | Unique patient clinical tracking ID | Missing or empty string |
| `age` | `float` | $1.0 \le \text{age} \le 120.0$ | Patient chronological age (years) | `age = -5` or `age = 150` |
| `anaemia` | `int` | $\in \{0, 1\}$ | Binary haematocrit reduction indicator | `anaemia = 2` |
| `creatinine_phosphokinase` | `float` | $\ge 1.0$ | CPK blood enzyme level (mcg/L) | `cpk = 0` or negative |
| `diabetes` | `int` | $\in \{0, 1\}$ | Binary diabetes mellitus flag | `diabetes = -1` |
| `ejection_fraction` | `float` | $1.0 \le \text{EF} \le 100.0$ | Left ventricular ejection fraction (%) | `ejection_fraction = 0` or `120` |
| `high_blood_pressure` | `int` | $\in \{0, 1\}$ | Binary hypertension diagnosis | `high_blood_pressure = 5` |
| `platelets` | `float` | $\ge 1.0$ | Platelet count (kiloplatelets/mL) | `platelets = -100` |
| `serum_creatinine` | `float` | $\ge 0.1$ | Serum creatinine level (mg/dL) | `serum_creatinine = 0.0` |
| `serum_sodium` | `float` | $50.0 \le \text{sodium} \le 200.0$ | Blood serum sodium concentration (mEq/L)| `serum_sodium = 30` or `250` |
| `sex` | `int` | $\in \{0, 1\}$ | Biological sex (0 = Female, 1 = Male) | `sex = 2` |
| `smoking` | `int` | $\in \{0, 1\}$ | Binary cigarette smoking history | `smoking = 3` |

All out-of-bound requests are rejected immediately at the boundary with HTTP 422 Unprocessable Entity, preventing malformed vectors from entering inference.
