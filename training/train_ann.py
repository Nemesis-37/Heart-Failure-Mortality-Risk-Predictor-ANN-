
import os
import sys
import copy
import pandas as pd
import torch
import torch.nn as nn

from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

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
# STEP 8.4 — ANN TRAINING WITH EARLY STOPPING
# ============================================================

# 1. Reproducibility
torch.manual_seed(42)

# 2. Load dataset
DATA_PATH = os.path.join(
    PROJECT_ROOT,
    "dataset",
    "heart_failure_clinical_records_dataset.csv"
)
df = pd.read_csv(DATA_PATH)

# 3. Separate features and target
# Exclude 'time' to avoid leakage
X = df.drop(columns=["DEATH_EVENT", "time"])
y = df["DEATH_EVENT"]

# 4. Select the first fold for this practice run
skf = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

train_index, val_index = next(skf.split(X, y))

X_train = X.iloc[train_index]
X_val = X.iloc[val_index]

y_train = y.iloc[train_index]
y_val = y.iloc[val_index]

# 5. Scale features using training data only
scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)

# 6. Convert data into PyTorch tensors
X_train_tensor = torch.tensor(
    X_train_scaled,
    dtype=torch.float32
)

X_val_tensor = torch.tensor(
    X_val_scaled,
    dtype=torch.float32
)

y_train_tensor = torch.tensor(
    y_train.to_numpy(),
    dtype=torch.float32
).reshape(-1, 1)

y_val_tensor = torch.tensor(
    y_val.to_numpy(),
    dtype=torch.float32
).reshape(-1, 1)

# 7. Create training batches
train_dataset = TensorDataset(
    X_train_tensor,
    y_train_tensor
)

train_loader = DataLoader(
    train_dataset,
    batch_size=32,
    shuffle=True
)

# 8. Create the ANN model
model = HeartFailureANN()

# 9. Define loss function and optimizer
loss_function = nn.BCELoss()

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=0.001,
    weight_decay=0.0001
)

# 10. Training settings
epochs = 100
patience = 10

best_val_loss = float("inf")
best_model_state = None
epochs_without_improvement = 0

print("=" * 60)
print("ANN TRAINING WITH EARLY STOPPING")
print("=" * 60)

print("Training samples:", len(X_train))
print("Validation samples:", len(X_val))
print("Input features:", X_train.shape[1])
print("Maximum epochs:", epochs)
print("Early stopping patience:", patience)

# ============================================================
# STEP 8.5 — SINGLE TRAINING LOOP
# ============================================================

for epoch in range(epochs):

    # -------------------------
    # Training phase
    # -------------------------
    model.train()
    total_train_loss = 0.0

    for batch_X, batch_y in train_loader:

        # Clear gradients from the previous batch
        optimizer.zero_grad()

        # Forward pass
        predictions = model(batch_X)

        # Calculate prediction error
        loss = loss_function(predictions, batch_y)

        # Backpropagation
        loss.backward()

        # Update model weights
        optimizer.step()

        total_train_loss += loss.item() * len(batch_X)

    average_train_loss = (
        total_train_loss / len(train_dataset)
    )

    # -------------------------
    # Validation phase
    # -------------------------
    model.eval()

    with torch.no_grad():
        val_predictions = model(X_val_tensor)

        val_loss = loss_function(
            val_predictions,
            y_val_tensor
        ).item()

    # -------------------------
    # Save the best model
    # -------------------------
    if val_loss < best_val_loss:

        best_val_loss = val_loss

        best_model_state = copy.deepcopy(
            model.state_dict()
        )

        epochs_without_improvement = 0

    else:
        epochs_without_improvement += 1

    # Print progress every 10 epochs
    if (epoch + 1) % 10 == 0:
        print(
            f"Epoch [{epoch + 1}/{epochs}] | "
            f"Train Loss: {average_train_loss:.4f} | "
            f"Validation Loss: {val_loss:.4f} | "
            f"Patience: "
            f"{epochs_without_improvement}/{patience}"
        )

    # Stop if validation loss does not improve
    if epochs_without_improvement >= patience:
        print(f"\nEarly stopping at epoch {epoch + 1}.")
        break

# ============================================================
# STEP 8.6 — RESTORE THE BEST MODEL
# ============================================================

if best_model_state is not None:
    model.load_state_dict(best_model_state)

print("\nANN training completed.")
print(f"Best validation loss: {best_val_loss:.4f}")
print("Best model weights restored.")




# ============================================================
# STEP 8.7 — ANN MODEL EVALUATION
# ============================================================

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)

# Put model in evaluation mode
model.eval()

# Generate validation probabilities
with torch.no_grad():
    val_probabilities = model(X_val_tensor).cpu().numpy().ravel()

# Convert probabilities into class predictions
threshold = 0.5
val_predictions = (val_probabilities >= threshold).astype(int)

# Calculate evaluation metrics
y_true = y_val.to_numpy()

accuracy = accuracy_score(y_true, val_predictions)
precision = precision_score(
    y_true, val_predictions, zero_division=0
)
sensitivity = recall_score(
    y_true, val_predictions, zero_division=0
)
f1 = f1_score(
    y_true, val_predictions, zero_division=0
)

# Confusion matrix: [[TN, FP], [FN, TP]]
tn, fp, fn, tp = confusion_matrix(
    y_true, val_predictions, labels=[0, 1]
).ravel()

specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

# AUROC uses probabilities, not class predictions
if len(set(y_true)) == 2:
    auroc = roc_auc_score(y_true, val_probabilities)
else:
    auroc = float("nan")

# Display results
print("\n" + "=" * 60)
print("ANN VALIDATION RESULTS")
print("=" * 60)

print(f"Accuracy:     {accuracy:.4f}")
print(f"Precision:    {precision:.4f}")
print(f"Sensitivity:  {sensitivity:.4f}")
print(f"Specificity:  {specificity:.4f}")
print(f"F1-score:     {f1:.4f}")
print(f"AUROC:        {auroc:.4f}")

print("\nConfusion Matrix:")
print(f"True Negatives (TN):  {tn}")
print(f"False Positives (FP): {fp}")
print(f"False Negatives (FN): {fn}")
print(f"True Positives (TP):  {tp}")

print("\nClassification Report:")
print(classification_report(
    y_true,
    val_predictions,
    labels=[0, 1],
    target_names=["No Death Event", "Death Event"],
    zero_division=0
))



# ============================================================
# STEP 8.8 — SAVE TRAINED ANN AND SCALER
# ============================================================

MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

# Save the best trained ANN weights
torch.save(
    model.state_dict(),
    os.path.join(MODEL_DIR, "ann_model.pth")
)

# Save the fitted scaler
import joblib

joblib.dump(
    scaler,
    os.path.join(MODEL_DIR, "ann_scaler.joblib")
)

# Save the expected feature order
joblib.dump(
    list(X.columns),
    os.path.join(MODEL_DIR, "ann_feature_names.joblib")
)

print("\nANN model, scaler, and feature names saved successfully.")


