"""
Patient-specific Logistic Regression feature contribution explainer.

Computes exact log-odds contributions from the frozen production pipeline:
    models/logistic_regression_pipeline.joblib

For a StandardScaler -> LogisticRegression pipeline:
    standardized_i = (x_i - mean_i) / scale_i
    contribution_i = standardized_i * coef_i
    logit = intercept + sum_i(contribution_i)

This identity mathematically reconstructs `pipeline.decision_function(X)[0]`
without modifying, retraining, or approximating the production model.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence
import numpy as np
import pandas as pd


CLINICAL_FEATURE_METADATA: Dict[str, Dict[str, Any]] = {
    "age": {
        "label": "Age",
        "unit": "years",
        "type": "continuous",
        "modifiable": False,
    },
    "anaemia": {
        "label": "Anaemia",
        "unit": "Hb < 12 g/dL",
        "type": "binary",
        "true_text": "Present (1)",
        "false_text": "Absent (0)",
        "modifiable": True,
    },
    "creatinine_phosphokinase": {
        "label": "Creatinine Phosphokinase",
        "unit": "mcg/L",
        "type": "continuous",
        "modifiable": True,
    },
    "diabetes": {
        "label": "Diabetes",
        "unit": "Diagnosis",
        "type": "binary",
        "true_text": "Yes (1)",
        "false_text": "No (0)",
        "modifiable": True,
    },
    "ejection_fraction": {
        "label": "Ejection Fraction",
        "unit": "%",
        "type": "continuous",
        "modifiable": True,
    },
    "high_blood_pressure": {
        "label": "High Blood Pressure",
        "unit": "Hypertension",
        "type": "binary",
        "true_text": "Yes (1)",
        "false_text": "No (0)",
        "modifiable": True,
    },
    "platelets": {
        "label": "Platelets",
        "unit": "cells/µL",
        "type": "continuous",
        "modifiable": True,
    },
    "serum_creatinine": {
        "label": "Serum Creatinine",
        "unit": "mg/dL",
        "type": "continuous",
        "modifiable": True,
    },
    "serum_sodium": {
        "label": "Serum Sodium",
        "unit": "mEq/L",
        "type": "continuous",
        "modifiable": True,
    },
    "sex": {
        "label": "Biological Sex",
        "unit": "0 = Female, 1 = Male",
        "type": "binary",
        "true_text": "Male (1)",
        "false_text": "Female (0)",
        "modifiable": False,
    },
    "smoking": {
        "label": "Smoking",
        "unit": "Tobacco history",
        "type": "binary",
        "true_text": "Yes (1)",
        "false_text": "No (0)",
        "modifiable": True,
    },
}


def _format_patient_value(feature_name: str, value: float, meta: Dict[str, Any]) -> str:
    """Format the patient's raw entered value with human-readable units/labels."""
    if meta.get("type") == "binary":
        return meta["true_text"] if int(round(value)) == 1 else meta["false_text"]

    if feature_name == "platelets":
        if abs(value - round(value)) < 1e-6:
            return f"{int(round(value)):,} {meta['unit']}"
        return f"{value:,.1f} {meta['unit']}"

    if feature_name in ("age", "ejection_fraction", "creatinine_phosphokinase", "serum_sodium"):
        if abs(value - round(value)) < 1e-6:
            num_str = str(int(round(value)))
        else:
            num_str = f"{value:.2f}".rstrip("0").rstrip(".")
        if meta["unit"] == "%":
            return f"{num_str}%"
        return f"{num_str} {meta['unit']}"

    num_str = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{num_str} {meta['unit']}"


def explain_logistic_prediction(
    lr_pipeline: Any,
    input_df: pd.DataFrame,
    feature_names: Sequence[str],
) -> Dict[str, Any]:
    """
    Compute exact per-feature log-odds contributions from the trained
    StandardScaler + LogisticRegression pipeline.
    """
    if "time" in feature_names or "time" in input_df.columns:
        raise ValueError("Forbidden post-baseline feature 'time' detected in explanation input.")
    if len(feature_names) != 11:
        raise ValueError(f"Expected 11 clinical features, found {len(feature_names)}.")

    # Extract fitted preprocessing steps (all steps except final classifier)
    named_steps = getattr(lr_pipeline, "named_steps", None)
    if named_steps and "scaler" in named_steps and "classifier" in named_steps:
        scaler = named_steps["scaler"]
        classifier = named_steps["classifier"]
    elif hasattr(lr_pipeline, "steps") and len(lr_pipeline.steps) >= 2:
        scaler = lr_pipeline.steps[0][1]
        classifier = lr_pipeline.steps[-1][1]
    else:
        raise RuntimeError("Unexpected Logistic Regression pipeline structure.")

    ordered_df = input_df[list(feature_names)]
    standardized_row = np.asarray(scaler.transform(ordered_df)[0], dtype=np.float64)
    coefficients = np.asarray(classifier.coef_[0], dtype=np.float64)
    intercept = float(classifier.intercept_[0])

    raw_values = ordered_df.iloc[0]
    raw_contributions = standardized_row * coefficients
    reconstructed_logit_raw = float(intercept + np.sum(raw_contributions))
    model_logit_raw = float(lr_pipeline.decision_function(ordered_df)[0])
    reconstruction_error = float(abs(reconstructed_logit_raw - model_logit_raw))

    scaler_means = getattr(scaler, "mean_", None)

    contributions: List[Dict[str, Any]] = []
    for idx, feat_name in enumerate(feature_names):
        meta = CLINICAL_FEATURE_METADATA.get(
            feat_name,
            {"label": feat_name, "unit": "", "type": "continuous", "modifiable": True},
        )
        raw_val = float(raw_values[feat_name])
        if meta.get("type") == "binary":
            patient_val: Any = int(round(raw_val))
        else:
            patient_val = round(raw_val, 4)

        contrib_val = float(raw_contributions[idx])
        if contrib_val > 1e-9:
            direction = "positive"
        elif contrib_val < -1e-9:
            direction = "negative"
        else:
            direction = "neutral"

        entry: Dict[str, Any] = {
            "feature": feat_name,
            "label": meta["label"],
            "unit": meta.get("unit", ""),
            "feature_type": meta.get("type", "continuous"),
            "modifiable": bool(meta.get("modifiable", True)),
            "patient_value": patient_val,
            "display_value": _format_patient_value(feat_name, raw_val, meta),
            "standardized_value": round(float(standardized_row[idx]), 6),
            "coefficient": round(float(coefficients[idx]), 6),
            "contribution": round(contrib_val, 6),
            "abs_contribution": round(float(abs(contrib_val)), 6),
            "direction": direction,
        }
        if scaler_means is not None and idx < len(scaler_means):
            entry["cohort_mean"] = round(float(scaler_means[idx]), 4)

        contributions.append(entry)

    # Sort descending by absolute contribution magnitude (deterministic tie-breaker)
    contributions.sort(key=lambda item: (-item["abs_contribution"], item["feature"]))

    return {
        "baseline_intercept": round(intercept, 6),
        "logit": round(model_logit_raw, 6),
        "reconstructed_logit": round(reconstructed_logit_raw, 6),
        "logit_reconstruction_error": reconstruction_error,
        "feature_contributions": contributions,
    }
