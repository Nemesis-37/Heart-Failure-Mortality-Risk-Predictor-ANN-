# Project Viva & Academic Defense Questions (with Complete Model Answers)

**Project:** Heart Failure Mortality Risk Predictor  
**Domain:** Clinical Machine Learning, Deep Learning, Software Architecture, and Healthcare Ethics  
**Target Examination:** Academic Project Defense / Technical Viva Voce  
**Date:** November 2026

---

## CATEGORY 1: CLINICAL DOMAIN & DATASET INTEGRITY

### Q1: What dataset was used for this project, and what are its key clinical characteristics?
**Answer:**  
The project uses the UCI Heart Failure Clinical Records dataset, compiled by Tanvir Ahmad et al. (Allied Hospital, Faisalabad, Pakistan) and published by Davide Chicco and Giuseppe Jurman (BMC Medical Informatics and Decision Making, 2020). It consists of **299 patient records** diagnosed with heart failure (NYHA classes III–IV). There are **96 mortality events (32.11%)** and **203 survivals (67.89%)**, monitored for the target binary endpoint `DEATH_EVENT`.

---

### Q2: Why did you explicitly exclude the `time` feature from all machine learning models?
**Answer:**  
The variable `time` indicates the duration of the patient follow-up period in days. In survival analysis, patients who die leave observation at the moment of death, whereas survivors remain observed for the full trial duration. This creates a severe **post-baseline target leakage** and survivor bias (bivariate correlation with death is $-0.53$). While including `time` artificially inflates AUROC above $85\%$, it is clinically useless because follow-up duration cannot be known at the moment of hospital admission when a clinician needs to assess risk. Excluding `time` guarantees realistic, admission-time prospective validity.

---

### Q3: Which biological features provide the strongest predictive information for mortality?
**Answer:**  
Empirical feature importance across both models identifies two dominant pathophysiological drivers:
1. **Left Ventricular Ejection Fraction (EF):** Strong inverse relationship with mortality. Values below $30\%$ indicate severe systolic dysfunction and poor forward cardiac output.
2. **Serum Creatinine:** Strong direct relationship with mortality. Elevated creatinine indicates impaired renal glomerular filtration (cardiorenal syndrome), a primary prognostic indicator of heart failure decompensation.
3. **Age:** Secondary risk factor reflecting accumulated vascular stiffness and biological senescence.

---

### Q4: Why did variables like diabetes, sex, and smoking show low predictive contribution in your feature ablation experiments?
**Answer:**  
In our Phase 8 feature ablation experiments, removing `diabetes`, `sex`, and `smoking` marginally improved validation AUROC from $76.89\%$ to $77.68\%$. This does **not** mean these factors are biologically irrelevant to cardiovascular disease. Rather, in a small sample of 299 patients with advanced end-stage heart failure (NYHA III–IV), the acute hemodynamic collapse caused by severe systolic failure (low EF) and renal shutdown (high creatinine) completely overwhelms the statistical signal of chronic lifestyle and demographic risk factors.

---

## CATEGORY 2: MACHINE LEARNING & DEEP LEARNING METHODOLOGY

### Q5: What is the exact architecture of your production Artificial Neural Network?
**Answer:**  
The production ANN checkpoint (`models/ann_model.pth`) is a feedforward deep neural network ($11 \to 64 \to 32 \to 1$) consisting of **2,881 trainable float32 parameters**:
- **Input Layer:** 11 normalized clinical features.
- **Hidden Layer 1:** `Linear(11, 64)` (768 params) + `ReLU()` + `Dropout(p=0.2)`.
- **Hidden Layer 2:** `Linear(64, 32)` (2,080 params) + `ReLU()` + `Dropout(p=0.2)`.
- **Output Layer:** `Linear(32, 1)` (33 params), yielding an unconstrained logit.
- **Normalization:** Evaluated with `torch.sigmoid(logit)` to produce calibrated probabilities $\in [0, 1]$.

---

### Q6: How does the production ANN compare against the canonical Logistic Regression model?
**Answer:**  
On rigorous 5-fold stratified cross-validation using identical splits:
- **Canonical Logistic Regression (12 parameters):** Mean AUROC = **$77.17\% \pm 5.51\%$**, Brier Score = **0.1777**, Log Loss = **0.5437**.
- **Production ANN (2,881 parameters):** Mean AUROC = **$76.22\% \pm 4.90\%$**, Brier Score = **0.1804**, Log Loss = **0.5415**.
- **Wilcoxon Signed-Rank Test:** Yields $p = 0.6250$, confirming no statistically significant difference in discrimination. Logistic Regression matches the deep network while offering complete interpretability, deterministic behavior, and 240-fold lower parameter complexity.

---

### Q7: Why didn't the Artificial Neural Network significantly outperform Logistic Regression?
**Answer:**  
This illustrates a fundamental tenet of statistical learning theory:
1. **Sample Size vs Capacity:** The dataset contains only 299 samples and 96 positive events. Deep learning architectures thrive when given thousands or millions of samples where high capacity enables learning hierarchical representations. With $n=299$, high-capacity networks tend to overfit the training fold noise unless heavily constrained by dropout and weight decay.
2. **Tabular Nature of Data:** Unlike images or audio, tabular features possess heterogeneous distributions, non-spatial semantics, and largely linear or monotonic risk relationships with the target. When biological risk gradients are primarily additive, generalized linear models represent the true data generating process effectively.

---

### Q8: What was the Wide & Deep ANN architecture tested in Phase 7 and Phase 8?
**Answer:**  
The Wide & Deep ANN combined a linear wide branch with a non-linear deep branch:
$$\text{logit}(x) = (w_{\text{wide}}^T x + b_{\text{wide}}) + \text{MLP}_{\text{deep}}(x)$$
This guarantees that the network can collapse to a standard Logistic Regression model if the deep non-linear branch weights shrink to zero during regularized optimization. On 8 selected features, it achieved an AUROC of $77.68\%$, but matched 8-feature Logistic Regression achieved $78.10\%$, further reinforcing the sufficiency of linear representations.

---

### Q9: Why was `BCEWithLogitsLoss` preferred over applying `Sigmoid` inside the PyTorch forward pass?
**Answer:**  
Applying `nn.Sigmoid()` followed by standard `nn.BCELoss()` is prone to numerical underflow and overflow when computing log probabilities for extreme logits ($\log(\sigma(z))$ as $z \to -\infty$). `BCEWithLogitsLoss` combines the sigmoid and binary cross-entropy steps into a single mathematical layer using the log-sum-exp trick, ensuring numerical stability and preventing gradient explosion or truncation during backpropagation.

---

### Q10: How did you ensure there was no data leakage during preprocessing?
**Answer:**  
Preprocessing (specifically `StandardScaler`) was strictly fitted **inside** each training fold of the 5-fold cross-validation loop. The calculated training mean $\mu_{\text{train}}$ and standard deviation $\sigma_{\text{train}}$ were then used to transform both the validation fold and outer test fold. Computing scalers or transformations across the entire 299-patient dataset before splitting would contaminate training folds with global distributional statistics, artificially inflating evaluation metrics.

---

### Q11: What is the difference between model discrimination and model calibration?
**Answer:**  
- **Discrimination (AUROC):** The ability of the model to rank a randomly chosen deceased patient higher in risk than a surviving patient. It is invariant to monotonic probability shifts.
- **Calibration (Brier Score / ECE):** The degree to which predicted probabilities match empirical observed frequencies. If a model predicts a $30\%$ mortality risk for 100 patients, approximately 30 of those patients should actually experience the mortality event. In clinical decision support, calibration is vital because treatment thresholds depend on absolute risk values, not just relative rankings.

---

### Q12: What is Youden's $J$ statistic, and why is the optimal threshold different from 0.50?
**Answer:**  
Youden's Index ($J = \text{Sensitivity} + \text{Specificity} - 1$) identifies the optimal classification cutoff on the ROC curve by treating false positives and false negatives with equal geometric weight. In an imbalanced dataset with $32.11\%$ prevalence, the default $\tau = 0.50$ cutoff yields a low sensitivity of $48.9\%$. Lowering the threshold to $\tau^* = 0.35 - 0.38$ optimizes Youden's $J$, raising sensitivity to $72.9\%$ and ensuring that high-risk patients are not missed during screening.

---

## CATEGORY 3: SOFTWARE ARCHITECTURE & SYSTEMS ENGINEERING

### Q13: Explain your application's dual-database strategy and offline fallback mechanism.
**Answer:**  
In `backend/database/config.py`:
- In **Production (`APP_ENV=production`)**, the application strictly requires PostgreSQL (`postgresql+psycopg2`) connected via Render's `DATABASE_URL` and managed connection pools.
- In **Local Development (`APP_ENV=development`)**, the system executes a rapid 0.5-second non-blocking socket probe to `127.0.0.1:5433`. If local PostgreSQL is offline, it gracefully falls back to `sqlite:///clinical_local.db` with Write-Ahead Logging (WAL) enabled. This allows seamless offline development without crashing the application.

---

### Q14: How does the application protect against Insecure Direct Object References (IDOR)?
**Answer:**  
In `clinical/router.py`, the client never passes `doctor_id` as a trusted parameter. Instead:
1. The physician's identity is strictly decoded from the verified JWT access token in the `Authorization: Bearer` header.
2. Every database query enforces an explicit ownership predicate:
   ```python
   Assessment.assessment_id == assessment_id, Assessment.doctor_id == current_doctor.doctor_id
   ```
3. If an assessment ID exists but belongs to another physician, the API returns **HTTP 404 Not Found** (rather than 403), preventing attackers from enumerating valid patient assessment IDs across hospital tenants.

---

### Q15: Why did you choose Argon2id for password hashing?
**Answer:**  
Argon2id won the Password Hashing Competition (PHC) and is recommended by OWASP. Unlike classical MD5, SHA-256, or even standard bcrypt, Argon2id provides hybrid defense against both side-channel cache-timing attacks (Argon2i) and GPU/ASIC brute-force cracking (Argon2d) by requiring high memory allocation (`memory_cost=65536` KB, `time_cost=3`, `parallelism=4`).

---

### Q16: How is the React frontend deployed alongside the FastAPI backend on Render?
**Answer:**  
The application uses a unified single-service cloud architecture:
1. In `render-build.sh`, the frontend is compiled into production static assets (`frontend/dist`) using Vite.
2. In `main.py`, FastAPI mounts `/assets` via Starlette `StaticFiles`.
3. A catch-all route `/{full_path:path}` serves `index.html` for client-side React Router navigation while exempting API, health, and docs routes. This eliminates CORS overhead in production and reduces hosting costs.

---

### Q17: What is the purpose of Pydantic schema validation at the API boundary?
**Answer:**  
Pydantic v2 defines strict data models (`PatientData`) that validate input types and physiological boundaries (e.g., $1 \le \text{age} \le 120$, $1 \le \text{EF} \le 100$, binary fields $\in \{0, 1\}$). Out-of-bounds or malformed requests are arrested at the API boundary with HTTP 422 Unprocessable Entity, preventing corrupted vectors from reaching PyTorch tensors or causing silent NaN propagation in inference calculations.

---

## CATEGORY 4: ETHICAL AI & CLINICAL GOVERNANCE

### Q18: What are the primary demographic and clinical limitations of the training cohort?
**Answer:**  
The cohort consists of 299 patients treated at a single tertiary care center in Pakistan. It may not reflect the genetic, nutritional, or clinical comorbidity profile of global populations. Furthermore, all patients had severe heart failure (NYHA III–IV); thus, the model cannot be generalized to early-stage (NYHA I–II) outpatient screening without substantial risk of miscalibration.

---

### Q19: Why can't a non-significant $p$-value ($p = 0.6250$) be interpreted as "proving the models are identical"?
**Answer:**  
In classical hypothesis testing, failing to reject the null hypothesis ($H_0$) does not prove $H_0$ is true; it merely demonstrates that the observed data does not provide sufficient evidence to reject it at the chosen significance level ($\alpha = 0.05$). Claiming equivalence requires formalized equivalence testing (such as Two One-Sided Tests, TOST) within a pre-specified margin of clinical irrelevance ($\pm \delta$). We therefore report that superiority was not established, rather than claiming mathematical equivalence.

---

### Q20: What safeguards are implemented to prevent clinical misuse of this system?
**Answer:**  
1. **Persistent Disclaimer Banners:** Displayed on every frontend view and included in every API response payload (`notice: "Educational prototype only; not for medical decisions."`).
2. **Physician-Only Access:** Access is restricted to authenticated medical professionals rather than open unmonitored consumer access.
3. **Dual-Model Transparency:** Providing both linear and neural network outputs alongside confidence intervals encourages clinicians to inspect feature drivers rather than treating predictions as infallible black boxes.
