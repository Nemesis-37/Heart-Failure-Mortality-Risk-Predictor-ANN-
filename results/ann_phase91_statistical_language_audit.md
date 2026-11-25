# Phase 9.1 — Statistical Language Audit & Correction Report

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** 9.1 — Final Deployment Consistency Audit  
**Date:** November 2026  
**Subject:** Rigorous Scientific Communication & Removal of Exaggerated Statistical Claims  

---

## 1. Executive Summary

This audit reviewed all documentation, report narratives, and summaries produced across the project to eliminate inaccurate statistical interpretations, unverified clinical assertions, and overstatements. Four specific areas of scientific language were corrected:

1. **Interpretation of Non-Significant $p$-values** (rejection of equivalence claims).
2. **Interpretation of Low Bivariate Feature Correlations** (rejection of "noise" claims).
3. **Characterization of Feature Relationships** (rejection of claims that clinical biology is "fundamentally linear").
4. **Validation Claims** (strict distinction between internal cross-validation and external clinical validation).

---

## 2. Itemized Language Audits and Corrections

### 2.1 Non-Significant $p$-values vs Claims of Equivalence
- ❌ **Unacceptable Language:** *"The non-significant p-value of 0.6250 proves that the 8-feature ANN is equivalent to Logistic Regression."*
- ✅ **Corrected Scientific Language:**  
  *"The paired Wilcoxon signed-rank test yields $p = 0.6250$, indicating insufficient statistical evidence to reject the null hypothesis of equal discrimination between the two models on this sample. Given the modest cohort size ($N=299$, 96 events), statistical power to detect small differences (e.g. $< 3\%$ AUROC) is low. A non-significant $p$-value must never be interpreted as positive evidence of equivalence, non-inferiority, or interchangeable performance."*

### 2.2 Low Individual Feature Correlations vs "Noise" Labels
- ❌ **Unacceptable Language:** *"Features with low correlation like diabetes, sex, and smoking are noise features and contain zero predictive value."*
- ✅ **Corrected Scientific Language:**  
  *"In bivariate screening, `diabetes` ($r = -0.002$), `sex` ($r = -0.004$), and `smoking` ($r = -0.013$) exhibited near-zero linear correlation with mortality in this retrospective sample. Removing them improved Events-Per-Variable (EPV) from 8.7 to 12.0 and reduced estimation variance for both models. However, this reflects sample-specific empirical unhelpfulness under penalized estimation, not an absence of biological relevance in broader heart failure pathophysiology."*

### 2.3 Cohort Linearity Claims
- ❌ **Unacceptable Language:** *"Cardiovascular biology and the clinical signal in this cohort are fundamentally linear."*
- ✅ **Corrected Scientific Language:**  
  *"Within this 299-patient dataset across the 11 measured indicators, linear additive log-odds models (Logistic Regression) perform as well as or better than non-linear multi-layer perceptrons under cross-validation. While biological processes often involve complex feedback mechanisms, the available sample size and feature resolution in this dataset do not provide recoverable non-linear interaction signals that an artificial neural network can exploit to improve generalization over a linear model."*

### 2.4 Internal Cross-Validation vs Clinical Validity
- ❌ **Unacceptable Language:** *"The model has achieved 77.17% AUROC and is clinically validated for hospital deployment."*
- ✅ **Corrected Scientific Language:**  
  *"The reported AUROC of 77.17% represents out-of-fold internal cross-validation performance on a single retrospective cohort of 299 patients from a single medical center. Internal cross-validation evaluates internal consistency and protects against data leakage during model comparison; it does NOT establish clinical validity, generalizability to independent patient populations, or readiness for therapeutic decisions. External validation on independent multi-center cohorts has NOT been conducted."*

---

## 3. Mandatory Educational Disclaimers

All client-facing interfaces and model documentation must maintain the following persistent disclaimer:
> **"Educational ML Prototype:** This software is an academic machine-learning research prototype developed for educational demonstration. It is not certified as a medical device and must not be used for clinical diagnosis, patient triage, or therapeutic decision-making."
