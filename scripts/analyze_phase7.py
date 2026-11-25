import pandas as pd
import numpy as np

fold = pd.read_csv('results/ann_phase7_fold_metrics.csv')
print('=== FOLD METRICS ===')
for mid in fold['Model_ID'].unique():
    sub = fold[fold['Model_ID'] == mid]
    print(f'\n{mid}:')
    cols = ['Fold','AUROC','Brier_Score','Log_Loss','Sensitivity','Specificity','Precision','F1_Score','Calibration_Slope','Calibration_Intercept','TP','FP','TN','FN']
    print(sub[cols].to_string(index=False))
    print(f'  Mean AUROC: {sub["AUROC"].mean():.6f} +/- {sub["AUROC"].std():.6f}')
    print(f'  Mean Brier: {sub["Brier_Score"].mean():.6f} +/- {sub["Brier_Score"].std():.6f}')
    print(f'  Mean LogLoss: {sub["Log_Loss"].mean():.6f} +/- {sub["Log_Loss"].std():.6f}')
    print(f'  Mean CalSlope: {sub["Calibration_Slope"].mean():.4f}')
    print(f'  Mean CalIntercept: {sub["Calibration_Intercept"].mean():.4f}')

print('\n=== PREPROCESSING COMPARISON ===')
pre = pd.read_csv('results/ann_phase7_preprocessing_comparison.csv')
print(pre.to_string(index=False))

print('\n=== OOF CONCORDANCE CHECK ===')
pred = pd.read_csv('results/ann_phase7_prediction_comparison.csv')
print('Total patients:', len(pred))
print('Agreement LR vs WD_Log at 0.50:', (pred['Pred_LR_050'] == pred['Pred_WD_Log_050']).mean())
print('Agreement LR vs WD_Std at 0.50:', (pred['Pred_LR_050'] == pred['Pred_WD_Std_050']).mean())
print('WD_Log TP at 0.50:', ((pred['Pred_WD_Log_050']==1) & (pred['True_Death_Event']==1)).sum())
print('LR TP at 0.50:', ((pred['Pred_LR_050']==1) & (pred['True_Death_Event']==1)).sum())
print('WD_Log FP at 0.50:', ((pred['Pred_WD_Log_050']==1) & (pred['True_Death_Event']==0)).sum())
print('LR FP at 0.50:', ((pred['Pred_LR_050']==1) & (pred['True_Death_Event']==0)).sum())
print('WD_Log FN at 0.50:', ((pred['Pred_WD_Log_050']==0) & (pred['True_Death_Event']==1)).sum())
print('LR FN at 0.50:', ((pred['Pred_LR_050']==0) & (pred['True_Death_Event']==1)).sum())
print('\n--- Wilcoxon AUROC pair tests (LR vs each ANN) ---')
from scipy.stats import wilcoxon
lr_auroc = fold[fold['Model_ID']=='Logistic_Regression']['AUROC'].values
for mid in ['Arch_B_Standard', 'WideDeep_Standard', 'WideDeep_Log']:
    ann_auroc = fold[fold['Model_ID']==mid]['AUROC'].values
    if len(ann_auroc) == len(lr_auroc):
        stat, p = wilcoxon(lr_auroc, ann_auroc)
        delta = ann_auroc.mean() - lr_auroc.mean()
        print(f'  LR vs {mid}: delta={delta*100:+.2f}%, Wilcoxon p={p:.4f}')
