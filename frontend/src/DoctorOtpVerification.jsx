import React, { useState, useEffect, useRef } from 'react'

export default function DoctorOtpVerification({
  email,
  doctorData,
  onVerifiedSuccess,
  onNavigateToLogin,
}) {
  const [digits, setDigits] = useState(['', '', '', '', '', ''])
  const [isVerifying, setIsVerifying] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [countdown, setCountdown] = useState(45)
  const [canResend, setCanResend] = useState(false)
  const [isVerified, setIsVerified] = useState(false)

  const inputRefs = [
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
    useRef(null),
  ]

  // Focus first input on mount
  useEffect(() => {
    inputRefs[0].current?.focus()
  }, [])

  // Cooldown countdown timer
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown((c) => c - 1), 1000)
      return () => clearTimeout(timer)
    } else {
      setCanResend(true)
    }
  }, [countdown])

  const handleDigitChange = (index, value) => {
    // Only accept numbers
    if (value && !/^\d+$/.test(value)) return

    const newDigits = [...digits]

    // Handle paste of complete 6-digit code
    if (value.length > 1) {
      const pasted = value.replace(/\D/g, '').slice(0, 6).split('')
      pasted.forEach((char, i) => {
        newDigits[i] = char
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

    // Move to next input if digit entered
    if (value && index < 5) {
      inputRefs[index + 1].current?.focus()
    }
  }

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs[index - 1].current?.focus()
    }
  }

  const handlePaste = (e) => {
    e.preventDefault()
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (!text) return

    const newDigits = [...digits]
    text.split('').forEach((char, i) => {
      newDigits[i] = char
    })
    setDigits(newDigits)
    setErrorMessage('')
    inputRefs[Math.min(text.length, 5)].current?.focus()
  }

  const handleVerify = async (e) => {
    if (e) e.preventDefault()
    const otpCode = digits.join('')
    if (otpCode.length !== 6) {
      setErrorMessage('Please enter all 6 digits of your verification code.')
      return
    }

    setIsVerifying(true)
    setErrorMessage('')

    try {
      const res = await fetch('http://127.0.0.1:8000/auth/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          otp: otpCode,
        }),
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Verification failed. Please check your code.')
      }

      setIsVerified(true)
      setSuccessMessage(data.message || 'Email verified successfully!')
      if (onVerifiedSuccess) onVerifiedSuccess(data)
    } catch (err) {
      setErrorMessage(err.message || 'Error connecting to verification server.')
    } finally {
      setIsVerifying(false)
    }
  }

  const handleResend = async () => {
    if (!canResend || isResending) return

    setIsResending(true)
    setErrorMessage('')

    try {
      const res = await fetch('http://127.0.0.1:8000/auth/resend-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to resend verification code.')
      }

      setCountdown(data.cooldown_seconds || 45)
      setCanResend(false)
      setDigits(['', '', '', '', '', ''])
      inputRefs[0].current?.focus()
    } catch (err) {
      setErrorMessage(err.message || 'Error requesting new verification code.')
    } finally {
      setIsResending(false)
    }
  }

  return (
    <div className="login-page">
      {/* ───── LEFT PANEL: Clinical Branding ───── */}
      <div className="login-left-panel">
        <div className="left-panel-bg-layer" aria-hidden="true" />
        <div className="left-panel-glow-1" aria-hidden="true" />
        <div className="left-panel-glow-2" aria-hidden="true" />

        <div className="left-panel-brand">
          <div className="brand-icon-shield">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <div className="brand-text-block">
            <span className="brand-name">CardioPredict Portal</span>
            <span className="brand-edition">Two-Factor Email Verification</span>
          </div>
        </div>

        <div className="left-panel-body">
          <div className="left-badge-tag">
            <span className="badge-pulse-dot" aria-hidden="true" />
            <span>Step 2 of 2 &bull; Identity Confirmation</span>
          </div>

          <h1 className="left-panel-headline">
            Institutional Email Ownership Verification
          </h1>

          <p className="left-panel-description">
            To prevent unauthorized access to AI heart failure clinical predictions,
            every physician account requires two-phase confirmation: institutional email validation
            followed by medical council credential approval.
          </p>

          <div className="left-feature-cards">
            <div className="feature-card">
              <div className="feature-card-icon" style={{ background: '#DBEAFE', color: '#1565D8' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                  <polyline points="22,6 12,13 2,6" />
                </svg>
              </div>
              <div className="feature-card-text">
                <h3>One-Time 6-Digit Token</h3>
                <p>Cryptographically hashed and automatically expires after 5 minutes.</p>
              </div>
            </div>

            <div className="feature-card">
              <div className="feature-card-icon" style={{ background: '#ccfbf1', color: '#0f766e' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <polyline points="9 12 11 14 15 10" />
                </svg>
              </div>
              <div className="feature-card-text">
                <h3>Manual Credential Review</h3>
                <p>Email verification alone does not grant access; medical credentials are confirmed manually.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="left-panel-footer">
          <div className="compliance-shield">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span>Rate-Limited Protection &bull; Max 5 Attempts Permitted</span>
          </div>
        </div>
      </div>

      {/* ───── RIGHT PANEL: OTP Verification Form ───── */}
      <div className="login-right-panel" style={{ padding: '2.5rem 1.5rem' }}>
        <div className="login-form-wrapper" style={{ maxWidth: '520px' }}>
          <div className="login-form-card" style={{ padding: '2.5rem' }}>

            {isVerified ? (
              /* Verified Success State */
              <div style={{ textAlign: 'center', padding: '1rem 0' }}>
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
                  color: '#16a34a',
                  background: '#dcfce7',
                  padding: '4px 12px',
                  borderRadius: '12px',
                }}>
                  Email Verified
                </span>

                <h2 style={{
                  fontSize: '1.75rem',
                  fontWeight: 800,
                  color: '#0B1F3A',
                  marginTop: '0.85rem',
                  marginBottom: '0.5rem',
                }}>
                  Email Address Confirmed
                </h2>

                <p style={{ fontSize: '0.92rem', color: '#64748b', lineHeight: 1.6, margin: '0 auto 1.5rem' }}>
                  Your ownership of <strong>{email}</strong> has been successfully established.
                </p>

                {/* Important Notice: Status is still PENDING */}
                <div style={{
                  background: '#fffbeb',
                  border: '1.5px solid #fde68a',
                  borderRadius: '12px',
                  padding: '1.25rem',
                  textAlign: 'left',
                  marginBottom: '1.75rem',
                  fontSize: '0.85rem',
                  color: '#92400e',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', fontWeight: 700, color: '#b45309' }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    <span>Status: Awaiting Administrator Approval</span>
                  </div>
                  <p style={{ margin: 0, lineHeight: 1.55 }}>
                    In accordance with clinical safety regulations, email verification alone does not activate predictive tools.
                    Our administrative credentialing officers are verifying your registration number (<strong>{doctorData?.registration_number || 'Registered License'}</strong>)
                    with the medical council. You will receive an activation notification once approved.
                  </p>
                </div>

                <button
                  type="button"
                  className="btn-login-primary"
                  onClick={onNavigateToLogin}
                  style={{ width: '100%' }}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                    <polyline points="10 17 15 12 10 7" />
                    <line x1="15" y1="12" x2="3" y2="12" />
                  </svg>
                  <span>Return to Doctor Sign In</span>
                </button>
              </div>
            ) : (
              /* OTP Entry State */
              <>
                <div className="login-card-header" style={{ marginBottom: '1.75rem' }}>
                  <span className="login-access-kicker">Two-Factor Authentication</span>
                  <h2 className="login-card-title" style={{ fontSize: '1.85rem' }}>Enter Verification Code</h2>
                  <p className="login-card-subtitle" style={{ fontSize: '0.88rem' }}>
                    We sent a 6-digit confirmation code to <strong>{email}</strong>. Enter it below to verify your email.
                  </p>
                </div>

                {errorMessage && (
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
                    <span>{errorMessage}</span>
                  </div>
                )}

                <form onSubmit={handleVerify} className="login-form">
                  {/* Segmented 6-digit input boxes */}
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: '0.5rem',
                      margin: '1.5rem 0',
                    }}
                    onPaste={handlePaste}
                  >
                    {digits.map((digit, idx) => (
                      <input
                        key={idx}
                        ref={inputRefs[idx]}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={digit}
                        onChange={(e) => handleDigitChange(idx, e.target.value)}
                        onKeyDown={(e) => handleKeyDown(idx, e)}
                        disabled={isVerifying}
                        style={{
                          width: '48px',
                          height: '56px',
                          textAlign: 'center',
                          fontSize: '1.5rem',
                          fontWeight: 700,
                          fontFamily: 'Consolas, monospace',
                          color: '#0B1F3A',
                          background: digit ? '#EFF6FF' : '#ffffff',
                          border: digit ? '2px solid #1565D8' : '1.5px solid #cbd5e1',
                          borderRadius: '10px',
                          outline: 'none',
                          boxShadow: digit ? '0 0 0 3px rgba(21, 101, 216, 0.15)' : 'none',
                          transition: 'all 150ms ease',
                        }}
                      />
                    ))}
                  </div>

                  {/* Verify Code Button */}
                  <button
                    type="submit"
                    className="btn-login-primary"
                    disabled={isVerifying || digits.join('').length !== 6}
                    style={{ width: '100%', minHeight: '50px' }}
                  >
                    {isVerifying ? (
                      <>
                        <span className="login-spinner" aria-hidden="true" />
                        <span>Verifying Code&hellip;</span>
                      </>
                    ) : (
                      <>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        <span>Verify Email Address</span>
                      </>
                    )}
                  </button>

                  {/* Resend Cooldown Section */}
                  <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.85rem', color: '#64748b' }}>
                    {canResend ? (
                      <div>
                        Didn't receive the email?{' '}
                        <button
                          type="button"
                          onClick={handleResend}
                          disabled={isResending}
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
                          {isResending ? 'Sending...' : 'Resend Code Now'}
                        </button>
                      </div>
                    ) : (
                      <span>
                        Resend code available in <strong style={{ color: '#1565D8' }}>{countdown}s</strong>
                      </span>
                    )}
                  </div>

                  <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.82rem' }}>
                    <button
                      type="button"
                      onClick={onNavigateToLogin}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#64748b',
                        cursor: 'pointer',
                      }}
                    >
                      &larr; Back to Sign In
                    </button>
                  </div>
                </form>

                <div className="login-card-footer" style={{ marginTop: '2rem' }}>
                  <p>
                    CardioPredict Clinical Portal &bull; Two-Phase Physician Credentialing
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
