import React from 'react'
import { getSupportiveGuidance } from '../utils/supportiveGuidance.js'

export default function PatientSupportCard({ probability }) {
  if (probability === null || probability === undefined || isNaN(probability)) {
    return null
  }

  const guidance = getSupportiveGuidance(probability)
  if (!guidance) return null

  const pct = (Number(probability) <= 1.0 ? Number(probability) * 100 : Number(probability)).toFixed(1)

  return (
    <div
      className="patient-support-card"
      style={{
        marginTop: '1.25rem',
        borderRadius: '14px',
        padding: '1.25rem 1.35rem',
        background: 'rgba(11, 31, 58, 0.55)',
        border: `1.5px solid ${guidance.accentColor}33`,
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Decorative top accent line */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '3px',
          background: `linear-gradient(90deg, ${guidance.accentColor} 0%, transparent 100%)`,
        }}
      />

      {/* Header Row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: guidance.accentBg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.15rem',
              flexShrink: 0,
            }}
          >
            {guidance.icon}
          </span>
          <div>
            <h4 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 800, color: '#F8FAFC' }}>
              Patient Support & Guidance
            </h4>
            <span style={{ fontSize: '0.74rem', color: guidance.accentColor, fontWeight: 700, letterSpacing: '0.02em' }}>
              {guidance.category} &bull; {guidance.label}
            </span>
          </div>
        </div>

        <span
          style={{
            fontSize: '0.74rem',
            padding: '3px 9px',
            borderRadius: '999px',
            background: 'rgba(255, 255, 255, 0.08)',
            color: '#CBD5E1',
            fontWeight: 600,
          }}
        >
          Model Estimate: {pct}%
        </span>
      </div>

      {/* Headline */}
      <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#E2E8F0', marginBottom: '0.5rem', lineHeight: '1.35' }}>
        {guidance.headline}
      </div>

      {/* Motivational & Supportive Message */}
      <p style={{ margin: '0 0 0.85rem', fontSize: '0.83rem', color: '#94A3B8', lineHeight: '1.55' }}>
        {guidance.message}
      </p>

      {/* Practical Clinical Focus Points */}
      {guidance.practicalFocus && guidance.practicalFocus.length > 0 && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.45)',
            border: '1px solid rgba(255, 255, 255, 0.06)',
            borderRadius: '8px',
            padding: '0.75rem 0.85rem',
            marginBottom: '0.75rem',
          }}
        >
          <div style={{ fontSize: '0.72rem', fontWeight: 800, color: '#38BDF8', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>
            Recommended Focus
          </div>
          <ul style={{ margin: 0, paddingLeft: '1.15rem', fontSize: '0.78rem', color: '#CBD5E1', lineHeight: '1.5' }}>
            {guidance.practicalFocus.map((tip, idx) => (
              <li key={idx}>{tip}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Safety Notice Footer */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.7rem', color: '#64748B', lineHeight: '1.4' }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span>
          Supportive educational text only. Does not replace physician diagnosis or personalized medical therapy.
        </span>
      </div>
    </div>
  )
}
