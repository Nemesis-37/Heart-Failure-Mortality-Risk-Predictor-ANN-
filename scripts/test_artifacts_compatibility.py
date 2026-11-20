import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import torch
import numpy as np
import pandas as pd
import sklearn
from models.ann_model import HeartFailureANN

print("=== Library Versions ===")
print("NumPy:", np.__version__)
print("Pandas:", pd.__version__)
print("Scikit-Learn:", sklearn.__version__)
print("PyTorch:", torch.__version__)
print("Joblib:", joblib.__version__)

print("\n=== Testing Artifact Loading ===")
MODELS_DIR = PROJECT_ROOT / "models"

# 1. LR Model & Features
lr_model = joblib.load(MODELS_DIR / "logistic_regression_pipeline.joblib")
print("✓ Logistic Regression Pipeline loaded:", type(lr_model))

lr_features = joblib.load(MODELS_DIR / "feature_names.joblib")
print("✓ LR Features loaded:", lr_features)

# 2. ANN Scaler & Features
ann_scaler = joblib.load(MODELS_DIR / "ann_scaler.joblib")
print("✓ ANN Scaler loaded:", type(ann_scaler))

ann_features = joblib.load(MODELS_DIR / "ann_feature_names.joblib")
print("✓ ANN Features loaded:", ann_features)

# 3. ANN PyTorch Weights
ann_model = HeartFailureANN()
weights = torch.load(MODELS_DIR / "ann_model.pth", weights_only=True)
ann_model.load_state_dict(weights)
ann_model.eval()
print("✓ ANN PyTorch Model loaded and set to eval mode")

print("\n=== Testing Inference Execution ===")
sample_data = pd.DataFrame([{
    "age": 65.0,
    "anaemia": 0,
    "creatinine_phosphokinase": 150.0,
    "diabetes": 0,
    "ejection_fraction": 38.0,
    "high_blood_pressure": 0,
    "platelets": 250000.0,
    "serum_creatinine": 1.1,
    "serum_sodium": 137.0,
    "sex": 1,
    "smoking": 0
}])

# Test LR
lr_pred = lr_model.predict(sample_data)[0]
lr_prob = lr_model.predict_proba(sample_data)[0][1]
print(f"✓ LR Prediction: class={lr_pred}, prob={lr_prob:.4f}")

# Test ANN
scaled = ann_scaler.transform(sample_data)
with torch.inference_mode():
    ann_prob = float(ann_model(torch.tensor(scaled, dtype=torch.float32)).item())
ann_pred = int(ann_prob >= 0.5)
print(f"✓ ANN Prediction: class={ann_pred}, prob={ann_prob:.4f}")

print("\nALL ARTIFACTS AND PREDICTIONS VERIFIED SUCCESSFULLY!")
