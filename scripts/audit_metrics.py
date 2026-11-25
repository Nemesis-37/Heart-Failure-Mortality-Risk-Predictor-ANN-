import os
import pandas as pd
import numpy as np

print("=" * 80)
print("COMPREHENSIVE METRIC AUDIT & EXTRACTION")
print("=" * 80)

# 1. Phase 1
df_p1 = pd.read_csv('results/ann_phase1_experiments_summary.csv')
print("\n--- PHASE 1 SUMMARY (Top Models) ---")
for model_name in df_p1['Model'].unique():
    sub = df_p1[df_p1['Model'] == model_name]
    metrics = dict(zip(sub['Metric'], zip(sub['Mean'], sub['Standard_Deviation'])))
    auroc = metrics.get('AUROC', (None, None))
    brier = metrics.get('Brier_Score', (None, None))
    sens = metrics.get('Sensitivity', (None, None))
    spec = metrics.get('Specificity', (None, None))
    f1 = metrics.get('F1_Score', (None, None))
    acc = metrics.get('Accuracy', (None, None))
    print(f"{model_name:50} | AUROC: {auroc[0]:.4f}±{auroc[1]:.4f} | Brier: {brier[0]:.4f} | Sens: {sens[0]:.4f} | Spec: {spec[0]:.4f} | F1: {f1[0]:.4f}")

# 2. Phase 2
df_p2 = pd.read_csv('results/ann_phase2_experiments_summary.csv')
print("\n--- PHASE 2 SUMMARY (Selected Candidates) ---")
# Look for Arch_B models
b_rows = df_p2[df_p2['Architecture'] == 'Arch_B_16']
for _, r in b_rows.iterrows():
    print(f"{r['Model']:50} | AUROC: {r['AUROC_Mean']:.6f}±{r['AUROC_Std']:.6f} | Brier: {r['Brier_Score_Mean']:.6f} | Sens: {r['Sensitivity_Mean']:.4f}±{r['Sensitivity_Std']:.4f} | Spec: {r['Specificity_Mean']:.4f}")

# Look for Arch_C models
c_rows = df_p2[df_p2['Architecture'] == 'Arch_C_32_16']
for _, r in c_rows.iterrows():
    if 'wd0.001' in r['Model'] or 'wd0.01' in r['Model']:
        print(f"{r['Model']:50} | AUROC: {r['AUROC_Mean']:.6f}±{r['AUROC_Std']:.6f} | Brier: {r['Brier_Score_Mean']:.6f} | Sens: {r['Sensitivity_Mean']:.4f} | Spec: {r['Specificity_Mean']:.4f}")

# 3. Phase 3
df_p3_model = pd.read_csv('results/ann_phase3_model_comparison.csv')
print("\n--- PHASE 3 MODEL COMPARISON ---")
for _, r in df_p3_model.iterrows():
    print(f"{r['Model']:28} | {r['Operating_Mode']:30} | Thr: {r['Decision_Threshold']:15} | AUROC: {r['AUROC']:15} | Brier: {r['Brier_Score']:15} | Sens: {r['Sensitivity']:15} | Spec: {r['Specificity']:15} | F1: {r['F1_Score']:15}")

# 4. Phase 3 Fold Results
df_p3_folds = pd.read_csv('results/ann_phase3_fold_results.csv')
print("\n--- PHASE 3 FOLD RESULTS COLS ---")
print(df_p3_folds.columns.tolist())
print(df_p3_folds.head(5).to_string())

# Find the exact column names
model_col = [c for c in df_p3_folds.columns if 'model' in c.lower()][0]
mode_col = [c for c in df_p3_folds.columns if 'mode' in c.lower() or 'eval' in c.lower() or 'threshold' in c.lower()][0]

print("\n--- PHASE 3 FOLD RESULTS GROUPBY ---")
num_cols = df_p3_folds.select_dtypes(include=[np.number]).columns.tolist()
print(df_p3_folds.groupby([model_col, mode_col])[num_cols].mean().to_string())

# 5. Check Fold 1-5 details for Logistic Regression & Arch B at threshold 0.33
print("\n--- FOLD-LEVEL DETAIL: LOGISTIC REGRESSION ---")
lr_folds = df_p3_folds[df_p3_folds[model_col].str.contains('Logistic')]
print(lr_folds.to_string())

print("\n--- FOLD-LEVEL DETAIL: ARCH B ---")
b_folds = df_p3_folds[df_p3_folds[model_col].str.contains('Arch B')]
print(b_folds.to_string())

# 6. Check Phase 4 external metrics csv
print("\n--- PHASE 4 EXTERNAL METRICS CSV ---")
df_p4_ext = pd.read_csv('results/ann_phase4_external_metrics.csv')
for _, r in df_p4_ext.iterrows():
    print(f"{r['Cohort_Type']:15} | {r['Cohort_Name']:30} | {str(r['Model_Evaluated']):20} | Thr: {str(r['Decision_Threshold']):20} | AUROC: {str(r['AUROC']):15} | Sens: {str(r['Sensitivity']):15} | Status: {r['Validation_Status']}")

