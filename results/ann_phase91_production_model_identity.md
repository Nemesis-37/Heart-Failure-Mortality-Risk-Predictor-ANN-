# Phase 9.1 — Production ANN Model Identity Verification Report

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** 9.1 — Final Deployment Consistency Audit  
**Date:** November 2026  
**Subject:** Precise Architectural & Parameter Identification of Deployed Models  

---

## 1. Executive Summary

This report establishes the verified identity, layer dimensions, parameter count, and preprocessing alignment of the production model checkpoint currently deployed in the application.

> [!IMPORTANT]
> **Production ANN Verified Identity:**
> - **Checkpoint File:** `models/ann_model.pth`
> - **Class Name:** `HeartFailureANN` (`models/ann_model.py`)
> - **Exact Architecture:** $11 \to 64 \to 32 \to 1$
> - **Exact Parameter Count:** **2,881 trainable parameters**
> - **Status:** Actively loaded by FastAPI; **preserved and unmodified**.

---

## 2. Layer-by-Layer Weight Tensor Verification

Inspection of `models/ann_model.pth` via PyTorch state-dictionary tensor analysis:

| Layer Name | PyTorch Module | Tensor Name | Dimensions | Parameter Count | Data Type |
|:---|:---|:---|:---:|:---:|:---:|
| **Input $\to$ Hidden 1** | `Linear(11, 64)` | `network.0.weight` | `[64, 11]` | $64 \times 11 = 704$ | `torch.float32` |
| | | `network.0.bias` | `[64]` | $64$ | `torch.float32` |
| **Activation 1** | `ReLU()` | — | — | 0 | — |
| **Regularization 1** | `Dropout(p=0.2)` | — | — | 0 | — |
| **Hidden 1 $\to$ Hidden 2**| `Linear(64, 32)` | `network.3.weight` | `[32, 64]` | $32 \times 64 = 2,048$ | `torch.float32` |
| | | `network.3.bias` | `[32]` | $32$ | `torch.float32` |
| **Activation 2** | `ReLU()` | — | — | 0 | — |
| **Regularization 2** | `Dropout(p=0.2)` | — | — | 0 | — |
| **Hidden 2 $\to$ Output** | `Linear(32, 1)` | `network.6.weight` | `[1, 32]` | $1 \times 32 = 32$ | `torch.float32` |
| | | `network.6.bias` | `[1]` | $1$ | `torch.float32` |
| **Total** | | | | **2,881 parameters** | |

---

## 3. Clear Distinction Across Model Generations

It is critical to distinguish the **production deployed ANN** from the various **research benchmarks** explored across the project:

| Model Designation | Architecture | Total Parameters | Primary Role | Location / Checkpoint |
|:---|:---:|:---:|:---|:---|
| **Production Checkpoint** | **$11 \to 64 \to 32 \to 1$** | **2,881** | **Active Production Model** | `models/ann_model.pth` (Loaded by `main.py`) |
| **Canonical Research Arch B** | $11 \to 16 \to 1$ | 209 | Frozen Research Baseline | Evaluated in Phase 1, 3, 4.1, 5, 6 |
| **Research Arch C** | $11 \to 32 \to 16 \to 1$ | 929 | Evaluated Candidate | Evaluated in Phase 2 & 3 |
| **Wide & Deep (11 features)** | Linear + ($11 \to 8 \to 1$) | 117 | Residual Experiment | Evaluated in Phase 7 & 8 |
| **Wide & Deep (8 features)** | Linear + ($8 \to 8 \to 1$) | 90 | Ablation Candidate | Evaluated in Phase 8 |
| **Logistic Regression** | Linear ($11 \to 1$) | 12 | Canonical Production Model | `models/logistic_regression_pipeline.joblib` |

---

## 4. Preprocessing & Feature Ordering Verification

We audited the preprocessing pipeline in `main.py` lines 50–68 and 566–610:

1. **Feature Names (`models/ann_feature_names.joblib`):**
   Exact sequence of 11 features:
   `['age', 'anaemia', 'creatinine_phosphokinase', 'diabetes', 'ejection_fraction', 'high_blood_pressure', 'platelets', 'serum_creatinine', 'serum_sodium', 'sex', 'smoking']`
2. **Scaler (`models/ann_scaler.joblib`):**
   - Type: `sklearn.preprocessing.StandardScaler`
   - Input feature dimension: 11
   - Mean vector ($\mu$): shape `(11,)` (e.g. age mean = 60.55 yrs, ejection fraction mean = 37.87%)
   - Scale vector ($\sigma$): shape `(11,)` (e.g. age std = 11.79 yrs, ejection fraction std = 11.66%)
3. **Inference Execution (`main.py`):**
   ```python
   input_data = prepare_input(patient, ann_feature_names)
   scaled_data = ann_scaler.transform(input_data)
   input_tensor = torch.tensor(scaled_data, dtype=torch.float32)
   with torch.inference_mode():
       raw_output = ann_model(input_tensor)
       probability = float(torch.sigmoid(raw_output).item())
   prediction = int(probability >= 0.5)
   ```
4. **Conclusion:** Preprocessing scaling parameters, feature names, and column sequence match the production checkpoint with complete precision.
