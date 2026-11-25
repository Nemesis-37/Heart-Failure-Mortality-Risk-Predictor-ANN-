# Phase 6: ANN Learning Curve & Training Dynamics Analysis

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** Phase 6 — ANN Performance Diagnosis  
**Date:** November 2026  
**Focus:** Loss Curves, Generalization Gap, Early-Stopping Behavior & Optimization Stability  

---

## 1. Executive Summary

A critical diagnostic question is whether the PyTorch Artificial Neural Network (ANN) fails to outperform Logistic Regression due to **overfitting** (memorizing training fold noise), **underfitting** (failing to minimize loss), or **unstable optimization** (gradient oscillations or premature early stopping).

By instrumenting epoch-by-epoch metrics across the 5 outer cross-validation folds on both candidate architectures (**Arch B: 11 $\to$ 16 $\to$ 1** and **Arch C: 11 $\to$ 32 $\to$ 16 $\to$ 1**), this analysis reveals:
1. **Arch C Suffers from Unconstrained Overfitting:** In Arch C (929 parameters, dropout 0.0, weight decay 0.001), a widening generalization gap emerges after epoch 25. By epoch 50, training loss drops to 0.4630 while validation loss plateaus at 0.4978, with training AUROC reaching 84.32% while validation AUROC is capped at 79.68%.
2. **Arch B Successfully Controls the Generalization Gap:** In Arch B (209 parameters, dropout 0.2, weight decay 0.01), strong $L_2$ regularization and dropout keep the generalization gap near zero ($\Delta \text{Loss} \le 0.004$ through epoch 50).
3. **The Hidden Bottleneck of Arch B is Optimization Noise:** Because Arch B is heavily regularized, its training loss decreases very slowly (from 0.7111 to 0.5225 over 50 epochs). With only $N=191$ inner training samples and batch size 32 (only 6 mini-batches per epoch), stochastic mini-batch noise creates high fold-to-fold variance in early-stopping triggers (best epoch ranges from 72 to 200).
4. **Conclusion:** Arch B is neither catastrophically overfitting nor severely underfitting. Rather, it is **approximating a linear boundary with stochastic estimation noise**.

---

## 2. Early-Stopping Behavior & Step Budgets

Early stopping was evaluated with a patience of 15 epochs on the inner validation split ($20\%$ holdout from the training fold, $N=48$).

| Model | Fold | Best Epoch | Best Validation Loss | Stopped Epoch | Batches / Epoch | Inner Step Budget | Refit Step Multiplier ($1.25\times$) | Outer Refit Steps |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Arch B (16 $\to$ 1)** | **Fold 1** | 128 | 0.5000 | 143 | 6 | 768 | $1.25$ | 960 |
| **Arch B (16 $\to$ 1)** | **Fold 2** | 72 | 0.5163 | 87 | 6 | 432 | $1.25$ | 540 |
| **Arch B (16 $\to$ 1)** | **Fold 3** | 200 | 0.4512 | 200 (max) | 6 | 1200 | $1.25$ | 1500 |
| **Arch B (16 $\to$ 1)** | **Fold 4** | 106 | 0.4726 | 121 | 6 | 636 | $1.25$ | 795 |
| **Arch B (16 $\to$ 1)** | **Fold 5** | 168 | 0.4817 | 183 | 6 | 1008 | $1.25$ | 1260 |
| **Arch B Mean** | — | **134.8** | **0.4844** | **146.8** | **6** | **808.8** | — | **1011.0** |
| **Arch C (32 $\to$ 16 $\to$ 1)** | **Fold 1** | 84 | 0.5129 | 99 | 3 | 252 | $1.25$ | 315 |
| **Arch C (32 $\to$ 16 $\to$ 1)** | **Fold 2** | 47 | 0.5325 | 62 | 3 | 141 | $1.25$ | 176 |
| **Arch C (32 $\to$ 16 $\to$ 1)** | **Fold 3** | 105 | 0.4140 | 120 | 3 | 315 | $1.25$ | 394 |
| **Arch C (32 $\to$ 16 $\to$ 1)** | **Fold 4** | 58 | 0.4547 | 73 | 3 | 174 | $1.25$ | 218 |
| **Arch C (32 $\to$ 16 $\to$ 1)** | **Fold 5** | 78 | 0.4874 | 93 | 3 | 234 | $1.25$ | 293 |
| **Arch C Mean** | — | **74.4** | **0.4803** | **89.4** | **3** | **223.2** | — | **279.2** |

### Observations on Early Stopping:
- **Arch C Stops Twice as Fast:** Because Arch C has 929 parameters and no dropout, it fits the training set rapidly. Validation loss reaches its minimum around epoch 74, after which it begins overfitting.
- **Arch B Has Wide Fold Variance in Optimal Epochs:** In Fold 2, Arch B reaches its minimum at epoch 72, whereas in Fold 3 it continues improving up to epoch 200. This large variance ($\sigma = 51.5$ epochs) occurs because with only 6 batches per epoch, loss updates fluctuate depending on which mini-batch contains high-leverage outliers.

---

## 3. Epoch-by-Epoch Learning Trajectories

Mean training loss, validation loss, discrimination (AUROC), and gradient norms across all 5 folds:

### 3.1 Arch B (11 $\to$ 16 $\to$ 1, Dropout=0.2, Weight Decay=0.01, Batch Size=32)

| Epoch | Train BCE Loss | Val BCE Loss | Loss Gap ($\text{Val} - \text{Train}$) | Train AUROC | Val AUROC | AUROC Gap | Mean Gradient Norm |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 0.7111 | 0.7119 | +0.0009 | 0.5144 | 0.5426 | -0.0282 | 0.3305 |
| **5** | 0.6852 | 0.6865 | +0.0013 | 0.5787 | 0.5855 | -0.0068 | 0.3004 |
| **10** | 0.6573 | 0.6605 | +0.0032 | 0.6533 | 0.6384 | +0.0149 | 0.2833 |
| **15** | 0.6340 | 0.6381 | +0.0041 | 0.7010 | 0.6800 | +0.0210 | 0.2688 |
| **20** | 0.6171 | 0.6173 | +0.0002 | 0.7342 | 0.7055 | +0.0287 | 0.2673 |
| **25** | 0.5967 | 0.5974 | +0.0007 | 0.7572 | 0.7309 | +0.0263 | 0.2511 |
| **30** | 0.5741 | 0.5785 | +0.0044 | 0.7751 | 0.7572 | +0.0179 | 0.2466 |
| **40** | 0.5463 | 0.5466 | +0.0003 | 0.7986 | 0.7911 | +0.0075 | 0.2442 |
| **50** | 0.5225 | 0.5243 | +0.0018 | 0.8138 | 0.8069 | +0.0069 | 0.2413 |

### 3.2 Arch C (11 $\to$ 32 $\to$ 16 $\to$ 1, Dropout=0.0, Weight Decay=0.001, Batch Size=64)

| Epoch | Train BCE Loss | Val BCE Loss | Loss Gap ($\text{Val} - \text{Train}$) | Train AUROC | Val AUROC | AUROC Gap | Mean Gradient Norm |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 0.6784 | 0.6683 | -0.0100 | 0.5456 | 0.5956 | -0.0500 | 0.2030 |
| **5** | 0.6583 | 0.6507 | -0.0076 | 0.6385 | 0.6545 | -0.0160 | 0.1861 |
| **10** | 0.6365 | 0.6309 | -0.0056 | 0.7010 | 0.6954 | +0.0056 | 0.1759 |
| **15** | 0.6140 | 0.6102 | -0.0038 | 0.7396 | 0.7220 | +0.0176 | 0.1865 |
| **20** | 0.5888 | 0.5880 | -0.0008 | 0.7690 | 0.7451 | +0.0239 | 0.1846 |
| **25** | 0.5625 | 0.5660 | +0.0035 | 0.7925 | 0.7604 | +0.0321 | 0.1771 |
| **30** | 0.5375 | 0.5453 | +0.0078 | 0.8076 | 0.7766 | +0.0310 | 0.1796 |
| **40** | 0.4947 | 0.5137 | **+0.0190** | 0.8261 | 0.7972 | +0.0289 | 0.1843 |
| **50** | 0.4630 | 0.4978 | **+0.0348** | 0.8432 | 0.7968 | **+0.0464** | 0.1891 |

---

## 4. Key Comparative Findings

```mermaid
graph LR
    subgraph Arch B (16->1)
        B1["Dropout (0.2) + Weight Decay (0.01)"] --> B2["Controlled Generalization Gap<br>(Gap = +0.0018 at Epoch 50)"]
        B2 --> B3["Smooth Trajectory, Stable Val AUROC"]
        B3 --> B4["High Stochastic Noise due to 6 batches/epoch"]
    end

    subgraph Arch C (32->16->1)
        C1["Dropout (0.0) + Weight Decay (0.001)"] --> C2["Capacity = 929 Params on N=191"]
        C2 --> C3["Diverging Gap at Epoch 40-50<br>(Gap = +0.0348, AUC Gap = +0.0464)"]
        C3 --> C4["Premature Overfitting and Early Stop"]
    end
```

### 1. Generalization Gap Divergence:
- In Arch C, the generalization gap grows monotonically after epoch 20, reaching $+0.0348$ in loss and $+0.0464$ in AUROC by epoch 50. This confirms that without substantial dropout and weight decay, an MLP on 299 patients overfits rapidly.
- In Arch B, the generalization gap remains constrained between $0.000$ and $0.004$ across 50 epochs. This proves that Phase 2's hyperparameter choices (dropout 0.2, weight decay 0.01) were successful at suppressing variance.

### 2. Gradient Dynamics & Optimization Stability:
- Gradient norms for Arch B remain stable, decaying gently from $0.3305$ at epoch 1 to $0.2413$ at epoch 50. There is no evidence of vanishing gradients (gradient norm never drops below 0.20) or exploding gradients (maximum batch norm never exceeded 1.2).
- The loss curves do not oscillate violently, indicating that the learning rate of $0.001$ with Adam is well-calibrated.

### 3. Why Arch B Stalls at 76.11% AUROC:
- Arch B's validation AUROC reaches $\approx 80.6\%$ on the inner stop set, but when evaluated out-of-fold on the outer test set, it drops to **76.11%**.
- This discrepancy occurs because the inner stop set is only $N=48$ patients (with only $\approx 15$ deaths). Stopping based on a 48-patient sample introduces substantial stopping-time variance. In some folds, the model stops too early (before finding the optimal decision boundary), while in others it trains for 200 epochs on noisy samples.
- In contrast, Logistic Regression optimizes a convex objective over the entire 239 training patients using second-order curvature (L-BFGS). It has no stopping-time variance, no mini-batch noise, and zero hyperparameters to tune, achieving a more reliable and stable hyperplane.
