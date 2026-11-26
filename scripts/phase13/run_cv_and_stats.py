"""
scripts/phase13/run_cv_and_stats.py
===================================
Phase 13 Isolated Research Script:
- Baseline Side-by-Side Comparison (Genuine Leak-Free OOF + Reference Production Checkpoints)
- 5-Fold Stratified CV (Identical splits, inner-val early stopping for ANN)
- Repeated Stratified 5x10 CV (50 folds)
- ANN Multi-Seed Sensitivity Analysis (Seeds 42, 101, 202, 303, 404)
- Paired Statistical Tests (DeLong AUROC, Paired Bootstrap 5000x, McNemar)
- Patient-Level OOF & Disagreement Datasets
- Nested & Fixed-Weight Ensemble Evaluation (P_ens = w * P_LR + (1 - w) * P_ANN)
- Calibration & Inner-Fold Calibrator Experiments (Platt & Isotonic)

STRICT RESEARCH-ONLY GUARANTEE:
Reads dataset & existing production artifacts read-only; writes ONLY to results/phase13/.
"""

import copy
import json
import math
import random
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from scipy import stats
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.ann_model import HeartFailureANN
from models.logistic_model import create_logistic_model

DATA_PATH = PROJECT_ROOT / "dataset" / "heart_failure_clinical_records_dataset.csv"
OUT_DIR = PROJECT_ROOT / "results" / "phase13"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
ANN_EPOCHS = 100
ANN_PATIENCE = 10
ANN_BATCH_SIZE = 32
ANN_LR = 0.001
ANN_WD = 0.0001


def set_all_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.clip(np.asarray(y_prob, dtype=float), 1e-7, 1.0 - 1e-7)
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "sensitivity": float(recall_score(y_true, y_pred, zero_division=0)),
        "specificity": float(spec),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "auroc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "log_loss": float(log_loss(y_true, y_prob, labels=[0, 1])),
        "tp": int(tp),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
    }


def calibration_intercept_slope(y_true: np.ndarray, y_prob: np.ndarray) -> tuple[float, float]:
    y_prob_clip = np.clip(y_prob, 1e-6, 1.0 - 1e-6)
    logits = np.log(y_prob_clip / (1.0 - y_prob_clip)).reshape(-1, 1)
    # Unpenalized logistic regression of y on logit(p) -> intercept & slope
    lr_cal = LogisticRegression(C=1e9, solver="lbfgs", max_iter=1000)
    lr_cal.fit(logits, y_true)
    slope = float(lr_cal.coef_[0][0])
    # Intercept with slope fixed at 1 (calibration-in-the-large / CITL) and free intercept
    intercept_free = float(lr_cal.intercept_[0])
    # Calibration-in-the-large (offset = logits)
    from scipy.optimize import minimize
    def neg_ll(alpha):
        p = 1.0 / (1.0 + np.exp(-(alpha[0] + logits.ravel())))
        p = np.clip(p, 1e-12, 1.0 - 1e-12)
        return -np.sum(y_true * np.log(p) + (1 - y_true) * np.log(1 - p))
    res = minimize(neg_ll, x0=[0.0])
    citl = float(res.x[0])
    return citl, slope, intercept_free


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> tuple[float, float]:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    mce = 0.0
    n = len(y_true)
    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1] if i < n_bins - 1 else y_prob <= bins[i + 1])
        cnt = int(np.sum(mask))
        if cnt > 0:
            err = abs(float(np.mean(y_true[mask])) - float(np.mean(y_prob[mask])))
            ece += (cnt / n) * err
            mce = max(mce, err)
    return float(ece), float(mce)


# ---------------------------------------------------------------------------
# Exact DeLong Test for Paired AUROCs (Sun & Xu 2014 fast algorithm)
# ---------------------------------------------------------------------------
def _compute_midrank(x):
    J = np.argsort(x)
    Z = x[J]
    N = len(x)
    T = np.zeros(N, dtype=float)
    i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]:
            j += 1
        T[i:j] = 0.5 * (i + j - 1) + 1
        i = j
    T2 = np.empty(N, dtype=float)
    T2[J] = T
    return T2


def _fast_delong(predictions_sorted_transposed, label_1_count):
    m = label_1_count
    n = predictions_sorted_transposed.shape[1] - m
    positive_examples = predictions_sorted_transposed[:, :m]
    negative_examples = predictions_sorted_transposed[:, m:]
    k = predictions_sorted_transposed.shape[0]
    tx = np.empty([k, m], dtype=float)
    ty = np.empty([k, n], dtype=float)
    tz = np.empty([k, m + n], dtype=float)
    for r in range(k):
        tx[r, :] = _compute_midrank(positive_examples[r, :])
        ty[r, :] = _compute_midrank(negative_examples[r, :])
        tz[r, :] = _compute_midrank(predictions_sorted_transposed[r, :])
    aucs = tz[:, :m].sum(axis=1) / (m * n) - (m + 1.0) / (2.0 * n)
    v01 = (tz[:, :m] - tx[:, :]) / n
    v10 = 1.0 - (tz[:, m:] - ty[:, :]) / m
    sx = np.cov(v01)
    sy = np.cov(v10)
    delongcov = sx / m + sy / n
    return aucs, delongcov


def delong_roc_test(y_true: np.ndarray, prob_a: np.ndarray, prob_b: np.ndarray) -> dict:
    order = np.argsort(-y_true)  # positives first
    y_sorted = y_true[order]
    m = int(np.sum(y_sorted == 1))
    preds = np.vstack([prob_a, prob_b])[:, order]
    aucs, cov = _fast_delong(preds, m)
    diff = aucs[0] - aucs[1]
    var = cov[0, 0] + cov[1, 1] - 2 * cov[0, 1]
    se = math.sqrt(max(var, 1e-12))
    z = diff / se
    p_val = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
    return {
        "auc_lr": float(aucs[0]),
        "auc_ann": float(aucs[1]),
        "diff_lr_minus_ann": float(diff),
        "se_diff": float(se),
        "z_stat": float(z),
        "p_value": float(p_val),
    }


def mcnemar_test(y_true: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray) -> dict:
    corr_a = (pred_a == y_true)
    corr_b = (pred_b == y_true)
    n11 = int(np.sum(corr_a & corr_b))
    n10 = int(np.sum(corr_a & ~corr_b))   # A right, B wrong
    n01 = int(np.sum(~corr_a & corr_b))   # A wrong, B right
    n00 = int(np.sum(~corr_a & ~corr_b))
    # Exact binomial test on discordant pairs (recommended for small counts)
    disc = n10 + n01
    if disc == 0:
        p_exact = 1.0
    else:
        p_exact = float(stats.binomtest(min(n10, n01), n=disc, p=0.5).pvalue)
    chi2_cc = ((abs(n10 - n01) - 1) ** 2) / disc if disc > 0 else 0.0
    return {
        "both_correct": n11,
        "lr_only_correct": n10,
        "ann_only_correct": n01,
        "both_wrong": n00,
        "discordant_total": disc,
        "exact_p_value": p_exact,
        "chi2_continuity_corrected": float(chi2_cc),
    }


def train_ann_single_fold(
    X_outer_train: pd.DataFrame,
    y_outer_train: pd.Series,
    X_test: pd.DataFrame,
    seed: int = SEED,
    return_inner_val_preds: bool = False,
):
    """Strict leak-free ANN training using an 80/20 stratified inner validation split for early stopping."""
    set_all_seeds(seed)
    inner_tr_idx, inner_va_idx = train_test_split(
        np.arange(len(X_outer_train)),
        test_size=0.20,
        random_state=seed,
        stratify=y_outer_train,
    )
    X_tr = X_outer_train.iloc[inner_tr_idx]
    y_tr = y_outer_train.iloc[inner_tr_idx]
    X_va = X_outer_train.iloc[inner_va_idx]
    y_va = y_outer_train.iloc[inner_va_idx]

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_va_s = scaler.transform(X_va)
    X_te_s = scaler.transform(X_test)

    X_tr_t = torch.tensor(X_tr_s, dtype=torch.float32)
    y_tr_t = torch.tensor(y_tr.to_numpy(), dtype=torch.float32).reshape(-1, 1)
    X_va_t = torch.tensor(X_va_s, dtype=torch.float32)
    y_va_t = torch.tensor(y_va.to_numpy(), dtype=torch.float32).reshape(-1, 1)
    X_te_t = torch.tensor(X_te_s, dtype=torch.float32)

    gen = torch.Generator().manual_seed(seed)
    loader = DataLoader(TensorDataset(X_tr_t, y_tr_t), batch_size=ANN_BATCH_SIZE, shuffle=True, generator=gen)

    model = HeartFailureANN()
    loss_fn = nn.BCEWithLogitsLoss()
    opt = torch.optim.Adam(model.parameters(), lr=ANN_LR, weight_decay=ANN_WD)

    best_loss = float("inf")
    best_state = copy.deepcopy(model.state_dict())
    best_epoch = 0
    patience_ctr = 0

    for epoch in range(ANN_EPOCHS):
        model.train()
        for bx, by in loader:
            opt.zero_grad()
            out = model(bx)
            loss = loss_fn(out, by)
            loss.backward()
            opt.step()

        model.eval()
        with torch.inference_mode():
            v_logits = model(X_va_t)
            v_loss = float(loss_fn(v_logits, y_va_t).item())

        if v_loss < best_loss:
            best_loss = v_loss
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch + 1
            patience_ctr = 0
        else:
            patience_ctr += 1

        if patience_ctr >= ANN_PATIENCE:
            break

    model.load_state_dict(best_state)
    model.eval()
    with torch.inference_mode():
        test_probs = torch.sigmoid(model(X_te_t)).cpu().numpy().ravel()
        va_probs = torch.sigmoid(model(X_va_t)).cpu().numpy().ravel()

    info = {
        "best_epoch": best_epoch,
        "best_inner_val_loss": best_loss,
        "inner_val_idx": inner_va_idx,
        "inner_val_y": y_va.to_numpy(),
        "inner_val_probs": va_probs,
    }
    if return_inner_val_preds:
        return test_probs, model, scaler, info
    return test_probs, best_epoch, best_loss


def main():
    print("=" * 75)
    print("PHASE 13 — COMPREHENSIVE LR vs ANN EVALUATION & STATISTICAL SUITE")
    print("=" * 75)

    df = pd.read_csv(DATA_PATH)
    X = df.drop(columns=["DEATH_EVENT", "time"])
    y = df["DEATH_EVENT"].astype(int)
    feature_names = list(X.columns)

    # Load frozen production models READ-ONLY for reference comparison
    prod_lr = joblib.load(PROJECT_ROOT / "models" / "logistic_regression_pipeline.joblib")
    prod_ann_scaler = joblib.load(PROJECT_ROOT / "models" / "ann_scaler.joblib")
    prod_ann = HeartFailureANN()
    prod_ann.load_state_dict(torch.load(PROJECT_ROOT / "models" / "ann_model.pth", map_location="cpu", weights_only=True))
    prod_ann.eval()

    prod_lr_probs = prod_lr.predict_proba(X)[:, 1]
    with torch.inference_mode():
        prod_ann_probs = torch.sigmoid(
            prod_ann(torch.tensor(prod_ann_scaler.transform(X), dtype=torch.float32))
        ).cpu().numpy().ravel()

    # =========================================================================
    # 1. STRICT 5-FOLD STRATIFIED CROSS-VALIDATION (SEED=42)
    # =========================================================================
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

    oof_lr = np.zeros(len(X), dtype=float)
    oof_ann = np.zeros(len(X), dtype=float)
    oof_fold = np.zeros(len(X), dtype=int)

    # For inner-calibrated probabilities (zero outer test leakage)
    oof_lr_platt = np.zeros(len(X), dtype=float)
    oof_lr_iso = np.zeros(len(X), dtype=float)
    oof_ann_platt = np.zeros(len(X), dtype=float)
    oof_ann_iso = np.zeros(len(X), dtype=float)

    # Also track LR trained strictly on the exact same 80% inner train split as ANN
    oof_lr_inner80 = np.zeros(len(X), dtype=float)

    # Track nested-selected ensemble weight
    oof_nested_ens_probs = np.zeros(len(X), dtype=float)
    nested_weights = []

    cv_rows = []
    fold_splits = list(skf.split(X, y))

    # Identify which fold matches production ANN Fold 4
    prod_ann_fold_idx = 4  # Confirmed in audit (scaler mean matches Fold 4 train split)

    for fold, (outer_tr_idx, test_idx) in enumerate(fold_splits, start=1):
        X_outer_tr, y_outer_tr = X.iloc[outer_tr_idx], y.iloc[outer_tr_idx]
        X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]

        # 1a. Standard LR trained on full outer train (239 rows)
        lr_pipe = create_logistic_model()
        lr_pipe.fit(X_outer_tr, y_outer_tr)
        lr_probs = lr_pipe.predict_proba(X_te)[:, 1]

        # 1b. LR trained strictly on 80% inner train (matching ANN sample size ~191 rows) + inner val probs
        inner_tr_idx, inner_va_idx = train_test_split(
            np.arange(len(X_outer_tr)),
            test_size=0.20,
            random_state=SEED + fold,
            stratify=y_outer_tr,
        )
        lr_inner_pipe = create_logistic_model()
        lr_inner_pipe.fit(X_outer_tr.iloc[inner_tr_idx], y_outer_tr.iloc[inner_tr_idx])
        lr_inner80_probs = lr_inner_pipe.predict_proba(X_te)[:, 1]
        lr_inner_va_probs = lr_inner_pipe.predict_proba(X_outer_tr.iloc[inner_va_idx])[:, 1]

        # 1c. ANN trained strictly on 80% inner train with early stopping on 20% inner val
        ann_probs, ann_model_f, ann_scaler_f, ann_info = train_ann_single_fold(
            X_outer_tr, y_outer_tr, X_te, seed=SEED + fold, return_inner_val_preds=True
        )

        oof_lr[test_idx] = lr_probs
        oof_lr_inner80[test_idx] = lr_inner80_probs
        oof_ann[test_idx] = ann_probs
        oof_fold[test_idx] = fold

        # Inner calibration (fit ONLY on inner validation split, evaluate on untouched outer test)
        y_va_inner = ann_info["inner_val_y"]
        ann_va_probs = ann_info["inner_val_probs"]

        # Platt scaling (logistic recalibration on logits)
        def _fit_platt(va_p, va_y, te_p):
            va_l = np.log(np.clip(va_p, 1e-6, 1 - 1e-6) / (1 - np.clip(va_p, 1e-6, 1 - 1e-6))).reshape(-1, 1)
            te_l = np.log(np.clip(te_p, 1e-6, 1 - 1e-6) / (1 - np.clip(te_p, 1e-6, 1 - 1e-6))).reshape(-1, 1)
            platt = LogisticRegression(C=1e6, max_iter=1000)
            platt.fit(va_l, va_y)
            return platt.predict_proba(te_l)[:, 1]

        def _fit_iso(va_p, va_y, te_p):
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(va_p, va_y)
            return iso.predict(te_p)

        oof_lr_platt[test_idx] = _fit_platt(lr_inner_va_probs, y_va_inner, lr_inner80_probs)
        oof_lr_iso[test_idx] = _fit_iso(lr_inner_va_probs, y_va_inner, lr_inner80_probs)
        oof_ann_platt[test_idx] = _fit_platt(ann_va_probs, y_va_inner, ann_probs)
        oof_ann_iso[test_idx] = _fit_iso(ann_va_probs, y_va_inner, ann_probs)

        # Nested ensemble weight selection (optimize log loss on inner validation split)
        best_w = 0.5
        best_va_ll = float("inf")
        for w in np.linspace(0.0, 1.0, 21):
            ens_va = np.clip(w * lr_inner_va_probs + (1.0 - w) * ann_va_probs, 1e-7, 1 - 1e-7)
            ll = log_loss(y_va_inner, ens_va, labels=[0, 1])
            if ll < best_va_ll:
                best_va_ll = ll
                best_w = float(w)
        nested_weights.append(best_w)
        oof_nested_ens_probs[test_idx] = best_w * lr_probs + (1.0 - best_w) * ann_probs

        # Record 5-fold metrics
        for model_label, probs, extra in [
            ("Logistic_Regression", lr_probs, {"best_epoch": np.nan, "inner_val_loss": np.nan}),
            ("Logistic_Regression_Inner80", lr_inner80_probs, {"best_epoch": np.nan, "inner_val_loss": np.nan}),
            ("ANN_11_64_32_1", ann_probs, {"best_epoch": ann_info["best_epoch"], "inner_val_loss": ann_info["best_inner_val_loss"]}),
        ]:
            m_050 = compute_metrics(y_te.to_numpy(), probs, threshold=0.50)
            m_033 = compute_metrics(y_te.to_numpy(), probs, threshold=0.33)
            cv_rows.append({
                "experiment": "5Fold_Nested_Seed42",
                "repeat": 1,
                "fold": fold,
                "model": model_label,
                "n_val": len(test_idx),
                "n_pos": int(y_te.sum()),
                "threshold": 0.50,
                **m_050,
                "sens_at_033": m_033["sensitivity"],
                "spec_at_033": m_033["specificity"],
                "bal_acc_at_033": m_033["balanced_accuracy"],
                "f1_at_033": m_033["f1_score"],
                **extra,
            })

    # =========================================================================
    # 2. ANN MULTI-SEED SENSITIVITY (5 SEEDS x 5 FOLDS = 25 SPLITS)
    # =========================================================================
    ann_seeds = [42, 101, 202, 303, 404]
    seed_oof_probs = {}
    for s in ann_seeds:
        s_oof = np.zeros(len(X), dtype=float)
        for fold, (outer_tr_idx, test_idx) in enumerate(fold_splits, start=1):
            X_outer_tr, y_outer_tr = X.iloc[outer_tr_idx], y.iloc[outer_tr_idx]
            X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]
            ann_p, best_ep, best_vl = train_ann_single_fold(X_outer_tr, y_outer_tr, X_te, seed=s + fold)
            s_oof[test_idx] = ann_p
            if s != SEED:
                m = compute_metrics(y_te.to_numpy(), ann_p, threshold=0.50)
                m33 = compute_metrics(y_te.to_numpy(), ann_p, threshold=0.33)
                cv_rows.append({
                    "experiment": f"ANN_SeedSensitivity_Seed{s}",
                    "repeat": 1,
                    "fold": fold,
                    "model": "ANN_11_64_32_1",
                    "n_val": len(test_idx),
                    "n_pos": int(y_te.sum()),
                    "threshold": 0.50,
                    **m,
                    "sens_at_033": m33["sensitivity"],
                    "spec_at_033": m33["specificity"],
                    "bal_acc_at_033": m33["balanced_accuracy"],
                    "f1_at_033": m33["f1_score"],
                    "best_epoch": best_ep,
                    "inner_val_loss": best_vl,
                })
        seed_oof_probs[s] = s_oof

    # =========================================================================
    # 3. REPEATED STRATIFIED 5x10 CROSS-VALIDATION (50 TOTAL FOLDS)
    # =========================================================================
    print("Running 5x10 Repeated Stratified Cross-Validation (50 folds)...")
    rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEED)
    rep_lr_metrics = []
    rep_ann_metrics = []
    for idx_split, (tr_idx, te_idx) in enumerate(rskf.split(X, y)):
        rep = (idx_split // 5) + 1
        fold = (idx_split % 5) + 1
        X_outer_tr, y_outer_tr = X.iloc[tr_idx], y.iloc[tr_idx]
        X_te, y_te = X.iloc[te_idx], y.iloc[te_idx]

        lr_p_model = create_logistic_model()
        lr_p_model.fit(X_outer_tr, y_outer_tr)
        lr_p = lr_p_model.predict_proba(X_te)[:, 1]
        ann_p, best_ep, best_vl = train_ann_single_fold(X_outer_tr, y_outer_tr, X_te, seed=SEED + idx_split + 1)

        m_lr = compute_metrics(y_te.to_numpy(), lr_p, threshold=0.50)
        m_lr33 = compute_metrics(y_te.to_numpy(), lr_p, threshold=0.33)
        m_ann = compute_metrics(y_te.to_numpy(), ann_p, threshold=0.50)
        m_ann33 = compute_metrics(y_te.to_numpy(), ann_p, threshold=0.33)

        rep_lr_metrics.append(m_lr)
        rep_ann_metrics.append(m_ann)

        cv_rows.append({
            "experiment": "Repeated_5x10_CV",
            "repeat": rep,
            "fold": fold,
            "model": "Logistic_Regression",
            "n_val": len(te_idx),
            "n_pos": int(y_te.sum()),
            "threshold": 0.50,
            **m_lr,
            "sens_at_033": m_lr33["sensitivity"],
            "spec_at_033": m_lr33["specificity"],
            "bal_acc_at_033": m_lr33["balanced_accuracy"],
            "f1_at_033": m_lr33["f1_score"],
            "best_epoch": np.nan,
            "inner_val_loss": np.nan,
        })
        cv_rows.append({
            "experiment": "Repeated_5x10_CV",
            "repeat": rep,
            "fold": fold,
            "model": "ANN_11_64_32_1",
            "n_val": len(te_idx),
            "n_pos": int(y_te.sum()),
            "threshold": 0.50,
            **m_ann,
            "sens_at_033": m_ann33["sensitivity"],
            "spec_at_033": m_ann33["specificity"],
            "bal_acc_at_033": m_ann33["balanced_accuracy"],
            "f1_at_033": m_ann33["f1_score"],
            "best_epoch": best_ep,
            "inner_val_loss": best_vl,
        })

    cv_df = pd.DataFrame(cv_rows)
    cv_df.to_csv(OUT_DIR / "phase13_cross_validation_results.csv", index=False)

    # =========================================================================
    # 4. BASELINE COMPARISON TABLE (OOF POOLED, FOLD MEAN±SD, REPEATED MEAN±SD, PRODUCTION)
    # =========================================================================
    y_np = y.to_numpy()
    baseline_rows = []

    def add_baseline_row(label, eval_regime, probs, thresh=0.50):
        m = compute_metrics(y_np, probs, threshold=thresh)
        ece, mce = expected_calibration_error(y_np, probs, n_bins=10)
        citl, slope, intercept = calibration_intercept_slope(y_np, probs)
        baseline_rows.append({
            "model": label,
            "evaluation_regime": eval_regime,
            "threshold": thresh,
            "n_patients": len(y_np),
            **m,
            "ece_10bin": ece,
            "mce_10bin": mce,
            "calibration_citl": citl,
            "calibration_slope": slope,
            "calibration_intercept": intercept,
        })

    # Genuine OOF Unseen Evaluations (Threshold 0.50 & Prevalence-Aligned 0.33)
    add_baseline_row("Logistic Regression", "Genuine_5Fold_OOF_Unseen", oof_lr, 0.50)
    add_baseline_row("Logistic Regression (Inner80)", "Genuine_5Fold_OOF_Unseen_MatchedN", oof_lr_inner80, 0.50)
    add_baseline_row("ANN (11->64->32->1)", "Genuine_5Fold_OOF_Unseen", oof_ann, 0.50)
    add_baseline_row("Logistic Regression", "Genuine_5Fold_OOF_Unseen_Thresh033", oof_lr, 0.33)
    add_baseline_row("ANN (11->64->32->1)", "Genuine_5Fold_OOF_Unseen_Thresh033", oof_ann, 0.33)

    # Production Artifacts (In-Sample / Fold-4-Contaminated — clearly tagged as NON-UNSEEN!)
    add_baseline_row("Production LR (models/logistic_regression_pipeline.joblib)", "NonUnseen_Full299_InSample", prod_lr_probs, 0.50)
    add_baseline_row("Production ANN (models/ann_model.pth, Fold4_Ckpt)", "NonUnseen_Mixed_Fold4Train239_EarlyStop60", prod_ann_probs, 0.50)
    # Also evaluate Production ANN ONLY on Fold 4 validation 60 patients (still early-stopping selected)
    fold4_val_idx = fold_splits[3][1]
    m_f4_ann = compute_metrics(y_np[fold4_val_idx], prod_ann_probs[fold4_val_idx], 0.50)
    m_f4_lr = compute_metrics(y_np[fold4_val_idx], oof_lr[fold4_val_idx], 0.50)

    baseline_df = pd.DataFrame(baseline_rows)
    baseline_df.to_csv(OUT_DIR / "phase13_baseline_comparison.csv", index=False)

    # =========================================================================
    # 5. OOF PATIENT PREDICTIONS & PATIENT-LEVEL COMPARISON CSVs
    # =========================================================================
    lr_pred_050 = (oof_lr >= 0.50).astype(int)
    ann_pred_050 = (oof_ann >= 0.50).astype(int)
    lr_pred_033 = (oof_lr >= 0.33).astype(int)
    ann_pred_033 = (oof_ann >= 0.33).astype(int)

    def assign_group(y_i, p_lr_cls, p_ann_cls, p_lr, p_ann):
        lr_ok = (p_lr_cls == y_i)
        ann_ok = (p_ann_cls == y_i)
        if lr_ok and ann_ok:
            return "Both_Correct"
        if (not lr_ok) and (not ann_ok):
            if p_lr_cls == 0 and y_i == 1:
                return "Both_False_Negative"
            return "Both_False_Positive"
        if lr_ok and (not ann_ok):
            return "LR_Correct_ANN_Wrong"
        return "ANN_Correct_LR_Wrong"

    oof_df = df.copy()
    oof_df.insert(0, "patient_id", np.arange(1, len(df) + 1))
    oof_df["cv_fold"] = oof_fold
    oof_df["actual_death_event"] = y_np
    oof_df["oof_lr_prob"] = np.round(oof_lr, 6)
    oof_df["oof_ann_prob"] = np.round(oof_ann, 6)
    oof_df["oof_prob_diff_lr_minus_ann"] = np.round(oof_lr - oof_ann, 6)
    oof_df["oof_abs_prob_diff"] = np.round(np.abs(oof_lr - oof_ann), 6)
    oof_df["oof_lr_class_050"] = lr_pred_050
    oof_df["oof_ann_class_050"] = ann_pred_050
    oof_df["oof_agree_050"] = (lr_pred_050 == ann_pred_050)
    oof_df["oof_lr_correct_050"] = (lr_pred_050 == y_np)
    oof_df["oof_ann_correct_050"] = (ann_pred_050 == y_np)
    oof_df["oof_lr_class_033"] = lr_pred_033
    oof_df["oof_ann_class_033"] = ann_pred_033
    oof_df["oof_lr_platt_prob"] = np.round(oof_lr_platt, 6)
    oof_df["oof_ann_platt_prob"] = np.round(oof_ann_platt, 6)
    oof_df["oof_lr_iso_prob"] = np.round(oof_lr_iso, 6)
    oof_df["oof_ann_iso_prob"] = np.round(oof_ann_iso, 6)
    oof_df["prod_lr_insample_prob"] = np.round(prod_lr_probs, 6)
    oof_df["prod_ann_fold4ckpt_prob"] = np.round(prod_ann_probs, 6)

    oof_df.to_csv(OUT_DIR / "phase13_oof_patient_predictions.csv", index=False)

    comp_df = oof_df[[
        "patient_id", "cv_fold", "age", "ejection_fraction", "serum_creatinine", "serum_sodium", "platelets",
        "actual_death_event", "oof_lr_prob", "oof_ann_prob", "oof_lr_class_050", "oof_ann_class_050",
        "oof_prob_diff_lr_minus_ann", "oof_abs_prob_diff", "oof_agree_050",
        "oof_lr_correct_050", "oof_ann_correct_050",
        "prod_lr_insample_prob", "prod_ann_fold4ckpt_prob"
    ]].copy()
    comp_df["comparison_group_050"] = [
        assign_group(y_np[i], lr_pred_050[i], ann_pred_050[i], oof_lr[i], oof_ann[i])
        for i in range(len(y_np))
    ]
    comp_df["substantial_prob_diff_ge_015_same_class"] = (
        (comp_df["oof_agree_050"]) & (comp_df["oof_abs_prob_diff"] >= 0.15)
    )
    comp_df.to_csv(OUT_DIR / "phase13_patient_level_comparison.csv", index=False)

    # =========================================================================
    # 6. ENSEMBLE EXPERIMENTS (OOF PROBABILITIES & NESTED WEIGHTS)
    # =========================================================================
    ens_rows = []
    for w in [round(x, 2) for x in np.linspace(0.0, 1.0, 11)]:
        p_ens = w * oof_lr + (1.0 - w) * oof_ann
        m50 = compute_metrics(y_np, p_ens, threshold=0.50)
        m33 = compute_metrics(y_np, p_ens, threshold=0.33)
        ece, mce = expected_calibration_error(y_np, p_ens)
        citl, slope, _ = calibration_intercept_slope(y_np, p_ens)
        # Also compute 5-fold mean/sd for this weight
        fold_aurocs = []
        fold_briers = []
        for _, test_idx in fold_splits:
            fold_aurocs.append(roc_auc_score(y_np[test_idx], p_ens[test_idx]))
            fold_briers.append(brier_score_loss(y_np[test_idx], p_ens[test_idx]))
        label = "ANN_Only" if w == 0.0 else ("LR_Only" if w == 1.0 else ("Equal_50_50" if w == 0.5 else f"Weighted_{int(w*100)}LR_{int((1-w)*100)}ANN"))
        ens_rows.append({
            "strategy": label,
            "weight_lr": w,
            "weight_ann": round(1.0 - w, 2),
            "oof_auroc": m50["auroc"],
            "oof_pr_auc": m50["pr_auc"],
            "oof_brier_score": m50["brier_score"],
            "oof_log_loss": m50["log_loss"],
            "oof_ece_10bin": ece,
            "oof_cal_slope": slope,
            "oof_sens_050": m50["sensitivity"],
            "oof_spec_050": m50["specificity"],
            "oof_f1_050": m50["f1_score"],
            "oof_sens_033": m33["sensitivity"],
            "oof_spec_033": m33["specificity"],
            "oof_f1_033": m33["f1_score"],
            "fold5_auroc_mean": float(np.mean(fold_aurocs)),
            "fold5_auroc_sd": float(np.std(fold_aurocs, ddof=1)),
            "fold5_brier_mean": float(np.mean(fold_briers)),
            "fold5_brier_sd": float(np.std(fold_briers, ddof=1)),
        })

    # Nested-selected ensemble row
    m50_n = compute_metrics(y_np, oof_nested_ens_probs, threshold=0.50)
    m33_n = compute_metrics(y_np, oof_nested_ens_probs, threshold=0.33)
    ece_n, _ = expected_calibration_error(y_np, oof_nested_ens_probs)
    _, slope_n, _ = calibration_intercept_slope(y_np, oof_nested_ens_probs)
    f_aucs_n = [roc_auc_score(y_np[te], oof_nested_ens_probs[te]) for _, te in fold_splits]
    f_bri_n = [brier_score_loss(y_np[te], oof_nested_ens_probs[te]) for _, te in fold_splits]
    ens_rows.append({
        "strategy": f"Nested_InnerVal_Selected (mean_w={np.mean(nested_weights):.2f})",
        "weight_lr": float(np.mean(nested_weights)),
        "weight_ann": float(1.0 - np.mean(nested_weights)),
        "oof_auroc": m50_n["auroc"],
        "oof_pr_auc": m50_n["pr_auc"],
        "oof_brier_score": m50_n["brier_score"],
        "oof_log_loss": m50_n["log_loss"],
        "oof_ece_10bin": ece_n,
        "oof_cal_slope": slope_n,
        "oof_sens_050": m50_n["sensitivity"],
        "oof_spec_050": m50_n["specificity"],
        "oof_f1_050": m50_n["f1_score"],
        "oof_sens_033": m33_n["sensitivity"],
        "oof_spec_033": m33_n["specificity"],
        "oof_f1_033": m33_n["f1_score"],
        "fold5_auroc_mean": float(np.mean(f_aucs_n)),
        "fold5_auroc_sd": float(np.std(f_aucs_n, ddof=1)),
        "fold5_brier_mean": float(np.mean(f_bri_n)),
        "fold5_brier_sd": float(np.std(f_bri_n, ddof=1)),
    })

    ens_df = pd.DataFrame(ens_rows)
    ens_df.to_csv(OUT_DIR / "phase13_ensemble_comparison.csv", index=False)

    # =========================================================================
    # 7. PAIRED STATISTICAL TESTS & CALIBRATION METRICS SUMMARY JSON
    # =========================================================================
    delong_res = delong_roc_test(y_np, oof_lr, oof_ann)
    mcnemar_050 = mcnemar_test(y_np, lr_pred_050, ann_pred_050)
    mcnemar_033 = mcnemar_test(y_np, lr_pred_033, ann_pred_033)

    # Paired bootstrap B=5000 on OOF patients
    rng = np.random.default_rng(SEED)
    B = 5000
    boot_diffs = {k: [] for k in ["auroc", "pr_auc", "brier", "log_loss", "bal_acc_050", "sens_050", "spec_050", "f1_050"]}
    n = len(y_np)
    for _ in range(B):
        idx = rng.integers(0, n, size=n)
        yb = y_np[idx]
        if len(np.unique(yb)) < 2:
            continue
        p_a = oof_lr[idx]
        p_b = oof_ann[idx]
        pred_a = (p_a >= 0.50).astype(int)
        pred_b = (p_b >= 0.50).astype(int)
        boot_diffs["auroc"].append(roc_auc_score(yb, p_a) - roc_auc_score(yb, p_b))
        boot_diffs["pr_auc"].append(average_precision_score(yb, p_a) - average_precision_score(yb, p_b))
        boot_diffs["brier"].append(brier_score_loss(yb, p_a) - brier_score_loss(yb, p_b))
        boot_diffs["log_loss"].append(log_loss(yb, np.clip(p_a, 1e-7, 1 - 1e-7)) - log_loss(yb, np.clip(p_b, 1e-7, 1 - 1e-7)))
        boot_diffs["bal_acc_050"].append(balanced_accuracy_score(yb, pred_a) - balanced_accuracy_score(yb, pred_b))
        boot_diffs["sens_050"].append(recall_score(yb, pred_a, zero_division=0) - recall_score(yb, pred_b, zero_division=0))
        tn_a, fp_a, _, _ = confusion_matrix(yb, pred_a, labels=[0, 1]).ravel()
        tn_b, fp_b, _, _ = confusion_matrix(yb, pred_b, labels=[0, 1]).ravel()
        boot_diffs["spec_050"].append((tn_a / (tn_a + fp_a)) - (tn_b / (tn_b + fp_b)))
        boot_diffs["f1_050"].append(f1_score(yb, pred_a, zero_division=0) - f1_score(yb, pred_b, zero_division=0))

    boot_summary = {}
    for k, vals in boot_diffs.items():
        arr = np.array(vals)
        boot_summary[k] = {
            "mean_diff_lr_minus_ann": float(np.mean(arr)),
            "ci95_low": float(np.percentile(arr, 2.5)),
            "ci95_high": float(np.percentile(arr, 97.5)),
            "prob_lr_gt_ann": float(np.mean(arr > 0)),
        }

    # Repeated CV paired summary (50 folds)
    rep_lr_df = pd.DataFrame(rep_lr_metrics)
    rep_ann_df = pd.DataFrame(rep_ann_metrics)
    rep_summary = {}
    for col in ["auroc", "pr_auc", "accuracy", "balanced_accuracy", "sensitivity", "specificity", "precision", "f1_score", "brier_score", "log_loss"]:
        diff = rep_lr_df[col] - rep_ann_df[col]
        t_res = stats.ttest_rel(rep_lr_df[col], rep_ann_df[col])
        rep_summary[col] = {
            "lr_mean": float(rep_lr_df[col].mean()),
            "lr_sd": float(rep_lr_df[col].std(ddof=1)),
            "ann_mean": float(rep_ann_df[col].mean()),
            "ann_sd": float(rep_ann_df[col].std(ddof=1)),
            "diff_mean": float(diff.mean()),
            "diff_sd": float(diff.std(ddof=1)),
            "lr_wins_folds": int(np.sum(diff > 0)),
            "ann_wins_folds": int(np.sum(diff < 0)),
            "ties": int(np.sum(diff == 0)),
        }

    # Seed sensitivity summary
    seed_summary = {}
    for s, s_oof in seed_oof_probs.items():
        m = compute_metrics(y_np, s_oof, 0.50)
        seed_summary[str(s)] = m

    # Inner calibration summary
    cal_summary = {}
    for cname, cprobs in [
        ("LR_Uncalibrated_FullOuter", oof_lr),
        ("LR_Uncalibrated_Inner80", oof_lr_inner80),
        ("LR_Platt_InnerCal", oof_lr_platt),
        ("LR_Isotonic_InnerCal", oof_lr_iso),
        ("ANN_Uncalibrated", oof_ann),
        ("ANN_Platt_InnerCal", oof_ann_platt),
        ("ANN_Isotonic_InnerCal", oof_ann_iso),
    ]:
        ece, mce = expected_calibration_error(y_np, cprobs)
        citl, slope, intercept = calibration_intercept_slope(y_np, cprobs)
        m = compute_metrics(y_np, cprobs, 0.50)
        cal_summary[cname] = {
            "auroc": m["auroc"],
            "brier_score": m["brier_score"],
            "log_loss": m["log_loss"],
            "ece_10bin": ece,
            "mce_10bin": mce,
            "citl": citl,
            "slope": slope,
            "intercept": intercept,
        }

    summary_payload = {
        "delong_oof": delong_res,
        "mcnemar_050": mcnemar_050,
        "mcnemar_033": mcnemar_033,
        "bootstrap_5000": boot_summary,
        "repeated_5x10_cv": rep_summary,
        "ann_seed_sensitivity_oof": seed_summary,
        "calibration_oof": cal_summary,
        "nested_ensemble_weights": nested_weights,
        "fold4_prod_ann_vs_lr": {"ann_fold4": m_f4_ann, "lr_oof_fold4": m_f4_lr},
        "group_counts_050": comp_df["comparison_group_050"].value_counts().to_dict(),
    }

    with open(OUT_DIR / "phase13_cv_stats_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    print("\n--- KEY PHASE 2-3 RESULTS (GENUINE OOF N=299) ---")
    print("LR  OOF Metrics:", compute_metrics(y_np, oof_lr, 0.50))
    print("ANN OOF Metrics:", compute_metrics(y_np, oof_ann, 0.50))
    print("DeLong AUROC test:", delong_res)
    print("McNemar @ 0.50:", mcnemar_050)
    print("Repeated 5x10 AUROC:", rep_summary["auroc"])
    print("Repeated 5x10 Brier:", rep_summary["brier_score"])
    print("Repeated 5x10 LogLoss:", rep_summary["log_loss"])
    print("Group counts @ 0.50:", summary_payload["group_counts_050"])
    print("Saved CSVs & JSON to:", OUT_DIR)


if __name__ == "__main__":
    main()
