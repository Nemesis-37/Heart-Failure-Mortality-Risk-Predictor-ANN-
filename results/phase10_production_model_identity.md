# Phase 10 — Production Model Identity Verification

**Date:** 2026-11-25 14:29:26 UTC  
**Target Checkpoint:** `models/ann_model.pth`  
**Evaluation:** Final Production Verification (Task A.1)

---

## 1. Checkpoint Integrity & Metadata

| Attribute | Value |
|---|---|
| **File Path** | `models/ann_model.pth` |
| **File Size** | 14,701 bytes |
| **Last Modified (UTC)** | `2026-10-23T14:37:18.665020+00:00` |
| **SHA-256 Hash** | `0e469da724c7bab36c1d29878fb3e16988b8842643b3312c54486da2792f0ca3` |
| **PyTorch Architecture** | `HeartFailureANN` ($11 \to 64 \to 32 \to 1$) |
| **Total Trainable Parameters** | **2,881** float32 parameters |
| **Deployment Status** | **VERIFIED & FROZEN IN PRODUCTION** |

---

## 2. Layer-by-Layer Parameter Breakdown

The production checkpoint loaded by `main.py` is an exact sequential feedforward neural network comprising two hidden layers with ReLU activations and dropout regularizers:

```
Input (11 features)
  │
  ▼
Linear(in_features=11, out_features=64, bias=True)   [Weight: 64x11 = 704, Bias: 64 = 768 params]
ReLU()
Dropout(p=0.2)
  │
  ▼
Linear(in_features=64, out_features=32, bias=True)   [Weight: 32x64 = 2,048, Bias: 32 = 2,080 params]
ReLU()
Dropout(p=0.2)
  │
  ▼
Linear(in_features=32, out_features=1, bias=True)    [Weight: 1x32 = 32, Bias: 1 = 33 params]
  │
  ▼
Output Logit (1 scalar value) ──[Sigmoid]──> Probability ∈ [0, 1]
```

### Detailed Tensor Specifications

| Layer / Parameter | Shape | Parameter Count | Data Type | Weight Mean | Weight Std |
|---|---|---|---|---|---|
| `network.0.weight` | `[64, 11]` | 704 | `torch.float32` | -0.0034 | 0.1964 |
| `network.0.bias` | `[64]` | 64 | `torch.float32` | +0.0059 | 0.2030 |
| `network.3.weight` | `[32, 64]` | 2,048 | `torch.float32` | +0.0089 | 0.0883 |
| `network.3.bias` | `[32]` | 32 | `torch.float32` | +0.0590 | 0.0834 |
| `network.6.weight` | `[1, 32]` | 32 | `torch.float32` | -0.0599 | 0.1877 |
| `network.6.bias` | `[1]` | 1 | `torch.float32` | +0.0466 | 0.0000 |
| **Total Parameters** | — | **2,881** | — | — | — |

---

## 3. Architecture Distinction & Research Model Lineage

To ensure absolute scientific and operational clarity, the production model is strictly distinguished from all experimental models explored across Phases 1–8:

| Model Designation | Architecture | Total Params | Role in Project | AUROC (11 Features) | Status |
|---|---|---|---|---|---|
| **Canonical Logistic Regression** | Linear / Sigmoid (11 weights + 1 bias) | **12** | **Production Baseline** | **77.17% ± 5.51%** | **FROZEN & DEPLOYED** (`/predict`) |
| **Production ANN Checkpoint** | $11 \to 64 \to 32 \to 1$ | **2,881** | **Production Neural Net** | **76.22% ± 4.90%** | **FROZEN & DEPLOYED** (`/predict-ann`) |
| **Research Baseline Arch B** | $11 \to 16 \to 1$ | 209 | Phase 1–6 Research Benchmark | 76.11% ± 6.22% | Research Reference Only |
| **Research Candidate Arch C** | $11 \to 32 \to 16 \to 1$ | 929 | Phase 2–3 Exploration | 76.54% ± 5.10% | Research Reference Only |
| **Phase 7 Wide & Deep ANN** | Linear (11) + Deep ($11 \to 8 \to 1$) | 108 | Residual Hybrid Candidate | 76.89% ± 5.30% | Research Reference Only |
| **Phase 8 Ablation Wide & Deep**| Linear (8) + Deep ($8 \to 8 \to 1$) | 90 | 8-Feature Experimental Model | 77.68% ± 4.80% | Experimental Only (Matched LR: 78.10%) |

### Confirmation of Experimental Rules
1. The production checkpoint `models/ann_model.pth` has **not** been overwritten or replaced.
2. No experimental or reduced-feature model has been promoted to production.
3. The production model continues to serve inference on all 11 patient features via `/predict-ann`.
