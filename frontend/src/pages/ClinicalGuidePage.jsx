import React, { useState } from 'react'

const PARAMETERS_DATA = [
  // ── Quantitative Features (6) ──────────────────────────────────────────────
  {
    id: 'ef',
    fieldName: 'ejection_fraction',
    name: 'Ejection Fraction (EF)',
    category: 'Quantitative',
    system: 'Hemodynamics',
    unit: '%',
    dataType: 'Continuous (Percentage)',
    datasetRange: '14% – 80% (Cohort mean: ~38.1%)',
    medicalNormal: '50% – 70%',
    criticalThreshold: '< 30% (Severe systolic dysfunction)',
    importance: 'High',
    shortSummary:
      'Percentage of blood pumped out of the ventricles with each cardiac contraction. One of the single strongest independent predictors of mortality in heart failure.',
    whatItRepresents:
      'The volumetric fraction of blood evacuated from the left ventricle with each contraction (Stroke Volume divided by End-Diastolic Volume). It is the primary physiological metric of cardiac systolic pump performance.',
    meaningInDataset:
      'In the UCI cohort of 299 heart failure patients, ejection fraction ranged between 14% and 80%, with a mean of 38.1%. A lower ejection fraction directly correlated with heightened 30-day mortality.',
    whyIncludedInModel:
      'Ejection fraction reflects whether heart failure presents with reduced ejection fraction (HFrEF, EF ≤ 40%) or preserved ejection fraction (HFpEF). Severely reduced contractile reserve directly limits cardiac output and peripheral tissue perfusion under hemodynamic stress.',
    datasetEncoding:
      'Recorded as a continuous numerical percentage (e.g., 38 for 38%). In the ML pipeline, it is normalized via z-score scaling before model ingestion.',
    referenceNote:
      'Clinically measured via transthoracic echocardiography, cardiac MRI, or radionuclide ventriculography. Values <40% indicate heart failure with reduced ejection fraction.',
  },
  {
    id: 'creatinine',
    fieldName: 'serum_creatinine',
    name: 'Serum Creatinine',
    category: 'Quantitative',
    system: 'Renal & Electrolytes',
    unit: 'mg/dL',
    dataType: 'Continuous (Laboratory assay)',
    datasetRange: '0.5 – 9.4 mg/dL (Cohort mean: ~1.39 mg/dL)',
    medicalNormal: '0.7 – 1.3 mg/dL',
    criticalThreshold: '> 2.0 mg/dL (Severe renal impairment)',
    importance: 'High',
    shortSummary:
      'Byproduct of muscle metabolism filtered exclusively by renal glomeruli. Key clinical indicator of cardiorenal syndrome and kidney filtration rate.',
    whatItRepresents:
      'A chemical waste molecule generated from skeletal muscle creatine phosphate turnover. Because healthy kidneys filter creatinine at a constant rate without significant reabsorption, serum levels inversely reflect estimated Glomerular Filtration Rate (eGFR).',
    meaningInDataset:
      'In the UCI clinical records, creatinine values spanned 0.5 to 9.4 mg/dL with a median of ~1.1 mg/dL. Elevated serum creatinine was identified by Chicco & Jurman (2020) as the second strongest predictor of death alongside ejection fraction.',
    whyIncludedInModel:
      'Cardiorenal syndrome (Types 1 and 2) is a frequent and lethal complication where reduced cardiac output diminishes renal perfusion pressure, triggering acute-on-chronic kidney injury and fluid retention refractory to diuretics.',
    datasetEncoding:
      'Recorded as a continuous floating-point value in milligrams per deciliter (e.g., 1.1). Standardized via StandardScaler in the model pipeline.',
    referenceNote:
      'Elevated creatinine must be interpreted in light of baseline muscle mass and hydration status. Values >1.4 mg/dL warrant cardiorenal evaluation.',
  },
  {
    id: 'age',
    fieldName: 'age',
    name: 'Patient Age',
    category: 'Quantitative',
    system: 'Demographics',
    unit: 'years',
    dataType: 'Continuous / Discrete integer',
    datasetRange: '40 – 95 years (Cohort mean: ~60.8 years)',
    medicalNormal: 'Adult baseline',
    criticalThreshold: '≥ 70 years (Elevated cohort vulnerability)',
    importance: 'Moderate',
    shortSummary:
      'Chronological age of the patient at assessment time. Reflects physiological vascular stiffening, comorbid burden, and multi-organ functional reserve.',
    whatItRepresents:
      'Patient age in years at the time of clinical hospital admission or baseline assessment.',
    meaningInDataset:
      'The UCI cohort consists of adult cardiac patients aged 40 to 95 years, with an average age of ~60.8 years. Mortality incidence steadily increased with advanced patient age.',
    whyIncludedInModel:
      'Age is an established demographic risk factor across all cardiovascular prognostic indices (including Framingham and MAGGIC). Aging leads to arterial elastance deterioration, nephron loss, and diminished autonomic baroreflex sensitivity.',
    datasetEncoding:
      'Recorded as a continuous positive numerical value in years (e.g., 60). Standardized in both Logistic Regression and ANN inputs.',
    referenceNote:
      'Patients older than 70 years present higher vulnerability to polypharmacy adverse events and acute cardiogenic shock.',
  },
  {
    id: 'sodium',
    fieldName: 'serum_sodium',
    name: 'Serum Sodium',
    category: 'Quantitative',
    system: 'Renal & Electrolytes',
    unit: 'mEq/L',
    dataType: 'Continuous (Electrolyte assay)',
    datasetRange: '113 – 148 mEq/L (Cohort mean: ~136.6 mEq/L)',
    medicalNormal: '135 – 145 mEq/L',
    criticalThreshold: '< 130 mEq/L (Severe dilutional hyponatremia)',
    importance: 'Moderate',
    shortSummary:
      'Primary extracellular cation responsible for osmotic balance. Dilutional hyponatremia marks hyperactive neurohormonal compensation.',
    whatItRepresents:
      'The concentration of sodium cations (Na+) in circulating blood plasma, representing the chief determinant of extracellular fluid osmolality.',
    meaningInDataset:
      'Cohort measurements ranged from 113 to 148 mEq/L. Sub-normal sodium concentrations (<135 mEq/L) strongly correlated with acute decompensation and reduced survival.',
    whyIncludedInModel:
      'In congestive heart failure, diminished effective arterial blood volume triggers non-osmotic release of vasopressin (ADH) alongside excessive renin-angiotensin-aldosterone system (RAAS) activation, causing dilutional hyponatremia.',
    datasetEncoding:
      'Continuous numerical value in milliequivalents per liter (e.g., 137). In the input pipeline, it is normalized to standard normal distribution.',
    referenceNote:
      'Serum sodium <135 mEq/L defines hyponatremia. Values below 130 mEq/L indicate advanced hemodynamic compromise.',
  },
  {
    id: 'cpk',
    fieldName: 'creatinine_phosphokinase',
    name: 'Creatinine Phosphokinase (CPK)',
    category: 'Quantitative',
    system: 'Hematology & Enzymes',
    unit: 'mcg/L',
    dataType: 'Continuous (Enzyme concentration)',
    datasetRange: '23 – 7,861 mcg/L (Cohort median: ~250 mcg/L)',
    medicalNormal: '10 – 120 mcg/L',
    criticalThreshold: '> 500 mcg/L (Active myocyte injury / strain)',
    importance: 'Moderate',
    shortSummary:
      'Intracellular enzyme found in cardiac and skeletal muscle tissue. Elevation indicates active myocardial injury, ischemia, or muscular necrosis.',
    whatItRepresents:
      'The serum catalytic concentration of the creatine kinase (CK) enzyme, which catalyzes the reversible transfer of high-energy phosphate between ATP and phosphocreatine in muscle cells.',
    meaningInDataset:
      'In the dataset, CPK values exhibited significant positive skewness, ranging from 23 to 7,861 mcg/L with a median around 250 mcg/L.',
    whyIncludedInModel:
      'Acutely elevated CPK levels signal active myocyte disruption, recent myocardial infarction, severe peripheral muscular ischemia, or intense hemodynamic wall stress.',
    datasetEncoding:
      'Continuous numerical value in micrograms per liter (mcg/L). Scaled prior to linear regression and deep learning inference.',
    referenceNote:
      'Normal laboratory reference limits vary slightly across assays (typically 10–120 mcg/L). Extreme values (>1000 mcg/L) reflect severe rhabdomyolysis or major cardiac necrosis.',
  },
  {
    id: 'platelets',
    fieldName: 'platelets',
    name: 'Platelet Count',
    category: 'Quantitative',
    system: 'Hematology & Enzymes',
    unit: 'cells/µL',
    dataType: 'Continuous (Hematology cell count)',
    datasetRange: '25,100 – 850,000 cells/µL (Cohort mean: ~263,358)',
    medicalNormal: '150,000 – 450,000 cells/µL',
    criticalThreshold: '< 100,000 (Thrombocytopenia risk)',
    importance: 'Low-Moderate',
    shortSummary:
      'Circulating thrombocyte count essential for primary hemostasis. Altered in systemic congestion, splenomegaly, or endothelial distress.',
    whatItRepresents:
      'The concentration of circulating blood platelets (thrombocytes) per unit volume of blood, responsible for primary hemostatic plug formation and clot retraction.',
    meaningInDataset:
      'Observed values ranged from severe thrombocytopenia (25,100 cells/µL) to thrombocytosis (850,000 cells/µL), centering around a physiological mean of ~263,358 cells/µL.',
    whyIncludedInModel:
      'Both thrombocytopenia (frequently secondary to congestive splenomegaly or hepatic congestion) and elevated platelets (secondary to chronic systemic vascular inflammation) influence cardiovascular prognosis.',
    datasetEncoding:
      'Continuous absolute cell count (e.g., 260000). Standardized in model feature pipelines.',
    referenceNote:
      'Standard clinical reference range is 150,000 to 450,000 cells/µL in adult peripheral blood smears.',
  },

  // ── Binary & Demographic Features (5) ──────────────────────────────────────
  {
    id: 'anaemia',
    fieldName: 'anaemia',
    name: 'Anaemia',
    category: 'Binary & Demographic',
    system: 'Hematology & Enzymes',
    unit: 'Binary (0 / 1)',
    dataType: 'Categorical Binary Indicator',
    datasetRange: '0 (57% absence) or 1 (43% presence)',
    medicalNormal: '0 (Absence / Hemoglobin ≥ 12 g/dL)',
    criticalThreshold: '1 (Confirmed Anaemia, Hb < 12 g/dL)',
    importance: 'Moderate',
    shortSummary:
      'Reduction in circulating hemoglobin concentration (<12 g/dL). Impairs oxygen transport and intensifies compensatory cardiac strain.',
    whatItRepresents:
      'A clinical condition characterized by a deficit in the total number of circulating red blood cells or a reduced hemoglobin concentration in blood.',
    meaningInDataset:
      'In the UCI dataset, 43% of the patient cohort presented with diagnosed anaemia. Defined clinically in the cohort documentation as a blood hemoglobin level < 12 g/dL.',
    whyIncludedInModel:
      'Anaemia decreases peripheral oxygen delivery, requiring the heart to augment stroke volume and cardiac index (cardiorenal-anaemia syndrome), accelerating myocardial fatigue and ventricular remodelling.',
    datasetEncoding:
      '0 = Absence of anaemia (Hb ≥ 12 g/dL), 1 = Documented anaemia (Hb < 12 g/dL). This binary flag represents presence or absence, not a graded severity score.',
    referenceNote:
      'World Health Organization (WHO) defines anaemia as Hb < 13 g/dL in men and < 12 g/dL in non-pregnant women.',
  },
  {
    id: 'diabetes',
    fieldName: 'diabetes',
    name: 'Diabetes Mellitus',
    category: 'Binary & Demographic',
    system: 'Metabolic & Lifestyle',
    unit: 'Binary (0 / 1)',
    dataType: 'Categorical Binary Indicator',
    datasetRange: '0 (58% non-diabetic) or 1 (42% diabetic)',
    medicalNormal: '0 (No diabetes diagnosis)',
    criticalThreshold: '1 (Confirmed clinical diabetes)',
    importance: 'Moderate',
    shortSummary:
      'Chronic metabolic disorder of glycemic dysregulation. Promotes diabetic cardiomyopathy and microvascular endothelial damage.',
    whatItRepresents:
      'A persistent metabolic disease characterized by chronic hyperglycemia resulting from defects in insulin secretion, insulin action, or both.',
    meaningInDataset:
      '42% of the 299 heart failure patients in the cohort had an established diagnosis of diabetes mellitus.',
    whyIncludedInModel:
      'Diabetic cardiomyopathy promotes interstitial myocardial fibrosis, advanced glycation end-product accumulation, reduced coronary flow reserve, and accelerated atherosclerosis.',
    datasetEncoding:
      '0 = No documented diabetes, 1 = Confirmed diabetes diagnosis. Binary diagnosis flag; does not measure HbA1c or glycemic control.',
    referenceNote:
      'Diagnosed per ADA guidelines by fasting plasma glucose ≥ 126 mg/dL or HbA1c ≥ 6.5%.',
  },
  {
    id: 'hbp',
    fieldName: 'high_blood_pressure',
    name: 'High Blood Pressure',
    category: 'Binary & Demographic',
    system: 'Hemodynamics',
    unit: 'Binary (0 / 1)',
    dataType: 'Categorical Binary Indicator',
    datasetRange: '0 (65% normotensive) or 1 (35% hypertensive)',
    medicalNormal: '0 (No documented hypertension)',
    criticalThreshold: '1 (Confirmed arterial hypertension)',
    importance: 'Moderate',
    shortSummary:
      'Documented history of systemic arterial hypertension. Elevated afterload drives left ventricular concentric hypertrophy and stiffening.',
    whatItRepresents:
      'A documented clinical history or confirmed diagnosis of chronic systemic arterial hypertension (systolic BP ≥ 140 mmHg or diastolic BP ≥ 90 mmHg).',
    meaningInDataset:
      '35% of cohort patients had documented high blood pressure upon presentation.',
    whyIncludedInModel:
      'Elevated systemic vascular resistance increases the work of ventricular ejection (afterload). Chronic hypertension leads to left ventricular hypertrophy, impaired diastolic relaxation, and microvascular rarefaction.',
    datasetEncoding:
      '0 = Normotensive / no documented hypertension history, 1 = Documented hypertension history. Coded as binary presence/absence.',
    referenceNote:
      'ACC/AHA guidelines classify Stage 2 hypertension as systolic BP ≥ 140 mmHg or diastolic BP ≥ 90 mmHg.',
  },
  {
    id: 'sex',
    fieldName: 'sex',
    name: 'Biological Sex',
    category: 'Binary & Demographic',
    system: 'Demographics',
    unit: 'Binary (0: Female, 1: Male)',
    dataType: 'Categorical Binary Indicator',
    datasetRange: '0 (35% female) or 1 (65% male)',
    medicalNormal: 'N/A (Demographic factor)',
    criticalThreshold: 'N/A',
    importance: 'Low-Moderate',
    shortSummary:
      'Biological sex assigned at birth. Heart failure phenotypes and etiology exhibit well-documented sex-specific epidemiological differences.',
    whatItRepresents:
      'The biological sex of the patient as recorded in the clinical record (UCI dataset specification).',
    meaningInDataset:
      'The cohort composition is 65% male (194 patients) and 35% female (105 patients).',
    whyIncludedInModel:
      'Sex-based biological differences influence cardiac remodelling: male patients more frequently present with ischemic cardiomyopathy and systolic dysfunction (HFrEF), while female patients exhibit higher prevalence of hypertensive heart disease and HFpEF.',
    datasetEncoding:
      '0 = Female, 1 = Male (per UCI dataset standard encoding). Numeric values represent category keys, not an ordinal ranking.',
    referenceNote:
      'Included in epidemiological cardiovascular risk models to account for baseline demographic differences.',
  },
  {
    id: 'smoking',
    fieldName: 'smoking',
    name: 'Smoking History',
    category: 'Binary & Demographic',
    system: 'Metabolic & Lifestyle',
    unit: 'Binary (0 / 1)',
    dataType: 'Categorical Binary Indicator',
    datasetRange: '0 (68% non-smoker) or 1 (32% smoker)',
    medicalNormal: '0 (Non-smoker)',
    criticalThreshold: '1 (Active / regular tobacco smoker)',
    importance: 'Moderate',
    shortSummary:
      'Active tobacco smoking habit. Accelerates coronary atherogenesis, induces endothelial dysfunction, and impairs myocardial oxygen delivery.',
    whatItRepresents:
      'Whether the patient is an active or regular consumer of combustible tobacco cigarettes.',
    meaningInDataset:
      '32% of patients in the UCI cohort were classified as active smokers at the time of study observation.',
    whyIncludedInModel:
      'Tobacco smoke exposure promotes coronary vasoconstriction, accelerates atherothrombosis, triggers systemic inflammatory cascade activation, and elevates carboxyhemoglobin levels, impairing myocardial oxygen extraction.',
    datasetEncoding:
      '0 = Non-smoker, 1 = Active / regular tobacco smoker. Binary lifestyle flag; does not quantify pack-years or cessation duration.',
    referenceNote:
      'Smoking cessation is a Class I recommendation in all cardiovascular clinical guidelines to attenuate adverse ventricular remodelling.',
  },
]

export default function ClinicalGuidePage({ onNavigate }) {
  const [activeCategory, setActiveCategory] = useState('ALL')
  const [activeSystem, setActiveSystem] = useState('ALL')
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedCardId, setExpandedCardId] = useState(null)

  const toggleExpand = (id) => {
    setExpandedCardId((prev) => (prev === id ? null : id))
  }

  const expandAll = () => {
    setExpandedCardId('ALL')
  }

  const collapseAll = () => {
    setExpandedCardId(null)
  }

  // Categories and Systems lists
  const systems = ['ALL', 'Hemodynamics', 'Renal & Electrolytes', 'Hematology & Enzymes', 'Metabolic & Lifestyle', 'Demographics']

  // Filter logic
  const filteredParameters = PARAMETERS_DATA.filter((p) => {
    const matchesCategory =
      activeCategory === 'ALL' ||
      (activeCategory === 'QUANT' && p.category === 'Quantitative') ||
      (activeCategory === 'BINARY' && p.category === 'Binary & Demographic')

    const matchesSystem = activeSystem === 'ALL' || p.system === activeSystem

    const searchLower = searchTerm.toLowerCase().trim()
    const matchesSearch =
      !searchLower ||
      p.name.toLowerCase().includes(searchLower) ||
      p.fieldName.toLowerCase().includes(searchLower) ||
      p.whatItRepresents.toLowerCase().includes(searchLower) ||
      p.whyIncludedInModel.toLowerCase().includes(searchLower) ||
      p.system.toLowerCase().includes(searchLower)

    return matchesCategory && matchesSystem && matchesSearch
  })

  return (
    <div className="guide-page-container">
      {/* 1. Header Hero Card with Dataset Attribution */}
      <section className="guide-header-hero" aria-label="Biomarkers Reference Overview">
        <div className="guide-hero-content">
          <div className="guide-hero-badge">
            <span className="guide-pulse-dot" />
            <span>UCI Heart Failure Clinical Records Reference &bull; 11 Model Features</span>
          </div>
          <h2 className="guide-hero-title">Clinical Parameters Guide</h2>
          <p className="guide-hero-subtitle">
            Comprehensive reference manual for the 11 patient biomarkers used across our Logistic Regression baseline and Deep Artificial Neural Network models. Feature definitions, cohort distributions, and binary encodings are derived strictly from the clinical dataset documentation.
          </p>
          <div className="guide-dataset-citation">
            <strong>Source Cohort:</strong> Tanvir Ahmad et al. (2017), Davide Chicco &amp; Giuseppe Jurman (BMC Medical Informatics, 2020). 299 patients with heart failure (NYHA Class III–IV).
          </div>
        </div>

        <div className="guide-hero-actions">
          <button
            type="button"
            className="btn-dash-primary"
            onClick={() => onNavigate('prediction')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <span>Launch Prediction Form</span>
          </button>
        </div>
      </section>

      {/* 2. Important Clinical & Encoding Distinctions Card */}
      <section className="guide-notice-card" aria-label="Data Interpretation Guidelines">
        <div className="notice-icon-box" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
        </div>
        <div className="notice-body">
          <h3 className="notice-title">Important Dataset Encoding &amp; Clinical Data Standards</h3>
          <p className="notice-text">
            <strong>Dataset Encoding vs. Clinical Severity:</strong> Binary features in this application (such as Anaemia, Diabetes, High Blood Pressure, and Smoking) are coded as binary indicators (<code>0 = Negative / Absence</code>, <code>1 = Positive / Presence</code>). These numeric values represent dataset qualitative encodings, not clinical severity scores or stage ratings.
          </p>
          <p className="notice-text" style={{ marginTop: '4px' }}>
            <strong>Continuous Measurements:</strong> Continuous values (such as Ejection Fraction, Serum Creatinine, and CPK) are normalized through standard z-score scaling (StandardScaler) prior to inference in both the linear and neural architectures.
          </p>
        </div>
      </section>

      {/* 3. Search and Category Filter Toolbar */}
      <div className="guide-toolbar-card">
        {/* Search Input */}
        <div className="guide-search-wrapper">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="guide-search-field"
            placeholder="Search parameter, physiological system, or field name (e.g. creatinine, EF)…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <button
              type="button"
              className="guide-clear-search"
              onClick={() => setSearchTerm('')}
              aria-label="Clear search"
            >
              &times;
            </button>
          )}
        </div>

        {/* Primary Category Switcher */}
        <div className="guide-category-toggle">
          <button
            type="button"
            className={`cat-toggle-btn ${activeCategory === 'ALL' ? 'active' : ''}`}
            onClick={() => setActiveCategory('ALL')}
          >
            All Features (11)
          </button>
          <button
            type="button"
            className={`cat-toggle-btn ${activeCategory === 'QUANT' ? 'active' : ''}`}
            onClick={() => setActiveCategory('QUANT')}
          >
            Quantitative (6)
          </button>
          <button
            type="button"
            className={`cat-toggle-btn ${activeCategory === 'BINARY' ? 'active' : ''}`}
            onClick={() => setActiveCategory('BINARY')}
          >
            Binary &amp; Demographics (5)
          </button>
        </div>

        {/* Expand / Collapse All Controls */}
        <div className="guide-view-toggles">
          <button
            type="button"
            className="btn-text-action"
            onClick={expandAll}
            title="Expand all parameter details"
          >
            Expand All
          </button>
          <span className="toggle-separator">&bull;</span>
          <button
            type="button"
            className="btn-text-action"
            onClick={collapseAll}
            title="Collapse all parameter details"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Secondary Physiological System Chips */}
      <div className="guide-system-chips-row">
        <span className="system-chips-label">Filter by System:</span>
        <div className="system-chips-list">
          {systems.map((sys) => (
            <button
              key={sys}
              type="button"
              className={`system-chip ${activeSystem === sys ? 'active' : ''}`}
              onClick={() => setActiveSystem(sys)}
            >
              {sys}
            </button>
          ))}
        </div>
      </div>

      {/* 4. Parameters Detailed Cards Grid */}
      {filteredParameters.length === 0 ? (
        <div className="guide-empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <h3>No clinical parameters match your filter</h3>
          <p>Try searching for a different term or reset your category and system filters.</p>
          <button
            type="button"
            className="btn-dash-secondary"
            onClick={() => {
              setSearchTerm('')
              setActiveCategory('ALL')
              setActiveSystem('ALL')
            }}
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="guide-parameters-grid">
          {filteredParameters.map((param) => {
            const isExpanded = expandedCardId === 'ALL' || expandedCardId === param.id

            return (
              <article key={param.id} className={`param-guide-card ${isExpanded ? 'is-expanded' : ''}`}>
                {/* Card Header Top */}
                <div className="param-card-header">
                  <div className="param-header-left">
                    <div className="param-meta-badges">
                      <span className={`param-type-badge ${param.category === 'Quantitative' ? 'badge-quant' : 'badge-binary'}`}>
                        {param.category}
                      </span>
                      <span className="param-system-badge">{param.system}</span>
                      <span className="param-fieldname-tag" title="API field key">
                        <code>{param.fieldName}</code>
                      </span>
                    </div>
                    <h3 className="param-card-title">{param.name}</h3>
                  </div>

                  <div className="param-header-right">
                    <span className={`param-importance-pill ${param.importance.toLowerCase()}`}>
                      {param.importance} Predictive Weight
                    </span>
                  </div>
                </div>

                {/* Short Overview */}
                <p className="param-short-summary">{param.shortSummary}</p>

                {/* Key Clinical & Dataset Attributes */}
                <div className="param-metrics-strip">
                  <div className="metric-strip-item">
                    <span className="metric-strip-label">Unit of Measure</span>
                    <span className="metric-strip-value font-mono">{param.unit}</span>
                  </div>
                  <div className="metric-strip-item">
                    <span className="metric-strip-label">Dataset Range</span>
                    <span className="metric-strip-value">{param.datasetRange}</span>
                  </div>
                  <div className="metric-strip-item">
                    <span className="metric-strip-label">General Reference</span>
                    <span className="metric-strip-value normal">{param.medicalNormal}</span>
                  </div>
                </div>

                {/* Expandable In-Depth Information Panel */}
                {isExpanded && (
                  <div className="param-expanded-panel">
                    <div className="expanded-section">
                      <h4 className="expanded-heading">What this parameter represents:</h4>
                      <p className="expanded-text">{param.whatItRepresents}</p>
                    </div>

                    <div className="expanded-section">
                      <h4 className="expanded-heading">Significance in Heart Failure Dataset:</h4>
                      <p className="expanded-text">{param.meaningInDataset}</p>
                    </div>

                    <div className="expanded-section">
                      <h4 className="expanded-heading">Why it is included in the prediction models:</h4>
                      <p className="expanded-text">{param.whyIncludedInModel}</p>
                    </div>

                    <div className="expanded-grid-row">
                      <div className="expanded-box encoding-box">
                        <span className="box-kicker">Dataset Specification</span>
                        <h5 className="box-title">Encoding &amp; Scaling</h5>
                        <p className="box-text">{param.datasetEncoding}</p>
                      </div>

                      <div className="expanded-box reference-box">
                        <span className="box-kicker">Clinical Literature</span>
                        <h5 className="box-title">Reference Guidance</h5>
                        <p className="box-text">{param.referenceNote}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Card Action Footer */}
                <div className="param-card-footer">
                  <button
                    type="button"
                    className="btn-toggle-expand"
                    onClick={() => toggleExpand(param.id)}
                    aria-expanded={isExpanded}
                  >
                    <span>{isExpanded ? 'Hide Details' : 'View Full Reference & Encoding'}</span>
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      style={{
                        transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 200ms ease',
                      }}
                      aria-hidden="true"
                    >
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </button>

                  <button
                    type="button"
                    className="btn-test-param"
                    onClick={() => onNavigate('prediction')}
                    title={`Test ${param.name} in prediction form`}
                  >
                    <span>Evaluate in Model &rarr;</span>
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
