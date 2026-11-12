import React, { useState } from 'react'

export default function DoctorLogin({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
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

    // NOTE: No real backend authentication endpoint exists yet.
    // This simulates a login flow for UI demonstration purposes only.
    // When a real auth API is implemented, replace this setTimeout
    // with an actual fetch() call to your authentication endpoint.
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
        name: formattedName ? `Dr. ${formattedName}` : 'Doctor',
        role: 'Attending Physician',
        department: 'Cardiovascular Medicine',
        avatarInitials: formattedName
          ? formattedName
              .split(' ')
              .map((w) => w[0])
              .join('')
              .slice(0, 2)
              .toUpperCase()
          : 'DR',
      }

      onLogin(doctorProfile, rememberMe)
    }, 600)
  }

  const handleQuickDemo = () => {
    setEmail('dr.carter@hospital.org')
    setPassword('demo-password')
    setErrors({})
    setIsSubmitting(true)

    setTimeout(() => {
      setIsSubmitting(false)
      const demoProfile = {
        email: 'dr.carter@hospital.org',
        name: 'Dr. Julian Carter, MD',
        role: 'Attending Cardiologist',
        department: 'Cardiovascular Medicine',
        avatarInitials: 'JC',
      }
      onLogin(demoProfile, rememberMe)
    }, 500)
  }

  return (
    <div className="login-page">
      {/* ───── LEFT PANEL: Premium Clinical Branding ───── */}
      <div className="login-left-panel">
        {/* Decorative background layers */}
        <div className="left-panel-bg-layer" aria-hidden="true" />
        <div className="left-panel-glow-1" aria-hidden="true" />
        <div className="left-panel-glow-2" aria-hidden="true" />
        <div className="left-panel-grid-overlay" aria-hidden="true" />

        {/* ECG waveform decoration */}
        <svg className="ecg-decoration" viewBox="0 0 600 80" fill="none" aria-hidden="true" preserveAspectRatio="none">
          <path
            d="M0 40 L80 40 L100 40 L120 20 L135 65 L150 10 L165 55 L180 40 L220 40 L300 40 L320 40 L340 20 L355 65 L370 10 L385 55 L400 40 L440 40 L520 40 L540 40 L555 25 L565 60 L575 15 L585 50 L600 40"
            stroke="rgba(56, 189, 248, 0.15)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        <div className="left-panel-content">
          {/* Brand Header */}
          <div className="brand-header">
            <div className="brand-icon-container">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
              </svg>
            </div>
            <div className="brand-text-group">
              <span className="brand-intelligence-badge">Clinical Intelligence</span>
              <h1 className="brand-product-name">
                Heart Failure<br />
                Mortality Risk Predictor
              </h1>
              <p className="brand-tagline">Advanced Clinical Risk Assessment</p>
            </div>
          </div>

          {/* Feature Highlights */}
          <div className="brand-features">
            <div className="brand-feature-card">
              <div className="feature-card-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
              <div className="feature-card-text">
                <strong>Intelligent Risk Analysis</strong>
                <span>Clinical parameter-based mortality prediction</span>
              </div>
            </div>

            <div className="feature-divider" aria-hidden="true" />

            <div className="brand-feature-card">
              <div className="feature-card-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <line x1="8" y1="21" x2="16" y2="21" />
                  <line x1="12" y1="17" x2="12" y2="21" />
                </svg>
              </div>
              <div className="feature-card-text">
                <strong>Dual Model Architecture</strong>
                <span>Logistic Regression and Artificial Neural Network</span>
              </div>
            </div>

            <div className="feature-divider" aria-hidden="true" />

            <div className="brand-feature-card">
              <div className="feature-card-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
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
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>Secure Physician &amp; Research Portal</span>
          </div>
        </div>
      </div>

      {/* ───── RIGHT PANEL: Premium Doctor Login Form ───── */}
      <div className="login-right-panel">
        {/* Soft decorative background elements */}
        <div className="right-panel-radial" aria-hidden="true" />

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
                <span>Password recovery will be available once backend authentication is implemented.</span>
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

            {/* Login Form */}
            <form onSubmit={handleSubmit} noValidate className="login-form">
              {/* Email */}
              <div className="login-field-group">
                <label className="login-field-label" htmlFor="doctor-email">
                  Email Address
                </label>
                <div className="login-input-container">
                  <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                  <input
                    id="doctor-email"
                    type="email"
                    autoComplete="email"
                    className={`login-input ${errors.email ? 'has-error' : ''}`}
                    placeholder="doctor@hospital.org"
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
                  <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  <input
                    id="doctor-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    className={`login-input ${errors.password ? 'has-error' : ''}`}
                    placeholder="Enter your password"
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
                  <span id="password-error" className="login-field-error">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
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
                    <span>Signing In&hellip;</span>
                  </>
                ) : (
                  <>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
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
