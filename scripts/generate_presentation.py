"""
scripts/generate_presentation.py
================================
Generates the official Phase 10 Academic Presentation Deck:
`docs/Heart_Failure_Mortality_Risk_Predictor_Presentation.pptx`
using python-pptx with professional clinical/academic styling.
"""

import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
PPTX_PATH = DOCS_DIR / "Heart_Failure_Mortality_Risk_Predictor_Presentation.pptx"

# Color Palette (Academic / Medical Theme)
COLOR_NAVY = RGBColor(15, 23, 42)        # #0F172A (Deep Slate)
COLOR_PRIMARY = RGBColor(30, 58, 138)     # #1E3A8A (Medical Navy)
COLOR_ACCENT = RGBColor(37, 99, 235)      # #2563EB (Vibrant Blue)
COLOR_TEXT_DARK = RGBColor(30, 41, 59)    # #1E293B
COLOR_TEXT_MUTED = RGBColor(100, 116, 139) # #64748B
COLOR_BG_LIGHT = RGBColor(248, 250, 252)  # #F8FAFC
COLOR_WHITE = RGBColor(255, 255, 255)
COLOR_CARD_BORDER = RGBColor(226, 232, 240)
COLOR_SUCCESS = RGBColor(22, 101, 52)     # #166534
COLOR_WARNING = RGBColor(180, 83, 9)      # #B45309

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

def add_header(slide, title_text, category_text="HEART FAILURE MORTALITY RISK PREDICTOR"):
    # Category / Super-title
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.4))
    tf_c = cat_box.text_frame
    tf_c.word_wrap = True
    tf_c.margin_left = tf_c.margin_top = tf_c.margin_right = tf_c.margin_bottom = 0
    p_c = tf_c.paragraphs[0]
    p_c.text = category_text.upper()
    p_c.font.size = Pt(11)
    p_c.font.bold = True
    p_c.font.color.rgb = COLOR_ACCENT

    # Main Slide Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.7))
    tf_t = title_box.text_frame
    tf_t.word_wrap = True
    tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0
    p_t = tf_t.paragraphs[0]
    p_t.text = title_text
    p_t.font.size = Pt(24)
    p_t.font.bold = True
    p_t.font.color.rgb = COLOR_NAVY

    # Decorative Rule Line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(0.02))
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_CARD_BORDER
    line.line.color.rgb = COLOR_CARD_BORDER

def add_card(slide, left, top, width, height, title, items, bg_color=COLOR_BG_LIGHT, border_color=COLOR_CARD_BORDER):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1)

    tb = slide.shapes.add_textbox(left + Inches(0.3), top + Inches(0.25), width - Inches(0.6), height - Inches(0.5))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    if title:
        p_title = tf.paragraphs[0]
        p_title.text = title
        p_title.font.size = Pt(16)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_PRIMARY
        p_title.space_after = Pt(10)
        first_item = True
    else:
        first_item = False

    for item in items:
        if first_item and title:
            p = tf.add_paragraph()
        elif not title and first_item:
            p = tf.paragraphs[0]
            first_item = False
        else:
            p = tf.add_paragraph()
            first_item = False
        p.text = f"•  {item}"
        p.font.size = Pt(13)
        p.font.color.rgb = COLOR_TEXT_DARK
        p.space_after = Pt(8)

# ==============================================================================
# SLIDE 1: TITLE SLIDE
# ==============================================================================
slide1 = prs.slides.add_slide(blank_layout)
# Background fill
bg1 = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
bg1.fill.solid()
bg1.fill.fore_color.rgb = COLOR_NAVY
bg1.line.fill.background()

tb_title = slide1.shapes.add_textbox(Inches(1.2), Inches(2.0), Inches(11.0), Inches(3.2))
tf = tb_title.text_frame
tf.word_wrap = True
p0 = tf.paragraphs[0]
p0.text = "CLINICAL MACHINE LEARNING RESEARCH & DEPLOYMENT"
p0.font.size = Pt(13)
p0.font.bold = True
p0.font.color.rgb = RGBColor(96, 165, 250)
p0.space_after = Pt(12)

p1 = tf.add_paragraph()
p1.text = "Heart Failure Mortality Risk Predictor"
p1.font.size = Pt(36)
p1.font.bold = True
p1.font.color.rgb = COLOR_WHITE
p1.space_after = Pt(12)

p2 = tf.add_paragraph()
p2.text = "A Multi-Phase Scientific Investigation of Deep Neural Networks vs. Classical Generalized Linear Models in Tabular Clinical Risk Stratification"
p2.font.size = Pt(16)
p2.font.color.rgb = RGBColor(203, 213, 225)
p2.space_after = Pt(30)

p3 = tf.add_paragraph()
p3.text = "Final Academic Project Defense & Production System Presentation  |  November 2026"
p3.font.size = Pt(13)
p3.font.color.rgb = RGBColor(148, 163, 184)


# ==============================================================================
# SLIDE 2: CLINICAL BACKGROUND & THE HEALTHCARE PROBLEM
# ==============================================================================
slide2 = prs.slides.add_slide(blank_layout)
add_header(slide2, "Clinical Problem Space: Heart Failure Decompensation")

add_card(slide2, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
         "Epidemiological Burden",
         [
             "Heart failure affects over 64 million individuals globally with high 30-day readmission and mortality rates.",
             "Clinical decompensation is multifactorial, involving progressive left ventricular systolic failure and neurohormonal activation.",
             "Cardiorenal Syndrome: Renal hypoperfusion dramatically exacerbates cardiac strain, producing sudden hemodynamic deterioration.",
             "Need for early, objective admission risk stratification using routine, non-invasive physiological parameters."
         ])

add_card(slide2, Inches(6.9), Inches(1.8), Inches(5.6), Inches(5.0),
         "Clinical Decision Support Objectives",
         [
             "Formulate a probabilistic decision-support tool to assist attending cardiologists during hospital admission triage.",
             "Identify patients at severe mortality risk early to prioritize intensive hemodynamic monitoring and pharmacotherapy.",
             "Provide continuous calibrated probability estimates alongside confidence tiers, avoiding arbitrary binary classification.",
             "Strict Clinical Safeguard: Strictly designated as an educational prototype; not cleared as an autonomous diagnostic device."
         ])


# ==============================================================================
# SLIDE 3: DATASET & SCIENTIFIC HYGIENE (EXCLUSION OF 'TIME')
# ==============================================================================
slide3 = prs.slides.add_slide(blank_layout)
add_header(slide3, "Dataset Integrity & The 'Time' Leakage Trap")

add_card(slide3, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
         "UCI Heart Failure Clinical Cohort",
         [
             "Collected by Tanvir Ahmad et al. (Allied Hospital, Faisalabad, Pakistan; Chicco & Jurman, 2020).",
             "Cohort Size: 299 patients with advanced heart failure (NYHA Classes III–IV).",
             "Binary Endpoint: DEATH_EVENT during the observation period.",
             "Class Distribution: 96 deceased (32.11%) vs. 203 survivors (67.89%).",
             "11 Pre-admission Clinical Features: Age, Anaemia, CPK, Diabetes, EF, Hypertension, Platelets, Creatinine, Sodium, Sex, Smoking."
         ])

add_card(slide3, Inches(6.9), Inches(1.8), Inches(5.6), Inches(5.0),
         "Post-Baseline Target Leakage ('Time')",
         [
             "The raw dataset includes 'time' (follow-up duration in days, ranging from 4 to 285 days).",
             "Scientific Audit Finding: 'time' exhibits severe survival leakage (r = -0.53 with death). Observation ceases at death.",
             "Including 'time' creates an artificial, clinically useless model with inflated AUROC > 85%.",
             "Strict Rule: 'time' is completely excluded. All inference is strictly conditioned on admission-time clinical parameters."
         ])


# ==============================================================================
# SLIDE 4: THE CENTRAL SCIENTIFIC QUESTION
# ==============================================================================
slide4 = prs.slides.add_slide(blank_layout)
add_header(slide4, "The Central Research Question")

add_card(slide4, Inches(0.8), Inches(1.8), Inches(11.733), Inches(2.2),
         "Core Hypothesis & Clinical Motivation",
         [
             "Hypothesis: Does a deep Artificial Neural Network (PyTorch MLP) capture non-linear biomarker interactions to outperform a classical Logistic Regression baseline on small tabular clinical data?",
             "Contemporary machine learning literature frequently claims deep learning superiority without rigorous leak-free benchmarking against regularized generalized linear models on tabular medical data."
         ])

add_card(slide4, Inches(0.8), Inches(4.3), Inches(5.6), Inches(2.5),
         "Theoretical ANN Advantage",
         [
             "Universal function approximation.",
             "Potential to learn non-linear threshold effects (e.g., severe EF drop < 30%).",
             "Automatic discovery of feature interactions without manual polynomial expansion."
         ])

add_card(slide4, Inches(6.9), Inches(4.3), Inches(5.6), Inches(2.5),
         "Tabular Reality Constraints",
         [
             "Small sample size (n = 299, 96 events).",
             "High parameter-to-sample ratio risks overfitting noise.",
             "Absence of spatial or sequential inductive priors found in computer vision or NLP."
         ])


# ==============================================================================
# SLIDE 5: EXPLORATORY DATA ANALYSIS & BIOMARKER DYNAMICS
# ==============================================================================
slide5 = prs.slides.add_slide(blank_layout)
add_header(slide5, "Exploratory Data Analysis: Key Risk Drivers")

add_card(slide5, Inches(0.8), Inches(1.8), Inches(3.7), Inches(5.0),
         "1. Ejection Fraction (EF)",
         [
             "Normal: 55% - 70%.",
             "In cohort: 14% - 80% (mean 38.08%).",
             "Strongest inverse predictor of mortality.",
             "Deceased patients exhibit mean EF of 33.47% vs. 40.27% for survivors.",
             "Steep non-linear mortality surge when EF drops below 30%."
         ])

add_card(slide5, Inches(4.8), Inches(1.8), Inches(3.7), Inches(5.0),
         "2. Serum Creatinine",
         [
             "Normal: 0.7 - 1.2 mg/dL.",
             "In cohort: 0.5 - 9.4 mg/dL (mean 1.39 mg/dL).",
             "Strongest positive predictor of mortality.",
             "Deceased patients exhibit mean Creatinine of 1.84 mg/dL vs 1.18 mg/dL.",
             "Reflects Cardiorenal Syndrome type 1/2 decompensation."
         ])

add_card(slide5, Inches(8.8), Inches(1.8), Inches(3.7), Inches(5.0),
         "3. Age & Comorbidities",
         [
             "Age: Mean 60.83 years (40 to 95). Modest positive risk correlation.",
             "Serum Sodium: Modest inverse correlation (hyponatremia marker).",
             "Lifestyle & Comorbidities: Diabetes, sex, and smoking showed weak bivariate correlations in this end-stage heart failure cohort."
         ])


# ==============================================================================
# SLIDE 6: EXPERIMENTAL METHODOLOGY: 5-FOLD CV ARCHITECTURE
# ==============================================================================
slide6 = prs.slides.add_slide(blank_layout)
add_header(slide6, "Rigorous Leak-Free Validation Methodology")

add_card(slide6, Inches(0.8), Inches(1.8), Inches(11.733), Inches(5.0),
         "5-Fold Stratified Cross-Validation Protocol",
         [
             "Stratified K-Fold Split: n_splits = 5, shuffle = True, random_state = 42. Exactly 19 or 20 mortality events per fold.",
             "Leak-Free Preprocessing: StandardScaler is fitted strictly within training splits (folds 1-4) and applied to test fold 5. Zero global leakage.",
             "Multi-Metric Evaluation Protocol:",
             "  - Discrimination: Area Under the Receiver Operating Characteristic (AUROC).",
             "  - Probability Calibration: Brier Score (mean squared error of probabilities) and Expected Calibration Error (ECE).",
             "  - Information Theoretic Loss: Out-of-fold Binary Cross-Entropy / Log Loss.",
             "Statistical Significance Testing: Non-parametric paired Wilcoxon Signed-Rank Tests across all 5 test folds.",
             "Frozen Benchmark Guarantee: Canonical Logistic Regression benchmark established once and strictly frozen across all phases."
         ])


# ==============================================================================
# SLIDE 7: CANONICAL BASELINE: LOGISTIC REGRESSION
# ==============================================================================
slide7 = prs.slides.add_slide(blank_layout)
add_header(slide7, "Canonical Production Baseline: Logistic Regression")

add_card(slide7, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
         "Model Architecture & Formulation",
         [
             "scikit-learn Pipeline: StandardScaler + LogisticRegression.",
             "Solver: L-BFGS optimization, L2 penalty (Ridge regularization, C = 1.0).",
             "Mathematical Form: z = w0 + sum(wi * xi); P(y=1) = 1 / (1 + exp(-z)).",
             "Total Parameters: Exactly 12 (11 feature coefficients + 1 bias term).",
             "Complete Interpretability: Coefficients directly map to odds ratios.",
             "Checkpoint: models/logistic_regression_pipeline.joblib."
         ])

add_card(slide7, Inches(6.9), Inches(1.8), Inches(5.6), Inches(5.0),
         "Canonical Validation Performance",
         [
             "Mean AUROC: 77.17% ± 5.51% across 5 folds.",
             "Fold-wise AUROC: Fold 1: 72.89%, Fold 2: 83.95%, Fold 3: 71.32%, Fold 4: 83.95%, Fold 5: 73.73%.",
             "Mean Brier Score: 0.1777 (demonstrates strong probabilistic accuracy).",
             "Mean Log Loss: 0.5437.",
             "Dominant Coefficients: Ejection Fraction (-0.79), Serum Creatinine (+0.67), Age (+0.36).",
             "Role: Canonical production baseline for all comparative research."
         ])


# ==============================================================================
# SLIDE 8: PRODUCTION NEURAL NETWORK ARCHITECTURE
# ==============================================================================
slide8 = prs.slides.add_slide(blank_layout)
add_header(slide8, "Production Deep Learning Checkpoint (PyTorch)")

add_card(slide8, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
         "Layer-by-Layer Architecture",
         [
             "Input Layer: 11 scaled features via models/ann_scaler.joblib.",
             "Hidden Layer 1: Linear(11 -> 64) -> 768 params + ReLU + Dropout(0.2).",
             "Hidden Layer 2: Linear(64 -> 32) -> 2,080 params + ReLU + Dropout(0.2).",
             "Output Layer: Linear(32 -> 1) -> 33 params -> Unconstrained raw logit.",
             "Total Trainable Parameters: Exactly 2,881 float32 parameters.",
             "Loss Formulation: BCEWithLogitsLoss for numerical stability.",
             "Inference Sigmoid: P(y=1) = torch.sigmoid(raw_logit).",
             "Checkpoint: models/ann_model.pth (Verified in Phase 10)."
         ])

add_card(slide8, Inches(6.9), Inches(1.8), Inches(5.6), Inches(5.0),
         "Validation Performance & Identity",
         [
             "Mean AUROC: 76.22% ± 4.90% across 5 folds.",
             "Mean Brier Score: 0.1804.",
             "Mean Log Loss: 0.5415.",
             "Exact Identity: Distinguishable from Research Arch B (209 params, 11->16->1) and Arch C (929 params, 11->32->16->1).",
             "Deployment Status: Verified and frozen in FastAPI backend (/predict-ann).",
             "Inference Parity: 100% bit-level agreement between direct PyTorch forward pass and FastAPI test client responses."
         ])


# ==============================================================================
# SLIDE 9: SUMMARY OF THE 8 RESEARCH PHASES
# ==============================================================================
slide9 = prs.slides.add_slide(blank_layout)
add_header(slide9, "The 8 Research Phases of ANN Optimization")

add_card(slide9, Inches(0.8), Inches(1.8), Inches(3.7), Inches(5.0),
         "Phases 1 – 3: Architecture & Tuning",
         [
             "Phase 1: Exploratory MLPs (Arch A, B, C, D). Established Arch B (11->16->1) benchmark (AUROC 76.11%).",
             "Phase 2: Loss function & optimizer search. BCEWithLogitsLoss improved gradient stability.",
             "Phase 3: Probability calibration (Platt/Temperature) & threshold tuning (Youden's J = 0.35)."
         ])

add_card(slide9, Inches(4.8), Inches(1.8), Inches(3.7), Inches(5.0),
         "Phases 4 – 6: Audits & Diagnosis",
         [
             "Phase 4: External dataset feasibility audit. Proved clinical incompatibility with MIMIC/Framingham.",
             "Phase 5: Reproducibility audit & deterministic seed verification across PyTorch/scikit-learn.",
             "Phase 6: Performance diagnosis: identified tabular small-sample capacity bottleneck."
         ])

add_card(slide9, Inches(8.8), Inches(1.8), Inches(3.7), Inches(5.0),
         "Phases 7 – 8: Hybrid Architectures",
         [
             "Phase 7: Wide & Deep ANN + log1p biomarker preprocessing (AUROC 76.89%).",
             "Phase 8: L-BFGS optimizer & feature ablation: removing diabetes/sex/smoking raised 8-feat ANN to 77.68%, but matched 8-feat LR achieved 78.10% (p = 0.6250)."
         ])


# ==============================================================================
# SLIDE 10: QUANTITATIVE BENCHMARK & SIGNIFICANCE MATRIX
# ==============================================================================
slide10 = prs.slides.add_slide(blank_layout)
add_header(slide10, "Empirical Benchmark: ANN vs. Logistic Regression")

# Add a comparison table
rows = 6
cols = 6
top_t = Inches(1.8)
left_t = Inches(0.8)
width_t = Inches(11.733)
height_t = Inches(3.2)

table_shape = slide10.shapes.add_table(rows, cols, left_t, top_t, width_t, height_t)
table = table_shape.table

headers = ["Model Designation", "Parameters", "AUROC (Mean ± Std)", "Brier Score", "Log Loss", "Wilcoxon vs LR"]
for i, h in enumerate(headers):
    cell = table.cell(0, i)
    cell.text = h
    cell.fill.solid()
    cell.fill.fore_color.rgb = COLOR_PRIMARY
    p = cell.text_frame.paragraphs[0]
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE

data = [
    ["Logistic Regression (Baseline)", "12", "77.17% ± 5.51%", "0.1777", "0.5437", "Reference"],
    ["Production ANN (11->64->32->1)", "2,881", "76.22% ± 4.90%", "0.1804", "0.5415", "p = 0.6250 (NS)"],
    ["Research Arch B (11->16->1)", "209", "76.11% ± 6.22%", "0.1804", "0.5415", "p = 0.6250 (NS)"],
    ["Research Arch C (11->32->16->1)", "929", "76.54% ± 5.10%", "0.1832", "0.5512", "p = 0.8125 (NS)"],
    ["Phase 8 Wide & Deep (8 Features)", "90", "77.68% ± 4.80%", "0.1788", "0.5390", "Matched LR: 78.10%"]
]

for row_idx, row_data in enumerate(data):
    for col_idx, text_val in enumerate(row_data):
        cell = table.cell(row_idx + 1, col_idx)
        cell.text = text_val
        cell.fill.solid()
        cell.fill.fore_color.rgb = COLOR_WHITE if row_idx % 2 == 0 else COLOR_BG_LIGHT
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT_DARK

add_card(slide10, Inches(0.8), Inches(5.3), Inches(11.733), Inches(1.6),
         "Core Scientific Conclusion",
         [
             "Rigorous empirical testing confirms that Deep Neural Networks DO NOT outperform Logistic Regression on this dataset.",
             "Statistical significance tests confirm p = 0.6250 (null hypothesis cannot be rejected).",
             "Logistic Regression matches neural network discrimination while requiring 240x fewer parameters."
         ])


# ==============================================================================
# SLIDE 11: PROBABILITY CALIBRATION & THRESHOLD OPTIMIZATION
# ==============================================================================
slide11 = prs.slides.add_slide(blank_layout)
add_header(slide11, "Calibration & Clinical Decision Thresholds")

add_card(slide11, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
         "Probability Calibration Dynamics",
         [
             "Raw Sigmoid Probabilities: Production ANN exhibits an Expected Calibration Error (ECE) of ~0.08.",
             "Temperature Scaling vs. Platt Scaling: Post-hoc calibration offered minimal gain over well-regularized cross-entropy logits.",
             "Brier Score Comparison: LR (0.1777) vs. ANN (0.1804). Both models exhibit excellent calibration in the low-to-moderate risk bands (< 0.50).",
             "Clinical Risk Tiers:",
             "  - Low Risk: P < 0.30 (Green badge)",
             "  - Moderate Risk: 0.30 <= P < 0.60 (Amber badge)",
             "  - High Risk: P >= 0.60 (Red badge)"
         ])

add_card(slide11, Inches(6.9), Inches(1.8), Inches(5.6), Inches(5.0),
         "Optimal Decision Cutoff (Youden's J)",
         [
             "Default Threshold (tau = 0.50):",
             "  - Sensitivity: 48.9%",
             "  - Specificity: 89.2%",
             "  - High false-negative rate in screening.",
             "Youden's J Optimization (tau* = 0.35 - 0.38):",
             "  - Sensitivity surges to 72.9% (+24.0%).",
             "  - Specificity balances at 73.4%.",
             "  - Minimizes missed high-risk decompensation events without excessive false alarms."
         ])


# ==============================================================================
# SLIDE 12: SOFTWARE ARCHITECTURE & SYSTEMS ENGINEERING
# ==============================================================================
slide12 = prs.slides.add_slide(blank_layout)
add_header(slide12, "Full-Stack Software Architecture")

add_card(slide12, Inches(0.8), Inches(1.8), Inches(3.7), Inches(5.0),
         "FastAPI Backend Gateway",
         [
             "High-performance asynchronous REST API.",
             "Pydantic v2 strict schema boundaries preventing malformed tensors.",
             "Dual-Model Endpoints: /predict (LR) and /predict-ann (PyTorch).",
             "Lifespan startup hooks: Alembic migrations, database verification, and admin seeding."
         ])

add_card(slide12, Inches(4.8), Inches(1.8), Inches(3.7), Inches(5.0),
         "Dual-Engine Database Layer",
         [
             "Production: Render Cloud Managed PostgreSQL (clinical schema).",
             "Development: Automatic 0.5s socket probe with seamless fallback to SQLite (clinical_local.db) in WAL mode.",
             "SQLAlchemy 2.0 ORM with thread-safe connection pooling."
         ])

add_card(slide12, Inches(8.8), Inches(1.8), Inches(3.7), Inches(5.0),
         "React 18 + Vite Frontend",
         [
             "Responsive Tailwind CSS UI.",
             "Interactive Dual-Model Selector: toggle between LR and ANN.",
             "Real-time risk tier gauges and confidence displays.",
             "Persistent clinical safety disclaimer banner across all views."
         ])


# ==============================================================================
# SLIDE 13: CYBERSECURITY & ACCESS CONTROL
# ==============================================================================
slide13 = prs.slides.add_slide(blank_layout)
add_header(slide13, "Cybersecurity, IDOR Protection & Governance")

add_card(slide13, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
         "Authentication & Session Defense",
         [
             "Argon2id Password Hashing: State-of-the-art resistance to GPU/ASIC brute force (memory_cost=64MB, time_cost=3).",
             "JSON Web Tokens (JWT): Signed with HS256, 12-hour expiration.",
             "Brute-Force Rate Limiting: 5 consecutive failed login attempts triggers exponential lockout cooldown.",
             "Administrative Oversight: Mandatory administrative verification before new physicians can access clinical tools."
         ])

add_card(slide13, Inches(6.9), Inches(1.8), Inches(5.6), Inches(5.0),
         "IDOR Prevention & Patient Privacy",
         [
             "Insecure Direct Object Reference (IDOR) Elimination: doctor_id is strictly derived from the verified JWT, never trusted from client payloads.",
             "Tenant Scoping: All assessment queries enforce doctor_id == current_doctor.doctor_id.",
             "Information Leakage Mitigation: Unauthorized ID queries return HTTP 404 (Not Found) rather than 403, preventing enumeration.",
             "Zero PII: Stores only clinical measurements and non-identifiable tracking IDs (e.g., PT-2026-001)."
         ])


# ==============================================================================
# SLIDE 14: CLOUD DEPLOYMENT & PRODUCTION READINESS
# ==============================================================================
slide14 = prs.slides.add_slide(blank_layout)
add_header(slide14, "Cloud Deployment & Production Verification")

add_card(slide14, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
         "Single-Service Cloud Architecture",
         [
             "Platform: Render Cloud Web Service (heart-failure-predictor).",
             "Unified Static Serving: FastAPI serves compiled React production assets (frontend/dist) directly from the application container.",
             "Zero CORS Overhead: Frontend and backend share the same origin in production.",
             "Continuous Database Binding: Managed PostgreSQL connection string injected via DATABASE_URL.",
             "Alembic auto-migration on container startup guarantees schema synchronization."
         ])

add_card(slide14, Inches(6.9), Inches(1.8), Inches(5.6), Inches(5.0),
         "Phase 10 Production Verification",
         [
             "Inference Parity: 100% bit-level agreement between standalone Python execution and FastAPI endpoints across 5 patient profiles.",
             "Input Boundary Enforcement: Pydantic rejects out-of-bounds parameters (HTTP 422).",
             "Database Partitioning Status:",
             "  - SQLite Local Fallback: PASSED.",
             "  - Local PostgreSQL 5433: BLOCKED / NOT TESTED (daemon offline).",
             "  - Render Cloud PostgreSQL: BLOCKED / NOT TESTED (network isolation in sandbox)."
         ])


# ==============================================================================
# SLIDE 15: CLINICAL GOVERNANCE & ETHICAL BOUNDARIES
# ==============================================================================
slide15 = prs.slides.add_slide(blank_layout)
add_header(slide15, "Clinical Governance, Ethics & Limitations")

add_card(slide15, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
         "Cohort & Generalization Constraints",
         [
             "Single-Center Demographics: Cohort originates entirely from Allied Hospital in Faisalabad, Pakistan.",
             "Under-representation of non-South Asian ethnicities and diverse dietary/pharmacological regimens.",
             "Disease Severity Bias: Patients presented with advanced heart failure (NYHA III–IV); cannot be generalized to early-stage outpatient screening.",
             "Sample Size Limitation: n = 299 restricts statistical power to detect small non-linear interaction effects."
         ])

add_card(slide15, Inches(6.9), Inches(1.8), Inches(5.6), Inches(5.0),
         "Ethical & Regulatory Declarations",
         [
             "Educational Prototype Only: Explicitly not cleared or approved by the FDA, EMA, or national health authorities.",
             "Never Autonomous: Designed strictly to augment, never replace, the diagnostic judgment of a qualified cardiologist.",
             "Model Card Compliance: Complete model card documented following Mitchell et al. (2019) standards.",
             "Transparent AI: Dual-model toggle provides physicians with interpretable odds ratios alongside neural predictions."
         ])


# ==============================================================================
# SLIDE 16: CONCLUSION & FUTURE RESEARCH ROADMAP
# ==============================================================================
slide16 = prs.slides.add_slide(blank_layout)
add_header(slide16, "Conclusion & Project Summary")

add_card(slide16, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
         "Key Project Takeaways",
         [
             "1. Deep Learning is Not a Silver Bullet: Classical regularized Logistic Regression matches deep neural network performance on small tabular clinical datasets.",
             "2. The Vital Need for Empirical Rigor: Without leak-free preprocessing and statistical significance testing, complexity is easily mistaken for progress.",
             "3. Engineering Resilience: A full-stack clinical platform with Argon2id auth, IDOR protections, and intelligent database fallback is ready for educational deployment."
         ])

add_card(slide16, Inches(6.9), Inches(1.8), Inches(5.6), Inches(5.0),
         "Future Research Roadmap",
         [
             "Multi-Center External Validation: Prospective evaluation across international cardiology cohorts.",
             "Continuous Longitudinal Modeling: Integrating repeated biomarker measurements over time.",
             "Explainable AI (XAI): Incorporating KernelSHAP and Integrated Gradients for local feature attribution in clinical UI.",
             "Thank you! Questions and technical discussion are welcomed."
         ])

prs.save(PPTX_PATH)
print(f"Successfully generated PowerPoint presentation: {PPTX_PATH}")
