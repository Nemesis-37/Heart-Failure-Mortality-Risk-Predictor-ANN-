import React, { useState } from 'react'

export default function DoctorLogin({ onLogin }) {
  const [email, setEmail] = useState('dr.carter@hospital.org')
  const [password, setPassword] = useState('demo-doctor-2026')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(true)
  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)
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

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return

    setIsSubmitting(true)

    // Simulate clean authentication flow
    setTimeout(() => {
      setIsSubmitting(false)
      const username = email.split('@')[0]
      const formattedName = username
        .replace(/[^a-zA-Z]/g, ' ')
        .trim()
        .split(' ')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
        .join(' ')

      const doctorProfile = {
        email: email.trim(),
        name: formattedName ? `Dr. ${formattedName}` : 'Dr. Julian Carter, MD',
        role: 'Attending Cardiologist',
        department: 'Cardiovascular Medicine',
        avatarInitials: formattedName
          ? formattedName
              .split(' ')
              .map((w) => w[0])
              .join('')
              .slice(0, 2)
              .toUpperCase()
          : 'JC',
      }

      onLogin(doctorProfile, rememberMe)
    }, 400)
  }

  const handleQuickDemo = () => {
    setEmail('dr.carter@hospital.org')
    setPassword('demo-doctor-2026')
    setErrors({})

    const demoProfile = {
      email: 'dr.carter@hospital.org',
      name: 'Dr. Julian Carter, MD',
      role: 'Attending Cardiologist',
      department: 'Cardiovascular Medicine',
      avatarInitials: 'JC',
    }

    onLogin(demoProfile, rememberMe)
  }

  return (
    <div className="login-page">
      <div className="login-card-container">
        {/* Left Branding Panel (Healthcare Theme) */}
        <div className="login-brand-panel">
          <div className="brand-panel-header">
            <div className="login-brand-icon" aria-hidden="true">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
              </svg>
            </div>
            <div>
              <span className="brand-badge">Clinical ML Prototype</span>
              <h1 className="brand-panel-title">Heart Failure Mortality Risk Predictor</h1>
            </div>
          </div>

          <p className="brand-panel-desc">
            An educational decision-support platform designed for comparing classical and deep learning mortality risk estimation in heart failure clinical cohorts.
          </p>

          <div className="brand-features-list">
            <div className="brand-feature-item">
              <div className="feature-icon" aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
              <div className="feature-text">
                <strong>Dual Inference Architecture</strong>
                <span>Evaluate patient cases using both Logistic Regression and Artificial Neural Networks.</span>
              </div>
            </div>

            <div className="brand-feature-item">
              <div className="feature-icon" aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <line x1="8" y1="21" x2="16" y2="21" />
                  <line x1="12" y1="17" x2="12" y2="21" />
                </svg>
              </div>
              <div className="feature-text">
                <strong>11 Clinical Biomarkers</strong>
                <span>Calculates risk scores strictly from validated patient clinical and demographic parameters.</span>
              </div>
            </div>

            <div className="brand-feature-item">
              <div className="feature-icon" aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
              <div className="feature-text">
                <strong>Educational Decision Support</strong>
                <span>Research prototype for algorithmic comparison; not a replacement for clinical diagnosis.</span>
              </div>
            </div>
          </div>

          <div className="brand-panel-footer">
            <span className="secure-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              Physician &amp; Clinical Research Portal
            </span>
          </div>
        </div>

        {/* Right Section: Doctor Login Form */}
        <div className="login-form-panel">
          <div className="login-form-header">
            <span className="login-kicker">Healthcare Provider Access</span>
            <h2 className="login-heading">Doctor Login</h2>
            <p className="login-subheading">
              Sign in to access patient parameters, model selection, and risk inference.
            </p>
          </div>

          {/* Backend Authentication Status Disclaimer */}
          <div className="backend-auth-notice" role="note">
            <div className="auth-notice-icon" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <div className="auth-notice-text">
              <strong>Backend Auth Integration Pending:</strong>
              <p>
                FastAPI currently provides ML prediction endpoints (<code>/predict</code>, <code>/predict-ann</code>). Full doctor database authentication is scheduled for upcoming backend integration. Enter any valid email or click <strong>Demo Sign In</strong> to test the dashboard.
              </p>
            </div>
          </div>

          {showForgotNotice && (
            <div className="forgot-notice" role="alert">
              <span>Password recovery will connect to your clinical directory (LDAP/OAuth2) once backend auth is provisioned.</span>
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

          <form onSubmit={handleSubmit} noValidate className="login-form">
            {/* Email Address */}
            <div className="form-group">
              <label className="form-label" htmlFor="doctor-email">
                Email Address
              </label>
              <div className="input-wrapper">
                <input
                  id="doctor-email"
                  type="email"
                  autoComplete="email"
                  className={`form-input ${errors.email ? 'has-error' : ''}`}
                  placeholder="e.g. dr.carter@hospital.org"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    if (errors.email) {
                      setErrors((prev) => ({ ...prev, email: null }))
                    }
                  }}
                  disabled={isSubmitting}
                  aria-invalid={!!errors.email}
                  aria-describedby={errors.email ? 'email-error' : undefined}
                />
              </div>
              {errors.email && (
                <span id="email-error" className="error-text">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  {errors.email}
                </span>
              )}
            </div>

            {/* Password */}
            <div className="form-group">
              <div className="label-row">
                <label className="form-label" htmlFor="doctor-password">
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
              <div className="input-wrapper password-wrapper">
                <input
                  id="doctor-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  className={`form-input ${errors.password ? 'has-error' : ''}`}
                  placeholder="Enter your physician password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    if (errors.password) {
                      setErrors((prev) => ({ ...prev, password: null }))
                    }
                  }}
                  disabled={isSubmitting}
                  aria-invalid={!!errors.password}
                  aria-describedby={errors.password ? 'password-error' : undefined}
                />
                <button
                  type="button"
                  className="btn-toggle-password"
                  onClick={() => setShowPassword((prev) => !prev)}
                  title={showPassword ? 'Hide password' : 'Show password'}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={0}
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
              {errors.password && (
                <span id="password-error" className="error-text">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  {errors.password}
                </span>
              )}
            </div>

            {/* Remember Me Checkbox */}
            <div className="login-options-row">
              <label className="checkbox-label" htmlFor="remember-me">
                <input
                  id="remember-me"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  disabled={isSubmitting}
                />
                <span>Remember me on this workstation</span>
              </label>
            </div>

            {/* Submit Action */}
            <button
              type="submit"
              className="btn-primary btn-signin"
              disabled={isSubmitting}
              aria-busy={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  <span>Signing In&hellip;</span>
                </>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                    <polyline points="10 17 15 12 10 7" />
                    <line x1="15" y1="12" x2="3" y2="12" />
                  </svg>
                  <span>Sign In to Clinical Workspace</span>
                </>
              )}
            </button>

            {/* Quick Demo Button */}
            <button
              type="button"
              className="btn-secondary btn-demo-doctor"
              onClick={handleQuickDemo}
              disabled={isSubmitting}
            >
              <span>Quick Demo Doctor Access</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          </form>

          <div className="login-panel-disclaimer">
            <p>
              Heart Failure Mortality Risk Predictor &bull; Educational Machine Learning Prototype &bull; Not for clinical decision-making
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

