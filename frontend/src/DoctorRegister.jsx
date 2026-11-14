import React, { useState, useId } from 'react'

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

  const calculatePasswordStrength = (pwd) => {
    let score = 0
    if (!pwd) return { score: 0, label: 'None', color: '#94a3b8' }
    if (pwd.length >= 8) score += 1
    if (/[A-Z]/.test(pwd)) score += 1
    if (/[a-z]/.test(pwd)) score += 1
    if (/\d/.test(pwd)) score += 1
    if (/[^A-Za-z0-9]/.test(pwd)) score += 1

    if (score <= 2) return { score, label: 'Weak', color: '#ef4444' }
    if (score === 3 || score === 4) return { score, label: 'Good', color: '#f59e0b' }
    return { score, label: 'Strong', color: '#10b981' }
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
        document: 'Invalid file format. Please upload a PDF, PNG, or JPEG file.',
      }))
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setErrors((prev) => ({
        ...prev,
        document: 'Document size exceeds 10MB limit.',
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
      errs.email = 'Professional email address is required.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailTrim)) {
      errs.email = 'Please enter a valid institutional or personal email.'
    }

    const mobileTrim = formData.mobile.trim()
    if (!mobileTrim) {
      errs.mobile = 'Mobile contact number is required.'
    } else if (!/^[0-9+\-\s()]{7,20}$/.test(mobileTrim)) {
      errs.mobile = 'Please enter a valid telephone number.'
    }

    if (!formData.medicalDegree.trim()) {
      errs.medicalDegree = 'Medical qualification / degree is required (e.g. MBBS, MD, FACC).'
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

      const res = await fetch('http://127.0.0.1:8000/auth/register', {
        method: 'POST',
        body: data,
      })

      const json = await res.json()

      if (!res.ok) {
        throw new Error(json.detail || 'Registration failed. Please review your entries.')
      }

      setRegisteredDoctor(json.doctor || {
        full_name: formData.fullName,
        email: formData.email,
        registration_number: formData.registrationNumber,
        registration_council: formData.registrationCouncil,
      })
      setRegistrationComplete(true)
      if (onRegisterSuccess) onRegisterSuccess(json.doctor)
    } catch (err) {
      setServerError(err.message || 'Unable to connect to server. Ensure FastAPI backend is running.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      {/* ───── LEFT PANEL: Clinical SaaS Brand & Trust ───── */}
      <div className="login-left-panel">
        <div className="left-panel-bg-layer" aria-hidden="true" />
        <div className="left-panel-glow-1" aria-hidden="true" />
        <div className="left-panel-glow-2" aria-hidden="true" />

        <div className="left-panel-brand">
          <div className="brand-icon-shield">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <div className="brand-text-block">
            <span className="brand-name">CardioPredict SaaS</span>
            <span className="brand-edition">Physician Credentialing System</span>
          </div>
        </div>

        <div className="left-panel-body">
          <div className="left-badge-tag">
            <span className="badge-pulse-dot" aria-hidden="true" />
            <span>Secure Medical Registration</span>
          </div>

          <h1 className="left-panel-headline">
            Verified Clinical Access for Healthcare Providers
          </h1>

          <p className="left-panel-description">
            Register your medical credentials to evaluate heart failure mortality risk
            using dual-engine Artificial Neural Network and Logistic Regression clinical models.
          </p>

          <div className="left-feature-cards">
            <div className="feature-card">
              <div className="feature-card-icon" style={{ background: '#DBEAFE', color: '#1565D8' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="8.5" cy="7.5" r="4" />
                  <polyline points="17 11 19 13 23 9" />
                </svg>
              </div>
              <div className="feature-card-text">
                <h3>Council Identity Verification</h3>
                <p>Every account is verified against official medical registration councils.</p>
              </div>
            </div>

            <div className="feature-card">
              <div className="feature-card-icon" style={{ background: '#ccfbf1', color: '#0f766e' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              </div>
              <div className="feature-card-text">
                <h3>Argon2id Hybrid Encryption</h3>
                <p>Industry-standard OWASP credential protection and encrypted audit trails.</p>
              </div>
            </div>

            <div className="feature-card">
              <div className="feature-card-icon" style={{ background: '#f3e8ff', color: '#7e22ce' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
              </div>
              <div className="feature-card-text">
                <h3>Encrypted Document Vault</h3>
                <p>Medical licenses and evidence stored safely outside public directories.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="left-panel-footer">
          <div className="compliance-shield">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span>Strict Verification Required &bull; Account Pending Review by Default</span>
          </div>
        </div>
      </div>

      {/* ───── RIGHT PANEL: Registration Form ───── */}
      <div className="login-right-panel" style={{ overflowY: 'auto', maxHeight: '100vh', padding: '2.5rem 1.5rem' }}>
        <div className="login-form-wrapper" style={{ maxWidth: '640px' }}>
          <div className="login-form-card" style={{ padding: '2.25rem' }}>

            {/* Registration Success Confirmation */}
            {registrationComplete ? (
              <div className="reg-success-card" style={{ textAlign: 'center', padding: '1rem 0' }}>
                <div style={{
                  width: '68px',
                  height: '68px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
                  color: '#15803d',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 1.5rem',
                  boxShadow: '0 4px 14px rgba(22, 163, 74, 0.25)',
                }}>
                  <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>

                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  color: '#0d9488',
                  background: '#ccfbf1',
                  padding: '4px 12px',
                  borderRadius: '12px',
                }}>
                  Registration Submitted
                </span>

                <h2 style={{
                  fontSize: '1.65rem',
                  fontWeight: 800,
                  color: '#0B1F3A',
                  marginTop: '0.85rem',
                  marginBottom: '0.5rem',
                }}>
                  Credentials Received
                </h2>

                <p style={{ fontSize: '0.92rem', color: '#64748b', lineHeight: 1.6, maxWidth: '480px', margin: '0 auto 1.5rem' }}>
                  Thank you, <strong>{registeredDoctor?.full_name}</strong>. Your account has been registered with status{' '}
                  <span style={{ fontWeight: 700, color: '#d97706', background: '#fef3c7', padding: '2px 8px', borderRadius: '4px' }}>
                    PENDING
                  </span>.
                </p>

                <div style={{
                  background: '#F3F7FC',
                  border: '1px solid #DBEAFE',
                  borderRadius: '12px',
                  padding: '1.25rem',
                  textAlign: 'left',
                  marginBottom: '1.75rem',
                  fontSize: '0.85rem',
                  color: '#334155',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.65rem', fontWeight: 700, color: '#1565D8' }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                    <span>Next Step: Email Verification</span>
                  </div>
                  <p style={{ margin: 0, lineHeight: 1.5 }}>
                    A verification link has been queued for <strong>{registeredDoctor?.email}</strong>. Please check your medical institutional inbox to verify email ownership.
                  </p>
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px dashed #cbd5e1', fontSize: '0.78rem', color: '#64748b' }}>
                    Registration Number: <strong>{registeredDoctor?.registration_number}</strong> &bull; Council: <strong>{registeredDoctor?.registration_council}</strong>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <button
                    type="button"
                    className="btn-login-primary"
                    onClick={() => {
                      if (onRegisterSuccess) {
                        onRegisterSuccess(registeredDoctor)
                      }
                    }}
                    style={{ width: '100%' }}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                    <span>Enter 6-Digit Verification Code</span>
                  </button>

                  <button
                    type="button"
                    className="btn-login-demo"
                    onClick={onNavigateToLogin}
                    style={{ width: '100%', justifyContent: 'center' }}
                  >
                    <span>Sign In Later</span>
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Form Header */}
                <div className="login-card-header" style={{ marginBottom: '1.5rem' }}>
                  <span className="login-access-kicker">New Practitioner Onboarding</span>
                  <h2 className="login-card-title" style={{ fontSize: '1.85rem' }}>Physician Registration</h2>
                  <p className="login-card-subtitle" style={{ fontSize: '0.88rem' }}>
                    Submit your clinical credentials for verification and access to the AI mortality predictor.
                  </p>
                </div>

                {/* Server Error Alert */}
                {serverError && (
                  <div style={{
                    background: '#fef2f2',
                    border: '1px solid #fecaca',
                    borderRadius: '10px',
                    padding: '0.85rem 1.15rem',
                    marginBottom: '1.25rem',
                    color: '#b91c1c',
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.65rem',
                  }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    <span>{serverError}</span>
                  </div>
                )}

                {/* Registration Form */}
                <form onSubmit={handleSubmit} noValidate className="login-form">
                  {/* Two column grid on desktop */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
                    
                    {/* Full Name */}
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor={fullNameId}>Full Legal Name *</label>
                      <div className="login-input-container">
                        <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                          <circle cx="12" cy="7" r="4" />
                        </svg>
                        <input
                          id={fullNameId}
                          name="fullName"
                          type="text"
                          className={`login-input ${errors.fullName ? 'has-error' : ''}`}
                          placeholder="Dr. Full Name"
                          value={formData.fullName}
                          onChange={handleChange}
                          disabled={isSubmitting}
                        />
                      </div>
                      {errors.fullName && <span className="login-field-error">{errors.fullName}</span>}
                    </div>

                    {/* Email */}
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor={emailId}>Professional Email *</label>
                      <div className="login-input-container">
                        <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                          <polyline points="22,6 12,13 2,6" />
                        </svg>
                        <input
                          id={emailId}
                          name="email"
                          type="email"
                          className={`login-input ${errors.email ? 'has-error' : ''}`}
                          placeholder="doctor@hospital.org"
                          value={formData.email}
                          onChange={handleChange}
                          disabled={isSubmitting}
                        />
                      </div>
                      {errors.email && <span className="login-field-error">{errors.email}</span>}
                    </div>

                    {/* Mobile Phone */}
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor={mobileId}>Contact Number *</label>
                      <div className="login-input-container">
                        <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                        </svg>
                        <input
                          id={mobileId}
                          name="mobile"
                          type="tel"
                          className={`login-input ${errors.mobile ? 'has-error' : ''}`}
                          placeholder="+1 (555) 000-0000"
                          value={formData.mobile}
                          onChange={handleChange}
                          disabled={isSubmitting}
                        />
                      </div>
                      {errors.mobile && <span className="login-field-error">{errors.mobile}</span>}
                    </div>

                    {/* Medical Degree */}
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor={degreeId}>Medical Degree / Qualification *</label>
                      <div className="login-input-container">
                        <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="8" r="7" />
                          <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88" />
                        </svg>
                        <input
                          id={degreeId}
                          name="medicalDegree"
                          type="text"
                          className={`login-input ${errors.medicalDegree ? 'has-error' : ''}`}
                          placeholder="e.g. MBBS, MD, FACC"
                          value={formData.medicalDegree}
                          onChange={handleChange}
                          disabled={isSubmitting}
                        />
                      </div>
                      {errors.medicalDegree && <span className="login-field-error">{errors.medicalDegree}</span>}
                    </div>

                    {/* Registration Number */}
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor={regNumberId}>Medical Registration Number *</label>
                      <div className="login-input-container">
                        <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                          <line x1="16" y1="2" x2="16" y2="6" />
                          <line x1="8" y1="2" x2="8" y2="6" />
                          <line x1="3" y1="10" x2="21" y2="10" />
                        </svg>
                        <input
                          id={regNumberId}
                          name="registrationNumber"
                          type="text"
                          className={`login-input ${errors.registrationNumber ? 'has-error' : ''}`}
                          placeholder="e.g. MCI-2024-88421"
                          value={formData.registrationNumber}
                          onChange={handleChange}
                          disabled={isSubmitting}
                        />
                      </div>
                      {errors.registrationNumber && <span className="login-field-error">{errors.registrationNumber}</span>}
                    </div>

                    {/* Registration Council */}
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor={councilId}>Registration Council *</label>
                      <div className="login-input-container">
                        <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M3 21h18M3 7v1a3 3 0 0 0 6 0V7m0 1a3 3 0 0 0 6 0V7m0 1a3 3 0 0 0 6 0V7H3l2-4h14l2 4M5 21V10.85M19 21V10.85M9 21v-4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v4" />
                        </svg>
                        <input
                          id={councilId}
                          name="registrationCouncil"
                          type="text"
                          className={`login-input ${errors.registrationCouncil ? 'has-error' : ''}`}
                          placeholder="e.g. State Medical Council"
                          value={formData.registrationCouncil}
                          onChange={handleChange}
                          disabled={isSubmitting}
                        />
                      </div>
                      {errors.registrationCouncil && <span className="login-field-error">{errors.registrationCouncil}</span>}
                    </div>
                  </div>

                  {/* Passwords Row */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginTop: '0.25rem' }}>
                    
                    {/* Password */}
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor={passwordId}>Password *</label>
                      <div className="login-input-container">
                        <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                        </svg>
                        <input
                          id={passwordId}
                          name="password"
                          type={showPassword ? 'text' : 'password'}
                          className={`login-input ${errors.password ? 'has-error' : ''}`}
                          placeholder="Minimum 8 characters"
                          value={formData.password}
                          onChange={handleChange}
                          disabled={isSubmitting}
                        />
                        <button
                          type="button"
                          className="btn-toggle-pw"
                          onClick={() => setShowPassword(!showPassword)}
                          aria-label={showPassword ? 'Hide password' : 'Show password'}
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
                      {errors.password && <span className="login-field-error">{errors.password}</span>}
                    </div>

                    {/* Confirm Password */}
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor={confirmPasswordId}>Confirm Password *</label>
                      <div className="login-input-container">
                        <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                        </svg>
                        <input
                          id={confirmPasswordId}
                          name="confirmPassword"
                          type={showConfirmPassword ? 'text' : 'password'}
                          className={`login-input ${errors.confirmPassword ? 'has-error' : ''}`}
                          placeholder="Re-enter password"
                          value={formData.confirmPassword}
                          onChange={handleChange}
                          disabled={isSubmitting}
                        />
                        <button
                          type="button"
                          className="btn-toggle-pw"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
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
                      {errors.confirmPassword && <span className="login-field-error">{errors.confirmPassword}</span>}
                    </div>
                  </div>

                  {/* Password Strength Meter */}
                  {formData.password && (
                    <div style={{
                      background: '#F8FAFC',
                      padding: '0.75rem 1rem',
                      borderRadius: '8px',
                      border: '1px solid #E2E8F0',
                      marginTop: '0.25rem',
                      fontSize: '0.78rem',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                        <span style={{ color: '#64748b' }}>Password Strength:</span>
                        <strong style={{ color: passwordStrength.color }}>{passwordStrength.label}</strong>
                      </div>
                      <div style={{ width: '100%', height: '5px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{
                          height: '100%',
                          width: `${(passwordStrength.score / 5) * 100}%`,
                          background: passwordStrength.color,
                          transition: 'width 250ms ease, background 250ms ease',
                        }} />
                      </div>
                      <div style={{ display: 'flex', gap: '0.85rem', flexWrap: 'wrap', marginTop: '0.45rem', color: '#64748b' }}>
                        <span style={{ color: formData.password.length >= 8 ? '#16a34a' : '#94a3b8' }}>
                          {formData.password.length >= 8 ? '✓' : '•'} 8+ chars
                        </span>
                        <span style={{ color: /[A-Z]/.test(formData.password) ? '#16a34a' : '#94a3b8' }}>
                          {/[A-Z]/.test(formData.password) ? '✓' : '•'} Uppercase
                        </span>
                        <span style={{ color: /[a-z]/.test(formData.password) ? '#16a34a' : '#94a3b8' }}>
                          {/[a-z]/.test(formData.password) ? '✓' : '•'} Lowercase
                        </span>
                        <span style={{ color: /\d/.test(formData.password) ? '#16a34a' : '#94a3b8' }}>
                          {/\d/.test(formData.password) ? '✓' : '•'} Number
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Supporting Document Upload */}
                  <div className="login-field-group" style={{ marginTop: '0.5rem' }}>
                    <label className="login-field-label" htmlFor={fileUploadId}>
                      Medical Registration Proof / Certificate <span style={{ color: '#64748b', fontWeight: 400 }}>(PDF, JPG, PNG - Max 10MB)</span>
                    </label>
                    <div style={{
                      border: '1.5px dashed #93C5FD',
                      background: '#EFF6FF',
                      borderRadius: '12px',
                      padding: '1.25rem',
                      textAlign: 'center',
                      cursor: 'pointer',
                      position: 'relative',
                    }}>
                      <input
                        id={fileUploadId}
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png"
                        onChange={handleFileChange}
                        disabled={isSubmitting}
                        style={{
                          position: 'absolute',
                          inset: 0,
                          opacity: 0,
                          cursor: 'pointer',
                          width: '100%',
                          height: '100%',
                        }}
                      />
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.35rem', pointerEvents: 'none' }}>
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#1565D8" strokeWidth="2">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                          <polyline points="17 8 12 3 7 8" />
                          <line x1="12" y1="3" x2="12" y2="15" />
                        </svg>
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#1565D8' }}>
                          {documentFile ? documentFile.name : 'Click or drag registration certificate to upload'}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                          {documentFile ? `${(documentFile.size / 1024 / 1024).toFixed(2)} MB uploaded` : 'Optional evidence for expedited manual credential approval'}
                        </span>
                      </div>
                    </div>
                    {errors.document && <span className="login-field-error">{errors.document}</span>}
                  </div>

                  {/* Submit Registration Button */}
                  <button
                    type="submit"
                    className="btn-login-primary"
                    disabled={isSubmitting}
                    style={{ marginTop: '0.75rem' }}
                  >
                    {isSubmitting ? (
                      <>
                        <span className="login-spinner" aria-hidden="true" />
                        <span>Submitting Medical Credentials&hellip;</span>
                      </>
                    ) : (
                      <>
                        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                          <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                          <circle cx="8.5" cy="7.5" r="4" />
                          <polyline points="17 11 19 13 23 9" />
                        </svg>
                        <span>Register as Physician</span>
                      </>
                    )}
                  </button>

                  {/* Switch to Login */}
                  <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.88rem', color: '#64748b' }}>
                    Already have a verified physician account?{' '}
                    <button
                      type="button"
                      onClick={onNavigateToLogin}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#1565D8',
                        fontWeight: 700,
                        cursor: 'pointer',
                        textDecoration: 'underline',
                        textUnderlineOffset: '3px',
                      }}
                    >
                      Sign In Here
                    </button>
                  </div>
                </form>

                <div className="login-card-footer" style={{ marginTop: '1.5rem' }}>
                  <p>
                    Heart Failure Mortality Risk Predictor &bull; Doctor Registration &bull; Credential Verification Module
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
