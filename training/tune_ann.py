
import copy
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    confusion_matrix,
)


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dataset" / "heart_failure_clinical_records_dataset.csv"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SEED = 42
FOLDS = 5
MAX_EPOCHS = 100
PATIENCE = 10
BATCH_SIZE = 32
WEIGHT_DECAY = 0.0001


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


# --------------------------------------------------
# 2. ANN architecture (Numerically Stable Logits)
# --------------------------------------------------

class TunableANN(nn.Module):
    def __init__(self, input_size, hidden_layers):
        super().__init__()

        layers = []
        previous_size = input_size

        for size in hidden_layers:
            layers.extend([
                nn.Linear(previous_size, size),
                nn.ReLU(),
                nn.Dropout(0.2),
            ])
            previous_size = size

        layers.extend([
            nn.Linear(previous_size, 1),
        ])

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        """Returns raw unconstrained logits for BCEWithLogitsLoss."""
        return self.network(x)

    def predict_proba(self, x):
        """Convert logits to calibrated probabilities."""
        return torch.sigmoid(self.forward(x))


# --------------------------------------------------
# 3. Training helpers
# --------------------------------------------------

def to_tensors(X, y):
    return (
        torch.tensor(X, dtype=torch.float32),
        torch.tensor(np.asarray(y), dtype=torch.float32).reshape(-1, 1),
    )


def train_with_early_stopping(
    X_train, y_train, X_stop, y_stop, config, seed, pos_weight=None
):
    """
    Use an inner validation split to select the optimal training stopping point.
    Returns best_epoch, total optimizer update steps, and inner batch metrics.
    """
    set_seed(seed)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_stop_scaled = scaler.transform(X_stop)

    train_X, train_y = to_tensors(X_train_scaled, y_train)
    stop_X, stop_y = to_tensors(X_stop_scaled, y_stop)

    loader = DataLoader(
        TensorDataset(train_X, train_y),
        batch_size=BATCH_SIZE,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )

    model = TunableANN(
        input_size=X_train.shape[1],
        hidden_layers=config["layers"],
    )

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config["lr"],
        weight_decay=WEIGHT_DECAY,
    )
    
    if pos_weight is not None:
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    else:
        loss_fn = nn.BCEWithLogitsLoss()

    best_loss = float("inf")
    best_state = None
    best_epoch = 1
    patience_count = 0
    inner_batches_per_epoch = len(loader)

    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()

        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            logits = model(batch_X)
            loss = loss_fn(logits, batch_y)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.inference_mode():
            val_logits = model(stop_X)
            val_loss = loss_fn(val_logits, stop_y).item()

        if val_loss < best_loss:
            best_loss = val_loss
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch
            patience_count = 0
        else:
            patience_count += 1

        if patience_count >= PATIENCE:
            break

    total_inner_steps = best_epoch * inner_batches_per_epoch

    return {
        "best_epoch": best_epoch,
        "best_val_loss": best_loss,
        "total_inner_steps": total_inner_steps,
        "inner_batches_per_epoch": inner_batches_per_epoch,
    }


def fit_final_fold_model(
    X_train, y_train, config, seed,
    target_steps=None,
    epochs=None,
    pos_weight=None,
):
    """
    Refit using all outer training data.
    If target_steps is provided, stops when optimizer update count matches the inner budget.
    If epochs is provided, trains for a fixed epoch count.
    """
    set_seed(seed)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)
    train_X, train_y = to_tensors(X_scaled, y_train)

    loader = DataLoader(
        TensorDataset(train_X, train_y),
        batch_size=BATCH_SIZE,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )

    model = TunableANN(
        input_size=X_train.shape[1],
        hidden_layers=config["layers"],
    )
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config["lr"],
        weight_decay=WEIGHT_DECAY,
    )
    if pos_weight is not None:
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    else:
        loss_fn = nn.BCEWithLogitsLoss()

    outer_batches_per_epoch = len(loader)
    steps_run = 0

    if target_steps is not None:
        # Step-adjusted refitting to ensure total optimizer updates match early stopping
        while steps_run < target_steps:
            model.train()
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                logits = model(batch_X)
                loss = loss_fn(logits, batch_y)
                loss.backward()
                optimizer.step()
                steps_run += 1
                if steps_run >= target_steps:
                    break
    elif epochs is not None:
        # Traditional fixed epoch refit (unadjusted step count)
        for _ in range(epochs):
            model.train()
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                logits = model(batch_X)
                loss = loss_fn(logits, batch_y)
                loss.backward()
                optimizer.step()
                steps_run += 1
    else:
        raise ValueError("Must specify either target_steps or epochs.")

    return model, scaler, steps_run, outer_batches_per_epoch


def calculate_metrics(y_true, probabilities):
    predictions = (probabilities >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(
        y_true, predictions, labels=[0, 1]
    ).ravel()

    return {
        "Accuracy": accuracy_score(y_true, predictions),
        "Precision": precision_score(
            y_true, predictions, zero_division=0
        ),
        "Sensitivity": recall_score(
            y_true, predictions, zero_division=0
        ),
        "Specificity": tn / (tn + fp) if tn + fp else 0.0,
        "F1_Score": f1_score(
            y_true, predictions, zero_division=0
        ),
        "AUROC": roc_auc_score(y_true, probabilities),
        "Brier_Score": brier_score_loss(y_true, probabilities),
        "Mean_Probability": float(np.mean(probabilities)),
    }


# --------------------------------------------------
# 4. Load dataset and create shared folds
# --------------------------------------------------

df = pd.read_csv(DATA_PATH)
X = df.drop(columns=["DEATH_EVENT", "time"])
y = df["DEATH_EVENT"].astype(int)

cv = StratifiedKFold(
    n_splits=FOLDS,
    shuffle=True,
    random_state=SEED,
)

# Materialize once so every model uses exactly the same folds.
splits = list(cv.split(X, y))
all_results = []

# --------------------------------------------------
# 5. Evaluate Logistic Regression baseline
# --------------------------------------------------

for fold, (train_idx, val_idx) in enumerate(splits, start=1):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, random_state=SEED),
    )
    model.fit(X_train, y_train)

    probabilities = model.predict_proba(X_val)[:, 1]
    metrics = calculate_metrics(y_val.to_numpy(), probabilities)

    all_results.append({
        "Model": "Logistic_Regression",
        "Fold": fold,
        **metrics,
    })

    print(
        f"Logistic Regression | Fold {fold} | "
        f"Accuracy={metrics['Accuracy']:.3f} | "
        f"AUROC={metrics['AUROC']:.3f}"
    )


# --------------------------------------------------
# 6. Evaluate Controlled ANN Configurations (Phase 1)
# --------------------------------------------------

EXPERIMENTS = [
    {
        "name": "ANN_32_16_BCEWithLogits_StepAdjusted_Unweighted",
        "layers": [32, 16],
        "lr": 0.001,
        "step_adjusted": True,
        "weighted": False,
    },
    {
        "name": "ANN_32_16_BCEWithLogits_StepAdjusted_Weighted",
        "layers": [32, 16],
        "lr": 0.001,
        "step_adjusted": True,
        "weighted": True,
    },
    {
        "name": "ANN_32_16_BCEWithLogits_UnadjustedRefit_Unweighted",
        "layers": [32, 16],
        "lr": 0.001,
        "step_adjusted": False,
        "weighted": False,
    },
    {
        "name": "ANN_32_16_BCEWithLogits_UnadjustedRefit_Weighted",
        "layers": [32, 16],
        "lr": 0.001,
        "step_adjusted": False,
        "weighted": True,
    },
]

print("\n" + "=" * 65)
print("ANN PHASE 1 CONTROLLED EXPERIMENTS — 5-FOLD STRATIFIED CV")
print("=" * 65)

for exp_index, exp in enumerate(EXPERIMENTS):
    print(f"\n>>> Running Experiment: {exp['name']} <<<")
    for fold, (train_idx, val_idx) in enumerate(splits, start=1):
        X_outer_train = X.iloc[train_idx]
        X_outer_val = X.iloc[val_idx]
        y_outer_train = y.iloc[train_idx]
        y_outer_val = y.iloc[val_idx]

        # Inner split: early stopping only (untouched outer test fold isolated)
        inner_train_idx, stop_idx = train_test_split(
            np.arange(len(X_outer_train)),
            test_size=0.2,
            random_state=SEED,
            stratify=y_outer_train,
        )

        X_inner = X_outer_train.iloc[inner_train_idx]
        y_inner = y_outer_train.iloc[inner_train_idx]
        X_stop = X_outer_train.iloc[stop_idx]
        y_stop = y_outer_train.iloc[stop_idx]

        # Compute fold-specific class weights using training labels only
        if exp["weighted"]:
            y_inner_arr = y_inner.to_numpy()
            inner_pos = int(np.sum(y_inner_arr == 1))
            inner_neg = int(np.sum(y_inner_arr == 0))
            inner_pw = torch.tensor([inner_neg / inner_pos], dtype=torch.float32)

            y_outer_arr = y_outer_train.to_numpy()
            outer_pos = int(np.sum(y_outer_arr == 1))
            outer_neg = int(np.sum(y_outer_arr == 0))
            outer_pw = torch.tensor([outer_neg / outer_pos], dtype=torch.float32)
        else:
            inner_pw = None
            outer_pw = None

        seed_value = SEED + fold + exp_index * 100

        # Run inner early stopping
        es_result = train_with_early_stopping(
            X_inner,
            y_inner,
            X_stop,
            y_stop,
            exp,
            seed=seed_value,
            pos_weight=inner_pw,
        )

        best_epoch = es_result["best_epoch"]
        target_steps = es_result["total_inner_steps"]
        inner_batches = es_result["inner_batches_per_epoch"]

        # Refit model on the complete outer training fold
        if exp["step_adjusted"]:
            model, scaler, steps_run, outer_batches = fit_final_fold_model(
                X_outer_train,
                y_outer_train,
                exp,
                seed=seed_value,
                target_steps=target_steps,
                pos_weight=outer_pw,
            )
        else:
            model, scaler, steps_run, outer_batches = fit_final_fold_model(
                X_outer_train,
                y_outer_train,
                exp,
                seed=seed_value,
                epochs=best_epoch,
                pos_weight=outer_pw,
            )

        # Evaluate on the untouched outer validation fold
        X_val_scaled = scaler.transform(X_outer_val)
        val_tensor = torch.tensor(X_val_scaled, dtype=torch.float32)

        model.eval()
        with torch.inference_mode():
            logits = model(val_tensor)
            probabilities = torch.sigmoid(logits).numpy().ravel()

        metrics = calculate_metrics(y_outer_val.to_numpy(), probabilities)

        equiv_outer_epochs = steps_run / outer_batches

        all_results.append({
            "Model": exp["name"],
            "Fold": fold,
            "Inner_Best_Epoch": best_epoch,
            "Inner_Batches_Per_Epoch": inner_batches,
            "Target_Steps": target_steps,
            "Outer_Batches_Per_Epoch": outer_batches,
            "Outer_Steps_Run": steps_run,
            "Equivalent_Outer_Epochs": round(equiv_outer_epochs, 2),
            "Pos_Weight": float(outer_pw.item()) if outer_pw is not None else 1.0,
            **metrics,
        })

        print(
            f"Fold {fold} | Inner Best Epoch={best_epoch:2d} (Steps={target_steps:3d}) | "
            f"Outer Steps Run={steps_run:3d} (~{equiv_outer_epochs:.1f} eps) | "
            f"AUROC={metrics['AUROC']:.4f} | Sens={metrics['Sensitivity']:.4f} | "
            f"Spec={metrics['Specificity']:.4f} | Brier={metrics['Brier_Score']:.4f}"
        )


# --------------------------------------------------
# 7. Save per-fold results and summary
# --------------------------------------------------

results_df = pd.DataFrame(all_results)
results_path = RESULTS_DIR / "ann_tuning_fold_results.csv"
phase1_results_path = RESULTS_DIR / "ann_phase1_experiments_fold_results.csv"
results_df.to_csv(results_path, index=False)
results_df.to_csv(phase1_results_path, index=False)

metric_names = [
    "Accuracy",
    "Precision",
    "Sensitivity",
    "Specificity",
    "F1_Score",
    "AUROC",
    "Brier_Score",
    "Mean_Probability",
]

summary_rows = []

for model_name, group in results_df.groupby("Model", sort=False):
    for metric in metric_names:
        summary_rows.append({
            "Model": model_name,
            "Metric": metric,
            "Mean": group[metric].mean(),
            "Standard_Deviation": group[metric].std(ddof=1),
        })

summary_df = pd.DataFrame(summary_rows)
summary_path = RESULTS_DIR / "ann_tuning_summary.csv"
phase1_summary_path = RESULTS_DIR / "ann_phase1_experiments_summary.csv"
summary_df.to_csv(summary_path, index=False)
summary_df.to_csv(phase1_summary_path, index=False)

print("\n" + "=" * 65)
print("ANN PHASE 1 EXPERIMENTAL SUMMARY (5-FOLD STRATIFIED CV)")
print("=" * 65)
print(summary_df.to_string(index=False))
print(f"\nFold results: {results_path}")
print(f"Summary:      {summary_path}")


