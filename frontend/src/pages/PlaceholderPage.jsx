import React from 'react'

export default function PlaceholderPage({ title, subtitle, stepNumber, icon, onNavigate }) {
  return (
    <div className="placeholder-page-wrapper">
      <div className="placeholder-card">
        <div className="placeholder-icon-halo" aria-hidden="true">
          {icon || (
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
              <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
            </svg>
          )}
        </div>

        <div className="placeholder-badge">
          <span>Planned for Step {stepNumber || 'Next'}</span>
        </div>

        <h2 className="placeholder-title">{title}</h2>
        <p className="placeholder-description">
          {subtitle ||
            'This module is scheduled for implementation in the next project milestone. You can navigate back to the dashboard or launch a new patient assessment.'}
        </p>

        <div className="placeholder-actions">
          <button
            type="button"
            className="btn-dash-primary"
            onClick={() => onNavigate('prediction')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <span>Launch Prediction Workspace</span>
          </button>
          <button
            type="button"
            className="btn-dash-secondary"
            onClick={() => onNavigate('dashboard')}
          >
            <span>Back to Dashboard</span>
          </button>
        </div>
      </div>
    </div>
  )
}
