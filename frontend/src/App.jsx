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
    desc: 'Classical ML baseline · highly interpretable',
    tag: 'Baseline',
  },
  {
    id: 'ann',
    label: 'Artificial Neural Network',
    endpoint: '/api/predict-ann',
    fallbackEndpoint: 'http://127.0.0.1:8000/predict-ann',
    desc: 'Deep learning · non-linear feature interactions',
    tag: 'Deep Learning',
  },
]

export default function App() {
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
      ['age', 1, 120, 'Age must be between 1 and 120 years'],
      ['creatinine_phosphokinase', 1, 10000, 'CPK must be a positive value (typically 10–10,000)'],
      ['ejection_fraction', 1, 100, 'Ejection fraction must be between 1% and 100%'],
      ['platelets', 1, 1500000, 'Platelet count must be a positive number'],
      ['serum_creatinine', 0.1, 25, 'Serum creatinine must be a positive value (typically 0.1–25)'],
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
    if (loading) return // Prevent duplicate concurrent requests

    setApiError(null)

    if (!validate()) {
      return
    }

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
        throw new Error(data.detail || `Server error (${response.status}): ${response.statusText}`)
      }

      setResult(data)
      setBackendStatus('online')
    } catch (error) {
      setApiError(
        error.message || 'Could not connect to the prediction API. Ensure FastAPI is running on port 8000.'
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

  const getProbabilityColor = (probability) => {
    if (probability < 0.35) return 'var(--success)'
    if (probability < 0.6) return 'var(--warning)'
    return 'var(--danger)'
  }

  const getRiskLevel = (probability) => {
    if (probability < 0.35) return 'Low Mortality Risk'
    if (probability < 0.6) return 'Moderate Mortality Risk'
    return 'High Mortality Risk'
  }

  const selectedModel = MODELS.find((m) => m.id === selectedModelId) || MODELS[0]

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
            </svg>
          </div>
          <div>
            <h1 className="brand-title">Heart Failure Mortality Risk Predictor</h1>
            <p className="brand-subtitle">
              Clinical Decision-Support &amp; Educational Machine Learning Prototype
            </p>
          </div>
        </div>

        <button
          type="button"
          className="header-status"
          onClick={checkHealth}
          title={`API Status: ${backendStatus}. Click to test connection.`}
          aria-label={`API Status: ${backendStatus}. Click to test connection.`}
        >
          <span className={`status-dot ${backendStatus}`} aria-hidden="true" />
          <span>
            {backendStatus === 'online'
              ? 'API Online'
              : backendStatus === 'offline'
              ? 'API Offline · Click to Retry'
              : 'Checking API…'}
          </span>
        </button>
      </header>

      {/* Educational Disclaimer */}
      <div className="disclaimer-banner" role="note">
        <span className="disclaimer-banner-icon" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
        </span>
        <p>
          <strong>Educational Machine-Learning Prototype:</strong> This interface is designed for academic evaluation of predictive models. It is <strong>not intended for medical diagnosis, clinical prognosis, or patient management</strong>. Always consult licensed medical professionals for health assessments.
        </p>
      </div>

      {/* Quick Fill Presets Bar */}
      <div className="presets-bar" aria-label="Quick fill presets">
        <span className="presets-label">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
          Clinical Presets:
        </span>
        <button
          type="button"
          id="preset-low-risk"
          className="preset-btn preset-low"
          onClick={() => loadPreset(PRESET_LOW_RISK)}
          disabled={loading}
        >
          <span className="preset-dot low" aria-hidden="true" />
          Low Risk Profile
        </button>
        <button
          type="button"
          id="preset-high-risk"
          className="preset-btn preset-high"
          onClick={() => loadPreset(PRESET_HIGH_RISK)}
          disabled={loading}
        >
          <span className="preset-dot high" aria-hidden="true" />
          High Risk Profile
        </button>
        <button
          type="button"
          id="btn-reset-defaults"
          className="preset-btn btn-reset"
          onClick={handleReset}
          disabled={loading}
          title="Restore default clinical values"
        >
          Reset to Defaults
        </button>
      </div>

      {/* Main Grid */}
      <main className="dashboard-grid">
        {/* Input Form Card */}
        <section className="card form-card">
          <div className="card-header">
            <div className="card-header-main">
              <h2 className="card-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                </svg>
                Patient Clinical Parameters
              </h2>
              <span className="card-header-badge">11 Required Features</span>
            </div>
            <p className="card-subtitle">
              Enter documented laboratory assays, demographic indicators, and physiological metrics.
            </p>
          </div>

          <div className="card-body">
            {apiError && (
              <div className="alert-banner error" role="alert">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <div className="alert-content">
                  <strong>API Connection Error:</strong>
                  <p>{apiError}</p>
                  <div className="alert-actions">
                    <button type="button" className="btn-alert-action" onClick={handleSubmit}>
                      Retry Prediction
                    </button>
                    <button type="button" className="btn-alert-action outline" onClick={checkHealth}>
                      Check API Health
                    </button>
                  </div>
                </div>
              </div>
            )}

            {Object.keys(fieldErrors).length > 0 && (
              <div className="alert-banner warning" role="alert">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                <div className="alert-content">
                  <strong>Validation Attention Required:</strong>
                  <p>Please review and correct the {Object.keys(fieldErrors).length} invalid clinical value(s) highlighted below.</p>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              {/* Section 1: Quantitative Measurements */}
              <div className="form-section-header">
                <span className="section-step">1</span>
                <div>
                  <h3 className="form-section-heading">Quantitative Measurements</h3>
                  <p className="form-section-sub">Continuous physiological indicators and lab assays</p>
                </div>
              </div>

              <div className="form-grid">
                {/* Age */}
                <div className="form-group">
                  <label className="form-label" htmlFor="age">
                    <span>
                      Age <span className="required-indicator" title="Required">*</span>
                    </span>
                    <span className="label-unit">years</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="age"
                      type="number"
                      step="any"
                      min="1"
                      max="120"
                      placeholder="e.g. 60"
                      disabled={loading}
                      aria-required="true"
                      aria-invalid={!!fieldErrors.age}
                      aria-describedby={fieldErrors.age ? 'age-error' : undefined}
                      className={`form-input ${fieldErrors.age ? 'has-error' : ''}`}
                      value={formData.age}
                      onChange={(e) => handleInputChange('age', e.target.value)}
                    />
                  </div>
                  {fieldErrors.age && (
                    <span id="age-error" className="error-text">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      {fieldErrors.age}
                    </span>
                  )}
                </div>

                {/* Ejection Fraction */}
                <div className="form-group">
                  <label className="form-label" htmlFor="ejection_fraction">
                    <span>
                      Ejection Fraction <span className="required-indicator" title="Required">*</span>
                    </span>
                    <span className="label-unit">% (normal: 50–70%)</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="ejection_fraction"
                      type="number"
                      step="any"
                      min="1"
                      max="100"
                      placeholder="e.g. 38"
                      disabled={loading}
                      aria-required="true"
                      aria-invalid={!!fieldErrors.ejection_fraction}
                      aria-describedby={fieldErrors.ejection_fraction ? 'ejection_fraction-error' : undefined}
                      className={`form-input ${fieldErrors.ejection_fraction ? 'has-error' : ''}`}
                      value={formData.ejection_fraction}
                      onChange={(e) => handleInputChange('ejection_fraction', e.target.value)}
                    />
                  </div>
                  {fieldErrors.ejection_fraction && (
                    <span id="ejection_fraction-error" className="error-text">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      {fieldErrors.ejection_fraction}
                    </span>
                  )}
                </div>

                {/* Serum Creatinine */}
                <div className="form-group">
                  <label className="form-label" htmlFor="serum_creatinine">
                    <span>
                      Serum Creatinine <span className="required-indicator" title="Required">*</span>
                    </span>
                    <span className="label-unit">mg/dL (normal: 0.7–1.3)</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="serum_creatinine"
                      type="number"
                      step="any"
                      min="0.1"
                      max="25"
                      placeholder="e.g. 1.1"
                      disabled={loading}
                      aria-required="true"
                      aria-invalid={!!fieldErrors.serum_creatinine}
                      aria-describedby={fieldErrors.serum_creatinine ? 'serum_creatinine-error' : undefined}
                      className={`form-input ${fieldErrors.serum_creatinine ? 'has-error' : ''}`}
                      value={formData.serum_creatinine}
                      onChange={(e) => handleInputChange('serum_creatinine', e.target.value)}
                    />
                  </div>
                  {fieldErrors.serum_creatinine && (
                    <span id="serum_creatinine-error" className="error-text">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      {fieldErrors.serum_creatinine}
                    </span>
                  )}
                </div>

                {/* Serum Sodium */}
                <div className="form-group">
                  <label className="form-label" htmlFor="serum_sodium">
                    <span>
                      Serum Sodium <span className="required-indicator" title="Required">*</span>
                    </span>
                    <span className="label-unit">mEq/L (normal: 135–145)</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="serum_sodium"
                      type="number"
                      step="any"
                      min="50"
                      max="200"
                      placeholder="e.g. 137"
                      disabled={loading}
                      aria-required="true"
                      aria-invalid={!!fieldErrors.serum_sodium}
                      aria-describedby={fieldErrors.serum_sodium ? 'serum_sodium-error' : undefined}
                      className={`form-input ${fieldErrors.serum_sodium ? 'has-error' : ''}`}
                      value={formData.serum_sodium}
                      onChange={(e) => handleInputChange('serum_sodium', e.target.value)}
                    />
                  </div>
                  {fieldErrors.serum_sodium && (
                    <span id="serum_sodium-error" className="error-text">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      {fieldErrors.serum_sodium}
                    </span>
                  )}
                </div>

                {/* Platelets */}
                <div className="form-group">
                  <label className="form-label" htmlFor="platelets">
                    <span>
                      Platelets <span className="required-indicator" title="Required">*</span>
                    </span>
                    <span className="label-unit">cells/mL (normal: 150k–400k)</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="platelets"
                      type="number"
                      step="any"
                      placeholder="e.g. 260000"
                      disabled={loading}
                      aria-required="true"
                      aria-invalid={!!fieldErrors.platelets}
                      aria-describedby={fieldErrors.platelets ? 'platelets-error' : undefined}
                      className={`form-input ${fieldErrors.platelets ? 'has-error' : ''}`}
                      value={formData.platelets}
                      onChange={(e) => handleInputChange('platelets', e.target.value)}
                    />
                  </div>
                  {fieldErrors.platelets && (
                    <span id="platelets-error" className="error-text">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      {fieldErrors.platelets}
                    </span>
                  )}
                </div>

                {/* Creatinine Phosphokinase (CPK) */}
                <div className="form-group">
                  <label className="form-label" htmlFor="creatinine_phosphokinase">
                    <span>
                      Creatinine Phosphokinase <span className="required-indicator" title="Required">*</span>
                    </span>
                    <span className="label-unit">mcg/L (normal: 10–120)</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="creatinine_phosphokinase"
                      type="number"
                      step="any"
                      placeholder="e.g. 250"
                      disabled={loading}
                      aria-required="true"
                      aria-invalid={!!fieldErrors.creatinine_phosphokinase}
                      aria-describedby={fieldErrors.creatinine_phosphokinase ? 'creatinine_phosphokinase-error' : undefined}
                      className={`form-input ${fieldErrors.creatinine_phosphokinase ? 'has-error' : ''}`}
                      value={formData.creatinine_phosphokinase}
                      onChange={(e) => handleInputChange('creatinine_phosphokinase', e.target.value)}
                    />
                  </div>
                  {fieldErrors.creatinine_phosphokinase && (
                    <span id="creatinine_phosphokinase-error" className="error-text">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      {fieldErrors.creatinine_phosphokinase}
                    </span>
                  )}
                </div>
              </div>

              {/* Section 2: Binary & Demographic Indicators */}
              <div className="form-section-header">
                <span className="section-step">2</span>
                <div>
                  <h3 className="form-section-heading">Binary &amp; Demographic Indicators</h3>
                  <p className="form-section-sub">Documented clinical conditions and baseline demographic profile</p>
                </div>
              </div>

              <div className="form-grid">
                {/* Sex */}
                <div className="form-group">
                  <label className="form-label" id="label-sex">
                    <span>
                      Biological Sex <span className="required-indicator" title="Required">*</span>
                    </span>
                  </label>
                  <div className="toggle-group" role="radiogroup" aria-labelledby="label-sex">
                    <button
                      type="button"
                      role="radio"
                      aria-checked={formData.sex === 0}
                      disabled={loading}
                      className={`toggle-option ${formData.sex === 0 ? 'active' : ''}`}
                      onClick={() => handleInputChange('sex', 0)}
                    >
                      Female
                    </button>
                    <button
                      type="button"
                      role="radio"
                      aria-checked={formData.sex === 1}
                      disabled={loading}
                      className={`toggle-option ${formData.sex === 1 ? 'active' : ''}`}
                      onClick={() => handleInputChange('sex', 1)}
                    >
                      Male
                    </button>
                  </div>
                </div>

                {/* Anaemia */}
                <div className="form-group">
                  <label className="form-label" id="label-anaemia">
                    <span>
                      Anaemia <span className="required-indicator" title="Required">*</span>
                    </span>
                    <span className="label-unit">Hb &lt; 12 g/dL</span>
                  </label>
                  <div className="toggle-group" role="radiogroup" aria-labelledby="label-anaemia">
                    <button
                      type="button"
                      role="radio"
                      aria-checked={formData.anaemia === 0}
                      disabled={loading}
                      className={`toggle-option ${formData.anaemia === 0 ? 'active' : ''}`}
                      onClick={() => handleInputChange('anaemia', 0)}
                    >
                      No
                    </button>
                    <button
                      type="button"
                      role="radio"
                      aria-checked={formData.anaemia === 1}
                      disabled={loading}
                      className={`toggle-option ${formData.anaemia === 1 ? 'active' : ''}`}
                      onClick={() => handleInputChange('anaemia', 1)}
                    >
                      Yes
                    </button>
                  </div>
                </div>

                {/* Diabetes */}
                <div className="form-group">
                  <label className="form-label" id="label-diabetes">
                    <span>
                      Diabetes Diagnosis <span className="required-indicator" title="Required">*</span>
                    </span>
                  </label>
                  <div className="toggle-group" role="radiogroup" aria-labelledby="label-diabetes">
                    <button
                      type="button"
                      role="radio"
                      aria-checked={formData.diabetes === 0}
                      disabled={loading}
                      className={`toggle-option ${formData.diabetes === 0 ? 'active' : ''}`}
                      onClick={() => handleInputChange('diabetes', 0)}
                    >
                      No
                    </button>
                    <button
                      type="button"
                      role="radio"
                      aria-checked={formData.diabetes === 1}
                      disabled={loading}
                      className={`toggle-option ${formData.diabetes === 1 ? 'active' : ''}`}
                      onClick={() => handleInputChange('diabetes', 1)}
                    >
                      Yes
                    </button>
                  </div>
                </div>

                {/* High Blood Pressure */}
                <div className="form-group">
                  <label className="form-label" id="label-hbp">
                    <span>
                      High Blood Pressure <span className="required-indicator" title="Required">*</span>
                    </span>
                    <span className="label-unit">Hypertension history</span>
                  </label>
                  <div className="toggle-group" role="radiogroup" aria-labelledby="label-hbp">
                    <button
                      type="button"
                      role="radio"
                      aria-checked={formData.high_blood_pressure === 0}
                      disabled={loading}
                      className={`toggle-option ${formData.high_blood_pressure === 0 ? 'active' : ''}`}
                      onClick={() => handleInputChange('high_blood_pressure', 0)}
                    >
                      No
                    </button>
                    <button
                      type="button"
                      role="radio"
                      aria-checked={formData.high_blood_pressure === 1}
                      disabled={loading}
                      className={`toggle-option ${formData.high_blood_pressure === 1 ? 'active' : ''}`}
                      onClick={() => handleInputChange('high_blood_pressure', 1)}
                    >
                      Yes
                    </button>
                  </div>
                </div>

                {/* Smoking */}
                <div className="form-group">
                  <label className="form-label" id="label-smoking">
                    <span>
                      Smoking Habit <span className="required-indicator" title="Required">*</span>
                    </span>
                    <span className="label-unit">Active tobacco use</span>
                  </label>
                  <div className="toggle-group" role="radiogroup" aria-labelledby="label-smoking">
                    <button
                      type="button"
                      role="radio"
                      aria-checked={formData.smoking === 0}
                      disabled={loading}
                      className={`toggle-option ${formData.smoking === 0 ? 'active' : ''}`}
                      onClick={() => handleInputChange('smoking', 0)}
                    >
                      No
                    </button>
                    <button
                      type="button"
                      role="radio"
                      aria-checked={formData.smoking === 1}
                      disabled={loading}
                      className={`toggle-option ${formData.smoking === 1 ? 'active' : ''}`}
                      onClick={() => handleInputChange('smoking', 1)}
                    >
                      Yes
                    </button>
                  </div>
                </div>
              </div>

              {/* Section 3: Model Selection */}
              <div className="form-section-header">
                <span className="section-step">3</span>
                <div>
                  <h3 className="form-section-heading">Model Architecture</h3>
                  <p className="form-section-sub">Choose which trained machine learning model performs inference</p>
                </div>
              </div>

              <div className="model-select-group" role="radiogroup" aria-label="Select prediction model architecture">
                {MODELS.map((model) => (
                  <label
                    key={model.id}
                    className={`model-option${selectedModelId === model.id ? ' selected' : ''}`}
                    htmlFor={`model-${model.id}`}
                  >
                    <input
                      type="radio"
                      id={`model-${model.id}`}
                      name="model"
                      value={model.id}
                      checked={selectedModelId === model.id}
                      onChange={() => setSelectedModelId(model.id)}
                      disabled={loading}
                      className="model-radio"
                    />
                    <div className="model-option-icon" aria-hidden="true">
                      {model.id === 'lr' ? (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="18" y1="20" x2="18" y2="10" />
                          <line x1="12" y1="20" x2="12" y2="4" />
                          <line x1="6" y1="20" x2="6" y2="14" />
                          <line x1="2" y1="20" x2="22" y2="20" />
                        </svg>
                      ) : (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="5" r="3" />
                          <circle cx="5" cy="19" r="3" />
                          <circle cx="19" cy="19" r="3" />
                          <line x1="12" y1="8" x2="5" y2="16" />
                          <line x1="12" y1="8" x2="19" y2="16" />
                          <line x1="5" y1="19" x2="19" y2="19" />
                        </svg>
                      )}
                    </div>
                    <div className="model-option-text">
                      <div className="model-option-heading">
                        <span className="model-option-name">{model.label}</span>
                        <span className="model-badge">{model.tag}</span>
                      </div>
                      <span className="model-option-desc">{model.desc}</span>
                    </div>
                    {selectedModelId === model.id && (
                      <div className="model-option-check" aria-hidden="true">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      </div>
                    )}
                  </label>
                ))}
              </div>

              {/* Actions */}
              <div className="form-actions">
                <button
                  type="button"
                  id="btn-reset-form"
                  className="btn-secondary"
                  onClick={handleReset}
                  disabled={loading}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                    <path d="M3 3v5h5" />
                  </svg>
                  Reset Form
                </button>
                <button
                  type="submit"
                  id="btn-predict"
                  className="btn-primary"
                  disabled={loading}
                  aria-busy={loading}
                >
                  {loading ? (
                    <>
                      <span className="spinner" aria-hidden="true" />
                      <span>Calculating Mortality Risk&hellip;</span>
                    </>
                  ) : (
                    <>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                        <polyline points="22 4 12 14.01 9 11.01" />
                      </svg>
                      <span>Run {selectedModel.label} Prediction</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </section>

        {/* Results Card */}
        <aside className="card results-card" aria-label="Prediction assessment output" aria-live="polite">
          <div className="card-header">
            <div className="card-header-main">
              <h2 className="card-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
                Risk Assessment Output
              </h2>
              {result && (
                <span className="result-model-tag" title="Inference model">
                  {result.model}
                </span>
              )}
            </div>
            <p className="card-subtitle">
              Calculated probability and educational risk interpretation
            </p>
          </div>

          <div className="card-body">
            {loading ? (
              <div className="loading-state">
                <div className="loading-spinner-lg" aria-hidden="true" />
                <div className="loading-text-group">
                  <h4>Running {selectedModel.label} Inference&hellip;</h4>
                  <p>Processing patient clinical vector across calibrated decision weights.</p>
                </div>
              </div>
            ) : !result ? (
              <div className="empty-state">
                <div className="empty-icon" aria-hidden="true">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                  </svg>
                </div>
                <h3>Awaiting Patient Parameters</h3>
                <p>
                  Configure the 11 clinical biomarkers and select a model, then click <strong>Run Prediction</strong> to generate risk probability.
                </p>
                <div className="empty-quick-fill">
                  <span>Need quick sample data?</span>
                  <div className="empty-presets">
                    <button type="button" className="btn-mini-preset" onClick={() => loadPreset(PRESET_LOW_RISK)}>
                      Load Low Risk
                    </button>
                    <button type="button" className="btn-mini-preset" onClick={() => loadPreset(PRESET_HIGH_RISK)}>
                      Load High Risk
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="prediction-result">
                {/* Status Badge Card */}
                <div
                  className={`status-badge-card ${
                    result.predicted_class === 1 ? 'high-risk' : 'low-risk'
                  }`}
                >
                  <div className="status-badge-icon" aria-hidden="true">
                    {result.predicted_class === 1 ? (
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="8" x2="12" y2="12" />
                        <line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                    ) : (
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                        <polyline points="22 4 12 14.01 9 11.01" />
                      </svg>
                    )}
                  </div>
                  <div className="status-badge-content">
                    <span className="status-badge-caption">Predicted Model Classification</span>
                    <h3 className="outcome-label">{result.predicted_label}</h3>
                    <span className="outcome-binary-badge">
                      Class: <strong>{result.predicted_class}</strong> ({result.predicted_class === 1 ? 'High Mortality Event' : 'Surviving Event'})
                    </span>
                  </div>
                </div>

                {/* Probability Metric Container */}
                <div className="metric-container">
                  <div className="metric-header">
                    <div>
                      <span className="metric-title">Statistical Mortality Risk</span>
                      <span className="metric-caption">Estimated likelihood over study window</span>
                    </div>
                    <span
                      className="metric-value"
                      style={{ color: getProbabilityColor(result.predicted_probability) }}
                    >
                      {(result.predicted_probability * 100).toFixed(1)}%
                    </span>
                  </div>

                  <div className="progress-bar-bg" role="progressbar" aria-valuenow={Math.round(result.predicted_probability * 100)} aria-valuemin="0" aria-valuemax="100">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${Math.min(100, Math.max(0, result.predicted_probability * 100))}%`,
                        backgroundColor: getProbabilityColor(result.predicted_probability),
                      }}
                    />
                  </div>

                  <div className="probability-scale" aria-hidden="true">
                    <span>0% (Low)</span>
                    <span className="scale-marker">35% Threshold</span>
                    <span className="scale-marker">60% Elevated</span>
                    <span>100%</span>
                  </div>
                </div>

                {/* Metadata & Risk Tier Rows */}
                <div className="result-data-group">
                  <div className="result-data-row">
                    <span className="result-data-label">Assigned Risk Tier</span>
                    <span
                      className="risk-level-chip"
                      style={{
                        background: `${getProbabilityColor(result.predicted_probability)}15`,
                        color: getProbabilityColor(result.predicted_probability),
                        borderColor: `${getProbabilityColor(result.predicted_probability)}35`,
                      }}
                    >
                      {getRiskLevel(result.predicted_probability)}
                    </span>
                  </div>

                  <div className="result-data-row">
                    <span className="result-data-label">Evaluation Architecture</span>
                    <span className="result-data-value">{result.model}</span>
                  </div>
                </div>

                {/* Algorithmic Output Explanation */}
                <div className="result-explanation">
                  <h4>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="16" x2="12" y2="12" />
                      <line x1="12" y1="8" x2="12.01" y2="8" />
                    </svg>
                    Algorithmic Interpretation
                  </h4>
                  <p>
                    {result.predicted_class === 1
                      ? 'The model detects high-risk clinical patterns (such as reduced ejection fraction, elevated creatinine, or compounding morbidities) correlated with increased mortality risk in patient records.'
                      : 'The model identified biomarker combinations consistent with higher survival probability (such as preserved ejection fraction and balanced serum electrolytes).'}
                  </p>
                </div>

                {/* Clinical Notice */}
                <div className="result-notice">
                  <strong>Notice: </strong>
                  {result.notice || 'Educational prototype only; not for clinical diagnosis or treatment.'}
                </div>
              </div>
            )}
          </div>
        </aside>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>Heart Failure Mortality Risk Predictor &bull; Educational Machine Learning Prototype &bull; Not for clinical decision-making</p>
      </footer>
    </div>
  )
}
