import React from 'react'

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
            <span className="dash-stat-value">0</span>
            <span className="dash-stat-label">Total Assessments</span>
          </div>
          <div className="dash-stat-footer">
            <span className="dash-stat-subtext">No historical records logged yet</span>
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
                <rect x="4" y="4" width="16" height="16" rx="2" ry="2" />
                <rect x="9" y="9" width="6" height="6" />
                <line x1="9" y1="1" x2="9" y2="4" />
                <line x1="15" y1="1" x2="15" y2="4" />
                <line x1="9" y1="20" x2="9" y2="23" />
                <line x1="15" y1="20" x2="15" y2="23" />
                <line x1="20" y1="9" x2="23" y2="9" />
                <line x1="20" y1="14" x2="23" y2="14" />
                <line x1="1" y1="9" x2="4" y2="9" />
                <line x1="1" y1="14" x2="4" y2="14" />
              </svg>
            </div>
          </div>
          <div className="dash-stat-main">
            <span className="dash-stat-value">2 Active</span>
            <span className="dash-stat-label">ML Architectures</span>
          </div>
          <div className="dash-stat-footer">
            <span className="dash-stat-subtext">Logistic Regression &amp; Deep ANN</span>
          </div>
        </div>

        {/* Stat 4: Clinical Biomarkers */}
        <div className="dash-stat-card">
          <div className="dash-stat-header">
            <span className="dash-stat-tag">Feature Pipeline</span>
            <div className="dash-stat-icon icon-emerald" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>
          </div>
          <div className="dash-stat-main">
            <span className="dash-stat-value">11</span>
            <span className="dash-stat-label">Clinical Features</span>
          </div>
          <div className="dash-stat-footer">
            <span className="dash-stat-subtext">Serum assays &amp; hemodynamics</span>
          </div>
        </div>
      </section>

      {/* 3. Quick Action Banner */}
      <section className="dash-quick-action-card" aria-label="Start Patient Assessment">
        <div className="quick-action-text-area">
          <div className="quick-action-badge">Ready for Inference</div>
          <h3 className="quick-action-title">Start a New Patient Mortality Risk Assessment</h3>
          <p className="quick-action-desc">
            Input patient laboratory parameters including Ejection Fraction, Serum Creatinine, and CPK.
            Generate real-time death-event risk probabilities and compare linear baseline with neural network inference.
          </p>
        </div>
        <div className="quick-action-cta">
          <button
            type="button"
            className="btn-quick-action"
            onClick={() => onNavigate('prediction')}
          >
            <span>Open Assessment Form</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </button>
        </div>
      </section>

      {/* 4. Recent Patient Assessments Section */}
      <section className="dash-recent-section" aria-label="Recent Assessments">
        <div className="dash-section-header">
          <div>
            <h3 className="dash-section-title">Recent Patient Assessments</h3>
            <p className="dash-section-subtitle">Clinical audit log of patient evaluations completed in this workspace</p>
          </div>
          <span className="dash-audit-badge">Session Records</span>
        </div>

        {/* Clean Honest Empty State */}
        <div className="dash-empty-state-card">
          <div className="empty-state-icon-wrap" aria-hidden="true">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
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
      </section>

      {/* 5. Quick Clinical Navigation Cards */}
      <section className="dash-nav-cards-grid" aria-label="Clinical Quick Links">
        {/* Card 1: Biomarkers Guide */}
        <div
          className="dash-nav-card"
          onClick={() => onNavigate('parameters')}
          role="button"
          tabIndex={0}
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
