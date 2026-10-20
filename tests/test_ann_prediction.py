
from pathlib import Path
import sys

import joblib
import pandas as pd
import torch

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.ann_model import HeartFailureANN

MODEL_DIR = PROJECT_ROOT / "models"

MODEL_PATH = MODEL_DIR / "ann_model.pth"
SCALER_PATH = MODEL_DIR / "ann_scaler.joblib"
FEATURES_PATH = MODEL_DIR / "ann_feature_names.joblib"


def main():
    # Check that all required files exist
    for path in (MODEL_PATH, SCALER_PATH, FEATURES_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Required file not found: {path}")

    # Load preprocessing artifacts
    scaler = joblib.load(SCALER_PATH)
    feature_names = joblib.load(FEATURES_PATH)

    # Initialize ANN and load trained weights
    model = HeartFailureANN()
    model.load_state_dict(
        torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    )
    model.eval()

    # Example input values for software testing only
    patient = {
        "age": 65,
        "anaemia": 0,
        "creatinine_phosphokinase": 146,
        "diabetes": 0,
        "ejection_fraction": 35,
        "high_blood_pressure": 1,
        "platelets": 250000,
        "serum_creatinine": 1.3,
        "serum_sodium": 137,
        "sex": 1,
        "smoking": 0,
    }

    # Validate and arrange features in training order
    missing = set(feature_names) - set(patient)
    if missing:
        raise ValueError(f"Missing patient features: {sorted(missing)}")

    input_df = pd.DataFrame(
        [[patient[name] for name in feature_names]],
        columns=feature_names,
    )

    # Apply the scaler fitted during training
    input_scaled = scaler.transform(input_df)
    input_tensor = torch.tensor(input_scaled, dtype=torch.float32)

    # Predict using the trained model
    with torch.inference_mode():
        probability = model(input_tensor).item()

    predicted_class = int(probability >= 0.5)

    print("=" * 40)
    print("TRAINED ANN PREDICTION")
    print("=" * 40)
    print(f"Probability output: {probability:.4f}")
    print(f"Predicted class:    {predicted_class}")
    print(f"Features used:      {len(feature_names)}")


if __name__ == "__main__":
    main()




