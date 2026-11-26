import React, { useState, useEffect } from 'react'

const WAITING_QUOTES = [
  { text: "Even the heart beats faster than this OTP sometimes.", tag: "CARDIAC PACING" },
  { text: "Your inbox is having a quick coffee break.", tag: "EMAIL DISPATCH" },
  { text: "The OTP is travelling through the digital bloodstream.", tag: "TELEMETRY" },
  { text: "Six digits. One mission. Zero patience.", tag: "SECURITY PROTOCOL" },
  { text: "Your email is playing hide and seek. Check your inbox!", tag: "INBOX MONITOR" },
  { text: "Meanwhile, the neurons are doing their best.", tag: "NEURAL NETWORK" },
]

export default function OtpWaitingVisualizer() {
  const [quoteIndex, setQuoteIndex] = useState(0)
  const [fadeState, setFadeState] = useState('fade-in')
  const [simulatedBpm, setSimulatedBpm] = useState(72)

  // Smooth quote rotation every 4.5 seconds with fade transitions
  useEffect(() => {
    const interval = setInterval(() => {
      setFadeState('fade-out')
      setTimeout(() => {
        setQuoteIndex((prev) => (prev + 1) % WAITING_QUOTES.length)
        setFadeState('fade-in')
      }, 400)
    }, 4500)
    return () => clearInterval(interval)
  }, [])

  // Micro-fluctuating telemetry (70 - 75 BPM)
  useEffect(() => {
    const hrInterval = setInterval(() => {
      setSimulatedBpm((prev) => {
        const delta = Math.floor(Math.random() * 3) - 1
        const next = prev + delta
        return next >= 69 && next <= 75 ? next : 72
      })
    }, 3000)
    return () => clearInterval(hrInterval)
  }, [])

  const currentQuote = WAITING_QUOTES[quoteIndex]

  return (
    <div className="otp-visual-container" aria-label="Medical AI Verification Telemetry">
      {/* ── Top Telemetry Strip ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="auth-pulse-dot" style={{ background: '#34D399', boxShadow: '0 0 8px #34D399' }} />
          <span style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.08em', color: '#34D399', textTransform: 'uppercase' }}>
            VERIFICATION TELEMETRY
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(15, 23, 42, 0.7)', border: '1px solid rgba(56, 189, 248, 0.2)', padding: '2px 8px', borderRadius: '6px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 800, color: '#38BDF8', fontFamily: 'monospace' }}>
            {simulatedBpm}
          </span>
          <span style={{ fontSize: '0.62rem', color: '#94A3B8' }}>BPM</span>
        </div>
      </div>

      {/* ── Central Animated Heart & Orbital Rings ── */}
      <div className="otp-heart-pulse-box">
        <div className="otp-orbital-ring ring-1" />
        <div className="otp-orbital-ring ring-2" />

        <svg
          className="otp-heart-svg"
          width="46"
          height="46"
          viewBox="0 0 24 24"
          fill="#EF4444"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
        </svg>
      </div>

      {/* ── Continuous Simulated ECG Waveform Trace ── */}
      <div style={{ position: 'relative', height: '48px', margin: '0.5rem 0', overflow: 'hidden' }}>
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 400 48"
          preserveAspectRatio="none"
          style={{ display: 'block' }}
        >
          <line x1="0" y1="24" x2="400" y2="24" stroke="rgba(56, 189, 248, 0.15)" strokeDasharray="4 4" />
          <path
            d="M 0,24 L 60,24 L 75,24 Q 85,18 95,24 L 115,24 L 125,10 L 135,38 L 145,4 L 155,30 L 165,24 Q 180,16 195,24 L 260,24 L 275,24 Q 285,18 295,24 L 315,24 L 325,10 L 335,38 L 345,4 L 355,30 L 365,24 Q 380,16 395,24 L 400,24"
            fill="none"
            stroke="#38BDF8"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              filter: 'drop-shadow(0 0 6px rgba(56, 189, 248, 0.7))',
            }}
          />
        </svg>
      </div>

      {/* ── Waiting Humorous Quotes Card ── */}
      <div className="otp-quotes-card">
        <div className="otp-quotes-header">
          <span className="otp-quotes-label">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span>{currentQuote.tag}</span>
          </span>
          <span className="otp-quotes-counter">
            {quoteIndex + 1}/{WAITING_QUOTES.length}
          </span>
        </div>
        <div className={`otp-quote-text ${fadeState}`}>
          &ldquo;{currentQuote.text}&rdquo;
        </div>
      </div>

      {/* Subtle Safety Note */}
      <div style={{ marginTop: '0.75rem', fontSize: '0.65rem', color: '#64748B', textAlign: 'center' }}>
        Simulated ECG &bull; Clinical decision-support demonstration prototype
      </div>
    </div>
  )
}
