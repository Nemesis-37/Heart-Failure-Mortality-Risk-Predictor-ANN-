import React, { useState, useEffect } from 'react'

const ROTATING_MESSAGES = [
  {
    title: 'Intelligent Cardiac Risk Assessment',
    subtitle: 'Dual-engine real-time inference on admission clinical biomarkers',
    tag: 'CLINICAL INFERENCE',
    color: '#38BDF8',
  },
  {
    title: 'ANN + Logistic Regression',
    subtitle: 'Transparent comparison between deep neural network and interpretable linear model',
    tag: 'DUAL ARCHITECTURE',
    color: '#34D399',
  },
  {
    title: 'Evidence-Informed Decision Support',
    subtitle: 'Calibrated survival risk stratification conditioned on 11 admission features',
    tag: 'CARDIOLOGY PROTOCOL',
    color: '#C084FC',
  },
  {
    title: 'Designed for Clinical Research',
    subtitle: 'Educational prototype demonstrating machine learning dynamics in tabular medicine',
    tag: 'ACADEMIC AUDIT',
    color: '#FBBF24',
  },
]

const FLOATING_BIOMARKERS = [
  { label: 'LVEF', value: '38%', desc: 'Systolic Function', delay: '0s' },
  { label: 'Creatinine', value: '1.3 mg/dL', desc: 'Cardiorenal Marker', delay: '1.2s' },
  { label: 'CPK Enzyme', value: '250 mcg/L', desc: 'Biomarker', delay: '2.4s' },
  { label: 'Serum Sodium', value: '137 mEq/L', desc: 'Electrolyte Balance', delay: '3.6s' },
]

export default function MedicalAiVisualizer() {
  const [activeMessageIndex, setActiveMessageIndex] = useState(0)
  const [heartRate, setHeartRate] = useState(72)

  // Rotating clinical messages carousel
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveMessageIndex((prev) => (prev + 1) % ROTATING_MESSAGES.length)
    }, 4000)
    return () => clearInterval(timer)
  }, [])

  // Micro-fluctuation on heart rate telemetry (71 - 74 BPM)
  useEffect(() => {
    const hrTimer = setInterval(() => {
      setHeartRate((prev) => {
        const delta = Math.floor(Math.random() * 3) - 1 // -1, 0, or +1
        const next = prev + delta
        return next >= 69 && next <= 75 ? next : 72
      })
    }, 2800)
    return () => clearInterval(hrTimer)
  }, [])

  const currentMsg = ROTATING_MESSAGES[activeMessageIndex]

  return (
    <section
      className="med-ai-visualizer-card"
      aria-label="Medical AI System Visualization and Cardiac Monitor"
    >
      {/* Background Ambient Glow & Grid Pattern */}
      <div className="med-ai-glow" aria-hidden="true" />
      <div className="med-ai-grid" aria-hidden="true" />

      {/* ── Top Header: Cardiac Monitor Telemetry ── */}
      <div className="med-ai-header">
        <div className="med-ai-pulse-group">
          <div className="med-ai-heart-indicator">
            <svg
              className="med-ai-heart-icon"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
            </svg>
            <span className="med-ai-pulse-ring" aria-hidden="true" />
          </div>
          <div>
            <div className="med-ai-status-label">
              <span className="med-ai-live-dot" aria-hidden="true" />
              SIMULATION TELEMETRY
            </div>
            <div className="med-ai-rhythm-text">Simulated Sinus Rhythm (Illustrative)</div>
          </div>
        </div>

        <div className="med-ai-telemetry-stats">
          <div className="med-ai-stat-box" title="Illustrative demonstration rate (not real patient monitoring)">
            <span className="med-ai-stat-value font-mono">{heartRate}</span>
            <span className="med-ai-stat-unit">BPM (Simulated)</span>
          </div>
          <div className="med-ai-model-pill">
            <span className="med-ai-pill-dot" aria-hidden="true" />
            <span>ANN + LR</span>
          </div>
        </div>
      </div>

      {/* ── Middle: Animated Cardiac ECG Waveform Tracing ── */}
      <div className="med-ai-ecg-container" aria-hidden="true">
        <div className="med-ai-oscilloscope-grid" />
        <svg
          className="med-ai-ecg-svg"
          viewBox="0 0 600 120"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="ecgGlowGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#0284C7" stopOpacity="0.2" />
              <stop offset="35%" stopColor="#38BDF8" stopOpacity="0.8" />
              <stop offset="50%" stopColor="#34D399" stopOpacity="1" />
              <stop offset="65%" stopColor="#38BDF8" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#0284C7" stopOpacity="0.2" />
            </linearGradient>
            <filter id="ecgNeon" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Reference flat guide line */}
          <line
            x1="0"
            y1="60"
            x2="600"
            y2="60"
            stroke="rgba(56, 189, 248, 0.12)"
            strokeDasharray="4 4"
          />

          {/* Continuous Authentic P-QRS-T Path Loop */}
          <path
            className="med-ai-ecg-trace"
            d="
              M 0,60
              L 40,60
              Q 50,52 60,60
              L 75,60
              L 85,72
              L 95,12
              L 105,95
              L 115,50
              L 125,60
              Q 145,40 165,60
              L 200,60
              L 240,60
              Q 250,52 260,60
              L 275,60
              L 285,72
              L 295,12
              L 305,95
              L 315,50
              L 325,60
              Q 345,40 365,60
              L 400,60
              L 440,60
              Q 450,52 460,60
              L 475,60
              L 485,72
              L 495,12
              L 505,95
              L 515,50
              L 525,60
              Q 545,40 565,60
              L 600,60
            "
            fill="none"
            stroke="url(#ecgGlowGrad)"
            strokeWidth="2.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            filter="url(#ecgNeon)"
          />
        </svg>

        {/* Dynamic Sweep Glow Head */}
        <div className="med-ai-sweep-head" />
      </div>

      {/* ── Neural Network Synapses & Biomarker Convergence ── */}
      <div className="med-ai-synapse-row" aria-hidden="true">
        <div className="med-ai-nn-diagram">
          <svg width="100%" height="46" viewBox="0 0 280 46" fill="none">
            {/* Synaptic connection paths */}
            <line x1="24" y1="12" x2="110" y2="23" stroke="rgba(56, 189, 248, 0.3)" strokeWidth="1.2" strokeDasharray="3 3" className="med-ai-synapse-pulse" />
            <line x1="24" y1="23" x2="110" y2="23" stroke="rgba(56, 189, 248, 0.45)" strokeWidth="1.2" />
            <line x1="24" y1="34" x2="110" y2="23" stroke="rgba(56, 189, 248, 0.3)" strokeWidth="1.2" strokeDasharray="3 3" className="med-ai-synapse-pulse delay-1" />

            <line x1="110" y1="23" x2="190" y2="16" stroke="rgba(52, 211, 153, 0.4)" strokeWidth="1.2" />
            <line x1="110" y1="23" x2="190" y2="30" stroke="rgba(52, 211, 153, 0.4)" strokeWidth="1.2" strokeDasharray="3 3" className="med-ai-synapse-pulse delay-2" />

            <line x1="190" y1="16" x2="260" y2="23" stroke="rgba(192, 132, 252, 0.5)" strokeWidth="1.4" />
            <line x1="190" y1="30" x2="260" y2="23" stroke="rgba(192, 132, 252, 0.5)" strokeWidth="1.4" />

            {/* Input layer nodes (11 biomarkers) */}
            <circle cx="24" cy="12" r="4.5" fill="#0284C7" stroke="#38BDF8" strokeWidth="1.5" />
            <circle cx="24" cy="23" r="4.5" fill="#0284C7" stroke="#38BDF8" strokeWidth="1.5" />
            <circle cx="24" cy="34" r="4.5" fill="#0284C7" stroke="#38BDF8" strokeWidth="1.5" />

            {/* Hidden layer 1 (64) */}
            <circle cx="110" cy="23" r="6" fill="#0D9488" stroke="#34D399" strokeWidth="1.8" className="med-ai-node-glow" />

            {/* Hidden layer 2 (32) */}
            <circle cx="190" cy="16" r="5" fill="#2563EB" stroke="#60A5FA" strokeWidth="1.5" />
            <circle cx="190" cy="30" r="5" fill="#2563EB" stroke="#60A5FA" strokeWidth="1.5" />

            {/* Output layer (Logit / P(Death)) */}
            <circle cx="260" cy="23" r="7" fill="#9333EA" stroke="#C084FC" strokeWidth="2" className="med-ai-node-pulse" />
          </svg>
        </div>

        <div className="med-ai-nn-labels">
          <span className="font-mono text-cyan-400">11 Inputs</span>
          <span className="med-ai-arrow" aria-hidden="true">→</span>
          <span className="font-mono text-emerald-400">Deep MLP</span>
          <span className="med-ai-arrow" aria-hidden="true">→</span>
          <span className="font-mono text-purple-400">P(Risk)</span>
        </div>
      </div>

      {/* ── Floating Clinical Biomarker Pills (Demonstration Values) ── */}
      <div className="med-ai-biomarkers-header">
        <span className="med-ai-biomarkers-title">Sample Clinical Biomarkers</span>
        <span className="med-ai-biomarkers-subtitle">(Demonstration Values Only)</span>
      </div>
      <div className="med-ai-biomarkers-grid">
        {FLOATING_BIOMARKERS.map((item, idx) => (
          <div
            key={idx}
            className="med-ai-biomarker-pill"
            style={{ animationDelay: item.delay }}
          >
            <div className="med-ai-pill-top">
              <span className="med-ai-biomarker-name">{item.label}</span>
              <span className="med-ai-biomarker-val font-mono">{item.value}</span>
            </div>
            <div className="med-ai-biomarker-desc">{item.desc}</div>
          </div>
        ))}
      </div>

      {/* ── Bottom: Rotating Clinical Presentation Carousel ── */}
      <div className="med-ai-carousel-section">
        <div className="med-ai-carousel-indicator-row">
          <span
            className="med-ai-carousel-badge"
            style={{ borderColor: currentMsg.color, color: currentMsg.color }}
          >
            {currentMsg.tag}
          </span>
          <div className="med-ai-carousel-dots" aria-hidden="true">
            {ROTATING_MESSAGES.map((_, i) => (
              <button
                key={i}
                type="button"
                className={`med-ai-dot ${i === activeMessageIndex ? 'active' : ''}`}
                onClick={() => setActiveMessageIndex(i)}
                aria-label={`Go to slide ${i + 1}`}
              />
            ))}
          </div>
        </div>

        <div className="med-ai-carousel-content" key={activeMessageIndex}>
          <h4 className="med-ai-carousel-title">{currentMsg.title}</h4>
          <p className="med-ai-carousel-sub">{currentMsg.subtitle}</p>
        </div>
      </div>

      {/* ── Clinical Safety Notice: Explicit Educational Prototype Disclaimer ── */}
      <div className="med-ai-safety-notice" role="note">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true" style={{ flexShrink: 0, marginTop: '1px' }}>
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span>
          <strong>Educational Prototype Notice:</strong> The simulated cardiac rhythm, ~72 BPM telemetry, and biomarker figures shown above are illustrative demonstration values. This animation is not live patient monitoring and does not represent a real patient&rsquo;s current physiological state.
        </span>
      </div>
    </section>
  )
}
