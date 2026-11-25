"""
scripts/evaluate_phase5_fixed_thresholds.py
Executes a strict, leakage-safe evaluation of fixed operating thresholds (0.30, 0.33, 0.35, 0.40, 0.50)
for Arch B (11->16->1), Arch C (11->32->16->1), and Logistic Regression on the exact 5-fold CV splits.
Generates:
- results/ann_phase5_fixed_threshold_assessment.csv
- results/ann_phase5_fold_metrics.csv
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (
    roc_auc_score,
    brier_score_loss,
    log_loss,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "dataset" / "heart_failure_clinical_records_dataset.csv"
RESULTS_DIR = PROJECT_ROOT / "results"
SEED = 42
FOLDS = 5

class ConfigurableANN(nn.Module):
    def __init__(self, in_features, hidden_layers, dropout=0.0):
        super().__init__()
        layers = []
        prev = in_features
        for h in hidden_layers:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            if dropout > 0.0:
                layers.append(nn.Dropout(p=dropout))
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)

def set_all_seeds(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def train_ann_with_early_stopping(X_train, y_train, X_stop, y_stop, config, seed):
    set_all_seeds(seed)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_stop_s = scaler.transform(X_stop)

    t_train_X = torch.tensor(X_train_s, dtype=torch.float32)
    t_train_y = torch.tensor(y_train.to_numpy(), dtype=torch.float32).unsqueeze(1)
    t_stop_X = torch.tensor(X_stop_s, dtype=torch.float32)

    model = ConfigurableANN(X_train.shape[1], config["layers"], dropout=config["dropout"])
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config["lr"],
        weight_decay=config["weight_decay"]
    )

    batch_size = config["batch_size"]
    n_samples = len(X_train)
    patience = 15
    best_val_loss = float("inf")
    best_step = 0
    patience_counter = 0
    total_steps = 0
    max_epochs = 300

    y_stop_np = y_stop.to_numpy()

    for epoch in range(1, max_epochs + 1):
        perm = np.random.permutation(n_samples)
        model.train()
        for i in range(0, n_samples, batch_size):
            b_idx = perm[i: i + batch_size]
            b_x = t_train_X[b_idx]
            b_y = t_train_y[b_idx]

            optimizer.zero_grad()
            logits = model(b_x)
            loss = criterion(logits, b_y)
            loss.backward()
            optimizer.step()
            total_steps += 1

        model.eval()
        with torch.inference_mode():
            val_logits = model(t_stop_X).numpy().ravel()
            val_loss = log_loss(y_stop_np, torch.sigmoid(torch.tensor(val_logits)).numpy(), labels=[0, 1])

        if val_loss < best_val_loss - 1e-4:
            best_val_loss = val_loss
            best_step = total_steps
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                break

    # Re-evaluate model at best state
    model.eval()
    with torch.inference_mode():
        stop_logits = model(t_stop_X).numpy().ravel()
        stop_probs = torch.sigmoid(torch.tensor(stop_logits)).numpy().ravel()

    return {
        "best_steps": best_step,
        "scaler": scaler,
        "inner_stop_probs": stop_probs,
        "inner_stop_logits": stop_logits,
    }

def fit_final_outer_ann(X_train, y_train, config, seed, target_steps):
    set_all_seeds(seed)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    t_train_X = torch.tensor(X_train_s, dtype=torch.float32)
    t_train_y = torch.tensor(y_train.to_numpy(), dtype=torch.float32).unsqueeze(1)

    model = ConfigurableANN(X_train.shape[1], config["layers"], dropout=config["dropout"])
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config["lr"],
        weight_decay=config["weight_decay"]
    )

    batch_size = config["batch_size"]
    n_samples = len(X_train)
    steps_done = 0

    while steps_done < target_steps:
        perm = np.random.permutation(n_samples)
        model.train()
        for i in range(0, n_samples, batch_size):
            if steps_done >= target_steps:
                break
            b_idx = perm[i: i + batch_size]
            b_x = t_train_X[b_idx]
            b_y = t_train_y[b_idx]

            optimizer.zero_grad()
            logits = model(b_x)
            loss = criterion(logits, b_y)
            loss.backward()
            optimizer.step()
            steps_done += 1

    return model, scaler

def calculate_metrics_at_threshold(y_true, y_prob, threshold):
    preds = (y_prob >= threshold).astype(int)
    cm = confusion_matrix(y_true, preds, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * (prec * sens) / (prec + sens) if (prec + sens) > 0 else 0.0
    acc = (tp + tn) / len(y_true)
    return {
        "Threshold": float(threshold),
        "Accuracy": float(acc),
        "Sensitivity": float(sens),
        "Specificity": float(spec),
        "Precision": float(prec),
        "F1_Score": float(f1),
        "TP": int(tp),
        "FP": int(fp),
        "TN": int(tn),
        "FN": int(fn),
    }

print("=" * 75)
print("PHASE 5: LEAKAGE-SAFE FIXED THRESHOLD & FINAL MODEL EVALUATION")
print("=" * 75)

df = pd.read_csv(DATA_PATH)
X = df.drop(columns=["DEATH_EVENT", "time"])
y = df["DEATH_EVENT"].astype(int)

cv = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
splits = list(cv.split(X, y))

MODELS_CONFIG = [
    {
        "id": "Logistic_Regression",
        "name": "Logistic Regression Baseline",
        "type": "linear",
        "params": 12,
    },
    {
        "id": "Arch_B_16",
        "name": "Arch B (16->1)",
        "type": "ann",
        "layers": [16],
        "dropout": 0.2,
        "weight_decay": 0.01,
        "batch_size": 32,
        "lr": 0.001,
        "params": 209,
    },
    {
        "id": "Arch_C_32_16",
        "name": "Arch C (32->16->1)",
        "type": "ann",
        "layers": [32, 16],
        "dropout": 0.0,
        "weight_decay": 0.001,
        "batch_size": 64,
        "lr": 0.001,
        "params": 929,
    },
]

CANDIDATE_THRESHOLDS = [0.30, 0.33, 0.35, 0.40, 0.50]

fold_metrics_records = []
fixed_threshold_records = []

for m_info in MODELS_CONFIG:
    m_id = m_info["id"]
    m_name = m_info["name"]
    print(f"\n>>> Running Model: {m_name} <<<")

    model_fold_probs = []
    model_fold_targets = []

    for fold, (train_idx, val_idx) in enumerate(splits, start=1):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        y_val_np = y_val.to_numpy()

        X_train_inner, X_stop, y_train_inner, y_stop = train_test_split(
            X_train, y_train, test_size=0.20, stratify=y_train, random_state=SEED + fold
        )

        if m_info["type"] == "linear":
            lr_pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=SEED))
            lr_pipe.fit(X_train, y_train)
            outer_probs = lr_pipe.predict_proba(X_val)[:, 1]
        else:
            ann_res = train_ann_with_early_stopping(
                X_train_inner, y_train_inner, X_stop, y_stop, m_info, seed=SEED + fold
            )
            final_ann, final_scaler = fit_final_outer_ann(
                X_train, y_train, m_info, seed=SEED + fold, target_steps=ann_res["best_steps"]
            )
            final_ann.eval()
            X_val_s = final_scaler.transform(X_val)
            with torch.inference_mode():
                logits = final_ann(torch.tensor(X_val_s, dtype=torch.float32)).numpy().ravel()
                outer_probs = torch.sigmoid(torch.tensor(logits)).numpy().ravel()

        model_fold_probs.append(outer_probs)
        model_fold_targets.append(y_val_np)

        # Baseline outer metrics
        auroc = roc_auc_score(y_val_np, outer_probs)
        brier = brier_score_loss(y_val_np, outer_probs)
        ll = log_loss(y_val_np, outer_probs, labels=[0, 1])

        # Evaluate candidate fixed thresholds
        for th in CANDIDATE_THRESHOLDS:
            m_th = calculate_metrics_at_threshold(y_val_np, outer_probs, threshold=th)
            fold_metrics_records.append({
                "Model_ID": m_id,
                "Model_Name": m_name,
                "Fold": fold,
                "AUROC": float(auroc),
                "Brier_Score": float(brier),
                "Log_Loss": float(ll),
                **m_th,
            })

# Summary across folds for candidate fixed thresholds
df_fold_metrics = pd.DataFrame(fold_metrics_records)
df_fold_metrics.to_csv(RESULTS_DIR / "ann_phase5_fold_metrics.csv", index=False)
print(f"✓ Saved fold metrics: {RESULTS_DIR / 'ann_phase5_fold_metrics.csv'}")

# Generate Fixed Threshold Assessment Summary
for m_info in MODELS_CONFIG:
    m_id = m_info["id"]
    m_name = m_info["name"]
    sub_df = df_fold_metrics[df_fold_metrics["Model_ID"] == m_id]

    auroc_mean = sub_df.groupby("Fold")["AUROC"].first().mean()
    auroc_std = sub_df.groupby("Fold")["AUROC"].first().std()
    brier_mean = sub_df.groupby("Fold")["Brier_Score"].first().mean()
    brier_std = sub_df.groupby("Fold")["Brier_Score"].first().std()
    ll_mean = sub_df.groupby("Fold")["Log_Loss"].first().mean()
    ll_std = sub_df.groupby("Fold")["Log_Loss"].first().std()

    for th in CANDIDATE_THRESHOLDS:
        th_df = sub_df[sub_df["Threshold"] == th]

        sens_mean = th_df["Sensitivity"].mean()
        sens_std = th_df["Sensitivity"].std()
        spec_mean = th_df["Specificity"].mean()
        spec_std = th_df["Specificity"].std()
        prec_mean = th_df["Precision"].mean()
        prec_std = th_df["Precision"].std()
        f1_mean = th_df["F1_Score"].mean()
        f1_std = th_df["F1_Score"].std()
        acc_mean = th_df["Accuracy"].mean()
        acc_std = th_df["Accuracy"].std()

        mean_tp = th_df["TP"].mean()
        mean_fp = th_df["FP"].mean()
        mean_tn = th_df["TN"].mean()
        mean_fn = th_df["FN"].mean()

        fixed_threshold_records.append({
            "Model_ID": m_id,
            "Model_Name": m_name,
            "Fixed_Threshold": th,
            "AUROC_Mean": auroc_mean,
            "AUROC_Std": auroc_std,
            "Brier_Score_Mean": brier_mean,
            "Brier_Score_Std": brier_std,
            "Log_Loss_Mean": ll_mean,
            "Log_Loss_Std": ll_std,
            "Accuracy_Mean": acc_mean,
            "Accuracy_Std": acc_std,
            "Sensitivity_Mean": sens_mean,
            "Sensitivity_Std": sens_std,
            "Specificity_Mean": spec_mean,
            "Specificity_Std": spec_std,
            "Precision_Mean": prec_mean,
            "Precision_Std": prec_std,
            "F1_Score_Mean": f1_mean,
            "F1_Score_Std": f1_std,
            "Mean_TP": mean_tp,
            "Mean_FP": mean_fp,
            "Mean_TN": mean_tn,
            "Mean_FN": mean_fn,
            "Methodological_Note": (
                "Evaluated across untouched outer test folds using a single fixed decision boundary."
            ),
        })

df_fixed_thresh = pd.DataFrame(fixed_threshold_records)
df_fixed_thresh.to_csv(RESULTS_DIR / "ann_phase5_fixed_threshold_assessment.csv", index=False)
print(f"✓ Saved fixed threshold assessment: {RESULTS_DIR / 'ann_phase5_fixed_threshold_assessment.csv'}")

print("\n--- ARCH B FIXED THRESHOLD ASSESSMENT SUMMARY ---")
arch_b_fixed = df_fixed_thresh[df_fixed_thresh["Model_ID"] == "Arch_B_16"]
for _, r in arch_b_fixed.iterrows():
    print(
        f"Thr {r['Fixed_Threshold']:.2f} | "
        f"Sens: {r['Sensitivity_Mean']*100:.2f}% ± {r['Sensitivity_Std']*100:.2f}% | "
        f"Spec: {r['Specificity_Mean']*100:.2f}% ± {r['Specificity_Std']*100:.2f}% | "
        f"F1: {r['F1_Score_Mean']:.4f} ± {r['F1_Score_Std']:.4f} | "
        f"TP: {r['Mean_TP']:.1f}, FP: {r['Mean_FP']:.1f}, FN: {r['Mean_FN']:.1f}"
    )

print("\n--- LOGISTIC REGRESSION FIXED THRESHOLD ASSESSMENT SUMMARY ---")
lr_fixed = df_fixed_thresh[df_fixed_thresh["Model_ID"] == "Logistic_Regression"]
for _, r in lr_fixed.iterrows():
    print(
        f"Thr {r['Fixed_Threshold']:.2f} | "
        f"Sens: {r['Sensitivity_Mean']*100:.2f}% ± {r['Sensitivity_Std']*100:.2f}% | "
        f"Spec: {r['Specificity_Mean']*100:.2f}% ± {r['Specificity_Std']*100:.2f}% | "
        f"F1: {r['F1_Score_Mean']:.4f} ± {r['F1_Score_Std']:.4f} | "
        f"TP: {r['Mean_TP']:.1f}, FP: {r['Mean_FP']:.1f}, FN: {r['Mean_FN']:.1f}"
    )
