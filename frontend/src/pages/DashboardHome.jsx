import React, { useState, useEffect } from 'react'

const API_BASE = 'http://127.0.0.1:8000'

function fetchWithAuth(path) {
  const token = localStorage.getItem('cardiopredict_access_token')
  return fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
}

export default function DashboardHome({ doctorUser, onNavigate }) {
  const cleanDoctorName = (doctorUser?.name || 'Doctor')
    .replace(/^Dr\.\s*Dr\.\s*/i, 'Dr. ')
    .replace(/^Dr\.\s*Dr\b/i, 'Dr. ')

  const todayFormatted = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  const [stats, setStats] = useState(null)
  const [recentAssessments, setRecentAssessments] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function loadDashboard() {
      try {
        const [summaryRes, recentRes] = await Promise.all([
          fetchWithAuth('/dashboard/summary'),
          fetchWithAuth('/dashboard/recent-assessments'),
        ])
        if (cancelled) return
        if (summaryRes.ok) {
          const data = await summaryRes.json()
          setStats(data)
        }
        if (recentRes.ok) {
          const data = await recentRes.json()
          setRecentAssessments(Array.isArray(data) ? data : [])
        }
      } catch (err) {
        console.warn('Dashboard data fetch error:', err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadDashboard()
    return () => { cancelled = true }
  }, [])

  const totalAssessments = stats?.total_assessments ?? '—'
  const totalPredictions = stats?.total_predictions ?? '—'
  const lrPredictions = stats?.logistic_regression_predictions ?? '—'
  const annPredictions = stats?.ann_predictions ?? '—'

  return (
    <div className="dash-home-container">
      {/* 1. Doctor Welcome Hero Card */}
      <section className="dash-home-welcome-card" aria-label="Welcome Overview">
        <div className="dash-welcome-content">
          <div className="dash-welcome-meta-pill">
            <span className="welcome-pulse-dot" />
            <span>Cardiology Service · Shift Active · {todayFormatted}</span>
          </div>
          <h2 className="dash-welcome-title">Welcome back, {cleanDoctorName}</h2>
          <p className="dash-welcome-subtitle">
            Clinical Decision Support Workspace for 30-day heart failure mortality risk estimation.
            Evaluate patient serum biomarkers and hemodynamic measurements using our dual-model machine learning architecture.
          </p>
        </div>
        <div className="dash-welcome-actions">
          <button
            type="button"
            className="btn-dash-primary"
            onClick={() => onNavigate('prediction')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <span>Start New Assessment</span>
          </button>
          <button
            type="button"
            className="btn-dash-secondary"
            onClick={() => onNavigate('parameters')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span>Biomarker Guide</span>
          </button>
        </div>
      </section>

      {/* 2. Four Clinical Overview / Statistics Cards */}
      <section className="dash-stats-grid" aria-label="Clinical Metrics Overview">
        {/* Stat 1: Total Assessments */}
        <div className="dash-stat-card">
          <div className="dash-stat-header">
            <span className="dash-stat-tag">Patient Cohort</span>
            <div className="dash-stat-icon icon-blue" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
              </svg>
            </div>
          </div>
          <div className="dash-stat-main">
            <span className="dash-stat-value">{loading ? '…' : totalAssessments}</span>
            <span className="dash-stat-label">Total Assessments</span>
          </div>
          <div className="dash-stat-footer">
            <span className="dash-stat-subtext">
              {loading ? 'Loading…' : totalAssessments === 0 ? 'No historical records logged yet' : 'Patients evaluated in this session'}
            </span>
          </div>
        </div>

        {/* Stat 2: High-Risk Threshold */}
        <div className="dash-stat-card">
          <div className="dash-stat-header">
            <span className="dash-stat-tag">Classification Cutoff</span>
            <div className="dash-stat-icon icon-teal" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
          </div>
          <div className="dash-stat-main">
            <span className="dash-stat-value">50%</span>
            <span className="dash-stat-label">Decision Boundary</span>
          </div>
          <div className="dash-stat-footer">
            <span className="dash-stat-subtext">Binary probability threshold</span>
          </div>
        </div>

        {/* Stat 3: Active Models */}
        <div className="dash-stat-card">
          <div className="dash-stat-header">
            <span className="dash-stat-tag">Inference Engines</span>
            <div className="dash-stat-icon icon-purple" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
            </div>
          </div>
          <div className="dash-stat-main">
            <span className="dash-stat-value">2</span>
            <span className="dash-stat-label">Active Models</span>
          </div>
          <div className="dash-stat-footer">
            <span className="dash-stat-subtext">LR + Deep Neural Network (ANN)</span>
          </div>
        </div>

        {/* Stat 4: Total Predictions */}
        <div className="dash-stat-card">
          <div className="dash-stat-header">
            <span className="dash-stat-tag">Predictions Run</span>
            <div className="dash-stat-icon icon-blue" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
          </div>
          <div className="dash-stat-main">
            <span className="dash-stat-value">{loading ? '…' : totalPredictions}</span>
            <span className="dash-stat-label">Total Predictions</span>
          </div>
          <div className="dash-stat-footer">
            <span className="dash-stat-subtext">
              {loading ? 'Loading…' : `LR: ${lrPredictions} · ANN: ${annPredictions}`}
            </span>
          </div>
        </div>
      </section>

      {/* 3. Recent Assessments */}
      <section className="dash-recent-section" aria-label="Recent Clinical Assessments">
        <div className="dash-section-header">
          <h3 className="dash-section-title">Recent Assessments</h3>
          <button
            type="button"
            className="dash-view-all-btn"
            onClick={() => onNavigate('assessments')}
          >
            View All →
          </button>
        </div>

        {loading ? (
          <div className="dash-loading-state">
            <span className="dash-spinner" aria-hidden="true" />
            <span>Loading recent assessments…</span>
          </div>
        ) : recentAssessments.length === 0 ? (
          <div className="dash-empty-state">
            <div className="empty-state-icon" aria-hidden="true">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="12" y1="18" x2="12" y2="12" />
                <line x1="9" y1="15" x2="15" y2="15" />
              </svg>
            </div>
            <h4 className="empty-state-title">No Assessments Recorded Yet</h4>
            <p className="empty-state-desc">
              You haven&apos;t run any patient predictions during this clinical session. Once you evaluate a patient in the New Prediction workspace, the inference results, risk classifications, and probability metrics will appear here.
            </p>
            <button
              type="button"
              className="btn-empty-action"
              onClick={() => onNavigate('prediction')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
              <span>Run First Prediction</span>
            </button>
          </div>
        ) : (
          <div className="dash-recent-list">
            {recentAssessments.map((asm) => {
              const dateStr = asm.created_at
                ? new Date(asm.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                : '—'
              return (
                <div key={asm.assessment_id} className="dash-recent-item">
                  <div className="recent-item-left">
                    <span className="recent-item-code">{asm.assessment_id?.slice(0, 8).toUpperCase() || '—'}</span>
                    <span className="recent-item-ref">
                      {asm.patient_reference ? `Ref: ${asm.patient_reference}` : 'Anonymous patient'}
                    </span>
                  </div>
                  <div className="recent-item-right">
                    <span className="recent-item-date">{dateStr}</span>
                    {asm.prediction_count > 0 && (
                      <span className="recent-item-badge">{asm.prediction_count} prediction{asm.prediction_count !== 1 ? 's' : ''}</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* 4. Quick Clinical Navigation Cards */}
      <section className="dash-nav-cards-grid" aria-label="Clinical Quick Links">
        {/* Card 1: Biomarkers Guide */}
        <div
          className="dash-nav-card"
          onClick={() => onNavigate('parameters')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onNavigate('parameters')}
        >
          <div className="nav-card-icon icon-teal" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
          </div>
          <h4 className="nav-card-title">Clinical Parameters Guide</h4>
          <p className="nav-card-desc">
            Explore the diagnostic significance, biological normal ranges, and risk correlation for all 11 patient biomarkers.
          </p>
          <span className="nav-card-link">
            <span>Explore Parameters</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </span>
        </div>

        {/* Card 2: Prediction History */}
        <div
          className="dash-nav-card"
          onClick={() => onNavigate('history')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onNavigate('history')}
        >
          <div className="nav-card-icon icon-blue" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <h4 className="nav-card-title">Prediction History</h4>
          <p className="nav-card-desc">
            Review past patient risk scores, model selections, and probability distributions over time.
          </p>
          <span className="nav-card-link">
            <span>View History</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </span>
        </div>

        {/* Card 3: Model Performance */}
        <div
          className="dash-nav-card"
          onClick={() => onNavigate('performance')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onNavigate('performance')}
        >
          <div className="nav-card-icon icon-purple" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
          </div>
          <h4 className="nav-card-title">Model Performance</h4>
          <p className="nav-card-desc">
            Analyze architectural metrics, sensitivity, specificity, and ROC-AUC for Logistic Regression vs Deep ANN.
          </p>
          <span className="nav-card-link">
            <span>Compare Models</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </span>
        </div>
      </section>
    </div>
  )
}
