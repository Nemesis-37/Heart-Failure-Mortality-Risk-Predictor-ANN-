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
  creatinine_phosphokinase: '168',
  ejection_fraction: '45',
  platelets: '276000',
  serum_creatinine: '0.9',
  serum_sodium: '140',
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
  smoking: 1,
}

const MODELS = [
  {
    id: 'lr',
    label: 'Logistic Regression',
    endpoint: '/api/predict',
    fallbackEndpoint: 'http://127.0.0.1:8000/predict',
    desc: 'Classical ML baseline · interpretable',
  },
  {
    id: 'ann',
    label: 'Artificial Neural Network',
    endpoint: '/api/predict-ann',
    fallbackEndpoint: 'http://127.0.0.1:8000/predict-ann',
    desc: 'Deep learning · non-linear patterns',
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
      const errors = { ...prev }
      delete errors[field]
      return errors
    })
  }

  const validate = () => {
    const errors = {}
    const rules = [
      ['age', 1, 120, 'Age must be between 1 and 120'],
      ['creatinine_phosphokinase', 0, Infinity, 'CPK must be a positive number'],
      ['ejection_fraction', 1, 100, 'Ejection fraction must be between 1% and 100%'],
      ['platelets', 0, Infinity, 'Platelet count must be a positive number'],
      ['serum_creatinine', 0, Infinity, 'Serum creatinine must be a positive number'],
      ['serum_sodium', 0, Infinity, 'Serum sodium must be a positive number'],
    ]

    rules.forEach(([field, min, max, message]) => {
      const rawVal = String(formData[field] || '').trim()
      const value = Number(rawVal)

      if (
        rawVal === '' ||
        !Number.isFinite(value) ||
        value < min ||
        value > max ||
        (min === 0 && value <= 0)
      ) {
        errors[field] = message
      }
    })

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setApiError(null)
    setResult(null)

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
        throw new Error(data.detail || `Server error: ${response.status}`)
      }

      setResult(data)
      setBackendStatus('online')
    } catch (error) {
      setApiError(error.message || 'Could not connect to the prediction API.')
      setBackendStatus('offline')
    } finally {
      setLoading(false)
    }
  }

  const loadPreset = (preset) => {
    setFormData({ ...preset })
    setFieldErrors({})
    setApiError(null)
    setResult(null)
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
    if (probability < 0.35) return 'Low Risk'
    if (probability < 0.6) return 'Moderate Risk'
    return 'High Risk'
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-icon">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
            </svg>
          </div>
          <div>
            <h1 className="brand-title">Heart Failure Mortality Risk Predictor</h1>
            <p className="brand-subtitle">
              Educational Machine Learning Prototype &bull; Not for clinical use
            </p>
          </div>
        </div>

        <div className="header-status" title={`Backend API: ${backendStatus}`}>
          <span className={`status-dot ${backendStatus}`} aria-hidden="true" />
          <span>
            {backendStatus === 'online'
              ? 'API Online'
              : backendStatus === 'offline'
              ? 'API Offline'
              : 'Connecting…'}
          </span>
        </div>
      </header>

      {/* Educational Disclaimer */}
      <div className="disclaimer-banner" role="note">
        <span className="disclaimer-banner-icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
        </span>
        <p>
          <strong>Educational Prototype Only.</strong> This tool is a machine-learning
          demonstration and is <strong>not intended for medical diagnosis, treatment, or
          clinical decision-making.</strong> Always consult a qualified healthcare professional.
        </p>
      </div>

      {/* Quick Presets */}
      <div className="presets-bar">
        <span className="presets-label">Quick fill:</span>
        <button
          type="button"
          id="preset-low-risk"
          className="preset-btn preset-low"
          onClick={() => loadPreset(PRESET_LOW_RISK)}
        >
          Low Risk Sample
        </button>
        <button
          type="button"
          id="preset-high-risk"
          className="preset-btn preset-high"
          onClick={() => loadPreset(PRESET_HIGH_RISK)}
        >
          High Risk Sample
        </button>
        <button
          type="button"
          id="btn-reset-defaults"
          className="preset-btn btn-reset"
          onClick={handleReset}
        >
          Reset
        </button>
      </div>

      {/* Main Grid */}
      <main className="dashboard-grid">
        {/* Input Form Card */}
        <section className="card">
          <div className="card-header">
            <h2 className="card-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
              Patient Clinical Parameters
            </h2>
          </div>
          <div className="card-body">
            {apiError && (
              <div className="alert-banner error">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <div>
                  <strong>Error: </strong>
                  {apiError} (Please verify that the backend is running at http://127.0.0.1:8000)
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="form-section-title">1. Quantitative Measurements</div>
              <div className="form-grid">
                {/* Age */}
                <div className="form-group">
                  <label className="form-label" htmlFor="age">
                    <span>Age</span>
                    <span className="label-unit">years</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="age"
                      type="number"
                      step="any"
                      className={`form-input ${fieldErrors.age ? 'has-error' : ''}`}
                      value={formData.age}
                      onChange={(e) => handleInputChange('age', e.target.value)}
                    />
                  </div>
                  {fieldErrors.age && <span className="error-text">{fieldErrors.age}</span>}
                </div>

                {/* Ejection Fraction */}
                <div className="form-group">
                  <label className="form-label" htmlFor="ejection_fraction">
                    <span>Ejection Fraction</span>
                    <span className="label-unit">%</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="ejection_fraction"
                      type="number"
                      step="any"
                      className={`form-input ${fieldErrors.ejection_fraction ? 'has-error' : ''}`}
                      value={formData.ejection_fraction}
                      onChange={(e) => handleInputChange('ejection_fraction', e.target.value)}
                    />
                  </div>
                  {fieldErrors.ejection_fraction && (
                    <span className="error-text">{fieldErrors.ejection_fraction}</span>
                  )}
                </div>

                {/* Serum Creatinine */}
                <div className="form-group">
                  <label className="form-label" htmlFor="serum_creatinine">
                    <span>Serum Creatinine</span>
                    <span className="label-unit">mg/dL</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="serum_creatinine"
                      type="number"
                      step="any"
                      className={`form-input ${fieldErrors.serum_creatinine ? 'has-error' : ''}`}
                      value={formData.serum_creatinine}
                      onChange={(e) => handleInputChange('serum_creatinine', e.target.value)}
                    />
                  </div>
                  {fieldErrors.serum_creatinine && (
                    <span className="error-text">{fieldErrors.serum_creatinine}</span>
                  )}
                </div>

                {/* Serum Sodium */}
                <div className="form-group">
                  <label className="form-label" htmlFor="serum_sodium">
                    <span>Serum Sodium</span>
                    <span className="label-unit">mEq/L</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="serum_sodium"
                      type="number"
                      step="any"
                      className={`form-input ${fieldErrors.serum_sodium ? 'has-error' : ''}`}
                      value={formData.serum_sodium}
                      onChange={(e) => handleInputChange('serum_sodium', e.target.value)}
                    />
                  </div>
                  {fieldErrors.serum_sodium && (
                    <span className="error-text">{fieldErrors.serum_sodium}</span>
                  )}
                </div>

                {/* Platelets */}
                <div className="form-group">
                  <label className="form-label" htmlFor="platelets">
                    <span>Platelets</span>
                    <span className="label-unit">cells/mL</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="platelets"
                      type="number"
                      step="any"
                      className={`form-input ${fieldErrors.platelets ? 'has-error' : ''}`}
                      value={formData.platelets}
                      onChange={(e) => handleInputChange('platelets', e.target.value)}
                    />
                  </div>
                  {fieldErrors.platelets && (
                    <span className="error-text">{fieldErrors.platelets}</span>
                  )}
                </div>

                {/* CPK */}
                <div className="form-group">
                  <label className="form-label" htmlFor="creatinine_phosphokinase">
                    <span>Creatinine Phosphokinase</span>
                    <span className="label-unit">mcg/L</span>
                  </label>
                  <div className="input-wrapper">
                    <input
                      id="creatinine_phosphokinase"
                      type="number"
                      step="any"
                      className={`form-input ${fieldErrors.creatinine_phosphokinase ? 'has-error' : ''}`}
                      value={formData.creatinine_phosphokinase}
                      onChange={(e) => handleInputChange('creatinine_phosphokinase', e.target.value)}
                    />
                  </div>
                  {fieldErrors.creatinine_phosphokinase && (
                    <span className="error-text">{fieldErrors.creatinine_phosphokinase}</span>
                  )}
                </div>
              </div>

              <div className="form-section-title">2. Binary & Demographic Indicators</div>
              <div className="form-grid">
                {/* Sex */}
                <div className="form-group">
                  <label className="form-label">
                    <span>Sex</span>
                  </label>
                  <div className="toggle-group">
                    <button
                      type="button"
                      className={`toggle-option ${formData.sex === 0 ? 'active' : ''}`}
                      onClick={() => handleInputChange('sex', 0)}
                    >
                      Female
                    </button>
                    <button
                      type="button"
                      className={`toggle-option ${formData.sex === 1 ? 'active' : ''}`}
                      onClick={() => handleInputChange('sex', 1)}
                    >
                      Male
                    </button>
                  </div>
                </div>

                {/* Anaemia */}
                <div className="form-group">
                  <label className="form-label">
                    <span>Anaemia</span>
                  </label>
                  <div className="toggle-group">
                    <button
                      type="button"
                      className={`toggle-option ${formData.anaemia === 0 ? 'active' : ''}`}
                      onClick={() => handleInputChange('anaemia', 0)}
                    >
                      No
                    </button>
                    <button
                      type="button"
                      className={`toggle-option ${formData.anaemia === 1 ? 'active' : ''}`}
                      onClick={() => handleInputChange('anaemia', 1)}
                    >
                      Yes
                    </button>
                  </div>
                </div>

                {/* Diabetes */}
                <div className="form-group">
                  <label className="form-label">
                    <span>Diabetes</span>
                  </label>
                  <div className="toggle-group">
                    <button
                      type="button"
                      className={`toggle-option ${formData.diabetes === 0 ? 'active' : ''}`}
                      onClick={() => handleInputChange('diabetes', 0)}
                    >
                      No
                    </button>
                    <button
                      type="button"
                      className={`toggle-option ${formData.diabetes === 1 ? 'active' : ''}`}
                      onClick={() => handleInputChange('diabetes', 1)}
                    >
                      Yes
                    </button>
                  </div>
                </div>

                {/* High Blood Pressure */}
                <div className="form-group">
                  <label className="form-label">
                    <span>High Blood Pressure</span>
                  </label>
                  <div className="toggle-group">
                    <button
                      type="button"
                      className={`toggle-option ${formData.high_blood_pressure === 0 ? 'active' : ''}`}
                      onClick={() => handleInputChange('high_blood_pressure', 0)}
                    >
                      No
                    </button>
                    <button
                      type="button"
                      className={`toggle-option ${formData.high_blood_pressure === 1 ? 'active' : ''}`}
                      onClick={() => handleInputChange('high_blood_pressure', 1)}
                    >
                      Yes
                    </button>
                  </div>
                </div>

                {/* Smoking */}
                <div className="form-group">
                  <label className="form-label">
                    <span>Smoking</span>
                  </label>
                  <div className="toggle-group">
                    <button
                      type="button"
                      className={`toggle-option ${formData.smoking === 0 ? 'active' : ''}`}
                      onClick={() => handleInputChange('smoking', 0)}
                    >
                      No
                    </button>
                    <button
                      type="button"
                      className={`toggle-option ${formData.smoking === 1 ? 'active' : ''}`}
                      onClick={() => handleInputChange('smoking', 1)}
                    >
                      Yes
                    </button>
                  </div>
                </div>
              </div>

              {/* Model Selection */}
              <div className="form-section-title">3 &middot; Prediction Model</div>
              <div className="model-select-group" role="radiogroup" aria-label="Select prediction model">
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
                      className="model-radio"
                    />
                    <div className="model-option-icon" aria-hidden="true">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="4" y="4" width="16" height="16" rx="2" />
                        <rect x="9" y="9" width="6" height="6" />
                        <line x1="9" y1="2" x2="9" y2="4" /><line x1="15" y1="2" x2="15" y2="4" />
                        <line x1="9" y1="20" x2="9" y2="22" /><line x1="15" y1="20" x2="15" y2="22" />
                        <line x1="20" y1="9" x2="22" y2="9" /><line x1="20" y1="14" x2="22" y2="14" />
                        <line x1="2" y1="9" x2="4" y2="9" /><line x1="2" y1="14" x2="4" y2="14" />
                      </svg>
                    </div>
                    <div className="model-option-text">
                      <span className="model-option-name">{model.label}</span>
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

              <div className="form-actions">
                <button
                  type="button"
                  id="btn-reset-form"
                  className="btn-secondary"
                  onClick={handleReset}
                >
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
                      <span>Calculating&hellip;</span>
                    </>
                  ) : (
                    <>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                        <polyline points="22 4 12 14.01 9 11.01" />
                      </svg>
                      <span>Run Prediction</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </section>

        {/* Results Card */}
        <aside className="card results-card" aria-label="Prediction results" aria-live="polite">
          <div className="card-header">
            <h2 className="card-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
              Risk Assessment Output
            </h2>
            {result && <span className="result-model-tag">{result.model}</span>}
          </div>
          <div className="card-body">
            {loading ? (<div className="loading-state"><div className="loading-spinner-lg" aria-hidden="true" /><p>Running <strong>{selectedModelId === 'ann' ? 'Artificial Neural Network' : 'Logistic Regression'}</strong> prediction&hellip;</p></div>) : !result ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="16" x2="12" y2="12" />
                    <line x1="12" y1="8" x2="12.01" y2="8" />
                  </svg>
                </div>
                <h3>No Prediction Yet</h3>
                <p>
                  Fill in the patient parameters and click <strong>Run Prediction</strong> to see the result.
                </p>
              </div>
            ) : (
              <div className="prediction-result">
                <div
                  className={`status-badge-card ${
                    result.predicted_class === 1 ? 'high-risk' : 'low-risk'
                  }`}
                >
                  <div className="status-badge-icon">
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
                    <h4>Predicted Outcome</h4>
                    <div className="outcome-label">{result.predicted_label}</div>
                  </div>
                </div>

                <div className="metric-container">
                  <div className="metric-header">
                    <span className="metric-title">Mortality Risk Probability</span>
                    <span
                      className="metric-value"
                      style={{ color: getProbabilityColor(result.predicted_probability) }}
                    >
                      {(result.predicted_probability * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="progress-bar-bg">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${Math.min(100, Math.max(0, result.predicted_probability * 100))}%`,
                        backgroundColor: getProbabilityColor(result.predicted_probability),
                      }}
                    />
                  </div>
                  <div className="probability-scale" aria-hidden="true">
                    <span>0% &mdash; Low</span>
                    <span>50%</span>
                    <span>High &mdash; 100%</span>
                  </div>
                </div>

                <div className="risk-level-row">
                  <span className="risk-level-label">Risk Level</span>
                  <span className="risk-level-chip" style={{ background: `${getProbabilityColor(result.predicted_probability)}18`, color: getProbabilityColor(result.predicted_probability), border: `1px solid ${getProbabilityColor(result.predicted_probability)}40` }}>{getRiskLevel(result.predicted_probability)}</span>
                </div>
                <div className="result-meta-row">
                  <span className="result-meta-label">Model</span>
                  <span className="result-meta-value">{result.model}</span>
                </div>
                <div className="result-notice">
                  <strong>&#9888; Notice: </strong>
                  {result.notice || 'Educational prototype only; not for clinical diagnosis or treatment.'}
                </div>
              </div>
            )}
          </div>
        </aside>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>Heart Failure Mortality Risk Predictor &bull; Educational Machine Learning Prototype &bull; Not for clinical use</p>
      </footer>
    </div>
  )
}
