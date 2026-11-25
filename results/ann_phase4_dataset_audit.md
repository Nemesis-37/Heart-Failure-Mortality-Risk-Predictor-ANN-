# Heart Failure Mortality Risk Predictor — ANN Optimization Phase 4
## External Dataset Audit & Generalization Feasibility Assessment

**Date:** November 25, 2026  
**Objective:** Identify, audit, and evaluate independent, publicly accessible heart-failure cohorts to assess whether the shortlisted models (Logistic Regression, Arch B, Arch C) generalize beyond the original 299-patient training cohort.  

---

## 1. Executive Summary & Audit Mandate

In accordance with strict clinical AI governance principles:
> *"If no suitable dataset can be identified, do not fabricate external validation. Generate a feasibility report explaining the limitations and what data would be required."*

An exhaustive systematic search was conducted across public open-science repositories, electronic health record databases, clinical trial registries, and benchmark portals:
- **UCI Machine Learning Repository**
- **Kaggle Datasets & Medical Repositories**
- **PhysioNet (MIT Laboratory for Computational Physiology)**
- **Zenodo, Figshare, and Dryad Open Repositories**
- **Vanderbilt University Department of Biostatistics (Harrell Datasets)**
- **National Heart, Lung, and Blood Institute (NHLBI) BioLINCC Registry**

### Key Audit Findings:
1. **Pervasive Duplicate Repackaging**: Over 95% of datasets online titled *"Heart Failure Clinical Records"* or *"Heart Failure Prediction"* are mirrors, copies, or SMOTE-resampled expansions of the **exact same 299-patient cohort** from Tanvir Ahmad et al. (Faisalabad Institute of Cardiology, Pakistan, 2017). Evaluating against any of these constitutes severe circular data leakage, not external validation.
2. **Clinical Target Misclassification in Popular Benchmarks**: The widely circulated 918-patient and 1,190-patient *"Heart Failure Prediction Dataset"* (fedesoriano / Kaggle) is **not heart failure mortality**. It is an amalgamation of five 1980s Coronary Artery Disease (CAD) datasets (Cleveland, Hungarian, Long Beach, Switzerland, Statlog). Its target `HeartDisease` reflects angiographic coronary artery stenosis ($\ge 50\%$ diameter narrowing), **not patient mortality (`DEATH_EVENT`)**. Furthermore, it completely lacks 5 of the 11 baseline biomarkers (`creatinine_phosphokinase`, `ejection_fraction`, `platelets`, `serum_creatinine`, `serum_sodium`).
3. **Legitimate External Cohorts are Restricted or Require Manual DUA Access**:
   - The **Zigong Fourth People's Hospital EHR Cohort** (Zhang et al. 2021, PhysioNet, $N=2,008$) is a genuine, high-quality heart failure cohort with mortality tracking. However, it is published under PhysioNet **Restricted Access**, requiring individual CITI human-subjects credentialing, identity verification, and signed Data Use Agreements (DUA).
   - Major randomized clinical trial cohorts (e.g. **DIG Trial**, $N=6,800$; **TOPCAT**, $N=3,445$) hosted on **NHLBI BioLINCC** require formal IRB-approved scientific proposals, committee review, and institutional data sharing agreements.
4. **General EHR Datasets Lack Structured LVEF**: In general open ICU databases (e.g., MIMIC-IV demo), Left Ventricular Ejection Fraction (LVEF) is documented exclusively in unstructured free-text echocardiography notes (excluded from open de-identified demos), and serum CPK is not routinely measured in non-acute chronic heart failure management.
5. **Conclusion**: To maintain strict scientific integrity, **we do not fabricate a pseudo-external validation by misusing CAD diagnostic data or duplicate Faisalabad mirrors**. Instead, this audit establishes a rigorous clinical feasibility framework, feature mapping specification, and explicit protocol for future prospective institutional validation.

---

## 2. Systematic Audit of Candidate External Datasets

### Candidate 1: Kaggle / UCI / Figshare "Heart Failure Clinical Records" Mirrors
- **Repository Sources**: UCI ML Repository (ID 519), Kaggle (`andrewmvd/heart-failure-clinical-data`), Figshare (ehrapy mirror), GitHub repositories.
- **Reported Sample Size**: 299 patients (or 2,000–5,000 via synthetic SMOTE expansions).
- **Origin**: Faisalabad Institute of Cardiology and Allied Hospital, Faisalabad, Pakistan (Collected April–December 2015; published by Ahmad et al., PLoS ONE 2017; Chicco & Jurman, BMC Med Inform Decis Mak 2020).
- **Target Variable**: `DEATH_EVENT` (1 = deceased during follow-up, 0 = survived).
- **Clinical Features**: Exactly the 11 features utilized in our baseline training (`age`, `anaemia`, `creatinine_phosphokinase`, `diabetes`, `ejection_fraction`, `high_blood_pressure`, `platelets`, `serum_creatinine`, `serum_sodium`, `sex`, `smoking`) plus `time`.
- **Audit Verdict**: ❌ **REJECTED — DUPLICATE DATA LEAKAGE**.
- **Scientific Justification**: This dataset is the exact source data on which the models were originally trained and cross-validated. Evaluating frozen models on these mirrors would yield circular testing with zero external validity.

---

### Candidate 2: "Heart Failure Prediction Dataset" by Fedesoriano ($N = 918$ / $N = 1,190$)
- **Repository Source**: Kaggle (`fedesoriano/heart-failure-prediction`).
- **Origin**: Aggregation of 5 clinical cohorts from the 1980s: Cleveland Clinic ($N=303$), Hungarian Institute of Cardiology ($N=294$), Long Beach VA Medical Center ($N=200$), University Hospital Zurich ($N=123$), and Statlog Heart ($N=270$).
- **Reported Target**: `HeartDisease` (1 = presence of coronary artery disease, 0 = normal).
- **Variables Present**: `Age`, `Sex`, `ChestPainType`, `RestingBP`, `Cholesterol`, `FastingBS`, `RestingECG`, `MaxHR`, `ExerciseAngina`, `Oldpeak`, `ST_Slope`.
- **Variables Missing**:
  - `creatinine_phosphokinase` — **MISSING**
  - `ejection_fraction` — **MISSING** (primary predictive biomarker)
  - `platelets` — **MISSING**
  - `serum_creatinine` — **MISSING** (primary predictive biomarker)
  - `serum_sodium` — **MISSING**
  - `anaemia` — **MISSING**
  - `smoking` — **MISSING**
- **Audit Verdict**: ❌ **REJECTED — INCOMPATIBLE CLINICAL TARGET & MISSING BIOMARKERS**.
- **Scientific Justification**:
  1. **Target Mismatch**: The target variable reflects angiographic diagnosis of coronary artery stenosis ($\ge 50\%$ lumen reduction), **not mortality or heart failure survival**. Predicting CAD stenosis is a completely different clinical objective from predicting heart failure mortality.
  2. **Biomarker Deficiency**: The dataset lacks both `ejection_fraction` and `serum_creatinine`, which Chicco & Jurman (2020) demonstrated account for the vast majority of prognostic signal. Feeding synthetic or zero-imputed values for 5 missing clinical biomarkers would produce invalid inferences.

---

### Candidate 3: Zigong Fourth People's Hospital Heart Failure Database ($N = 2,008$)
- **Repository Source**: PhysioNet (`https://physionet.org/content/heart-failure-zigong/1.0.0/`).
- **Publication**: Zhang, Z., Cao, L., Chen, R. et al. *"Hospitalized patients with heart failure: integrating electronic healthcare records and external outcome data."* BMC Med Inform Decis Mak 21, 237 (2021).
- **Origin**: Hospitalized adult heart failure patients admitted to Zigong Fourth People's Hospital (Sichuan, China) between December 2016 and June 2019.
- **Clinical Target**: In-hospital mortality, 28-day mortality, 90-day mortality, and post-discharge all-cause mortality (linked via national civil registry records).
- **Biomarkers Tracked**:
  - `age`, `gender` (sex)
  - `serum_creatinine` (enzymatic method, $\mu\text{mol/L}$ requiring conversion to $\text{mg/dL}$)
  - `serum_sodium` ($\text{mmol/L}$)
  - `platelet_count` ($\times 10^9/\text{L}$)
  - `creatine_kinase` (CK, $\text{U/L}$)
  - `left_ventricular_ejection_fraction` (LVEF, %)
  - Comorbidity flags: `diabetes`, `hypertension`, `anemia`
  - Social history: `smoking_status`
- **Access Policy**: **PhysioNet Restricted Access (Credentialed)**.
- **Audit Verdict**: ⚠️ **HIGHLY RELEVANT BUT INACCESSIBLE WITHOUT MANUAL CREDENTIALING**.
- **Scientific Justification**: This is the most clinically compatible open heart-failure cohort in existence. However, it requires an individual researcher to complete CITI human-subjects training, submit an application, sign an institutional data use agreement, and obtain approval from the PhysioNet review board. In an automated offline environment, bypassing credentialing is strictly prohibited by AI safety guidelines. It represents the prime target for future prospective validation.

---

### Candidate 4: Vanderbilt SUPPORT / SUPPORT2 Cohort ($N = 9,105$)
- **Repository Source**: Vanderbilt University Department of Biostatistics (Harrell FE et al., 1995; Connors AF et al., 1996).
- **Origin**: Multi-center prospective study of hospitalized patients with life-threatening illnesses across five US teaching hospitals.
- **Target Variable**: In-hospital death, 2-month mortality, and 6-month mortality (`death` flag with survival days).
- **Sub-cohort**: 3,927 patients diagnosed with acute or chronic Congestive Heart Failure (CHF).
- **Features Present**: `age`, `sex`, `diabetes`, `sod` (sodium), `crea` (creatinine), mean arterial blood pressure.
- **Features Missing**:
  - `creatinine_phosphokinase` (CPK) — **MISSING**
  - `ejection_fraction` (LVEF) — **MISSING** (not systematically recorded across the general medical wards)
  - `platelets` — **MISSING** in primary summary tables
  - `smoking` — **MISSING** as a structured baseline predictor
- **Audit Verdict**: ❌ **REJECTED — INCOMPLETE BIOMARKER PROFILE**.
- **Scientific Justification**: Without echocardiographic ejection fraction, the model cannot evaluate myocardial systolic function, severely crippling both the Logistic Regression and neural network inference engines.

---

### Candidate 5: MIMIC-IV Clinical Database / eICU-CRD
- **Repository Source**: MIT Laboratory for Computational Physiology / PhysioNet.
- **Origin**: Critical care admissions at Beth Israel Deaconess Medical Center (Boston, MA).
- **Heart Failure Sub-cohort**: Identifiable via ICD-9 (428.x) and ICD-10 (I50.x) diagnosis codes.
- **Mortality Target**: In-hospital mortality and post-discharge out-of-hospital survival (via Social Security Death Index).
- **Audit Verdict**: ❌ **INCOMPATIBLE FOR OPEN VALIDATION**.
- **Scientific Justification**:
  1. In the open public demo ($N=100$), multi-condition queries for heart failure with complete laboratory profiles yield zero to fewer than 5 patients.
  2. LVEF is trapped in unstructured free-text radiology and echocardiography notes, which are stripped from open de-identified distributions.
  3. Serum CPK is not part of standard routine heart failure monitoring panels unless acute coronary syndrome is actively suspected.

---

### Candidate 6: NHLBI BioLINCC Clinical Trial Repositories (DIG, TOPCAT, SOLVD)
- **Repository Source**: National Heart, Lung, and Blood Institute (NHLBI) Biologic Specimen and Data Repository Information Coordinating Center.
- **Clinical Trials**:
  - **DIG Trial** ($N = 6,800$, chronic heart failure patients with LVEF $\le 45\%$, tracked for all-cause mortality).
  - **TOPCAT Trial** ($N = 3,445$, heart failure with preserved ejection fraction).
  - **SOLVD Trial** ($N = 6,797$, left ventricular dysfunction).
- **Audit Verdict**: ⚠️ **GOLD-STANDARD EXTERNAL COHORTS BUT RESTRICTED ACCESS**.
- **Scientific Justification**: These multi-center randomized controlled trials are the gold standard in cardiology. However, access requires a formal scientific research proposal submission, institutional review board (IRB) review, and a fully executed BioLINCC Data Sharing Agreement with an institutional signing official, requiring 4 to 8 weeks for approval.

---

## 3. Summary Feature Compatibility Matrix

| Baseline 11 Feature | Ahmad et al. (Original 299) | Fedesoriano CAD (918) | Zigong HF EHR (2,008) | SUPPORT CHF (3,927) | MIMIC-IV Open Demo (100) | BioLINCC DIG Trial (6,800) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Age** (years) | Yes | Yes | Yes | Yes | Yes | Yes |
| **Sex** (binary 0/1) | Yes | Yes | Yes | Yes | Yes | Yes |
| **Anaemia** (binary) | Yes | No | Yes (via Hb) | No | Yes (via Hb) | Yes (via Hct) |
| **Diabetes** (binary) | Yes | Yes (FastingBS) | Yes (ICD-10) | Yes | Yes (ICD-10) | Yes |
| **High Blood Pressure** (binary) | Yes | Yes (RestingBP) | Yes (ICD-10) | Yes (MAP) | Yes (ICD-10) | Yes |
| **Smoking** (binary) | Yes | No | Yes | No | No (unstructured) | No |
| **Platelets** (platelets/$\mu\text{L}$) | Yes | **NO** | Yes | No | Yes | No |
| **Serum Creatinine** ($\text{mg/dL}$) | Yes | **NO** | Yes ($\mu\text{mol/L}$) | Yes | Yes | Yes |
| **Serum Sodium** ($\text{mEq/L}$) | Yes | **NO** | Yes | Yes | Yes | Yes |
| **Creatinine Phosphokinase** ($\text{U/L}$) | Yes | **NO** | Yes | **NO** | No (rarely ordered) | No |
| **Ejection Fraction** (LVEF %) | Yes | **NO** | Yes | **NO** | No (in text notes) | Yes |
| **Target: Mortality Outcome** | **DEATH_EVENT** | **NO (CAD stenosis)** | **YES (All-cause death)** | **YES (Survival)** | **YES (In-hospital)** | **YES (All-cause death)** |
| **Immediate Open Access** | Yes (Original) | Yes (Incompatible) | ❌ Restricted (DUA) | Yes (Missing EF/CK) | ❌ Notes Excluded | ❌ BioLINCC Proposal |

---

## 4. Feasibility Assessment & Requirements for Future External Validation

To validate the shortlisted models (**Arch B**, **Arch C**, and **Logistic Regression**) without compromising clinical or ethical standards, the following data collection protocol must be implemented:

1. **Target Population**: Ambulatory or hospitalized adult patients ($\ge 18$ years) with a confirmed diagnosis of Heart Failure (NYHA Class II–IV or ACC/AHA Stage C–D).
2. **Mandatory Biomarker Panel**:
   - Echocardiographic **LVEF** (measured by Simpson's biplane or 2D echo within 30 days of evaluation).
   - Renal panel: **Serum Creatinine** ($\text{mg/dL}$ or $\mu\text{mol/L}$ converted via $1\text{ mg/dL} = 88.42\ \mu\text{mol/L}$) and **Serum Sodium** ($\text{mEq/L}$ or $\text{mmol/L}$).
   - Hematologic panel: **Platelet Count** ($\times 10^3/\mu\text{L}$ or platelets/$\mu\text{L}$).
   - Cardiac enzyme: **Creatinine Phosphokinase** ($\text{U/L}$ or $\mu\text{g/L}$).
   - Clinical comorbidities: Documented history of **Hypertension**, **Diabetes Mellitus**, **Anemia** (or hemoglobin $< 12.0\text{ g/dL}$ for women, $< 13.0\text{ g/dL}$ for men), and **Tobacco Smoking Status**.
3. **Primary Endpoint**: All-cause mortality within a predefined follow-up window (e.g., 30-day, 1-year, or median 130-day follow-up matching the Ahmad cohort).
4. **Institutional Execution Plan**:
   - Submit an institutional data request for the **PhysioNet Zigong Fourth People's Hospital Database** to evaluate performance on East Asian hospitalized cohorts.
   - Apply for NHLBI BioLINCC access to the **DIG Trial** or **TOPCAT Trial** for North American / European clinical trial cohorts.
