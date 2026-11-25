"""
phase3_optimization.py
======================
Heart Failure Mortality Risk Predictor — ANN Optimization Phase 3
Decision-Threshold Optimization, Probability Calibration & Model Reliability Analysis.

Strict Evaluation Protocol:
- Stratified 5-Fold Cross-Validation (SEED=42, shuffle=True).
- Evaluates 3 Candidates:
  1. Logistic Regression Baseline (12 params)
  2. Arch C: 11 -> 32 -> 16 -> 1, unweighted, dropout 0.0, weight decay 0.001, batch size 64 (929 params)
  3. Arch B: 11 -> 16 -> 1, unweighted, dropout 0.2, weight decay 0.01, batch size 32 (209 params)
- Threshold selection strictly on inner validation data (Youden's J and F1 max).
- Calibration (Platt Scaling, Isotonic Regression) fitted strictly on inner validation data.
- Outer test folds completely isolated from threshold selection and calibration training.
- Outputs detailed metrics, calibration intercept/slope, ECE, Brier score, log loss, and confusion matrices.
"""

import copy
import math
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
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    log_loss,
    confusion_matrix,
    matthews_corrcoef,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dataset" / "heart_failure_clinical_records_dataset.csv"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SEED = 42
FOLDS = 5
MAX_EPOCHS = 100
PATIENCE = 10
THRESHOLD_GRID = np.round(np.linspace(0.10, 0.90, 17), 2)  # 0.10, 0.15, ..., 0.90


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class ConfigurableANN(nn.Module):
    def __init__(self, input_size, hidden_layers, dropout=0.2):
        super().__init__()
        layers = []
        prev = input_size
        for sz in hidden_layers:
            layers.append(nn.Linear(prev, sz))
            layers.append(nn.ReLU())
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            prev = sz
        layers.append(nn.Linear(prev, 1))
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)

    def predict_proba(self, x):
        return torch.sigmoid(self.forward(x))


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def to_tensors(X, y):
    return (
        torch.tensor(X, dtype=torch.float32),
        torch.tensor(np.asarray(y), dtype=torch.float32).reshape(-1, 1),
    )


def safe_logit(p, eps=1e-7):
    p = np.clip(p, eps, 1.0 - eps)
    return np.log(p / (1.0 - p))


def compute_calibration_curve(y_true, y_prob, n_bins=5):
    """Compute calibration curve data (mean predicted probability vs observed fraction of positives)."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers = []
    bin_empirical = []
    bin_counts = []
    
    for i in range(n_bins):
        low, high = bins[i], bins[i + 1]
        mask = (y_prob >= low) & (y_prob < high if i < n_bins - 1 else y_prob <= high)
        count = int(np.sum(mask))
        bin_counts.append(count)
        if count > 0:
            bin_centers.append(float(np.mean(y_prob[mask])))
            bin_empirical.append(float(np.mean(y_true[mask])))
        else:
            bin_centers.append(float((low + high) / 2))
            bin_empirical.append(0.0)
            
    return bin_centers, bin_empirical, bin_counts


def compute_expected_calibration_error(y_true, y_prob, n_bins=10):
    """Expected Calibration Error (ECE) with equal-width binning."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total = len(y_true)
    for i in range(n_bins):
        low, high = bins[i], bins[i + 1]
        mask = (y_prob >= low) & (y_prob < high if i < n_bins - 1 else y_prob <= high)
        count = np.sum(mask)
        if count > 0:
            conf = np.mean(y_prob[mask])
            acc = np.mean(y_true[mask])
            ece += (count / total) * abs(acc - conf)
    return float(ece)


def compute_calibration_slope_and_intercept(y_true, y_prob):
    """
    Standard clinical calibration analysis:
    - Calibration Slope (beta): logit(P(Y=1)) = alpha + beta * logit(p). Ideal beta = 1.0.
    - Calibration Intercept (alpha): logit(P(Y=1)) = alpha + 1.0 * logit(p). Ideal alpha = 0.0.
    """
    logits = safe_logit(y_prob).reshape(-1, 1)
    y = np.asarray(y_true, dtype=int)
    
    # Check if there is variation in y
    if len(np.unique(y)) < 2:
        return 1.0, 0.0
    
    try:
        # Calibration Slope
        lr_slope = LogisticRegression(penalty=None, solver='lbfgs', max_iter=1000)
        lr_slope.fit(logits, y)
        slope = float(lr_slope.coef_[0][0])
    except Exception:
        slope = float("nan")
        
    try:
        # Calibration Intercept (offset model fixing slope to 1)
        # Using statsmodels or simple Newton optimization if available, or offset optimization
        # Under logit model with offset z: P(Y=1) = sigmoid(alpha + z)
        # We can find alpha minimizing log loss:
        from scipy.optimize import minimize_scalar
        def neg_log_lik(alpha):
            p = 1.0 / (1.0 + np.exp(-(alpha + logits.ravel())))
            p = np.clip(p, 1e-15, 1 - 1e-15)
            return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
        res = minimize_scalar(neg_log_lik, bracket=[-2.0, 2.0])
        intercept = float(res.x) if res.success else 0.0
    except Exception:
        intercept = float("nan")
        
    return slope, intercept


def calculate_metrics_at_threshold(y_true, probabilities, threshold=0.50):
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    
    acc = accuracy_score(y_true, predictions)
    sens = recall_score(y_true, predictions, zero_division=0)
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    prec = precision_score(y_true, predictions, zero_division=0)
    f1 = f1_score(y_true, predictions, zero_division=0)
    try:
        mcc = matthews_corrcoef(y_true, predictions)
    except Exception:
        mcc = 0.0
        
    youden_j = sens + spec - 1.0
    
    return {
        "Threshold": float(threshold),
        "Accuracy": float(acc),
        "Sensitivity": float(sens),
        "Specificity": float(spec),
        "Precision": float(prec),
        "F1_Score": float(f1),
        "Youden_J": float(youden_j),
        "MCC": float(mcc),
        "True_Positives": int(tp),
        "False_Positives": int(fp),
        "True_Negatives": int(tn),
        "False_Negatives": int(fn),
    }


def select_best_thresholds_from_validation(y_val, val_probs):
    """
    Select optimal candidate thresholds strictly on inner validation data:
    1. Threshold maximizing Youden's J statistic (Sensitivity + Specificity - 1)
    2. Threshold maximizing F1 score
    3. Threshold providing balanced Sensitivity & Specificity
    """
    candidates = np.round(np.linspace(0.10, 0.90, 81), 2)  # fine 0.01-0.02 step
    best_youden_j = -1e9
    best_youden_thresh = 0.50
    best_f1 = -1e9
    best_f1_thresh = 0.50
    
    for th in candidates:
        m = calculate_metrics_at_threshold(y_val, val_probs, threshold=th)
        if m["Youden_J"] > best_youden_j:
            best_youden_j = m["Youden_J"]
            best_youden_thresh = th
        if m["F1_Score"] > best_f1:
            best_f1 = m["F1_Score"]
            best_f1_thresh = th
            
    return {
        "thresh_youden": best_youden_thresh,
        "val_youden_j": best_youden_j,
        "thresh_f1": best_f1_thresh,
        "val_best_f1": best_f1,
    }


def train_ann_with_early_stopping(X_train, y_train, X_stop, y_stop, config, seed):
    set_seed(seed)
    batch_size = config.get("batch_size", 32)
    lr = config.get("lr", 0.001)
    weight_decay = config.get("weight_decay", 0.001)
    dropout = config.get("dropout", 0.0)
    layers = config["layers"]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_stop_scaled = scaler.transform(X_stop)

    train_X, train_y = to_tensors(X_train_scaled, y_train)
    stop_X, stop_y = to_tensors(X_stop_scaled, y_stop)

    loader = DataLoader(
        TensorDataset(train_X, train_y),
        batch_size=batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )

    model = ConfigurableANN(
        input_size=X_train.shape[1],
        hidden_layers=layers,
        dropout=dropout,
    )

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=lr,
        weight_decay=weight_decay,
    )
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

    # Evaluate best inner model on inner stop set to get inner validation predictions & logits
    model.load_state_dict(best_state)
    model.eval()
    with torch.inference_mode():
        stop_logits = model(stop_X).numpy().ravel()
        stop_probs = torch.sigmoid(model(stop_X)).numpy().ravel()

    return {
        "best_epoch": best_epoch,
        "best_val_loss": best_loss,
        "total_inner_steps": total_inner_steps,
        "inner_stop_probs": stop_probs,
        "inner_stop_logits": stop_logits,
    }


def fit_final_outer_ann(X_train, y_train, config, seed, target_steps):
    set_seed(seed)
    batch_size = config.get("batch_size", 32)
    lr = config.get("lr", 0.001)
    weight_decay = config.get("weight_decay", 0.001)
    dropout = config.get("dropout", 0.0)
    layers = config["layers"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)
    train_X, train_y = to_tensors(X_scaled, y_train)

    loader = DataLoader(
        TensorDataset(train_X, train_y),
        batch_size=batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )

    model = ConfigurableANN(
        input_size=X_train.shape[1],
        hidden_layers=layers,
        dropout=dropout,
    )
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=lr,
        weight_decay=weight_decay,
    )
    loss_fn = nn.BCEWithLogitsLoss()

    steps_run = 0
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

    return model, scaler


def run_phase3():
    print("=" * 80)
    print("PHASE 3: ANN THRESHOLD OPTIMIZATION & PROBABILITY CALIBRATION")
    print("=" * 80)

    df = pd.read_csv(DATA_PATH)
    X = df.drop(columns=["DEATH_EVENT", "time"])
    y = df["DEATH_EVENT"].astype(int)

    prevalence = float(np.mean(y))
    print(f"Dataset Size: {len(df)} patients | Features: {X.shape[1]} | Overall Mortality Prevalence: {prevalence*100:.2f}% ({np.sum(y)}/{len(y)})")

    cv = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    splits = list(cv.split(X, y))

    MODELS_CONFIG = [
        {
            "id": "Logistic_Regression",
            "name": "Logistic Regression Baseline",
            "type": "linear",
            "layers": [1],
            "params": 12,
            "desc": "Linear (11->1)",
        },
        {
            "id": "Arch_C_32_16",
            "name": "Arch C (32->16->1)",
            "type": "ann",
            "layers": [32, 16],
            "dropout": 0.0,
            "weight_decay": 0.001,
            "batch_size": 64,
            "lr": 0.001,
            "params": 929,
            "desc": "11->32->16->1 (dp=0.0, wd=0.001, bs=64)",
        },
        {
            "id": "Arch_B_16",
            "name": "Arch B (16->1)",
            "type": "ann",
            "layers": [16],
            "dropout": 0.2,
            "weight_decay": 0.01,
            "batch_size": 32,
            "lr": 0.001,
            "params": 209,
            "desc": "11->16->1 (dp=0.2, wd=0.01, bs=32)",
        },
    ]

    threshold_results = []
    calibration_results = []
    fold_results = []
    outer_predictions_store = {m["id"]: {"y_true": [], "uncal_prob": [], "platt_prob": [], "iso_prob": [], "logits": []} for m in MODELS_CONFIG}

    for model_info in MODELS_CONFIG:
        m_id = model_info["id"]
        m_name = model_info["name"]
        m_type = model_info["type"]
        print(f"\n>>> Running Model: {m_name} ({model_info['desc']}) <<<")

        for fold, (train_idx, val_idx) in enumerate(splits, start=1):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            y_val_np = y_val.to_numpy()

            # Inner partition (80% train-inner, 20% validation-stop) strictly from outer train
            X_train_inner, X_stop, y_train_inner, y_stop = train_test_split(
                X_train, y_train, test_size=0.20, stratify=y_train, random_state=SEED + fold
            )
            y_stop_np = y_stop.to_numpy()

            if m_type == "linear":
                # Inner fit on X_train_inner to get inner validation predictions & logits
                lr_inner_pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=SEED))
                lr_inner_pipe.fit(X_train_inner, y_train_inner)
                inner_val_probs = lr_inner_pipe.predict_proba(X_stop)[:, 1]
                inner_val_logits = lr_inner_pipe.decision_function(X_stop)

                # Outer fit on full X_train
                lr_outer_pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=SEED))
                lr_outer_pipe.fit(X_train, y_train)
                outer_test_probs = lr_outer_pipe.predict_proba(X_val)[:, 1]
                outer_test_logits = lr_outer_pipe.decision_function(X_val)

            else:
                # ANN training
                ann_inner_res = train_ann_with_early_stopping(
                    X_train_inner, y_train_inner, X_stop, y_stop, model_info, seed=SEED + fold
                )
                inner_val_probs = ann_inner_res["inner_stop_probs"]
                inner_val_logits = ann_inner_res["inner_stop_logits"]
                target_steps = ann_inner_res["total_inner_steps"]

                # Refit on full X_train
                final_model, final_scaler = fit_final_outer_ann(
                    X_train, y_train, model_info, seed=SEED + fold, target_steps=target_steps
                )
                final_model.eval()
                X_val_scaled = final_scaler.transform(X_val)
                with torch.inference_mode():
                    t_val_X = torch.tensor(X_val_scaled, dtype=torch.float32)
                    outer_test_logits = final_model(t_val_X).numpy().ravel()
                    outer_test_probs = torch.sigmoid(final_model(t_val_X)).numpy().ravel()

            # ---------------------------------------------------------
            # 1. Inner Threshold Selection (Strictly on inner_val_probs)
            # ---------------------------------------------------------
            inner_thresh_selection = select_best_thresholds_from_validation(y_stop_np, inner_val_probs)
            th_youden = inner_thresh_selection["thresh_youden"]
            th_f1 = inner_thresh_selection["thresh_f1"]

            # ---------------------------------------------------------
            # 2. Calibration Models Fitted Strictly on Inner Data
            # ---------------------------------------------------------
            # A. Platt Scaling (Logistic Regression on inner logits)
            platt_model = LogisticRegression(C=1e5, solver="lbfgs", max_iter=1000)
            platt_model.fit(inner_val_logits.reshape(-1, 1), y_stop_np)
            platt_test_probs = platt_model.predict_proba(outer_test_logits.reshape(-1, 1))[:, 1]

            # B. Isotonic Regression (Non-parametric on inner probs)
            iso_model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            iso_model.fit(inner_val_probs, y_stop_np)
            iso_test_probs = iso_model.predict(outer_test_probs)

            # Store concatenated predictions for global diagnostic diagrams
            outer_predictions_store[m_id]["y_true"].extend(y_val_np.tolist())
            outer_predictions_store[m_id]["uncal_prob"].extend(outer_test_probs.tolist())
            outer_predictions_store[m_id]["platt_prob"].extend(platt_test_probs.tolist())
            outer_predictions_store[m_id]["iso_prob"].extend(iso_test_probs.tolist())
            outer_predictions_store[m_id]["logits"].extend(outer_test_logits.tolist())

            # ---------------------------------------------------------
            # 3. Outer Test Fold Threshold Sweep (0.10 to 0.90)
            # ---------------------------------------------------------
            for th in THRESHOLD_GRID:
                m_at_th = calculate_metrics_at_threshold(y_val_np, outer_test_probs, threshold=th)
                threshold_results.append({
                    "Model_ID": m_id,
                    "Model_Name": m_name,
                    "Fold": fold,
                    "Selected_Via": "Sweep_Grid",
                    "Is_Reference_050": (th == 0.50),
                    **m_at_th,
                })

            # Evaluate outer test fold at internally selected thresholds
            m_at_youden = calculate_metrics_at_threshold(y_val_np, outer_test_probs, threshold=th_youden)
            threshold_results.append({
                "Model_ID": m_id,
                "Model_Name": m_name,
                "Fold": fold,
                "Selected_Via": "Inner_Youden_J",
                "Is_Reference_050": False,
                **m_at_youden,
            })

            m_at_f1 = calculate_metrics_at_threshold(y_val_np, outer_test_probs, threshold=th_f1)
            threshold_results.append({
                "Model_ID": m_id,
                "Model_Name": m_name,
                "Fold": fold,
                "Selected_Via": "Inner_F1_Max",
                "Is_Reference_050": False,
                **m_at_f1,
            })

            # ---------------------------------------------------------
            # 4. Probability Calibration Metrics on Outer Test Fold
            # ---------------------------------------------------------
            cal_variants = [
                ("Uncalibrated", outer_test_probs),
                ("Platt_Scaled", platt_test_probs),
                ("Isotonic_Calibrated", iso_test_probs),
            ]

            for cal_name, p_eval in cal_variants:
                brier = brier_score_loss(y_val_np, p_eval)
                # Clip for numerical stability in log loss
                p_clipped = np.clip(p_eval, 1e-15, 1 - 1e-15)
                ll = log_loss(y_val_np, p_clipped)
                auc = roc_auc_score(y_val_np, p_eval)
                ece = compute_expected_calibration_error(y_val_np, p_eval, n_bins=10)
                slope, intercept = compute_calibration_slope_and_intercept(y_val_np, p_eval)
                mean_p = float(np.mean(p_eval))
                std_p = float(np.std(p_eval))

                # Standard metrics at threshold 0.50 for calibrated probabilities
                m_050 = calculate_metrics_at_threshold(y_val_np, p_eval, threshold=0.50)

                calibration_results.append({
                    "Model_ID": m_id,
                    "Model_Name": m_name,
                    "Calibration_Method": cal_name,
                    "Fold": fold,
                    "AUROC": float(auc),
                    "Brier_Score": float(brier),
                    "Log_Loss": float(ll),
                    "ECE": float(ece),
                    "Calibration_Slope": float(slope),
                    "Calibration_Intercept": float(intercept),
                    "Mean_Predicted_Prob": mean_p,
                    "Std_Predicted_Prob": std_p,
                    "Actual_Prevalence": float(np.mean(y_val_np)),
                    "Accuracy_at_050": m_050["Accuracy"],
                    "Sensitivity_at_050": m_050["Sensitivity"],
                    "Specificity_at_050": m_050["Specificity"],
                    "Precision_at_050": m_050["Precision"],
                    "F1_at_050": m_050["F1_Score"],
                })

            # ---------------------------------------------------------
            # 5. Core Fold Results Record for Model Comparison
            # ---------------------------------------------------------
            ref_050 = calculate_metrics_at_threshold(y_val_np, outer_test_probs, threshold=0.50)
            platt_050 = calculate_metrics_at_threshold(y_val_np, platt_test_probs, threshold=0.50)

            fold_results.append({
                "Model_ID": m_id,
                "Model_Name": m_name,
                "Fold": fold,
                "Inner_Selected_Youden_Thresh": th_youden,
                "Inner_Selected_F1_Thresh": th_f1,
                "AUROC": float(roc_auc_score(y_val_np, outer_test_probs)),
                # Metrics at Ref 0.50 (Uncalibrated)
                "Uncal_Brier": float(brier_score_loss(y_val_np, outer_test_probs)),
                "Uncal_LogLoss": float(log_loss(y_val_np, np.clip(outer_test_probs, 1e-15, 1 - 1e-15))),
                "Uncal_Acc_050": ref_050["Accuracy"],
                "Uncal_Sens_050": ref_050["Sensitivity"],
                "Uncal_Spec_050": ref_050["Specificity"],
                "Uncal_Prec_050": ref_050["Precision"],
                "Uncal_F1_050": ref_050["F1_Score"],
                "Uncal_TP_050": ref_050["True_Positives"],
                "Uncal_FP_050": ref_050["False_Positives"],
                "Uncal_TN_050": ref_050["True_Negatives"],
                "Uncal_FN_050": ref_050["False_Negatives"],
                # Metrics at Selected Youden Threshold (Uncalibrated)
                "Youden_Acc": m_at_youden["Accuracy"],
                "Youden_Sens": m_at_youden["Sensitivity"],
                "Youden_Spec": m_at_youden["Specificity"],
                "Youden_Prec": m_at_youden["Precision"],
                "Youden_F1": m_at_youden["F1_Score"],
                "Youden_TP": m_at_youden["True_Positives"],
                "Youden_FP": m_at_youden["False_Positives"],
                "Youden_TN": m_at_youden["True_Negatives"],
                "Youden_FN": m_at_youden["False_Negatives"],
                # Metrics at Selected F1 Threshold (Uncalibrated)
                "F1_Opt_Acc": m_at_f1["Accuracy"],
                "F1_Opt_Sens": m_at_f1["Sensitivity"],
                "F1_Opt_Spec": m_at_f1["Specificity"],
                "F1_Opt_Prec": m_at_f1["Precision"],
                "F1_Opt_F1": m_at_f1["F1_Score"],
                # Platt-Calibrated Metrics
                "Platt_Brier": float(brier_score_loss(y_val_np, platt_test_probs)),
                "Platt_LogLoss": float(log_loss(y_val_np, np.clip(platt_test_probs, 1e-15, 1 - 1e-15))),
                "Platt_Acc_050": platt_050["Accuracy"],
                "Platt_Sens_050": platt_050["Sensitivity"],
                "Platt_Spec_050": platt_050["Specificity"],
                "Platt_F1_050": platt_050["F1_Score"],
            })

            print(
                f"[{m_id}] Fold {fold} | AUROC={roc_auc_score(y_val_np, outer_test_probs):.4f} | "
                f"Th=0.50 (Sens={ref_050['Sensitivity']:.2f}, Spec={ref_050['Specificity']:.2f}) | "
                f"Youden Th={th_youden:.2f} (Sens={m_at_youden['Sensitivity']:.2f}, Spec={m_at_youden['Specificity']:.2f}) | "
                f"Brier (Uncal={brier_score_loss(y_val_np, outer_test_probs):.4f}, Platt={brier_score_loss(y_val_np, platt_test_probs):.4f})"
            )

    # -------------------------------------------------------------
    # DataFrames & CSV Exports
    # -------------------------------------------------------------
    df_thresh = pd.DataFrame(threshold_results)
    df_cal = pd.DataFrame(calibration_results)
    df_folds = pd.DataFrame(fold_results)

    # Export raw results
    df_thresh.to_csv(RESULTS_DIR / "ann_phase3_threshold_results.csv", index=False)
    df_cal.to_csv(RESULTS_DIR / "ann_phase3_calibration_results.csv", index=False)
    df_folds.to_csv(RESULTS_DIR / "ann_phase3_fold_results.csv", index=False)

    print(f"\n✓ Saved: {RESULTS_DIR / 'ann_phase3_threshold_results.csv'}")
    print(f"✓ Saved: {RESULTS_DIR / 'ann_phase3_calibration_results.csv'}")
    print(f"✓ Saved: {RESULTS_DIR / 'ann_phase3_fold_results.csv'}")

    # -------------------------------------------------------------
    # Model Comparison Summary Table
    # -------------------------------------------------------------
    # Build comprehensive comparison dataframe
    comp_rows = []
    for model_info in MODELS_CONFIG:
        m_id = model_info["id"]
        m_name = model_info["name"]
        m_folds = df_folds[df_folds["Model_ID"] == m_id]

        # 1. Uncalibrated at Reference Threshold 0.50
        comp_rows.append({
            "Model": m_name,
            "Parameters": model_info["params"],
            "Operating_Mode": "Threshold 0.50 (Uncalibrated)",
            "Decision_Threshold": "0.50 (Fixed)",
            "AUROC": f"{m_folds['AUROC'].mean()*100:.2f}% ± {m_folds['AUROC'].std()*100:.2f}%",
            "Brier_Score": f"{m_folds['Uncal_Brier'].mean():.4f} ± {m_folds['Uncal_Brier'].std():.4f}",
            "Log_Loss": f"{m_folds['Uncal_LogLoss'].mean():.4f} ± {m_folds['Uncal_LogLoss'].std():.4f}",
            "Accuracy": f"{m_folds['Uncal_Acc_050'].mean()*100:.2f}% ± {m_folds['Uncal_Acc_050'].std()*100:.2f}%",
            "Sensitivity": f"{m_folds['Uncal_Sens_050'].mean()*100:.2f}% ± {m_folds['Uncal_Sens_050'].std()*100:.2f}%",
            "Specificity": f"{m_folds['Uncal_Spec_050'].mean()*100:.2f}% ± {m_folds['Uncal_Spec_050'].std()*100:.2f}%",
            "Precision": f"{m_folds['Uncal_Prec_050'].mean()*100:.2f}% ± {m_folds['Uncal_Prec_050'].std()*100:.2f}%",
            "F1_Score": f"{m_folds['Uncal_F1_050'].mean():.4f} ± {m_folds['Uncal_F1_050'].std():.4f}",
            "Mean_FP": f"{m_folds['Uncal_FP_050'].mean():.1f}",
            "Mean_FN": f"{m_folds['Uncal_FN_050'].mean():.1f}",
        })

        # 2. Uncalibrated at Internally Selected Youden's J Threshold
        comp_rows.append({
            "Model": m_name,
            "Parameters": model_info["params"],
            "Operating_Mode": "Inner-Selected Youden Threshold",
            "Decision_Threshold": f"{m_folds['Inner_Selected_Youden_Thresh'].mean():.2f} (mean)",
            "AUROC": f"{m_folds['AUROC'].mean()*100:.2f}% ± {m_folds['AUROC'].std()*100:.2f}%",
            "Brier_Score": f"{m_folds['Uncal_Brier'].mean():.4f} ± {m_folds['Uncal_Brier'].std():.4f}",
            "Log_Loss": f"{m_folds['Uncal_LogLoss'].mean():.4f} ± {m_folds['Uncal_LogLoss'].std():.4f}",
            "Accuracy": f"{m_folds['Youden_Acc'].mean()*100:.2f}% ± {m_folds['Youden_Acc'].std()*100:.2f}%",
            "Sensitivity": f"{m_folds['Youden_Sens'].mean()*100:.2f}% ± {m_folds['Youden_Sens'].std()*100:.2f}%",
            "Specificity": f"{m_folds['Youden_Spec'].mean()*100:.2f}% ± {m_folds['Youden_Spec'].std()*100:.2f}%",
            "Precision": f"{m_folds['Youden_Prec'].mean()*100:.2f}% ± {m_folds['Youden_Prec'].std()*100:.2f}%",
            "F1_Score": f"{m_folds['Youden_F1'].mean():.4f} ± {m_folds['Youden_F1'].std():.4f}",
            "Mean_FP": f"{m_folds['Youden_FP'].mean():.1f}",
            "Mean_FN": f"{m_folds['Youden_FN'].mean():.1f}",
        })

        # 3. Uncalibrated at Internally Selected F1 Threshold
        comp_rows.append({
            "Model": m_name,
            "Parameters": model_info["params"],
            "Operating_Mode": "Inner-Selected F1 Threshold",
            "Decision_Threshold": f"{m_folds['Inner_Selected_F1_Thresh'].mean():.2f} (mean)",
            "AUROC": f"{m_folds['AUROC'].mean()*100:.2f}% ± {m_folds['AUROC'].std()*100:.2f}%",
            "Brier_Score": f"{m_folds['Uncal_Brier'].mean():.4f} ± {m_folds['Uncal_Brier'].std():.4f}",
            "Log_Loss": f"{m_folds['Uncal_LogLoss'].mean():.4f} ± {m_folds['Uncal_LogLoss'].std():.4f}",
            "Accuracy": f"{m_folds['F1_Opt_Acc'].mean()*100:.2f}% ± {m_folds['F1_Opt_Acc'].std()*100:.2f}%",
            "Sensitivity": f"{m_folds['F1_Opt_Sens'].mean()*100:.2f}% ± {m_folds['F1_Opt_Sens'].std()*100:.2f}%",
            "Specificity": f"{m_folds['F1_Opt_Spec'].mean()*100:.2f}% ± {m_folds['F1_Opt_Spec'].std()*100:.2f}%",
            "Precision": f"{m_folds['F1_Opt_Prec'].mean()*100:.2f}% ± {m_folds['F1_Opt_Prec'].std()*100:.2f}%",
            "F1_Score": f"{m_folds['F1_Opt_F1'].mean():.4f} ± {m_folds['F1_Opt_F1'].std():.4f}",
            "Mean_FP": "-",
            "Mean_FN": "-",
        })

        # 4. Platt-Calibrated at Threshold 0.50
        comp_rows.append({
            "Model": m_name,
            "Parameters": model_info["params"],
            "Operating_Mode": "Platt Scaled (Threshold 0.50)",
            "Decision_Threshold": "0.50 (Post-Platt)",
            "AUROC": f"{m_folds['AUROC'].mean()*100:.2f}% ± {m_folds['AUROC'].std()*100:.2f}%",
            "Brier_Score": f"{m_folds['Platt_Brier'].mean():.4f} ± {m_folds['Platt_Brier'].std():.4f}",
            "Log_Loss": f"{m_folds['Platt_LogLoss'].mean():.4f} ± {m_folds['Platt_LogLoss'].std():.4f}",
            "Accuracy": f"{m_folds['Platt_Acc_050'].mean()*100:.2f}% ± {m_folds['Platt_Acc_050'].std()*100:.2f}%",
            "Sensitivity": f"{m_folds['Platt_Sens_050'].mean()*100:.2f}% ± {m_folds['Platt_Sens_050'].std()*100:.2f}%",
            "Specificity": f"{m_folds['Platt_Spec_050'].mean()*100:.2f}% ± {m_folds['Platt_Spec_050'].std()*100:.2f}%",
            "Precision": "-",
            "F1_Score": f"{m_folds['Platt_F1_050'].mean():.4f} ± {m_folds['Platt_F1_050'].std():.4f}",
            "Mean_FP": "-",
            "Mean_FN": "-",
        })

    df_comp = pd.DataFrame(comp_rows)
    df_comp.to_csv(RESULTS_DIR / "ann_phase3_model_comparison.csv", index=False)
    print(f"✓ Saved: {RESULTS_DIR / 'ann_phase3_model_comparison.csv'}")

    # -------------------------------------------------------------
    # Compute Calibration Reliability Diagrams (Binned)
    # -------------------------------------------------------------
    cal_curves = {}
    for m_id in MODELS_CONFIG:
        y_all = np.array(outer_predictions_store[m_id["id"]]["y_true"])
        p_uncal = np.array(outer_predictions_store[m_id["id"]]["uncal_prob"])
        p_platt = np.array(outer_predictions_store[m_id["id"]]["platt_prob"])
        p_iso = np.array(outer_predictions_store[m_id["id"]]["iso_prob"])

        c_uncal, e_uncal, cnt_uncal = compute_calibration_curve(y_all, p_uncal, n_bins=5)
        c_platt, e_platt, cnt_platt = compute_calibration_curve(y_all, p_platt, n_bins=5)
        c_iso, e_iso, cnt_iso = compute_calibration_curve(y_all, p_iso, n_bins=5)

        cal_curves[m_id["id"]] = {
            "uncal": {"centers": c_uncal, "empirical": e_uncal, "counts": cnt_uncal},
            "platt": {"centers": c_platt, "empirical": e_platt, "counts": cnt_platt},
            "iso": {"centers": c_iso, "empirical": e_iso, "counts": cnt_iso},
        }

    return {
        "df_thresh": df_thresh,
        "df_cal": df_cal,
        "df_folds": df_folds,
        "df_comp": df_comp,
        "cal_curves": cal_curves,
        "outer_predictions": outer_predictions_store,
    }


if __name__ == "__main__":
    run_phase3()
