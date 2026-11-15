import React, { useState, useEffect } from 'react'

export default function DoctorLogin({ onLogin, onNavigateToRegister, onNavigateToAdmin }) {
  // Tab switcher: 'doctor' | 'admin'
  const [loginMode, setLoginMode] = useState('doctor')

  // --- Doctor Login State ---
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [serverError, setServerError] = useState('')
  const [showForgotNotice, setShowForgotNotice] = useState(false)

  // --- Admin Login State ---
  const [adminUsername, setAdminUsername] = useState('')
  const [adminPassword, setAdminPassword] = useState('')
  const [showAdminPassword, setShowAdminPassword] = useState(false)
  const [adminError, setAdminError] = useState('')
  const [isAdminSubmitting, setIsAdminSubmitting] = useState(false)

  // --- Admin Forgot Password State ---
  // Stages: 'none' | 'username' | 'otp' | 'new_password'
  const [forgotStage, setForgotStage] = useState('none')
  const [forgotUsername, setForgotUsername] = useState('')
  const [forgotOTP, setForgotOTP] = useState('')
  const [forgotNewPassword, setForgotNewPassword] = useState('')
  const [forgotConfirmPassword, setForgotConfirmPassword] = useState('')
  const [showForgotPw, setShowForgotPw] = useState(false)
  const [forgotMaskedEmail, setForgotMaskedEmail] = useState('')
  const [forgotResetToken, setForgotResetToken] = useState('')
  const [forgotError, setForgotError] = useState('')
  const [forgotSuccessMsg, setForgotSuccessMsg] = useState('')
  const [isForgotSubmitting, setIsForgotSubmitting] = useState(false)
  const [cooldown, setCooldown] = useState(0)

  // 60-second cooldown timer for OTP resend
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown((c) => c - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [cooldown])

  // --- Doctor Validation & Submit ---
  const validateDoctor = () => {
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

  const handleDoctorSubmit = async (e) => {
    e.preventDefault()
    setServerError('')
    if (!validateDoctor()) return

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

  // --- Admin Login Submit ---
  const handleAdminSubmit = async (e) => {
    e.preventDefault()
    setAdminError('')
    if (!adminUsername.trim() || !adminPassword) {
      setAdminError('Please enter both administrator username and password.')
      return
    }

    setIsAdminSubmitting(true)
    try {
      const res = await fetch('http://127.0.0.1:8000/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: adminUsername.trim(),
          password: adminPassword,
        }),
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Administrator login failed.')
      }

      sessionStorage.setItem('cardiopredict_admin_token', data.token)
      sessionStorage.setItem('cardiopredict_admin_profile', JSON.stringify(data.admin))

      if (onNavigateToAdmin) {
        onNavigateToAdmin()
      }
    } catch (err) {
      setAdminError(err.message || 'Unable to connect to administration service.')
    } finally {
      setIsAdminSubmitting(false)
    }
  }

  // --- Admin Forgot Password Handlers ---
  const handleForgotSendOTP = async (e) => {
    if (e) e.preventDefault()
    setForgotError('')
    if (!forgotUsername.trim()) {
      setForgotError('Please enter your administrator username.')
      return
    }

    setIsForgotSubmitting(true)
    try {
      const res = await fetch('http://127.0.0.1:8000/admin/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: forgotUsername.trim() }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to dispatch verification code.')

      setForgotMaskedEmail(data.recovery_email_masked || 'debashish.g333@gmail.com')
      setForgotStage('otp')
      setCooldown(60)
    } catch (err) {
      setForgotError(err.message)
    } finally {
      setIsForgotSubmitting(false)
    }
  }

  const handleForgotVerifyOTP = async (e) => {
    e.preventDefault()
    setForgotError('')
    if (!forgotOTP.trim() || forgotOTP.trim().length !== 6) {
      setForgotError('Please enter the 6-digit numeric verification code.')
      return
    }

    setIsForgotSubmitting(true)
    try {
      const res = await fetch('http://127.0.0.1:8000/admin/verify-reset-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: forgotUsername.trim(),
          otp: forgotOTP.trim(),
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'OTP verification failed.')

      setForgotResetToken(data.reset_token)
      setForgotStage('new_password')
    } catch (err) {
      setForgotError(err.message)
    } finally {
      setIsForgotSubmitting(false)
    }
  }

  const handleForgotResetPassword = async (e) => {
    e.preventDefault()
    setForgotError('')

    if (forgotNewPassword.length < 8) {
      setForgotError('Password must be at least 8 characters long.')
      return
    }
    if (forgotNewPassword !== forgotConfirmPassword) {
      setForgotError('New password and confirm password do not match.')
      return
    }

    setIsForgotSubmitting(true)
    try {
      const res = await fetch('http://127.0.0.1:8000/admin/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: forgotUsername.trim(),
          reset_token: forgotResetToken,
          otp: forgotOTP.trim(),
          new_password: forgotNewPassword,
          confirm_password: forgotConfirmPassword,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Password reset failed.')

      setForgotSuccessMsg('Password has been reset successfully! Please sign in with your new credentials.')
      setAdminUsername(forgotUsername.trim())
      setForgotStage('none')
      setForgotOTP('')
      setForgotNewPassword('')
      setForgotConfirmPassword('')
      setForgotResetToken('')
    } catch (err) {
      setForgotError(err.message)
    } finally {
      setIsForgotSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      {/* ───── LEFT PANEL: Premium Clinical Branding ───── */}
      <div className="login-left-panel">
        <div className="left-panel-bg-layer" aria-hidden="true" />
        <div className="left-panel-glow-1" aria-hidden="true" />
        <div className="left-panel-glow-2" aria-hidden="true" />
        <div className="left-panel-glow-3" aria-hidden="true" />
        <div className="left-panel-grid-overlay" aria-hidden="true" />

        <svg className="ecg-decoration" viewBox="0 0 800 90" fill="none" aria-hidden="true" preserveAspectRatio="none">
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
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              </div>
              <div className="feature-card-text">
                <strong>Credentialed &amp; Role-Gated</strong>
                <span>Argon2id password hashing &amp; Administrator oversight</span>
              </div>
            </div>
          </div>

          <div className="brand-footer-badge">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>Secure Physician &amp; Administrator Portal</span>
          </div>
        </div>
      </div>

      {/* ───── RIGHT PANEL: Login Card ───── */}
      <div className="login-right-panel">
        <div className="right-panel-radial" aria-hidden="true" />
        <div className="right-panel-radial-2" aria-hidden="true" />

        <div className="login-form-wrapper">
          <div className="login-form-card">
            {/* Separate Login Options: Doctor Login vs Admin Login */}
            <div style={{
              display: 'flex',
              background: '#F1F5F9',
              borderRadius: '10px',
              padding: '4px',
              marginBottom: '1.25rem',
              gap: '4px',
            }}>
              <button
                type="button"
                onClick={() => {
                  setLoginMode('doctor')
                  setServerError('')
                  setAdminError('')
                  setForgotStage('none')
                }}
                style={{
                  flex: 1,
                  padding: '9px 14px',
                  borderRadius: '8px',
                  border: 'none',
                  fontWeight: 700,
                  fontSize: '0.86rem',
                  cursor: 'pointer',
                  background: loginMode === 'doctor' ? '#1565D8' : 'transparent',
                  color: loginMode === 'doctor' ? '#ffffff' : '#64748B',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                <span>👨‍⚕️</span>
                <span>Doctor Login</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setLoginMode('admin')
                  setServerError('')
                  setAdminError('')
                  setForgotStage('none')
                }}
                style={{
                  flex: 1,
                  padding: '9px 14px',
                  borderRadius: '8px',
                  border: 'none',
                  fontWeight: 700,
                  fontSize: '0.86rem',
                  cursor: 'pointer',
                  background: loginMode === 'admin' ? '#0B1F3A' : 'transparent',
                  color: loginMode === 'admin' ? '#ffffff' : '#64748B',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                <span>🛡️</span>
                <span>Admin Login</span>
              </button>
            </div>

            {/* Success message banner */}
            {forgotSuccessMsg && (
              <div style={{
                background: '#DCFCE7',
                border: '1px solid #86EFAC',
                color: '#166534',
                padding: '10px 14px',
                borderRadius: '8px',
                fontSize: '0.86rem',
                marginBottom: '1rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <span>✓ {forgotSuccessMsg}</span>
                <button type="button" onClick={() => setForgotSuccessMsg('')} style={{ background: 'transparent', border: 'none', color: '#166534', cursor: 'pointer' }}>✕</button>
              </div>
            )}

            {/* =============================================================
                MODE 1: DOCTOR LOGIN (Unchanged)
            ============================================================= */}
            {loginMode === 'doctor' && (
              <>
                <div className="login-card-header">
                  <span className="login-access-kicker">Healthcare Provider Access</span>
                  <h2 className="login-card-title">Doctor Portal</h2>
                  <p className="login-card-subtitle">
                    Sign in with your verified institutional email and password.
                  </p>
                </div>

                {showForgotNotice && (
                  <div className="forgot-notice" role="alert">
                    <span>Physician password recovery connects through hospital credential administration. Contact your medical registry officer.</span>
                    <button type="button" className="btn-dismiss-notice" onClick={() => setShowForgotNotice(false)} aria-label="Dismiss notice">
                      &times;
                    </button>
                  </div>
                )}

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
                    <button type="button" className="btn-dismiss-error" onClick={() => setServerError('')} aria-label="Dismiss error">
                      &times;
                    </button>
                  </div>
                )}

                <form onSubmit={handleDoctorSubmit} noValidate className="login-form">
                  {/* Email */}
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
                      />
                    </div>
                    {errors.email && (
                      <span className="login-field-error">
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
                      <button type="button" className="link-forgot-password" onClick={() => setShowForgotNotice(true)}>
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
                      />
                      <button
                        type="button"
                        className="btn-toggle-pw"
                        onClick={() => setShowPassword((prev) => !prev)}
                        title={showPassword ? 'Hide password' : 'Show password'}
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
                      <span className="login-field-error">
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

                  {/* Submit */}
                  <button type="submit" className="btn-login-primary" disabled={isSubmitting}>
                    {isSubmitting ? 'Signing In to Portal…' : 'Sign In as Doctor'}
                  </button>

                  <div className="login-divider">
                    <span>or continue with demo</span>
                  </div>

                  <button type="button" className="btn-login-demo" onClick={handleQuickDemo} disabled={isSubmitting}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <polygon points="5 3 19 12 5 21 5 3" />
                    </svg>
                    <span>Quick Demo Access</span>
                  </button>

                  {onNavigateToRegister && (
                    <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.88rem', color: '#64748B' }}>
                      New physician or resident?{' '}
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
                </form>
              </>
            )}

            {/* =============================================================
                MODE 2: ADMIN LOGIN & FORGOT PASSWORD WORKFLOW
            ============================================================= */}
            {loginMode === 'admin' && (
              <>
                {/* 2A: Standard Admin Login */}
                {forgotStage === 'none' && (
                  <>
                    <div className="login-card-header">
                      <span className="login-access-kicker" style={{ color: '#0B1F3A' }}>Governance &amp; Review Access</span>
                      <h2 className="login-card-title">Administrator Portal</h2>
                      <p className="login-card-subtitle">
                        Sign in using your assigned administrator username and password.
                      </p>
                    </div>

                    {adminError && (
                      <div className="login-server-error" role="alert">
                        <div className="error-content">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ flexShrink: 0, marginTop: '2px' }} aria-hidden="true">
                            <circle cx="12" cy="12" r="10" />
                            <line x1="12" y1="8" x2="12" y2="12" />
                            <line x1="12" y1="16" x2="12.01" y2="16" />
                          </svg>
                          <span>{adminError}</span>
                        </div>
                        <button type="button" className="btn-dismiss-error" onClick={() => setAdminError('')} aria-label="Dismiss error">
                          &times;
                        </button>
                      </div>
                    )}

                    <form onSubmit={handleAdminSubmit} noValidate className="login-form">
                      {/* Username */}
                      <div className="login-field-group">
                        <label className="login-field-label" htmlFor="admin-username">
                          Administrator Username
                        </label>
                        <div className="login-input-container">
                          <svg className="login-input-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                            <circle cx="12" cy="7" r="4" />
                          </svg>
                          <input
                            id="admin-username"
                            type="text"
                            autoComplete="username"
                            className="login-input"
                            placeholder="admin"
                            value={adminUsername}
                            onChange={(e) => setAdminUsername(e.target.value)}
                            disabled={isAdminSubmitting}
                          />
                        </div>
                      </div>

                      {/* Password */}
                      <div className="login-field-group">
                        <div className="login-label-row">
                          <label className="login-field-label" htmlFor="admin-password">
                            Password
                          </label>
                          <button
                            type="button"
                            className="link-forgot-password"
                            onClick={() => {
                              setForgotStage('username')
                              setForgotUsername(adminUsername)
                              setForgotError('')
                            }}
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
                            id="admin-password"
                            type={showAdminPassword ? 'text' : 'password'}
                            autoComplete="current-password"
                            className="login-input"
                            placeholder="••••••••••••"
                            value={adminPassword}
                            onChange={(e) => setAdminPassword(e.target.value)}
                            disabled={isAdminSubmitting}
                          />
                          <button
                            type="button"
                            className="btn-toggle-pw"
                            onClick={() => setShowAdminPassword((p) => !p)}
                            title={showAdminPassword ? 'Hide password' : 'Show password'}
                          >
                            {showAdminPassword ? (
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
                      </div>

                      <button
                        type="submit"
                        className="btn-login-primary"
                        disabled={isAdminSubmitting}
                        style={{ background: '#0B1F3A' }}
                      >
                        {isAdminSubmitting ? 'Verifying Admin Credentials…' : 'Sign In as Administrator'}
                      </button>

                      <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.8rem', color: '#64748B' }}>
                        🔒 Predefined administrative credentialing portal &bull; No public registration
                      </div>
                    </form>
                  </>
                )}

                {/* 2B: Forgot Password — Step 1: Username Input */}
                {forgotStage === 'username' && (
                  <div>
                    <div className="login-card-header">
                      <span className="login-access-kicker">Administrator Recovery</span>
                      <h2 className="login-card-title">Forgot Password</h2>
                      <p className="login-card-subtitle">
                        Enter your administrator username. A 6-digit verification code will be dispatched to your recovery email.
                      </p>
                    </div>

                    {forgotError && (
                      <div className="login-server-error" style={{ marginBottom: '1rem' }}>
                        <div className="error-content"><span>{forgotError}</span></div>
                      </div>
                    )}

                    <form onSubmit={handleForgotSendOTP}>
                      <div className="login-field-group">
                        <label className="login-field-label">Administrator Username</label>
                        <div className="login-input-container">
                          <input
                            type="text"
                            className="login-input"
                            placeholder="e.g. admin"
                            value={forgotUsername}
                            onChange={(e) => setForgotUsername(e.target.value)}
                            disabled={isForgotSubmitting}
                            autoFocus
                          />
                        </div>
                      </div>

                      <button
                        type="submit"
                        className="btn-login-primary"
                        disabled={isForgotSubmitting}
                        style={{ background: '#0B1F3A', marginTop: '0.5rem' }}
                      >
                        {isForgotSubmitting ? 'Sending OTP…' : 'Send Verification Code'}
                      </button>

                      <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                        <button
                          type="button"
                          onClick={() => { setForgotStage('none'); setForgotError(''); }}
                          style={{ background: 'transparent', border: 'none', color: '#1565D8', cursor: 'pointer', fontSize: '0.85rem' }}
                        >
                          ← Back to Admin Login
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                {/* 2C: Forgot Password — Step 2: OTP Verification */}
                {forgotStage === 'otp' && (
                  <div>
                    <div className="login-card-header">
                      <span className="login-access-kicker">Step 2 of 3</span>
                      <h2 className="login-card-title">Enter Verification Code</h2>
                      <p className="login-card-subtitle">
                        A 6-digit code was dispatched to <strong>{forgotMaskedEmail}</strong>. Valid for 5 minutes.
                      </p>
                    </div>

                    {forgotError && (
                      <div className="login-server-error" style={{ marginBottom: '1rem' }}>
                        <div className="error-content"><span>{forgotError}</span></div>
                      </div>
                    )}

                    <form onSubmit={handleForgotVerifyOTP}>
                      <div className="login-field-group">
                        <label className="login-field-label">6-Digit Verification Code</label>
                        <div className="login-input-container">
                          <input
                            type="text"
                            maxLength={6}
                            className="login-input"
                            placeholder="123456"
                            value={forgotOTP}
                            onChange={(e) => setForgotOTP(e.target.value.replace(/\D/g, ''))}
                            disabled={isForgotSubmitting}
                            style={{ letterSpacing: '8px', fontSize: '1.3rem', fontWeight: 700, textAlign: 'center' }}
                            autoFocus
                          />
                        </div>
                      </div>

                      <button
                        type="submit"
                        className="btn-login-primary"
                        disabled={isForgotSubmitting || forgotOTP.length !== 6}
                        style={{ background: '#0B1F3A', marginTop: '0.5rem' }}
                      >
                        {isForgotSubmitting ? 'Verifying Code…' : 'Verify Code & Proceed'}
                      </button>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', fontSize: '0.84rem' }}>
                        <button
                          type="button"
                          onClick={() => { setForgotStage('username'); setForgotError(''); }}
                          style={{ background: 'transparent', border: 'none', color: '#64748B', cursor: 'pointer' }}
                        >
                          ← Change Username
                        </button>

                        <button
                          type="button"
                          onClick={() => handleForgotSendOTP()}
                          disabled={cooldown > 0 || isForgotSubmitting}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: cooldown > 0 ? '#94A3B8' : '#1565D8',
                            cursor: cooldown > 0 ? 'not-allowed' : 'pointer',
                            fontWeight: 600,
                          }}
                        >
                          {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend Code'}
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                {/* 2D: Forgot Password — Step 3: Set New Password */}
                {forgotStage === 'new_password' && (
                  <div>
                    <div className="login-card-header">
                      <span className="login-access-kicker">Step 3 of 3</span>
                      <h2 className="login-card-title">Set New Password</h2>
                      <p className="login-card-subtitle">
                        Enter your new password (minimum 8 characters). Password will be hashed using Argon2id.
                      </p>
                    </div>

                    {forgotError && (
                      <div className="login-server-error" style={{ marginBottom: '1rem' }}>
                        <div className="error-content"><span>{forgotError}</span></div>
                      </div>
                    )}

                    <form onSubmit={handleForgotResetPassword}>
                      <div className="login-field-group">
                        <label className="login-field-label">New Password</label>
                        <div className="login-input-container password-container">
                          <input
                            type={showForgotPw ? 'text' : 'password'}
                            className="login-input"
                            placeholder="At least 8 characters"
                            value={forgotNewPassword}
                            onChange={(e) => setForgotNewPassword(e.target.value)}
                            disabled={isForgotSubmitting}
                          />
                          <button
                            type="button"
                            className="btn-toggle-pw"
                            onClick={() => setShowForgotPw((p) => !p)}
                          >
                            {showForgotPw ? 'Hide' : 'Show'}
                          </button>
                        </div>
                      </div>

                      <div className="login-field-group">
                        <label className="login-field-label">Confirm New Password</label>
                        <div className="login-input-container">
                          <input
                            type={showForgotPw ? 'text' : 'password'}
                            className="login-input"
                            placeholder="Repeat new password"
                            value={forgotConfirmPassword}
                            onChange={(e) => setForgotConfirmPassword(e.target.value)}
                            disabled={isForgotSubmitting}
                          />
                        </div>
                      </div>

                      <button
                        type="submit"
                        className="btn-login-primary"
                        disabled={isForgotSubmitting}
                        style={{ background: '#16A34A', marginTop: '0.5rem' }}
                      >
                        {isForgotSubmitting ? 'Updating Password…' : 'Update Administrator Password'}
                      </button>

                      <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                        <button
                          type="button"
                          onClick={() => { setForgotStage('none'); setForgotError(''); }}
                          style={{ background: 'transparent', border: 'none', color: '#64748B', cursor: 'pointer', fontSize: '0.84rem' }}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  </div>
                )}
              </>
            )}

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
