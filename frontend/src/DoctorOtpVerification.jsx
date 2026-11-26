import React, { useState, useEffect, useRef } from 'react'
import { getAuthCandidateUrls } from './apiConfig.js'
import { safeParseResponse, parseApiError } from './utils/apiErrorHelper.js'
import OtpWaitingVisualizer from './components/OtpWaitingVisualizer.jsx'
import './AuthPages.css'

export default function DoctorOtpVerification({
  email: initialEmail = '',
  doctorData,
  onVerifiedSuccess,
  onNavigateToLogin,
}) {
  // Retrieve email from props or sessionStorage fallback
  const [email, setEmail] = useState(() => {
    if (initialEmail && initialEmail.trim()) return initialEmail.trim()
    try {
      const stored = sessionStorage.getItem('cardiopredict_pending_otp_email')
      if (stored) return stored.trim()
    } catch (_) {}
    return ''
  })

  const [digits, setDigits] = useState(['', '', '', '', '', ''])
  const [isVerifying, setIsVerifying] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [countdown, setCountdown] = useState(() => (Boolean(import.meta.env?.DEV) ? 5 : 60))
  const [canResend, setCanResend] = useState(false)
  const [isVerified, setIsVerified] = useState(false)
  const [devOtpCode, setDevOtpCode] = useState(() => {
    return (
      doctorData?.dev_otp_code ||
      (() => {
        try {
          return sessionStorage.getItem('cardiopredict_dev_otp_code') || ''
        } catch (_) {
          return ''
        }
      })()
    )
  })

  const inputRefs = [
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
  ]

  // Permanently force dark mode on OTP Verification page
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

  // Persist pending email in sessionStorage
  useEffect(() => {
    if (email) {
      try {
        sessionStorage.setItem('cardiopredict_pending_otp_email', email)
      } catch (_) {}
    }
  }, [email])

  // Automatically focus first input on mount
  useEffect(() => {
    inputRefs[0].current?.focus()
  }, [])

  // Cooldown countdown timer
  useEffect(() => {
    if (countdown > 0) {
      setCanResend(false)
      const timer = setTimeout(() => setCountdown((c) => c - 1), 1000)
      return () => clearTimeout(timer)
    } else {
      setCanResend(true)
    }
  }, [countdown])

  // Mask destination email (e.g. debashish.g333@gmail.com -> d***3@gmail.com)
  const getMaskedEmail = (raw) => {
    if (!raw || !raw.includes('@')) return 'your email'
    const [name, domain] = raw.split('@')
    if (name.length <= 2) return `${name[0]}***@${domain}`
    return `${name[0]}***${name[name.length - 1]}@${domain}`
  }

  const handleDigitChange = (index, value) => {
    // Only accept numeric digits
    if (value && !/^\d+$/.test(value)) return

    const newDigits = [...digits]

    // Handle paste inside an individual input box
    if (value.length > 1) {
      const pasted = value.replace(/\D/g, '').slice(0, 6).split('')
      pasted.forEach((char, i) => {
        if (i < 6) newDigits[i] = char
      })
      setDigits(newDigits)
      const nextIndex = Math.min(pasted.length, 5)
      inputRefs[nextIndex].current?.focus()
      setErrorMessage('')
      return
    }

    newDigits[index] = value.slice(-1)
    setDigits(newDigits)
    setErrorMessage('')

    // Automatically advance to next input box if a digit was entered
    if (value && index < 5) {
      inputRefs[index + 1].current?.focus()
    }
  }

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace') {
      if (!digits[index] && index > 0) {
        inputRefs[index - 1].current?.focus()
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs[index - 1].current?.focus()
    } else if (e.key === 'ArrowRight' && index < 5) {
      inputRefs[index + 1].current?.focus()
    }
  }

  const handlePaste = (e) => {
    e.preventDefault()
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (!text) return

    const newDigits = [...digits]
    text.split('').forEach((char, i) => {
      if (i < 6) newDigits[i] = char
    })
    setDigits(newDigits)
    setErrorMessage('')
    inputRefs[Math.min(text.length, 5)].current?.focus()
  }

  const handleAutofill = (code) => {
    if (!code || code.length !== 6) return
    const newDigits = code.split('')
    setDigits(newDigits)
    setErrorMessage('')
    if (inputRefs[5].current) {
      inputRefs[5].current.focus()
    }
  }

  const handleVerify = async (e) => {
    if (e) e.preventDefault()
    const otpCode = digits.join('')
    if (otpCode.length !== 6) {
      setErrorMessage('Please enter all 6 digits of your verification code.')
      return
    }

    if (!email.trim()) {
      setErrorMessage('Destination email is missing. Please return to registration.')
      return
    }

    setIsVerifying(true)
    setErrorMessage('')

    try {
      const candidateUrls = getAuthCandidateUrls('/auth/verify-otp')
      let successfulData = null
      let lastParsedError = null

      for (const endpoint of candidateUrls) {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 20000)

        try {
          const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: email.trim().toLowerCase(),
              otp: otpCode,
            }),
            signal: controller.signal,
          })
          clearTimeout(timeoutId)

          const parsedBody = await safeParseResponse(res)

          if (res.ok && parsedBody) {
            successfulData = parsedBody
            break
          } else {
            lastParsedError = parseApiError(null, res, parsedBody)
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
        setErrorMessage(lastParsedError?.message || 'Verification failed. Please check your code.')
        return
      }

      setIsVerified(true)
      setSuccessMessage(successfulData.message || 'Email verified successfully!')
      if (onVerifiedSuccess) onVerifiedSuccess(successfulData)
    } catch (err) {
      setErrorMessage(err.message || 'Error connecting to verification server.')
    } finally {
      setIsVerifying(false)
    }
  }

  const handleResend = async () => {
    if (!canResend || isResending) return

    if (!email.trim()) {
      setErrorMessage('Destination email is missing. Please return to registration.')
      return
    }

    setIsResending(true)
    setErrorMessage('')

    try {
      const candidateUrls = getAuthCandidateUrls('/auth/resend-otp')
      let successfulData = null
      let lastParsedError = null

      for (const endpoint of candidateUrls) {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 20000)

        try {
          const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email.trim().toLowerCase() }),
            signal: controller.signal,
          })
          clearTimeout(timeoutId)

          const parsedBody = await safeParseResponse(res)

          if (res.ok && parsedBody) {
            successfulData = parsedBody
            break
          } else {
            lastParsedError = parseApiError(null, res, parsedBody)
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
        setErrorMessage(lastParsedError?.message || 'Failed to resend verification code.')
        return
      }

      setCountdown(successfulData.cooldown_seconds || 60)
      setCanResend(false)
      setDigits(['', '', '', '', '', ''])
      inputRefs[0].current?.focus()
      if (successfulData.dev_otp_code) {
        setDevOtpCode(successfulData.dev_otp_code)
        try {
          sessionStorage.setItem('cardiopredict_dev_otp_code', successfulData.dev_otp_code)
        } catch (_) {}
        setErrorMessage('')
        setSuccessMessage('A new verification code has been generated.')
      } else if (successfulData.delivery_status === 'SENT') {
        setErrorMessage('')
        setSuccessMessage('A verification code has been dispatched to your email address.')
      } else if (successfulData.delivery_status === 'BLOCKED') {
        setErrorMessage(
          successfulData.message ||
            'Notice: SMTP email delivery is currently BLOCKED on the server. Please verify SMTP credentials.'
        )
      }
    } catch (err) {
      setErrorMessage(err.message || 'Error requesting new verification code.')
    } finally {
      setIsResending(false)
    }
  }

  const isComplete = digits.every((d) => d.length === 1)

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
            <span>Two-Stage Clinical Security</span>
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
              Secure Physician Verification
            </h1>
            <p className="auth-hero-desc" style={{ marginTop: '0.75rem' }}>
              To safeguard diagnostic decision-support models, every physician account requires two-phase confirmation: institutional email ownership validation followed by medical council credential review.
            </p>
          </div>

          {/* Animated Medical AI Visualizer & Humorous Waiting Quotes */}
          <OtpWaitingVisualizer />

          {/* Verification Protocol Highlights */}
          <div className="auth-features-list">
            <div className="auth-feature-item">
              <div className="auth-feature-icon-wrapper" style={{ background: 'rgba(14, 165, 233, 0.15)', color: '#38BDF8' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                  <polyline points="22,6 12,13 2,6" />
                </svg>
              </div>
              <div className="auth-feature-text">
                <div className="auth-feature-title">6-Digit Cryptographic Code</div>
                <div className="auth-feature-desc">PBKDF2 salted hash with 5-minute expiry and 5-attempt rate-limiting.</div>
              </div>
            </div>

            <div className="auth-feature-item">
              <div className="auth-feature-icon-wrapper" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34D399' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <polyline points="9 12 11 14 15 10" />
                </svg>
              </div>
              <div className="auth-feature-text">
                <div className="auth-feature-title">Administrative Review Gate</div>
                <div className="auth-feature-desc">Email verification promotes credentials into the hospital admin review queue.</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ───── RIGHT PANEL: OTP Verification Form ───── */}
      <div className="auth-right-panel">
        <div className="auth-form-card register-wide" style={{ maxWidth: '520px' }}>
          {isVerified ? (
            /* Verified Success State */
            <div style={{ textAlign: 'center', padding: '1rem 0' }}>
              <div
                style={{
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
                }}
              >
                <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>

              <span className="auth-brand-badge" style={{ margin: '0 auto 0.75rem' }}>
                Email Verified
              </span>

              <h2 className="auth-card-title" style={{ fontSize: '1.75rem', marginTop: '0.5rem' }}>
                Email Address Confirmed
              </h2>

              <p className="auth-hero-desc" style={{ maxWidth: '440px', margin: '0 auto 1.5rem', fontSize: '0.92rem' }}>
                Ownership of <strong>{email}</strong> has been successfully verified.
              </p>

              {/* Status Notice: Status is still PENDING administrative approval */}
              <div
                style={{
                  background: 'rgba(13, 25, 48, 0.7)',
                  border: '1.5px solid rgba(245, 158, 11, 0.35)',
                  borderRadius: '12px',
                  padding: '1.25rem',
                  textAlign: 'left',
                  marginBottom: '1.75rem',
                  fontSize: '0.86rem',
                  color: '#CBD5E1',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    marginBottom: '0.65rem',
                    fontWeight: 700,
                    color: '#FBBF24',
                  }}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span>Status: Awaiting Administrator Credential Review</span>
                </div>
                <p style={{ margin: 0, lineHeight: 1.55 }}>
                  In accordance with clinical protocol, email verification alone does not activate predictive tools.
                  Your credentials ({doctorData?.registration_number || 'Registered License'}) have now been submitted to the hospital administration queue. A credentialing officer will review and approve your access.
                </p>
              </div>

              <button
                type="button"
                className="auth-btn-primary"
                onClick={onNavigateToLogin}
                style={{ width: '100%' }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                  <polyline points="10 17 15 12 10 7" />
                  <line x1="15" y1="12" x2="3" y2="12" />
                </svg>
                <span>Proceed to Sign In Portal</span>
              </button>
            </div>
          ) : (
            /* OTP Input Form */
            <form onSubmit={handleVerify} noValidate>
              <div className="auth-card-header" style={{ textAlign: 'center' }}>
                <span className="auth-card-kicker">Stage 1: Identity Confirmation</span>
                <h2 className="auth-card-title">Verify Your Email</h2>
                <p className="auth-card-subtitle" style={{ margin: '0 auto' }}>
                  Please enter the 6-digit verification code sent to:
                </p>
                <div className="otp-masked-badge">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                  <span>{getMaskedEmail(email)}</span>
                </div>
              </div>

              {/* Success Alert */}
              {successMessage && (
                <div className="auth-alert-success" role="alert" style={{ marginBottom: '1.25rem' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span>{successMessage}</span>
                </div>
              )}

              {/* Developer Sandbox Active Banner */}
              {devOtpCode && (
                <div
                  style={{
                    background: 'rgba(14, 165, 233, 0.09)',
                    border: '1.5px solid rgba(56, 189, 248, 0.35)',
                    borderRadius: '12px',
                    padding: '1rem 1.25rem',
                    marginBottom: '1.25rem',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#38BDF8', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                      🧪 Development Sandbox Active
                    </span>
                    <span style={{ fontSize: '0.65rem', color: '#94A3B8' }}>Local Mode</span>
                  </div>
                  <div style={{ fontSize: '0.84rem', color: '#CBD5E1', marginBottom: '0.65rem' }}>
                    SMTP unconfigured in <code>.env</code>. Your test verification code is:
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
                    <span
                      style={{
                        fontFamily: 'ui-monospace, monospace',
                        fontSize: '1.45rem',
                        fontWeight: 800,
                        color: '#34D399',
                        background: 'rgba(15, 23, 42, 0.9)',
                        padding: '4px 14px',
                        borderRadius: '8px',
                        letterSpacing: '4px',
                        border: '1px solid rgba(52, 211, 153, 0.4)',
                      }}
                    >
                      {devOtpCode}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleAutofill(devOtpCode)}
                      className="auth-btn-primary"
                      style={{ padding: '6px 14px', fontSize: '0.8rem', height: 'auto', width: 'auto' }}
                    >
                      Autofill Code
                    </button>
                  </div>
                </div>
              )}

              {/* Error Alert */}
              {errorMessage && !devOtpCode && (
                <div className="auth-alert-error" role="alert" style={{ marginBottom: '1.25rem' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* 6 Discrete Digit Inputs */}
              <div className="otp-digits-wrapper" onPaste={handlePaste}>
                {digits.map((digit, idx) => (
                  <input
                    key={idx}
                    ref={inputRefs[idx]}
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleDigitChange(idx, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(idx, e)}
                    className={`otp-digit-input ${digit ? 'filled' : ''}`}
                    aria-label={`Digit ${idx + 1} of verification code`}
                    autoComplete="one-time-code"
                    disabled={isVerifying}
                  />
                ))}
              </div>

              {/* Verify Button */}
              <button
                type="submit"
                className="auth-btn-primary"
                disabled={!isComplete || isVerifying}
                style={{ width: '100%', marginTop: '1rem' }}
              >
                {isVerifying ? (
                  <>
                    <svg
                      className="auth-btn-spinner"
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                    >
                      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                      <path d="M12 2a10 10 0 0 1 10 10" />
                    </svg>
                    <span>Verifying Code...</span>
                  </>
                ) : (
                  <>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    <span>Confirm &amp; Submit Verification</span>
                  </>
                )}
              </button>

              {/* Resend OTP Section */}
              <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.86rem', color: '#94A3B8' }}>
                {countdown > 0 ? (
                  <div>
                    Resend code available in{' '}
                    <strong style={{ color: '#38BDF8', fontFamily: 'monospace' }}>
                      {countdown}s
                    </strong>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={isResending}
                    className="auth-link-button"
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#38BDF8',
                      cursor: 'pointer',
                      fontWeight: 600,
                      textDecoration: 'underline',
                      fontSize: '0.86rem',
                    }}
                  >
                    {isResending ? 'Dispatching new code...' : 'Didn\u2019t receive the code? Resend Code'}
                  </button>
                )}
              </div>

              {/* Back to Sign In Link */}
              <div style={{ textAlign: 'center', marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid rgba(56, 189, 248, 0.12)' }}>
                <button
                  type="button"
                  onClick={onNavigateToLogin}
                  className="auth-link-button"
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#64748B',
                    cursor: 'pointer',
                    fontSize: '0.82rem',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="19" y1="12" x2="5" y2="12" />
                    <polyline points="12 19 5 12 12 5" />
                  </svg>
                  <span>Return to Sign In Portal</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
