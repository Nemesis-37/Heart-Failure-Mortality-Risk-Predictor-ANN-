import React, { useState, useEffect } from 'react'
import { apiUrl } from '../apiConfig.js'

function fetchWithAuth(path) {
  const token = localStorage.getItem('cardiopredict_access_token')
  return fetch(apiUrl(path), {
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
  const [recentPredictions, setRecentPredictions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function loadDashboard() {
      try {
        const [summaryRes, recentAsmRes, recentPredRes] = await Promise.all([
          fetchWithAuth('/dashboard/summary'),
          fetchWithAuth('/dashboard/recent-assessments'),
          fetchWithAuth('/dashboard/recent-predictions'),
        ])
        if (cancelled) return
        if (summaryRes.ok) {
          const data = await summaryRes.json()
          setStats(data)
        }
        if (recentAsmRes.ok) {
          const data = await recentAsmRes.json()
          setRecentAssessments(Array.isArray(data) ? data.slice(0, 5) : [])
        }
        if (recentPredRes.ok) {
          const data = await recentPredRes.json()
          setRecentPredictions(Array.isArray(data) ? data.slice(0, 5) : [])
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

  const totalAssessments = stats?.total_assessments ?? 0
  const totalPredictions = stats?.total_predictions ?? 0
  const lrPredictions = stats?.logistic_regression_predictions ?? 0
  const annPredictions = stats?.ann_predictions ?? 0

  const formatDate = (dateStr) => {
    if (!dateStr) return '—'
    try {
      return new Date(dateStr).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="dash-home-container" style={{ maxWidth: '1280px', margin: '0 auto', paddingBottom: '3rem' }}>
      {/* 1. Doctor Welcome Hero Card */}
      <section className="dash-home-welcome-card" aria-label="Welcome Overview" style={{
        background: 'linear-gradient(135deg, #0B1F3A 0%, #102F56 60%, #1565D8 100%)',
        borderRadius: '16px',
        padding: '2rem 2.25rem',
        color: '#FFFFFF',
        marginBottom: '2rem',
        boxShadow: '0 8px 24px rgba(11, 31, 58, 0.12)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1.5rem',
      }}>
        <div style={{ maxWidth: '680px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(255,255,255,0.12)',
            padding: '5px 12px',
            borderRadius: '20px',
            fontSize: '0.78rem',
            fontWeight: 600,
            marginBottom: '10px',
            backdropFilter: 'blur(8px)',
          }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#38BDF8', boxShadow: '0 0 8px #38BDF8' }} />
            <span>Cardiology Service &bull; Shift Active &bull; {todayFormatted}</span>
          </div>
          <h2 style={{ margin: '0 0 6px', fontSize: '1.85rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
            Your Clinical Workspace
          </h2>
          <p style={{ margin: '0 0 8px', fontSize: '1rem', fontWeight: 600, color: '#93C5FD' }}>
            Welcome back, {cleanDoctorName}
          </p>
          <p style={{ margin: 0, fontSize: '0.93rem', color: '#DBEAFE', lineHeight: '1.6', opacity: 0.95 }}>
            Manage patient assessments, review model-generated risk estimates, compare ANN and Logistic Regression outputs, and explore patient education resources from one place.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => onNavigate('prediction')}
            style={{
              background: '#38BDF8',
              color: '#0B1F3A',
              border: 'none',
              padding: '12px 22px',
              borderRadius: '10px',
              fontWeight: 700,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 14px rgba(56, 189, 248, 0.3)',
            }}
          >
            <span>⚡</span>
            <span>Make Prediction</span>
          </button>
          <button
            type="button"
            onClick={() => onNavigate('assessments')}
            style={{
              background: 'rgba(255,255,255,0.15)',
              color: '#FFFFFF',
              border: '1px solid rgba(255,255,255,0.3)',
              padding: '12px 20px',
              borderRadius: '10px',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span>📋</span>
            <span>Patient Assessments</span>
          </button>
        </div>
      </section>

      {/* 2. Platform Clinical Workflow Guidance */}
      <section aria-label="Using This Platform Guide" style={{ marginBottom: '2rem' }}>
        <div style={{
          background: 'var(--surface-card, #FFFFFF)',
          border: '1px solid var(--surface-border, #E2E8F0)',
          borderRadius: '16px',
          padding: '1.75rem 2rem',
          boxShadow: '0 4px 16px rgba(11, 31, 58, 0.04)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '0.5rem' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'rgba(21, 101, 216, 0.1)',
              color: '#1565D8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.1rem',
              fontWeight: 800,
            }}>
              🧭
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary, #0B1F3A)' }}>
                Using This Platform
              </h3>
              <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted, #64748B)' }}>
                Step-by-step clinical workflow for patient mortality risk evaluation and guidance
              </p>
            </div>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '0.85rem',
            marginTop: '1.25rem',
          }}>
            {[
              { step: '1', title: 'Enter Clinical Biomarkers', desc: 'Enter clinical values in the Clinical Parameters input form' },
              { step: '2', title: 'Execute Risk Models', desc: 'Click Run Mortality Risk Evaluation to execute the prediction models' },
              { step: '3', title: 'Evaluate Risk Estimates', desc: 'Review the predicted mortality risk percentage, risk category, and contributing risk factors' },
              { step: '4', title: 'Compare Dual Models', desc: 'Use the model comparison to review outputs from both Logistic Regression and Artificial Neural Network models' },
              { step: '5', title: 'Patient Support & Guidance', desc: 'Check the Patient Support & Guidance section for tailored, non-fatalistic communication points' },
              { step: '6', title: 'Clinical Reference Library', desc: 'Access the Clinical Parameters Guide or Heart Health Counselling resources for reference' },
              { step: '7', title: 'Session History Audit', desc: 'All assessments are recorded in your clinical session history for reference' },
            ].map((item) => (
              <div
                key={item.step}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                  padding: '0.85rem 1rem',
                  borderRadius: '10px',
                  background: 'var(--surface-card-subtle, rgba(241, 245, 249, 0.6))',
                  border: '1px solid var(--surface-border-subtle, rgba(226, 232, 240, 0.8))',
                }}
              >
                <div style={{
                  flexShrink: 0,
                  width: '26px',
                  height: '26px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #1565D8 0%, #0284C7 100%)',
                  color: '#FFFFFF',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.8rem',
                  fontWeight: 800,
                  boxShadow: '0 2px 6px rgba(21, 101, 216, 0.3)',
                }}>
                  {item.step}
                </div>
                <div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary, #0F172A)', marginBottom: '2px' }}>
                    {item.title}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary, #475569)', lineHeight: 1.45 }}>
                    {item.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 3. Doctor Dashboard Statistics (Actual Records Belonging Strictly to Logged-in Doctor) */}
      <section aria-label="Clinical Metrics Overview" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: '#0B1F3A' }}>
            Clinical Activity Statistics
          </h3>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1.25rem',
        }}>
          {/* Stat 1: Total Assessments */}
          <div className="stat-card" style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            border: '1px solid #DBEAFE',
            padding: '1.5rem',
            boxShadow: '0 2px 8px rgba(11, 31, 58, 0.04)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#1565D8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Total Assessments
              </span>
              <span style={{ background: '#EFF6FF', color: '#1565D8', padding: '6px 10px', borderRadius: '8px', fontSize: '1rem' }}>📋</span>
            </div>
            <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#0B1F3A', marginTop: '10px' }}>
              {loading ? '…' : totalAssessments}
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748B', marginTop: '4px' }}>
              Patient profiles recorded by you
            </div>
          </div>

          {/* Stat 2: Total Predictions */}
          <div className="stat-card" style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            border: '1px solid #DBEAFE',
            padding: '1.5rem',
            boxShadow: '0 2px 8px rgba(11, 31, 58, 0.04)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0D9488', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Total Predictions
              </span>
              <span style={{ background: '#F0FDFA', color: '#0D9488', padding: '6px 10px', borderRadius: '8px', fontSize: '1rem' }}>⚡</span>
            </div>
            <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#0D9488', marginTop: '10px' }}>
              {loading ? '…' : totalPredictions}
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748B', marginTop: '4px' }}>
              Dual-model risk evaluations run
            </div>
          </div>

          {/* Stat 3: Logistic Regression Predictions */}
          <div className="stat-card" style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            border: '1px solid #DBEAFE',
            padding: '1.5rem',
            boxShadow: '0 2px 8px rgba(11, 31, 58, 0.04)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#2563EB', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Logistic Regression
              </span>
              <span style={{ background: '#EFF6FF', color: '#2563EB', padding: '6px 10px', borderRadius: '8px', fontSize: '1rem' }}>📊</span>
            </div>
            <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#1565D8', marginTop: '10px' }}>
              {loading ? '…' : lrPredictions}
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748B', marginTop: '4px' }}>
              Linear log-odds baseline inferences
            </div>
          </div>

          {/* Stat 4: ANN Predictions */}
          <div className="stat-card" style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            border: '1px solid #DDD6FE',
            padding: '1.5rem',
            boxShadow: '0 2px 8px rgba(124, 58, 237, 0.04)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#7C3AED', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                ANN Predictions
              </span>
              <span style={{ background: '#F5F3FF', color: '#7C3AED', padding: '6px 10px', borderRadius: '8px', fontSize: '1rem' }}>🧠</span>
            </div>
            <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#7C3AED', marginTop: '10px' }}>
              {loading ? '…' : annPredictions}
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748B', marginTop: '4px' }}>
              Deep Neural Network (32-16) runs
            </div>
          </div>
        </div>
      </section>

      {/* 3. Quick Actions Shortcuts */}
      <section aria-label="Quick Actions" style={{ marginBottom: '2.25rem' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '1.15rem', fontWeight: 800, color: '#0B1F3A' }}>
          Quick Actions
        </h3>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
        }}>
          {/* Action 1: Create New Assessment */}
          <button
            type="button"
            className="quick-action-card"
            onClick={() => onNavigate('assessments')}
            style={{
              background: '#FFFFFF',
              border: '1px solid #BFDBFE',
              borderRadius: '12px',
              padding: '1.25rem 1rem',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              cursor: 'pointer',
              boxShadow: '0 2px 6px rgba(11, 31, 58, 0.03)',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease',
            }}
          >
            <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: '#EFF6FF', color: '#1565D8', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem' }}>
              ➕
            </div>
            <span style={{ fontWeight: 700, color: '#0B1F3A', fontSize: '0.9rem' }}>Create New Assessment</span>
            <span style={{ fontSize: '0.74rem', color: '#64748B', textAlign: 'center' }}>Record 11 patient biomarkers</span>
          </button>

          {/* Action 2: Make Prediction */}
          <button
            type="button"
            className="quick-action-card"
            onClick={() => onNavigate('prediction')}
            style={{
              background: '#FFFFFF',
              border: '1px solid #99F6E4',
              borderRadius: '12px',
              padding: '1.25rem 1rem',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              cursor: 'pointer',
              boxShadow: '0 2px 6px rgba(11, 31, 58, 0.03)',
            }}
          >
            <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: '#F0FDFA', color: '#0D9488', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem' }}>
              ⚡
            </div>
            <span style={{ fontWeight: 700, color: '#0B1F3A', fontSize: '0.9rem' }}>Make Prediction</span>
            <span style={{ fontSize: '0.74rem', color: '#64748B', textAlign: 'center' }}>Execute LR or Deep ANN</span>
          </button>

          {/* Action 3: View Assessment History */}
          <button
            type="button"
            className="quick-action-card"
            onClick={() => onNavigate('assessments')}
            style={{
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '12px',
              padding: '1.25rem 1rem',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              cursor: 'pointer',
              boxShadow: '0 2px 6px rgba(11, 31, 58, 0.03)',
            }}
          >
            <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: '#F8FAFC', color: '#475569', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem' }}>
              📁
            </div>
            <span style={{ fontWeight: 700, color: '#0B1F3A', fontSize: '0.9rem' }}>View Assessment History</span>
            <span style={{ fontSize: '0.74rem', color: '#64748B', textAlign: 'center' }}>Manage clinical profiles</span>
          </button>

          {/* Action 4: View Prediction History */}
          <button
            type="button"
            className="quick-action-card"
            onClick={() => onNavigate('history')}
            style={{
              background: '#FFFFFF',
              border: '1px solid #DDD6FE',
              borderRadius: '12px',
              padding: '1.25rem 1rem',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              cursor: 'pointer',
              boxShadow: '0 2px 6px rgba(11, 31, 58, 0.03)',
            }}
          >
            <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: '#F5F3FF', color: '#7C3AED', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem' }}>
              📜
            </div>
            <span style={{ fontWeight: 700, color: '#0B1F3A', fontSize: '0.9rem' }}>View Prediction History</span>
            <span style={{ fontSize: '0.74rem', color: '#64748B', textAlign: 'center' }}>Audit historical inference runs</span>
          </button>

          {/* Action 5: Open Heart Health Counselling */}
          <button
            type="button"
            className="quick-action-card"
            onClick={() => onNavigate('counselling')}
            style={{
              background: '#FFFFFF',
              border: '1px solid #FED7AA',
              borderRadius: '12px',
              padding: '1.25rem 1rem',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              cursor: 'pointer',
              boxShadow: '0 2px 6px rgba(11, 31, 58, 0.03)',
            }}
          >
            <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: '#FFF7ED', color: '#EA580C', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem' }}>
              ❤️
            </div>
            <span style={{ fontWeight: 700, color: '#0B1F3A', fontSize: '0.9rem' }}>Heart Health Counselling</span>
            <span style={{ fontSize: '0.74rem', color: '#64748B', textAlign: 'center' }}>6-part patient care guides</span>
          </button>
        </div>
      </section>

      {/* 4. Two-Column Live Records Grid: Recent Assessments & Recent Predictions */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))',
        gap: '1.75rem',
      }}>
        {/* Panel A: Recent Assessments (Latest 5) */}
        <section className="dashboard-panel-card" style={{
          background: '#FFFFFF',
          borderRadius: '16px',
          border: '1px solid #DBEAFE',
          padding: '1.75rem',
          boxShadow: '0 2px 10px rgba(11, 31, 58, 0.04)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#0B1F3A', fontWeight: 800 }}>
                Recent Assessments
              </h3>
              <span style={{ fontSize: '0.78rem', color: '#64748B' }}>Latest 5 patient evaluations logged by you</span>
            </div>
            <button
              type="button"
              onClick={() => onNavigate('assessments')}
              style={{
                background: '#EFF6FF',
                color: '#1565D8',
                border: '1px solid #BFDBFE',
                padding: '6px 12px',
                borderRadius: '8px',
                fontSize: '0.78rem',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              View All &rarr;
            </button>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#64748B' }}>Loading assessments…</div>
          ) : recentAssessments.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 1.5rem', background: '#F8FAFC', borderRadius: '12px', border: '1px dashed #CBD5E1' }}>
              <div style={{ fontSize: '1.75rem', marginBottom: '8px' }}>📋</div>
              <h4 style={{ margin: '0 0 6px', color: '#0B1F3A', fontSize: '0.95rem' }}>No Assessments Recorded Yet</h4>
              <p style={{ margin: '0 0 14px', color: '#64748B', fontSize: '0.82rem', lineHeight: '1.5' }}>
                You have not logged any patient profiles. Create your first assessment to record clinical parameters.
              </p>
              <button
                type="button"
                onClick={() => onNavigate('assessments')}
                style={{
                  background: '#1565D8',
                  color: '#FFFFFF',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                + Create First Assessment
              </button>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="recent-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.84rem' }}>
                <thead>
                  <tr style={{ background: '#F8FAFC', borderBottom: '2px solid #E2E8F0', color: '#64748B' }}>
                    <th style={{ padding: '10px 12px' }}>Assessment ID</th>
                    <th style={{ padding: '10px 12px' }}>Patient Ref</th>
                    <th style={{ padding: '10px 12px' }}>Date</th>
                    <th style={{ padding: '10px 12px', textAlign: 'center' }}>Predictions</th>
                    <th style={{ padding: '10px 12px', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {recentAssessments.map((asm) => (
                    <tr key={asm.assessment_id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontWeight: 700, color: '#0B1F3A' }}>
                        {asm.assessment_id.substring(0, 8).toUpperCase()}…
                      </td>
                      <td style={{ padding: '10px 12px', color: '#475569' }}>
                        {asm.patient_reference ? (
                          <span style={{ fontWeight: 600, color: '#1565D8' }}>{asm.patient_reference}</span>
                        ) : (
                          <span style={{ color: '#94A3B8', fontStyle: 'italic' }}>Anonymous</span>
                        )}
                      </td>
                      <td style={{ padding: '10px 12px', color: '#64748B', fontSize: '0.78rem' }}>
                        {formatDate(asm.created_at).split(',')[0]}
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                        <span style={{
                          background: asm.prediction_count > 0 ? '#EFF6FF' : '#F1F5F9',
                          color: asm.prediction_count > 0 ? '#1565D8' : '#64748B',
                          padding: '2px 8px',
                          borderRadius: '10px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                        }}>
                          {asm.prediction_count}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                        <button
                          type="button"
                          onClick={() => onNavigate('assessments')}
                          style={{
                            background: '#FFFFFF',
                            color: '#1565D8',
                            border: '1px solid #CBD5E1',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            fontSize: '0.76rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Panel B: Recent Predictions (Latest 5) */}
        <section className="dashboard-panel-card" style={{
          background: '#FFFFFF',
          borderRadius: '16px',
          border: '1px solid #DBEAFE',
          padding: '1.75rem',
          boxShadow: '0 2px 10px rgba(11, 31, 58, 0.04)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#0B1F3A', fontWeight: 800 }}>
                Recent Predictions
              </h3>
              <span style={{ fontSize: '0.78rem', color: '#64748B' }}>Latest 5 risk calculations by your account</span>
            </div>
            <button
              type="button"
              onClick={() => onNavigate('history')}
              style={{
                background: '#F5F3FF',
                color: '#7C3AED',
                border: '1px solid #DDD6FE',
                padding: '6px 12px',
                borderRadius: '8px',
                fontSize: '0.78rem',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              View History &rarr;
            </button>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#64748B' }}>Loading predictions…</div>
          ) : recentPredictions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 1.5rem', background: '#F8FAFC', borderRadius: '12px', border: '1px dashed #CBD5E1' }}>
              <div style={{ fontSize: '1.75rem', marginBottom: '8px' }}>⚡</div>
              <h4 style={{ margin: '0 0 6px', color: '#0B1F3A', fontSize: '0.95rem' }}>No Predictions Generated Yet</h4>
              <p style={{ margin: '0 0 14px', color: '#64748B', fontSize: '0.82rem', lineHeight: '1.5' }}>
                Execute a prediction on any patient profile using Logistic Regression or Deep Neural Network.
              </p>
              <button
                type="button"
                onClick={() => onNavigate('prediction')}
                style={{
                  background: '#7C3AED',
                  color: '#FFFFFF',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Run First Prediction
              </button>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="recent-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.84rem' }}>
                <thead>
                  <tr style={{ background: '#F8FAFC', borderBottom: '2px solid #E2E8F0', color: '#64748B' }}>
                    <th style={{ padding: '10px 10px' }}>Pred ID</th>
                    <th style={{ padding: '10px 10px' }}>Model</th>
                    <th style={{ padding: '10px 10px' }}>Outcome</th>
                    <th style={{ padding: '10px 10px' }}>Probability</th>
                    <th style={{ padding: '10px 10px', textAlign: 'right' }}>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {recentPredictions.map((pred) => {
                    const isPositive = pred.predicted_class === 1
                    return (
                      <tr key={pred.prediction_id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                        <td style={{ padding: '10px 10px', fontFamily: 'monospace', fontWeight: 600, color: '#475569', fontSize: '0.78rem' }}>
                          {pred.prediction_id?.substring(0, 10) || '—'}
                        </td>
                        <td style={{ padding: '10px 10px', fontWeight: 600, color: '#0B1F3A' }}>
                          {pred.model_name?.includes('Neural') || pred.model_name?.includes('ANN') ? (
                            <span style={{ color: '#7C3AED' }}>Deep ANN</span>
                          ) : (
                            <span style={{ color: '#1565D8' }}>Logistic Reg</span>
                          )}
                        </td>
                        <td style={{ padding: '10px 10px' }}>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '12px',
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            background: isPositive ? '#FEE2E2' : '#DCFCE7',
                            color: isPositive ? '#DC2626' : '#166534',
                          }}>
                            {isPositive ? 'Death Event (1)' : 'Survives (0)'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 10px', fontWeight: 700, color: isPositive ? '#DC2626' : '#1565D8' }}>
                          {(pred.predicted_probability * 100).toFixed(1)}%
                        </td>
                        <td style={{ padding: '10px 10px', textAlign: 'right', color: '#64748B', fontSize: '0.76rem' }}>
                          {formatDate(pred.created_at).split(',')[0]}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
