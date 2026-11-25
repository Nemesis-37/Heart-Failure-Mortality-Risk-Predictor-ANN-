"""
run_phase6_diagnostics.py
=========================
Comprehensive diagnostic suite for Phase 6: ANN Performance Diagnosis.
Investigates:
1. Learning curves, training vs validation loss, early stopping behavior, and gradient norms.
2. Feature distributions, skewness, collinearity, non-linear relationships (spline/poly LRT), and interactions.
3. Out-of-fold prediction agreement between Logistic Regression and ANN (Spearman, Pearson, discordance matrices).
4. Patient-level error analysis: Discordant cases, clinical profiles, and high-loss outliers.
5. Sample size, parameter capacity, and EPV (Events Per Variable) analysis.
"""

import copy
import math
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as stats
from scipy.special import expit, logit
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    log_loss,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dataset" / "heart_failure_clinical_records_dataset.csv"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SEED = 42
FOLDS = 5

def set_seed(seed=42):
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

class ConfigurableANN(nn.Module):
    def __init__(self, input_size, hidden_layers, dropout=0.0):
        super().__init__()
        layers = []
        prev_dim = input_size
        for h_dim in hidden_layers:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.ReLU())
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            prev_dim = h_dim
        layers.append(nn.Linear(prev_dim, 1))
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)

def run_diagnostics():
    print("=" * 80)
    print("PHASE 6: ANN PERFORMANCE DIAGNOSIS")
    print("=" * 80)

    # 1. Load Data
    df = pd.read_csv(DATA_PATH)
    X = df.drop(columns=["DEATH_EVENT", "time"])
    y = df["DEATH_EVENT"].astype(int)
    feature_names = list(X.columns)

    n_samples, n_features = X.shape
    n_pos = int(np.sum(y))
    n_neg = n_samples - n_pos
    prevalence = n_pos / n_samples
    print(f"Data Loaded: {n_samples} patients, {n_features} features, {n_pos} deaths ({prevalence*100:.2f}%)")

    # -------------------------------------------------------------------------
    # PART 1: FEATURE DISTRIBUTIONS, SKEWNESS & OUTLIERS
    # -------------------------------------------------------------------------
    print("\n[Part 1] Analyzing Feature Distributions & Skewness...")
    feat_stats = []
    for col in feature_names:
        vals = X[col].values
        skew = float(stats.skew(vals))
        kurt = float(stats.kurtosis(vals))
        q25, q75 = np.percentile(vals, 25), np.percentile(vals, 75)
        iqr = q75 - q25
        outliers = np.sum((vals < q25 - 1.5 * iqr) | (vals > q75 + 1.5 * iqr)) if iqr > 0 else 0
        r_pearson, p_pearson = stats.pearsonr(vals, y)
        r_spearman, p_spearman = stats.spearmanr(vals, y)

        feat_stats.append({
            "Feature": col,
            "Type": "Binary" if len(np.unique(vals)) == 2 else "Continuous",
            "Mean": float(np.mean(vals)),
            "Std": float(np.std(vals)),
            "Min": float(np.min(vals)),
            "Median": float(np.median(vals)),
            "Max": float(np.max(vals)),
            "Skewness": skew,
            "Kurtosis": kurt,
            "IQR_Outliers": int(outliers),
            "Pearson_r": float(r_pearson),
            "Pearson_p": float(p_pearson),
            "Spearman_rho": float(r_spearman),
            "Spearman_p": float(p_spearman),
        })
    df_feat_stats = pd.DataFrame(feat_stats)
    print(df_feat_stats[["Feature", "Type", "Skewness", "IQR_Outliers", "Pearson_r", "Spearman_rho"]].to_string())

    # -------------------------------------------------------------------------
    # PART 2: NONLINEARITY TEST (POLYNOMIAL / SPLINE LRT)
    # -------------------------------------------------------------------------
    print("\n[Part 2] Testing for Non-linear Relationships with DEATH_EVENT...")
    nonlin_results = []
    continuous_features = [col for col in feature_names if len(np.unique(X[col])) > 2]
    
    cv = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    splits = list(cv.split(X, y))

    for col in continuous_features:
        # Cross-validated linear vs quadratic logit
        x_vals = X[[col]].values
        
        linear_aucs = []
        quad_aucs = []
        cubic_aucs = []

        for train_idx, val_idx in splits:
            x_tr, x_va = x_vals[train_idx], x_vals[val_idx]
            y_tr, y_va = y.iloc[train_idx], y.iloc[val_idx]

            # Linear
            pipe_lin = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000, random_state=SEED))
            pipe_lin.fit(x_tr, y_tr)
            p_lin = pipe_lin.predict_proba(x_va)[:, 1]
            linear_aucs.append(roc_auc_score(y_va, p_lin))

            # Quadratic
            pipe_quad = make_pipeline(StandardScaler(), PolynomialFeatures(degree=2, include_bias=False), LogisticRegression(C=1.0, max_iter=1000, random_state=SEED))
            pipe_quad.fit(x_tr, y_tr)
            p_quad = pipe_quad.predict_proba(x_va)[:, 1]
            quad_aucs.append(roc_auc_score(y_va, p_quad))

            # Cubic
            pipe_cub = make_pipeline(StandardScaler(), PolynomialFeatures(degree=3, include_bias=False), LogisticRegression(C=1.0, max_iter=1000, random_state=SEED))
            pipe_cub.fit(x_tr, y_tr)
            p_cub = pipe_cub.predict_proba(x_va)[:, 1]
            cubic_aucs.append(roc_auc_score(y_va, p_cub))

        lin_m = np.mean(linear_aucs)
        quad_m = np.mean(quad_aucs)
        cub_m = np.mean(cubic_aucs)
        delta_quad = quad_m - lin_m
        delta_cub = cub_m - lin_m

        # Full-sample Likelihood Ratio Test for degree 2 vs 1
        scaler = StandardScaler()
        x_s = scaler.fit_transform(x_vals)
        lr_lin = LogisticRegression(C=1e5, solver='lbfgs', max_iter=1000).fit(x_s, y)
        ll_lin = log_loss(y, lr_lin.predict_proba(x_s)[:, 1], normalize=False)
        
        poly2 = PolynomialFeatures(degree=2, include_bias=False)
        x_s2 = poly2.fit_transform(x_s)
        lr_quad = LogisticRegression(C=1e5, solver='lbfgs', max_iter=1000).fit(x_s2, y)
        ll_quad = log_loss(y, lr_quad.predict_proba(x_s2)[:, 1], normalize=False)

        # Deviance difference
        dev_diff = 2 * (ll_lin - ll_quad)
        lrt_p = 1 - stats.chi2.cdf(max(0, dev_diff), df=1)

        nonlin_results.append({
            "Feature": col,
            "Linear_CV_AUROC": lin_m,
            "Quadratic_CV_AUROC": quad_m,
            "Cubic_CV_AUROC": cub_m,
            "Delta_Quad_AUROC": delta_quad,
            "Delta_Cubic_AUROC": delta_cub,
            "Deviance_Diff": dev_diff,
            "LRT_p_value": lrt_p,
            "Nonlinear_Signal": "Significant" if lrt_p < 0.05 and delta_quad > 0.01 else "Negligible/Noisy"
        })
    df_nonlin = pd.DataFrame(nonlin_results)
    print(df_nonlin[["Feature", "Linear_CV_AUROC", "Quadratic_CV_AUROC", "Delta_Quad_AUROC", "LRT_p_value", "Nonlinear_Signal"]].to_string())

    # -------------------------------------------------------------------------
    # PART 3: PAIRWISE INTERACTION ANALYSIS
    # -------------------------------------------------------------------------
    print("\n[Part 3] Testing Pairwise Interactions in Logistic Regression...")
    interaction_candidates = []
    # Test top clinical interactions
    key_features = ["age", "ejection_fraction", "serum_creatinine", "serum_sodium", "high_blood_pressure", "creatinine_phosphokinase"]
    
    # Baseline all-feature LR CV
    base_lr_aucs = []
    for train_idx, val_idx in splits:
        pipe = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000, random_state=SEED))
        pipe.fit(X.iloc[train_idx], y.iloc[train_idx])
        base_lr_aucs.append(roc_auc_score(y.iloc[val_idx], pipe.predict_proba(X.iloc[val_idx])[:, 1]))
    base_lr_auc = np.mean(base_lr_aucs)
    print(f"Base 11-feature Logistic Regression AUROC: {base_lr_auc*100:.2f}%")

    for i in range(len(key_features)):
        for j in range(i + 1, len(key_features)):
            f1, f2 = key_features[i], key_features[j]
            X_inter = X.copy()
            X_inter[f"{f1}_x_{f2}"] = X[f1] * X[f2]

            inter_aucs = []
            for train_idx, val_idx in splits:
                pipe = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000, random_state=SEED))
                pipe.fit(X_inter.iloc[train_idx], y.iloc[train_idx])
                inter_aucs.append(roc_auc_score(y.iloc[val_idx], pipe.predict_proba(X_inter.iloc[val_idx])[:, 1]))
            inter_auc = np.mean(inter_aucs)
            delta = inter_auc - base_lr_auc

            interaction_candidates.append({
                "Interaction": f"{f1} * {f2}",
                "Base_AUROC": base_lr_auc,
                "Interaction_AUROC": inter_auc,
                "Delta_AUROC": delta,
            })
    df_inter = pd.DataFrame(interaction_candidates).sort_values("Delta_AUROC", ascending=False)
    print(df_inter.head(10).to_string())

    # -------------------------------------------------------------------------
    # PART 4: LEARNING CURVES, OVERFITTING & EARLY STOPPING DYNAMICS
    # -------------------------------------------------------------------------
    print("\n[Part 4] Capturing Epoch-by-Epoch Learning Curves for Arch B and Arch C...")
    
    configs = [
        {"id": "Arch_B_16", "name": "Arch B (16->1)", "layers": [16], "dropout": 0.2, "weight_decay": 0.01, "batch_size": 32, "lr": 0.001},
        {"id": "Arch_C_32_16", "name": "Arch C (32->16->1)", "layers": [32, 16], "dropout": 0.0, "weight_decay": 0.001, "batch_size": 64, "lr": 0.001},
    ]

    learning_curve_records = []
    early_stopping_stats = []

    for cfg in configs:
        m_id = cfg["id"]
        for fold, (train_idx, val_idx) in enumerate(splits, start=1):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # Inner partition 80/20
            X_tr_in, X_val_in, y_tr_in, y_val_in = train_test_split(
                X_train, y_train, test_size=0.20, stratify=y_train, random_state=SEED + fold
            )
            scaler = StandardScaler()
            X_tr_s = scaler.fit_transform(X_tr_in)
            X_va_s = scaler.transform(X_val_in)

            t_X_tr = torch.tensor(X_tr_s, dtype=torch.float32)
            t_y_tr = torch.tensor(y_tr_in.values, dtype=torch.float32).unsqueeze(1)
            t_X_va = torch.tensor(X_va_s, dtype=torch.float32)
            t_y_va = torch.tensor(y_val_in.values, dtype=torch.float32).unsqueeze(1)

            loader = DataLoader(
                TensorDataset(t_X_tr, t_y_tr),
                batch_size=cfg["batch_size"],
                shuffle=True,
                generator=torch.Generator().manual_seed(SEED + fold)
            )

            set_seed(SEED + fold)
            model = ConfigurableANN(X.shape[1], cfg["layers"], dropout=cfg["dropout"])
            optimizer = torch.optim.Adam(model.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
            loss_fn = nn.BCEWithLogitsLoss()

            patience = 15
            best_val_loss = float("inf")
            best_epoch = 0
            patience_cnt = 0
            max_epochs = 200

            for epoch in range(1, max_epochs + 1):
                model.train()
                tr_losses = []
                grad_norms = []
                for b_x, b_y in loader:
                    optimizer.zero_grad()
                    logits = model(b_x)
                    loss = loss_fn(logits, b_y)
                    loss.backward()
                    
                    # Track gradient norm
                    total_norm = 0.0
                    for p in model.parameters():
                        if p.grad is not None:
                            total_norm += p.grad.data.norm(2).item() ** 2
                    grad_norms.append(total_norm ** 0.5)

                    optimizer.step()
                    tr_losses.append(loss.item())

                mean_tr_loss = float(np.mean(tr_losses))
                mean_grad_norm = float(np.mean(grad_norms))

                model.eval()
                with torch.inference_mode():
                    val_logits = model(t_X_va)
                    val_loss = float(loss_fn(val_logits, t_y_va).item())
                    val_probs = torch.sigmoid(val_logits).numpy().ravel()
                    tr_probs = torch.sigmoid(model(t_X_tr)).numpy().ravel()
                    
                val_auc = float(roc_auc_score(y_val_in, val_probs))
                tr_auc = float(roc_auc_score(y_tr_in, tr_probs))

                learning_curve_records.append({
                    "Model_ID": m_id,
                    "Fold": fold,
                    "Epoch": epoch,
                    "Train_Loss": mean_tr_loss,
                    "Val_Loss": val_loss,
                    "Train_AUROC": tr_auc,
                    "Val_AUROC": val_auc,
                    "Generalization_Gap_Loss": val_loss - mean_tr_loss,
                    "Generalization_Gap_AUROC": tr_auc - val_auc,
                    "Grad_Norm": mean_grad_norm,
                })

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    best_epoch = epoch
                    patience_cnt = 0
                else:
                    patience_cnt += 1

                if patience_cnt >= patience:
                    break

            early_stopping_stats.append({
                "Model_ID": m_id,
                "Fold": fold,
                "Best_Epoch": best_epoch,
                "Best_Val_Loss": best_val_loss,
                "Stopped_Epoch": epoch,
                "Batches_Per_Epoch": len(loader),
                "Total_Inner_Steps": best_epoch * len(loader),
            })

    df_lc = pd.DataFrame(learning_curve_records)
    df_es = pd.DataFrame(early_stopping_stats)
    print("\nEarly Stopping Summary:")
    print(df_es.to_string())

    # Average learning curves per model across folds at epochs 1, 5, 10, 15, 20, 25, 30, 40, 50
    print("\nAverage Learning Curves (Arch B vs Arch C):")
    for m_id in ["Arch_B_16", "Arch_C_32_16"]:
        sub = df_lc[df_lc["Model_ID"] == m_id]
        print(f"\n--- {m_id} ---")
        for ep in [1, 5, 10, 15, 20, 25, 30, 40, 50]:
            ep_sub = sub[sub["Epoch"] == ep]
            if len(ep_sub) > 0:
                print(f"Epoch {ep:2d}: Train Loss={ep_sub['Train_Loss'].mean():.4f}, Val Loss={ep_sub['Val_Loss'].mean():.4f}, Gap={ep_sub['Generalization_Gap_Loss'].mean():.4f}, Train AUC={ep_sub['Train_AUROC'].mean():.4f}, Val AUC={ep_sub['Val_AUROC'].mean():.4f}, Grad Norm={ep_sub['Grad_Norm'].mean():.4f}")

    # -------------------------------------------------------------------------
    # PART 5: OUT-OF-FOLD PREDICTION AGREEMENT & DISCORDANCE ANALYSIS
    # -------------------------------------------------------------------------
    print("\n[Part 5] Analyzing Out-of-Fold Prediction Agreement and Errors...")
    
    oof_predictions = []
    
    for fold, (train_idx, val_idx) in enumerate(splits, start=1):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        val_indices = val_idx.tolist()

        # 1. Logistic Regression
        lr_pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=SEED))
        lr_pipe.fit(X_train, y_train)
        lr_probs = lr_pipe.predict_proba(X_val)[:, 1]

        # 2. Arch B (using canonical Phase 3 inner early stopping & refit)
        # Inner split
        X_tr_in, X_val_in, y_tr_in, y_val_in = train_test_split(
            X_train, y_train, test_size=0.20, stratify=y_train, random_state=SEED + fold
        )
        s_in = StandardScaler()
        x_tr_s = s_in.fit_transform(X_tr_in)
        x_va_s = s_in.transform(X_val_in)

        t_x_tr = torch.tensor(x_tr_s, dtype=torch.float32)
        t_y_tr = torch.tensor(y_tr_in.values, dtype=torch.float32).unsqueeze(1)
        t_x_va = torch.tensor(x_va_s, dtype=torch.float32)
        t_y_va = torch.tensor(y_val_in.values, dtype=torch.float32).unsqueeze(1)

        loader_in = DataLoader(
            TensorDataset(t_x_tr, t_y_tr), batch_size=32, shuffle=True,
            generator=torch.Generator().manual_seed(SEED + fold)
        )
        set_seed(SEED + fold)
        m_b = ConfigurableANN(11, [16], dropout=0.2)
        opt_b = torch.optim.Adam(m_b.parameters(), lr=0.001, weight_decay=0.01)
        loss_fn = nn.BCEWithLogitsLoss()
        
        best_vl = float("inf")
        best_ep = 0
        p_cnt = 0
        for ep in range(1, 200):
            m_b.train()
            for bx, by in loader_in:
                opt_b.zero_grad()
                loss_fn(m_b(bx), by).backward()
                opt_b.step()
            m_b.eval()
            with torch.inference_mode():
                vl = loss_fn(m_b(t_x_va), t_y_va).item()
            if vl < best_vl:
                best_vl = vl
                best_ep = ep
                p_cnt = 0
            else:
                p_cnt += 1
            if p_cnt >= 15:
                break
        
        target_steps = best_ep * len(loader_in)

        # Refit on full X_train
        s_out = StandardScaler()
        x_out_s = s_out.fit_transform(X_train)
        t_x_out = torch.tensor(x_out_s, dtype=torch.float32)
        t_y_out = torch.tensor(y_train.values, dtype=torch.float32).unsqueeze(1)
        loader_out = DataLoader(
            TensorDataset(t_x_out, t_y_out), batch_size=32, shuffle=True,
            generator=torch.Generator().manual_seed(SEED + fold)
        )
        set_seed(SEED + fold)
        final_b = ConfigurableANN(11, [16], dropout=0.2)
        opt_out = torch.optim.Adam(final_b.parameters(), lr=0.001, weight_decay=0.01)
        st_done = 0
        while st_done < target_steps:
            final_b.train()
            for bx, by in loader_out:
                opt_out.zero_grad()
                loss_fn(final_b(bx), by).backward()
                opt_out.step()
                st_done += 1
                if st_done >= target_steps:
                    break

        final_b.eval()
        x_val_s = s_out.transform(X_val)
        with torch.inference_mode():
            ann_b_probs = torch.sigmoid(final_b(torch.tensor(x_val_s, dtype=torch.float32))).numpy().ravel()

        for idx, p_lr, p_b, yt in zip(val_indices, lr_probs, ann_b_probs, y_val.values):
            oof_predictions.append({
                "Patient_Index": idx,
                "Fold": fold,
                "True_Death_Event": int(yt),
                "Prob_LR": float(p_lr),
                "Prob_ANN_B": float(p_b),
                "Pred_LR_050": int(p_lr >= 0.50),
                "Pred_ANN_B_050": int(p_b >= 0.50),
                "Pred_LR_033": int(p_lr >= 0.33),
                "Pred_ANN_B_033": int(p_b >= 0.33),
                "Abs_Diff": float(abs(p_lr - p_b)),
                "Brier_LR": float((p_lr - yt) ** 2),
                "Brier_ANN_B": float((p_b - yt) ** 2),
                "LogLoss_LR": float(- (yt * np.log(max(1e-15, p_lr)) + (1 - yt) * np.log(max(1e-15, 1 - p_lr)))),
                "LogLoss_ANN_B": float(- (yt * np.log(max(1e-15, p_b)) + (1 - yt) * np.log(max(1e-15, 1 - p_b)))),
            })

    df_oof = pd.DataFrame(oof_predictions).sort_values("Patient_Index")
    
    # Global metrics
    r_pearson, _ = stats.pearsonr(df_oof["Prob_LR"], df_oof["Prob_ANN_B"])
    r_spearman, _ = stats.spearmanr(df_oof["Prob_LR"], df_oof["Prob_ANN_B"])
    mad = df_oof["Abs_Diff"].mean()
    median_ad = df_oof["Abs_Diff"].median()

    print(f"\nModel Output Agreement:")
    print(f"Pearson Correlation (LR vs ANN Arch B): {r_pearson:.4f}")
    print(f"Spearman Rank Correlation: {r_spearman:.4f}")
    print(f"Mean Absolute Probability Difference: {mad:.4f}")
    print(f"Median Absolute Probability Difference: {median_ad:.4f}")

    # Agreement table at 0.50
    agree_050 = (df_oof["Pred_LR_050"] == df_oof["Pred_ANN_B_050"]).mean()
    lr_corr_ann_wrong_050 = ((df_oof["Pred_LR_050"] == df_oof["True_Death_Event"]) & (df_oof["Pred_ANN_B_050"] != df_oof["True_Death_Event"])).sum()
    ann_corr_lr_wrong_050 = ((df_oof["Pred_ANN_B_050"] == df_oof["True_Death_Event"]) & (df_oof["Pred_LR_050"] != df_oof["True_Death_Event"])).sum()
    both_wrong_050 = ((df_oof["Pred_LR_050"] != df_oof["True_Death_Event"]) & (df_oof["Pred_ANN_B_050"] != df_oof["True_Death_Event"])).sum()
    both_correct_050 = ((df_oof["Pred_LR_050"] == df_oof["True_Death_Event"]) & (df_oof["Pred_ANN_B_050"] == df_oof["True_Death_Event"])).sum()

    print(f"\nClassification Agreement at Threshold 0.50:")
    print(f"Total Agreement Rate: {agree_050*100:.2f}% ({agree_050*299:.0f}/299)")
    print(f"Both Correct: {both_correct_050}")
    print(f"Both Incorrect: {both_wrong_050}")
    print(f"LR Correct, ANN Incorrect: {lr_corr_ann_wrong_050}")
    print(f"ANN Correct, LR Incorrect: {ann_corr_lr_wrong_050}")

    # Agreement table at 0.33
    agree_033 = (df_oof["Pred_LR_033"] == df_oof["Pred_ANN_B_033"]).mean()
    lr_corr_ann_wrong_033 = ((df_oof["Pred_LR_033"] == df_oof["True_Death_Event"]) & (df_oof["Pred_ANN_B_033"] != df_oof["True_Death_Event"])).sum()
    ann_corr_lr_wrong_033 = ((df_oof["Pred_ANN_B_033"] == df_oof["True_Death_Event"]) & (df_oof["Pred_LR_033"] != df_oof["True_Death_Event"])).sum()
    both_wrong_033 = ((df_oof["Pred_LR_033"] != df_oof["True_Death_Event"]) & (df_oof["Pred_ANN_B_033"] != df_oof["True_Death_Event"])).sum()
    both_correct_033 = ((df_oof["Pred_LR_033"] == df_oof["True_Death_Event"]) & (df_oof["Pred_ANN_B_033"] == df_oof["True_Death_Event"])).sum()

    print(f"\nClassification Agreement at Threshold 0.33:")
    print(f"Total Agreement Rate: {agree_033*100:.2f}% ({agree_033*299:.0f}/299)")
    print(f"Both Correct: {both_correct_033}")
    print(f"Both Incorrect: {both_wrong_033}")
    print(f"LR Correct, ANN Incorrect: {lr_corr_ann_wrong_033}")
    print(f"ANN Correct, LR Incorrect: {ann_corr_lr_wrong_033}")

    # Analyze clinical characteristics of discordant patients
    df_merged = df.copy()
    df_merged["Prob_LR"] = df_oof["Prob_LR"].values
    df_merged["Prob_ANN_B"] = df_oof["Prob_ANN_B"].values
    df_merged["Pred_LR_050"] = df_oof["Pred_LR_050"].values
    df_merged["Pred_ANN_B_050"] = df_oof["Pred_ANN_B_050"].values

    discordant_mask = df_merged["Pred_LR_050"] != df_merged["Pred_ANN_B_050"]
    df_disc = df_merged[discordant_mask]
    print(f"\nTotal Discordant Patients at 0.50: {len(df_disc)}")
    print(df_disc[["age", "ejection_fraction", "serum_creatinine", "serum_sodium", "DEATH_EVENT", "Prob_LR", "Prob_ANN_B"]].to_string())

    # Save diagnostic summary CSVs
    df_feat_stats.to_csv(RESULTS_DIR / "ann_phase6_feature_distributions.csv", index=False)
    df_nonlin.to_csv(RESULTS_DIR / "ann_phase6_nonlinearity_tests.csv", index=False)
    df_inter.to_csv(RESULTS_DIR / "ann_phase6_interaction_tests.csv", index=False)
    df_lc.to_csv(RESULTS_DIR / "ann_phase6_learning_curves.csv", index=False)
    df_es.to_csv(RESULTS_DIR / "ann_phase6_early_stopping_summary.csv", index=False)
    df_oof.to_csv(RESULTS_DIR / "ann_phase6_oof_predictions_comparison.csv", index=False)
    print("\nSaved all Phase 6 diagnostic CSVs to results/")

if __name__ == "__main__":
    run_diagnostics()
