
import os
import sys
import copy
import random
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

# Project root and models directory
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
if MODELS_DIR not in sys.path:
    sys.path.insert(0, MODELS_DIR)

from ann_model import HeartFailureANN


# ============================================================
# STEP 8.8 — ANN 5-FOLD CROSS-VALIDATION
# ============================================================

SEED = 42
EPOCHS = 100
PATIENCE = 10
BATCH_SIZE = 32
LEARNING_RATE = 0.001
WEIGHT_DECAY = 0.0001

torch.manual_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)

# Load dataset
DATA_PATH = os.path.join(
    PROJECT_ROOT,
    "dataset",
    "heart_failure_clinical_records_dataset.csv"
)
df = pd.read_csv(DATA_PATH)

# Exclude target and leakage-prone time column
X = df.drop(columns=["DEATH_EVENT", "time"])
y = df["DEATH_EVENT"]

# Create output folder
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Five outer folds
outer_cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=SEED
)

fold_results = []

print("=" * 65)
print("ANN — STRATIFIED 5-FOLD CROSS-VALIDATION")
print("=" * 65)
print("Dataset samples:", len(X))
print("Input features:", X.shape[1])
print("Maximum epochs:", EPOCHS)
print("Early stopping patience:", PATIENCE)


for fold, (outer_train_idx, test_idx) in enumerate(
    outer_cv.split(X, y), start=1
):
    print(f"\n{'=' * 25} FOLD {fold} {'=' * 25}")

    # --------------------------------------------------------
    # 1. Separate outer training data and untouched test data
    # --------------------------------------------------------
    X_outer_train = X.iloc[outer_train_idx]
    y_outer_train = y.iloc[outer_train_idx]

    X_test = X.iloc[test_idx]
    y_test = y.iloc[test_idx]

    # Internal split for training and early stopping
    inner_train_idx, inner_val_idx = train_test_split(
        np.arange(len(X_outer_train)),
        test_size=0.20,
        random_state=SEED + fold,
        stratify=y_outer_train
    )

    X_train = X_outer_train.iloc[inner_train_idx]
    y_train = y_outer_train.iloc[inner_train_idx]

    X_val = X_outer_train.iloc[inner_val_idx]
    y_val = y_outer_train.iloc[inner_val_idx]

    # --------------------------------------------------------
    # 2. Scale using inner training data only
    # --------------------------------------------------------
    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # Convert data to PyTorch tensors
    X_train_tensor = torch.tensor(
        X_train_scaled, dtype=torch.float32
    )
    X_val_tensor = torch.tensor(
        X_val_scaled, dtype=torch.float32
    )
    X_test_tensor = torch.tensor(
        X_test_scaled, dtype=torch.float32
    )

    y_train_tensor = torch.tensor(
        y_train.to_numpy(), dtype=torch.float32
    ).reshape(-1, 1)

    y_val_tensor = torch.tensor(
        y_val.to_numpy(), dtype=torch.float32
    ).reshape(-1, 1)

    # --------------------------------------------------------
    # 3. Create training batches and model
    # --------------------------------------------------------
    train_dataset = TensorDataset(
        X_train_tensor, y_train_tensor
    )

    loader_generator = torch.Generator()
    loader_generator.manual_seed(SEED + fold)

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        generator=loader_generator
    )

    # Reset model initialization for reproducibility
    torch.manual_seed(SEED + fold)

    model = HeartFailureANN()

    loss_function = nn.BCEWithLogitsLoss()

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY
    )

    # --------------------------------------------------------
    # 4. Train with early stopping on internal validation data
    # --------------------------------------------------------
    best_val_loss = float("inf")
    best_model_state = None
    epochs_without_improvement = 0
    best_epoch = 0

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

        with torch.no_grad():
            val_predictions = model(X_val_tensor)
            val_loss = loss_function(
                val_predictions, y_val_tensor
            ).item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_state = copy.deepcopy(
                model.state_dict()
            )
            best_epoch = epoch + 1
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        if epochs_without_improvement >= PATIENCE:
            break

    # Restore the best internal-validation model
    if best_model_state is not None:
        model.load_state_dict(best_model_state)

    # --------------------------------------------------------
    # 5. Evaluate once on the untouched outer test fold
    # --------------------------------------------------------
    model.eval()

    with torch.no_grad():
        test_logits = model(X_test_tensor)
        test_probabilities = (
            torch.sigmoid(test_logits).cpu().numpy().ravel()
        )

    test_predictions = (
        test_probabilities >= 0.5
    ).astype(int)

    y_true = y_test.to_numpy()

    accuracy = accuracy_score(y_true, test_predictions)
    precision = precision_score(
        y_true, test_predictions, zero_division=0
    )
    sensitivity = recall_score(
        y_true, test_predictions, zero_division=0
    )
    f1 = f1_score(
        y_true, test_predictions, zero_division=0
    )

    tn, fp, fn, tp = confusion_matrix(
        y_true, test_predictions, labels=[0, 1]
    ).ravel()

    specificity = (
        tn / (tn + fp) if (tn + fp) > 0 else 0.0
    )

    auroc = roc_auc_score(y_true, test_probabilities)

    fold_result = {
        "Fold": fold,
        "Best_Epoch": best_epoch,
        "Best_Validation_Loss": best_val_loss,
        "Accuracy": accuracy,
        "Precision": precision,
        "Sensitivity": sensitivity,
        "Specificity": specificity,
        "F1_Score": f1,
        "AUROC": auroc,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "TP": tp
    }

    fold_results.append(fold_result)

    print("Training samples:", len(X_train))
    print("Internal validation samples:", len(X_val))
    print("Outer test samples:", len(X_test))
    print("Best epoch:", best_epoch)
    print(f"Best validation loss: {best_val_loss:.4f}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Sensitivity: {sensitivity:.4f}")
    print(f"Specificity: {specificity:.4f}")
    print(f"F1-score: {f1:.4f}")
    print(f"AUROC: {auroc:.4f}")
    print(f"Confusion matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}")


# ============================================================
# STEP 8.9 — SAVE RESULTS AND SUMMARIZE PERFORMANCE
# ============================================================

results_df = pd.DataFrame(fold_results)

results_path = os.path.join(RESULTS_DIR, "ann_5fold_results.csv")
results_df.to_csv(results_path, index=False)

metric_columns = [
    "Accuracy",
    "Precision",
    "Sensitivity",
    "Specificity",
    "F1_Score",
    "AUROC"
]

summary_df = pd.DataFrame({
    "Metric": metric_columns,
    "Mean": [
        results_df[column].mean()
        for column in metric_columns
    ],
    "Standard_Deviation": [
        results_df[column].std(ddof=1)
        for column in metric_columns
    ]
})

summary_path = os.path.join(RESULTS_DIR, "ann_5fold_summary.csv")
summary_df.to_csv(summary_path, index=False)

print("\n" + "=" * 65)
print("ANN 5-FOLD CROSS-VALIDATION SUMMARY")
print("=" * 65)

print(summary_df.to_string(index=False, float_format="%.4f"))

print("\nFold results saved to:", results_path)
print("Summary saved to:", summary_path)
print("\nANN 5-fold evaluation completed.")







