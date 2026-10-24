
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

CONFIGS = [
    {"name": "ANN_32_16_lr001", "layers": [32, 16], "lr": 0.001},
    {"name": "ANN_64_32_lr001", "layers": [64, 32], "lr": 0.001},
    {"name": "ANN_32_lr0001", "layers": [32], "lr": 0.0001},
]


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


# --------------------------------------------------
# 2. ANN architecture
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
            nn.Sigmoid(),
        ])

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


# --------------------------------------------------
# 3. Training helpers
# --------------------------------------------------

def to_tensors(X, y):
    return (
        torch.tensor(X, dtype=torch.float32),
        torch.tensor(np.asarray(y), dtype=torch.float32).reshape(-1, 1),
    )


def train_with_early_stopping(
    X_train, y_train, X_stop, y_stop, config, seed
):
    """Use an inner validation split only to select the epoch."""
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
    loss_fn = nn.BCELoss()

    best_loss = float("inf")
    best_state = None
    best_epoch = 1
    patience_count = 0

    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()

        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            loss = loss_fn(model(batch_X), batch_y)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.inference_mode():
            val_loss = loss_fn(model(stop_X), stop_y).item()

        if val_loss < best_loss:
            best_loss = val_loss
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch
            patience_count = 0
        else:
            patience_count += 1

        if patience_count >= PATIENCE:
            break

    return best_epoch


def fit_final_fold_model(X_train, y_train, config, epochs, seed):
    """Refit using all outer training data for the selected epoch count."""
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
    loss_fn = nn.BCELoss()

    for _ in range(epochs):
        model.train()
        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            loss = loss_fn(model(batch_X), batch_y)
            loss.backward()
            optimizer.step()

    return model, scaler


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
# 6. Evaluate each ANN configuration
# --------------------------------------------------

for config_index, config in enumerate(CONFIGS):
    for fold, (train_idx, val_idx) in enumerate(splits, start=1):
        X_outer_train = X.iloc[train_idx]
        X_outer_val = X.iloc[val_idx]
        y_outer_train = y.iloc[train_idx]
        y_outer_val = y.iloc[val_idx]

        # Inner split: early stopping only, not final evaluation.
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

        best_epoch = train_with_early_stopping(
            X_inner,
            y_inner,
            X_stop,
            y_stop,
            config,
            seed=SEED + fold + config_index * 100,
        )

        # Retrain on the complete outer training fold.
        model, scaler = fit_final_fold_model(
            X_outer_train,
            y_outer_train,
            config,
            epochs=best_epoch,
            seed=SEED + fold + config_index * 100,
        )

        # Evaluate once on the untouched outer validation fold.
        X_val_scaled = scaler.transform(X_outer_val)
        val_tensor = torch.tensor(
            X_val_scaled, dtype=torch.float32
        )

        model.eval()
        with torch.inference_mode():
            probabilities = (
                model(val_tensor).numpy().ravel()
            )

        metrics = calculate_metrics(
            y_outer_val.to_numpy(), probabilities
        )

        all_results.append({
            "Model": config["name"],
            "Fold": fold,
            "Best_Epoch": best_epoch,
            **metrics,
        })

        print(
            f"{config['name']} | Fold {fold} | "
            f"Epoch={best_epoch} | "
            f"Accuracy={metrics['Accuracy']:.3f} | "
            f"AUROC={metrics['AUROC']:.3f}"
        )


# --------------------------------------------------
# 7. Save per-fold results and summary
# --------------------------------------------------

results_df = pd.DataFrame(all_results)
results_path = RESULTS_DIR / "ann_tuning_fold_results.csv"
results_df.to_csv(results_path, index=False)

metric_names = [
    "Accuracy",
    "Precision",
    "Sensitivity",
    "Specificity",
    "F1_Score",
    "AUROC",
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
summary_df.to_csv(summary_path, index=False)

print("\nMODEL COMPARISON: FIVE-FOLD CV")
print(summary_df.to_string(index=False))
print(f"\nFold results: {results_path}")
print(f"Summary:      {summary_path}")


