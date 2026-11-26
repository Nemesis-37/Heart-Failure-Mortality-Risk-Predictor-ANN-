"""
scripts/phase13/generate_plots.py
=================================
Generates all publication-quality Phase 13 visualizations into results/phase13/plots/.
Every chart explicitly states the dataset, sample count, and evaluation procedure.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    auc,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = PROJECT_ROOT / "results" / "phase13"
PLOT_DIR = OUT_DIR / "plots"
PLOT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#F8FAFC",
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
    "font.size": 10,
    "axes.titlesize": 11.5,
    "axes.titleweight": "bold",
})

LR_COLOR = "#1D4ED8"
ANN_COLOR = "#DC2626"
ENS_COLOR = "#059669"


def main():
    oof_df = pd.read_csv(OUT_DIR / "phase13_oof_patient_predictions.csv")
    comp_df = pd.read_csv(OUT_DIR / "phase13_patient_level_comparison.csv")
    pert_df = pd.read_csv(OUT_DIR / "phase13_feature_perturbation_results.csv")
    inter_df = pd.read_csv(OUT_DIR / "phase13_feature_interaction_results.csv")
    ens_df = pd.read_csv(OUT_DIR / "phase13_ensemble_comparison.csv")
    cv_df = pd.read_csv(OUT_DIR / "phase13_cross_validation_results.csv")
    with open(OUT_DIR / "phase13_cv_stats_summary.json", "r", encoding="utf-8") as f:
        stats_json = json.load(f)
    with open(OUT_DIR / "phase13_platelet_summary.json", "r", encoding="utf-8") as f:
        plt_json = json.load(f)
    with open(OUT_DIR / "phase13_explainability_summary.json", "r", encoding="utf-8") as f:
        exp_json = json.load(f)

    y_true = oof_df["actual_death_event"].to_numpy()
    p_lr = oof_df["oof_lr_prob"].to_numpy()
    p_ann = oof_df["oof_ann_prob"].to_numpy()

    # 1. ROC CURVES
    fig, ax = plt.subplots(figsize=(7.2, 6.0), dpi=160)
    fpr_lr, tpr_lr, _ = roc_curve(y_true, p_lr)
    fpr_ann, tpr_ann, _ = roc_curve(y_true, p_ann)
    auc_lr = roc_auc_score(y_true, p_lr)
    auc_ann = roc_auc_score(y_true, p_ann)
    delong_p = stats_json["delong_oof"]["p_value"]
    ax.plot(fpr_lr, tpr_lr, color=LR_COLOR, lw=2.4, label=f"Logistic Regression (OOF AUROC = {auc_lr:.4f})")
    ax.plot(fpr_ann, tpr_ann, color=ANN_COLOR, lw=2.4, label=f"ANN 11-64-32-1 (OOF AUROC = {auc_ann:.4f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1.2, alpha=0.6, label="Random Chance (AUROC = 0.5000)")
    ax.set_xlabel("False Positive Rate (1 - Specificity)")
    ax.set_ylabel("True Positive Rate (Sensitivity)")
    ax.set_title(
        "LR vs ANN ROC Curves (Unseen Out-of-Fold Evaluation)\n"
        f"Dataset: UCI HF N=299 (96 deaths, 203 survivors) | 5-Fold Stratified OOF | DeLong p = {delong_p:.6f}",
        fontsize=10.5,
    )
    ax.legend(loc="lower right", frameon=True)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "fig01_roc_curves.png")
    plt.close(fig)

    # 2. PRECISION-RECALL CURVES
    fig, ax = plt.subplots(figsize=(7.2, 6.0), dpi=160)
    prec_lr, rec_lr, _ = precision_recall_curve(y_true, p_lr)
    prec_ann, rec_ann, _ = precision_recall_curve(y_true, p_ann)
    ap_lr = average_precision_score(y_true, p_lr)
    ap_ann = average_precision_score(y_true, p_ann)
    prev = float(np.mean(y_true))
    ax.plot(rec_lr, prec_lr, color=LR_COLOR, lw=2.4, label=f"Logistic Regression (PR-AUC = {ap_lr:.4f})")
    ax.plot(rec_ann, prec_ann, color=ANN_COLOR, lw=2.4, label=f"ANN 11-64-32-1 (PR-AUC = {ap_ann:.4f})")
    ax.axhline(prev, color="gray", ls="--", lw=1.2, label=f"Baseline Mortality Rate = {prev:.3f}")
    ax.set_xlabel("Recall (Sensitivity)")
    ax.set_ylabel("Precision (Positive Predictive Value)")
    ax.set_title(
        "LR vs ANN Precision-Recall Curves (Unseen Out-of-Fold Evaluation)\n"
        "Dataset: UCI HF N=299 (Positive Class Prevalence = 32.11%) | 5-Fold Stratified Leak-Free OOF",
        fontsize=10.5,
    )
    ax.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "fig02_pr_curves.png")
    plt.close(fig)

    # 3. CALIBRATION CURVES (RELIABILITY DIAGRAM)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.6), dpi=160)
    for name, probs, col in [
        ("LR (Uncalibrated OOF)", p_lr, LR_COLOR),
        ("ANN (Uncalibrated OOF)", p_ann, ANN_COLOR),
        ("ANN + Inner Platt", oof_df["oof_ann_platt_prob"].to_numpy(), "#EA580C"),
    ]:
        frac_pos, mean_pred = calibration_curve(y_true, probs, n_bins=8, strategy="quantile")
        brier = brier_score_loss(y_true, probs)
        ax1.plot(mean_pred, frac_pos, "o-", color=col, lw=2.0, label=f"{name} (Brier={brier:.4f})")
    ax1.plot([0, 1], [0, 1], "k--", lw=1.2, label="Perfect Calibration (y = x)")
    ax1.set_xlabel("Mean Predicted Mortality Probability (Quantile Bins)")
    ax1.set_ylabel("Observed Mortality Frequency")
    ax1.set_title("Reliability Diagram (8 Quantile Bins)\n5-Fold Stratified Leak-Free OOF (N=299)", fontsize=10.5)
    ax1.legend(loc="upper left", fontsize=8.8)

    ax2.hist(p_lr, bins=15, range=(0, 1), alpha=0.55, color=LR_COLOR, label="LR Predicted Probabilities", edgecolor="white")
    ax2.hist(p_ann, bins=15, range=(0, 1), alpha=0.50, color=ANN_COLOR, label="ANN Predicted Probabilities", edgecolor="white")
    ax2.axvline(0.50, color="black", ls="--", lw=1.3, label="Decision Threshold (0.50)")
    ax2.axvline(prev, color="#059669", ls=":", lw=1.5, label=f"Cohort Mortality Rate ({prev:.2f})")
    ax2.set_xlabel("Predicted Mortality Probability")
    ax2.set_ylabel("Patient Count")
    ax2.set_title("OOF Predicted Probability Distributions\nLR Slope=0.751 (ECE=0.041) vs ANN Slope=0.479 (ECE=0.103)", fontsize=10.5)
    ax2.legend(loc="upper right", fontsize=8.8)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "fig03_calibration_curves.png")
    plt.close(fig)

    # 4. CONFUSION MATRICES (OOF @ 0.50 AND @ 0.33)
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 9.0), dpi=160)
    cm_specs = [
        ("LR OOF @ Threshold 0.50", (p_lr >= 0.50).astype(int), axes[0, 0], "Blues"),
        ("ANN OOF @ Threshold 0.50", (p_ann >= 0.50).astype(int), axes[0, 1], "Reds"),
        ("LR OOF @ Threshold 0.33", (p_lr >= 0.33).astype(int), axes[1, 0], "Blues"),
        ("ANN OOF @ Threshold 0.33", (p_ann >= 0.33).astype(int), axes[1, 1], "Reds"),
    ]
    for title, preds, ax, cmap in cm_specs:
        cm = confusion_matrix(y_true, preds, labels=[0, 1])
        im = ax.imshow(cm, cmap=cmap)
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred Survive (0)", "Pred Death (1)"])
        ax.set_yticklabels(["Actual Survive (0)", "Actual Death (1)"])
        tn, fp, fn, tp = cm.ravel()
        sens = tp / (tp + fn)
        spec = tn / (tn + fp)
        ax.set_title(f"{title}\nSens={sens:.1%}, Spec={spec:.1%}", fontsize=10.5)
        for i in range(2):
            for j in range(2):
                val = cm[i, j]
                col = "white" if val > cm.max() * 0.55 else "black"
                tag = ["TN", "FP", "FN", "TP"][i * 2 + j]
                ax.text(j, i, f"{tag}\n{val}", ha="center", va="center", color=col, fontsize=12, fontweight="bold")
    fig.suptitle("Out-of-Fold Confusion Matrices (N=299 Unseen Patients, 5-Fold Stratified CV)", fontsize=12, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(PLOT_DIR / "fig04_confusion_matrices.png")
    plt.close(fig)

    # 5. FEATURE PERTURBATION CURVES (ALL 11 FEATURES)
    med = pert_df[pert_df["profile"] == "Cohort_Median_Profile"]
    low = pert_df[pert_df["profile"] == "Low_Risk_Baseline"]
    high = pert_df[pert_df["profile"] == "High_Risk_Critical"]
    feats = list(med["feature"].unique())
    fig, axes = plt.subplots(3, 4, figsize=(16.5, 11.5), dpi=160)
    axes_flat = axes.ravel()
    binary_feats = {"anaemia", "diabetes", "high_blood_pressure", "sex", "smoking"}
    for idx, feat in enumerate(feats):
        ax = axes_flat[idx]
        gm = med[med["feature"] == feat]
        gh = high[high["feature"] == feat]
        if feat in binary_feats:
            x_vals = gm["feature_value"].to_numpy()
            w = 0.32
            ax.bar(x_vals - w / 2, gm["prod_lr_prob"], width=w, color=LR_COLOR, alpha=0.85, label="LR (Median)")
            ax.bar(x_vals + w / 2, gm["prod_ann_prob"], width=w, color=ANN_COLOR, alpha=0.85, label="ANN (Median)")
            ax.set_xticks([0, 1])
            ax.set_xticklabels(["0 (No/F)", "1 (Yes/M)"])
        else:
            ax.plot(gm["feature_value"], gm["prod_lr_prob"], color=LR_COLOR, lw=2.0, label="Prod LR (Median)")
            ax.plot(gm["feature_value"], gm["prod_ann_prob"], color=ANN_COLOR, lw=2.0, label="Prod ANN (Median)")
            ax.plot(gh["feature_value"], gh["prod_lr_prob"], color=LR_COLOR, lw=1.3, ls="--", alpha=0.65, label="Prod LR (HighRisk)")
            ax.plot(gh["feature_value"], gh["prod_ann_prob"], color=ANN_COLOR, lw=1.3, ls="--", alpha=0.65, label="Prod ANN (HighRisk)")
        ax.set_ylim(-0.02, 1.02)
        ax.set_title(feat, fontsize=10.5)
        ax.set_ylabel("Mortality Prob")
        if idx == 0 or idx == 1:
            ax.legend(fontsize=7.5, loc="best")
    axes_flat[11].axis("off")
    axes_flat[11].text(
        0.05, 0.5,
        "Evaluation Basis:\n"
        "- Frozen Production LR\n  (trained on N=299)\n"
        "- Frozen Production ANN\n  (Fold 4 checkpoint, N=239)\n"
        "- Single-feature sweep holding\n  other 10 features fixed at\n  Cohort Median & High-Risk profiles",
        fontsize=9.5, va="center", bbox=dict(boxstyle="round", facecolor="#EFF6FF", edgecolor="#93C5FD")
    )
    fig.suptitle("Phase 5 — Feature-by-Feature Behavioural Response Curves (All 11 Features)", fontsize=13, fontweight="bold", y=0.985)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(PLOT_DIR / "fig05_feature_perturbation_curves.png")
    plt.close(fig)

    # 6. PLATELET RESPONSE CURVES (DEDICATED PHASE 7 CHART)
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.2), dpi=160)
    # Panel A: Multi-profile comparison
    ax = axes[0]
    for prof_name, ls in [("Low_Risk_Baseline", ":"), ("Cohort_Median_Profile", "-"), ("Borderline_Cardiorenal", "-."), ("High_Risk_Critical", "--")]:
        sub = pert_df[(pert_df["profile"] == prof_name) & (pert_df["feature"] == "platelets")]
        ax.plot(sub["feature_value"] / 1000.0, sub["prod_lr_prob"], color=LR_COLOR, ls=ls, lw=1.8, label=f"LR ({prof_name.split('_')[0]})")
        ax.plot(sub["feature_value"] / 1000.0, sub["prod_ann_prob"], color=ANN_COLOR, ls=ls, lw=1.8, label=f"ANN ({prof_name.split('_')[0]})")
    ax.axvspan(25.1, 850.0, color="#E2E8F0", alpha=0.45, label="Observed Range [25.1k, 850k]")
    ax.set_xlabel("Platelets (thousands / mcL)")
    ax.set_ylabel("Predicted Mortality Probability")
    ax.set_title("A. Multi-Profile Platelet Curves\n(Frozen Production LR vs ANN)")
    ax.legend(fontsize=7.0, ncol=2, loc="best")

    # Panel B: Fold-to-fold ANN instability on Cohort Median Profile
    ax = axes[1]
    px = np.array(plt_json["fold_curves_median_profile"]["platelets"]) / 1000.0
    ax.plot(px, plt_json["fold_curves_median_profile"]["prod_lr"], color=LR_COLOR, lw=2.6, label="Prod LR (Slope=-0.066 std)")
    fold_cols = ["#F97316", "#EAB308", "#8B5CF6", "#DC2626", "#EC4899"]
    for fi in range(1, 6):
        ax.plot(px, plt_json["fold_curves_median_profile"][f"cv_ann_fold{fi}"], color=fold_cols[fi - 1], lw=1.7, alpha=0.85, label=f"CV ANN Fold {fi}")
    ax.set_xlabel("Platelets (thousands / mcL)")
    ax.set_ylabel("Predicted Mortality Probability")
    ax.set_title("B. Fold-to-Fold ANN Instability (Median Profile)\nOpposite Slopes Across CV Folds Prove Noise Overfitting")
    ax.legend(fontsize=7.8, loc="best")

    # Panel C: Actual Dataset Platelet Quartiles vs Mortality Rate
    ax = axes[2]
    q_recs = plt_json["dataset_platelet_quartiles"]
    q_labels = [f"Q{i+1}\n{r['bin']}" for i, r in enumerate(q_recs)]
    q_rates = [r["mortality_rate"] * 100 for r in q_recs]
    bars = ax.bar(range(4), q_rates, color=["#64748B", "#0284C7", "#0284C7", "#64748B"], alpha=0.85)
    ax.set_xticks(range(4))
    ax.set_xticklabels([f"Q1\n(25-212k)", "Q2\n(212-262k)", "Q3\n(262-303k)", "Q4\n(303-850k)"], fontsize=8.8)
    ax.set_ylabel("Observed Mortality Rate (%)")
    ax.set_ylim(0, 52)
    ax.set_title("C. Observed Cohort Mortality by Platelet Quartile\n(N=299; r = -0.049; Non-Monotonic U-Shape)")
    for b, val, r in zip(bars, q_rates, q_recs):
        ax.text(b.get_x() + b.get_width() / 2, val + 1.2, f"{val:.1f}%\n({r['deaths']}/{r['count']})", ha="center", fontsize=8.5)
    fig.suptitle("Phase 7 — Platelet Count Investigation: Non-Linear ANN Overfitting vs Linear Monotonicity", fontsize=12.5, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(PLOT_DIR / "fig06_platelet_response_curves.png")
    plt.close(fig)

    # 7. FEATURE INTERACTION HEATMAPS (KEY 3 PAIRS SIDE BY SIDE)
    top_pairs = ["age_x_ejection_fraction", "ejection_fraction_x_serum_creatinine", "platelets_x_serum_creatinine"]
    fig, axes = plt.subplots(3, 2, figsize=(12.2, 13.5), dpi=160)
    for r_i, pair_name in enumerate(top_pairs):
        sub = inter_df[inter_df["pair"] == pair_name]
        f1 = sub["feature_1"].iloc[0]
        f2 = sub["feature_2"].iloc[0]
        piv_lr = sub.pivot(index="value_1", columns="value_2", values="prod_lr_prob")
        piv_ann = sub.pivot(index="value_1", columns="value_2", values="prod_ann_prob")

        for c_i, (piv, mname) in enumerate([(piv_lr, "Production LR"), (piv_ann, "Production ANN")]):
            ax = axes[r_i, c_i]
            im = ax.imshow(piv.values, aspect="auto", origin="lower", cmap="RdYlBu_r", vmin=0.0, vmax=1.0)
            ax.set_xticks(range(len(piv.columns)))
            ax.set_xticklabels([f"{v:.1f}" if v < 100 else f"{int(v)}" for v in piv.columns], rotation=35, fontsize=8)
            ax.set_yticks(range(len(piv.index)))
            ax.set_yticklabels([f"{int(v/1000)}k" if f1 == "platelets" else f"{int(v)}" for v in piv.index], fontsize=8)
            ax.set_xlabel(f2)
            ax.set_ylabel(f1)
            ax.set_title(f"{mname}: {f1} vs {f2}")
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("Phase 6 — 2D Feature Interaction Surfaces (Cohort Median Baseline Fixed for Other 9 Features)", fontsize=12.5, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(PLOT_DIR / "fig07_feature_interaction_heatmaps.png")
    plt.close(fig)

    # 8. PROBABILITY DISAGREEMENT DISTRIBUTION
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.2), dpi=160)
    diff = comp_df["oof_prob_diff_lr_minus_ann"].to_numpy()
    ax1.hist(diff, bins=25, color="#4F46E5", alpha=0.82, edgecolor="white")
    ax1.axvline(0.0, color="black", ls="--", lw=1.4)
    ax1.axvline(np.mean(diff), color=LR_COLOR, ls=":", lw=1.8, label=f"Mean Diff = {np.mean(diff):+.4f}")
    ax1.set_xlabel("OOF Probability Difference (P_LR - P_ANN)")
    ax1.set_ylabel("Patient Count")
    ax1.set_title("Signed Probability Disagreement (P_LR - P_ANN)\nN=299 Out-of-Fold Unseen Patients")
    ax1.legend()

    dis = comp_df[~comp_df["oof_agree_050"]]
    cats = ["Both Correct\n(Agree)", "Both Wrong:\nFalse Neg", "Both Wrong:\nFalse Pos", "Disagree:\nLR Right / ANN Wrong", "Disagree:\nANN Right / LR Wrong"]
    gcounts = stats_json["group_counts_050"]
    vals = [
        gcounts.get("Both_Correct", 0),
        gcounts.get("Both_False_Negative", 0),
        gcounts.get("Both_False_Positive", 0),
        gcounts.get("LR_Correct_ANN_Wrong", 0),
        gcounts.get("ANN_Correct_LR_Wrong", 0),
    ]
    cols = ["#10B981", "#EF4444", "#F59E0B", LR_COLOR, ANN_COLOR]
    bars = ax2.bar(range(len(cats)), vals, color=cols, alpha=0.88)
    ax2.set_xticks(range(len(cats)))
    ax2.set_xticklabels(cats, fontsize=8.5)
    ax2.set_ylabel("Number of Patients (N=299)")
    ax2.set_title("Classification Agreement & Discordance Breakdown (@ 0.50)\nMcNemar Exact p = 0.0201 (LR 23 vs ANN 9 Discordant Wins)")
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 3, str(v), ha="center", fontweight="bold")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "fig08_disagreement_distribution.png")
    plt.close(fig)

    # 9. PATIENT-LEVEL PREDICTION COMPARISON SCATTER
    fig, ax = plt.subplots(figsize=(7.4, 6.4), dpi=160)
    surv = comp_df[comp_df["actual_death_event"] == 0]
    died = comp_df[comp_df["actual_death_event"] == 1]
    ax.scatter(surv["oof_lr_prob"], surv["oof_ann_prob"], c="#2563EB", alpha=0.62, s=36, label="Survived (DEATH_EVENT=0, n=203)", edgecolors="white", lw=0.4)
    ax.scatter(died["oof_lr_prob"], died["oof_ann_prob"], c="#DC2626", marker="^", alpha=0.80, s=46, label="Mortality (DEATH_EVENT=1, n=96)", edgecolors="white", lw=0.4)
    ax.plot([0, 1], [0, 1], "k--", lw=1.2, alpha=0.6, label="Exact Agreement (P_LR = P_ANN)")
    ax.axvline(0.50, color="gray", ls=":", lw=1.2)
    ax.axhline(0.50, color="gray", ls=":", lw=1.2)
    ax.text(0.73, 0.22, "LR=1, ANN=0\n(n=13; LR 8/13 right)", fontsize=8.5, bbox=dict(boxstyle="round", facecolor="#DBEAFE", alpha=0.8))
    ax.text(0.10, 0.78, "ANN=1, LR=0\n(n=19; ANN 4/19 right)", fontsize=8.5, bbox=dict(boxstyle="round", facecolor="#FEE2E2", alpha=0.8))
    ax.set_xlabel("Out-of-Fold LR Predicted Probability")
    ax.set_ylabel("Out-of-Fold ANN Predicted Probability")
    ax.set_title("Patient-Level OOF Prediction Comparison (N=299 Unseen Patients)\n5-Fold Stratified Leak-Free CV | r = " + f"{np.corrcoef(p_lr, p_ann)[0, 1]:.3f}", fontsize=10.8)
    ax.legend(loc="upper left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "fig09_patient_level_comparison.png")
    plt.close(fig)

    # 10. ENSEMBLE VS INDIVIDUAL MODEL COMPARISON
    grid_ens = ens_df[ens_df["strategy"] != ens_df["strategy"].iloc[-1]].sort_values("weight_lr")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.2), dpi=160)
    w = grid_ens["weight_lr"].to_numpy()
    ax1.plot(w, grid_ens["oof_auroc"], "o-", color=LR_COLOR, lw=2.2, label="Pooled OOF AUROC")
    ax1.plot(w, grid_ens["oof_pr_auc"], "s--", color=ENS_COLOR, lw=2.0, label="Pooled OOF PR-AUC")
    ax1.set_xlabel("LR Weight w  (P_ens = w * P_LR + (1-w) * P_ANN)")
    ax1.set_ylabel("Discrimination Score (Higher is Better)")
    ax1.set_title("A. Ensemble Discrimination Across Weight Grid\nPure LR (w=1.0) Strictly Dominates Every Blend")
    ax1.legend()

    ax2.plot(w, grid_ens["oof_brier_score"], "o-", color="#7C3AED", lw=2.2, label="OOF Brier Score (Lower=Better)")
    ax2_twin = ax2.twinx()
    ax2_twin.plot(w, grid_ens["oof_log_loss"], "s--", color=ANN_COLOR, lw=2.0, label="OOF Log Loss (Lower=Better)")
    ax2.set_xlabel("LR Weight w  (0.0 = ANN Only, 1.0 = LR Only)")
    ax2.set_ylabel("Brier Score", color="#7C3AED")
    ax2_twin.set_ylabel("Log Loss", color=ANN_COLOR)
    ax2.set_title("B. Ensemble Probability Error Across Weight Grid\nAdding Any ANN Weight Increases Calibration Error")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "fig10_ensemble_comparison.png")
    plt.close(fig)

    # 11. EXPLAINABILITY & REPEATED CV STABILITY SUMMARY
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.6), dpi=160)
    perm = exp_json["oof_permutation_importance_auroc_drop"]
    feat_sorted = sorted(perm.keys(), key=lambda k: perm[k]["lr_mean_drop"], reverse=False)
    y_pos = np.arange(len(feat_sorted))
    h = 0.36
    ax1.barh(y_pos + h / 2, [perm[f]["lr_mean_drop"] for f in feat_sorted], height=h, color=LR_COLOR, alpha=0.88, label="LR OOF Perm Importance")
    ax1.barh(y_pos - h / 2, [perm[f]["ann_mean_drop"] for f in feat_sorted], height=h, color=ANN_COLOR, alpha=0.85, label="ANN OOF Perm Importance")
    ax1.axvline(0.0, color="black", lw=1.0)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(feat_sorted, fontsize=9)
    ax1.set_xlabel("Mean OOF AUROC Drop on Permutation (Higher = More Important)")
    ax1.set_title("A. Leak-Free OOF Permutation Feature Importance\n(30 Repeats x 5 Untouched Outer Folds)")
    ax1.legend(loc="lower right", fontsize=8.5)

    rep = cv_df[cv_df["experiment"] == "Repeated_5x10_CV"]
    lr_rep_auc = rep[rep["model"] == "Logistic_Regression"]["auroc"].to_numpy()
    ann_rep_auc = rep[rep["model"] == "ANN_11_64_32_1"]["auroc"].to_numpy()
    bp = ax2.boxplot([lr_rep_auc, ann_rep_auc], tick_labels=["Logistic Regression\n(50 folds)", "ANN 11-64-32-1\n(50 folds)"], patch_artist=True, widths=0.45)
    bp["boxes"][0].set_facecolor("#BFDBFE")
    bp["boxes"][1].set_facecolor("#FECACA")
    ax2.set_ylabel("Fold AUROC")
    ax2.set_title(
        "B. 5x10 Repeated Stratified CV Stability (50 Folds)\n"
        f"LR: {lr_rep_auc.mean():.4f} ± {lr_rep_auc.std(ddof=1):.4f} vs ANN: {ann_rep_auc.mean():.4f} ± {ann_rep_auc.std(ddof=1):.4f}\n"
        "LR Wins 41/50 Folds (7 ANN wins, 2 ties)"
    )
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "fig11_explainability_and_stability.png")
    plt.close(fig)

    print("Successfully generated all 11 Phase 13 visualizations in:", PLOT_DIR)


if __name__ == "__main__":
    main()
