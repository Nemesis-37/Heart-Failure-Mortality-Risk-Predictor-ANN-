import pandas as pd

print("=== Phase 2 Architecture Comparison ===")
df2_arch = pd.read_csv("results/ann_phase2_architecture_comparison.csv")
c_arch = df2_arch[df2_arch["Model"].str.contains("Arch_C")]
print(c_arch[["Model", "Parameters", "Dropout", "Weight_Decay", "Batch_Size", "AUROC_Mean", "AUROC_Std", "Brier_Score_Mean"]])

print("\n=== Phase 2 Tuning (Best Arch C) ===")
df2_exp = pd.read_csv("results/ann_phase2_experiments_summary.csv")
c_exp = df2_exp[df2_exp["Model"].str.contains("Arch_C")]
print(c_exp[["Model", "Dropout", "Weight_Decay", "Batch_Size", "AUROC_Mean", "AUROC_Std", "Brier_Score_Mean"]])

print("\n=== Phase 3 Models Fold Results ===")
df3 = pd.read_csv("results/ann_phase3_fold_results.csv")
for mid in df3["Model_ID"].unique():
    sub = df3[df3["Model_ID"] == mid]
    print(f"\n{mid}:")
    print(f"  AUROC Mean: {sub['AUROC'].mean():.6f} ± {sub['AUROC'].std(ddof=1):.6f}")
    print(f"  Uncal Brier Mean: {sub['Uncal_Brier'].mean():.6f}")
    print(f"  Uncal LogLoss Mean: {sub['Uncal_LogLoss'].mean():.6f}")
    print(f"  Uncal Sens 0.50 Mean: {sub['Uncal_Sens_050'].mean():.6f}")
    print(f"  Uncal Spec 0.50 Mean: {sub['Uncal_Spec_050'].mean():.6f}")
    for _, r in sub.iterrows():
        print(f"    Fold {int(r['Fold'])}: AUROC={r['AUROC']:.6f}, Brier={r['Uncal_Brier']:.6f}, LogLoss={r['Uncal_LogLoss']:.6f}")
