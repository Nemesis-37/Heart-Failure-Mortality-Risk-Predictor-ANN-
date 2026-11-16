# Heart Failure Mortality Risk Predictor (ANN)

A full-stack, machine-learning-driven **clinical decision-support prototype** that estimates the probability of a mortality event for patients with heart failure at the point of clinical assessment.

The project combines an **Advanced Data Science / Deep Learning pipeline** with a production-oriented web architecture consisting of **PyTorch, scikit-learn, FastAPI, React, Tailwind CSS, and PostgreSQL**.

> **Clinical Safety Notice:** This project is a research and clinical decision-support prototype. It is not a diagnostic system and must not replace professional clinical judgment or be used as the sole basis for treatment or discharge decisions.

---

# 1. Project Overview

Heart failure patients can have substantially different mortality risks depending on their clinical characteristics.

This project aims to build a machine-learning system that accepts patient-level clinical information and produces a **mortality probability** using a trained Artificial Neural Network.

The project follows a complete machine-learning lifecycle:

```text
Clinical Dataset
      ↓
Data Quality Checks
      ↓
Exploratory Data Analysis
      ↓
Prediction-Timepoint Definition
      ↓
Leakage Assessment
      ↓
Feature / Target Preparation
      ↓
Stratified 5-Fold Cross-Validation
      ↓
Fold-Safe Preprocessing
      ↓
Logistic Regression Baseline
      ↓
PyTorch Deep ANN
      ↓
Hyperparameter / Architecture Experimentation
      ↓
Regularization + Early Stopping
      ↓
Out-of-Fold Evaluation
      ↓
Threshold Analysis
      ↓
Probability Calibration
      ↓
Model Serialization
      ↓
FastAPI Prediction Service
      ↓
React Clinical Dashboard
      ↓
PostgreSQL
```

The system is designed around a **probability-first prediction approach**, rather than assigning arbitrary LOW/MEDIUM/HIGH labels without validation-based justification.

---

# 2. Objectives

The primary objectives are to:

- Build a binary mortality-risk prediction model for heart failure patients.
- Establish a **Logistic Regression baseline**.
- Develop a **Deep Artificial Neural Network using PyTorch**.
- Compare the ANN against the baseline using the same validation methodology.
- Prevent data leakage throughout preprocessing, validation, and calibration.
- Evaluate discrimination using AUROC.
- Evaluate clinically relevant classification behavior using sensitivity and specificity.
- Produce calibrated mortality probabilities.
- Provide a prediction API using FastAPI.
- Provide a clinician-oriented React dashboard.
- Store application data and prediction history using PostgreSQL.
- Provide authentication and controlled access to the application.
- Support model explainability and prediction transparency.
- Containerize the complete application for deployment.

---

# 3. Clinical Use Case

## Intended Users

The intended users include:

- Cardiologists
- Physicians
- Hospital discharge-planning teams
- Authorized clinical users

## Intended Workflow

```text
User Login
    ↓
Clinical Dashboard
    ↓
Enter Patient Information
    ↓
Validate Input
    ↓
Send Prediction Request
    ↓
Preprocess Clinical Features
    ↓
ANN Model
    ↓
Mortality Probability
    ↓
Display Prediction + Explanation
    ↓
Store Prediction History
```

The system is intended to support clinical assessment and decision-making, while leaving the final clinical decision to qualified healthcare professionals.

---

# 4. Dataset

The project uses the **Heart Failure Clinical Records Dataset**.

The dataset contains:

- **299 patient records**
- Clinical features related to heart failure
- A binary mortality target: `DEATH_EVENT`

The original dataset contains:

```text
age
anaemia
creatinine_phosphokinase
diabetes
ejection_fraction
high_blood_pressure
platelets
serum_creatinine
serum_sodium
sex
smoking
time
DEATH_EVENT
```

## Target

```text
DEATH_EVENT
```

Meaning:

```text
0 → No death event
1 → Death event
```

---

# 5. Prediction Timepoint and Data Leakage

The prediction timepoint is defined as the patient's **clinical assessment / discharge-time decision context**.

The `time` feature represents retrospective follow-up duration.

Because this information would not be appropriately available at the intended prediction point, `time` is excluded from the deployment feature set.

Therefore:

```text
Original columns: 13
        ↓
Remove time
        ↓
Remove DEATH_EVENT from inputs
        ↓
11 model features
```

Current model features:

```text
age
anaemia
creatinine_phosphokinase
diabetes
ejection_fraction
high_blood_pressure
platelets
serum_creatinine
serum_sodium
sex
smoking
```

The leakage assessment is part of the required preprocessing workflow.

---

# 6. Data Preparation

The preprocessing stage includes:

- Dataset loading
- Data type inspection
- Missing-value analysis
- Duplicate detection
- Binary-value validation
- Numerical range inspection
- Potential outlier analysis
- Target distribution analysis
- Feature distribution analysis
- Feature-vs-target EDA
- Leakage assessment
- Feature/target separation
- Feature scaling

Potential outliers are inspected using the **IQR method** and are not automatically removed merely because they fall outside the IQR boundaries.

---

# 7. Feature and Target Preparation

The model inputs are separated from the target:

```python
X = df.drop(columns=["DEATH_EVENT", "time"])
y = df["DEATH_EVENT"]
```

This produces:

```text
X → 299 × 11
y → 299
```

The binary clinical variables are already represented using `0/1` values, so additional categorical encoding is unnecessary for this dataset.

---

# 8. Validation Strategy

Because the dataset is relatively small, the project uses:

## Stratified 5-Fold Cross-Validation

Each iteration contains:

```text
4 folds → Training
1 fold → Validation
```

The process is repeated five times.

Stratification ensures that the class distribution remains approximately consistent between training and validation folds.

```text
Dataset
   ↓
 ┌─────┬─────┬─────┬─────┬─────┐
 │ F1  │ F2  │ F3  │ F4  │ F5  │
 └─────┴─────┴─────┴─────┴─────┘

Fold 1 → F2+F3+F4+F5 train → F1 validation
Fold 2 → F1+F3+F4+F5 train → F2 validation
Fold 3 → F1+F2+F4+F5 train → F3 validation
Fold 4 → F1+F2+F3+F5 train → F4 validation
Fold 5 → F1+F2+F3+F4 train → F5 validation
```

The same validation methodology is used for the Logistic Regression baseline and ANN to enable a fair comparison.

---

# 9. Leakage-Safe Preprocessing

Preprocessing is performed **inside each cross-validation fold**.

For scaling:

```python
scaler.fit(X_train)
X_train_scaled = scaler.transform(X_train)
X_val_scaled = scaler.transform(X_val)
```

The validation data is never used to fit the scaler.

This prevents information from the validation fold from influencing the training process.

The project also defines a reusable preprocessing pipeline for model development and deployment.

---

# 10. Logistic Regression Baseline

Before implementing the ANN, Logistic Regression is used as the mandatory baseline model.

The baseline establishes a reference level of performance against which the ANN can be evaluated.

Current 5-fold results:

| Metric | Mean |
|---|---:|
| Accuracy | **75.60%** |
| AUROC | **77.17%** |
| Sensitivity | **48.11%** |
| Specificity | **88.67%** |

Confusion-matrix components are also recorded for each fold:

- True Positive (TP)
- True Negative (TN)
- False Positive (FP)
- False Negative (FN)

---

# 11. Artificial Neural Network

The primary model is a **Deep Artificial Neural Network implemented using PyTorch**.

The ANN receives the 11 prepared clinical features:

```text
11 Clinical Features
        ↓
Input Layer
        ↓
Hidden Layer(s)
        ↓
Activation Functions
        ↓
Regularization
        ↓
Output Layer
        ↓
Mortality Probability
```

The exact ANN architecture is not fixed beforehand.

Architecture and hyperparameters are selected through controlled experimentation and validation rather than assuming that a particular number of layers or neurons is optimal.

---

# 12. ANN Training

The ANN training process follows:

```text
Input
  ↓
Forward Pass
  ↓
Predicted Probability
  ↓
Loss Calculation
  ↓
Backpropagation
  ↓
Optimizer
  ↓
Weight Update
  ↓
Next Training Epoch
```

Training will include mechanisms for controlling overfitting, including:

- Dropout
- Weight decay
- Early stopping where appropriate

Early stopping is used to prevent continued training after validation performance stops improving.

---

# 13. Class Imbalance

The dataset contains fewer positive mortality events than negative events.

Therefore, class distribution is considered during model training and evaluation.

The project evaluates the model using metrics beyond accuracy so that performance on the mortality class is not hidden by the class imbalance.

---

# 14. Evaluation Metrics

The primary evaluation metrics are:

## AUROC

Measures the model's ability to distinguish between mortality and non-mortality outcomes across thresholds.

## Sensitivity

Measures how many actual mortality events are correctly identified.

```text
Sensitivity = TP / (TP + FN)
```

## Specificity

Measures how many actual non-mortality cases are correctly identified.

```text
Specificity = TN / (TN + FP)
```

## Supporting Metrics

The system also evaluates:

- Accuracy
- Precision
- Recall
- F1 Score
- Confusion Matrix
- ROC curve
- Precision-Recall analysis

These evaluation requirements are defined in the project scope.

---

# 15. Out-of-Fold Predictions

For each validation fold, the model produces predictions for data that was not used for training that fold.

These predictions are collected:

```text
Fold 1 predictions
        +
Fold 2 predictions
        +
Fold 3 predictions
        +
Fold 4 predictions
        +
Fold 5 predictions
        ↓
Out-of-Fold Predictions
```

The complete set of out-of-fold predictions is used for unbiased model evaluation and probability calibration.

---

# 16. Threshold Analysis

The model produces a probability rather than directly relying on an arbitrary classification label.

Threshold analysis is performed using validation data to understand the relationship between:

- Sensitivity
- Specificity
- False positives
- False negatives

The final threshold policy must be derived from validation evidence rather than chosen arbitrarily.

---

# 17. Probability Calibration

A major part of the project is ensuring that the predicted probabilities are meaningful.

For example, if a model produces predictions around:

```text
0.70
```

the probability should correspond reasonably to the observed frequency of the outcome for cases receiving similar predictions.

Calibration uses:

- Out-of-fold predictions
- Reliability / calibration curves
- Brier score

Calibration must be performed without fitting and evaluating the calibration procedure on the same observations.

---

# 18. Brier Score

The Brier score evaluates the accuracy of probabilistic predictions.

It measures the difference between predicted probabilities and actual binary outcomes.

A lower Brier score indicates better probabilistic accuracy.

The Brier score is therefore used alongside discrimination metrics such as AUROC rather than replacing them.

---

# 19. Model Explainability

The system is designed to provide an explanation of the factors contributing to a prediction.

The explainability component is intended to help the clinician understand which input features contributed to the model output.

The PRD includes feature-importance / explainability functionality as part of the application design.

---

# 20. Probability-First Clinical Output

The system's primary output is:

```text
Estimated Mortality Probability
```

Example:

```text
Estimated mortality probability: 0.78
```

The project does **not** use arbitrary:

```text
LOW
MEDIUM
HIGH
```

categories unless thresholds are derived from validation data and justified.

This keeps the output aligned with the model's calibrated probability rather than introducing unsupported risk categories.

---

# 21. Model Serialization

After model selection and evaluation, the final preprocessing and model artifacts will be serialized.

The saved artifacts are intended to contain the information required to reproduce the same preprocessing and inference behavior during API prediction.

The deployment flow is:

```text
Saved Preprocessing
       +
Saved Model
       ↓
FastAPI
       ↓
New Patient Data
       ↓
Same Preprocessing
       ↓
Model Inference
       ↓
Mortality Probability
```

---

# 22. FastAPI Backend

The backend will expose the trained ML model through a FastAPI service.

The backend is responsible for:

- Authentication
- Request validation
- Patient input handling
- Feature preprocessing
- Model inference
- Mortality probability response
- Prediction history
- Model-related services
- API documentation

The architecture separates the ML inference layer from the React frontend.

---

# 23. API Design

The planned API layer includes functionality for:

```text
Authentication
    ↓
User/session management

Prediction
    ↓
Patient input
    ↓
Mortality probability

History
    ↓
Previous predictions

Model / Explainability
    ↓
Model information
    ↓
Feature importance / explanation
```

FastAPI's automatic API documentation will be available during development.

---

# 24. Authentication and Authorization

The application includes authentication to restrict access to authorized users.

The backend architecture uses:

- JWT-based authentication
- Stateless authentication/session handling
- Protected API endpoints
- Native Argon2id password hashing via `argon2-cffi` (install with `pip install -r requirements-auth.txt`)

For local development only, create the demo doctor with `APP_ENV=development` and `DEMO_DOCTOR_PASSWORD` set, then run `scripts/create_demo_doctor.py`. The script refuses non-local SQL Server targets and does not change an existing account.

Provision or update the administrator explicitly by setting `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the local environment and running `python scripts/provision_admin.py`. The password is stored as an Argon2id hash; no default administrator credentials are seeded. `ADMIN_RECOVERY_EMAIL` may be set separately for OTP password recovery and otherwise defaults to `ADMIN_EMAIL`. Keep all real credential values out of source control.

The system also includes role/access considerations as defined by the application requirements.

---

# 25. PostgreSQL

PostgreSQL is used as the application's persistent system of record.

It is intended to store application-level information such as:

- Users
- Authentication-related data
- Prediction history
- Relevant application metadata

SQLAlchemy is used for database interaction and Alembic is used for database migrations.

The PRD formally defines PostgreSQL as the system-of-record database.

---

# 26. Prediction History

Authorized users will be able to access previous predictions.

The prediction-history component supports:

- Patient/prediction records
- Prediction probability
- Timestamp / relevant metadata
- Historical review

This allows users to review previous model predictions through the application.

---

# 27. React Clinical Dashboard

The frontend will be developed using:

- React
- Tailwind CSS

The dashboard is designed around a simple clinical workflow.

Planned interface:

```text
Login
  ↓
Dashboard
  ↓
Patient Information
  ↓
Prediction
  ↓
Mortality Probability
  ↓
Explanation
  ↓
Prediction History
```

The interface follows the project's probability-first design principle.

---

# 28. Frontend Prediction Flow

The clinician enters the required clinical features.

```text
Patient Information
       ↓
Frontend Validation
       ↓
FastAPI Request
       ↓
Preprocessing
       ↓
ANN
       ↓
Probability
       ↓
Frontend Result
```

The frontend does not independently implement the ML model.

The trained model remains on the backend inference service.

---

# 29. System Architecture

The planned system architecture consists of:

```text
┌──────────────────────────────┐
│        React Frontend        │
│       Tailwind CSS           │
└──────────────┬───────────────┘
               │
               │ HTTP / API
               ▼
┌──────────────────────────────┐
│        FastAPI Backend       │
│                              │
│ Authentication               │
│ Prediction                   │
│ Validation                   │
│ History                      │
│ Explainability               │
└───────┬──────────────┬───────┘
        │              │
        │              │
        ▼              ▼
┌───────────────┐  ┌────────────────┐
│ ML Inference  │  │  PostgreSQL    │
│               │  │                │
│ Preprocessing │  │ Users          │
│ ANN           │  │ History        │
│ Calibration   │  │ Metadata       │
└───────────────┘  └────────────────┘
```

The HLD/LLD in the PRD defines the ML, API, frontend, database, authentication, history, and explainability layers.

---

# 30. Technology Stack

## Machine Learning

- Python
- pandas
- NumPy
- scikit-learn
- PyTorch
- Matplotlib

## Backend

- FastAPI
- Python
- SQLAlchemy
- Alembic
- PostgreSQL
- JWT authentication

## Frontend

- React
- JavaScript
- Tailwind CSS

## Deployment

- Docker
- docker-compose

---

# 31. Project Structure

The final project is planned around the following structure:

```text
Heart-Failure-Mortality-Risk-Predictor-ANN/
│
├── data/
│   └── heart_failure_clinical_records_dataset.csv
│
├── ml/
│   ├── preprocessing/
│   ├── models/
│   ├── training/
│   ├── evaluation/
│   └── calibration/
│
├── artifacts/
│   ├── preprocessing/
│   └── model/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   └── migrations/
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       └── ...
│
├── tests/
│
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
```

The exact structure may evolve during implementation while remaining consistent with the PRD architecture.

---

# 32. Testing and Reproducibility

The project includes testing and reproducibility requirements covering:

### ML

- Preprocessing correctness
- Leakage prevention
- Cross-validation
- Metric calculation
- Model inference
- Calibration

### Backend

- API validation
- Authentication
- Prediction endpoints
- Database operations

### Frontend

- Input validation
- Prediction workflow
- Result rendering
- History display

### Reproducibility

The ML pipeline uses controlled random seeds where appropriate so that experiments can be reproduced.

---

# 33. Deployment

The complete application is intended to be containerized using Docker.

Planned services:

```text
docker-compose
      │
      ├── React Frontend
      │
      ├── FastAPI Backend
      │
      └── PostgreSQL
```

Environment-specific configuration will be supplied through environment variables.

Sensitive information such as:

- Database credentials
- JWT secrets
- Environment configuration

must not be committed directly to the repository.

---

# 34. Environment Configuration

A `.env.example` file will define the required configuration structure.

Example categories include:

```text
DATABASE_URL
JWT_SECRET
ENVIRONMENT
API configuration
```

Actual secrets must remain outside version control.

---

# 35. Current Development Status

## Machine Learning

- [x] Dataset loaded
- [x] Data quality checks
- [x] Missing-value analysis
- [x] Duplicate analysis
- [x] Binary-value validation
- [x] Outlier inspection
- [x] Initial EDA
- [x] Target distribution
- [x] Numerical feature distributions
- [x] Feature/target preparation
- [x] `time` leakage exclusion
- [x] Stratified 5-Fold Cross-Validation
- [x] Feature scaling
- [x] Leakage-safe fold preprocessing
- [x] Logistic Regression baseline

## Remaining ML Work

- [ ] Complete feature-vs-target EDA
- [ ] Final reusable preprocessing pipeline
- [ ] ANN architecture experimentation
- [ ] PyTorch ANN training
- [ ] Regularization
- [ ] Early stopping
- [ ] ANN 5-Fold Cross-Validation
- [ ] ANN evaluation
- [ ] Baseline vs ANN comparison
- [ ] Out-of-fold predictions
- [ ] Threshold analysis
- [ ] Calibration curve
- [ ] Brier score
- [ ] Final model selection
- [ ] Model serialization

## Backend

- [ ] FastAPI application
- [ ] Prediction endpoint
- [ ] Request/response schemas
- [ ] JWT authentication
- [ ] Protected endpoints
- [ ] PostgreSQL integration
- [ ] SQLAlchemy models
- [ ] Alembic migrations
- [ ] Prediction history
- [ ] Model information/explainability endpoints

## Frontend

- [ ] React application
- [ ] Authentication UI
- [ ] Clinical dashboard
- [ ] Patient input form
- [ ] Prediction result
- [ ] Probability visualization
- [ ] Explanation display
- [ ] Prediction history
- [ ] Tailwind styling

## Deployment

- [ ] Docker configuration
- [ ] docker-compose
- [ ] Environment configuration
- [ ] End-to-end integration
- [ ] Application testing

---

# 36. Current Logistic Regression Baseline

The current baseline was evaluated using Stratified 5-Fold Cross-Validation.

```text
Mean Accuracy     : 0.7560
Mean AUROC        : 0.7717
Mean Sensitivity  : 0.4811
Mean Specificity  : 0.8867
```

These values are the **current project baseline**.

The ANN will be evaluated using the same validation methodology and core metrics.

---

# 37. Future ML Extension

The PRD allows a possible future survival-analysis extension.

The current MVP remains focused on **binary mortality classification**.

A time-to-event/survival-analysis component is considered an optional extension after the core prediction system is completed.

---

# 38. Disclaimer

This project is an **academic/research and clinical decision-support prototype**.

The predicted probability is generated by a machine-learning model and should be interpreted within the limitations of the dataset, preprocessing methodology, validation results, calibration performance, and deployment environment.

The system:

- Is not a diagnosis.
- Does not replace a physician.
- Does not autonomously determine treatment.
- Should not be the sole basis for discharge decisions.
- Should not be interpreted as a guarantee of an individual patient's outcome.

Clinical decisions remain the responsibility of qualified healthcare professionals.

---

# 39. License

Add the project's chosen open-source or academic license here when the repository license is finalized.

---

# 40. Project Summary

**Heart Failure Mortality Risk Predictor (ANN)** combines:

```text
Advanced Data Science
        +
Deep Learning
        +
Probability Calibration
        +
Explainable Prediction
        +
FastAPI
        +
React
        +
PostgreSQL
```

The final system is intended to provide a validated, probability-first mortality-risk estimate through a secure full-stack clinical decision-support application.