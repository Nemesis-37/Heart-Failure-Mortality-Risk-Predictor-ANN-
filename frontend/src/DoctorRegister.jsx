import React, { useState, useEffect, useId } from 'react'
import { getAuthCandidateUrls } from './apiConfig.js'
import { safeParseResponse, parseApiError } from './utils/apiErrorHelper.js'
import MedicalAiVisualizer from './components/MedicalAiVisualizer.jsx'
import './AuthPages.css'

export default function DoctorRegister({ onNavigateToLogin, onRegisterSuccess }) {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    mobile: '',
    medicalDegree: '',
    registrationNumber: '',
    registrationCouncil: '',
    password: '',
    confirmPassword: '',
  })

  const [documentFile, setDocumentFile] = useState(null)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [serverError, setServerError] = useState('')
  const [registrationComplete, setRegistrationComplete] = useState(false)
  const [registeredDoctor, setRegisteredDoctor] = useState(null)

  const fullNameId = useId()
  const emailId = useId()
  const mobileId = useId()
  const degreeId = useId()
  const regNumberId = useId()
  const councilId = useId()
  const passwordId = useId()
  const confirmPasswordId = useId()
  const fileUploadId = useId()

  // Permanently force dark mode on Registration page
  useEffect(() => {
    const root = document.documentElement
    const prevTheme = root.getAttribute('data-theme')
    const hadDarkClass = root.classList.contains('dark')

    root.classList.add('dark')
    root.setAttribute('data-theme', 'dark')

    return () => {
      if (prevTheme === 'light') {
        root.classList.remove('dark')
        root.setAttribute('data-theme', 'light')
      } else if (!hadDarkClass && prevTheme !== 'dark') {
        root.classList.remove('dark')
      }
    }
  }, [])

  const calculatePasswordStrength = (pwd) => {
    let score = 0
    if (!pwd) return { score: 0, label: 'None', color: '#64748B' }
    if (pwd.length >= 8) score += 1
    if (/[A-Z]/.test(pwd)) score += 1
    if (/[a-z]/.test(pwd)) score += 1
    if (/\d/.test(pwd)) score += 1
    if (/[^A-Za-z0-9]/.test(pwd)) score += 1

    if (score <= 2) return { score, label: 'Weak', color: '#F87171' }
    if (score === 3 || score === 4) return { score, label: 'Moderate', color: '#FBBF24' }
    return { score, label: 'Strong', color: '#34D399' }
  }

  const passwordStrength = calculatePasswordStrength(formData.password)

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }))
    }
    if (serverError) setServerError('')
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const allowed = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
    if (!allowed.includes(file.type)) {
      setErrors((prev) => ({
        ...prev,
        document: 'Invalid file format. Please upload a PDF, PNG, or JPEG certificate.',
      }))
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setErrors((prev) => ({
        ...prev,
        document: 'Document size exceeds the 10MB limit.',
      }))
      return
    }

    setDocumentFile(file)
    setErrors((prev) => ({ ...prev, document: '' }))
  }

  const validate = () => {
    const errs = {}

    if (!formData.fullName.trim() || formData.fullName.trim().length < 3) {
      errs.fullName = 'Full legal name must be at least 3 characters.'
    }

    const emailTrim = formData.email.trim()
    if (!emailTrim) {
      errs.email = 'Professional institutional email is required.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailTrim)) {
      errs.email = 'Please enter a valid institutional or professional email.'
    }

    const mobileTrim = formData.mobile.trim()
    if (!mobileTrim) {
      errs.mobile = 'Mobile contact number is required.'
    } else if (!/^[0-9+\-\s()]{7,20}$/.test(mobileTrim)) {
      errs.mobile = 'Please enter a valid contact phone number.'
    }

    if (!formData.medicalDegree.trim()) {
      errs.medicalDegree = 'Medical qualification is required (e.g. MBBS, MD, FACC).'
    }

    if (!formData.registrationNumber.trim()) {
      errs.registrationNumber = 'Medical council registration number is required.'
    }

    if (!formData.registrationCouncil.trim()) {
      errs.registrationCouncil = 'Issuing state or national medical council is required.'
    }

    if (!formData.password) {
      errs.password = 'Password is required.'
    } else if (formData.password.length < 8) {
      errs.password = 'Password must be at least 8 characters long.'
    } else if (!/[A-Z]/.test(formData.password)) {
      errs.password = 'Must include at least one uppercase letter (A-Z).'
    } else if (!/[a-z]/.test(formData.password)) {
      errs.password = 'Must include at least one lowercase letter (a-z).'
    } else if (!/\d/.test(formData.password)) {
      errs.password = 'Must include at least one digit (0-9).'
    }

    if (!formData.confirmPassword) {
      errs.confirmPassword = 'Confirm your password entry.'
    } else if (formData.password !== formData.confirmPassword) {
      errs.confirmPassword = 'Passwords do not match.'
    }

    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (isSubmitting) return
    if (!validate()) return

    setIsSubmitting(true)
    setServerError('')

    try {
      const data = new FormData()
      data.append('full_name', formData.fullName.trim())
      data.append('email', formData.email.trim().toLowerCase())
      data.append('mobile', formData.mobile.trim())
      data.append('medical_degree', formData.medicalDegree.trim())
      data.append('registration_number', formData.registrationNumber.trim().toUpperCase())
      data.append('registration_council', formData.registrationCouncil.trim())
      data.append('password', formData.password)
      data.append('confirm_password', formData.confirmPassword)

      if (documentFile) {
        data.append('document', documentFile)
      }

      const candidateUrls = getAuthCandidateUrls('/auth/register')
      let successfulData = null
      let lastParsedError = null

      for (const endpoint of candidateUrls) {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 20000)

        try {
          const res = await fetch(endpoint, {
            method: 'POST',
            body: data,
            signal: controller.signal,
          })
          clearTimeout(timeoutId)

          const parsedBody = await safeParseResponse(res)

          if (res.ok && parsedBody) {
            successfulData = parsedBody
            break
          } else {
            lastParsedError = parseApiError(null, res, parsedBody)
            // If the server answered with 400 (e.g. duplicate or validation), don't spam fallbacks
            if (res.status >= 400 && res.status < 500) {
              break
            }
          }
        } catch (fetchErr) {
          clearTimeout(timeoutId)
          lastParsedError = parseApiError(fetchErr)
        }
      }

      if (!successfulData) {
        const errorMsg =
          lastParsedError?.message ||
          'Unable to connect to registration server. Please ensure the backend is running.'
        setServerError(errorMsg)
        if (lastParsedError?.fieldErrors && Object.keys(lastParsedError.fieldErrors).length > 0) {
          setErrors((prev) => ({ ...prev, ...lastParsedError.fieldErrors }))
        }
        return
      }

      setRegisteredDoctor(
        successfulData.doctor || {
          full_name: formData.fullName,
          email: formData.email,
          registration_number: formData.registrationNumber,
          registration_council: formData.registrationCouncil,
        }
      )
      setRegistrationComplete(true)
      if (onRegisterSuccess) onRegisterSuccess(successfulData.doctor)
    } catch (err) {
      setServerError(err.message || 'An unexpected error occurred during physician registration.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-page-root">
      <div className="auth-bg-grid" aria-hidden="true" />
      <div className="auth-ambient-glow top-left" aria-hidden="true" />
      <div className="auth-ambient-glow bottom-right" aria-hidden="true" />

      {/* ───── LEFT PANEL: Clinical SaaS Brand & Trust ───── */}
      <div className="auth-left-panel">
        <div className="auth-left-container">

          <div className="auth-brand-badge">
            <span className="auth-pulse-dot" aria-hidden="true" />
            <span>Physician Credentialing Portal</span>
          </div>

          <div className="auth-brand-logo-row">
            <div className="auth-brand-icon-box">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <path d="M12 8v8" />
                <path d="M8 12h8" />
              </svg>
            </div>
            <div>
              <div className="auth-brand-title">CardioPredict</div>
              <div className="auth-brand-subtitle">Clinical Verification Module</div>
            </div>
          </div>

          <div>
            <h1 className="auth-hero-heading">
              Physician Registration &amp; Credential Verification
            </h1>
            <p className="auth-hero-desc" style={{ marginTop: '0.75rem' }}>
              Register your medical qualifications to evaluate heart failure mortality risk using dual-engine Artificial Neural Network and calibrated Logistic Regression diagnostic models.
            </p>
          </div>

          {/* Animated Medical AI Telemetry, ECG & Neural Network Visualizer */}
          <MedicalAiVisualizer />

          {/* 4 Security & Verification Feature Cards */}
          <div className="auth-features-list">
            <div className="auth-feature-item">
              <div className="auth-feature-icon-wrapper" style={{ background: 'rgba(14, 165, 233, 0.15)', color: '#38BDF8' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="8.5" cy="7.5" r="4" />
                  <polyline points="17 11 19 13 23 9" />
                </svg>
              </div>
              <div className="auth-feature-item-content">
                <h3>Medical Council Verification</h3>
                <p>Credential validation against official state and national medical licensing registers.</p>
              </div>
            </div>

            <div className="auth-feature-item">
              <div className="auth-feature-icon-wrapper" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34D399' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              </div>
              <div className="auth-feature-item-content">
                <h3>Argon2id Credential Protection</h3>
                <p>Military-grade salted hash protection preventing credential exposure and unauthorized access.</p>
              </div>
            </div>

            <div className="auth-feature-item">
              <div className="auth-feature-icon-wrapper" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#C084FC' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
              </div>
              <div className="auth-feature-item-content">
                <h3>Encrypted Document Vault</h3>
                <p>Registration certificates and licensing proofs stored securely outside publicly accessible web trees.</p>
              </div>
            </div>

            <div className="auth-feature-item">
              <div className="auth-feature-icon-wrapper" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#FBBF24' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
              <div className="auth-feature-item-content">
                <h3>Clinical Inference Platform</h3>
                <p>Instant access to dual ANN and Logistic Regression cardiology evaluation tools once approved.</p>
              </div>
            </div>
          </div>

          <div className="auth-left-footer-note">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span>Strict Medical Audit Required &bull; Account Pending Review by Default</span>
          </div>

        </div>
      </div>

      {/* ───── RIGHT PANEL: Registration Form ───── */}
      <div className="auth-right-panel">
        <div className="auth-form-card register-wide">

          {/* Registration Success Confirmation */}
          {registrationComplete ? (
            <div style={{ textAlign: 'center', padding: '1rem 0' }}>
              <div style={{
                width: '68px',
                height: '68px',
                borderRadius: '50%',
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(52, 211, 153, 0.4)',
                color: '#34D399',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1.5rem',
                boxShadow: '0 4px 20px rgba(16, 185, 129, 0.25)',
              }}>
                <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>

              <span className="auth-brand-badge" style={{ margin: '0 auto 0.75rem' }}>
                Registration Submitted
              </span>

              <h2 className="auth-card-title" style={{ fontSize: '1.75rem', marginTop: '0.5rem' }}>
                Credentials Received
              </h2>

              <p className="auth-hero-desc" style={{ maxWidth: '480px', margin: '0 auto 1.5rem', fontSize: '0.92rem' }}>
                Thank you, <strong>{registeredDoctor?.full_name}</strong>. Your medical registration has been recorded with verification status{' '}
                <span style={{ fontWeight: 700, color: '#FBBF24', background: 'rgba(245, 158, 11, 0.15)', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                  PENDING
                </span>.
              </p>

              <div style={{
                background: 'rgba(13, 25, 48, 0.6)',
                border: '1px solid rgba(56, 189, 248, 0.18)',
                borderRadius: '12px',
                padding: '1.25rem',
                textAlign: 'left',
                marginBottom: '1.75rem',
                fontSize: '0.86rem',
                color: '#CBD5E1',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.65rem', fontWeight: 700, color: '#38BDF8' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                  <span>Next Step: Email Verification</span>
                </div>
                <p style={{ margin: 0, lineHeight: 1.5 }}>
                  A verification code has been queued for <strong>{registeredDoctor?.email}</strong>. Please check your medical institutional inbox to verify email ownership.
                </p>
                <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px dashed rgba(100, 116, 139, 0.3)', fontSize: '0.78rem', color: '#94A3B8' }}>
                  Registration Number: <strong style={{ color: '#F1F5F9' }}>{registeredDoctor?.registration_number}</strong> &bull; Council: <strong style={{ color: '#F1F5F9' }}>{registeredDoctor?.registration_council}</strong>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <button
                  type="button"
                  className="auth-btn-primary"
                  onClick={() => {
                    if (onRegisterSuccess) {
                      onRegisterSuccess(registeredDoctor)
                    }
                  }}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                  <span>Enter 6-Digit Verification Code</span>
                </button>

                <button
                  type="button"
                  className="auth-btn-demo"
                  onClick={onNavigateToLogin}
                >
                  <span>Sign In Later</span>
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Form Header */}
              <div className="auth-card-header">
                <span className="auth-card-kicker">New Practitioner Onboarding</span>
                <h2 className="auth-card-title">Physician Registration</h2>
                <p className="auth-card-subtitle">
                  Submit your clinical credentials for medical council verification and diagnostic decision-support access.
                </p>
              </div>

              {/* Server Error Alert */}
              {serverError && (
                <div className="auth-alert-error" role="alert">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span>{serverError}</span>
                </div>
              )}

              {/* Structured Registration Form */}
              <form onSubmit={handleSubmit} noValidate className="auth-form">

                {/* Section 1: Practitioner Identity */}
                <div className="auth-form-section">
                  <div className="auth-form-section-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                    <span>1. Practitioner Identity</span>
                  </div>

                  <div className="auth-grid-2col">
                    {/* Full Name */}
                    <div className="auth-field-group auth-grid-span-full">
                      <label className="auth-field-label" htmlFor={fullNameId}>
                        Full Legal Name <span className="auth-required-star">*</span>
                      </label>
                      <div className="auth-input-container">
                        <span className="auth-input-icon" aria-hidden="true">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                            <circle cx="12" cy="7" r="4" />
                          </svg>
                        </span>
                        <input
                          id={fullNameId}
                          name="fullName"
                          type="text"
                          className={`auth-input has-left-icon ${errors.fullName ? 'has-error' : ''}`}
                          placeholder="Dr. Full Name"
                          value={formData.fullName}
                          onChange={handleChange}
                          disabled={isSubmitting}
                          required
                        />
                      </div>
                      {errors.fullName && <span className="auth-field-error-text">{errors.fullName}</span>}
                    </div>

                    {/* Email */}
                    <div className="auth-field-group">
                      <label className="auth-field-label" htmlFor={emailId}>
                        Professional Email <span className="auth-required-star">*</span>
                      </label>
                      <div className="auth-input-container">
                        <span className="auth-input-icon" aria-hidden="true">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                            <polyline points="22,6 12,13 2,6" />
                          </svg>
                        </span>
                        <input
                          id={emailId}
                          name="email"
                          type="email"
                          className={`auth-input has-left-icon ${errors.email ? 'has-error' : ''}`}
                          placeholder="doctor@hospital.org"
                          value={formData.email}
                          onChange={handleChange}
                          disabled={isSubmitting}
                          required
                        />
                      </div>
                      {errors.email && <span className="auth-field-error-text">{errors.email}</span>}
                    </div>

                    {/* Contact Number */}
                    <div className="auth-field-group">
                      <label className="auth-field-label" htmlFor={mobileId}>
                        Contact Telephone <span className="auth-required-star">*</span>
                      </label>
                      <div className="auth-input-container">
                        <span className="auth-input-icon" aria-hidden="true">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                          </svg>
                        </span>
                        <input
                          id={mobileId}
                          name="mobile"
                          type="tel"
                          className={`auth-input has-left-icon ${errors.mobile ? 'has-error' : ''}`}
                          placeholder="+1 (555) 000-0000"
                          value={formData.mobile}
                          onChange={handleChange}
                          disabled={isSubmitting}
                          required
                        />
                      </div>
                      {errors.mobile && <span className="auth-field-error-text">{errors.mobile}</span>}
                    </div>
                  </div>
                </div>

                {/* Section 2: Medical Licensing & Qualifications */}
                <div className="auth-form-section">
                  <div className="auth-form-section-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="8" r="7" />
                      <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88" />
                    </svg>
                    <span>2. Medical Licensing &amp; Credentials</span>
                  </div>

                  <div className="auth-grid-2col">
                    {/* Medical Degree */}
                    <div className="auth-field-group">
                      <label className="auth-field-label" htmlFor={degreeId}>
                        Degree / Qualification <span className="auth-required-star">*</span>
                      </label>
                      <div className="auth-input-container">
                        <span className="auth-input-icon" aria-hidden="true">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="8" r="7" />
                            <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88" />
                          </svg>
                        </span>
                        <input
                          id={degreeId}
                          name="medicalDegree"
                          type="text"
                          className={`auth-input has-left-icon ${errors.medicalDegree ? 'has-error' : ''}`}
                          placeholder="e.g. MBBS, MD, FACC"
                          value={formData.medicalDegree}
                          onChange={handleChange}
                          disabled={isSubmitting}
                          required
                        />
                      </div>
                      {errors.medicalDegree && <span className="auth-field-error-text">{errors.medicalDegree}</span>}
                    </div>

                    {/* Registration Number */}
                    <div className="auth-field-group">
                      <label className="auth-field-label" htmlFor={regNumberId}>
                        Medical Registration Number <span className="auth-required-star">*</span>
                      </label>
                      <div className="auth-input-container">
                        <span className="auth-input-icon" aria-hidden="true">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                            <line x1="16" y1="2" x2="16" y2="6" />
                            <line x1="8" y1="2" x2="8" y2="6" />
                            <line x1="3" y1="10" x2="21" y2="10" />
                          </svg>
                        </span>
                        <input
                          id={regNumberId}
                          name="registrationNumber"
                          type="text"
                          className={`auth-input has-left-icon ${errors.registrationNumber ? 'has-error' : ''}`}
                          placeholder="e.g. REG-2024-88421"
                          value={formData.registrationNumber}
                          onChange={handleChange}
                          disabled={isSubmitting}
                          required
                        />
                      </div>
                      {errors.registrationNumber && <span className="auth-field-error-text">{errors.registrationNumber}</span>}
                    </div>

                    {/* Registration Council */}
                    <div className="auth-field-group auth-grid-span-full">
                      <label className="auth-field-label" htmlFor={councilId}>
                        Issuing Medical Council <span className="auth-required-star">*</span>
                      </label>
                      <div className="auth-input-container">
                        <span className="auth-input-icon" aria-hidden="true">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M3 21h18M3 7v1a3 3 0 0 0 6 0V7m0 1a3 3 0 0 0 6 0V7m0 1a3 3 0 0 0 6 0V7H3l2-4h14l2 4M5 21V10.85M19 21V10.85M9 21v-4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v4" />
                          </svg>
                        </span>
                        <input
                          id={councilId}
                          name="registrationCouncil"
                          type="text"
                          className={`auth-input has-left-icon ${errors.registrationCouncil ? 'has-error' : ''}`}
                          placeholder="e.g. State Medical Council or National Medical Board"
                          value={formData.registrationCouncil}
                          onChange={handleChange}
                          disabled={isSubmitting}
                          required
                        />
                      </div>
                      {errors.registrationCouncil && <span className="auth-field-error-text">{errors.registrationCouncil}</span>}
                    </div>
                  </div>
                </div>

                {/* Section 3: Account Security */}
                <div className="auth-form-section">
                  <div className="auth-form-section-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                    <span>3. Account Security</span>
                  </div>

                  <div className="auth-grid-2col">
                    {/* Password */}
                    <div className="auth-field-group">
                      <label className="auth-field-label" htmlFor={passwordId}>
                        Password <span className="auth-required-star">*</span>
                      </label>
                      <div className="auth-input-container">
                        <span className="auth-input-icon" aria-hidden="true">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                          </svg>
                        </span>
                        <input
                          id={passwordId}
                          name="password"
                          type={showPassword ? 'text' : 'password'}
                          className={`auth-input has-left-icon has-right-toggle ${errors.password ? 'has-error' : ''}`}
                          placeholder="Min. 8 characters"
                          value={formData.password}
                          onChange={handleChange}
                          disabled={isSubmitting}
                          required
                        />
                        <button
                          type="button"
                          className="auth-toggle-pwd-btn"
                          onClick={() => setShowPassword(!showPassword)}
                          aria-label={showPassword ? 'Hide password' : 'Show password'}
                          title={showPassword ? 'Hide password' : 'Show password'}
                        >
                          {showPassword ? (
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                              <line x1="1" y1="1" x2="23" y2="23" />
                            </svg>
                          ) : (
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                              <circle cx="12" cy="12" r="3" />
                            </svg>
                          )}
                        </button>
                      </div>
                      {errors.password && <span className="auth-field-error-text">{errors.password}</span>}
                    </div>

                    {/* Confirm Password */}
                    <div className="auth-field-group">
                      <label className="auth-field-label" htmlFor={confirmPasswordId}>
                        Confirm Password <span className="auth-required-star">*</span>
                      </label>
                      <div className="auth-input-container">
                        <span className="auth-input-icon" aria-hidden="true">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                          </svg>
                        </span>
                        <input
                          id={confirmPasswordId}
                          name="confirmPassword"
                          type={showConfirmPassword ? 'text' : 'password'}
                          className={`auth-input has-left-icon has-right-toggle ${errors.confirmPassword ? 'has-error' : ''}`}
                          placeholder="Re-enter password"
                          value={formData.confirmPassword}
                          onChange={handleChange}
                          disabled={isSubmitting}
                          required
                        />
                        <button
                          type="button"
                          className="auth-toggle-pwd-btn"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                          title={showConfirmPassword ? 'Hide password' : 'Show password'}
                        >
                          {showConfirmPassword ? (
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                              <line x1="1" y1="1" x2="23" y2="23" />
                            </svg>
                          ) : (
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                              <circle cx="12" cy="12" r="3" />
                            </svg>
                          )}
                        </button>
                      </div>
                      {errors.confirmPassword && <span className="auth-field-error-text">{errors.confirmPassword}</span>}
                    </div>

                    {/* Live Password Strength Meter */}
                    {formData.password && (
                      <div className="auth-grid-span-full">
                        <div className="auth-pwd-strength-container">
                          <div className="auth-pwd-strength-header">
                            <span>Password Strength:</span>
                            <strong style={{ color: passwordStrength.color }}>{passwordStrength.label}</strong>
                          </div>
                          <div className="auth-pwd-strength-track">
                            <div
                              className="auth-pwd-strength-fill"
                              style={{
                                width: `${(passwordStrength.score / 5) * 100}%`,
                                backgroundColor: passwordStrength.color,
                              }}
                            />
                          </div>
                          <div className="auth-pwd-requirements-row">
                            <span className={`auth-pwd-req-item ${formData.password.length >= 8 ? 'met' : 'unmet'}`}>
                              {formData.password.length >= 8 ? '✓' : '•'} 8+ characters
                            </span>
                            <span className={`auth-pwd-req-item ${/[A-Z]/.test(formData.password) ? 'met' : 'unmet'}`}>
                              {/[A-Z]/.test(formData.password) ? '✓' : '•'} Uppercase (A-Z)
                            </span>
                            <span className={`auth-pwd-req-item ${/[a-z]/.test(formData.password) ? 'met' : 'unmet'}`}>
                              {/[a-z]/.test(formData.password) ? '✓' : '•'} Lowercase (a-z)
                            </span>
                            <span className={`auth-pwd-req-item ${/\d/.test(formData.password) ? 'met' : 'unmet'}`}>
                              {/\d/.test(formData.password) ? '✓' : '•'} Numeric digit (0-9)
                            </span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Section 4: Verification Evidence (Document Upload) */}
                <div className="auth-form-section">
                  <div className="auth-form-section-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                    </svg>
                    <span>4. Verification Evidence (Optional Document)</span>
                  </div>

                  <div className="auth-field-group">
                    <label className="auth-field-label" htmlFor={fileUploadId}>
                      Medical Registration Proof / Certificate
                    </label>

                    <div className="auth-dropzone">
                      <input
                        id={fileUploadId}
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png"
                        onChange={handleFileChange}
                        disabled={isSubmitting}
                        className="auth-dropzone-input"
                      />
                      <div className="auth-dropzone-content">
                        <div className="auth-dropzone-icon">
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                            <polyline points="17 8 12 3 7 8" />
                            <line x1="12" y1="3" x2="12" y2="15" />
                          </svg>
                        </div>

                        {documentFile ? (
                          <div className="auth-file-selected-badge">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
                            <span>{documentFile.name} ({(documentFile.size / 1024 / 1024).toFixed(2)} MB)</span>
                          </div>
                        ) : (
                          <>
                            <span className="auth-dropzone-label">
                              Click or drag registration certificate to upload
                            </span>
                            <span className="auth-dropzone-meta">
                              Accepted formats: PDF, PNG, JPG &bull; Maximum file size: 10 MB
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    {errors.document && <span className="auth-field-error-text">{errors.document}</span>}
                  </div>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  className="auth-btn-primary"
                  disabled={isSubmitting}
                  style={{ marginTop: '0.5rem' }}
                >
                  {isSubmitting ? (
                    <>
                      <span className="auth-spinner" aria-hidden="true" />
                      <span>Submitting Medical Credentials&hellip;</span>
                    </>
                  ) : (
                    <>
                      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                        <circle cx="8.5" cy="7.5" r="4" />
                        <polyline points="17 11 19 13 23 9" />
                      </svg>
                      <span>Submit Physician Credentials</span>
                    </>
                  )}
                </button>

                {/* Navigation back to Sign In */}
                <div style={{ textAlign: 'center', marginTop: '0.5rem', fontSize: '0.86rem', color: '#94A3B8' }}>
                  Already have a verified physician account?{' '}
                  <button
                    type="button"
                    onClick={onNavigateToLogin}
                    className="auth-inline-link"
                    style={{ fontSize: '0.86rem' }}
                  >
                    Sign in to Portal
                  </button>
                </div>

              </form>

              <div className="auth-card-footer">
                <p style={{ margin: 0 }}>
                  Heart Failure Mortality Risk Predictor &bull; Doctor Registration &bull; Credential Verification Module
                </p>
              </div>
            </>
          )}

        </div>
      </div>
    </div>
  )
}
