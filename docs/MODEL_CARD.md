# Machine Learning Model Card: Heart Failure Mortality Risk Predictor

**Document Standard:** Mitchell et al. (2019) Model Cards for Model Reporting  
**Version:** 1.0.0 (Production Verified)  
**Date:** November 2026  
**Project:** Heart Failure Mortality Risk Predictor  
**Target Domain:** Educational Clinical Decision Support & Tabular Deep Learning Research

---

## 1. Model Details

### 1.1. Overview
The Heart Failure Mortality Risk Predictor is a dual-model machine learning system designed to estimate the in-hospital / post-discharge mortality probability for patients diagnosed with heart failure, conditioned upon 11 admission-time clinical and physiological features.

### 1.2. Architecture Specifications

```
+-----------------------------------------------------------------------------------+
| MODEL A: CANONICAL LOGISTIC REGRESSION (PRODUCTION BASELINE)                      |
+-----------------------------------------------------------------------------------+
| Framework:       scikit-learn 1.4+ (Pipeline)                                     |
| Preprocessing:   StandardScaler(with_mean=True, with_std=True)                    |
| Architecture:    Linear dot product + bias -> Logistic Sigmoid                    |
| Total Params:    12 (11 feature coefficients + 1 intercept)                       |
| Optimization:    L-BFGS solver, L2 regularization (C = 1.0), tol = 1e-4           |
| Checkpoint:      models/logistic_regression_pipeline.joblib                       |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| MODEL B: ARTIFICIAL NEURAL NETWORK (PRODUCTION DEEP LEARNING MODEL)               |
+-----------------------------------------------------------------------------------+
| Framework:       PyTorch 2.0+ (HeartFailureANN)                                   |
| Preprocessing:   StandardScaler(with_mean=True, with_std=True)                    |
| Architecture:    11 -> Linear(64) -> ReLU -> Dropout(0.2) ->                      |
|                  Linear(32) -> ReLU -> Dropout(0.2) -> Linear(1) -> Sigmoid       |
| Total Params:    2,881 trainable float32 weights and biases                       |
| Loss Function:   BCEWithLogitsLoss (numerically stable binary cross-entropy)      |
| Optimizer:       Adam (lr = 0.001, weight_decay = 1e-4)                           |
| Checkpoint:      models/ann_model.pth                                             |
+-----------------------------------------------------------------------------------+
```

---

## 2. Intended Use & Clinical Scope

### 2.1. Primary Intended Uses
- **Academic and Educational Instruction:** Serving as a reference implementation for comparative analysis between classical generalized linear models (GLMs) and multi-layer perceptrons on small tabular clinical datasets.
- **Methodological Auditing:** Demonstrating rigorous cross-validation, leak-free preprocessing, feature ablation, probability calibration, and empirical significance testing.
- **Decision-Support Prototyping:** Exploring user experience interfaces for dual-model comparison in medical applications.

### 2.2. Out-of-Scope & Prohibited Uses
- **Autonomous Clinical Diagnosis:** The system must never be used as a standalone diagnostic instrument.
- **Emergency Triage Decisions:** Under no circumstances should emergency department triage or ICU admission prioritization rely upon these models.
- **Treatment or Pharmaceutical Dosing:** Predictions must not dictate medication adjustments (e.g., ACE inhibitors, beta-blockers, inotropes).

---

## 3. Dataset & Feature Engineering

### 3.1. Training Cohort
- **Source:** UCI Machine Learning Repository — Heart Failure Clinical Records (Chicco & Jurman, 2020; Tanvir Ahmad et al., Allied Hospital, Faisalabad, Pakistan).
- **Cohort Size:** 299 patient records.
- **Target Variable:** `DEATH_EVENT` (Binary: 0 = Survived, 1 = Deceased during observation period).
- **Class Distribution:** 96 mortality events (32.11%) vs 203 survivals (67.89%).

### 3.2. Mandatory Feature Exclusions (Data Leakage Prevention)
The raw dataset contains the variable `time` (number of days the patient was followed up).
- **Scientific Audit Finding:** `time` exhibits an artificial inverse correlation with `DEATH_EVENT` (patients who died were followed for fewer days because observation ceased at death). Including `time` inflates AUROC to >85% but constitutes severe post-baseline target leakage that is unknowable at patient admission.
- **Engineering Enforcement:** `time` is strictly excluded from all training, validation, and production inference pipelines.

### 3.3. Input Feature Set (11 Baseline Clinical Predictors)

| Feature Name | Clinical Description | Data Type | Units / Range | Fitted Mean ($\mu$) | Fitted Std ($\sigma$) |
|---|---|---|---|---|---|
| `age` | Patient chronological age | Continuous | Years ($40 - 95$) | 60.83 | 11.89 |
| `anaemia` | Haematocrit reduction | Binary | 0 = No, 1 = Yes | 0.43 | 0.50 |
| `creatinine_phosphokinase` | CPK enzyme concentration | Continuous | mcg/L ($23 - 7861$) | 581.84 | 970.29 |
| `diabetes` | History of diabetes mellitus | Binary | 0 = No, 1 = Yes | 0.42 | 0.49 |
| `ejection_fraction` | Left ventricular ejection fraction | Continuous | % ($14 - 80$) | 38.08 | 11.83 |
| `high_blood_pressure` | Hypertension diagnosis | Binary | 0 = No, 1 = Yes | 0.35 | 0.48 |
| `platelets` | Blood platelet count | Continuous | kiloplatelets/mL ($25k - 850k$) | 263,358.03 | 97,804.25 |
| `serum_creatinine` | Blood creatinine level | Continuous | mg/dL ($0.5 - 9.4$) | 1.39 | 1.03 |
| `serum_sodium` | Blood sodium level | Continuous | mEq/L ($113 - 148$) | 136.63 | 4.41 |
| `sex` | Biological sex | Binary | 0 = Female, 1 = Male | 0.65 | 0.48 |
| `smoking` | Cigarette smoking history | Binary | 0 = No, 1 = Yes | 0.32 | 0.47 |

---

## 4. Empirical Evaluation & Benchmark Results

Performance was evaluated using **5-Fold Stratified Cross-Validation** ($n_{\text{splits}}=5$, seed=42) conducted with leak-free preprocessing:

### 4.1. Discrimination and Calibration Metrics

| Metric | Canonical Logistic Regression | Production ANN Checkpoint | Research Baseline Arch B | Research Candidate Arch C | Phase 8 Wide & Deep (8-feat) |
|---|---|---|---|---|---|
| **AUROC (Mean ± Std)** | **77.17% ± 5.51%** | **76.22% ± 4.90%** | 76.11% ± 6.22% | 76.54% ± 5.10% | 77.68% ± 4.80% |
| **Brier Score (Lower is better)** | **0.1777** | **0.1804** | 0.1804 | 0.1832 | 0.1788 |
| **Log Loss (Lower is better)** | **0.5437** | **0.5415** | 0.5415 | 0.5512 | 0.5390 |
| **Parameter Count** | **12** | **2,881** | 209 | 929 | 90 |
| **Wilcoxon vs LR ($p$-value)** | Reference Baseline | $p = 0.6250$ (Not Sig) | $p = 0.6250$ (Not Sig) | $p = 0.8125$ (Not Sig) | $p = 0.6250$ (Not Sig) |

### 4.2. Statistical Significance Analysis
- Paired two-tailed Wilcoxon signed-rank tests across the 5 outer folds yield $p = 0.6250$ between the neural network and Logistic Regression.
- **Scientific Takeaway:** The hypothesis that multi-layer perceptrons provide superior discrimination over generalized linear models on this 299-patient tabular dataset is **unsupported by empirical evidence**. Logistic Regression delivers identical or marginally superior discrimination with 240x fewer parameters.

---

## 5. Decision Thresholds & Risk Stratification

The models default to a standard statistical classification threshold of $\tau = 0.50$. In clinical screening, false negatives (failing to identify a patient at risk of death) carry greater harm than false positives.

### 5.1. Youden's $J$ Threshold Optimization
- At $\tau = 0.50$: Sensitivity = $48.9\%$, Specificity = $89.2\%$.
- Optimal Youden's Index ($J = \text{Sensitivity} + \text{Specificity} - 1$) occurs at $\tau^* = 0.35 - 0.38$:
  - Sensitivity increases to **$72.9\%$**.
  - Specificity remains at **$73.4\%$**.

### 5.2. Clinical Risk Tier Mapping
The user interface maps continuous probabilities into three intuitive operational categories:
- **Low Risk:** $P < 0.30$ (Routine outpatient follow-up).
- **Moderate Risk:** $0.30 \le P < 0.60$ (Close hemodynamic monitoring).
- **High Risk:** $P \ge 0.60$ (Urgent specialist consultation recommended).

---

## 6. Ethical Considerations & Limitations

1. **Single-Center Demographics:** The dataset originates exclusively from Allied Hospital in Faisalabad, Pakistan. Patterns of comorbidity, diet, genetic predispositions, and pharmacological standards may not generalize to North American, European, or East Asian populations.
2. **Small Cohort Size ($n = 299$):** Neural network parameter capacity (2,881 parameters) exceeds the effective degree of freedom in the sample (96 death events), creating an inherent susceptibility to overfitting that requires aggressive dropout and weight decay.
3. **Tabular Deep Learning Bottleneck:** In small tabular datasets lacking dense spatial or temporal structures, generalized linear models with $L_2$ regularization consistently match or exceed deep feedforward architectures.
