
import logging
from pathlib import Path

import joblib
import pandas as pd
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models.ann_model import HeartFailureANN

logger = logging.getLogger(__name__)

# Project paths
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

# Existing Logistic Regression artifacts
LR_MODEL_PATH = MODELS_DIR / "logistic_regression_pipeline.joblib"
LR_FEATURES_PATH = MODELS_DIR / "feature_names.joblib"

# Saved ANN artifacts
ANN_MODEL_PATH = MODELS_DIR / "ann_model.pth"
ANN_SCALER_PATH = MODELS_DIR / "ann_scaler.joblib"
ANN_FEATURES_PATH = MODELS_DIR / "ann_feature_names.joblib"

# Load Logistic Regression
lr_model = joblib.load(LR_MODEL_PATH)
lr_feature_names = joblib.load(LR_FEATURES_PATH)

# Load the trained ANN and its matching preprocessing artifacts
ann_scaler = joblib.load(ANN_SCALER_PATH)
ann_feature_names = joblib.load(ANN_FEATURES_PATH)

ann_model = HeartFailureANN()
ann_model.load_state_dict(
    torch.load(
        ANN_MODEL_PATH,
        map_location="cpu",
        weights_only=True,
    )
)
ann_model.eval()

app = FastAPI(
    title="Heart Failure Mortality Predictor",
    description="Educational machine-learning prototype, not a clinical tool.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PatientData(BaseModel):
    age: float
    anaemia: int
    creatinine_phosphokinase: float
    diabetes: int
    ejection_fraction: float
    high_blood_pressure: int
    platelets: float
    serum_creatinine: float
    serum_sodium: float
    sex: int
    smoking: int


def prepare_input(patient: PatientData, feature_names):
    patient_data = patient.model_dump()

    missing = set(feature_names) - set(patient_data)
    if missing:
        raise ValueError(f"Missing features: {sorted(missing)}")

    return pd.DataFrame(
        [[patient_data[name] for name in feature_names]],
        columns=feature_names,
    )


@app.get("/")
def home():
    return {
        "message": "Heart Failure Mortality Predictor API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "logistic_regression_loaded": lr_model is not None,
        "ann_loaded": True,
        "feature_count": len(ann_feature_names),
    }


@app.post("/predict")
def predict_logistic_regression(patient: PatientData):
    """Existing Logistic Regression prediction endpoint."""
    try:
        input_data = prepare_input(patient, lr_feature_names)

        prediction = int(lr_model.predict(input_data)[0])
        probability = float(
            lr_model.predict_proba(input_data)[0][1]
        )

        return {
            "model": "Logistic Regression",
            "predicted_class": prediction,
            "predicted_label": (
                "Death event predicted"
                if prediction == 1
                else "No death event predicted"
            ),
            "predicted_probability": round(probability, 4),
            "notice": (
                "Educational prototype only; "
                "not for medical decisions."
            ),
        }

    except Exception as exc:
        logger.exception("Logistic Regression prediction failed")
        raise HTTPException(
            status_code=500,
            detail="Prediction failed. Please try again.",
        ) from exc


@app.post("/predict-ann")
def predict_ann(patient: PatientData):
    """Prediction using the saved trained ANN."""
    try:
        input_data = prepare_input(patient, ann_feature_names)

        # Apply the scaler fitted during ANN training
        scaled_data = ann_scaler.transform(input_data)

        input_tensor = torch.tensor(
            scaled_data,
            dtype=torch.float32,
        )

        # Run inference with the saved trained weights
        with torch.inference_mode():
            probability = float(
                ann_model(input_tensor).item()
            )

        prediction = int(probability >= 0.5)

        return {
            "model": "Artificial Neural Network",
            "predicted_class": prediction,
            "predicted_label": (
                "Death event predicted"
                if prediction == 1
                else "No death event predicted"
            ),
            "predicted_probability": round(probability, 4),
            "notice": (
                "Educational prototype only; "
                "not for medical decisions."
            ),
        }

    except Exception as exc:
        logger.exception("ANN prediction failed")
        raise HTTPException(
            status_code=500,
            detail="ANN prediction failed. Please try again.",
        ) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


