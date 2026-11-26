"""
scripts/phase13/run_behavioral_and_explainability.py
====================================================
Phase 13 Isolated Research Script covering:
- Phase 5: Feature-by-Feature Behavioural Analysis (all 11 features x 5 profiles)
- Phase 6: 2D Feature Interaction Grids (6 key pairs)
- Phase 7: Dedicated Platelet-Count Investigation (across profiles, all 299 patients, and CV folds)
- Phase 8: Explainability Analysis (LR coeffs/ORs/SEs, OOF Permutation Importance, Integrated Gradients)

STRICT RESEARCH-ONLY GUARANTEE:
Reads dataset & existing production artifacts read-only; writes ONLY to results/phase13/.
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from models.ann_model import HeartFailureANN
from models.logistic_model import create_logistic_model
from run_cv_and_stats import train_ann_single_fold

DATA_PATH = PROJECT_ROOT / "dataset" / "heart_failure_clinical_records_dataset.csv"
OUT_DIR = PROJECT_ROOT / "results" / "phase13"
OUT_DIR.mkdir(parents=True, exist_ok=True)


PROFILES = {
    "Low_Risk_Baseline": {
        "age": 50.0, "anaemia": 0, "creatinine_phosphokinase": 168.0, "diabetes": 0,
        "ejection_fraction": 45.0, "high_blood_pressure": 0, "platelets": 276000.0,
        "serum_creatinine": 0.9, "serum_sodium": 140.0, "sex": 1, "smoking": 0,
    },
    "Cohort_Median_Profile": {
        "age": 60.0, "anaemia": 0, "creatinine_phosphokinase": 250.0, "diabetes": 0,
        "ejection_fraction": 38.0, "high_blood_pressure": 0, "platelets": 262000.0,
        "serum_creatinine": 1.1, "serum_sodium": 137.0, "sex": 1, "smoking": 0,
    },
    "Borderline_Cardiorenal": {
        "age": 70.0, "anaemia": 1, "creatinine_phosphokinase": 350.0, "diabetes": 1,
        "ejection_fraction": 30.0, "high_blood_pressure": 1, "platelets": 240000.0,
        "serum_creatinine": 1.6, "serum_sodium": 134.0, "sex": 1, "smoking": 0,
    },
    "High_Risk_Critical": {
        "age": 75.0, "anaemia": 1, "creatinine_phosphokinase": 582.0, "diabetes": 1,
        "ejection_fraction": 20.0, "high_blood_pressure": 1, "platelets": 265000.0,
        "serum_creatinine": 2.5, "serum_sodium": 130.0, "sex": 1, "smoking": 1,
    },
    "Female_Hypertensive_Moderate": {
        "age": 58.0, "anaemia": 1, "creatinine_phosphokinase": 210.0, "diabetes": 0,
        "ejection_fraction": 35.0, "high_blood_pressure": 1, "platelets": 300000.0,
        "serum_creatinine": 1.1, "serum_sodium": 138.0, "sex": 0, "smoking": 0,
    },
}


def predict_ann_batch(ann_model, ann_scaler, df_X: pd.DataFrame) -> np.ndarray:
    scaled = ann_scaler.transform(df_X)
    t = torch.tensor(scaled, dtype=torch.float32)
    with torch.inference_mode():
        return torch.sigmoid(ann_model(t)).cpu().numpy().ravel()


def integrated_gradients_ann(ann_model, ann_scaler, x_row: pd.DataFrame, steps: int = 64) -> np.ndarray:
    """
    Exact Integrated Gradients in standardized feature space using cohort-mean baseline (z = 0)
    with respect to output logit (log-odds) AND output probability.
    Returns (ig_logit, ig_prob).
    """
    x_scaled = ann_scaler.transform(x_row).astype(np.float32)[0]
    baseline = np.zeros_like(x_scaled, dtype=np.float32)
    alphas = np.linspace(0.0, 1.0, steps + 1, dtype=np.float32)

    # Interpolated path
    path = np.array([baseline + a * (x_scaled - baseline) for a in alphas], dtype=np.float32)
    inp = torch.tensor(path, dtype=torch.float32, requires_grad=True)

    # Grad of logit
    logits = ann_model(inp).sum()
    ann_model.zero_grad()
    logits.backward(retain_graph=True)
    grads_logit = inp.grad.detach().numpy()

    # Trapezoidal rule along path
    avg_grad_logit = (grads_logit[:-1] + grads_logit[1:]).mean(axis=0) / 1.0 * 0.5
    ig_logit = (x_scaled - baseline) * avg_grad_logit

    # Grad of probability
    inp2 = torch.tensor(path, dtype=torch.float32, requires_grad=True)
    probs = torch.sigmoid(ann_model(inp2)).sum()
    ann_model.zero_grad()
    probs.backward()
    grads_prob = inp2.grad.detach().numpy()
    avg_grad_prob = (grads_prob[:-1] + grads_prob[1:]).mean(axis=0) * 0.5
    ig_prob = (x_scaled - baseline) * avg_grad_prob
    return ig_logit, ig_prob


def main():
    print("=" * 75)
    print("PHASE 13 — BEHAVIOURAL PERTURBATION, PLATELETS, INTERACTIONS & EXPLAINABILITY")
    print("=" * 75)

    df = pd.read_csv(DATA_PATH)
    X = df.drop(columns=["DEATH_EVENT", "time"])
    y = df["DEATH_EVENT"].astype(int)
    feature_names = list(X.columns)

    # Load production artifacts read-only
    prod_lr = joblib.load(PROJECT_ROOT / "models" / "logistic_regression_pipeline.joblib")
    prod_ann_scaler = joblib.load(PROJECT_ROOT / "models" / "ann_scaler.joblib")
    prod_ann = HeartFailureANN()
    prod_ann.load_state_dict(torch.load(PROJECT_ROOT / "models" / "ann_model.pth", map_location="cpu", weights_only=True))
    prod_ann.eval()

    # Also train the 5 CV fold models in memory so we can distinguish general CV behaviour vs Fold-4 prod checkpoint
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_splits = list(skf.split(X, y))
    cv_lr_models = []
    cv_ann_models = []
    for fold, (tr_idx, te_idx) in enumerate(fold_splits, start=1):
        X_tr, y_tr = X.iloc[tr_idx], y.iloc[tr_idx]
        X_te = X.iloc[te_idx]
        lr_f = create_logistic_model()
        lr_f.fit(X_tr, y_tr)
        _, ann_f, scaler_f, _ = train_ann_single_fold(X_tr, y_tr, X_te, seed=42 + fold, return_inner_val_preds=True)
        cv_lr_models.append(lr_f)
        cv_ann_models.append((ann_f, scaler_f))

    # =========================================================================
    # PHASE 5: FEATURE-BY-FEATURE PERTURBATION ACROSS ALL 11 FEATURES
    # =========================================================================
    obs_min = X.min().to_dict()
    obs_max = X.max().to_dict()

    feature_grids = {
        "age": np.linspace(30, 95, 27),  # includes <40 plausible & 40-95 observed
        "anaemia": [0, 1],
        "creatinine_phosphokinase": np.array([20, 50, 100, 150, 250, 400, 582, 800, 1200, 2000, 3500, 5500, 7861]),
        "diabetes": [0, 1],
        "ejection_fraction": np.linspace(12, 80, 25),
        "high_blood_pressure": [0, 1],
        "platelets": np.array([15000, 25100, 50000, 100000, 150000, 200000, 250000, 262000, 300000, 350000, 450000, 600000, 750000, 850000, 950000]),
        "serum_creatinine": np.array([0.4, 0.5, 0.7, 0.9, 1.1, 1.3, 1.6, 2.0, 2.5, 3.5, 5.0, 7.0, 9.4]),
        "serum_sodium": np.linspace(113, 148, 22),
        "sex": [0, 1],
        "smoking": [0, 1],
    }

    pert_rows = []
    for prof_name, base_vals in PROFILES.items():
        base_df = pd.DataFrame([base_vals], columns=feature_names)
        base_lr = float(prod_lr.predict_proba(base_df)[0, 1])
        base_ann = float(predict_ann_batch(prod_ann, prod_ann_scaler, base_df)[0])

        for feat in feature_names:
            grid = feature_grids[feat]
            rows_batch = []
            for v in grid:
                r = dict(base_vals)
                r[feat] = int(v) if feat in ("anaemia", "diabetes", "high_blood_pressure", "sex", "smoking") else float(v)
                rows_batch.append(r)
            batch_df = pd.DataFrame(rows_batch, columns=feature_names)

            lr_p = prod_lr.predict_proba(batch_df)[:, 1]
            ann_p = predict_ann_batch(prod_ann, prod_ann_scaler, batch_df)

            # 5-fold CV ensemble mean across folds
            cv_lr_p = np.mean([m.predict_proba(batch_df)[:, 1] for m in cv_lr_models], axis=0)
            cv_ann_p = np.mean([predict_ann_batch(m, sc, batch_df) for m, sc in cv_ann_models], axis=0)

            for i, v in enumerate(grid):
                in_obs = (v >= obs_min[feat] - 1e-9) and (v <= obs_max[feat] + 1e-9)
                pert_rows.append({
                    "profile": prof_name,
                    "feature": feat,
                    "feature_value": float(v),
                    "in_observed_dataset_range": bool(in_obs),
                    "prod_lr_prob": float(lr_p[i]),
                    "prod_ann_prob": float(ann_p[i]),
                    "prod_prob_diff_lr_minus_ann": float(lr_p[i] - ann_p[i]),
                    "delta_lr_from_profile_base": float(lr_p[i] - base_lr),
                    "delta_ann_from_profile_base": float(ann_p[i] - base_ann),
                    "cv5_lr_mean_prob": float(cv_lr_p[i]),
                    "cv5_ann_mean_prob": float(cv_ann_p[i]),
                })

    pert_df = pd.DataFrame(pert_rows)
    pert_df.to_csv(OUT_DIR / "phase13_feature_perturbation_results.csv", index=False)

    # =========================================================================
    # PHASE 6: 2D FEATURE INTERACTION GRIDS (6 REQUESTED PAIRS)
    # =========================================================================
    interaction_pairs = [
        ("age", np.linspace(40, 90, 11), "ejection_fraction", np.linspace(15, 70, 12)),
        ("age", np.linspace(40, 90, 11), "serum_creatinine", np.array([0.7, 1.0, 1.3, 1.8, 2.5, 3.5, 5.0, 7.0])),
        ("ejection_fraction", np.linspace(15, 70, 12), "serum_creatinine", np.array([0.7, 1.0, 1.3, 1.8, 2.5, 3.5, 5.0, 7.0])),
        ("platelets", np.array([50000, 100000, 150000, 200000, 262000, 350000, 450000, 600000, 800000]),
         "serum_creatinine", np.array([0.7, 1.0, 1.3, 1.8, 2.5, 3.5, 5.0, 7.0])),
        ("serum_sodium", np.linspace(120, 146, 11), "ejection_fraction", np.linspace(15, 70, 12)),
        ("age", np.linspace(40, 90, 11), "serum_sodium", np.linspace(120, 146, 11)),
    ]

    inter_rows = []
    med_base = PROFILES["Cohort_Median_Profile"]
    for f1, g1, f2, g2 in interaction_pairs:
        pair_name = f"{f1}_x_{f2}"
        batch = []
        coords = []
        for v1 in g1:
            for v2 in g2:
                r = dict(med_base)
                r[f1] = float(v1)
                r[f2] = float(v2)
                batch.append(r)
                coords.append((float(v1), float(v2)))
        bdf = pd.DataFrame(batch, columns=feature_names)
        lr_p = prod_lr.predict_proba(bdf)[:, 1]
        ann_p = predict_ann_batch(prod_ann, prod_ann_scaler, bdf)
        cv_lr_p = np.mean([m.predict_proba(bdf)[:, 1] for m in cv_lr_models], axis=0)
        cv_ann_p = np.mean([predict_ann_batch(m, sc, bdf) for m, sc in cv_ann_models], axis=0)
        for idx, (v1, v2) in enumerate(coords):
            inter_rows.append({
                "pair": pair_name,
                "feature_1": f1,
                "value_1": v1,
                "feature_2": f2,
                "value_2": v2,
                "prod_lr_prob": float(lr_p[idx]),
                "prod_ann_prob": float(ann_p[idx]),
                "prob_diff_lr_minus_ann": float(lr_p[idx] - ann_p[idx]),
                "cv5_lr_mean_prob": float(cv_lr_p[idx]),
                "cv5_ann_mean_prob": float(cv_ann_p[idx]),
            })

    inter_df = pd.DataFrame(inter_rows)
    inter_df.to_csv(OUT_DIR / "phase13_feature_interaction_results.csv", index=False)

    # =========================================================================
    # PHASE 7: DEDICATED PLATELET INVESTIGATION ACROSS ALL 299 PATIENTS & FOLDS
    # =========================================================================
    # For every patient in dataset, test dropping platelets from 350,000 -> 150,000 (and 250k -> 100k)
    df_high_plt = X.copy()
    df_high_plt["platelets"] = 350000.0
    df_low_plt = X.copy()
    df_low_plt["platelets"] = 150000.0

    lr_hi = prod_lr.predict_proba(df_high_plt)[:, 1]
    lr_lo = prod_lr.predict_proba(df_low_plt)[:, 1]
    ann_hi = predict_ann_batch(prod_ann, prod_ann_scaler, df_high_plt)
    ann_lo = predict_ann_batch(prod_ann, prod_ann_scaler, df_low_plt)

    d_lr = lr_lo - lr_hi     # negative means LR probability decreased when platelets dropped
    d_ann = ann_lo - ann_hi  # positive means ANN probability increased when platelets dropped

    opposing_count = int(np.sum((d_lr < 0) & (d_ann > 0)))
    both_down = int(np.sum((d_lr < 0) & (d_ann < 0)))

    # Also check across the 5 CV ANN fold models (not just Fold 4 prod) on Cohort_Median_Profile
    plt_grid = np.array([15000, 25100, 50000, 100000, 150000, 200000, 250000, 300000, 400000, 500000, 650000, 850000, 1000000])
    plt_df = pd.DataFrame([{**PROFILES["Cohort_Median_Profile"], "platelets": float(v)} for v in plt_grid], columns=feature_names)
    fold_plt_curves = {"platelets": plt_grid.tolist(), "prod_lr": prod_lr.predict_proba(plt_df)[:, 1].tolist(), "prod_ann": predict_ann_batch(prod_ann, prod_ann_scaler, plt_df).tolist()}
    for f_i, (ann_f, sc_f) in enumerate(cv_ann_models, start=1):
        fold_plt_curves[f"cv_ann_fold{f_i}"] = predict_ann_batch(ann_f, sc_f, plt_df).tolist()

    # Check clinical data mortality rate by platelet quartile
    df_tmp = df.copy()
    df_tmp["plt_bin"] = pd.qcut(df_tmp["platelets"], q=4)
    plt_quartiles = df_tmp.groupby("plt_bin", observed=False)["DEATH_EVENT"].agg(["count", "sum", "mean"]).reset_index()
    plt_quartile_records = [
        {"bin": str(r["plt_bin"]), "count": int(r["count"]), "deaths": int(r["sum"]), "mortality_rate": float(r["mean"])}
        for _, r in plt_quartiles.iterrows()
    ]

    # Correlation between platelets and other predictors in dataset
    plt_corrs = df.drop(columns=["time"]).corr(numeric_only=True)["platelets"].drop("platelets").to_dict()

    platelet_summary = {
        "n_patients_tested_350k_to_150k": len(X),
        "lr_decreases_count": int(np.sum(d_lr < 0)),
        "ann_increases_count": int(np.sum(d_ann > 0)),
        "ann_decreases_count": int(np.sum(d_ann < 0)),
        "opposite_direction_lr_down_ann_up_count": opposing_count,
        "same_direction_both_down_count": both_down,
        "mean_delta_lr_350k_to_150k": float(np.mean(d_lr)),
        "mean_delta_ann_350k_to_150k": float(np.mean(d_ann)),
        "min_delta_ann_350k_to_150k": float(np.min(d_ann)),
        "max_delta_ann_350k_to_150k": float(np.max(d_ann)),
        "fold_curves_median_profile": fold_plt_curves,
        "dataset_platelet_quartiles": plt_quartile_records,
        "dataset_platelet_correlations": {k: float(v) for k, v in plt_corrs.items()},
    }
    with open(OUT_DIR / "phase13_platelet_summary.json", "w", encoding="utf-8") as f:
        json.dump(platelet_summary, f, indent=2)

    # =========================================================================
    # PHASE 8: EXPLAINABILITY (LR COEFFICIENTS/OR/SE + OOF PERMUTATION + IG)
    # =========================================================================
    clf = prod_lr.named_steps["classifier"]
    scaler_lr = prod_lr.named_steps["scaler"]
    coefs_std = clf.coef_[0]
    intercept_std = float(clf.intercept_[0])
    scales = scaler_lr.scale_
    coefs_raw = coefs_std / scales

    # Wald Standard Errors for standardized LR coefficients using Fisher information (X_s^T W X_s + lambda I)^-1
    X_s_full = scaler_lr.transform(X)
    X_design = np.column_stack([np.ones(len(X_s_full)), X_s_full])
    p_hat = prod_lr.predict_proba(X)[:, 1]
    W = p_hat * (1.0 - p_hat)
    # Fisher information matrix (with L2 C=1.0 penalty on non-intercept weights)
    reg_diag = np.diag([0.0] + [1.0] * len(feature_names))
    info_mat = (X_design.T * W) @ X_design + reg_diag
    cov_mat = np.linalg.inv(info_mat)
    se_std = np.sqrt(np.diag(cov_mat))[1:]

    lr_explain_rows = []
    for i, feat in enumerate(feature_names):
        b = float(coefs_std[i])
        se = float(se_std[i])
        or_sd = float(np.exp(b))
        ci_low = float(np.exp(b - 1.96 * se))
        ci_high = float(np.exp(b + 1.96 * se))
        z_wald = float(b / se) if se > 0 else 0.0
        lr_explain_rows.append({
            "feature": feat,
            "std_coef": b,
            "std_se": se,
            "wald_z": z_wald,
            "odds_ratio_per_1sd": or_sd,
            "or_95ci_low": ci_low,
            "or_95ci_high": ci_high,
            "raw_coef_per_unit": float(coefs_raw[i]),
            "scaler_mean": float(scaler_lr.mean_[i]),
            "scaler_std": float(scales[i]),
            "abs_std_coef": abs(b),
        })

    # Out-of-fold Permutation Feature Importance (measured by AUROC drop across 5 untouched test folds, 30 repeats)
    rng_perm = np.random.default_rng(42)
    n_repeats = 30
    perm_drops_lr = {f: [] for f in feature_names}
    perm_drops_ann = {f: [] for f in feature_names}

    for fold_idx, (_, test_idx) in enumerate(fold_splits):
        X_te = X.iloc[test_idx].copy()
        y_te = y.iloc[test_idx].to_numpy()
        lr_f = cv_lr_models[fold_idx]
        ann_f, sc_f = cv_ann_models[fold_idx]

        base_auc_lr = roc_auc_score(y_te, lr_f.predict_proba(X_te)[:, 1])
        base_auc_ann = roc_auc_score(y_te, predict_ann_batch(ann_f, sc_f, X_te))

        for feat in feature_names:
            for _ in range(n_repeats):
                X_perm = X_te.copy()
                X_perm[feat] = rng_perm.permutation(X_perm[feat].to_numpy())
                auc_lr_p = roc_auc_score(y_te, lr_f.predict_proba(X_perm)[:, 1])
                auc_ann_p = roc_auc_score(y_te, predict_ann_batch(ann_f, sc_f, X_perm))
                perm_drops_lr[feat].append(base_auc_lr - auc_lr_p)
                perm_drops_ann[feat].append(base_auc_ann - auc_ann_p)

    # Integrated Gradients on production ANN (mean |IG| across all 299 patients + local profiles)
    ig_logits_all = []
    ig_probs_all = []
    for idx in range(len(X)):
        row_df = X.iloc[[idx]]
        igl, igp = integrated_gradients_ann(prod_ann, prod_ann_scaler, row_df, steps=50)
        ig_logits_all.append(igl)
        ig_probs_all.append(igp)
    ig_logits_arr = np.array(ig_logits_all)
    ig_probs_arr = np.array(ig_probs_all)

    local_explanations = {}
    for pname, pvals in PROFILES.items():
        pdf = pd.DataFrame([pvals], columns=feature_names)
        igl, igp = integrated_gradients_ann(prod_ann, prod_ann_scaler, pdf, steps=64)
        lr_std_x = scaler_lr.transform(pdf)[0]
        lr_logodds_contrib = lr_std_x * coefs_std
        local_explanations[pname] = {
            "prod_lr_prob": float(prod_lr.predict_proba(pdf)[0, 1]),
            "prod_ann_prob": float(predict_ann_batch(prod_ann, prod_ann_scaler, pdf)[0]),
            "lr_intercept": intercept_std,
            "lr_logodds_contrib": {feature_names[i]: float(lr_logodds_contrib[i]) for i in range(len(feature_names))},
            "ann_ig_logit_contrib": {feature_names[i]: float(igl[i]) for i in range(len(feature_names))},
            "ann_ig_prob_contrib": {feature_names[i]: float(igp[i]) for i in range(len(feature_names))},
        }

    explain_summary = {
        "lr_intercept_std": intercept_std,
        "lr_features": lr_explain_rows,
        "oof_permutation_importance_auroc_drop": {
            feat: {
                "lr_mean_drop": float(np.mean(perm_drops_lr[feat])),
                "lr_sd_drop": float(np.std(perm_drops_lr[feat], ddof=1)),
                "ann_mean_drop": float(np.mean(perm_drops_ann[feat])),
                "ann_sd_drop": float(np.std(perm_drops_ann[feat], ddof=1)),
            }
            for feat in feature_names
        },
        "ann_global_integrated_gradients": {
            feature_names[i]: {
                "mean_abs_ig_logit": float(np.mean(np.abs(ig_logits_arr[:, i]))),
                "mean_signed_ig_logit": float(np.mean(ig_logits_arr[:, i])),
                "mean_abs_ig_prob": float(np.mean(np.abs(ig_probs_arr[:, i]))),
            }
            for i in range(len(feature_names))
        },
        "local_profile_explanations": local_explanations,
    }

    with open(OUT_DIR / "phase13_explainability_summary.json", "w", encoding="utf-8") as f:
        json.dump(explain_summary, f, indent=2)

    print("Saved feature perturbations:", len(pert_df), "rows")
    print("Saved 2D interaction grids:", len(inter_df), "rows")
    print("Platelet reduction 350k->150k: LR decreases in", platelet_summary["lr_decreases_count"], "/ 299; ANN increases in", platelet_summary["ann_increases_count"], "/ 299")
    print("Saved explainability summary & platelet summary to:", OUT_DIR)


if __name__ == "__main__":
    main()
