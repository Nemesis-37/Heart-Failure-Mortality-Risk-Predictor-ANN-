import React, { useEffect, useState } from 'react'
import ThemeToggle from './components/ThemeToggle.jsx'
import { API_BASE_URL } from './apiConfig.js'

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
      setServerError('Please enter your email address and password.')
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
    <div className="login-page">
      <div className="login-left-panel">
        <div className="left-panel-bg-layer" aria-hidden="true" />
        <div className="left-panel-glow-1" aria-hidden="true" />
        <div className="left-panel-glow-2" aria-hidden="true" />
        <div className="left-panel-glow-3" aria-hidden="true" />
        <div className="left-panel-grid-overlay" aria-hidden="true" />
        <div className="left-panel-content">
          <div className="brand-header">
            <div className="brand-text-group">
              <span className="login-access-kicker">Clinical Intelligence</span>
              <h1 className="brand-product-name">Heart Failure<br />Mortality Risk Predictor</h1>
              <p className="brand-tagline">Advanced Clinical Risk Assessment</p>
              <p className="brand-description">
                A clinical decision-support platform for credentialed physicians and administrators.
              </p>
            </div>
          </div>
          <div className="brand-footer-badge">Secure, role-based access</div>
        </div>
      </div>

      <div className="login-right-panel">
        <div className="right-panel-radial" aria-hidden="true" />
        <div className="right-panel-radial-2" aria-hidden="true" />
        <div className="login-form-wrapper">
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
            <ThemeToggle />
          </div>
          <div className="login-form-card">
            {forgotStage === 'none' ? (
              <>
                <div className="login-card-header">
                  <span className="login-access-kicker">Secure Portal Access</span>
                  <h2 className="login-card-title">Sign In</h2>
                  <p className="login-card-subtitle">Use your registered email address and password.</p>
                </div>
                {serverError && <div className="login-server-error" role="alert">{serverError}</div>}
                {forgotSuccess && <div className="forgot-notice" role="status">{forgotSuccess}</div>}
                <form onSubmit={submitLogin} noValidate className="login-form">
                  <div className="login-field-group">
                    <label className="login-field-label" htmlFor="unified-email">Email Address</label>
                    <div className="login-input-container">
                      <span className="login-input-icon" aria-hidden="true">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="2" y="4" width="20" height="16" rx="2" />
                          <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                        </svg>
                      </span>
                      <input
                        id="unified-email"
                        type="email"
                        autoComplete="email"
                        className="login-input has-left-icon"
                        placeholder="name@hospital.org"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        disabled={isSubmitting}
                        required
                      />
                    </div>
                  </div>
                  <div className="login-field-group">
                    <div className="login-label-row">
                      <label className="login-field-label" htmlFor="unified-password">Password</label>
                      <button type="button" className="link-forgot-password" onClick={startRecovery}>
                        Forgot password?
                      </button>
                    </div>
                    <div className="login-input-container password-container">
                      <span className="login-input-icon" aria-hidden="true">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                        </svg>
                      </span>
                      <input
                        id="unified-password"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="current-password"
                        className="login-input has-left-icon"
                        placeholder="Enter your password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        disabled={isSubmitting}
                        required
                      />
                      <button
                        type="button"
                        className="btn-toggle-pw"
                        onClick={() => setShowPassword((value) => !value)}
                        title={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? 'Hide' : 'Show'}
                      </button>
                    </div>
                  </div>
                  <div className="login-options-row">
                    <label className="login-checkbox-label" htmlFor="remember-me">
                      <span className="custom-checkbox-wrapper">
                        <input
                          id="remember-me"
                          type="checkbox"
                          checked={rememberMe}
                          onChange={(event) => setRememberMe(event.target.checked)}
                          disabled={isSubmitting}
                          className="custom-checkbox-input"
                        />
                        <span className="custom-checkbox-box" aria-hidden="true">
                          <svg className="custom-checkbox-check" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </span>
                      </span>
                      <span className="checkbox-text">Remember me on this device</span>
                    </label>
                  </div>
                  <button type="submit" className="btn-login-primary" disabled={isSubmitting}>
                    {isSubmitting ? 'Signing In…' : 'Sign In'}
                  </button>
                  <div className="login-divider"><span>or continue with demo</span></div>
                  <button
                    type="button"
                    className="btn-login-demo"
                    onClick={handleQuickDemo}
                    disabled={isSubmitting}
                  >
                    {isSubmitting && email === 'dr.carter@hospital.org' ? (
                      <>
                        <span className="login-spinner" aria-hidden="true" />
                        <span>Signing In to Demo…</span>
                      </>
                    ) : (
                      <>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                          <polygon points="5 3 19 12 5 21 5 3" />
                        </svg>
                        <span>Quick Demo Access</span>
                      </>
                    )}
                  </button>
                  {onNavigateToRegister && (
                    <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.88rem', color: '#64748B' }}>
                      New physician or resident?{' '}
                      <button type="button" onClick={onNavigateToRegister}>Register for Access</button>
                    </div>
                  )}
                </form>
              </>
            ) : (
              <>
                <div className="login-card-header">
                  <span className="login-access-kicker">Password Recovery</span>
                  <h2 className="login-card-title">
                    {forgotStage === 'email' ? 'Forgot Password' : forgotStage === 'otp' ? 'Verify Code' : 'Set New Password'}
                  </h2>
                  <p className="login-card-subtitle">
                    {forgotStage === 'email' && 'Enter your account email to start recovery.'}
                    {forgotStage === 'otp' && `A verification code was sent to ${forgotMaskedEmail}.`}
                    {forgotStage === 'new_password' && 'Choose a new password for your administrator account.'}
                  </p>
                </div>
                {forgotSuccess && <div className="forgot-notice" role="status">{forgotSuccess}</div>}
                {forgotError && <div className="login-server-error" role="alert">{forgotError}</div>}
                {forgotStage === 'email' && (
                  <form onSubmit={sendRecoveryCode} className="login-form">
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor="recovery-email">Email Address</label>
                      <div className="login-input-container">
                        <span className="login-input-icon" aria-hidden="true">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="2" y="4" width="20" height="16" rx="2" />
                            <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                          </svg>
                        </span>
                        <input
                          id="recovery-email"
                          type="email"
                          autoComplete="email"
                          className="login-input has-left-icon"
                          placeholder="name@hospital.org"
                          value={forgotEmail}
                          onChange={(event) => setForgotEmail(event.target.value)}
                          required
                        />
                      </div>
                    </div>
                    <button className="btn-login-primary" type="submit" disabled={isForgotSubmitting}>
                      {isForgotSubmitting ? 'Sending Code…' : 'Send Verification Code'}
                    </button>
                  </form>
                )}
                {forgotStage === 'otp' && (
                  <form onSubmit={verifyRecoveryCode} className="login-form">
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor="recovery-otp">6-Digit Verification Code</label>
                      <input
                        id="recovery-otp"
                        className="login-input"
                        inputMode="numeric"
                        maxLength={6}
                        value={forgotOTP}
                        onChange={(event) => setForgotOTP(event.target.value.replace(/\D/g, ''))}
                        required
                      />
                    </div>
                    <button className="btn-login-primary" type="submit" disabled={isForgotSubmitting || forgotOTP.length !== 6}>
                      {isForgotSubmitting ? 'Verifying…' : 'Verify Code'}
                    </button>
                    <button type="button" disabled={cooldown > 0 || isForgotSubmitting} onClick={sendRecoveryCode}>
                      {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend Code'}
                    </button>
                  </form>
                )}
                {forgotStage === 'new_password' && (
                  <form onSubmit={resetPassword} className="login-form">
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor="recovery-new-password">New Password</label>
                      <div className="login-input-container">
                        <span className="login-input-icon" aria-hidden="true">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                          </svg>
                        </span>
                        <input
                          id="recovery-new-password"
                          type={showForgotPassword ? 'text' : 'password'}
                          className="login-input has-left-icon"
                          placeholder="Min. 8 characters"
                          autoComplete="new-password"
                          minLength={8}
                          value={forgotNewPassword}
                          onChange={(event) => setForgotNewPassword(event.target.value)}
                          required
                        />
                      </div>
                    </div>
                    <div className="login-field-group">
                      <label className="login-field-label" htmlFor="recovery-confirm-password">Confirm New Password</label>
                      <div className="login-input-container">
                        <span className="login-input-icon" aria-hidden="true">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                          </svg>
                        </span>
                        <input
                          id="recovery-confirm-password"
                          type={showForgotPassword ? 'text' : 'password'}
                          className="login-input has-left-icon"
                          placeholder="Re-enter new password"
                          autoComplete="new-password"
                          minLength={8}
                          value={forgotConfirmPassword}
                          onChange={(event) => setForgotConfirmPassword(event.target.value)}
                          required
                        />
                      </div>
                    </div>
                    <button type="button" className="btn-toggle-pw" onClick={() => setShowForgotPassword((value) => !value)}>
                      {showForgotPassword ? 'Hide passwords' : 'Show passwords'}
                    </button>
                    <button className="btn-login-primary" type="submit" disabled={isForgotSubmitting}>
                      {isForgotSubmitting ? 'Updating Password…' : 'Update Password'}
                    </button>
                  </form>
                )}
                <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                  <button type="button" onClick={returnToLogin}>Back to Sign In</button>
                </div>
              </>
            )}
            <div className="login-card-footer">
              <p>Heart Failure Mortality Risk Predictor &bull; Educational ML Prototype &bull; Not for clinical decision-making</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
