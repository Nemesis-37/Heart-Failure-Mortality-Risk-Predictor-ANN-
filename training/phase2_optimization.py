"""
phase2_optimization.py
======================
Heart Failure Mortality Risk Predictor — ANN Optimization Phase 2
Architecture and Hyperparameter Optimization with Strict Nested Isolation.

Evaluation Protocol:
- 5-Fold Stratified Cross-Validation (SEED=42, shuffle=True).
- Identical outer splits across Logistic Regression and all ANN variants.
- Outer test folds isolated from architecture and hyperparameter selection.
- Early stopping on inner validation partition (20% of outer train).
- Step-adjusted refit on outer training set to match inner optimizer budget.
- Threshold fixed at 0.50.
"""

import copy
import random
from pathlib import Path
from scipy import stats

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
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dataset" / "heart_failure_clinical_records_dataset.csv"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SEED = 42
FOLDS = 5
MAX_EPOCHS = 100
PATIENCE = 10


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


def calculate_metrics(y_true, probabilities):
    predictions = (probabilities >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    return {
        "Accuracy": float(accuracy_score(y_true, predictions)),
        "Precision": float(precision_score(y_true, predictions, zero_division=0)),
        "Sensitivity": float(recall_score(y_true, predictions, zero_division=0)),
        "Specificity": float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0,
        "F1_Score": float(f1_score(y_true, predictions, zero_division=0)),
        "AUROC": float(roc_auc_score(y_true, probabilities)),
        "Brier_Score": float(brier_score_loss(y_true, probabilities)),
        "Mean_Probability": float(np.mean(probabilities)),
    }


def train_with_early_stopping(
    X_train, y_train, X_stop, y_stop, config, seed, pos_weight=None
):
    set_seed(seed)
    batch_size = config.get("batch_size", 32)
    lr = config.get("lr", 0.001)
    weight_decay = config.get("weight_decay", 0.001)
    dropout = config.get("dropout", 0.2)
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

    if pos_weight is not None:
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    else:
        loss_fn = nn.BCEWithLogitsLoss()

    best_loss = float("inf")
    best_state = None
    best_epoch = 1
    patience_count = 0
    inner_batches_per_epoch = len(loader)
    train_loss_at_best = None

    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        running_train_loss = 0.0
        batch_count = 0

        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            logits = model(batch_X)
            loss = loss_fn(logits, batch_y)
            loss.backward()
            optimizer.step()
            running_train_loss += loss.item()
            batch_count += 1

        avg_train_loss = running_train_loss / max(batch_count, 1)

        model.eval()
        with torch.inference_mode():
            val_logits = model(stop_X)
            val_loss = loss_fn(val_logits, stop_y).item()

        if val_loss < best_loss:
            best_loss = val_loss
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch
            patience_count = 0
            train_loss_at_best = avg_train_loss
        else:
            patience_count += 1

        if patience_count >= PATIENCE:
            break

    total_inner_steps = best_epoch * inner_batches_per_epoch

    # Evaluate best inner model on stop set to get inner validation AUROC
    model.load_state_dict(best_state)
    model.eval()
    with torch.inference_mode():
        stop_probs = torch.sigmoid(model(stop_X)).numpy().ravel()
    inner_val_auroc = roc_auc_score(y_stop.to_numpy(), stop_probs)

    return {
        "best_epoch": best_epoch,
        "best_val_loss": best_loss,
        "train_loss_at_best": train_loss_at_best,
        "total_inner_steps": total_inner_steps,
        "inner_batches_per_epoch": inner_batches_per_epoch,
        "inner_val_auroc": float(inner_val_auroc),
    }


def fit_final_fold_model(
    X_train, y_train, config, seed, target_steps, pos_weight=None
):
    set_seed(seed)
    batch_size = config.get("batch_size", 32)
    lr = config.get("lr", 0.001)
    weight_decay = config.get("weight_decay", 0.001)
    dropout = config.get("dropout", 0.2)
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
    if pos_weight is not None:
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    else:
        loss_fn = nn.BCEWithLogitsLoss()

    outer_batches_per_epoch = len(loader)
    steps_run = 0
    final_train_loss = 0.0

    while steps_run < target_steps:
        model.train()
        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            logits = model(batch_X)
            loss = loss_fn(logits, batch_y)
            loss.backward()
            optimizer.step()
            steps_run += 1
            final_train_loss = loss.item()
            if steps_run >= target_steps:
                break

    return model, scaler, steps_run, outer_batches_per_epoch, final_train_loss


def run_phase2():
    print("=" * 75)
    print("ANN OPTIMIZATION PHASE 2: ARCHITECTURE & HYPERPARAMETER SEARCH")
    print("=" * 75)

    df = pd.read_csv(DATA_PATH)
    X = df.drop(columns=["DEATH_EVENT", "time"])
    y = df["DEATH_EVENT"].astype(int)

    cv = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    splits = list(cv.split(X, y))

    all_results = []

    # 1. Evaluate Logistic Regression Baseline on identical outer folds
    lr_aurocs = []
    lr_briers = []
    print("\n--- 1. Evaluating Logistic Regression Baseline ---")
    for fold, (train_idx, val_idx) in enumerate(splits, start=1):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        lr_pipe = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, random_state=SEED),
        )
        lr_pipe.fit(X_train, y_train)
        probabilities = lr_pipe.predict_proba(X_val)[:, 1]
        metrics = calculate_metrics(y_val.to_numpy(), probabilities)
        lr_aurocs.append(metrics["AUROC"])
        lr_briers.append(metrics["Brier_Score"])

        all_results.append({
            "Experiment_Type": "Baseline",
            "Model": "Logistic_Regression",
            "Architecture": "Linear",
            "Layers": "11->1",
            "Parameters": 12,
            "Dropout": 0.0,
            "Weight_Decay": 0.0,
            "Batch_Size": "Full",
            "Loss_Type": "Unweighted_BCE",
            "Fold": fold,
            "Inner_Best_Epoch": None,
            "Target_Steps": None,
            "Outer_Steps_Run": None,
            "Train_Loss": None,
            "Inner_Val_Loss": None,
            "Inner_Val_AUROC": None,
            "Pos_Weight": 1.0,
            **metrics,
        })
        print(f"LR | Fold {fold} | AUROC={metrics['AUROC']:.4f} | Brier={metrics['Brier_Score']:.4f} | Sens={metrics['Sensitivity']:.4f} | Spec={metrics['Specificity']:.4f}")

    print(f"--> Logistic Regression Mean AUROC: {np.mean(lr_aurocs)*100:.4f}% (std: {np.std(lr_aurocs, ddof=1):.4f})")

    # 2. Define Phase 2 Experimental Matrix
    # Architectures to compare (Task 1):
    ARCHITECTURES = {
        "Arch_A_8": {"layers": [8], "desc": "11->8->1"},
        "Arch_B_16": {"layers": [16], "desc": "11->16->1"},
        "Arch_C_32_16": {"layers": [32, 16], "desc": "11->32->16->1"},
        "Arch_D_64_32": {"layers": [64, 32], "desc": "11->64->32->1"},
    }

    # Controlled Configurations to explore
    # Phase 2 Grid covering Task 1 (architectures), Task 2 (hyperparameters: dropout, weight decay, batch size), Task 3 (loss)
    CONFIGS = []

    # Stage 1: Pure Architecture Comparison under standard baseline params (Dropout=0.2, WD=0.001, BS=32, LR=0.001, Unweighted)
    for arch_key, arch_info in ARCHITECTURES.items():
        CONFIGS.append({
            "exp_type": "Architecture_Comparison",
            "arch_key": arch_key,
            "layers": arch_info["layers"],
            "desc": arch_info["desc"],
            "dropout": 0.2,
            "weight_decay": 0.001,
            "batch_size": 32,
            "lr": 0.001,
            "weighted": False,
        })

    # Stage 2: Architecture Comparison with Weighted loss
    for arch_key, arch_info in ARCHITECTURES.items():
        CONFIGS.append({
            "exp_type": "Architecture_Weighted",
            "arch_key": arch_key,
            "layers": arch_info["layers"],
            "desc": arch_info["desc"],
            "dropout": 0.2,
            "weight_decay": 0.001,
            "batch_size": 32,
            "lr": 0.001,
            "weighted": True,
        })

    # Stage 3: Hyperparameter Search across promising architectures:
    # Testing Dropout (0.0, 0.1, 0.2), Weight Decay (0.001, 0.01), Batch Size (32, 64)
    # We focus search on compact Arch B (16), Arch A (8), and baseline Arch C (32, 16)
    for arch_key in ["Arch_B_16", "Arch_A_8", "Arch_C_32_16"]:
        layers = ARCHITECTURES[arch_key]["layers"]
        desc = ARCHITECTURES[arch_key]["desc"]

        # Varying Dropout: 0.0, 0.1 (0.2 is in Stage 1)
        for dp in [0.0, 0.1]:
            CONFIGS.append({
                "exp_type": "HP_Dropout",
                "arch_key": arch_key,
                "layers": layers,
                "desc": desc,
                "dropout": dp,
                "weight_decay": 0.001,
                "batch_size": 32,
                "lr": 0.001,
                "weighted": False,
            })

        # Varying Weight Decay: 0.01 (stronger regularization)
        for dp in [0.0, 0.2]:
            CONFIGS.append({
                "exp_type": "HP_WeightDecay",
                "arch_key": arch_key,
                "layers": layers,
                "desc": desc,
                "dropout": dp,
                "weight_decay": 0.01,
                "batch_size": 32,
                "lr": 0.001,
                "weighted": False,
            })

        # Varying Batch Size: 64 (vs 32)
        for dp in [0.0, 0.2]:
            CONFIGS.append({
                "exp_type": "HP_BatchSize",
                "arch_key": arch_key,
                "layers": layers,
                "desc": desc,
                "dropout": dp,
                "weight_decay": 0.001,
                "batch_size": 64,
                "lr": 0.001,
                "weighted": False,
            })

        # High-regularization combinations with weighted loss to test calibration mitigation
        CONFIGS.append({
            "exp_type": "HP_Weighted_Regularized",
            "arch_key": arch_key,
            "layers": layers,
            "desc": desc,
            "dropout": 0.2,
            "weight_decay": 0.01,
            "batch_size": 32,
            "lr": 0.001,
            "weighted": True,
        })

    # Eliminate any duplicate configs
    unique_configs = []
    seen = set()
    for c in CONFIGS:
        key = (
            tuple(c["layers"]),
            c["dropout"],
            c["weight_decay"],
            c["batch_size"],
            c["lr"],
            c["weighted"],
        )
        if key not in seen:
            seen.add(key)
            unique_configs.append(c)

    print(f"\nTotal distinct experimental configurations to evaluate: {len(unique_configs)}")

    # 3. Execute Controlled Cross-Validation
    for cfg_idx, cfg in enumerate(unique_configs, start=1):
        loss_label = "Weighted" if cfg["weighted"] else "Unweighted"
        model_name = (
            f"{cfg['arch_key']}_dp{cfg['dropout']}_wd{cfg['weight_decay']}_"
            f"bs{cfg['batch_size']}_{loss_label}"
        )
        sample_model = ConfigurableANN(11, cfg["layers"], dropout=cfg["dropout"])
        param_count = count_parameters(sample_model)

        print(
            f"\n[{cfg_idx}/{len(unique_configs)}] Running {model_name} | "
            f"Arch={cfg['desc']} ({param_count} params) | DP={cfg['dropout']} | "
            f"WD={cfg['weight_decay']} | BS={cfg['batch_size']} | {loss_label}"
        )

        for fold, (train_idx, val_idx) in enumerate(splits, start=1):
            X_outer_train = X.iloc[train_idx]
            X_outer_val = X.iloc[val_idx]
            y_outer_train = y.iloc[train_idx]
            y_outer_val = y.iloc[val_idx]

            # Inner 80/20 early stopping partition
            inner_train_idx, stop_idx = train_test_split(
                np.arange(len(X_outer_train)),
                test_size=0.2,
                random_state=SEED,
                stratify=y_outer_train,
            )

            X_inner = X_outer_train.iloc[inner_train_idx]
            y_inner = y_outer_train.iloc[inner_train_idx]
            X_stop = X_outer_train.iloc[stop_idx]
            y_stop = y_outer_train.iloc[stop_idx]

            # Compute fold-specific class weights using current training data only
            if cfg["weighted"]:
                y_inner_arr = y_inner.to_numpy()
                inner_pos = int(np.sum(y_inner_arr == 1))
                inner_neg = int(np.sum(y_inner_arr == 0))
                inner_pw = torch.tensor([inner_neg / inner_pos], dtype=torch.float32)

                y_outer_arr = y_outer_train.to_numpy()
                outer_pos = int(np.sum(y_outer_arr == 1))
                outer_neg = int(np.sum(y_outer_arr == 0))
                outer_pw = torch.tensor([outer_neg / outer_pos], dtype=torch.float32)
            else:
                inner_pw = None
                outer_pw = None

            seed_val = SEED + fold + cfg_idx * 100

            # 1. Inner early stopping
            es_res = train_with_early_stopping(
                X_inner,
                y_inner,
                X_stop,
                y_stop,
                cfg,
                seed=seed_val,
                pos_weight=inner_pw,
            )

            best_epoch = es_res["best_epoch"]
            target_steps = es_res["total_inner_steps"]
            inner_batches = es_res["inner_batches_per_epoch"]
            inner_val_loss = es_res["best_val_loss"]
            inner_train_loss = es_res["train_loss_at_best"]
            inner_val_auroc = es_res["inner_val_auroc"]

            # 2. Refit using step-adjusted outer training budget
            model, scaler, steps_run, outer_batches, final_train_loss = fit_final_fold_model(
                X_outer_train,
                y_outer_train,
                cfg,
                seed=seed_val,
                target_steps=target_steps,
                pos_weight=outer_pw,
            )

            # 3. Outer evaluation on untouched test fold
            X_val_scaled = scaler.transform(X_outer_val)
            val_tensor = torch.tensor(X_val_scaled, dtype=torch.float32)

            model.eval()
            with torch.inference_mode():
                logits = model(val_tensor)
                probabilities = torch.sigmoid(logits).numpy().ravel()

            metrics = calculate_metrics(y_outer_val.to_numpy(), probabilities)
            equiv_epochs = round(steps_run / max(outer_batches, 1), 2)

            all_results.append({
                "Experiment_Type": cfg["exp_type"],
                "Model": model_name,
                "Architecture": cfg["arch_key"],
                "Layers": cfg["desc"],
                "Parameters": param_count,
                "Dropout": cfg["dropout"],
                "Weight_Decay": cfg["weight_decay"],
                "Batch_Size": cfg["batch_size"],
                "Loss_Type": loss_label,
                "Fold": fold,
                "Inner_Best_Epoch": best_epoch,
                "Target_Steps": target_steps,
                "Outer_Steps_Run": steps_run,
                "Equivalent_Epochs": equiv_epochs,
                "Train_Loss": final_train_loss,
                "Inner_Val_Loss": inner_val_loss,
                "Inner_Val_AUROC": inner_val_auroc,
                "Pos_Weight": float(outer_pw.item()) if outer_pw is not None else 1.0,
                **metrics,
            })

            print(
                f"  Fold {fold} | Inner Ep={best_epoch:2d} (Steps={target_steps:3d}) | "
                f"AUROC={metrics['AUROC']:.4f} | Brier={metrics['Brier_Score']:.4f} | "
                f"Sens={metrics['Sensitivity']:.4f} | Spec={metrics['Specificity']:.4f}"
            )

    # 4. Save and Process Results
    results_df = pd.DataFrame(all_results)
    fold_results_path = RESULTS_DIR / "ann_phase2_experiments_fold_results.csv"
    results_df.to_csv(fold_results_path, index=False)
    print(f"\n--> Fold-level results saved to: {fold_results_path}")

    # Summary by Model
    metric_cols = [
        "AUROC",
        "Accuracy",
        "Sensitivity",
        "Specificity",
        "Precision",
        "F1_Score",
        "Brier_Score",
        "Mean_Probability",
    ]

    summary_records = []
    for model_name, grp in results_df.groupby("Model", sort=False):
        row = {
            "Model": model_name,
            "Architecture": grp["Architecture"].iloc[0],
            "Layers": grp["Layers"].iloc[0],
            "Parameters": grp["Parameters"].iloc[0],
            "Dropout": grp["Dropout"].iloc[0],
            "Weight_Decay": grp["Weight_Decay"].iloc[0],
            "Batch_Size": grp["Batch_Size"].iloc[0],
            "Loss_Type": grp["Loss_Type"].iloc[0],
            "Mean_Inner_Epoch": grp["Inner_Best_Epoch"].mean(),
            "Mean_Train_Loss": grp["Train_Loss"].mean(),
            "Mean_Inner_Val_Loss": grp["Inner_Val_Loss"].mean(),
        }
        for m in metric_cols:
            row[f"{m}_Mean"] = grp[m].mean()
            row[f"{m}_Std"] = grp[m].std(ddof=1)
        summary_records.append(row)

    summary_df = pd.DataFrame(summary_records)
    summary_path = RESULTS_DIR / "ann_phase2_experiments_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"--> Summary saved to: {summary_path}")

    # 5. Extract Dedicated Comparison Tables
    # A. Architecture Comparison Table (under baseline hyperparams: Dropout=0.2, WD=0.001, BS=32, Unweighted)
    arch_df = summary_df[
        (summary_df["Loss_Type"] == "Unweighted") &
        (summary_df["Dropout"] == 0.2) &
        (summary_df["Weight_Decay"] == 0.001) &
        (summary_df["Batch_Size"] == 32)
    ].sort_values(by="Parameters", ascending=True)

    arch_comp_path = RESULTS_DIR / "ann_phase2_architecture_comparison.csv"
    arch_df.to_csv(arch_comp_path, index=False)

    # B. Loss Comparison Table (Unweighted vs Weighted for all architectures)
    loss_comp_rows = []
    for arch_key in ARCHITECTURES.keys():
        unw = summary_df[
            (summary_df["Architecture"] == arch_key) &
            (summary_df["Loss_Type"] == "Unweighted") &
            (summary_df["Dropout"] == 0.2) &
            (summary_df["Weight_Decay"] == 0.001) &
            (summary_df["Batch_Size"] == 32)
        ]
        wtd = summary_df[
            (summary_df["Architecture"] == arch_key) &
            (summary_df["Loss_Type"] == "Weighted") &
            (summary_df["Dropout"] == 0.2) &
            (summary_df["Weight_Decay"] == 0.001) &
            (summary_df["Batch_Size"] == 32)
        ]
        if not unw.empty and not wtd.empty:
            loss_comp_rows.append(unw.iloc[0])
            loss_comp_rows.append(wtd.iloc[0])

    loss_comp_df = pd.DataFrame(loss_comp_rows)
    loss_comp_path = RESULTS_DIR / "ann_phase2_loss_comparison.csv"
    loss_comp_df.to_csv(loss_comp_path, index=False)

    # 6. Statistical Comparison Against Logistic Regression
    print("\n" + "=" * 75)
    print("TOP CANDIDATE ANN MODELS VS LOGISTIC REGRESSION (5-FOLD COMPARISON)")
    print("=" * 75)

    # Sort models by AUROC Mean
    sorted_models = summary_df.sort_values(by="AUROC_Mean", ascending=False)
    print(
        sorted_models[[
            "Model", "Layers", "Parameters", "Dropout", "Weight_Decay",
            "Batch_Size", "Loss_Type", "AUROC_Mean", "AUROC_Std",
            "Sensitivity_Mean", "Specificity_Mean", "Brier_Score_Mean"
        ]].head(10).to_string(index=False)
    )

    # Statistical significance testing for top unweighted and top overall model vs LR
    top_models = sorted_models.head(3)["Model"].tolist()
    stat_records = []

    for tm in top_models:
        tm_folds = results_df[results_df["Model"] == tm]["AUROC"].to_numpy()
        tm_brier = results_df[results_df["Model"] == tm]["Brier_Score"].to_numpy()

        diff_auroc = tm_folds - np.array(lr_aurocs)
        t_stat, p_val = stats.ttest_rel(tm_folds, lr_aurocs)
        try:
            w_stat, w_pval = stats.wilcoxon(tm_folds, lr_aurocs)
        except Exception:
            w_stat, w_pval = np.nan, np.nan

        stat_records.append({
            "Model": tm,
            "ANN_AUROC_Mean": np.mean(tm_folds),
            "LR_AUROC_Mean": np.mean(lr_aurocs),
            "Diff_Mean": np.mean(diff_auroc),
            "Paired_t_stat": t_stat,
            "Paired_t_pval": p_val,
            "Wilcoxon_stat": w_stat,
            "Wilcoxon_pval": w_pval,
            "Statistically_Significant_p05": bool(p_val < 0.05),
        })

    stat_df = pd.DataFrame(stat_records)
    stat_path = RESULTS_DIR / "ann_phase2_statistical_significance.csv"
    stat_df.to_csv(stat_path, index=False)
    print("\nStatistical Significance vs Logistic Regression:")
    print(stat_df.to_string(index=False))

    return results_df, summary_df, stat_df


if __name__ == "__main__":
    run_phase2()
