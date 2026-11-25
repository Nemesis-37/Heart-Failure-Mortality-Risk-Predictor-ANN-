"""
phase7_wide_deep_optimization.py
=================================
Phase 7: ANN Residual Architecture and Preprocessing Optimization
Heart Failure Mortality Risk Predictor

Models evaluated:
  1. Logistic Regression baseline (canonical)
  2. Existing ANN Arch B (11→16→1, dp=0.2, wd=0.01, bs=32) - standard preprocessing
  3. Wide & Deep ANN (linear + 11→8→1 nonlinear branch) - standard preprocessing
  4. Wide & Deep ANN (linear + 11→8→1 nonlinear branch) - log1p biomarker transforms

Preprocessing rules:
  - All scaler fits and log transforms use ONLY training fold data.
  - Validation and outer test folds receive fitted-transform application only.
  - No cross-contamination of test statistics into training.

Evaluation:
  - StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
  - Identical folds for all four models.
  - Outer test folds completely isolated during training and model selection.
  - Metrics: AUROC, Brier, LogLoss, Accuracy, Sensitivity, Specificity, Precision, F1,
             Calibration Slope & Intercept.
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
from sklearn.metrics import (
    roc_auc_score, brier_score_loss, log_loss,
    accuracy_score, confusion_matrix,
)
from scipy.optimize import minimize_scalar
from scipy.stats import pearsonr

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dataset" / "heart_failure_clinical_records_dataset.csv"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SEED = 42
FOLDS = 5
PATIENCE = 15
MAX_EPOCHS = 300

LOG_TRANSFORM_FEATURES = ["creatinine_phosphokinase", "serum_creatinine"]


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


# ---------------------------------------------------------------------------
# Architectures
# ---------------------------------------------------------------------------
class ArchB(nn.Module):
    """Original Arch B: 11 → 16 → ReLU → Dropout → 1"""
    def __init__(self, input_size=11, dropout=0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 16),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(16, 1),
        )

    def forward(self, x):
        return self.net(x)


class WideDeepANN(nn.Module):
    """
    Wide & Deep ANN:
      linear_branch: nn.Linear(input_size, 1)   — the 'wide' component
      nonlinear_branch: 11 → 8 → ReLU → Dropout → 1  — the 'deep' component
      logit(x) = linear_branch(x) + nonlinear_branch(x)

    The linear branch can represent an exact linear model.
    The nonlinear branch adds residual corrections if supported by data.
    """
    def __init__(self, input_size=11, hidden=8, dropout=0.2):
        super().__init__()
        self.linear_branch = nn.Linear(input_size, 1)
        self.nonlinear_branch = nn.Sequential(
            nn.Linear(input_size, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, 1),
        )

    def forward(self, x):
        return self.linear_branch(x) + self.nonlinear_branch(x)


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------
def apply_log1p_transform(X: pd.DataFrame, fit_cols: list, train: bool = True, log_means=None, log_stds=None):
    """
    Apply log1p to specified columns. Returns transformed DataFrame plus fit stats.
    If train=True, compute and return column-wise log1p statistics (means and stds).
    If train=False, apply pre-computed statistics.
    """
    X_out = X.copy()
    for col in fit_cols:
        X_out[col] = np.log1p(X_out[col])
    return X_out


def build_preprocessed_arrays(X_train_df, X_val_df, X_test_df, use_log=False):
    """
    Full preprocessing pipeline:
    1. (Optional) log1p transform fitted on training data, applied to val/test.
    2. StandardScaler fitted on training data, applied to val/test.
    
    All transforms strictly use training fold statistics only.
    """
    X_tr = X_train_df.copy()
    X_va = X_val_df.copy()
    X_te = X_test_df.copy()

    if use_log:
        for col in LOG_TRANSFORM_FEATURES:
            X_tr[col] = np.log1p(X_tr[col])
            X_va[col] = np.log1p(X_va[col])
            X_te[col] = np.log1p(X_te[col])

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_va_s = scaler.transform(X_va)
    X_te_s = scaler.transform(X_te)

    return X_tr_s, X_va_s, X_te_s, scaler


# ---------------------------------------------------------------------------
# Calibration utilities
# ---------------------------------------------------------------------------
def compute_calibration_slope_intercept(y_true, y_prob):
    """Standard clinical calibration analysis."""
    y = np.asarray(y_true, dtype=int)
    y_prob = np.clip(y_prob, 1e-7, 1 - 1e-7)
    logit_p = np.log(y_prob / (1 - y_prob)).reshape(-1, 1)

    if len(np.unique(y)) < 2:
        return 1.0, 0.0

    try:
        lr_slope = LogisticRegression(penalty=None, solver='lbfgs', max_iter=1000)
        lr_slope.fit(logit_p, y)
        slope = float(lr_slope.coef_[0][0])
    except Exception:
        slope = float("nan")

    try:
        def neg_log_lik(alpha):
            p = 1.0 / (1.0 + np.exp(-(alpha + logit_p.ravel())))
            p = np.clip(p, 1e-15, 1 - 1e-15)
            return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
        res = minimize_scalar(neg_log_lik, bracket=[-2.0, 2.0])
        intercept = float(res.x) if res.success else 0.0
    except Exception:
        intercept = float("nan")

    return slope, intercept


def compute_metrics_at_threshold(y_true, y_prob, threshold=0.50):
    preds = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, preds, labels=[0, 1]).ravel()
    n_pos = tp + fn
    n_neg = tn + fp
    sens = tp / n_pos if n_pos > 0 else 0.0
    spec = tn / n_neg if n_neg > 0 else 0.0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * (prec * sens) / (prec + sens) if (prec + sens) > 0 else 0.0
    acc = (tp + tn) / len(y_true)
    return dict(Accuracy=acc, Sensitivity=sens, Specificity=spec,
                Precision=prec, F1_Score=f1, TP=int(tp), FP=int(fp),
                TN=int(tn), FN=int(fn))


# ---------------------------------------------------------------------------
# ANN Training helpers (epoch-step early-stopping, canonical protocol)
# ---------------------------------------------------------------------------
def train_ann_inner(model_cls, model_kwargs, X_tr_s, y_tr, X_va_s, y_va,
                    batch_size, lr, weight_decay, seed, patience=PATIENCE, max_epochs=MAX_EPOCHS):
    """
    Train with early stopping on (X_va_s, y_va) inner stop set.
    Returns: best model state, best_epoch, steps_per_epoch.
    """
    set_seed(seed)
    model = model_cls(**model_kwargs)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = nn.BCEWithLogitsLoss()

    t_X_tr = torch.tensor(X_tr_s, dtype=torch.float32)
    t_y_tr = torch.tensor(y_tr.values if hasattr(y_tr, 'values') else y_tr, dtype=torch.float32).unsqueeze(1)
    t_X_va = torch.tensor(X_va_s, dtype=torch.float32)
    t_y_va = torch.tensor(y_va.values if hasattr(y_va, 'values') else y_va, dtype=torch.float32).unsqueeze(1)

    loader = DataLoader(
        TensorDataset(t_X_tr, t_y_tr),
        batch_size=batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )
    steps_per_epoch = len(loader)

    best_loss = float("inf")
    best_state = copy.deepcopy(model.state_dict())
    best_epoch = 1
    patience_cnt = 0

    for epoch in range(1, max_epochs + 1):
        model.train()
        for bx, by in loader:
            optimizer.zero_grad()
            loss_fn(model(bx), by).backward()
            optimizer.step()

        model.eval()
        with torch.inference_mode():
            val_loss = loss_fn(model(t_X_va), t_y_va).item()

        if val_loss < best_loss - 1e-5:
            best_loss = val_loss
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch
            patience_cnt = 0
        else:
            patience_cnt += 1
            if patience_cnt >= patience:
                break

    return best_state, best_epoch, steps_per_epoch


def refit_ann_outer(model_cls, model_kwargs, X_out_s, y_out,
                    batch_size, lr, weight_decay, seed, target_steps):
    """
    Refit on full outer training fold for exactly target_steps gradient steps.
    Uses same generator seed protocol as Phase 3 (canonical).
    """
    set_seed(seed)
    model = model_cls(**model_kwargs)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = nn.BCEWithLogitsLoss()

    t_X = torch.tensor(X_out_s, dtype=torch.float32)
    t_y = torch.tensor(y_out.values if hasattr(y_out, 'values') else y_out, dtype=torch.float32).unsqueeze(1)
    loader = DataLoader(
        TensorDataset(t_X, t_y),
        batch_size=batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )

    steps_done = 0
    model.train()
    while steps_done < target_steps:
        for bx, by in loader:
            if steps_done >= target_steps:
                break
            optimizer.zero_grad()
            loss_fn(model(bx), by).backward()
            optimizer.step()
            steps_done += 1

    return model


def predict_probs_ann(model, X_s):
    model.eval()
    with torch.inference_mode():
        t_X = torch.tensor(X_s, dtype=torch.float32)
        logits = model(t_X).numpy().ravel()
    return torch.sigmoid(torch.tensor(logits)).numpy()


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------
def run_phase7():
    print("=" * 80)
    print("PHASE 7: WIDE & DEEP ANN RESIDUAL ARCHITECTURE OPTIMIZATION")
    print("=" * 80)

    df = pd.read_csv(DATA_PATH)
    X = df.drop(columns=["DEATH_EVENT", "time"])
    y = df["DEATH_EVENT"].astype(int)
    feature_names = list(X.columns)

    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    print(f"Dataset: {len(df)} patients | {len(feature_names)} features | {n_pos} deaths ({n_pos/len(df)*100:.2f}%) | {n_neg} survivals")
    print(f"Features: {feature_names}")

    cv = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    splits = list(cv.split(X, y))

    # Models to evaluate
    model_configs = [
        {
            "id": "Logistic_Regression",
            "name": "Logistic Regression Baseline",
            "type": "lr",
            "use_log": False,
        },
        {
            "id": "Arch_B_Standard",
            "name": "ANN Arch B (11→16→1, standard preprocessing)",
            "type": "ann_b",
            "use_log": False,
            "ann_cls": ArchB,
            "ann_kwargs": {"input_size": 11, "dropout": 0.2},
            "batch_size": 32,
            "lr": 0.001,
            "weight_decay": 0.01,
        },
        {
            "id": "WideDeep_Standard",
            "name": "Wide & Deep ANN (11→8→1 deep + linear, standard preprocessing)",
            "type": "ann_wd",
            "use_log": False,
            "ann_cls": WideDeepANN,
            "ann_kwargs": {"input_size": 11, "hidden": 8, "dropout": 0.2},
            "batch_size": 32,
            "lr": 0.001,
            "weight_decay": 0.01,
        },
        {
            "id": "WideDeep_Log",
            "name": "Wide & Deep ANN (11→8→1 deep + linear, log1p CPK & creatinine)",
            "type": "ann_wd",
            "use_log": True,
            "ann_cls": WideDeepANN,
            "ann_kwargs": {"input_size": 11, "hidden": 8, "dropout": 0.2},
            "batch_size": 32,
            "lr": 0.001,
            "weight_decay": 0.01,
        },
    ]

    fold_metrics = []
    oof_all = {cfg["id"]: {"y_true": [], "y_prob": [], "patient_idx": []} for cfg in model_configs}
    preprocessing_rows = []

    for cfg in model_configs:
        m_id = cfg["id"]
        m_name = cfg["name"]
        use_log = cfg["use_log"]
        print(f"\n{'='*60}")
        print(f"Model: {m_name}")
        print(f"{'='*60}")

        for fold_idx, (train_idx, val_idx) in enumerate(splits, start=1):
            X_train_df = X.iloc[train_idx]
            X_val_df = X.iloc[val_idx]
            y_train = y.iloc[train_idx]
            y_val = y.iloc[val_idx]
            y_val_np = y_val.values

            # Inner split (strictly inside training fold; val-stop data never touches outer test)
            X_tr_in_df, X_va_in_df, y_tr_in, y_va_in = train_test_split(
                X_train_df, y_train,
                test_size=0.20, stratify=y_train, random_state=SEED + fold_idx
            )

            # Build preprocessed arrays (all fits on training data only)
            X_tr_in_s, X_va_in_s, _, _ = build_preprocessed_arrays(
                X_tr_in_df, X_va_in_df, X_va_in_df, use_log=use_log
            )
            X_tr_out_s, _, X_te_s, scaler_out = build_preprocessed_arrays(
                X_train_df, X_train_df, X_val_df, use_log=use_log
            )

            # Record preprocessing stats for Experiment 1 comparison
            if cfg["type"] in ("ann_wd",) and fold_idx == 1:
                for col in LOG_TRANSFORM_FEATURES:
                    if use_log:
                        vals_raw = X_train_df[col].values
                        vals_log = np.log1p(vals_raw)
                        preprocessing_rows.append({
                            "Feature": col,
                            "Preprocessing": "log1p + StandardScaler",
                            "Model_ID": m_id,
                            "Fold": fold_idx,
                            "Raw_Mean": float(np.mean(vals_raw)),
                            "Raw_Std": float(np.std(vals_raw)),
                            "Raw_Skewness": float(pd.Series(vals_raw).skew()),
                            "Transformed_Mean": float(np.mean(vals_log)),
                            "Transformed_Std": float(np.std(vals_log)),
                            "Transformed_Skewness": float(pd.Series(vals_log).skew()),
                        })
                    else:
                        vals_raw = X_train_df[col].values
                        preprocessing_rows.append({
                            "Feature": col,
                            "Preprocessing": "StandardScaler only",
                            "Model_ID": m_id,
                            "Fold": fold_idx,
                            "Raw_Mean": float(np.mean(vals_raw)),
                            "Raw_Std": float(np.std(vals_raw)),
                            "Raw_Skewness": float(pd.Series(vals_raw).skew()),
                            "Transformed_Mean": float(np.mean(vals_raw)),
                            "Transformed_Std": float(np.std(vals_raw)),
                            "Transformed_Skewness": float(pd.Series(vals_raw).skew()),
                        })

            # ----------------------------------------------------------------
            # Train model
            # ----------------------------------------------------------------
            if cfg["type"] == "lr":
                # Inner fit → find nothing (LR just trains on full outer fold)
                lr_outer = make_pipeline(
                    StandardScaler(),
                    LogisticRegression(max_iter=2000, random_state=SEED, C=1.0)
                )
                lr_outer.fit(X_train_df, y_train)
                y_prob = lr_outer.predict_proba(X_val_df)[:, 1]

            else:
                # ANN: inner early stopping → outer refit
                best_state, best_epoch, steps_per_epoch = train_ann_inner(
                    model_cls=cfg["ann_cls"],
                    model_kwargs=cfg["ann_kwargs"],
                    X_tr_s=X_tr_in_s,
                    y_tr=y_tr_in,
                    X_va_s=X_va_in_s,
                    y_va=y_va_in,
                    batch_size=cfg["batch_size"],
                    lr=cfg["lr"],
                    weight_decay=cfg["weight_decay"],
                    seed=SEED + fold_idx,
                )

                # Step-budget for outer refit (adjusted for larger outer training set)
                # Outer N_train / Inner N_train gives step multiplier
                n_inner = len(X_tr_in_df)
                n_outer = len(X_train_df)
                step_multiplier = n_outer / n_inner
                target_steps = int(round(best_epoch * steps_per_epoch * step_multiplier))

                final_model = refit_ann_outer(
                    model_cls=cfg["ann_cls"],
                    model_kwargs=cfg["ann_kwargs"],
                    X_out_s=X_tr_out_s,
                    y_out=y_train,
                    batch_size=cfg["batch_size"],
                    lr=cfg["lr"],
                    weight_decay=cfg["weight_decay"],
                    seed=SEED + fold_idx,
                    target_steps=target_steps,
                )

                y_prob = predict_probs_ann(final_model, X_te_s)

            # ----------------------------------------------------------------
            # Metrics
            # ----------------------------------------------------------------
            auroc = float(roc_auc_score(y_val_np, y_prob))
            brier = float(brier_score_loss(y_val_np, y_prob))
            ll = float(log_loss(y_val_np, y_prob))
            cal_slope, cal_intercept = compute_calibration_slope_intercept(y_val_np, y_prob)
            clf_metrics = compute_metrics_at_threshold(y_val_np, y_prob, threshold=0.50)

            fold_metrics.append({
                "Model_ID": m_id,
                "Model_Name": m_name,
                "Use_Log_Transform": use_log,
                "Fold": fold_idx,
                "N_Test": len(y_val_np),
                "N_Pos": int(y_val_np.sum()),
                "N_Neg": int((1 - y_val_np).sum()),
                "AUROC": auroc,
                "Brier_Score": brier,
                "Log_Loss": ll,
                "Calibration_Slope": cal_slope,
                "Calibration_Intercept": cal_intercept,
                **clf_metrics,
            })

            # Store OOF predictions
            oof_all[m_id]["y_true"].extend(y_val_np.tolist())
            oof_all[m_id]["y_prob"].extend(y_prob.tolist())
            oof_all[m_id]["patient_idx"].extend(val_idx.tolist())

            print(f"  Fold {fold_idx}: AUROC={auroc:.4f} | Brier={brier:.4f} | LogLoss={ll:.4f} | "
                  f"Sens={clf_metrics['Sensitivity']:.4f} | Spec={clf_metrics['Specificity']:.4f} | "
                  f"CalSlope={cal_slope:.3f}")

    # -----------------------------------------------------------------------
    # Save fold metrics CSV
    # -----------------------------------------------------------------------
    df_fold = pd.DataFrame(fold_metrics)
    df_fold.to_csv(RESULTS_DIR / "ann_phase7_fold_metrics.csv", index=False)
    print(f"\nSaved: ann_phase7_fold_metrics.csv ({len(df_fold)} rows)")

    # -----------------------------------------------------------------------
    # Aggregate summary
    # -----------------------------------------------------------------------
    agg_rows = []
    metric_cols = ["AUROC", "Brier_Score", "Log_Loss", "Accuracy", "Sensitivity",
                   "Specificity", "Precision", "F1_Score", "Calibration_Slope", "Calibration_Intercept"]

    for cfg in model_configs:
        m_id = cfg["id"]
        sub = df_fold[df_fold["Model_ID"] == m_id]
        row = {"Model_ID": m_id, "Model_Name": cfg["name"], "Use_Log_Transform": cfg["use_log"]}
        for col in metric_cols:
            if col in sub.columns:
                row[f"{col}_Mean"] = float(sub[col].mean())
                row[f"{col}_Std"] = float(sub[col].std())
        # Confusion matrix means
        for cm_col in ["TP", "FP", "TN", "FN"]:
            row[f"Mean_{cm_col}"] = float(sub[cm_col].mean())
        agg_rows.append(row)

    df_summary = pd.DataFrame(agg_rows)

    # Print summary table
    print("\n" + "=" * 100)
    print("PHASE 7 AGGREGATE SUMMARY (5-Fold Cross-Validation)")
    print("=" * 100)
    print(f"{'Model':<55} {'AUROC':>10} {'Brier':>8} {'LogLoss':>9} {'Sens':>8} {'Spec':>8} {'CalSlope':>10}")
    print("-" * 100)
    for _, row in df_summary.iterrows():
        print(f"{row['Model_Name']:<55} "
              f"{row['AUROC_Mean']*100:>8.2f}%  "
              f"{row['Brier_Score_Mean']:>8.4f}  "
              f"{row['Log_Loss_Mean']:>9.4f}  "
              f"{row['Sensitivity_Mean']*100:>6.2f}%  "
              f"{row['Specificity_Mean']*100:>6.2f}%  "
              f"{row['Calibration_Slope_Mean']:>10.3f}")

    df_summary.to_csv(RESULTS_DIR / "ann_phase7_wide_deep_metrics.csv", index=False)
    print(f"\nSaved: ann_phase7_wide_deep_metrics.csv")

    # -----------------------------------------------------------------------
    # OOF Prediction Comparison CSV
    # -----------------------------------------------------------------------
    oof_lr = oof_all["Logistic_Regression"]
    oof_ab = oof_all["Arch_B_Standard"]
    oof_wd_std = oof_all["WideDeep_Standard"]
    oof_wd_log = oof_all["WideDeep_Log"]

    # Sort all by patient index
    def sort_oof(d):
        idx = np.argsort(d["patient_idx"])
        return (
            np.array(d["patient_idx"])[idx],
            np.array(d["y_true"])[idx],
            np.array(d["y_prob"])[idx],
        )

    idx_lr, yt_lr, pp_lr = sort_oof(oof_lr)
    idx_ab, yt_ab, pp_ab = sort_oof(oof_ab)
    idx_ws, yt_ws, pp_ws = sort_oof(oof_wd_std)
    idx_wl, yt_wl, pp_wl = sort_oof(oof_wd_log)

    df_pred_cmp = pd.DataFrame({
        "Patient_Index": idx_lr,
        "True_Death_Event": yt_lr,
        "Prob_LR": pp_lr,
        "Prob_ArchB_Standard": pp_ab,
        "Prob_WideDeep_Standard": pp_ws,
        "Prob_WideDeep_Log": pp_wl,
        "Pred_LR_050": (pp_lr >= 0.50).astype(int),
        "Pred_ArchB_050": (pp_ab >= 0.50).astype(int),
        "Pred_WD_Std_050": (pp_ws >= 0.50).astype(int),
        "Pred_WD_Log_050": (pp_wl >= 0.50).astype(int),
        "Brier_LR": (pp_lr - yt_lr) ** 2,
        "Brier_ArchB": (pp_ab - yt_lr) ** 2,
        "Brier_WD_Std": (pp_ws - yt_lr) ** 2,
        "Brier_WD_Log": (pp_wl - yt_lr) ** 2,
    })
    df_pred_cmp.to_csv(RESULTS_DIR / "ann_phase7_prediction_comparison.csv", index=False)
    print(f"Saved: ann_phase7_prediction_comparison.csv ({len(df_pred_cmp)} rows)")

    # Correlation matrix
    print("\n--- OOF Probability Correlation Matrix ---")
    for a_name, a_prob in [("LR", pp_lr), ("ArchB", pp_ab), ("WD_Std", pp_ws), ("WD_Log", pp_wl)]:
        for b_name, b_prob in [("LR", pp_lr), ("ArchB", pp_ab), ("WD_Std", pp_ws), ("WD_Log", pp_wl)]:
            if a_name <= b_name:
                r, _ = pearsonr(a_prob, b_prob)
                print(f"  {a_name} vs {b_name}: Pearson r = {r:.4f}")

    # -----------------------------------------------------------------------
    # Preprocessing comparison CSV
    # -----------------------------------------------------------------------
    df_preproc = pd.DataFrame(preprocessing_rows) if preprocessing_rows else pd.DataFrame()
    if not df_preproc.empty:
        df_preproc.to_csv(RESULTS_DIR / "ann_phase7_preprocessing_comparison.csv", index=False)
        print(f"Saved: ann_phase7_preprocessing_comparison.csv")

    return df_summary, df_fold, df_pred_cmp


if __name__ == "__main__":
    run_phase7()
