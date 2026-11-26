import React, { useState } from 'react'
import { saveAssessment, savePrediction } from './services/assessmentStore.js'
import ThemeToggle from './components/ThemeToggle.jsx'
import DoctorProfilePhotoModal from './components/DoctorProfilePhotoModal.jsx'
import DoctorAvatar from './components/DoctorAvatar.jsx'
import { getPredictionCandidateUrls, refreshAccessToken } from './apiConfig.js'
import { safeParseResponse, parseApiError, extractFieldErrors } from './utils/apiErrorHelper.js'

const BLANK_FORM_STATE = {
  age: '',
  anaemia: null,
  creatinine_phosphokinase: '',
  diabetes: null,
  ejection_fraction: '',
  high_blood_pressure: null,
  platelets: '',
  serum_creatinine: '',
  serum_sodium: '',
  sex: null,
  smoking: null,
}

const EXAMPLE_INPUT_PROFILE = {
  patientRef: 'PT-2026-042',
  formData: {
    age: '68',
    anaemia: 1,
    creatinine_phosphokinase: '582',
    diabetes: 0,
    ejection_fraction: '30',
    high_blood_pressure: 1,
    platelets: '245000',
    serum_creatinine: '1.9',
    serum_sodium: '132',
    sex: 1,
    smoking: 0,
  },
}

function buildInitialState(initialRecord, initialDraft) {
  if (initialDraft?.formData) {
    return {
      patientRef: initialDraft.patientRef || '',
      formData: { ...BLANK_FORM_STATE, ...initialDraft.formData },
    }
  }
  if (initialRecord) {
    return {
      patientRef: initialRecord.patientReferenceId || '',
      formData: {
        age: initialRecord.age !== undefined && initialRecord.age !== null ? String(initialRecord.age) : '',
        anaemia: initialRecord.anaemia !== undefined && initialRecord.anaemia !== null ? Number(initialRecord.anaemia) : null,
        creatinine_phosphokinase:
          initialRecord.creatinine_phosphokinase !== undefined && initialRecord.creatinine_phosphokinase !== null
            ? String(initialRecord.creatinine_phosphokinase)
            : '',
        diabetes: initialRecord.diabetes !== undefined && initialRecord.diabetes !== null ? Number(initialRecord.diabetes) : null,
        ejection_fraction:
          initialRecord.ejection_fraction !== undefined && initialRecord.ejection_fraction !== null
            ? String(initialRecord.ejection_fraction)
            : '',
        high_blood_pressure:
          initialRecord.high_blood_pressure !== undefined && initialRecord.high_blood_pressure !== null
            ? Number(initialRecord.high_blood_pressure)
            : null,
        platelets: initialRecord.platelets !== undefined && initialRecord.platelets !== null ? String(initialRecord.platelets) : '',
        serum_creatinine:
          initialRecord.serum_creatinine !== undefined && initialRecord.serum_creatinine !== null
            ? String(initialRecord.serum_creatinine)
            : '',
        serum_sodium:
          initialRecord.serum_sodium !== undefined && initialRecord.serum_sodium !== null
            ? String(initialRecord.serum_sodium)
            : '',
        sex: initialRecord.sex !== undefined && initialRecord.sex !== null ? Number(initialRecord.sex) : null,
        smoking: initialRecord.smoking !== undefined && initialRecord.smoking !== null ? Number(initialRecord.smoking) : null,
      },
    }
  }
  return {
    patientRef: '',
    formData: { ...BLANK_FORM_STATE },
  }
}

export default function DoctorDashboard({
  doctorUser,
  onLogout,
  embedded = false,
  initialRecord = null,
  initialDraft = null,
  onPredictionSuccess,
  onUpdateDoctorUser,
}) {
  const initialState = buildInitialState(initialRecord, initialDraft)

  const [formData, setFormData] = useState(initialState.formData)
  const [patientRef, setPatientRef] = useState(initialState.patientRef)
  const [fieldErrors, setFieldErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState(null)
  const [showPhotoModal, setShowPhotoModal] = useState(false)

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

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    setFieldErrors((prev) => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
  }

  const validate = () => {
    const errors = {}

    if (!patientRef || !patientRef.trim()) {
      errors.patientRef = 'Patient Reference ID is required (e.g. PT-2026-001).'
    }

    const numericRules = [
      ['age', 1, 120, 'Enter a valid age between 1 and 120 years.'],
      ['ejection_fraction', 1, 100, 'Enter ejection fraction between 1% and 100%.'],
      ['serum_creatinine', 0.1, 25, 'Enter serum creatinine between 0.1 and 25 mg/dL.'],
      ['serum_sodium', 50, 200, 'Enter serum sodium between 50 and 200 mEq/L.'],
      ['platelets', 1, 1500000, 'Enter a valid platelet count (1–1,500,000 cells/µL).'],
      ['creatinine_phosphokinase', 1, 10000, 'Enter a valid CPK concentration (1–10,000 mcg/L).'],
    ]

    numericRules.forEach(([field, min, max, message]) => {
      const rawVal = String(formData[field] ?? '').trim()
      const parsed = Number(rawVal)
      if (rawVal === '' || !Number.isFinite(parsed) || parsed < min || parsed > max) {
        errors[field] = message
      }
    })

    const binaryRules = [
      ['sex', 'Please select biological sex.'],
      ['anaemia', 'Please select anaemia status.'],
      ['diabetes', 'Please select diabetes status.'],
      ['high_blood_pressure', 'Please select high blood pressure status.'],
      ['smoking', 'Please select smoking history status.'],
    ]

    binaryRules.forEach(([field, message]) => {
      if (formData[field] !== 0 && formData[field] !== 1) {
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
    const trimmedRef = patientRef.trim()
    payload.patient_reference_id = trimmedRef
    payload.patient_reference = trimmedRef

    try {
      const accessToken = localStorage.getItem('cardiopredict_access_token')
      const requestHeaders = { 'Content-Type': 'application/json' }
      if (accessToken) {
        requestHeaders['Authorization'] = `Bearer ${accessToken}`
      }

      // Exclusively invoke Logistic Regression endpoint (never ANN)
      const endpointsToTry = getPredictionCandidateUrls('lr')
      let response = null
      let data = null
      let lastParsedError = null

      for (const endpoint of endpointsToTry) {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 15000)

        try {
          let res = await fetch(endpoint, {
            method: 'POST',
            headers: requestHeaders,
            body: JSON.stringify(payload),
            signal: controller.signal,
          })

          if (res.status === 401) {
            const refreshed = await refreshAccessToken()
            if (refreshed) {
              requestHeaders['Authorization'] = `Bearer ${refreshed}`
              res = await fetch(endpoint, {
                method: 'POST',
                headers: requestHeaders,
                body: JSON.stringify(payload),
                signal: controller.signal,
              })
            } else if (typeof window !== 'undefined') {
              window.dispatchEvent(new CustomEvent('cardiopredict:session-expired'))
            }
          }
          clearTimeout(timeoutId)

          const parsedBody = await safeParseResponse(res)

          if (res.ok && parsedBody) {
            response = res
            data = parsedBody
            break
          } else {
            lastParsedError = parseApiError(null, res, parsedBody)
            if (res.status === 400 || res.status === 422) {
              const serverFields = extractFieldErrors(parsedBody)
              if (Object.keys(serverFields).length > 0) {
                setFieldErrors((prev) => ({ ...prev, ...serverFields }))
              }
              break
            }
          }
        } catch (fetchErr) {
          clearTimeout(timeoutId)
          lastParsedError = parseApiError(fetchErr)
        }
      }

      if (!response || !response.ok || !data) {
        throw new Error(
          lastParsedError?.message ||
            'Could not connect to the FastAPI prediction server. Please verify the backend is active.'
        )
      }

      const displayTimestamp = new Date().toLocaleString([], {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })

      let savedAssessment = null
      let savedPrediction = null
      const recordTargetId = initialDraft?.recordId || initialRecord?.id
      const recordTargetCode = initialDraft?.assessmentCode || initialRecord?.assessmentCode

      try {
        savedAssessment = saveAssessment({
          id: recordTargetId,
          assessmentCode: recordTargetCode,
          patientReferenceId: trimmedRef,
          doctorName: cleanDoctorName,
          doctorId: doctorUser?.email || 'DR-CURRENT',
          ...payload,
          model: data.model || 'Logistic Regression',
          predictedClass: data.predicted_class,
          predictedLabel: data.predicted_label,
          predictedProbability: data.predicted_probability,
          predictionTimestamp: displayTimestamp,
        })

        savedPrediction = savePrediction({
          assessmentId: savedAssessment.id,
          assessmentCode: savedAssessment.assessmentCode,
          patientReferenceId: trimmedRef,
          modelName: data.model || 'Logistic Regression',
          predictedClass: data.predicted_class,
          predictedLabel: data.predicted_label,
          predictedProbability: data.predicted_probability,
          classificationThreshold: Number(data.threshold ?? 0.5),
          modelVersion: 'v1.0.0',
          inputs: { ...payload },
        })
      } catch (err) {
        console.warn('Could not save assessment/prediction record locally:', err)
      }

      setApiError(null)

      if (onPredictionSuccess) {
        onPredictionSuccess({
          predictionResponse: data,
          patientInputs: payload,
          patientRef: trimmedRef,
          assessmentCode: savedAssessment?.assessmentCode || recordTargetCode || null,
          predictionCode: savedPrediction?.predictionCode || null,
          displayTimestamp,
          draft: {
            patientRef: trimmedRef,
            formData: { ...formData },
            recordId: savedAssessment?.id || recordTargetId,
            assessmentCode: savedAssessment?.assessmentCode || recordTargetCode,
          },
        })
      }
    } catch (error) {
      setApiError(error.message || 'Unable to complete clinical prediction request.')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setFormData({ ...BLANK_FORM_STATE })
    setPatientRef('')
    setFieldErrors({})
    setApiError(null)
  }

  const handleFillExampleInputs = () => {
    setPatientRef(EXAMPLE_INPUT_PROFILE.patientRef)
    setFormData({ ...EXAMPLE_INPUT_PROFILE.formData })
    setFieldErrors({})
    setApiError(null)
  }

  return (
    <div className={`dashboard-page ${embedded ? 'embedded-view' : ''}`}>
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
                  <h1 className="topbar-title">Patient Risk Assessment</h1>
                </div>
                <p className="topbar-subtitle">Clinical Decision Support Workspace</p>
              </div>
            </div>

            <div className="topbar-right">
              <ThemeToggle className="topbar-theme-toggle" />
              <div
                className="doctor-profile-pill clickable-pill"
                title={`${cleanDoctorName} — ${cleanRole} (Click to change photo)`}
                onClick={() => setShowPhotoModal(true)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setShowPhotoModal(true) }}
              >
                <div className="doctor-avatar" aria-hidden="true">
                  <DoctorAvatar
                    photoUrl={doctorUser?.profilePhotoUrl || doctorUser?.profile_photo_url}
                    initials={avatarInitials}
                    alt={cleanDoctorName}
                    email={doctorUser?.email}
                  />
                </div>
                <div className="doctor-info">
                  <span className="doctor-name">{cleanDoctorName}</span>
                  <span className="doctor-role">{cleanRole}</span>
                </div>
              </div>

              <button
                type="button"
                className="btn-logout"
                onClick={onLogout}
                title="Sign out of doctor portal"
                aria-label="Logout"
              >
                <span>Logout</span>
              </button>
            </div>
          </div>
        </header>
      )}

      <div className="patient-assessment-shell">
        {/* Clean Full-Width Assessment Header */}
        <section className="assessment-intro-card">
          <div className="assessment-intro-text">
            <h2>Patient Risk Assessment</h2>
            <p>
              Enter patient identification, documented clinical conditions, and baseline laboratory measurements across the 11 clinical parameters to generate an individual prediction report.
            </p>
          </div>
          <div className="assessment-intro-actions">
            <button
              type="button"
              className="btn-dash-secondary assessment-helper-btn"
              onClick={handleFillExampleInputs}
              disabled={loading}
              title="Populate the form fields with example clinical values for testing"
            >
              Fill Example Inputs
            </button>
            <button
              type="button"
              className="btn-dash-secondary assessment-helper-btn"
              onClick={handleReset}
              disabled={loading}
            >
              Clear Form
            </button>
          </div>
        </section>

        {/* API Error Alert */}
        {apiError && (
          <div className="alert-banner error" role="alert">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div className="alert-text">
              <strong>Prediction Error: </strong>
              <span>{apiError}</span>
            </div>
            <button type="button" className="btn-alert-retry" onClick={handleSubmit} disabled={loading}>
              Retry
            </button>
          </div>
        )}

        {/* Validation Summary Banner */}
        {Object.keys(fieldErrors).length > 0 && (
          <div className="alert-banner warning" role="alert">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <div className="alert-text">
              <strong>Validation Required: </strong>
              <span>Please review and complete the {Object.keys(fieldErrors).length} highlighted clinical field(s) before generating a prediction.</span>
            </div>
          </div>
        )}

        {/* Full-Width Clinical Form Card (Zero Right Side Panel) */}
        <section className="card assessment-form-card" aria-label="Patient Clinical Parameters Form">
          <div className="card-header">
            <div className="card-header-title-row">
              <h3 className="card-title">Clinical &amp; Laboratory Input Form</h3>
              <span className="card-counter-tag">11 Required Clinical Features</span>
            </div>
            <p className="card-subtitle">
              All baseline clinical parameters are validated before computing the assessment on the dedicated results dashboard.
            </p>
          </div>

          <div className="card-body">
            <form onSubmit={handleSubmit} noValidate>
              {/* Group 1: Patient Identification & Demographics */}
              <div className="form-group-section">
                <div className="section-title-row">
                  <span className="section-num">1</span>
                  <div>
                    <h4 className="section-heading">Patient Identification &amp; Demographics</h4>
                    <p className="section-desc">Tracking identifier, age, and recorded biological sex</p>
                  </div>
                </div>

                <div className="assessment-grid-three">
                  <div className="form-field">
                    <label className="form-label" htmlFor="param-patient-ref">
                      <span className="label-with-tip">
                        Patient Reference ID <span className="req-star" title="Required">*</span>
                      </span>
                      <span className="field-unit">e.g. PT-2026-001</span>
                    </label>
                    <input
                      id="param-patient-ref"
                      type="text"
                      placeholder="e.g. PT-2026-001"
                      className={`form-input ${fieldErrors.patientRef ? 'has-error' : ''}`}
                      value={patientRef}
                      onChange={(e) => {
                        setPatientRef(e.target.value)
                        if (fieldErrors.patientRef) {
                          setFieldErrors((prev) => {
                            const updated = { ...prev }
                            delete updated.patientRef
                            return updated
                          })
                        }
                      }}
                      disabled={loading}
                      maxLength={40}
                      aria-invalid={!!fieldErrors.patientRef}
                      aria-describedby={fieldErrors.patientRef ? 'ref-err' : undefined}
                    />
                    {fieldErrors.patientRef && <span id="ref-err" className="field-error-msg">{fieldErrors.patientRef}</span>}
                  </div>

                  <div className="form-field">
                    <label className="form-label" htmlFor="param-age">
                      <span className="label-with-tip">
                        Age <span className="req-star" title="Required">*</span>
                      </span>
                      <span className="field-unit">years (1–120)</span>
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

                  <div className="form-field">
                    <label className="form-label" id="lbl-sex">
                      <span className="label-with-tip">
                        Biological Sex <span className="req-star" title="Required">*</span>
                      </span>
                      <span className="field-unit">Female (0) / Male (1)</span>
                    </label>
                    <div
                      className={`segmented-toggle sliding-segmented-toggle ${
                        formData.sex === 1 ? 'pos-right' : formData.sex === 0 ? 'pos-left' : 'pos-unset'
                      } ${fieldErrors.sex ? 'toggle-error' : ''}`}
                      role="radiogroup"
                      aria-labelledby="lbl-sex"
                    >
                      {formData.sex !== null && <div className="segmented-sliding-glider" aria-hidden="true" />}
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
                    {fieldErrors.sex && <span className="field-error-msg">{fieldErrors.sex}</span>}
                  </div>
                </div>
              </div>

              {/* Group 2: Laboratory & Clinical Measurements */}
              <div className="form-group-section">
                <div className="section-title-row">
                  <span className="section-num">2</span>
                  <div>
                    <h4 className="section-heading">Laboratory &amp; Clinical Measurements</h4>
                    <p className="section-desc">Quantitative echocardiographic and blood biomarker readings</p>
                  </div>
                </div>

                <div className="assessment-grid-three">
                  <div className="form-field">
                    <label className="form-label" htmlFor="param-ef">
                      <span className="label-with-tip">
                        Ejection Fraction <span className="req-star" title="Required">*</span>
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

                  <div className="form-field">
                    <label className="form-label" htmlFor="param-creatinine">
                      <span className="label-with-tip">
                        Serum Creatinine <span className="req-star" title="Required">*</span>
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

                  <div className="form-field">
                    <label className="form-label" htmlFor="param-sodium">
                      <span className="label-with-tip">
                        Serum Sodium <span className="req-star" title="Required">*</span>
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

                  <div className="form-field">
                    <label className="form-label" htmlFor="param-platelets">
                      <span className="label-with-tip">
                        Platelets <span className="req-star" title="Required">*</span>
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

                  <div className="form-field">
                    <label className="form-label" htmlFor="param-cpk">
                      <span className="label-with-tip">
                        Creatinine Phosphokinase <span className="req-star" title="Required">*</span>
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

              {/* Group 3: Documented Clinical History */}
              <div className="form-group-section">
                <div className="section-title-row">
                  <span className="section-num">3</span>
                  <div>
                    <h4 className="section-heading">Clinical History &amp; Baseline Conditions</h4>
                    <p className="section-desc">Binary documented comorbidities and lifestyle history</p>
                  </div>
                </div>

                <div className="assessment-grid-two">
                  {[
                    { key: 'anaemia', label: 'Anaemia', unit: 'Hb < 12 g/dL', id: 'lbl-anaemia' },
                    { key: 'diabetes', label: 'Diabetes', unit: 'Documented diagnosis', id: 'lbl-diabetes' },
                    { key: 'high_blood_pressure', label: 'High Blood Pressure', unit: 'Hypertension', id: 'lbl-hbp' },
                    { key: 'smoking', label: 'Smoking', unit: 'Tobacco history', id: 'lbl-smoking' },
                  ].map((item) => (
                    <div className="form-field" key={item.key}>
                      <label className="form-label" id={item.id}>
                        <span className="label-with-tip">
                          {item.label} <span className="req-star" title="Required">*</span>
                        </span>
                        <span className="field-unit">{item.unit}</span>
                      </label>
                      <div
                        className={`segmented-toggle sliding-segmented-toggle ${
                          formData[item.key] === 1
                            ? 'pos-right'
                            : formData[item.key] === 0
                              ? 'pos-left'
                              : 'pos-unset'
                        } ${fieldErrors[item.key] ? 'toggle-error' : ''}`}
                        role="radiogroup"
                        aria-labelledby={item.id}
                      >
                        {formData[item.key] !== null && <div className="segmented-sliding-glider" aria-hidden="true" />}
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData[item.key] === 0}
                          className={`toggle-btn segmented-opt-btn ${formData[item.key] === 0 ? 'active' : ''}`}
                          onClick={() => handleInputChange(item.key, 0)}
                          disabled={loading}
                        >
                          No (0)
                        </button>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={formData[item.key] === 1}
                          className={`toggle-btn segmented-opt-btn ${formData[item.key] === 1 ? 'active' : ''}`}
                          onClick={() => handleInputChange(item.key, 1)}
                          disabled={loading}
                        >
                          Yes (1)
                        </button>
                      </div>
                      {fieldErrors[item.key] && <span className="field-error-msg">{fieldErrors[item.key]}</span>}
                    </div>
                  ))}
                </div>
              </div>

              {/* Form Footer & Primary Generate Prediction Action */}
              <div className="form-action-bar assessment-submit-bar">
                <button
                  type="button"
                  className="btn-secondary btn-reset-form"
                  onClick={handleReset}
                  disabled={loading}
                >
                  Reset Form
                </button>

                <button
                  type="submit"
                  className="btn-primary btn-predict assessment-submit-btn"
                  disabled={loading}
                  aria-busy={loading}
                >
                  {loading ? (
                    <>
                      <span className="spinner" aria-hidden="true" />
                      <span>Generating Assessment...</span>
                    </>
                  ) : (
                    <>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                      </svg>
                      <span>Generate Prediction</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </section>
      </div>

      <DoctorProfilePhotoModal
        isOpen={showPhotoModal}
        onClose={() => setShowPhotoModal(false)}
        doctorUser={doctorUser}
        currentPhotoUrl={doctorUser?.profilePhotoUrl || doctorUser?.profile_photo_url}
        onPhotoUpdated={(newPhotoUrl) => {
          if (onUpdateDoctorUser) {
            onUpdateDoctorUser({ profilePhotoUrl: newPhotoUrl, profile_photo_url: newPhotoUrl })
          }
        }}
      />
    </div>
  )
}
