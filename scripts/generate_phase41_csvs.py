"""
scripts/generate_phase41_csvs.py
Generates the three required CSV audit artifacts for Phase 4.1:
1. results/ann_phase41_experiment_inventory.csv
2. results/ann_phase41_fold_comparison.csv
3. results/ann_phase41_threshold_audit.csv
"""

import pandas as pd
import numpy as np

# ==============================================================================
# 1. GENERATE EXPERIMENT INVENTORY
# ==============================================================================
inventory_data = [
    {
        "Phase": "Phase 0 (Legacy)",
        "Experiment_ID": "Legacy_Logistic_CV",
        "Model_Name": "Logistic Regression (Legacy)",
        "Architecture": "Linear (11->1)",
        "Trainable_Params": 12,
        "Dataset": "heart_failure_clinical_records_dataset.csv",
        "Sample_Size": 299,
        "Feature_Count": 11,
        "Preprocessing": "StandardScaler (inside pipeline)",
        "CV_Method": "StratifiedKFold",
        "Folds": 5,
        "Random_Seed": 42,
        "Hyperparameters": "max_iter=2000, C=1.0, L2 penalty, fit on 80% train-inner (191 samples)",
        "Model_Checkpoint": "None (fitted during CV)",
        "Threshold_Method": "Default 0.50 (Fixed)",
        "Genuine_OOF_Predictions": "Yes",
        "Outer_Test_Leakage": "No",
        "Identical_Outer_Folds": "Yes (Same outer test folds, but inner training discarded 20%)",
        "AUROC_Mean": 0.744519,
        "AUROC_Std": 0.065516,
        "Brier_Mean": 0.177700, # Approximate from calibration
        "Audit_Notes": "Flawed baseline: model fit only on X_train_inner (191 samples) discarding 20% validation split without refitting.",
    },
    {
        "Phase": "Phase 0 (Legacy)",
        "Experiment_ID": "Legacy_ANN_32_16_CV",
        "Model_Name": "ANN 32-16 (Legacy)",
        "Architecture": "11->32->16->1",
        "Trainable_Params": 929,
        "Dataset": "heart_failure_clinical_records_dataset.csv",
        "Sample_Size": 299,
        "Feature_Count": 11,
        "Preprocessing": "StandardScaler (fitted per fold)",
        "CV_Method": "StratifiedKFold",
        "Folds": 10,
        "Random_Seed": 42,
        "Hyperparameters": "lr=0.001, Adam, BCE, Sigmoid output, batch_size=32",
        "Model_Checkpoint": "models/ann_model.pth (Historical)",
        "Threshold_Method": "Default 0.50 (Fixed)",
        "Genuine_OOF_Predictions": "Yes",
        "Outer_Test_Leakage": "No",
        "Identical_Outer_Folds": "No (10-fold CV instead of 5-fold CV)",
        "AUROC_Mean": 0.756756,
        "AUROC_Std": 0.082100,
        "Brier_Mean": 0.192000,
        "Audit_Notes": "Original benchmark used 10 folds; had Sigmoid inside BCE causing numerical instability; discarded 20% validation data.",
    },
    {
        "Phase": "Phase 1",
        "Experiment_ID": "P1_LR_FullTrain_Refit",
        "Model_Name": "Logistic Regression (Phase 1 Baseline)",
        "Architecture": "Linear (11->1)",
        "Trainable_Params": 12,
        "Dataset": "heart_failure_clinical_records_dataset.csv",
        "Sample_Size": 299,
        "Feature_Count": 11,
        "Preprocessing": "StandardScaler (fitted strictly on outer train fold)",
        "CV_Method": "StratifiedKFold",
        "Folds": 5,
        "Random_Seed": 42,
        "Hyperparameters": "max_iter=2000, C=1.0, L2 penalty, fit on 100% outer train (239 samples)",
        "Model_Checkpoint": "models/logistic_model.joblib",
        "Threshold_Method": "Default 0.50 (Fixed)",
        "Genuine_OOF_Predictions": "Yes",
        "Outer_Test_Leakage": "No",
        "Identical_Outer_Folds": "Yes (Reference 5-fold splits)",
        "AUROC_Mean": 0.771713,
        "AUROC_Std": 0.055057,
        "Brier_Mean": 0.177731,
        "Audit_Notes": "Corrected linear baseline fitted on full outer training fold (239 samples). Standard benchmark across all phases.",
    },
    {
        "Phase": "Phase 1",
        "Experiment_ID": "P1_ANN_32_16_StepAdj_Unweighted",
        "Model_Name": "ANN 32-16 Step-Adjusted Unweighted",
        "Architecture": "11->32->16->1",
        "Trainable_Params": 929,
        "Dataset": "heart_failure_clinical_records_dataset.csv",
        "Sample_Size": 299,
        "Feature_Count": 11,
        "Preprocessing": "StandardScaler (fitted strictly on outer train fold)",
        "CV_Method": "StratifiedKFold",
        "Folds": 5,
        "Random_Seed": 42,
        "Hyperparameters": "BCEWithLogitsLoss, Adam lr=0.001, early stopping patience=15, step-adjusted refit",
        "Model_Checkpoint": "None (in-memory CV)",
        "Threshold_Method": "Default 0.50 (Fixed)",
        "Genuine_OOF_Predictions": "Yes",
        "Outer_Test_Leakage": "No",
        "Identical_Outer_Folds": "Yes (Reference 5-fold splits)",
        "AUROC_Mean": 0.757974,
        "AUROC_Std": 0.066581,
        "Brier_Mean": 0.183772,
        "Audit_Notes": "Corrected BCEWithLogitsLoss with step-adjusted outer refit. Showed +0.22% improvement over legacy unweighted.",
    },
    {
        "Phase": "Phase 1",
        "Experiment_ID": "P1_ANN_32_16_StepAdj_Weighted",
        "Model_Name": "ANN 32-16 Step-Adjusted Weighted",
        "Architecture": "11->32->16->1",
        "Trainable_Params": 929,
        "Dataset": "heart_failure_clinical_records_dataset.csv",
        "Sample_Size": 299,
        "Feature_Count": 11,
        "Preprocessing": "StandardScaler (fitted strictly on outer train fold)",
        "CV_Method": "StratifiedKFold",
        "Folds": 5,
        "Random_Seed": 42,
        "Hyperparameters": "BCEWithLogitsLoss with pos_weight=2.11, Adam lr=0.001, patience=15",
        "Model_Checkpoint": "None (in-memory CV)",
        "Threshold_Method": "Default 0.50 (Fixed)",
        "Genuine_OOF_Predictions": "Yes",
        "Outer_Test_Leakage": "No",
        "Identical_Outer_Folds": "Yes (Reference 5-fold splits)",
        "AUROC_Mean": 0.768023,
        "AUROC_Std": 0.057386,
        "Brier_Mean": 0.201060,
        "Audit_Notes": "High AUROC and high sensitivity (72%), but poor calibration (Brier 0.2011) and severe probability inflation (mean prob 0.4578).",
    },
    {
        "Phase": "Phase 2",
        "Experiment_ID": "P2_Arch_B_16_dp0.2_wd0.01_bs32",
        "Model_Name": "Arch B (11->16->1)",
        "Architecture": "11->16->1",
        "Trainable_Params": 209,
        "Dataset": "heart_failure_clinical_records_dataset.csv",
        "Sample_Size": 299,
        "Feature_Count": 11,
        "Preprocessing": "StandardScaler (fitted strictly on outer train fold)",
        "CV_Method": "StratifiedKFold",
        "Folds": 5,
        "Random_Seed": 42,
        "Hyperparameters": "Dropout=0.2, Weight Decay=0.01, Batch Size=32, lr=0.001, inner split seed=42",
        "Model_Checkpoint": "None (in-memory CV)",
        "Threshold_Method": "Default 0.50 (Fixed)",
        "Genuine_OOF_Predictions": "Yes",
        "Outer_Test_Leakage": "No",
        "Identical_Outer_Folds": "Yes (Reference 5-fold splits)",
        "AUROC_Mean": 0.761297,
        "AUROC_Std": 0.057456,
        "Brier_Mean": 0.183504,
        "Audit_Notes": "Phase 2 winning compact architecture. Evaluated with fixed inner split seed (random_state=42).",
    },
    {
        "Phase": "Phase 2",
        "Experiment_ID": "P2_Arch_C_32_16_dp0.0_wd0.001_bs64",
        "Model_Name": "Arch C (11->32->16->1)",
        "Architecture": "11->32->16->1",
        "Trainable_Params": 929,
        "Dataset": "heart_failure_clinical_records_dataset.csv",
        "Sample_Size": 299,
        "Feature_Count": 11,
        "Preprocessing": "StandardScaler (fitted strictly on outer train fold)",
        "CV_Method": "StratifiedKFold",
        "Folds": 5,
        "Random_Seed": 42,
        "Hyperparameters": "Dropout=0.0, Weight Decay=0.001, Batch Size=64, lr=0.001, inner split seed=42",
        "Model_Checkpoint": "None (in-memory CV)",
        "Threshold_Method": "Default 0.50 (Fixed)",
        "Genuine_OOF_Predictions": "Yes",
        "Outer_Test_Leakage": "No",
        "Identical_Outer_Folds": "Yes (Reference 5-fold splits)",
        "AUROC_Mean": 0.767525,
        "AUROC_Std": 0.090475,
        "Brier_Mean": 0.186245,
        "Audit_Notes": "Phase 2 higher-capacity architecture; high AUROC but higher fold-to-fold variance (std 0.0905).",
    },
    {
        "Phase": "Phase 3",
        "Experiment_ID": "P3_LR_Threshold_Calibration",
        "Model_Name": "Logistic Regression (Threshold & Calibration)",
        "Architecture": "Linear (11->1)",
        "Trainable_Params": 12,
        "Dataset": "heart_failure_clinical_records_dataset.csv",
        "Sample_Size": 299,
        "Feature_Count": 11,
        "Preprocessing": "StandardScaler (fitted strictly on outer train fold)",
        "CV_Method": "StratifiedKFold",
        "Folds": 5,
        "Random_Seed": 42,
        "Hyperparameters": "max_iter=2000, C=1.0, inner split seed=42+fold",
        "Model_Checkpoint": "None (in-memory CV)",
        "Threshold_Method": "Inner Youden J (mean thr=0.334) & Inner F1-Max (mean thr=0.340) & Platt 0.50",
        "Genuine_OOF_Predictions": "Yes (Threshold selected strictly on inner validation split)",
        "Outer_Test_Leakage": "No (Zero outer test fold leakage in threshold selection or Platt scaling)",
        "Identical_Outer_Folds": "Yes (Reference 5-fold splits)",
        "AUROC_Mean": 0.771713,
        "AUROC_Std": 0.055057,
        "Brier_Mean": 0.177731,
        "Audit_Notes": "Threshold optimization on nested inner validation sets. Sensitivity at inner Youden 0.33 was 63.79% ± 19.74%.",
    },
    {
        "Phase": "Phase 3",
        "Experiment_ID": "P3_Arch_B_Threshold_Calibration",
        "Model_Name": "Arch B (Threshold & Calibration)",
        "Architecture": "11->16->1",
        "Trainable_Params": 209,
        "Dataset": "heart_failure_clinical_records_dataset.csv",
        "Sample_Size": 299,
        "Feature_Count": 11,
        "Preprocessing": "StandardScaler (fitted strictly on outer train fold)",
        "CV_Method": "StratifiedKFold",
        "Folds": 5,
        "Random_Seed": 42,
        "Hyperparameters": "dp=0.2, wd=0.01, bs=32, inner split seed=42+fold",
        "Model_Checkpoint": "None (in-memory CV)",
        "Threshold_Method": "Inner Youden J (mean thr=0.334) & Inner F1-Max (mean thr=0.350) & Platt 0.50",
        "Genuine_OOF_Predictions": "Yes (Threshold selected strictly on inner validation split)",
        "Outer_Test_Leakage": "No (Zero outer test fold leakage in threshold selection or Platt scaling)",
        "Identical_Outer_Folds": "Yes (Reference 5-fold splits)",
        "AUROC_Mean": 0.761093,
        "AUROC_Std": 0.062052,
        "Brier_Mean": 0.180407,
        "Audit_Notes": "AUROC 76.1093% (76.11%). Under inner Youden threshold (0.33), sensitivity was 71.95% ± 3.88% with F1=0.6110.",
    },
    {
        "Phase": "Phase 3",
        "Experiment_ID": "P3_Arch_C_Threshold_Calibration",
        "Model_Name": "Arch C (Threshold & Calibration)",
        "Architecture": "11->32->16->1",
        "Trainable_Params": 929,
        "Dataset": "heart_failure_clinical_records_dataset.csv",
        "Sample_Size": 299,
        "Feature_Count": 11,
        "Preprocessing": "StandardScaler (fitted strictly on outer train fold)",
        "CV_Method": "StratifiedKFold",
        "Folds": 5,
        "Random_Seed": 42,
        "Hyperparameters": "dp=0.0, wd=0.001, bs=64, inner split seed=42+fold",
        "Model_Checkpoint": "None (in-memory CV)",
        "Threshold_Method": "Inner Youden J (mean thr=0.302) & Inner F1-Max (mean thr=0.320) & Platt 0.50",
        "Genuine_OOF_Predictions": "Yes (Threshold selected strictly on inner validation split)",
        "Outer_Test_Leakage": "No (Zero outer test fold leakage in threshold selection or Platt scaling)",
        "Identical_Outer_Folds": "Yes (Reference 5-fold splits)",
        "AUROC_Mean": 0.748718,
        "AUROC_Std": 0.069942,
        "Brier_Mean": 0.185912,
        "Audit_Notes": "AUROC 74.8718% (74.87%). Under inner Youden threshold (0.30), sensitivity was 73.95% ± 6.47% with F1=0.6085.",
    },
    {
        "Phase": "Phase 4",
        "Experiment_ID": "P4_External_Feasibility_Audit",
        "Model_Name": "Cross-Cohort Feasibility & Generalization Audit",
        "Architecture": "Comparative (LR vs Arch B vs Arch C)",
        "Trainable_Params": "12 / 209 / 929",
        "Dataset": "Audited: Faisalabad mirrors, fedesoriano CAD, Zigong EHR, Vanderbilt, MIMIC-IV, BioLINCC",
        "Sample_Size": "N=299 / 918 / 2008 / 3927 / >40k / 6800",
        "Feature_Count": "Mapped across 11 features",
        "Preprocessing": "Unit conversion formulas established (Cr umol/L -> mg/dL, platelets, etc.)",
        "CV_Method": "N/A (External dataset feasibility audit; no external model execution performed)",
        "Folds": "N/A",
        "Random_Seed": "N/A",
        "Hyperparameters": "N/A",
        "Model_Checkpoint": "Frozen baseline models",
        "Threshold_Method": "Audit of operating thresholds (0.50 vs 0.33)",
        "Genuine_OOF_Predictions": "N/A (No external inference executed)",
        "Outer_Test_Leakage": "N/A",
        "Identical_Outer_Folds": "N/A",
        "AUROC_Mean": None,
        "AUROC_Std": None,
        "Brier_Mean": None,
        "Audit_Notes": "Feasibility audit only. Confirmed: external validation has NOT yet been performed due to DUA credential gating.",
    },
]

df_inv = pd.DataFrame(inventory_data)
df_inv.to_csv("results/ann_phase41_experiment_inventory.csv", index=False)
print("✓ Created results/ann_phase41_experiment_inventory.csv")

# ==============================================================================
# 2. GENERATE FOLD COMPARISON CSV
# ==============================================================================
# Extract from existing fold results
df_p3_folds = pd.read_csv("results/ann_phase3_fold_results.csv")
df_p1_folds = pd.read_csv("results/ann_phase1_experiments_fold_results.csv")
df_legacy_lr = pd.read_csv("results/logistic_regression_5fold_results.csv")

fold_comparison_rows = []

# Legacy LR
for _, r in df_legacy_lr.iterrows():
    fold_comparison_rows.append({
        "Experiment_Phase": "Phase 0 (Legacy)",
        "Model_ID": "Legacy_Logistic_Regression",
        "Model_Name": "Logistic Regression (Legacy 80% Train)",
        "Operating_Mode": "Threshold 0.50 (Legacy)",
        "Fold": int(r["Fold"]),
        "Threshold_Used": 0.50,
        "AUROC": r["AUROC"],
        "Brier_Score": np.nan,
        "Log_Loss": np.nan,
        "Accuracy": r["Accuracy"],
        "Sensitivity": r["Sensitivity"],
        "Specificity": r["Specificity"],
        "Precision": r["Precision"],
        "F1_Score": r["F1_Score"],
        "TP": int(r["TP"]),
        "FP": int(r["FP"]),
        "TN": int(r["TN"]),
        "FN": int(r["FN"]),
        "Audit_Notes": "Trained only on 80% of outer train (191 samples); discarded 20% validation split.",
    })

# Phase 1 LR Full Train
p1_lr = df_p1_folds[df_p1_folds["Model"] == "Logistic_Regression"]
for _, r in p1_lr.iterrows():
    fold_comparison_rows.append({
        "Experiment_Phase": "Phase 1",
        "Model_ID": "P1_Logistic_Regression_Refit",
        "Model_Name": "Logistic Regression (Phase 1 Baseline)",
        "Operating_Mode": "Threshold 0.50 (Uncalibrated)",
        "Fold": int(r["Fold"]),
        "Threshold_Used": 0.50,
        "AUROC": r["AUROC"],
        "Brier_Score": r["Brier_Score"],
        "Log_Loss": np.nan,
        "Accuracy": r["Accuracy"],
        "Sensitivity": r["Sensitivity"],
        "Specificity": r["Specificity"],
        "Precision": r["Precision"],
        "F1_Score": r["F1_Score"],
        "TP": np.nan,
        "FP": np.nan,
        "TN": np.nan,
        "FN": np.nan,
        "Audit_Notes": "Trained on 100% of outer train (239 samples). True standard baseline.",
    })

# Phase 3 Models (LR, Arch B, Arch C)
for _, r in df_p3_folds.iterrows():
    m_id = r["Model_ID"]
    m_name = r["Model_Name"]
    fold = int(r["Fold"])

    # 1. Fixed Threshold 0.50
    fold_comparison_rows.append({
        "Experiment_Phase": "Phase 3",
        "Model_ID": m_id,
        "Model_Name": m_name,
        "Operating_Mode": "Threshold 0.50 (Uncalibrated)",
        "Fold": fold,
        "Threshold_Used": 0.50,
        "AUROC": r["AUROC"],
        "Brier_Score": r["Uncal_Brier"],
        "Log_Loss": r["Uncal_LogLoss"],
        "Accuracy": r["Uncal_Acc_050"],
        "Sensitivity": r["Uncal_Sens_050"],
        "Specificity": r["Uncal_Spec_050"],
        "Precision": r["Uncal_Prec_050"],
        "F1_Score": r["Uncal_F1_050"],
        "TP": int(r["Uncal_TP_050"]),
        "FP": int(r["Uncal_FP_050"]),
        "TN": int(r["Uncal_TN_050"]),
        "FN": int(r["Uncal_FN_050"]),
        "Audit_Notes": "Standard fixed threshold 0.50 on outer test fold.",
    })

    # 2. Inner Youden J
    fold_comparison_rows.append({
        "Experiment_Phase": "Phase 3",
        "Model_ID": m_id,
        "Model_Name": m_name,
        "Operating_Mode": "Inner-Selected Youden Threshold",
        "Fold": fold,
        "Threshold_Used": r["Inner_Selected_Youden_Thresh"],
        "AUROC": r["AUROC"],
        "Brier_Score": r["Uncal_Brier"],
        "Log_Loss": r["Uncal_LogLoss"],
        "Accuracy": r["Youden_Acc"],
        "Sensitivity": r["Youden_Sens"],
        "Specificity": r["Youden_Spec"],
        "Precision": r["Youden_Prec"],
        "F1_Score": r["Youden_F1"],
        "TP": int(r["Youden_TP"]),
        "FP": int(r["Youden_FP"]),
        "TN": int(r["Youden_TN"]),
        "FN": int(r["Youden_FN"]),
        "Audit_Notes": "Threshold selected on inner validation fold without outer test leakage.",
    })

    # 3. Platt Scaled 0.50
    fold_comparison_rows.append({
        "Experiment_Phase": "Phase 3",
        "Model_ID": m_id,
        "Model_Name": m_name,
        "Operating_Mode": "Platt Scaled (Threshold 0.50)",
        "Fold": fold,
        "Threshold_Used": 0.50,
        "AUROC": r["AUROC"],
        "Brier_Score": r["Platt_Brier"],
        "Log_Loss": r["Platt_LogLoss"],
        "Accuracy": r["Platt_Acc_050"],
        "Sensitivity": r["Platt_Sens_050"],
        "Specificity": r["Platt_Spec_050"],
        "Precision": np.nan,
        "F1_Score": r["Platt_F1_050"],
        "TP": np.nan,
        "FP": np.nan,
        "TN": np.nan,
        "FN": np.nan,
        "Audit_Notes": "Platt scaling fit strictly on inner validation logits; applied to outer test logits.",
    })

df_fold_comp = pd.DataFrame(fold_comparison_rows)
df_fold_comp.to_csv("results/ann_phase41_fold_comparison.csv", index=False)
print("✓ Created results/ann_phase41_fold_comparison.csv")

# ==============================================================================
# 3. GENERATE THRESHOLD AUDIT CSV
# ==============================================================================
df_p3_thresh = pd.read_csv("results/ann_phase3_threshold_results.csv")
df_p3_model = pd.read_csv("results/ann_phase3_model_comparison.csv")

threshold_audit_rows = []

# Summary of operating modes from model comparison
for _, r in df_p3_model.iterrows():
    # Determine proper scientific classification
    mode = r["Operating_Mode"]
    thr_desc = str(r["Decision_Threshold"])

    if "0.50" in mode and "Uncalibrated" in mode:
        classification = "Arbitrary uncalibrated default threshold (0.50)"
        clinical_validity = "Poor (Under-diagnoses high-risk mortality; 48-51% false negative rate)"
    elif "Youden" in mode:
        classification = "Data-driven empirical threshold maximizing Sensitivity + Specificity - 1"
        clinical_validity = "Heuristic decision threshold; NOT 'clinically calibrated' or 'clinically validated'"
    elif "F1" in mode:
        classification = "Data-driven empirical threshold maximizing Harmonic Mean of Precision and Recall"
        clinical_validity = "Heuristic decision threshold prioritizing positive class detection"
    elif "Platt" in mode:
        classification = "Post-hoc parametric logistic recalibration (Platt scaling)"
        clinical_validity = "Calibration technique; alters Brier score/log loss but preserves AUROC rank ordering"
    else:
        classification = "Experimental threshold"
        clinical_validity = "Internal evaluation"

    threshold_audit_rows.append({
        "Model": r["Model"],
        "Operating_Mode": r["Operating_Mode"],
        "Decision_Threshold": r["Decision_Threshold"],
        "AUROC": r["AUROC"],
        "Brier_Score": r["Brier_Score"],
        "Log_Loss": r["Log_Loss"],
        "Accuracy": r["Accuracy"],
        "Sensitivity": r["Sensitivity"],
        "Specificity": r["Specificity"],
        "Precision": r["Precision"],
        "F1_Score": r["F1_Score"],
        "Mean_FP": r["Mean_FP"],
        "Mean_FN": r["Mean_FN"],
        "Methodological_Classification": classification,
        "Scientific_and_Clinical_Validity_Audit": clinical_validity,
    })

df_thresh_audit = pd.DataFrame(threshold_audit_rows)
df_thresh_audit.to_csv("results/ann_phase41_threshold_audit.csv", index=False)
print("✓ Created results/ann_phase41_threshold_audit.csv")

print("\nAll Phase 4.1 audit CSV artifacts compiled successfully!")
