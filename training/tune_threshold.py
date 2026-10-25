
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dataset" / "heart_failure_clinical_records_dataset.csv"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SEED = 42
FOLDS = 5
EPOCHS = 100
PATIENCE = 10
BATCH_SIZE = 32
LEARNING_RATE = 0.001
WEIGHT_DECAY = 0.0001
TARGET_SENSITIVITY = 0.70


class HeartFailureANN(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.network(x)


def train_model(X_train, y_train, X_stop, y_stop, seed):
    torch.manual_seed(seed)
    np.random.seed(seed)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_stop_scaled = scaler.transform(X_stop)

    train_X = torch.tensor(X_train_scaled, dtype=torch.float32)
    train_y = torch.tensor(
        np.asarray(y_train), dtype=torch.float32
    ).reshape(-1, 1)
    stop_X = torch.tensor(X_stop_scaled, dtype=torch.float32)
    stop_y = torch.tensor(
        np.asarray(y_stop), dtype=torch.float32
    ).reshape(-1, 1)

    loader = DataLoader(
        TensorDataset(train_X, train_y),
        batch_size=BATCH_SIZE,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )

    model = HeartFailureANN(X_train.shape[1])
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )
    loss_fn = nn.BCELoss()

    best_loss = float("inf")
    best_state = None
    best_epoch = 1
    patience_count = 0

    for epoch in range(1, EPOCHS + 1):
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
            best_state = {
                k: v.detach().clone()
                for k, v in model.state_dict().items()
            }
            best_epoch = epoch
            patience_count = 0
        else:
            patience_count += 1

        if patience_count >= PATIENCE:
            break

    model.load_state_dict(best_state)
    return model, scaler, best_epoch


def get_metrics(y_true, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(
        y_true, predictions, labels=[0, 1]
    ).ravel()

    return {
        "Threshold": threshold,
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
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
    }


# Load data, excluding the leakage-prone "time" feature
df = pd.read_csv(DATA_PATH)
X = df.drop(columns=["DEATH_EVENT", "time"])
y = df["DEATH_EVENT"].astype(int)

# Each row will receive a prediction from a model that did not
# train on that row. Threshold choice is exploratory on these
# out-of-fold predictions, not an unbiased final performance estimate.
oof_probabilities = np.full(len(X), np.nan)

cv = StratifiedKFold(
    n_splits=FOLDS, shuffle=True, random_state=SEED
)

for fold, (train_idx, val_idx) in enumerate(cv.split(X, y), 1):
    X_outer = X.iloc[train_idx]
    y_outer = y.iloc[train_idx]
    X_val = X.iloc[val_idx]

    inner_train_idx, stop_idx = train_test_split(
        np.arange(len(X_outer)),
        test_size=0.20,
        random_state=SEED + fold,
        stratify=y_outer,
    )

    model, scaler, best_epoch = train_model(
        X_outer.iloc[inner_train_idx],
        y_outer.iloc[inner_train_idx],
        X_outer.iloc[stop_idx],
        y_outer.iloc[stop_idx],
        seed=SEED + fold,
    )

    X_val_scaled = scaler.transform(X_val)
    X_val_tensor = torch.tensor(
        X_val_scaled, dtype=torch.float32
    )

    model.eval()
    with torch.inference_mode():
        probabilities = model(X_val_tensor).numpy().ravel()

    oof_probabilities[val_idx] = probabilities
    print(f"Fold {fold}: best epoch = {best_epoch}")

if np.isnan(oof_probabilities).any():
    raise RuntimeError("Some out-of-fold predictions are missing.")

# Evaluate thresholds using the combined out-of-fold predictions.
y_true = y.to_numpy()
thresholds = np.arange(0.10, 0.81, 0.01)

rows = [
    get_metrics(y_true, oof_probabilities, float(threshold))
    for threshold in thresholds
]
results = pd.DataFrame(rows)

# Among thresholds meeting the target sensitivity, select the
# one with the highest specificity. If none qualify, use the
# threshold with the highest sensitivity.
eligible = results[
    results["Sensitivity"] >= TARGET_SENSITIVITY
]

if not eligible.empty:
    chosen = eligible.sort_values(
        ["Specificity", "Precision"], ascending=False
    ).iloc[0]
else:
    chosen = results.sort_values(
        ["Sensitivity", "Specificity"], ascending=False
    ).iloc[0]

results.to_csv(
    RESULTS_DIR / "ann_threshold_results.csv", index=False
)

print("\nSelected exploratory threshold:")
print(chosen.to_string())
print("\nThreshold results saved to results/ann_threshold_results.csv")
print(
    "\nThis threshold is exploratory. Use a separate untouched "
    "test set or nested cross-validation for an unbiased final estimate."
)





