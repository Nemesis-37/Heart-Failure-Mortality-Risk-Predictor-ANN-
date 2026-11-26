"""
scripts/phase13/run_methodological_audit.py
===========================================
Phase 13 Final Methodological Audit & Independent Verification Script:
1. Verifies exact train/val/test partitions, disjointness, and training sample equivalence.
2. Runs 5x10 Repeated Stratified CV across 4 matched conditions:
   - LR_Outer239 (full outer train ~239)
   - LR_Inner191 (EXACT same inner train ~191 rows as ANN)
   - ANN_Inner191 (inner train ~191 + inner val ~48 early stopping)
   - ANN_RefitOuter239 (best_epoch selected leak-free on inner split, then refit on all 239 outer train rows)
3. Separates Fold-Mean (50 folds), Repeat-Level Pooled OOF (10 repeats), Seed-42 OOF (N=299),
   and Aggregated 10-Repeat OOF predictions.
4. Applies Nadeau & Bengio (2003) / Bouckaert & Frank (2004) corrected resampled t-test (factor 1/50 + n_test/n_train = 0.27)
   and reports per-repeat DeLong AUROC p-values across all 10 repeats.

STRICT RESEARCH-ONLY GUARANTEE:
Preserves all models/, scalers, thresholds, backend, frontend, and historical results.
"""

import copy
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from scipy import stats
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
from sklearn.model_selection import RepeatedStratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "phase13"))

from models.ann_model import HeartFailureANN
from models.logistic_model import create_logistic_model
from run_cv_and_stats import (
    ANN_BATCH_SIZE,
    ANN_EPOCHS,
    ANN_LR,
    ANN_PATIENCE,
    ANN_WD,
    DATA_PATH,
    SEED,
    compute_metrics,
    delong_roc_test,
    set_all_seeds,
)

OUT_DIR = PROJECT_ROOT / "results" / "phase13"


def train_ann_matched(
    X_outer_tr: pd.DataFrame,
    y_outer_tr: pd.Series,
    X_test: pd.DataFrame,
    inner_tr_idx: np.ndarray,
    inner_va_idx: np.ndarray,
    seed: int,
):
    """Train ANN_Inner191 AND also refit ANN_RefitOuter239 for best_epoch on full outer train."""
    set_all_seeds(seed)
    X_tr = X_outer_tr.iloc[inner_tr_idx]
    y_tr = y_outer_tr.iloc[inner_tr_idx]
    X_va = X_outer_tr.iloc[inner_va_idx]
    y_va = y_outer_tr.iloc[inner_va_idx]

    scaler_in = StandardScaler()
    X_tr_s = scaler_in.fit_transform(X_tr)
    X_va_s = scaler_in.transform(X_va)
    X_te_s = scaler_in.transform(X_test)

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
    best_epoch = 1
    patience_ctr = 0

    for epoch in range(ANN_EPOCHS):
        model.train()
        for bx, by in loader:
            opt.zero_grad()
            loss = loss_fn(model(bx), by)
            loss.backward()
            opt.step()

        model.eval()
        with torch.inference_mode():
            v_loss = float(loss_fn(model(X_va_t), y_va_t).item())

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
        p_inner191 = torch.sigmoid(model(X_te_t)).cpu().numpy().ravel()

    # Refit on ALL X_outer_tr (~239 rows) for exact best_epoch (zero test leakage)
    set_all_seeds(seed)
    scaler_out = StandardScaler()
    X_out_s = scaler_out.fit_transform(X_outer_tr)
    X_te_out_s = scaler_out.transform(X_test)
    X_out_t = torch.tensor(X_out_s, dtype=torch.float32)
    y_out_t = torch.tensor(y_outer_tr.to_numpy(), dtype=torch.float32).reshape(-1, 1)
    X_te_out_t = torch.tensor(X_te_out_s, dtype=torch.float32)

    gen2 = torch.Generator().manual_seed(seed)
    loader2 = DataLoader(TensorDataset(X_out_t, y_out_t), batch_size=ANN_BATCH_SIZE, shuffle=True, generator=gen2)
    model2 = HeartFailureANN()
    opt2 = torch.optim.Adam(model2.parameters(), lr=ANN_LR, weight_decay=ANN_WD)

    for _ in range(best_epoch):
        model2.train()
        for bx, by in loader2:
            opt2.zero_grad()
            loss = loss_fn(model2(bx), by)
            loss.backward()
            opt2.step()

    model2.eval()
    with torch.inference_mode():
        p_refit239 = torch.sigmoid(model2(X_te_out_t)).cpu().numpy().ravel()

    return p_inner191, p_refit239, best_epoch, best_loss


def nadeau_bengio_corrected_ttest(diffs: np.ndarray, k_folds: int = 5, n_repeats: int = 10, n_test: float = 59.8, n_train: float = 239.2) -> dict:
    """
    Nadeau & Bengio (2003) / Bouckaert & Frank (2004) corrected resampled paired t-test
    accounting for overlap dependence across repeated k-fold cross-validation splits.
    """
    n_splits = len(diffs)
    assert n_splits == k_folds * n_repeats
    mean_d = float(np.mean(diffs))
    sd_d = float(np.std(diffs, ddof=1))
    var_d = float(np.var(diffs, ddof=1))

    # Naive variance (INVALID - assumes independence)
    se_naive = sd_d / math.sqrt(n_splits)
    t_naive = mean_d / se_naive if se_naive > 0 else 0.0
    p_naive = float(2.0 * (1.0 - stats.t.cdf(abs(t_naive), df=n_splits - 1)))

    # Corrected resampled variance: (1/(K*R) + n_test/n_train) * s^2
    correction_factor = (1.0 / n_splits) + (n_test / n_train)
    se_corr = math.sqrt(correction_factor * var_d)
    t_corr = mean_d / se_corr if se_corr > 0 else 0.0
    df = n_splits - 1
    p_corr = float(2.0 * (1.0 - stats.t.cdf(abs(t_corr), df=df)))
    t_crit = float(stats.t.ppf(0.975, df=df))
    ci_low = mean_d - t_crit * se_corr
    ci_high = mean_d + t_crit * se_corr

    return {
        "mean_diff": mean_d,
        "fold_sd_diff": sd_d,
        "naive_se": se_naive,
        "naive_t": t_naive,
        "naive_p_INVALID": p_naive,
        "correction_factor": correction_factor,
        "corrected_se": se_corr,
        "corrected_t": t_corr,
        "df": df,
        "corrected_p": p_corr,
        "corrected_ci95_low": ci_low,
        "corrected_ci95_high": ci_high,
    }


def main():
    print("=" * 75)
    print("PHASE 13 — FINAL METHODOLOGICAL AUDIT & INDEPENDENT RE-VERIFICATION")
    print("=" * 75)

    df = pd.read_csv(DATA_PATH)
    X = df.drop(columns=["DEATH_EVENT", "time"])
    y = df["DEATH_EVENT"].astype(int)
    y_np = y.to_numpy()

    rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEED)

    # Storage for 10 repeats x 299 OOF arrays per model
    oof_preds = {
        m: np.zeros((10, len(X)), dtype=float)
        for m in ["LR_Outer239", "LR_Inner191", "ANN_Inner191", "ANN_RefitOuter239"]
    }

    fold_records = []
    partition_checks_passed = 0

    for idx_split, (outer_tr_idx, test_idx) in enumerate(rskf.split(X, y)):
        rep = (idx_split // 5) + 1
        fold = (idx_split % 5) + 1

        # Partition disjointness checks
        assert len(set(outer_tr_idx) & set(test_idx)) == 0, "Outer train/test overlap detected!"
        assert len(outer_tr_idx) + len(test_idx) == len(X)

        X_outer_tr, y_outer_tr = X.iloc[outer_tr_idx], y.iloc[outer_tr_idx]
        X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]

        # Inner 80/20 split (identical for LR_Inner191 and ANN_Inner191)
        # Note: in Repeat 1 (Seed 42 5-fold), run_cv_and_stats used seed = SEED + fold for train_test_split
        # whereas in Repeated_5x10_CV, seed = SEED + idx_split + 1. Let's check Repeat 1 uses exact SEED + fold (which equals SEED + idx_split + 1 for idx_split 0..4!)
        split_seed = SEED + idx_split + 1
        inner_tr_idx, inner_va_idx = train_test_split(
            np.arange(len(X_outer_tr)),
            test_size=0.20,
            random_state=split_seed,
            stratify=y_outer_tr,
        )
        assert len(set(inner_tr_idx) & set(inner_va_idx)) == 0, "Inner train/val overlap!"
        assert len(inner_tr_idx) + len(inner_va_idx) == len(X_outer_tr)
        partition_checks_passed += 1

        # 1. LR_Outer239 (full outer train ~239 rows)
        m_lr_out = create_logistic_model()
        m_lr_out.fit(X_outer_tr, y_outer_tr)
        p_lr_out = m_lr_out.predict_proba(X_te)[:, 1]

        # 2. LR_Inner191 (EXACT same ~191 inner rows & scaler as ANN_Inner191)
        m_lr_in = create_logistic_model()
        m_lr_in.fit(X_outer_tr.iloc[inner_tr_idx], y_outer_tr.iloc[inner_tr_idx])
        p_lr_in = m_lr_in.predict_proba(X_te)[:, 1]

        # 3 & 4. ANN_Inner191 & ANN_RefitOuter239
        p_ann_in, p_ann_refit, best_ep, best_vl = train_ann_matched(
            X_outer_tr, y_outer_tr, X_te, inner_tr_idx, inner_va_idx, seed=split_seed
        )

        oof_preds["LR_Outer239"][rep - 1, test_idx] = p_lr_out
        oof_preds["LR_Inner191"][rep - 1, test_idx] = p_lr_in
        oof_preds["ANN_Inner191"][rep - 1, test_idx] = p_ann_in
        oof_preds["ANN_RefitOuter239"][rep - 1, test_idx] = p_ann_refit

        for mname, probs in [
            ("LR_Outer239", p_lr_out),
            ("LR_Inner191", p_lr_in),
            ("ANN_Inner191", p_ann_in),
            ("ANN_RefitOuter239", p_ann_refit),
        ]:
            met = compute_metrics(y_te.to_numpy(), probs, threshold=0.50)
            met33 = compute_metrics(y_te.to_numpy(), probs, threshold=0.33)
            fold_records.append({
                "repeat": rep,
                "fold": fold,
                "split_index": idx_split + 1,
                "model": mname,
                "n_outer_train": len(outer_tr_idx),
                "n_inner_train": len(inner_tr_idx),
                "n_inner_val": len(inner_va_idx),
                "n_test": len(test_idx),
                "n_train_actual_model": len(outer_tr_idx) if "239" in mname else len(inner_tr_idx),
                "best_epoch": best_ep if "ANN" in mname else np.nan,
                **met,
                "sens_033": met33["sensitivity"],
                "spec_033": met33["specificity"],
            })

    folds_df = pd.DataFrame(fold_records)

    # Check exact match with previously saved phase13_cross_validation_results.csv for LR_Outer239 & ANN_Inner191
    prev_cv = pd.read_csv(OUT_DIR / "phase13_cross_validation_results.csv")
    prev_rep = prev_cv[prev_cv["experiment"] == "Repeated_5x10_CV"]
    prev_lr = prev_rep[prev_rep["model"] == "Logistic_Regression"]["auroc"].to_numpy()
    new_lr = folds_df[folds_df["model"] == "LR_Outer239"]["auroc"].to_numpy()
    prev_ann = prev_rep[prev_rep["model"] == "ANN_11_64_32_1"]["auroc"].to_numpy()
    new_ann = folds_df[folds_df["model"] == "ANN_Inner191"]["auroc"].to_numpy()
    max_lr_diff = float(np.max(np.abs(prev_lr - new_lr)))
    max_ann_diff = float(np.max(np.abs(prev_ann - new_ann)))
    print(f"Partition checks passed: {partition_checks_passed}/50")
    print(f"Reproducibility check vs prior CSV -> max|LR AUROC diff|={max_lr_diff:.2e}, max|ANN AUROC diff|={max_ann_diff:.2e}")

    # =========================================================================
    # AGGREGATION MODES VERIFICATION
    # =========================================================================
    agg_summary = {}
    for mname in ["LR_Outer239", "LR_Inner191", "ANN_Inner191", "ANN_RefitOuter239"]:
        sub = folds_df[folds_df["model"] == mname]
        # 1. Mean & SD across 50 folds
        fold50_stats = {
            col: {"mean": float(sub[col].mean()), "sd": float(sub[col].std(ddof=1))}
            for col in ["auroc", "pr_auc", "brier_score", "log_loss", "accuracy", "balanced_accuracy", "sensitivity", "specificity", "f1_score"]
        }
        # 2. Repeat-level Pooled OOF (10 values, one pooled N=299 OOF per repeat)
        rep_pooled = [compute_metrics(y_np, oof_preds[mname][r], 0.50) for r in range(10)]
        rep_pooled_df = pd.DataFrame(rep_pooled)
        rep_pooled_stats = {
            col: {"mean_10repeats": float(rep_pooled_df[col].mean()), "sd_10repeats": float(rep_pooled_df[col].std(ddof=1))}
            for col in ["auroc", "pr_auc", "brier_score", "log_loss", "accuracy", "balanced_accuracy", "sensitivity", "specificity", "f1_score"]
        }
        # 3. Single Seed-42 Repeat 1 Pooled OOF
        repeat1_pooled = rep_pooled[0]
        # 4. Aggregated Repeated OOF (average predicted probability across 10 repeats per patient)
        mean_prob_patient = oof_preds[mname].mean(axis=0)
        agg10_oof = compute_metrics(y_np, mean_prob_patient, 0.50)

        agg_summary[mname] = {
            "fold50_mean_sd": fold50_stats,
            "repeat10_pooled_oof_mean_sd": rep_pooled_stats,
            "repeat1_seed42_pooled_oof": repeat1_pooled,
            "repeat10_averaged_patient_oof": agg10_oof,
        }

    # =========================================================================
    # NADEAU-BENGIO CORRECTED RESAMPLED PAIRED TESTS (ALL 3 PAIRINGS)
    # =========================================================================
    pairings = [
        ("LR_Outer239_vs_ANN_Inner191", "LR_Outer239", "ANN_Inner191"),
        ("LR_Inner191_vs_ANN_Inner191_MatchedData", "LR_Inner191", "ANN_Inner191"),
        ("LR_Outer239_vs_ANN_RefitOuter239_Matched239", "LR_Outer239", "ANN_RefitOuter239"),
    ]
    stat_rows = []
    corrected_tests_json = {}

    for pair_label, m_a, m_b in pairings:
        sub_a = folds_df[folds_df["model"] == m_a].sort_values("split_index").reset_index(drop=True)
        sub_b = folds_df[folds_df["model"] == m_b].sort_values("split_index").reset_index(drop=True)
        corrected_tests_json[pair_label] = {}
        for col in ["auroc", "pr_auc", "brier_score", "log_loss", "accuracy", "balanced_accuracy", "sensitivity", "specificity", "f1_score"]:
            diffs = sub_a[col].to_numpy() - sub_b[col].to_numpy()
            res = nadeau_bengio_corrected_ttest(diffs, k_folds=5, n_repeats=10, n_test=299 * 0.2, n_train=299 * 0.8)
            corrected_tests_json[pair_label][col] = res
            stat_rows.append({
                "comparison": pair_label,
                "metric": col,
                "model_a": m_a,
                "model_a_50fold_mean": float(sub_a[col].mean()),
                "model_a_50fold_sd": float(sub_a[col].std(ddof=1)),
                "model_b": m_b,
                "model_b_50fold_mean": float(sub_b[col].mean()),
                "model_b_50fold_sd": float(sub_b[col].std(ddof=1)),
                "mean_diff_a_minus_b": res["mean_diff"],
                "fold_sd_diff": res["fold_sd_diff"],
                "naive_se_INVALID": res["naive_se"],
                "naive_p_INVALID": res["naive_p_INVALID"],
                "nb_corrected_se": res["corrected_se"],
                "nb_corrected_t": res["corrected_t"],
                "nb_corrected_p": res["corrected_p"],
                "nb_ci95_low": res["corrected_ci95_low"],
                "nb_ci95_high": res["corrected_ci95_high"],
                "significant_at_005_corrected": bool(res["corrected_p"] < 0.05),
                "a_fold_wins": int(np.sum(diffs > 0)),
                "b_fold_wins": int(np.sum(diffs < 0)),
                "ties": int(np.sum(diffs == 0)),
            })

    # Per-repeat DeLong AUROC tests across all 10 repeats
    delong_per_repeat = {}
    for pair_label, m_a, m_b in pairings:
        d_rows = []
        for r in range(10):
            dl = delong_roc_test(y_np, oof_preds[m_a][r], oof_preds[m_b][r])
            dl["repeat"] = r + 1
            d_rows.append(dl)
        delong_per_repeat[pair_label] = d_rows

    stat_df = pd.DataFrame(stat_rows)
    stat_df.to_csv(OUT_DIR / "phase13_corrected_cv_statistics.csv", index=False)
    folds_df.to_csv(OUT_DIR / "phase13_audit_50fold_details.csv", index=False)

    audit_payload = {
        "partition_checks_passed": partition_checks_passed,
        "reproducibility_max_diff": {"lr_auroc": max_lr_diff, "ann_auroc": max_ann_diff},
        "aggregation_summary": agg_summary,
        "corrected_tests": corrected_tests_json,
        "delong_per_repeat": delong_per_repeat,
    }
    with open(OUT_DIR / "phase13_methodological_audit_summary.json", "w", encoding="utf-8") as f:
        json.dump(audit_payload, f, indent=2)

    print("\n--- CORRECTED 5x10 CV SUMMARY ---")
    print(stat_df[stat_df["metric"].isin(["auroc", "pr_auc", "brier_score", "log_loss"])][
        ["comparison", "metric", "model_a_50fold_mean", "model_b_50fold_mean", "mean_diff_a_minus_b", "nb_corrected_se", "nb_corrected_t", "nb_corrected_p", "significant_at_005_corrected"]
    ].round(4).to_string(index=False))

    print("\n--- REPEAT 1..10 DELONG P-VALUES (LR_Outer239 vs ANN_Inner191) ---")
    for d in delong_per_repeat["LR_Outer239_vs_ANN_Inner191"]:
        print(f"Repeat {d['repeat']:2d}: LR={d['auc_lr']:.4f}, ANN={d['auc_ann']:.4f}, diff={d['diff_lr_minus_ann']:+.4f}, p={d['p_value']:.4f}")


if __name__ == "__main__":
    main()
