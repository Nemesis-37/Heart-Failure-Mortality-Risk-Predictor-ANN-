
import copy
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

import sys
from pathlib import Path

# Locate project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add project root to Python's import path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.ann_model import HeartFailureANN


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = (
    PROJECT_ROOT
    / "dataset"
    / "heart_failure_clinical_records_dataset.csv"
)
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
N_SPLITS = 5
EPOCHS = 100
PATIENCE = 10
BATCH_SIZE = 32
LEARNING_RATE = 0.001
WEIGHT_DECAY = 0.0001

torch.manual_seed(RANDOM_STATE)
np.random.seed(RANDOM_STATE)


# --------------------------------------------------
# 2. Load data
# --------------------------------------------------

df = pd.read_csv(DATA_PATH)

X = df.drop(columns=["DEATH_EVENT", "time"])
y = df["DEATH_EVENT"].astype(int)

print("Dataset shape:", X.shape)
print("Target distribution:")
print(y.value_counts().sort_index())


# --------------------------------------------------
# 3. Five-fold cross-validation
# --------------------------------------------------

skf = StratifiedKFold(
    n_splits=N_SPLITS,
    shuffle=True,
    random_state=RANDOM_STATE,
)

fold_results = []
best_fold_loss = float("inf")
best_fold_state = None
best_fold_scaler = None
best_fold_number = None
best_fold_features = list(X.columns)

for fold, (train_idx, val_idx) in enumerate(
    skf.split(X, y), start=1
):
    print(f"\n{'=' * 50}")
    print(f"FOLD {fold}/{N_SPLITS}")
    print(f"{'=' * 50}")

    X_train = X.iloc[train_idx]
    X_val = X.iloc[val_idx]
    y_train = y.iloc[train_idx]
    y_val = y.iloc[val_idx]

    # Fit scaler on training data only
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    X_train_tensor = torch.tensor(
        X_train_scaled, dtype=torch.float32
    )
    X_val_tensor = torch.tensor(
        X_val_scaled, dtype=torch.float32
    )
    y_train_tensor = torch.tensor(
        y_train.to_numpy(), dtype=torch.float32
    ).reshape(-1, 1)
    y_val_tensor = torch.tensor(
        y_val.to_numpy(), dtype=torch.float32
    ).reshape(-1, 1)

    train_dataset = TensorDataset(
        X_train_tensor, y_train_tensor
    )
    generator = torch.Generator().manual_seed(
        RANDOM_STATE + fold
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        generator=generator,
    )

    # Fresh model and optimizer for every fold
    model = HeartFailureANN()
    loss_function = nn.BCELoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )

    best_val_loss = float("inf")
    best_state = None
    epochs_without_improvement = 0

    # --------------------------------------------------
    # 4. Training with early stopping
    # --------------------------------------------------

    for epoch in range(EPOCHS):
        model.train()
        total_train_loss = 0.0

        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()

            predictions = model(batch_X)
            loss = loss_function(predictions, batch_y)

            loss.backward()
            optimizer.step()

            total_train_loss += loss.item() * len(batch_X)

        average_train_loss = (
            total_train_loss / len(train_dataset)
        )

        model.eval()
        with torch.inference_mode():
            val_probabilities_tensor = model(X_val_tensor)
            val_loss = loss_function(
                val_probabilities_tensor, y_val_tensor
            ).item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = copy.deepcopy(model.state_dict())
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        if (epoch + 1) % 10 == 0:
            print(
                f"Epoch {epoch + 1:03d} | "
                f"Train Loss: {average_train_loss:.4f} | "
                f"Val Loss: {val_loss:.4f}"
            )

        if epochs_without_improvement >= PATIENCE:
            print(f"Early stopping at epoch {epoch + 1}")
            break

    # Restore this fold's best validation-loss weights
    if best_state is None:
        raise RuntimeError(
            f"No best model state saved for fold {fold}"
        )

    model.load_state_dict(best_state)
    model.eval()

    # --------------------------------------------------
    # 5. Evaluate the fold
    # --------------------------------------------------

    with torch.inference_mode():
        probabilities = (
            model(X_val_tensor).cpu().numpy().ravel()
        )

    predictions = (probabilities >= 0.5).astype(int)
    y_true = y_val.to_numpy()

    tn, fp, fn, tp = confusion_matrix(
        y_true, predictions, labels=[0, 1]
    ).ravel()

    specificity = (
        tn / (tn + fp) if (tn + fp) > 0 else 0.0
    )
    auroc = roc_auc_score(y_true, probabilities)

    metrics = {
        "Fold": fold,
        "Accuracy": accuracy_score(y_true, predictions),
        "Precision": precision_score(
            y_true, predictions, zero_division=0
        ),
        "Sensitivity": recall_score(
            y_true, predictions, zero_division=0
        ),
        "Specificity": specificity,
        "F1_Score": f1_score(
            y_true, predictions, zero_division=0
        ),
        "AUROC": auroc,
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
        "Best_Validation_Loss": best_val_loss,
    }

    fold_results.append(metrics)

    print(
        f"Accuracy: {metrics['Accuracy']:.4f} | "
        f"AUROC: {metrics['AUROC']:.4f} | "
        f"Sensitivity: {metrics['Sensitivity']:.4f} | "
        f"Specificity: {metrics['Specificity']:.4f}"
    )

    # Retain the fold with the lowest best validation loss.
    # This is for a convenient inference artifact, not a
    # replacement for the five-fold evaluation.
    if best_val_loss < best_fold_loss:
        best_fold_loss = best_val_loss
        best_fold_state = copy.deepcopy(model.state_dict())
        best_fold_scaler = copy.deepcopy(scaler)
        best_fold_number = fold


# --------------------------------------------------
# 6. Save fold results and summary
# --------------------------------------------------

fold_df = pd.DataFrame(fold_results)

fold_metrics_path = RESULTS_DIR / "ann_5fold_results.csv"
fold_df.to_csv(fold_metrics_path, index=False)

metric_names = [
    "Accuracy",
    "Precision",
    "Sensitivity",
    "Specificity",
    "F1_Score",
    "AUROC",
]

summary_rows = []

for metric in metric_names:
    summary_rows.append({
        "Metric": metric,
        "Mean": fold_df[metric].mean(),
        "Standard_Deviation": fold_df[metric].std(ddof=1),
    })

summary_df = pd.DataFrame(summary_rows)
summary_path = RESULTS_DIR / "ann_5fold_summary.csv"
summary_df.to_csv(summary_path, index=False)

print(f"\n{'=' * 50}")
print("ANN FIVE-FOLD SUMMARY")
print(f"{'=' * 50}")
print(summary_df.to_string(index=False))

print(f"\nFold results saved to: {fold_metrics_path}")
print(f"Summary saved to: {summary_path}")


# --------------------------------------------------
# 7. Save one fold's model for inference testing
# --------------------------------------------------

if best_fold_state is not None:
    models_dir = PROJECT_ROOT / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    torch.save(
        best_fold_state,
        models_dir / "ann_model.pth",
    )
    joblib.dump(
        best_fold_scaler,
        models_dir / "ann_scaler.joblib",
    )
    joblib.dump(
        best_fold_features,
        models_dir / "ann_feature_names.joblib",
    )

    print(
        f"\nSaved inference artifacts from fold "
        f"{best_fold_number}."
    )
    print(
        "Note: this artifact is from one fold, "
        "not a model trained on the full dataset."
    )
