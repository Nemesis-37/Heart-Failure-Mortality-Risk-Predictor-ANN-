# Phase 13 — Project, Dataset & Production Model Inventory

**Project:** Heart Failure Mortality Risk Predictor — CardioPredict Clinical Portal  
**Phase:** Phase 13 (Research & Comparative Evaluation Only — Zero Production Changes)  
**Date:** November 26, 2026  

---

## 1. Repository & Dataset Audit

### 1.1 Dataset Specifications
- **File Path:** `dataset/heart_failure_clinical_records_dataset.csv`
- **Source Cohort:** Heart Failure Clinical Records (Faisalabad Institute of Cardiology and Allied Hospital, Pakistan; Ahmad et al., 2017; Chicco & Jurman, 2020)
- **Total Records:** **299 patients**
- **Original Columns:** 13 (`11` baseline clinical features + `time` + `DEATH_EVENT`)
- **Excluded Variable:** `time` (follow-up period in days) is strictly dropped before training and inference due to post-baseline target leakage.
- **Target Variable:** `DEATH_EVENT` (`0` = Survived, `1` = Deceased)
- **Target Distribution:**
  - Survived (`0`): **203 patients (67.89%)**
  - Mortality Event (`1`): **96 patients (32.11%)**
- **Duplicate Check:**
  - Exact row duplicates: **0**
  - Exact 11-feature duplicates: **0**

### 1.2 Production Input Feature Order (Verified Identical Across Both Models)
Verified directly from `models/feature_names.joblib` and `models/ann_feature_names.joblib`, and enforced in `main.py` (`PatientData` & `prepare_input`):

| Index | Feature Name | Data Type | Role / Clinical Domain | Pydantic Bounds (`main.py`) |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `age` | `float` | Demographics (years) | `[1, 120]` |
| 2 | `anaemia` | `int` (`0/1`) | Haematology (decrease of red blood cells/hemoglobin) | `{0, 1}` |
| 3 | `creatinine_phosphokinase` | `float` | Cardiac/muscle enzyme CPK (mcg/L) | `>= 1` |
| 4 | `diabetes` | `int` (`0/1`) | Metabolic comorbidity | `{0, 1}` |
| 5 | `ejection_fraction` | `float` | Systolic cardiac function LVEF (%) | `[1, 100]` |
| 6 | `high_blood_pressure` | `int` (`0/1`) | Vascular comorbidity (hypertension) | `{0, 1}` |
| 7 | `platelets` | `float` | Coagulation / hematology (kiloplatelets/mL) | `>= 1` |
| 8 | `serum_creatinine` | `float` | Renal biomarker (mg/dL) | `>= 0.1` |
| 9 | `serum_sodium` | `float` | Electrolyte homeostasis (mEq/L) | `[50, 200]` |
| 10 | `sex` | `int` (`0/1`) | Biological sex (`0` = Female, `1` = Male) | `{0, 1}` |
| 11 | `smoking` | `int` (`0/1`) | Behavioral risk factor | `{0, 1}` |

`lr_feature_names == ann_feature_names` was verified `True`. No feature ordering discrepancy exists at inference time in `main.py`.

---

## 2. Production Model Inventory & Architectural Comparison

| Property | Logistic Regression (Production `/predict`) | Artificial Neural Network (Production `/predict-ann`) |
| :--- | :--- | :--- |
| **Model Definition** | `models/logistic_model.py` (`create_logistic_model`) | `models/ann_model.py` (`HeartFailureANN`) |
| **Artifact Path(s)** | `models/logistic_regression_pipeline.joblib`<br>`models/feature_names.joblib` | `models/ann_model.pth`<br>`models/ann_scaler.joblib`<br>`models/ann_feature_names.joblib` |
| **Generating Script** | `training/save_model.py` | `training/train_ann.py` |
| **Architecture** | Scikit-Learn `Pipeline`: `StandardScaler` $\to$ `LogisticRegression(C=1.0, penalty='l2', solver='lbfgs', max_iter=2000, random_state=42)` | PyTorch `nn.Sequential`: `Linear(11, 64)` $\to$ `ReLU` $\to$ `Dropout(0.2)` $\to$ `Linear(64, 32)` $\to$ `ReLU` $\to$ `Dropout(0.2)` $\to$ `Linear(32, 1)` |
| **Learnable Parameters** | **12** (11 weights + 1 intercept) | **2,881** (`704+64` + `2048+32` + `32+1`) |
| **Training Objective** | Regularized Maximum Likelihood (L2 Log Loss) | `BCEWithLogitsLoss()`, `Adam(lr=0.001, weight_decay=1e-4)`, batch size `32`, max epochs `100`, early stopping `patience=10` |
| **Preprocessing** | `StandardScaler` inside Pipeline | Standalone `StandardScaler` (`ann_scaler.joblib`) applied once in `main.py` before `torch.tensor(..., dtype=torch.float32)` |
| **Actual Training Cohort in Saved Artifact** | **All 299 patients** (`scaler.n_samples_seen_ = 299`) | **239 patients only — Fold 4 training split** (`scaler.n_samples_seen_ = 239`) |
| **Production Decision Threshold** | `0.50` (`lr_model.predict(...)`) | `0.50` (`int(probability >= 0.5)`) |
| **UI Threshold (`DoctorDashboard.jsx`)** | `0.50` (`>= 0.5` elevated risk display) | `0.50` (`>= 0.5` elevated risk display) |

---

## 3. Critical Preprocessing, Provenance & Historical Script Discrepancies Discovered

1. **Asymmetric Training Coverage in Production Artifacts:**
   - `models/logistic_regression_pipeline.joblib` was trained on all **299** patients (`training/save_model.py`).
   - `models/ann_model.pth` and `models/ann_scaler.joblib` were saved by `training/train_ann.py`, which picked the single CV fold with the lowest validation loss (**Fold 4**, `Best_Validation_Loss = 0.4192`, `n_train = 239`, `n_val = 60`). Consequently, the deployed ANN has never seen the 60 Fold 4 patients during training, **but** those 60 patients influenced its early-stopping epoch and fold selection!
   - *Implication for Phase 13:* Neither production artifact (`save_model.py` LR on 299/299, or `train_ann.py` Fold 4 ANN with validation early-stopping) should be evaluated on the 299-patient cohort as if it were unseen data. Fair unseen-patient comparison requires strict, leak-free out-of-fold cross-validation (`Phase 3`).

2. **Two Historical ANN Cross-Validation Scripts With Different Protocols:**
   - `training/train_ann.py` (which wrote `models/ann_model.pth` and `results/ann_5fold_results.csv`): Used outer validation split `X_val` directly for early stopping (`PATIENCE=10`) and `best_fold_loss` checkpoint selection (early-stopping validation leakage). Historical summary: Mean AUROC = `0.7606`, Mean Sensitivity = `0.4090`, Mean Specificity = `0.8968`, Mean Accuracy = `0.7393`.
   - `training/ann_cross_validation.py` & `training/logistic_cross_validation.py`: Implemented nested 80/20 inner split (`train_test_split(..., test_size=0.20, random_state=42+fold, stratify=y_outer_train)`) inside each outer fold, leaving the outer test fold untouched during scaling and early stopping. Note: `logistic_cross_validation.py` also fit LR only on the 80% inner train split (`~191` rows) rather than the full 239 outer-train rows (`training/train.py` fit LR on all 239 outer-train rows, yielding Mean AUROC = `0.7717`).

3. **Research Candidates vs. Production Deployment:**
   - Phases 1–8 (`training/phase2_optimization.py`, `phase3_optimization.py`, etc.) evaluated alternative compact architectures such as **Arch B** ($11 \to 16 \to 1$, 209 params) and **Wide & Deep** hybrids.
   - As verified in `results/phase10_production_model_identity.md` and `models/ann_model.pth`, **none of those experimental models were deployed**. Production strictly uses `HeartFailureANN` ($11 \to 64 \to 32 \to 1$, 2,881 parameters) and `LogisticRegression` ($11 \to 1$, 12 parameters). Phase 13 evaluates the exact **production architectures and training configurations** (`HeartFailureANN` 11→64→32→1 vs `LogisticRegression` C=1.0).

4. **Inference Pipeline Consistency:**
   - Both `/predict` and `/predict-ann` in `main.py` call `prepare_input(patient, feature_names)` using identical 11 feature columns in identical order, followed by single z-score standardization (`StandardScaler`) and sigmoid probability output. There is **no** feature order or double-scaling bug in production inference.
