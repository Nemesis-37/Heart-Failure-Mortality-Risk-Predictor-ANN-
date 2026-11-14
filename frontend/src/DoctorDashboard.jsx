import React, { useState, useEffect } from 'react'
import { saveAssessment, savePrediction } from './services/assessmentStore.js'

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
  sex: 1, // 0: Female, 1: Male (UCI dataset encoding)
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
    shortName: 'Linear Baseline',
    endpoint: '/api/predict',
    fallbackEndpoint: 'http://127.0.0.1:8000/predict',
    desc: 'Classical linear statistical baseline with interpretable feature coefficients.',
  },
  {
    id: 'ann',
    label: 'Artificial Neural Network',
    shortName: 'Deep ANN',
    endpoint: '/api/predict-ann',
    fallbackEndpoint: 'http://127.0.0.1:8000/predict-ann',
    desc: 'Multi-layer feed-forward network trained to capture non-linear biomarker interactions.',
  },
]

export default function DoctorDashboard({
  doctorUser,
  onLogout,
  embedded = false,
  initialRecord = null,
}) {
  const [formData, setFormData] = useState(() => {
    if (initialRecord) {
      return {
        age: String(initialRecord.age ?? '60'),
        anaemia: Number(initialRecord.anaemia ?? 0),
        creatinine_phosphokinase: String(initialRecord.creatinine_phosphokinase ?? '250'),
        diabetes: Number(initialRecord.diabetes ?? 0),
        ejection_fraction: String(initialRecord.ejection_fraction ?? '38'),
        high_blood_pressure: Number(initialRecord.high_blood_pressure ?? 0),
        platelets: String(initialRecord.platelets ?? '260000'),
        serum_creatinine: String(initialRecord.serum_creatinine ?? '1.1'),
        serum_sodium: String(initialRecord.serum_sodium ?? '137'),
        sex: Number(initialRecord.sex ?? 1),
        smoking: Number(initialRecord.smoking ?? 0),
      }
    }
    return INITIAL_STATE
  })
  const [fieldErrors, setFieldErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState(null)
  const [result, setResult] = useState(null)
  const [backendStatus, setBackendStatus] = useState('checking')
  const [selectedModelId, setSelectedModelId] = useState('lr')
  const [patientRef, setPatientRef] = useState(() => initialRecord?.patientReferenceId || '')

  // Clean doctor name to prevent any duplicated title like "Dr. Dr Carter"
  const cleanDoctorName = (doctorUser?.name || 'Doctor')
    .replace(/^Dr\.\s*Dr\.\s*/i, 'Dr. ')
    .replace(/^Dr\.\s*Dr\b/i, 'Dr. ')

  const cleanRole = doctorUser?.role || 'Attending Physician'

  const avatarInitials =
    doctorUser?.avatarInitials ||
    cleanDoctorName
      .replace(/^Dr\.\s*/i, '')
      .trim()
      .split(/\s+/)
      .map((w) => w[0])
      .join('')
      .slice(0, 2)
      .toUpperCase() ||
    'DR'

  useEffect(() => {
    checkHealth()
  }, [])

  const checkHealth = async () => {
    setBackendStatus('checking')
    try {
      const response = await fetch('/api/health')
      if (response.ok) {
        setBackendStatus('online')
        return
      }
    } catch {
      // Fallback probe direct to local FastAPI backend
    }

    try {
      const response = await fetch('http://127.0.0.1:8000/health')
      setBackendStatus(response.ok ? 'online' : 'offline')
    } catch {
      setBackendStatus('offline')
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
      ['creatinine_phosphokinase', 1, 10000, 'CPK must be a positive value (1–10,000 mcg/L)'],
      ['ejection_fraction', 1, 100, 'Ejection fraction must be between 1% and 100%'],
      ['platelets', 1, 1500000, 'Platelet count must be a positive number (cells/µL)'],
      ['serum_creatinine', 0.1, 25, 'Serum creatinine must be a positive value (0.1–25 mg/dL)'],
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

      const timestamp = new Date().toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })

      setResult({
        ...data,
        patientRef: patientRef.trim() || 'Anonymous Assessment',
        timestamp,
        threshold: 0.5,
      })
      setBackendStatus('online')

      // Record this clinical assessment into the assessment directory and prediction history
      try {
        const savedAssessment = saveAssessment({
          id: initialRecord?.id,
          assessmentCode: initialRecord?.assessmentCode,
          patientReferenceId: patientRef.trim() || null,
          doctorName: cleanDoctorName,
          doctorId: doctorUser?.email || 'DR-CURRENT',
          ...payload,
          model: data.model,
          predictedClass: data.predicted_class,
          predictedLabel: data.predicted_label,
          predictedProbability: data.predicted_probability,
          predictionTimestamp: timestamp,
        })

        savePrediction({
          assessmentId: savedAssessment.id,
          assessmentCode: savedAssessment.assessmentCode,
          patientReferenceId: patientRef.trim() || null,
          modelName: data.model,
          predictedClass: data.predicted_class,
          predictedLabel: data.predicted_label,
          predictedProbability: data.predicted_probability,
          classificationThreshold: 0.5,
          modelVersion: 'v1.0.0',
          inputs: { ...payload },
        })
      } catch (err) {
        console.warn('Could not auto-save assessment and prediction records:', err)
      }
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
    setPatientRef('')
    setFieldErrors({})
    setResult(null)
    setApiError(null)
  }

  const selectedModel = MODELS.find((m) => m.id === selectedModelId) || MODELS[0]

  return (
    <div className={`dashboard-page ${embedded ? 'embedded-view' : ''}`}>
      {/* Top Application Bar (only shown when not embedded in AppLayout) */}
      {!embedded && (
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
                <p className="topbar-subtitle">
                  Clinical Risk Assessment Workspace · Dual Model Architecture
                </p>
              </div>
            </div>

            <div className="topbar-right">
              {/* API Health Status Indicator */}
              <button
                type="button"
                className="topbar-status-pill"
                onClick={checkHealth}
                title={`API Status: ${backendStatus}. Click to check connection with /health.`}
                aria-label={`API Status: ${backendStatus}. Click to refresh health check.`}
              >
                <span className={`status-dot ${backendStatus}`} aria-hidden="true" />
                <span>
                  {backendStatus === 'online'
                    ? 'API Online'
                    : backendStatus === 'offline'
                    ? 'API Offline'
                    : 'Checking…'}
                </span>
              </button>

              {/* Doctor Profile Pill */}
              <div className="doctor-profile-pill" title={`${cleanDoctorName} — ${cleanRole}`}>
                <div className="doctor-avatar" aria-hidden="true">
                  {avatarInitials}
                </div>
                <div className="doctor-info">
                  <span className="doctor-name">{cleanDoctorName}</span>
                  <span className="doctor-role">{cleanRole}</span>
                </div>
              </div>

              {/* Logout Action */}
              <button
                type="button"
                className="btn-logout"
                onClick={onLogout}
                title="Sign out of doctor portal"
                aria-label="Logout"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                <span>Logout</span>
              </button>
            </div>
          </div>
        </header>
      )}

      {/* Main Container */}
      <div className={`dashboard-content-container ${embedded ? 'embedded-content' : ''}`}>
        {/* Doctor Welcome Banner */}
        <div className="doctor-welcome-card">
          <div className="welcome-text">
            <h2>{embedded ? 'Heart Failure Risk Prediction' : `Welcome back, ${cleanDoctorName}`}</h2>
            <p>
              {embedded
                ? 'Enter clinical parameters to generate a model-based prediction across the classical Logistic Regression baseline and the deep Artificial Neural Network.'
                : 'Evaluate patient risk by inputting the 11 clinical biomarkers below. Compare predictions across the classical Logistic Regression baseline and the deep Artificial Neural Network model.'}
            </p>
          </div>
          <div className="welcome-actions">
            <span className="presets-label">Quick Sample Profiles:</span>
            <div className="preset-buttons">
              <button
                type="button"
                className="btn-preset-pill preset-low"
                onClick={() => loadPreset(PRESET_LOW_RISK)}
                disabled={loading}
              >
                <span className="dot dot-low" aria-hidden="true" />
                <span>Low Risk Sample</span>
              </button>
              <button
                type="button"
                className="btn-preset-pill preset-high"
                onClick={() => loadPreset(PRESET_HIGH_RISK)}
                disabled={loading}
              >
                <span className="dot dot-high" aria-hidden="true" />
                <span>High Risk Sample</span>
              </button>
              <button
                type="button"
                className="btn-preset-pill preset-reset"
                onClick={handleReset}
                disabled={loading}
              >
                <span>Reset Defaults</span>
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
              <strong>Connection Error: </strong>
              <span>{apiError} (Ensure FastAPI backend is running via <code>python -m uvicorn main:app</code> at http://127.0.0.1:8000)</span>
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
              <span>Please review and correct the {Object.keys(fieldErrors).length} highlighted clinical parameter(s) before running inference.</span>
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
                <span className="card-counter-tag">11 Required Indicators</span>
              </div>
              <p className="card-subtitle">
                Enter documented clinical measurements, laboratory assays, and patient conditions.
              </p>
            </div>

            <div className="card-body">
              <form onSubmit={handleSubmit} noValidate>
                {/* Optional Patient Identification */}
                <div className="patient-ref-box">
                  <div className="patient-ref-header">
                    <label className="form-label" htmlFor="param-patient-ref">
                      <span className="label-with-tip">
                        Patient Reference ID <span className="optional-tag">(Optional)</span>
                        <span
                          className="tooltip-trigger"
                          title="Optional reference identifier (e.g. PT-2026-084) for audit tracking. Omit for anonymous patient evaluation."
                          tabIndex={0}
                          aria-label="Info: Patient Reference"
                        >
                          ℹ
                        </span>
                      </span>
                    </label>
                    <span className="anon-hint">Allows anonymous assessments when omitted</span>
                  </div>
                  <div className="patient-ref-input-wrap">
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                    <input
                      id="param-patient-ref"
                      type="text"
                      placeholder="e.g. PT-2026-084 (or leave blank for anonymous)"
                      className="form-input patient-ref-input"
                      value={patientRef}
                      onChange={(e) => setPatientRef(e.target.value)}
                      disabled={loading}
                      maxLength={40}
                    />
                  </div>
                </div>

                {/* Group 1: Quantitative Measurements */}
                <div className="form-group-section">
                  <div className="section-title-row">
                    <span className="section-num">1</span>
                    <div>
                      <h3 className="section-heading">Quantitative Measurements &amp; Laboratory Assays</h3>
                      <p className="section-desc">Continuous biometric values and laboratory findings</p>
                    </div>
                  </div>

                  <div className="form-grid">
                    {/* 1. Age */}
                    <div className="form-field">
                      <label className="form-label" htmlFor="param-age">
                        <span className="label-with-tip">
                          Age <span className="req-star" title="Required">*</span>
                          <span className="tooltip-trigger" title="Patient age in years (cohort range: 40–95 years)" tabIndex={0} aria-label="Info: Patient age in years">ℹ</span>
                        </span>
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
                        <span className="label-with-tip">
                          Ejection Fraction <span className="req-star" title="Required">*</span>
                          <span className="tooltip-trigger" title="Percentage of blood leaving the left ventricle during each contraction (normal: 50–70%)" tabIndex={0} aria-label="Info: Ejection Fraction normal range 50-70%">ℹ</span>
                        </span>
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
                        <span className="label-with-tip">
                          Serum Creatinine <span className="req-star" title="Required">*</span>
                          <span className="tooltip-trigger" title="Blood creatinine concentration indicating renal filtration function (normal: 0.7–1.3 mg/dL)" tabIndex={0} aria-label="Info: Serum Creatinine normal range 0.7-1.3 mg/dL">ℹ</span>
                        </span>
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
                        <span className="label-with-tip">
                          Serum Sodium <span className="req-star" title="Required">*</span>
                          <span className="tooltip-trigger" title="Blood sodium electrolyte concentration (normal: 135–145 mEq/L)" tabIndex={0} aria-label="Info: Serum Sodium normal range 135-145 mEq/L">ℹ</span>
                        </span>
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
                        <span className="label-with-tip">
                          Platelets <span className="req-star" title="Required">*</span>
                          <span className="tooltip-trigger" title="Circulating blood platelet count (normal: 150,000–450,000 cells/µL)" tabIndex={0} aria-label="Info: Platelets normal range 150,000-450,000 cells/µL">ℹ</span>
                        </span>
                        <span className="field-unit">cells/µL (norm: 150k–450k)</span>
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
                        <span className="label-with-tip">
                          Creatinine Phosphokinase <span className="req-star" title="Required">*</span>
                          <span className="tooltip-trigger" title="Cardiac/muscular enzyme CPK concentration (normal: 10–120 mcg/L)" tabIndex={0} aria-label="Info: CPK normal range 10-120 mcg/L">ℹ</span>
                        </span>
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

                {/* Group 2: Binary & Demographic Indicators */}
                <div className="form-group-section">
                  <div className="section-title-row">
                    <span className="section-num">2</span>
                    <div>
                      <h3 className="section-heading">Binary &amp; Demographic Indicators</h3>
                      <p className="section-desc">Documented binary clinical conditions and patient demographics</p>
                    </div>
                  </div>

                  <div className="form-grid">
                    {/* 7. Biological Sex */}
                    <div className="form-field">
                      <label className="form-label" id="lbl-sex">
                        <span className="label-with-tip">
                          Biological Sex <span className="req-star" title="Required">*</span>
                          <span className="tooltip-trigger" title="Documented biological sex encoded in UCI cohort (0 = Female, 1 = Male)" tabIndex={0} aria-label="Info: Biological sex encoding">ℹ</span>
                        </span>
                        <span className="field-unit">0 = Female, 1 = Male</span>
                      </label>
                      <div className={`segmented-toggle sliding-segmented-toggle ${formData.sex === 1 ? 'pos-right' : 'pos-left'}`} role="radiogroup" aria-labelledby="lbl-sex">
                        <div className="segmented-sliding-glider" aria-hidden="true" />
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.sex === 0}
                          className={`toggle-btn segmented-opt-btn ${formData.sex === 0 ? 'active' : ''}`}
                          onClick={() => handleInputChange('sex', 0)}
                          disabled={loading}
                        >
                          Female (0)
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.sex === 1}
                          className={`toggle-btn segmented-opt-btn ${formData.sex === 1 ? 'active' : ''}`}
                          onClick={() => handleInputChange('sex', 1)}
                          disabled={loading}
                        >
                          Male (1)
                        </button>
                      </div>
                    </div>

                    {/* 8. Anaemia */}
                    <div className="form-field">
                      <label className="form-label" id="lbl-anaemia">
                        <span className="label-with-tip">
                          Anaemia <span className="req-star" title="Required">*</span>
                          <span className="tooltip-trigger" title="Decrease in red blood cells or haemoglobin level (haemoglobin < 12 g/dL)" tabIndex={0} aria-label="Info: Anaemia Hb < 12 g/dL">ℹ</span>
                        </span>
                        <span className="field-unit">Hb &lt; 12 g/dL</span>
                      </label>
                      <div className={`segmented-toggle sliding-segmented-toggle ${formData.anaemia === 1 ? 'pos-right' : 'pos-left'}`} role="radiogroup" aria-labelledby="lbl-anaemia">
                        <div className="segmented-sliding-glider" aria-hidden="true" />
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.anaemia === 0}
                          className={`toggle-btn segmented-opt-btn ${formData.anaemia === 0 ? 'active' : ''}`}
                          onClick={() => handleInputChange('anaemia', 0)}
                          disabled={loading}
                        >
                          No (0)
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.anaemia === 1}
                          className={`toggle-btn segmented-opt-btn ${formData.anaemia === 1 ? 'active' : ''}`}
                          onClick={() => handleInputChange('anaemia', 1)}
                          disabled={loading}
                        >
                          Yes (1)
                        </button>
                      </div>
                    </div>

                    {/* 9. Diabetes */}
                    <div className="form-field">
                      <label className="form-label" id="lbl-diabetes">
                        <span className="label-with-tip">
                          Diabetes Diagnosis <span className="req-star" title="Required">*</span>
                          <span className="tooltip-trigger" title="Confirmed clinical diagnosis of diabetic metabolic condition" tabIndex={0} aria-label="Info: Diabetes condition">ℹ</span>
                        </span>
                        <span className="field-unit">Diagnosed</span>
                      </label>
                      <div className={`segmented-toggle sliding-segmented-toggle ${formData.diabetes === 1 ? 'pos-right' : 'pos-left'}`} role="radiogroup" aria-labelledby="lbl-diabetes">
                        <div className="segmented-sliding-glider" aria-hidden="true" />
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.diabetes === 0}
                          className={`toggle-btn segmented-opt-btn ${formData.diabetes === 0 ? 'active' : ''}`}
                          onClick={() => handleInputChange('diabetes', 0)}
                          disabled={loading}
                        >
                          No (0)
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.diabetes === 1}
                          className={`toggle-btn segmented-opt-btn ${formData.diabetes === 1 ? 'active' : ''}`}
                          onClick={() => handleInputChange('diabetes', 1)}
                          disabled={loading}
                        >
                          Yes (1)
                        </button>
                      </div>
                    </div>

                    {/* 10. High Blood Pressure */}
                    <div className="form-field">
                      <label className="form-label" id="lbl-hbp">
                        <span className="label-with-tip">
                          High Blood Pressure <span className="req-star" title="Required">*</span>
                          <span className="tooltip-trigger" title="Documented clinical history of arterial hypertension" tabIndex={0} aria-label="Info: Hypertension">ℹ</span>
                        </span>
                        <span className="field-unit">Hypertension</span>
                      </label>
                      <div className={`segmented-toggle sliding-segmented-toggle ${formData.high_blood_pressure === 1 ? 'pos-right' : 'pos-left'}`} role="radiogroup" aria-labelledby="lbl-hbp">
                        <div className="segmented-sliding-glider" aria-hidden="true" />
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.high_blood_pressure === 0}
                          className={`toggle-btn segmented-opt-btn ${formData.high_blood_pressure === 0 ? 'active' : ''}`}
                          onClick={() => handleInputChange('high_blood_pressure', 0)}
                          disabled={loading}
                        >
                          No (0)
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.high_blood_pressure === 1}
                          className={`toggle-btn segmented-opt-btn ${formData.high_blood_pressure === 1 ? 'active' : ''}`}
                          onClick={() => handleInputChange('high_blood_pressure', 1)}
                          disabled={loading}
                        >
                          Yes (1)
                        </button>
                      </div>
                    </div>

                    {/* 11. Smoking */}
                    <div className="form-field">
                      <label className="form-label" id="lbl-smoking">
                        <span className="label-with-tip">
                          Smoking History <span className="req-star" title="Required">*</span>
                          <span className="tooltip-trigger" title="Active or established tobacco consumption habit" tabIndex={0} aria-label="Info: Active smoking habit">ℹ</span>
                        </span>
                        <span className="field-unit">Active tobacco</span>
                      </label>
                      <div className={`segmented-toggle sliding-segmented-toggle ${formData.smoking === 1 ? 'pos-right' : 'pos-left'}`} role="radiogroup" aria-labelledby="lbl-smoking">
                        <div className="segmented-sliding-glider" aria-hidden="true" />
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.smoking === 0}
                          className={`toggle-btn segmented-opt-btn ${formData.smoking === 0 ? 'active' : ''}`}
                          onClick={() => handleInputChange('smoking', 0)}
                          disabled={loading}
                        >
                          No (0)
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData.smoking === 1}
                          className={`toggle-btn segmented-opt-btn ${formData.smoking === 1 ? 'active' : ''}`}
                          onClick={() => handleInputChange('smoking', 1)}
                          disabled={loading}
                        >
                          Yes (1)
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
                      <p className="section-desc">Select which machine learning architecture computes inference</p>
                    </div>
                  </div>

                  <div className="model-selection-grid" role="radiogroup" aria-label="Prediction model selection">
                    {MODELS.map((m) => {
                      const isSelected = selectedModelId === m.id
                      return (
                        <label
                          key={m.id}
                          htmlFor={`model-choice-${m.id}`}
                          className={`model-card ${isSelected ? 'selected' : ''}`}
                        >
                          <input
                            id={`model-choice-${m.id}`}
                            type="radio"
                            name="model_choice"
                            value={m.id}
                            checked={isSelected}
                            onChange={() => setSelectedModelId(m.id)}
                            disabled={loading}
                            className="model-radio-input"
                          />
                          <div className="model-card-top">
                            <div className="model-title-group">
                              <div className="model-icon-badge" aria-hidden="true">
                                {m.id === 'lr' ? (
                                  /* Regression chart icon */
                                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <line x1="3" y1="20" x2="21" y2="20" />
                                    <line x1="3" y1="4" x2="3" y2="20" />
                                    <polyline points="4 16 10 11 15 14 21 6" />
                                  </svg>
                                ) : (
                                  /* Neural network nodes icon */
                                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <circle cx="5" cy="6" r="2.5" />
                                    <circle cx="5" cy="18" r="2.5" />
                                    <circle cx="12" cy="12" r="2.5" />
                                    <circle cx="19" cy="6" r="2.5" />
                                    <circle cx="19" cy="18" r="2.5" />
                                    <line x1="7.5" y1="7" x2="9.5" y2="11" />
                                    <line x1="7.5" y1="17" x2="9.5" y2="13" />
                                    <line x1="14.5" y1="11" x2="16.5" y2="7" />
                                    <line x1="14.5" y1="13" x2="16.5" y2="17" />
                                  </svg>
                                )}
                              </div>
                              <span className="model-title">{m.label}</span>
                            </div>
                            <span className="model-endpoint-pill">
                              {m.id === 'lr' ? 'POST /predict' : 'POST /predict-ann'}
                            </span>
                          </div>
                          <p className="model-desc">{m.desc}</p>
                          <div className="model-card-footer">
                            <span className="model-indicator-check">
                              {isSelected ? '● Selected Architecture' : '○ Click to Select'}
                            </span>
                          </div>
                        </label>
                      )
                    })}
                  </div>
                </div>

                {/* Form Action Buttons */}
                <div className="form-action-bar">
                  <button
                    type="button"
                    className="btn-secondary btn-reset-form"
                    onClick={handleReset}
                    disabled={loading}
                    title="Reset all patient fields to default values"
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
                        <span>Analyzing patient data...</span>
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

          {/* Right Column: Prediction Results Panel */}
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
                  <div className="result-header-tags">
                    <span className="result-model-tag">
                      {result.model}
                    </span>
                    {result.patientRef && result.patientRef !== 'Anonymous Assessment' && (
                      <span className="result-ref-tag">
                        {result.patientRef}
                      </span>
                    )}
                  </div>
                )}
              </div>
              <p className="card-subtitle">
                Model output derived strictly from the FastAPI backend response
              </p>
            </div>

            <div className="card-body">
              {/* State A: Loading State */}
              {loading ? (
                <div className="result-state-box loading-state">
                  <div className="clean-spinner-lg" aria-hidden="true" />
                  <h3>Analyzing Patient Data...</h3>
                  <p>
                    Transmitting clinical parameters to <strong>{selectedModel.label}</strong> endpoint.
                  </p>
                </div>
              ) : !result ? (
                /* State B: Empty Initial State (Ready for Analysis) */
                <div className="result-state-box empty-state">
                  <div className="empty-icon-circle" aria-hidden="true">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                    </svg>
                  </div>
                  <h3>Ready for Analysis</h3>
                  <p>
                    Enter patient clinical parameters on the left, select a model architecture, and click <strong>Run Prediction</strong> to generate results.
                  </p>
                  <div className="empty-state-guide">
                    <span className="guide-chip">Dual Model Comparison</span>
                    <span className="guide-chip">11 Clinical Features</span>
                  </div>
                </div>
              ) : (
                /* State C: Active Clinical Prediction Result */
                <div className="clean-result-container">
                  {/* Predicted Outcome Banner */}
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
                      <span className="outcome-kicker">Predicted Classification</span>
                      <h3 className="outcome-label">{result.predicted_label}</h3>
                      <span className="outcome-class-code">
                        Model Output Class: <strong>{result.predicted_class}</strong> ({result.predicted_class === 1 ? 'Positive event: mortality risk predicted' : 'Negative event: no mortality predicted'})
                      </span>
                    </div>
                  </div>

                  {/* Predicted Mortality Probability Metric Card */}
                  <div className="probability-metric-card">
                    <div className="metric-header-row">
                      <div>
                        <span className="metric-heading">Estimated Death-Event Probability</span>
                        <p className="metric-subheading">Calculated risk score from input biomarkers</p>
                      </div>
                      <span className={`metric-percentage ${result.predicted_probability >= 0.5 ? 'elevated' : 'baseline'}`}>
                        {(result.predicted_probability * 100).toFixed(1)}%
                      </span>
                    </div>

                    {/* Horizontal Probability Bar */}
                    <div
                      className="clean-progress-track"
                      role="progressbar"
                      aria-valuenow={Math.round(result.predicted_probability * 100)}
                      aria-valuemin="0"
                      aria-valuemax="100"
                    >
                      <div
                        className={`clean-progress-fill ${result.predicted_probability >= 0.5 ? 'fill-elevated' : 'fill-baseline'}`}
                        style={{ width: `${Math.min(100, Math.max(0, result.predicted_probability * 100))}%` }}
                      />
                    </div>

                    <div className="metric-scale-labels" aria-hidden="true">
                      <span>0% (Baseline)</span>
                      <span className="threshold-indicator">50% Decision Threshold</span>
                      <span>100% (Maximum)</span>
                    </div>
                  </div>

                  {/* Key Response Meta Table */}
                  <div className="result-meta-table">
                    <div className="meta-row">
                      <span className="meta-label">Patient Reference</span>
                      <span className="meta-value font-mono">{result.patientRef}</span>
                    </div>
                    <div className="meta-row">
                      <span className="meta-label">Selected Model</span>
                      <span className="meta-value">{result.model}</span>
                    </div>
                    <div className="meta-row">
                      <span className="meta-label">Raw Probability Score</span>
                      <span className="meta-value font-mono">{result.predicted_probability}</span>
                    </div>
                    <div className="meta-row">
                      <span className="meta-label">Classification Threshold</span>
                      <span className="meta-value font-mono">0.50 (50.0%)</span>
                    </div>
                    {result.timestamp && (
                      <div className="meta-row">
                        <span className="meta-label">Inference Timestamp</span>
                        <span className="meta-value font-mono">{result.timestamp}</span>
                      </div>
                    )}
                    {result.notice && (
                      <div className="meta-row notice-row">
                        <span className="meta-label">Backend Notice</span>
                        <span className="meta-value">{result.notice}</span>
                      </div>
                    )}
                  </div>

                  {/* Educational Disclaimer */}
                  <div className="clean-disclaimer-box" role="note">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="16" x2="12" y2="12" />
                      <line x1="12" y1="8" x2="12.01" y2="8" />
                    </svg>
                    <p>
                      <strong>Educational ML Prototype:</strong> This software is a machine-learning research prototype and is not certified for clinical diagnosis, therapeutic decisions, or medical management.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </aside>
        </main>

        {/* Global Footer */}
        {!embedded && (
          <footer className="dashboard-footer">
            <p>
              Heart Failure Mortality Risk Predictor &bull; Educational Machine Learning Prototype &bull; Not for clinical diagnosis or medical decision-making
            </p>
          </footer>
        )}
      </div>
    </div>
  )
}
