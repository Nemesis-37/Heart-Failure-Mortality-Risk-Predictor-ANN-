import React, { useState, useEffect } from 'react'

const INITIAL_STATE = {
  age: '60',
  anaemia: 0,
  creatinine_phosphokinase: '250',
  diabetes: 0,
  ejection_fraction: '38',
  high_blood_pressure: 0,
  platelets: '260000',
  serum_creatinine: '1.1',
  serum_sodium: '137',
  sex: 1, // 0: Female, 1: Male
  smoking: 0,
}

const PRESET_LOW_RISK = {
  ...INITIAL_STATE,
  age: '50',
  anaemia: 0,
  creatinine_phosphokinase: '168',
  diabetes: 0,
  ejection_fraction: '45',
  high_blood_pressure: 0,
  platelets: '276000',
  serum_creatinine: '0.9',
  serum_sodium: '140',
  sex: 1,
  smoking: 0,
}

const PRESET_HIGH_RISK = {
  ...INITIAL_STATE,
  age: '75',
  anaemia: 1,
  creatinine_phosphokinase: '582',
  diabetes: 1,
  ejection_fraction: '20',
  high_blood_pressure: 1,
  platelets: '265000',
  serum_creatinine: '2.5',
  serum_sodium: '130',
  sex: 1,
  smoking: 1,
}

const MODELS = [
  {
    id: 'lr',
    label: 'Logistic Regression',
    endpoint: '/api/predict',
    fallbackEndpoint: 'http://127.0.0.1:8000/predict',
    desc: 'Classical linear statistical baseline with interpretable feature coefficients.',
  },
  {
    id: 'ann',
    label: 'Artificial Neural Network',
    endpoint: '/api/predict-ann',
    fallbackEndpoint: 'http://127.0.0.1:8000/predict-ann',
    desc: 'Deep feed-forward network trained to capture complex non-linear biomarker interactions.',
  },
]

export default function DoctorDashboard({ doctorUser, onLogout }) {
  const [formData, setFormData] = useState(INITIAL_STATE)
  const [fieldErrors, setFieldErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState(null)
  const [result, setResult] = useState(null)
  const [backendStatus, setBackendStatus] = useState('checking')
  const [selectedModelId, setSelectedModelId] = useState('lr')

  useEffect(() => {
    checkHealth()
  }, [])

  const checkHealth = async () => {
    setBackendStatus('checking')
    try {
      const response = await fetch('/api/health')
      setBackendStatus(response.ok ? 'online' : 'offline')
    } catch {
      try {
        const response = await fetch('http://127.0.0.1:8000/health')
        setBackendStatus(response.ok ? 'online' : 'offline')
      } catch {
        setBackendStatus('offline')
      }
    }
  }

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }))

    setFieldErrors((prev) => {
      if (!prev[field]) return prev
      const errors = { ...prev }
      delete errors[field]
      return errors
    })
  }

  const validate = () => {
    const errors = {}
    const rules = [
      ['age', 1, 120, 'Age must be between 1 and 120'],
      ['creatinine_phosphokinase', 1, 10000, 'CPK must be a positive number'],
      ['ejection_fraction', 1, 100, 'Ejection fraction must be between 1% and 100%'],
      ['platelets', 1, 1500000, 'Platelet count must be a positive number'],
      ['serum_creatinine', 0.1, 25, 'Serum creatinine must be a positive number'],
      ['serum_sodium', 50, 200, 'Serum sodium must be between 50 and 200 mEq/L'],
    ]

    rules.forEach(([field, min, max, message]) => {
      const rawVal = String(formData[field] ?? '').trim()
      const value = Number(rawVal)

      if (
        rawVal === '' ||
        !Number.isFinite(value) ||
        value < min ||
        value > max
      ) {
        errors[field] = message
      }
    })

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault()
    if (loading) return

    setApiError(null)

    if (!validate()) return

    setLoading(true)

    const payload = Object.fromEntries(
      Object.entries(formData).map(([key, value]) => [
        key,
        ['anaemia', 'diabetes', 'high_blood_pressure', 'sex', 'smoking'].includes(key)
          ? Number.parseInt(value, 10)
          : Number.parseFloat(value),
      ])
    )

    const model = MODELS.find((m) => m.id === selectedModelId) || MODELS[0]

    try {
      let response

      try {
        response = await fetch(model.endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      } catch {
        response = await fetch(model.fallbackEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      }

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || `Server error (${response.status})`)
      }

      setResult(data)
      setBackendStatus('online')
    } catch (error) {
      setApiError(
        error.message || 'Could not connect to FastAPI backend at http://127.0.0.1:8000.'
      )
      setBackendStatus('offline')
    } finally {
      setLoading(false)
    }
  }

  const loadPreset = (preset) => {
    setFormData({ ...preset })
    setFieldErrors({})
    setApiError(null)
  }

  const handleReset = () => {
    setFormData(INITIAL_STATE)
    setFieldErrors({})
    setResult(null)
    setApiError(null)
  }

  const selectedModel = MODELS.find((m) => m.id === selectedModelId) || MODELS[0]

  return (
    <div className="dashboard-page">
      {/* Top Application Bar */}
      <header className="app-topbar">
        <div className="topbar-container">
          <div className="topbar-left">
            <div className="topbar-logo" aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
              </svg>
            </div>
            <div>
              <div className="topbar-title-row">
                <h1 className="topbar-title">Heart Failure Mortality Risk Predictor</h1>
                <span className="topbar-badge">Physician Workspace</span>
              </div>
              <p className="topbar-subtitle">Clinical Machine-Learning Prototype · Dual Model Architecture</p>
            </div>
          </div>

          <div className="topbar-right">
            {/* API Health Status Indicator */}
            <button
              type="button"
              className="topbar-status-pill"
              onClick={checkHealth}
              title={`API Status: ${backendStatus}. Click to check connection.`}
              aria-label={`API Status: ${backendStatus}. Click to check connection.`}
            >
              <span className={`status-dot ${backendStatus}`} aria-hidden="true" />
              <span>{backendStatus === 'online' ? 'API Online' : backendStatus === 'offline' ? 'API Offline (127.0.0.1:8000)' : 'Checking…'}</span>
            </button>

            {/* Doctor Profile Pill */}
            <div className="doctor-profile-pill">
              <div className="doctor-avatar" aria-hidden="true">
                {doctorUser?.avatarInitials || 'DR'}
              </div>
              <div className="doctor-info">
                <span className="doctor-name">{doctorUser?.name || 'Dr. Julian Carter, MD'}</span>
                <span className="doctor-role">{doctorUser?.role || 'Attending Cardiologist'}</span>
              </div>
            </div>

            {/* Logout Action */}
            <button
              type="button"
              className="btn-logout"
              onClick={onLogout}
              title="Sign out of doctor portal"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              <span>Logout</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="dashboard-content-container">
        {/* Doctor Welcome Banner */}
        <div className="doctor-welcome-card">
          <div className="welcome-text">
            <h2>Welcome back, {doctorUser?.name || 'Doctor'}</h2>
            <p>
              Evaluate patient risk by inputting the 11 documented clinical indicators below. Toggle between the classical Logistic Regression baseline and the Artificial Neural Network model to compare predictions.
            </p>
          </div>
          <div className="welcome-actions">
            <span className="presets-label">Quick Load Sample:</span>
            <div className="preset-buttons">
              <button
                type="button"
                className="btn-preset-pill preset-low"
                onClick={() => loadPreset(PRESET_LOW_RISK)}
                disabled={loading}
              >
                <span className="dot dot-low" aria-hidden="true" />
                Low Risk Profile
              </button>
              <button
                type="button"
                className="btn-preset-pill preset-high"
                onClick={() => loadPreset(PRESET_HIGH_RISK)}
                disabled={loading}
              >
                <span className="dot dot-high" aria-hidden="true" />
                High Risk Profile
              </button>
              <button
                type="button"
                className="btn-preset-pill preset-reset"
                onClick={handleReset}
                disabled={loading}
              >
                Reset Defaults
              </button>
            </div>
          </div>
        </div>

        {/* Global Error Banner */}
        {apiError && (
          <div className="alert-banner error" role="alert">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div className="alert-text">
              <strong>Prediction Service Error: </strong>
              <span>{apiError} (Verify backend is running via <code>python main.py</code> at http://127.0.0.1:8000)</span>
            </div>
            <button type="button" className="btn-alert-retry" onClick={handleSubmit}>
              Retry Prediction
            </button>
          </div>
        )}

        {/* Form Validation Alert */}
        {Object.keys(fieldErrors).length > 0 && (
          <div className="alert-banner warning" role="alert">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <div className="alert-text">
              <strong>Validation Notice: </strong>
              <span>Please review and correct the {Object.keys(fieldErrors).length} highlighted field(s) before running inference.</span>
            </div>
          </div>
        )}

        {/* Two-Column Clinical Dashboard Grid */}
        <main className="dashboard-grid">
          {/* Left Column: Patient Information & Model Selection Form */}
          <section className="card form-card">
            <div className="card-header">
              <div className="card-header-title-row">
                <h2 className="card-title">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                    <polyline points="10 9 9 9 8 9" />
                  </svg>
                  Patient Clinical Parameters
                </h2>
                <span className="card-counter-tag">11 Required Fields</span>
              </div>
              <p className="card-subtitle">
                Enter documented clinical measurements, laboratory assays, and patient conditions.
              </p>
            </div>

            <div className="card-body">
              <form onSubmit={handleSubmit} noValidate>
                {/* Group 1: Quantitative Clinical Measurements */}
                <div className="form-group-section">
                  <div className="section-title-row">
                    <span className="section-num">1</span>
                    <div>
                      <h3 className="section-heading">Clinical Measurements &amp; Laboratory Assays</h3>
                      <p className="section-desc">Continuous biometric values and laboratory findings</p>
                    </div>
                  </div>

                  <div className="form-grid">
                    {/* 1. Age */}
                    <div className="form-field">
                      <label className="form-label" htmlFor="param-age">
                        <span>Age <span className="req-star" title="Required">*</span></span>
                        <span className="field-unit">years</span>
                      </label>
                      <input
                        id="param-age"
                        type="number"
                        step="any"
                        placeholder="e.g. 60"
                        className={`form-input ${fieldErrors.age ? 'has-error' : ''}`}
                        value={formData.age}
                        onChange={(e) => handleInputChange('age', e.target.value)}
                        disabled={loading}
                        aria-invalid={!!fieldErrors.age}
                        aria-describedby={fieldErrors.age ? 'age-err' : undefined}
                      />
                      {fieldErrors.age && <span id="age-err" className="field-error-msg">{fieldErrors.age}</span>}
                    </div>

                    {/* 2. Ejection Fraction */}
                    <div className="form-field">
                      <label className="form-label" htmlFor="param-ef">
                        <span>Ejection Fraction <span className="req-star" title="Required">*</span></span>
                        <span className="field-unit">% (norm: 50–70)</span>
                      </label>
                      <input
                        id="param-ef"
                        type="number"
                        step="any"
                        placeholder="e.g. 38"
                        className={`form-input ${fieldErrors.ejection_fraction ? 'has-error' : ''}`}
                        value={formData.ejection_fraction}
                        onChange={(e) => handleInputChange('ejection_fraction', e.target.value)}
                        disabled={loading}
                        aria-invalid={!!fieldErrors.ejection_fraction}
                        aria-describedby={fieldErrors.ejection_fraction ? 'ef-err' : undefined}
                      />
                      {fieldErrors.ejection_fraction && <span id="ef-err" className="field-error-msg">{fieldErrors.ejection_fraction}</span>}
                    </div>

                    {/* 3. Serum Creatinine */}
                    <div className="form-field">
                      <label className="form-label" htmlFor="param-creatinine">
                        <span>Serum Creatinine <span className="req-star" title="Required">*</span></span>
                        <span className="field-unit">mg/dL (norm: 0.7–1.3)</span>
                      </label>
                      <input
                        id="param-creatinine"
                        type="number"
                        step="any"
                        placeholder="e.g. 1.1"
                        className={`form-input ${fieldErrors.serum_creatinine ? 'has-error' : ''}`}
                        value={formData.serum_creatinine}
                        onChange={(e) => handleInputChange('serum_creatinine', e.target.value)}
                        disabled={loading}
                        aria-invalid={!!fieldErrors.serum_creatinine}
                        aria-describedby={fieldErrors.serum_creatinine ? 'creat-err' : undefined}
                      />
                      {fieldErrors.serum_creatinine && <span id="creat-err" className="field-error-msg">{fieldErrors.serum_creatinine}</span>}
                    </div>

                    {/* 4. Serum Sodium */}
                    <div className="form-field">
                      <label className="form-label" htmlFor="param-sodium">
                        <span>Serum Sodium <span className="req-star" title="Required">*</span></span>
                        <span className="field-unit">mEq/L (norm: 135–145)</span>
                      </label>
                      <input
                        id="param-sodium"
                        type="number"
                        step="any"
                        placeholder="e.g. 137"
                        className={`form-input ${fieldErrors.serum_sodium ? 'has-error' : ''}`}
                        value={formData.serum_sodium}
                        onChange={(e) => handleInputChange('serum_sodium', e.target.value)}
                        disabled={loading}
                        aria-invalid={!!fieldErrors.serum_sodium}
                        aria-describedby={fieldErrors.serum_sodium ? 'sod-err' : undefined}
                      />
                      {fieldErrors.serum_sodium && <span id="sod-err" className="field-error-msg">{fieldErrors.serum_sodium}</span>}
                    </div>

                    {/* 5. Platelets */}
                    <div className="form-field">
                      <label className="form-label" htmlFor="param-platelets">
                        <span>Platelets <span className="req-star" title="Required">*</span></span>
                        <span className="field-unit">cells/mL</span>
                      </label>
                      <input
                        id="param-platelets"
                        type="number"
                        step="any"
                        placeholder="e.g. 260000"
                        className={`form-input ${fieldErrors.platelets ? 'has-error' : ''}`}
                        value={formData.platelets}
                        onChange={(e) => handleInputChange('platelets', e.target.value)}
                        disabled={loading}
                        aria-invalid={!!fieldErrors.platelets}
                        aria-describedby={fieldErrors.platelets ? 'plat-err' : undefined}
                      />
                      {fieldErrors.platelets && <span id="plat-err" className="field-error-msg">{fieldErrors.platelets}</span>}
                    </div>

                    {/* 6. Creatinine Phosphokinase */}
                    <div className="form-field">
                      <label className="form-label" htmlFor="param-cpk">
                        <span>Creatinine Phosphokinase <span className="req-star" title="Required">*</span></span>
                        <span className="field-unit">mcg/L (norm: 10–120)</span>
                      </label>
                      <input
                        id="param-cpk"
                        type="number"
                        step="any"
                        placeholder="e.g. 250"
                        className={`form-input ${fieldErrors.creatinine_phosphokinase ? 'has-error' : ''}`}
                        value={formData.creatinine_phosphokinase}
                        onChange={(e) => handleInputChange('creatinine_phosphokinase', e.target.value)}
                        disabled={loading}
                        aria-invalid={!!fieldErrors.creatinine_phosphokinase}
                        aria-describedby={fieldErrors.creatinine_phosphokinase ? 'cpk-err' : undefined}
                      />
                      {fieldErrors.creatinine_phosphokinase && <span id="cpk-err" className="field-error-msg">{fieldErrors.creatinine_phosphokinase}</span>}
                    </div>
                  </div>
                </div>

                {/* Group 2: Baseline Demographic & Medical Conditions */}
                <div className="form-group-section">
                  <div className="section-title-row">
                    <span className="section-num">2</span>
                    <div>
                      <h3 className="section-heading">Patient Conditions &amp; Demographics</h3>
                      <p className="section-desc">Documented binary clinical conditions and demographic profile</p>
                    </div>
                  </div>

                  <div className="form-grid">
                    {/* 7. Biological Sex */}
                    <div className="form-field">
                      <label className="form-label" id="lbl-sex">
                        <span>Biological Sex <span className="req-star" title="Required">*</span></span>
                      </label>
                      <div className="segmented-toggle" role="radiogroup" aria-labelledby="lbl-sex">
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.sex === 0}
                          className={`toggle-btn ${formData.sex === 0 ? 'active' : ''}`}
                          onClick={() => handleInputChange('sex', 0)}
                          disabled={loading}
                        >
                          Female
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.sex === 1}
                          className={`toggle-btn ${formData.sex === 1 ? 'active' : ''}`}
                          onClick={() => handleInputChange('sex', 1)}
                          disabled={loading}
                        >
                          Male
                        </button>
                      </div>
                    </div>

                    {/* 8. Anaemia */}
                    <div className="form-field">
                      <label className="form-label" id="lbl-anaemia">
                        <span>Anaemia <span className="req-star" title="Required">*</span></span>
                        <span className="field-unit">Hb &lt; 12 g/dL</span>
                      </label>
                      <div className="segmented-toggle" role="radiogroup" aria-labelledby="lbl-anaemia">
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.anaemia === 0}
                          className={`toggle-btn ${formData.anaemia === 0 ? 'active' : ''}`}
                          onClick={() => handleInputChange('anaemia', 0)}
                          disabled={loading}
                        >
                          No
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.anaemia === 1}
                          className={`toggle-btn ${formData.anaemia === 1 ? 'active' : ''}`}
                          onClick={() => handleInputChange('anaemia', 1)}
                          disabled={loading}
                        >
                          Yes
                        </button>
                      </div>
                    </div>

                    {/* 9. Diabetes */}
                    <div className="form-field">
                      <label className="form-label" id="lbl-diabetes">
                        <span>Diabetes Diagnosis <span className="req-star" title="Required">*</span></span>
                      </label>
                      <div className="segmented-toggle" role="radiogroup" aria-labelledby="lbl-diabetes">
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.diabetes === 0}
                          className={`toggle-btn ${formData.diabetes === 0 ? 'active' : ''}`}
                          onClick={() => handleInputChange('diabetes', 0)}
                          disabled={loading}
                        >
                          No
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.diabetes === 1}
                          className={`toggle-btn ${formData.diabetes === 1 ? 'active' : ''}`}
                          onClick={() => handleInputChange('diabetes', 1)}
                          disabled={loading}
                        >
                          Yes
                        </button>
                      </div>
                    </div>

                    {/* 10. High Blood Pressure */}
                    <div className="form-field">
                      <label className="form-label" id="lbl-hbp">
                        <span>High Blood Pressure <span className="req-star" title="Required">*</span></span>
                        <span className="field-unit">Hypertension</span>
                      </label>
                      <div className="segmented-toggle" role="radiogroup" aria-labelledby="lbl-hbp">
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.high_blood_pressure === 0}
                          className={`toggle-btn ${formData.high_blood_pressure === 0 ? 'active' : ''}`}
                          onClick={() => handleInputChange('high_blood_pressure', 0)}
                          disabled={loading}
                        >
                          No
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.high_blood_pressure === 1}
                          className={`toggle-btn ${formData.high_blood_pressure === 1 ? 'active' : ''}`}
                          onClick={() => handleInputChange('high_blood_pressure', 1)}
                          disabled={loading}
                        >
                          Yes
                        </button>
                      </div>
                    </div>

                    {/* 11. Smoking */}
                    <div className="form-field">
                      <label className="form-label" id="lbl-smoking">
                        <span>Smoking History <span className="req-star" title="Required">*</span></span>
                        <span className="field-unit">Active tobacco</span>
                      </label>
                      <div className="segmented-toggle" role="radiogroup" aria-labelledby="lbl-smoking">
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.smoking === 0}
                          className={`toggle-btn ${formData.smoking === 0 ? 'active' : ''}`}
                          onClick={() => handleInputChange('smoking', 0)}
                          disabled={loading}
                        >
                          No
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.smoking === 1}
                          className={`toggle-btn ${formData.smoking === 1 ? 'active' : ''}`}
                          onClick={() => handleInputChange('smoking', 1)}
                          disabled={loading}
                        >
                          Yes
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Group 3: Model Selection */}
                <div className="form-group-section">
                  <div className="section-title-row">
                    <span className="section-num">3</span>
                    <div>
                      <h3 className="section-heading">Model Selection</h3>
                      <p className="section-desc">Select which machine learning architecture performs inference</p>
                    </div>
                  </div>

                  <div className="model-selection-grid" role="radiogroup" aria-label="Prediction model selection">
                    {MODELS.map((m) => (
                      <label
                        key={m.id}
                        htmlFor={`model-choice-${m.id}`}
                        className={`model-card ${selectedModelId === m.id ? 'selected' : ''}`}
                      >
                        <input
                          id={`model-choice-${m.id}`}
                          type="radio"
                          name="model_choice"
                          value={m.id}
                          checked={selectedModelId === m.id}
                          onChange={() => setSelectedModelId(m.id)}
                          disabled={loading}
                          className="model-radio-input"
                        />
                        <div className="model-card-top">
                          <span className="model-title">{m.label}</span>
                          <span className="model-endpoint-pill">
                            {m.id === 'lr' ? 'POST /predict' : 'POST /predict-ann'}
                          </span>
                        </div>
                        <p className="model-desc">{m.desc}</p>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Form Action Buttons */}
                <div className="form-action-bar">
                  <button
                    type="button"
                    className="btn-secondary btn-reset-form"
                    onClick={handleReset}
                    disabled={loading}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                      <path d="M3 3v5h5" />
                    </svg>
                    <span>Reset Form</span>
                  </button>

                  <button
                    type="submit"
                    className="btn-primary btn-predict"
                    disabled={loading}
                    aria-busy={loading}
                  >
                    {loading ? (
                      <>
                        <span className="spinner" aria-hidden="true" />
                        <span>Running Prediction&hellip;</span>
                      </>
                    ) : (
                      <>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                          <circle cx="12" cy="12" r="10" />
                          <polygon points="10 8 16 12 10 16 10 8" />
                        </svg>
                        <span>Run {selectedModel.label} Prediction</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </section>

          {/* Right Column: Clean, Streamlined Prediction Results Panel */}
          <aside className="card results-card" aria-label="Prediction results card" aria-live="polite">
            <div className="card-header">
              <div className="card-header-title-row">
                <h2 className="card-title">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                  </svg>
                  Prediction Results
                </h2>
                {result && (
                  <span className="result-model-tag">
                    {result.model}
                  </span>
                )}
              </div>
              <p className="card-subtitle">
                Model output strictly derived from the FastAPI backend response
              </p>
            </div>

            <div className="card-body">
              {/* State A: Loading */}
              {loading ? (
                <div className="result-state-box loading-state">
                  <div className="clean-spinner-lg" aria-hidden="true" />
                  <h3>Evaluating Clinical Parameters&hellip;</h3>
                  <p>Calling FastAPI endpoint for <strong>{selectedModel.label}</strong>.</p>
                </div>
              ) : !result ? (
                /* State B: Empty Initial State */
                <div className="result-state-box empty-state">
                  <div className="empty-icon-circle" aria-hidden="true">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                    </svg>
                  </div>
                  <h3>No Prediction Generated Yet</h3>
                  <p>
                    Complete the 11 patient parameters on the left, select a model, and click <strong>Run Prediction</strong> to view results.
                  </p>
                </div>
              ) : (
                /* State C: Clean, Truthful API Response Results */
                <div className="clean-result-container">
                  {/* Predicted Outcome Badge */}
                  <div className={`clean-outcome-banner ${result.predicted_class === 1 ? 'positive-event' : 'negative-event'}`}>
                    <div className="outcome-icon" aria-hidden="true">
                      {result.predicted_class === 1 ? (
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                          <circle cx="12" cy="12" r="10" />
                          <line x1="12" y1="8" x2="12" y2="12" />
                          <line x1="12" y1="16" x2="12.01" y2="16" />
                        </svg>
                      ) : (
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                          <polyline points="22 4 12 14.01 9 11.01" />
                        </svg>
                      )}
                    </div>
                    <div className="outcome-text">
                      <span className="outcome-kicker">Predicted Label</span>
                      <h3 className="outcome-label">{result.predicted_label}</h3>
                      <span className="outcome-class-code">
                        Model Output Class: <strong>{result.predicted_class}</strong> ({result.predicted_class === 1 ? 'Death event' : 'No death event'})
                      </span>
                    </div>
                  </div>

                  {/* Predicted Probability Indicator */}
                  <div className="probability-metric-card">
                    <div className="metric-header-row">
                      <span className="metric-heading">Predicted Mortality Probability</span>
                      <span className={`metric-percentage ${result.predicted_probability >= 0.5 ? 'elevated' : 'baseline'}`}>
                        {(result.predicted_probability * 100).toFixed(1)}%
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="clean-progress-track" role="progressbar" aria-valuenow={Math.round(result.predicted_probability * 100)} aria-valuemin="0" aria-valuemax="100">
                      <div
                        className={`clean-progress-fill ${result.predicted_probability >= 0.5 ? 'fill-elevated' : 'fill-baseline'}`}
                        style={{ width: `${Math.min(100, Math.max(0, result.predicted_probability * 100))}%` }}
                      />
                    </div>

                    <div className="metric-scale-labels" aria-hidden="true">
                      <span>0%</span>
                      <span>50% Threshold</span>
                      <span>100%</span>
                    </div>
                  </div>

                  {/* Key Response Meta */}
                  <div className="result-meta-table">
                    <div className="meta-row">
                      <span className="meta-label">Selected Model</span>
                      <span className="meta-value">{result.model}</span>
                    </div>
                    <div className="meta-row">
                      <span className="meta-label">Raw Probability Score</span>
                      <span className="meta-value font-mono">{result.predicted_probability}</span>
                    </div>
                    {result.notice && (
                      <div className="meta-row notice-row">
                        <span className="meta-label">Backend Notice</span>
                        <span className="meta-value">{result.notice}</span>
                      </div>
                    )}
                  </div>

                  {/* Clear Educational Disclaimer */}
                  <div className="clean-disclaimer-box" role="note">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="16" x2="12" y2="12" />
                      <line x1="12" y1="8" x2="12.01" y2="8" />
                    </svg>
                    <p>
                      <strong>Educational Prototype:</strong> This project is an educational machine-learning prototype and is not intended for medical diagnosis or clinical decision-making.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </aside>
        </main>

        {/* Global Footer */}
        <footer className="dashboard-footer">
          <p>
            Heart Failure Mortality Risk Predictor &bull; Educational Machine Learning Prototype &bull; Not for clinical diagnosis or medical decision-making
          </p>
        </footer>
      </div>
    </div>
  )
}

