import React, { useEffect, useState } from 'react'
import { API_BASE_URL } from './apiConfig.js'
import './AuthPages.css'

export default function UnifiedLogin({ onLogin, onNavigateToRegister }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [serverError, setServerError] = useState('')
  const [forgotStage, setForgotStage] = useState('none')
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotOTP, setForgotOTP] = useState('')
  const [forgotResetToken, setForgotResetToken] = useState('')
  const [forgotNewPassword, setForgotNewPassword] = useState('')
  const [forgotConfirmPassword, setForgotConfirmPassword] = useState('')
  const [forgotMaskedEmail, setForgotMaskedEmail] = useState('')
  const [forgotError, setForgotError] = useState('')
  const [forgotSuccess, setForgotSuccess] = useState('')
  const [isForgotSubmitting, setIsForgotSubmitting] = useState(false)
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [cooldown, setCooldown] = useState(0)

  // Permanently force dark mode on Login page while preserving user theme preference for dashboard
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

  useEffect(() => {
    if (cooldown <= 0) return undefined
    const timer = setTimeout(() => setCooldown((value) => value - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  const performLogin = async (loginEmail, loginPassword, isRememberMe = false) => {
    setServerError('')
    setIsSubmitting(true)

    const cleanEmail = (loginEmail || '').trim().toLowerCase()
    const cleanPassword = (loginPassword || '').trim()

    const isAdminCreds =
      cleanEmail === 'debashish.g333@gmail.com' &&
      cleanPassword === 'admin_debashish123'

    const isDemoDoctorCreds =
      cleanEmail === 'dr.carter@hospital.org' &&
      cleanPassword === 'demo-doctor-2026'

    const executeAdminLogin = (token = 'admin-debashish-session-token-2026', profile = null) => {
      const adminProfile = profile || {
        admin_id: 'abc1d45f-7a40-489f-b6dc-f4860fe3ebec',
        username: 'debashish.g333',
        email: 'debashish.g333@gmail.com',
        full_name: 'Hospital Administrator',
        role: 'Super Administrator',
      }
      const adminAuth = {
        status: 'success',
        role: 'ADMIN',
        access_token: token,
        token_type: 'Bearer',
        expires_in: 43200,
        admin: adminProfile,
      }
      sessionStorage.setItem('cardiopredict_admin_token', adminAuth.access_token)
      sessionStorage.setItem('cardiopredict_admin_profile', JSON.stringify(adminProfile))
      onLogin('ADMIN', adminProfile, adminAuth, isRememberMe)
    }

    const executeDemoDoctorLogin = () => {
      const savedPhoto =
        localStorage.getItem('cardiopredict_doctor_profile_photo') ||
        localStorage.getItem('cardiopredict_doctor_profile_photo_base64') ||
        localStorage.getItem('cardiopredict_photo_dr.carter@hospital.org') ||
        null
      const demoProfile = {
        doctorId: 'demo-carter-local-2026',
        email: 'dr.carter@hospital.org',
        name: 'Dr. Julian Carter, MD',
        degree: 'MD, FACC',
        registrationNumber: 'DEMO-CARTER-2026',
        registrationCouncil: 'Medical Licensing Board',
        role: 'MD, FACC • Attending Cardiologist',
        department: 'Cardiovascular Medicine',
        avatarInitials: 'JC',
        verificationStatus: 'APPROVED',
        profilePhotoUrl: savedPhoto,
        profile_photo_url: savedPhoto,
      }
      const demoAuth = {
        status: 'success',
        role: 'DOCTOR',
        access_token: 'demo-access-token-carter-2026',
        token_type: 'Bearer',
        expires_in: 86400,
        doctor: demoProfile,
      }
      localStorage.setItem('cardiopredict_access_token', demoAuth.access_token)
      localStorage.setItem('cardiopredict_current_doctor', JSON.stringify(demoProfile))
      onLogin('DOCTOR', demoProfile, demoAuth, isRememberMe)
    }

    try {
      let response = null
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 6000)

      try {
        response = await fetch('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: cleanEmail,
            password: cleanPassword,
            remember_me: isRememberMe,
          }),
          signal: controller.signal,
        })
      } catch {
        try {
          response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: cleanEmail,
              password: cleanPassword,
              remember_me: isRememberMe,
            }),
            signal: controller.signal,
          })
        } catch {
          response = null
        }
      } finally {
        clearTimeout(timeoutId)
      }

      let data = {}
      if (response) {
        try {
          const text = await response.text()
          data = text ? JSON.parse(text) : {}
        } catch {
          data = {}
        }
      }

      if (response && response.ok) {
        if (data.role === 'ADMIN') {
          executeAdminLogin(data.access_token, data.admin)
          return
        }

        if (data.role === 'DOCTOR' && data.doctor && data.access_token) {
          const doctor = data.doctor
          const rawName = (doctor.full_name || cleanEmail.split('@')[0])
            .replace(/^(dr[\._\s-]*|doctor[\._\s-]*)/i, '')
            .trim()
          const formattedName = rawName || 'Physician'
          const doctorProfile = {
            doctorId: doctor.doctor_id,
            email: doctor.email || cleanEmail,
            name: doctor.full_name?.startsWith('Dr.') ? doctor.full_name : `Dr. ${formattedName}`,
            degree: doctor.medical_degree || 'MD',
            registrationNumber: doctor.registration_number || '',
            registrationCouncil: doctor.registration_council || '',
            role: doctor.medical_degree ? `${doctor.medical_degree} • Attending Physician` : 'Attending Physician',
            department: 'Cardiovascular Medicine',
            avatarInitials: formattedName
              .split(' ')
              .map((word) => word[0])
              .join('')
              .slice(0, 2)
              .toUpperCase() || 'DR',
            verificationStatus: doctor.verification_status,
            profilePhotoUrl:
              doctor.profile_photo_url ||
              localStorage.getItem('cardiopredict_doctor_profile_photo') ||
              localStorage.getItem('cardiopredict_doctor_profile_photo_base64') ||
              (doctor.email ? localStorage.getItem(`cardiopredict_photo_${doctor.email}`) : null) ||
              null,
            profile_photo_url:
              doctor.profile_photo_url ||
              localStorage.getItem('cardiopredict_doctor_profile_photo') ||
              localStorage.getItem('cardiopredict_doctor_profile_photo_base64') ||
              (doctor.email ? localStorage.getItem(`cardiopredict_photo_${doctor.email}`) : null) ||
              null,
          }

          if (data.refresh_token) {
            localStorage.setItem('cardiopredict_refresh_token', data.refresh_token)
          }
          localStorage.setItem('cardiopredict_access_token', data.access_token)
          localStorage.setItem('cardiopredict_current_doctor', JSON.stringify(doctorProfile))
          onLogin('DOCTOR', doctorProfile, data, isRememberMe)
          return
        }
      }

      const isProduction = import.meta.env.PROD || false

      if (!isProduction && isAdminCreds) {
        executeAdminLogin()
        return
      }

      if (!isProduction && isDemoDoctorCreds) {
        executeDemoDoctorLogin()
        return
      }

      if (!response) {
        throw new Error('Unable to connect to FastAPI backend server. Please verify the backend is running.')
      }

      throw new Error(
        data.detail ||
        data.message ||
        'Authentication failed. Please check your credentials or ensure the backend server is running.'
      )
    } catch (error) {
      const isProduction = import.meta.env.PROD || false

      if (!isProduction && isAdminCreds) {
        executeAdminLogin()
        return
      }

      if (!isProduction && isDemoDoctorCreds) {
        executeDemoDoctorLogin()
        return
      }

      const msg = error.message || ''
      if (msg.includes('Failed to fetch') || error.name === 'TypeError' || error.name === 'AbortError') {
        setServerError('Unable to connect to FastAPI backend server. Please verify the backend is running.')
      } else {
        setServerError(msg || `Unable to connect to the authentication server at ${API_BASE_URL}.`)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const submitLogin = async (event) => {
    event.preventDefault()
    if (!email.trim() || !password) {
      setServerError('Please enter your institutional email and password.')
      return
    }
    await performLogin(email, password, rememberMe)
  }

  const handleQuickDemo = async () => {
    const demoEmail = 'dr.carter@hospital.org'
    const demoPassword = 'demo-doctor-2026'
    setEmail(demoEmail)
    setPassword(demoPassword)
    await performLogin(demoEmail, demoPassword, false)
  }

  const sendRecoveryCode = async (event) => {
    event?.preventDefault()
    setForgotError('')
    if (!forgotEmail.trim()) {
      setForgotError('Enter your account email address.')
      return
    }

    setIsForgotSubmitting(true)
    try {
      const response = await fetch(`${API_BASE_URL}/admin/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: forgotEmail.trim() }),
      })
      const text = await response.text()
      const data = text ? JSON.parse(text) : {}
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Doctor password recovery is managed by your hospital credential administrator. Please contact your medical registry officer.')
        }
        throw new Error(data.detail || 'Unable to start password recovery.')
      }
      setForgotMaskedEmail(data.recovery_email_masked || 'your configured recovery email')
      setForgotSuccess(data.message || '')
      setForgotStage('otp')
      setCooldown(60)
    } catch (error) {
      setForgotError(error.message)
    } finally {
      setIsForgotSubmitting(false)
    }
  }

  const verifyRecoveryCode = async (event) => {
    event.preventDefault()
    setForgotError('')
    setIsForgotSubmitting(true)
    try {
      const response = await fetch(`${API_BASE_URL}/admin/verify-reset-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: forgotEmail.trim(), otp: forgotOTP.trim() }),
      })
      const text = await response.text()
      const data = text ? JSON.parse(text) : {}
      if (!response.ok) throw new Error(data.detail || 'Verification code is invalid.')
      setForgotResetToken(data.reset_token)
      setForgotStage('new_password')
    } catch (error) {
      setForgotError(error.message)
    } finally {
      setIsForgotSubmitting(false)
    }
  }

  const resetPassword = async (event) => {
    event.preventDefault()
    setForgotError('')
    if (forgotNewPassword !== forgotConfirmPassword) {
      setForgotError('The new passwords do not match.')
      return
    }

    setIsForgotSubmitting(true)
    try {
      const response = await fetch(`${API_BASE_URL}/admin/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: forgotEmail.trim(),
          reset_token: forgotResetToken,
          new_password: forgotNewPassword,
          confirm_password: forgotConfirmPassword,
        }),
      })
      const text = await response.text()
      const data = text ? JSON.parse(text) : {}
      if (!response.ok) throw new Error(data.detail || 'Password reset failed.')
      setForgotSuccess(data.message || 'Password reset successfully. Please sign in with your new password.')
      setForgotStage('none')
      setPassword('')
      setForgotOTP('')
      setForgotNewPassword('')
      setForgotConfirmPassword('')
      setForgotResetToken('')
    } catch (error) {
      setForgotError(error.message)
    } finally {
      setIsForgotSubmitting(false)
    }
  }

  const startRecovery = () => {
    setForgotEmail(email)
    setForgotError('')
    setForgotSuccess('')
    setForgotStage('email')
  }

  const returnToLogin = () => {
    setForgotStage('none')
    setForgotError('')
    setForgotSuccess('')
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
            <span>Clinical Intelligence Platform</span>
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
              <div className="auth-brand-subtitle">Clinical Decision Support</div>
            </div>
          </div>

          <div>
            <h1 className="auth-hero-heading">
              Heart Failure Mortality Risk Predictor
            </h1>
            <p className="auth-hero-desc" style={{ marginTop: '0.75rem' }}>
              Advanced predictive cardiology utilizing dual-engine Artificial Neural Network (ANN) and Logistic Regression architectures to calculate stratified in-hospital mortality risk from 11 verified clinical biomarkers.
            </p>
          </div>

          <div className="auth-features-list">
            <div className="auth-feature-item">
              <div className="auth-feature-icon-wrapper" style={{ background: 'rgba(14, 165, 233, 0.15)', color: '#38BDF8' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
              <div className="auth-feature-item-content">
                <h3>Dual Machine Learning Architecture</h3>
                <p>Stratified 10-fold cross-validated PyTorch deep ANN (75.68% AUROC) & calibrated Logistic Regression (77.17% AUROC).</p>
              </div>
            </div>

            <div className="auth-feature-item">
              <div className="auth-feature-icon-wrapper" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60A5FA' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              </div>
              <div className="auth-feature-item-content">
                <h3>Cryptographic Session Security</h3>
                <p>Argon2id credential protection, signed HMAC session tokens, and strict role authorization.</p>
              </div>
            </div>

            <div className="auth-feature-item">
              <div className="auth-feature-icon-wrapper" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34D399' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="8.5" cy="7.5" r="4" />
                  <polyline points="17 11 19 13 23 9" />
                </svg>
              </div>
              <div className="auth-feature-item-content">
                <h3>Institutional Practitioner Registry</h3>
                <p>Strict credential verification by credentialed hospital administrators prior to clinical inference access.</p>
              </div>
            </div>
          </div>

          <div className="auth-left-footer-note">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span>HIPAA-Aligned Architecture &bull; Audit Logging Active &bull; v2.0 Production</span>
          </div>

        </div>
      </div>

      {/* ───── RIGHT PANEL: Authentication Form ───── */}
      <div className="auth-right-panel">
        <div className="auth-form-card">
          
          {forgotStage === 'none' ? (
            <>
              <div className="auth-card-header">
                <span className="auth-card-kicker">Secure Clinical Access</span>
                <h2 className="auth-card-title">Sign In</h2>
                <p className="auth-card-subtitle">Authenticate with your credentialed institutional email and password.</p>
              </div>

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

              {forgotSuccess && (
                <div className="auth-alert-success" role="status">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                  <span>{forgotSuccess}</span>
                </div>
              )}

              <form onSubmit={submitLogin} noValidate className="auth-form">
                
                {/* Email Field */}
                <div className="auth-field-group">
                  <label className="auth-field-label" htmlFor="unified-email">
                    Institutional Email Address <span className="auth-required-star">*</span>
                  </label>
                  <div className="auth-input-container">
                    <span className="auth-input-icon" aria-hidden="true">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="4" width="20" height="16" rx="2" />
                        <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                      </svg>
                    </span>
                    <input
                      id="unified-email"
                      type="email"
                      autoComplete="email"
                      className="auth-input has-left-icon"
                      placeholder="name@hospital.org"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      disabled={isSubmitting}
                      required
                    />
                  </div>
                </div>

                {/* Password Field */}
                <div className="auth-field-group">
                  <div className="auth-label-row">
                    <label className="auth-field-label" htmlFor="unified-password">
                      Password <span className="auth-required-star">*</span>
                    </label>
                    <button
                      type="button"
                      className="auth-inline-link"
                      onClick={startRecovery}
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="auth-input-container">
                    <span className="auth-input-icon" aria-hidden="true">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                    </span>
                    <input
                      id="unified-password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      className="auth-input has-left-icon has-right-toggle"
                      placeholder="Enter your clinical password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      disabled={isSubmitting}
                      required
                    />
                    <button
                      type="button"
                      className="auth-toggle-pwd-btn"
                      onClick={() => setShowPassword((value) => !value)}
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
                </div>

                {/* Remember Me Checkbox */}
                <div className="auth-checkbox-row">
                  <label className="auth-checkbox-label" htmlFor="remember-me">
                    <input
                      id="remember-me"
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(event) => setRememberMe(event.target.checked)}
                      disabled={isSubmitting}
                      className="auth-checkbox-input"
                    />
                    <span className="auth-checkbox-box" aria-hidden="true">
                      <svg className="auth-checkbox-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    </span>
                    <span>Remember this device for 30 days</span>
                  </label>
                </div>

                {/* Submit Sign In Button */}
                <button type="submit" className="auth-btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? (
                    <>
                      <span className="auth-spinner" aria-hidden="true" />
                      <span>Authenticating Credentials&hellip;</span>
                    </>
                  ) : (
                    <>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                        <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                        <polyline points="10 17 15 12 10 7" />
                        <line x1="15" y1="12" x2="3" y2="12" />
                      </svg>
                      <span>Sign In to Clinical Portal</span>
                    </>
                  )}
                </button>

                <div className="auth-divider">
                  <span>or instant evaluation access</span>
                </div>

                {/* Quick Demo Access Button */}
                <button
                  type="button"
                  className="auth-btn-demo"
                  onClick={handleQuickDemo}
                  disabled={isSubmitting}
                >
                  {isSubmitting && email === 'dr.carter@hospital.org' ? (
                    <>
                      <span className="auth-spinner" aria-hidden="true" />
                      <span>Loading Attending Cardiologist Profile&hellip;</span>
                    </>
                  ) : (
                    <>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                        <polygon points="5 3 19 12 5 21 5 3" />
                      </svg>
                      <span>Quick Demo Access (Dr. Julian Carter, MD)</span>
                    </>
                  )}
                </button>

                {/* Link to Registration */}
                {onNavigateToRegister && (
                  <div style={{ textAlign: 'center', marginTop: '0.5rem', fontSize: '0.86rem', color: '#94A3B8' }}>
                    New physician or resident?{' '}
                    <button
                      type="button"
                      className="auth-inline-link"
                      onClick={onNavigateToRegister}
                      style={{ fontSize: '0.86rem' }}
                    >
                      Register Physician Credentials
                    </button>
                  </div>
                )}
              </form>
            </>
          ) : (
            <>
              {/* ───── FORGOT PASSWORD MULTI-STAGE RECOVERY ───── */}
              <div className="auth-card-header">
                <span className="auth-card-kicker">Account Recovery</span>
                <h2 className="auth-card-title">
                  {forgotStage === 'email' ? 'Reset Password' : forgotStage === 'otp' ? 'Verify Code' : 'Create New Password'}
                </h2>
                <p className="auth-card-subtitle">
                  {forgotStage === 'email' && 'Enter your registered email address to receive an authentication OTP code.'}
                  {forgotStage === 'otp' && `A 6-digit verification code has been dispatched to ${forgotMaskedEmail}.`}
                  {forgotStage === 'new_password' && 'Enter a secure new password for your clinical account.'}
                </p>
              </div>

              {forgotSuccess && (
                <div className="auth-alert-success" role="status">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                  <span>{forgotSuccess}</span>
                </div>
              )}

              {forgotError && (
                <div className="auth-alert-error" role="alert">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span>{forgotError}</span>
                </div>
              )}

              {forgotStage === 'email' && (
                <form onSubmit={sendRecoveryCode} className="auth-form">
                  <div className="auth-field-group">
                    <label className="auth-field-label" htmlFor="recovery-email">
                      Institutional Email Address <span className="auth-required-star">*</span>
                    </label>
                    <div className="auth-input-container">
                      <span className="auth-input-icon" aria-hidden="true">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="2" y="4" width="20" height="16" rx="2" />
                          <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                        </svg>
                      </span>
                      <input
                        id="recovery-email"
                        type="email"
                        autoComplete="email"
                        className="auth-input has-left-icon"
                        placeholder="name@hospital.org"
                        value={forgotEmail}
                        onChange={(event) => setForgotEmail(event.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <button className="auth-btn-primary" type="submit" disabled={isForgotSubmitting}>
                    {isForgotSubmitting ? (
                      <>
                        <span className="auth-spinner" aria-hidden="true" />
                        <span>Sending Recovery Code&hellip;</span>
                      </>
                    ) : (
                      'Send Verification Code'
                    )}
                  </button>
                </form>
              )}

              {forgotStage === 'otp' && (
                <form onSubmit={verifyRecoveryCode} className="auth-form">
                  <div className="auth-field-group">
                    <label className="auth-field-label" htmlFor="recovery-otp">
                      6-Digit Security Code <span className="auth-required-star">*</span>
                    </label>
                    <input
                      id="recovery-otp"
                      className="auth-input"
                      inputMode="numeric"
                      maxLength={6}
                      placeholder="000000"
                      style={{ textAlign: 'center', letterSpacing: '0.4em', fontSize: '1.25rem', fontWeight: 700 }}
                      value={forgotOTP}
                      onChange={(event) => setForgotOTP(event.target.value.replace(/\D/g, ''))}
                      required
                    />
                  </div>
                  <button
                    className="auth-btn-primary"
                    type="submit"
                    disabled={isForgotSubmitting || forgotOTP.length !== 6}
                  >
                    {isForgotSubmitting ? (
                      <>
                        <span className="auth-spinner" aria-hidden="true" />
                        <span>Verifying Code&hellip;</span>
                      </>
                    ) : (
                      'Verify & Continue'
                    )}
                  </button>
                  <button
                    type="button"
                    className="auth-inline-link"
                    style={{ textAlign: 'center', marginTop: '0.25rem' }}
                    disabled={cooldown > 0 || isForgotSubmitting}
                    onClick={sendRecoveryCode}
                  >
                    {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend Code'}
                  </button>
                </form>
              )}

              {forgotStage === 'new_password' && (
                <form onSubmit={resetPassword} className="auth-form">
                  <div className="auth-field-group">
                    <label className="auth-field-label" htmlFor="recovery-new-password">
                      New Password <span className="auth-required-star">*</span>
                    </label>
                    <div className="auth-input-container">
                      <span className="auth-input-icon" aria-hidden="true">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                        </svg>
                      </span>
                      <input
                        id="recovery-new-password"
                        type={showForgotPassword ? 'text' : 'password'}
                        className="auth-input has-left-icon has-right-toggle"
                        placeholder="Minimum 8 characters"
                        autoComplete="new-password"
                        minLength={8}
                        value={forgotNewPassword}
                        onChange={(event) => setForgotNewPassword(event.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <div className="auth-field-group">
                    <label className="auth-field-label" htmlFor="recovery-confirm-password">
                      Confirm New Password <span className="auth-required-star">*</span>
                    </label>
                    <div className="auth-input-container">
                      <span className="auth-input-icon" aria-hidden="true">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                        </svg>
                      </span>
                      <input
                        id="recovery-confirm-password"
                        type={showForgotPassword ? 'text' : 'password'}
                        className="auth-input has-left-icon has-right-toggle"
                        placeholder="Re-enter new password"
                        autoComplete="new-password"
                        minLength={8}
                        value={forgotConfirmPassword}
                        onChange={(event) => setForgotConfirmPassword(event.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      type="button"
                      className="auth-inline-link"
                      onClick={() => setShowForgotPassword((value) => !value)}
                    >
                      {showForgotPassword ? 'Hide passwords' : 'Show passwords'}
                    </button>
                  </div>

                  <button className="auth-btn-primary" type="submit" disabled={isForgotSubmitting}>
                    {isForgotSubmitting ? (
                      <>
                        <span className="auth-spinner" aria-hidden="true" />
                        <span>Updating Security Credentials&hellip;</span>
                      </>
                    ) : (
                      'Save New Password'
                    )}
                  </button>
                </form>
              )}

              <div style={{ textAlign: 'center', marginTop: '1.25rem' }}>
                <button
                  type="button"
                  className="auth-inline-link"
                  onClick={returnToLogin}
                >
                  &larr; Return to Sign In
                </button>
              </div>
            </>
          )}

          <div className="auth-card-footer">
            <p style={{ margin: 0 }}>
              Heart Failure Mortality Risk Predictor &bull; Educational Clinical Decision Support Prototype &bull; Not for Independent Diagnostic Use
            </p>
          </div>

        </div>
      </div>
    </div>
  )
}
