import React, { useState } from 'react'

export default function DoctorLogin({ onLogin, onNavigateToRegister, onNavigateToAdmin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [serverError, setServerError] = useState('')
  const [showForgotNotice, setShowForgotNotice] = useState(false)

  const validate = () => {
    const errs = {}
    const trimmedEmail = email.trim()

    if (!trimmedEmail) {
      errs.email = 'Email address is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errs.email = 'Please enter a valid email address'
    }

    if (!password) {
      errs.password = 'Password is required'
    } else if (password.length < 6) {
      errs.password = 'Password must be at least 6 characters'
    }

    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setServerError('')
    if (!validate()) return

    setIsSubmitting(true)

    try {
      const response = await fetch('http://127.0.0.1:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          password: password,
          remember_me: rememberMe,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        setServerError(data.detail || 'Authentication failed. Please verify your credentials.')
        setIsSubmitting(false)
        return
      }

      // Store security tokens in browser storage
      if (data.access_token) {
        localStorage.setItem('cardiopredict_access_token', data.access_token)
      }
      if (data.refresh_token) {
        localStorage.setItem('cardiopredict_refresh_token', data.refresh_token)
      }

      const doc = data.doctor || {}
      const rawName = (doc.full_name || email.split('@')[0])
        .replace(/^(dr[\._\s-]*|doctor[\._\s-]*)/i, '')
        .trim()
      const formattedName = rawName || 'Physician'

      const doctorProfile = {
        doctorId: doc.doctor_id,
        email: doc.email || email.trim(),
        name: doc.full_name?.startsWith('Dr.') ? doc.full_name : `Dr. ${formattedName}`,
        degree: doc.medical_degree || 'MD',
        registrationNumber: doc.registration_number || '',
        registrationCouncil: doc.registration_council || '',
        role: doc.medical_degree ? `${doc.medical_degree} • Attending Physician` : 'Attending Physician',
        department: 'Cardiovascular Medicine',
        avatarInitials:
          formattedName
            .split(' ')
            .map((w) => w[0])
            .join('')
            .slice(0, 2)
            .toUpperCase() || 'DR',
        verificationStatus: doc.verification_status,
      }

      localStorage.setItem('cardiopredict_current_doctor', JSON.stringify(doctorProfile))

      setIsSubmitting(false)
      onLogin(doctorProfile, rememberMe)
    } catch (err) {
      console.error('Login network error:', err)
      setServerError('Unable to connect to clinical authentication server. Please check backend connection at http://127.0.0.1:8000.')
      setIsSubmitting(false)
    }
  }

  const handleQuickDemo = () => {
    setEmail('dr.carter@hospital.org')
    setPassword('CardioCare2026!')
    setErrors({})
    setServerError('')
  }

  return (
    <div className="login-page">
      {/* ───── LEFT PANEL: Premium Clinical Branding (54% width) ───── */}
      <div className="login-left-panel">
        {/* Layered decorative backgrounds */}
        <div className="left-panel-bg-layer" aria-hidden="true" />
        <div className="left-panel-glow-1" aria-hidden="true" />
        <div className="left-panel-glow-2" aria-hidden="true" />
        <div className="left-panel-glow-3" aria-hidden="true" />
        <div className="left-panel-grid-overlay" aria-hidden="true" />

        {/* Dynamic ECG Waveform SVG decoration */}
        <svg
          className="ecg-decoration"
          viewBox="0 0 800 90"
          fill="none"
          aria-hidden="true"
          preserveAspectRatio="none"
        >
          <path
            d="M0 45 L110 45 L135 45 L150 25 L165 70 L180 12 L195 62 L210 45 L260 45 L380 45 L405 45 L420 22 L435 72 L450 10 L465 65 L480 45 L530 45 L650 45 L675 45 L690 28 L705 66 L718 15 L730 58 L745 45 L800 45"
            stroke="url(#ecgGradient)"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <defs>
            <linearGradient id="ecgGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.05" />
              <stop offset="35%" stopColor="#38bdf8" stopOpacity="0.3" />
              <stop offset="65%" stopColor="#0d9488" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.08" />
            </linearGradient>
          </defs>
        </svg>

        <div className="left-panel-content">
          {/* Brand Header */}
          <div className="brand-header">
            <div className="brand-icon-container" aria-hidden="true">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
              </svg>
            </div>
            <div className="brand-text-group">
              <div className="brand-badge-row">
                <span className="brand-intelligence-badge">
                  <span className="badge-pulse-dot" aria-hidden="true" />
                  Clinical Intelligence
                </span>
              </div>
              <h1 className="brand-product-name">
                Heart Failure<br />
                Mortality Risk Predictor
              </h1>
              <p className="brand-tagline">Advanced Clinical Risk Assessment</p>
              <p className="brand-description">
                A clinical decision-support platform comparing classical statistical inference and deep neural architectures using 11 validated patient biomarkers.
              </p>
            </div>
          </div>

          {/* Feature Highlights Grid */}
          <div className="brand-features">
            <div className="brand-feature-card">
              <div className="feature-card-icon" aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
              <div className="feature-card-text">
                <strong>Intelligent Risk Analysis</strong>
                <span>Clinical parameter-based mortality prediction</span>
              </div>
            </div>

            <div className="brand-feature-card">
              <div className="feature-card-icon" aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
              </div>
              <div className="feature-card-text">
                <strong>Dual Model Architecture</strong>
                <span>Logistic Regression and Artificial Neural Network</span>
              </div>
            </div>

            <div className="brand-feature-card">
              <div className="feature-card-icon" aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
              </div>
              <div className="feature-card-text">
                <strong>Clinical Data Insights</strong>
                <span>Analysis using 11 patient clinical parameters</span>
              </div>
            </div>
          </div>

          {/* Bottom Secure Badge */}
          <div className="brand-footer-badge">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>Secure Physician &amp; Clinical Research Portal</span>
          </div>
        </div>
      </div>

      {/* ───── RIGHT PANEL: Substantially Larger Doctor Login Card (46% width) ───── */}
      <div className="login-right-panel">
        {/* Soft decorative ambient lighting */}
        <div className="right-panel-radial" aria-hidden="true" />
        <div className="right-panel-radial-2" aria-hidden="true" />

        <div className="login-form-wrapper">
          <div className="login-form-card">
            {/* Form Header */}
            <div className="login-card-header">
              <span className="login-access-kicker">Healthcare Provider Access</span>
              <h2 className="login-card-title">Welcome Back</h2>
              <p className="login-card-subtitle">
                Sign in to access your clinical workspace.
              </p>
            </div>

            {/* Forgot Password Notice */}
            {showForgotNotice && (
              <div className="forgot-notice" role="alert">
                <span>Password recovery will connect to your clinical directory once backend authentication is provisioned.</span>
                <button
                  type="button"
                  className="btn-dismiss-notice"
                  onClick={() => setShowForgotNotice(false)}
                  aria-label="Dismiss notice"
                >
                  &times;
                </button>
              </div>
            )}

            {/* Server Authentication Error Alert */}
            {serverError && (
              <div className="login-server-error" role="alert">
                <div className="error-content">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ flexShrink: 0, marginTop: '2px' }} aria-hidden="true">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span>{serverError}</span>
                </div>
                <button
                  type="button"
                  className="btn-dismiss-error"
                  onClick={() => setServerError('')}
                  aria-label="Dismiss error"
                >
                  &times;
                </button>
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit} noValidate className="login-form">
              {/* Email Address */}
              <div className="login-field-group">
                <label className="login-field-label" htmlFor="doctor-email">
                  Email Address
                </label>
                <div className="login-input-container">
                  <svg className="login-input-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                  <input
                    id="doctor-email"
                    type="email"
                    autoComplete="email"
                    className={`login-input ${errors.email ? 'has-error' : ''}`}
                    placeholder="dr.carter@hospital.org"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value)
                      if (errors.email) setErrors((prev) => ({ ...prev, email: null }))
                    }}
                    disabled={isSubmitting}
                    aria-invalid={!!errors.email}
                    aria-describedby={errors.email ? 'email-error' : undefined}
                  />
                </div>
                {errors.email && (
                  <span id="email-error" className="login-field-error">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    {errors.email}
                  </span>
                )}
              </div>

              {/* Password */}
              <div className="login-field-group">
                <div className="login-label-row">
                  <label className="login-field-label" htmlFor="doctor-password">
                    Password
                  </label>
                  <button
                    type="button"
                    className="link-forgot-password"
                    onClick={() => setShowForgotNotice(true)}
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="login-input-container password-container">
                  <svg className="login-input-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  <input
                    id="doctor-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    className={`login-input ${errors.password ? 'has-error' : ''}`}
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value)
                      if (errors.password) setErrors((prev) => ({ ...prev, password: null }))
                    }}
                    disabled={isSubmitting}
                    aria-invalid={!!errors.password}
                    aria-describedby={errors.password ? 'password-error' : undefined}
                  />
                  <button
                    type="button"
                    className="btn-toggle-pw"
                    onClick={() => setShowPassword((prev) => !prev)}
                    title={showPassword ? 'Hide password' : 'Show password'}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    tabIndex={0}
                  >
                    {showPassword ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
                {errors.password && (
                  <span id="password-error" className="login-field-error">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    {errors.password}
                  </span>
                )}
              </div>

              {/* Remember Me */}
              <div className="login-options-row">
                <label className="login-checkbox-label" htmlFor="remember-me">
                  <input
                    id="remember-me"
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    disabled={isSubmitting}
                  />
                  <span>Remember me on this device</span>
                </label>
              </div>

              {/* Sign In Button */}
              <button
                type="submit"
                className="btn-login-primary"
                disabled={isSubmitting}
                aria-busy={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <span className="login-spinner" aria-hidden="true" />
                    <span>Signing In to Portal&hellip;</span>
                  </>
                ) : (
                  <>
                    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
                      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                      <polyline points="10 17 15 12 10 7" />
                      <line x1="15" y1="12" x2="3" y2="12" />
                    </svg>
                    <span>Sign In to Portal</span>
                  </>
                )}
              </button>

              {/* Divider */}
              <div className="login-divider">
                <span>or continue with demo</span>
              </div>

              {/* Quick Demo Button */}
              <button
                type="button"
                className="btn-login-demo"
                onClick={handleQuickDemo}
                disabled={isSubmitting}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                <span>Quick Demo Access</span>
              </button>

              {/* Register New Physician Link */}
              {onNavigateToRegister && (
                <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.88rem', color: '#64748b' }}>
                  New physician or medical resident?{' '}
                  <button
                    type="button"
                    onClick={onNavigateToRegister}
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
                    Register for Access
                  </button>
                </div>
              )}

              {/* Administrator Portal Access */}
              {onNavigateToAdmin && (
                <div style={{ textAlign: 'center', marginTop: '0.75rem' }}>
                  <button
                    type="button"
                    onClick={onNavigateToAdmin}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#94a3b8',
                      cursor: 'pointer',
                      fontSize: '0.76rem',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                    <span>Staff &bull; Administrator Verification Portal</span>
                  </button>
                </div>
              )}
            </form>

            {/* Footer Disclaimer */}
            <div className="login-card-footer">
              <p>
                Heart Failure Mortality Risk Predictor &bull; Educational ML Prototype &bull; Not for clinical decision-making
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
