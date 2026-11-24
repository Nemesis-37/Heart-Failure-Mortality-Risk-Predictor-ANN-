import React, { useState, useEffect } from 'react'
import { MODEL_DATA } from './pages/ModelPerformancePage.jsx'
import ThemeToggle from './components/ThemeToggle.jsx'
import { apiUrl } from './apiConfig.js'
import './AdminDashboard.css'

const ADMIN_TOKEN_KEY = 'cardiopredict_admin_token'
const ADMIN_PROFILE_KEY = 'cardiopredict_admin_profile'

export default function AdminDashboard({ onExitAdmin }) {
  const [adminToken, setAdminToken] = useState(() => sessionStorage.getItem(ADMIN_TOKEN_KEY))
  const [adminProfile, setAdminProfile] = useState(() => {
    try {
      const p = sessionStorage.getItem(ADMIN_PROFILE_KEY)
      return p ? JSON.parse(p) : null
    } catch {
      return null
    }
  })

  // Mobile sidebar drawer state
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Navigation tab state: 'overview' | 'management' | 'verification' | 'activity' | 'performance'
  const [activeTab, setActiveTab] = useState('overview')

  // Overview stats & recent activity state
  const [overviewStats, setOverviewStats] = useState(null)
  const [recentActivity, setRecentActivity] = useState(null)
  const [overviewLoading, setOverviewLoading] = useState(false)

  // Doctor list & management state
  const [doctors, setDoctors] = useState([])
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [listError, setListError] = useState('')

  // Verification queue state
  const [verificationFilter, setVerificationFilter] = useState('PENDING')
  const [verificationSearch, setVerificationSearch] = useState('')

  // Doctor activity state
  const [activities, setActivities] = useState([])
  const [activitySearch, setActivitySearch] = useState('')
  const [activityLoading, setActivityLoading] = useState(false)

  // Modals state
  const [selectedDoctor, setSelectedDoctor] = useState(null)
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [documentModalOpen, setDocumentModalOpen] = useState(false)
  const [documentUrl, setDocumentUrl] = useState(null)
  const [documentLoading, setDocumentLoading] = useState(false)

  const [approveModalOpen, setApproveModalOpen] = useState(false)
  const [rejectModalOpen, setRejectModalOpen] = useState(false)
  const [rejectionReason, setRejectionReason] = useState('')

  // Confirmation modal for account status toggle (Suspend/Activate)
  const [suspendModalOpen, setSuspendModalOpen] = useState(false)
  const [doctorToToggle, setDoctorToToggle] = useState(null)

  const [actionInProgress, setActionInProgress] = useState(false)
  const [actionFeedback, setActionFeedback] = useState('')

  // Load data based on active tab
  useEffect(() => {
    if (adminToken) {
      if (activeTab === 'overview') {
        fetchOverview()
        fetchRecentActivity()
      } else if (activeTab === 'management') {
        fetchDoctors(statusFilter)
      } else if (activeTab === 'verification') {
        fetchDoctors(verificationFilter)
      } else if (activeTab === 'activity') {
        fetchActivity()
      }
    }
  }, [adminToken, activeTab, statusFilter, verificationFilter])

  const handleAdminLogout = () => {
    setAdminToken(null)
    setAdminProfile(null)
    sessionStorage.removeItem(ADMIN_TOKEN_KEY)
    sessionStorage.removeItem(ADMIN_PROFILE_KEY)
    if (onExitAdmin) onExitAdmin()
  }

  const fetchOverview = async () => {
    setOverviewLoading(true)
    try {
      const res = await fetch(apiUrl('/admin/overview'), {
        headers: { Authorization: `Bearer ${adminToken}` },
      })
      if (res.ok) {
        const data = await res.json()
        setOverviewStats(data)
      } else if (res.status === 401 || res.status === 403) {
        handleAdminLogout()
      }
    } catch (err) {
      console.warn('Admin overview fetch error:', err)
    } finally {
      setOverviewLoading(false)
    }
  }

  const fetchRecentActivity = async () => {
    try {
      const res = await fetch(apiUrl('/admin/dashboard/recent-activity'), {
        headers: { Authorization: `Bearer ${adminToken}` },
      })
      if (res.ok) {
        const data = await res.json()
        setRecentActivity(data)
      }
    } catch (err) {
      console.warn('Recent activity fetch error:', err)
    }
  }

  const fetchDoctors = async (status) => {
    setIsLoading(true)
    setListError('')
    try {
      const url = status && status !== 'ALL'
        ? apiUrl(`/admin/doctors?status_filter=${status}`)
        : apiUrl('/admin/doctors?status_filter=ALL')

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${adminToken}` },
      })

      if (res.status === 401 || res.status === 403) {
        handleAdminLogout()
        throw new Error('Administrator session expired. Please sign in again.')
      }

      let data
      try {
        data = await res.json()
      } catch (parseErr) {
        if (!res.ok) {
          throw new Error(`Server returned HTTP ${res.status}: ${res.statusText || 'Error'}`)
        }
        throw new Error('Invalid JSON response received from server.')
      }

      if (!res.ok) throw new Error(data.detail || `Failed to fetch doctor registrations (HTTP ${res.status}).`)
      setDoctors(Array.isArray(data) ? data : [])
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setListError(`Cannot connect to the backend API at ${apiUrl('/admin/doctors')}. Ensure the FastAPI server is running.`)
      } else {
        setListError(err.message)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const fetchActivity = async () => {
    setActivityLoading(true)
    try {
      const res = await fetch(apiUrl('/admin/doctor-activity'), {
        headers: { Authorization: `Bearer ${adminToken}` },
      })
      if (res.ok) {
        const data = await res.json()
        setActivities(data)
      } else if (res.status === 401 || res.status === 403) {
        handleAdminLogout()
      }
    } catch (err) {
      console.warn('Activity fetch error:', err)
    } finally {
      setActivityLoading(false)
    }
  }

  const promptToggleActive = (doctor) => {
    setDoctorToToggle(doctor)
    setSuspendModalOpen(true)
  }

  const confirmToggleActive = async () => {
    if (!doctorToToggle) return
    setActionInProgress(true)
    try {
      const res = await fetch(apiUrl(`/admin/doctors/${doctorToToggle.doctor_id}/toggle-active`), {
        method: 'POST',
        headers: { Authorization: `Bearer ${adminToken}` },
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to update account status.')

      setActionFeedback(data.message)
      setSuspendModalOpen(false)
      setDoctorToToggle(null)

      if (activeTab === 'management') {
        fetchDoctors(statusFilter)
      } else {
        fetchDoctors(verificationFilter)
      }
      fetchOverview()
    } catch (err) {
      setActionFeedback(`Error: ${err.message}`)
    } finally {
      setActionInProgress(false)
    }
  }

  const handleViewDocument = async (doctor) => {
    setSelectedDoctor(doctor)
    setDocumentModalOpen(true)
    setDocumentLoading(true)
    setDocumentUrl(null)

    try {
      const res = await fetch(apiUrl(`/admin/doctors/${doctor.doctor_id}/document`), {
        headers: { Authorization: `Bearer ${adminToken}` },
      })
      if (!res.ok) throw new Error('Failed to retrieve medical registration document.')
      const blob = await res.blob()
      setDocumentUrl(URL.createObjectURL(blob))
    } catch (err) {
      setActionFeedback(`Error loading document: ${err.message}`)
    } finally {
      setDocumentLoading(false)
    }
  }

  const handleApprove = async () => {
    if (!selectedDoctor) return
    setActionInProgress(true)
    try {
      const res = await fetch(apiUrl(`/admin/doctors/${selectedDoctor.doctor_id}/approve`), {
        method: 'POST',
        headers: { Authorization: `Bearer ${adminToken}` },
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Approval failed.')

      setApproveModalOpen(false)
      setActionFeedback(`Dr. ${selectedDoctor.full_name} has been APPROVED. Assigned username: ${data.username || 'dr_' + selectedDoctor.full_name.toLowerCase().replace(/\s+/g, '')}. Confirmation email dispatched.`)
      fetchDoctors(activeTab === 'verification' ? verificationFilter : statusFilter)
      fetchOverview()
    } catch (err) {
      setActionFeedback(`Error: ${err.message}`)
    } finally {
      setActionInProgress(false)
    }
  }

  const handleReject = async () => {
    if (!selectedDoctor || !rejectionReason.trim()) return
    setActionInProgress(true)
    try {
      const res = await fetch(apiUrl(`/admin/doctors/${selectedDoctor.doctor_id}/reject`), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${adminToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reason: rejectionReason.trim() }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Rejection failed.')

      setRejectModalOpen(false)
      setRejectionReason('')
      setActionFeedback(`Dr. ${selectedDoctor.full_name} has been REJECTED. Reason recorded & notification email sent.`)
      fetchDoctors(activeTab === 'verification' ? verificationFilter : statusFilter)
      fetchOverview()
    } catch (err) {
      setActionFeedback(`Error: ${err.message}`)
    } finally {
      setActionInProgress(false)
    }
  }

  const openDoctorDetails = (doc) => {
    setSelectedDoctor(doc)
    setDetailModalOpen(true)
  }

  // Navigation Items
  const navItems = [
    {
      id: 'overview',
      label: 'System Overview',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="9" />
          <rect x="14" y="3" width="7" height="5" />
          <rect x="14" y="12" width="7" height="9" />
          <rect x="3" y="16" width="7" height="5" />
        </svg>
      ),
    },
    {
      id: 'management',
      label: 'Physician Management',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      ),
    },
    {
      id: 'verification',
      label: 'Physician Verification',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M9 12l2 2 4-4" />
        </svg>
      ),
    },
    {
      id: 'activity',
      label: 'Doctor Activity',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      ),
    },
    {
      id: 'performance',
      label: 'Model Performance',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
      ),
    },
  ]

  // Filtered lists
  const filteredManagementDoctors = doctors.filter((doc) => {
    const q = searchQuery.toLowerCase().trim()
    if (!q) return true
    return (
      (doc.full_name || '').toLowerCase().includes(q) ||
      (doc.email || '').toLowerCase().includes(q) ||
      (doc.registration_number || '').toLowerCase().includes(q) ||
      (doc.username || '').toLowerCase().includes(q) ||
      (doc.doctor_id || '').toLowerCase().includes(q)
    )
  })

  const filteredVerificationDoctors = doctors.filter((doc) => {
    const q = verificationSearch.toLowerCase().trim()
    if (!q) return true
    return (
      (doc.full_name || '').toLowerCase().includes(q) ||
      (doc.email || '').toLowerCase().includes(q) ||
      (doc.registration_number || '').toLowerCase().includes(q) ||
      (doc.medical_degree || '').toLowerCase().includes(q) ||
      (doc.registration_council || '').toLowerCase().includes(q)
    )
  })

  const filteredActivities = activities.filter((act) => {
    const q = activitySearch.toLowerCase().trim()
    if (!q) return true
    return (
      (act.full_name || '').toLowerCase().includes(q) ||
      (act.email || '').toLowerCase().includes(q) ||
      (act.registration_number || '').toLowerCase().includes(q) ||
      (act.username || '').toLowerCase().includes(q)
    )
  })

  // Format date helper
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

  // Distribution calculations for Chart 1
  const totalDocs = overviewStats?.total_doctors || 0
  const approvedDocs = overviewStats?.approved_doctors || 0
  const pendingDocs = overviewStats?.pending_doctors || 0
  const rejectedDocs = overviewStats?.rejected_doctors || 0

  const approvedPct = totalDocs > 0 ? ((approvedDocs / totalDocs) * 100).toFixed(1) : '0'
  const pendingPct = totalDocs > 0 ? ((pendingDocs / totalDocs) * 100).toFixed(1) : '0'
  const rejectedPct = totalDocs > 0 ? ((rejectedDocs / totalDocs) * 100).toFixed(1) : '0'

  // 7-day throughput calculations for Chart 2
  const recent7Asms = recentActivity?.total_assessments_last_7_days || 0
  const recent7Preds = recentActivity?.total_predictions_last_7_days || 0
  const totalAsms = overviewStats?.total_assessments || 0
  const totalPreds = overviewStats?.total_predictions || 0

  return (
    <div className="admin-dashboard-root">
      {/* ──────────────────────────────────────────────────────────────────────────
          1. LEFT SIDEBAR NAVIGATION
      ────────────────────────────────────────────────────────────────────────── */}
      <aside className={`admin-sidebar ${sidebarOpen ? 'open' : ''}`}>
        {/* Brand Header */}
        <div className="admin-sidebar-header">
          <div className="admin-sidebar-logo" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <div className="admin-sidebar-brand">
            <div className="admin-sidebar-brand-name">CardioPredict</div>
            <div className="admin-sidebar-brand-sub">Admin Console</div>
          </div>
        </div>

        {/* Sidebar Nav Items */}
        <nav className="admin-sidebar-nav" aria-label="Admin Navigation">
          <div className="admin-sidebar-nav-label">Governance &amp; Controls</div>

          {navItems.map((item) => {
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                type="button"
                className={`admin-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => {
                  setActiveTab(item.id)
                  setSidebarOpen(false)
                }}
              >
                <span className="admin-nav-icon">{item.icon}</span>
                <span>{item.label}</span>
                {item.id === 'verification' && overviewStats?.pending_doctors > 0 && (
                  <span className="admin-nav-badge" title={`${overviewStats.pending_doctors} Pending Verifications`}>
                    {overviewStats.pending_doctors}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {/* Sidebar Footer with Logout */}
        <div className="admin-sidebar-footer">
          <div className="admin-profile-pill">
            <div className="admin-profile-avatar" aria-hidden="true">
              {adminProfile?.username ? adminProfile.username.substring(0, 2).toUpperCase() : 'AD'}
            </div>
            <div className="admin-profile-info">
              <div className="admin-profile-name" title={adminProfile?.full_name || 'Hospital Admin'}>
                {adminProfile?.full_name || 'Hospital Admin'}
              </div>
              <div className="admin-profile-role">
                {adminProfile?.role || 'Super Administrator'}
              </div>
            </div>
          </div>

          <button
            type="button"
            className="admin-btn-logout"
            onClick={handleAdminLogout}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* ──────────────────────────────────────────────────────────────────────────
          2. MAIN CONTENT AREA
      ────────────────────────────────────────────────────────────────────────── */}
      <div className="admin-main-wrap">
        {/* Top Header */}
        <header className="admin-header-bar">
          <div className="admin-header-left">
            <button
              type="button"
              className="admin-mobile-toggle-btn"
              onClick={() => setSidebarOpen((prev) => !prev)}
              aria-label="Toggle navigation drawer"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>

            <div className="admin-header-title-box">
              <h1>
                {activeTab === 'overview' && 'System Overview & Clinical Intelligence'}
                {activeTab === 'management' && 'Physician Management Directory'}
                {activeTab === 'verification' && 'Physician Credential Verification'}
                {activeTab === 'activity' && 'Doctor Clinical Activity Analytics'}
                {activeTab === 'performance' && 'Machine Learning Model Performance'}
              </h1>
              <p>
                Heart Failure Mortality Risk Predictor &bull; Central Clinical Administration
              </p>
            </div>
          </div>

          <div className="admin-header-right">
            <ThemeToggle />

            {/* Active Session Badge */}
            <div className="admin-session-badge" title="Active Admin Session">
              <span className="admin-status-dot" aria-hidden="true" />
              <span>Admin: <strong>{adminProfile?.username || 'admin'}</strong></span>
              <span style={{ color: 'var(--admin-text-subtle)' }}>&bull;</span>
              <span>DB: <strong>{overviewStats?.database_engine || 'PostgreSQL'}</strong></span>
            </div>

            {onExitAdmin && (
              <button
                type="button"
                className="admin-btn-portal-switch"
                onClick={onExitAdmin}
                title="Switch view to Doctor Clinical Workspace"
              >
                <span>&larr;</span>
                <span>Doctor Portal</span>
              </button>
            )}
          </div>
        </header>

        {/* Main Body Content */}
        <main className="admin-content-body">
          {/* Action Feedback Toast */}
          {actionFeedback && (
            <div className="admin-toast-banner" role="status">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1.15rem' }}>🔔</span>
                <span>{actionFeedback}</span>
              </div>
              <button
                type="button"
                onClick={() => setActionFeedback('')}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: '1.3rem', lineHeight: 1 }}
                aria-label="Dismiss message"
              >
                &times;
              </button>
            </div>
          )}

          {/* =========================================================================
              PHASE 4: SYSTEM OVERVIEW PAGE
          ========================================================================= */}
          {activeTab === 'overview' && (
            <div>
              {overviewLoading ? (
                <div style={{ textAlign: 'center', padding: '4.5rem', color: 'var(--admin-text-muted)' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⏳</div>
                  <div>Retrieving live clinical telemetry and registry statistics…</div>
                </div>
              ) : (
                <>
                  {/* Quick Action Shortcuts (Phase 4 Requirement) */}
                  <section className="admin-quick-actions-bar" aria-label="Administrative Quick Actions">
                    <div
                      className="admin-quick-action-card"
                      onClick={() => setActiveTab('management')}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter') setActiveTab('management') }}
                    >
                      <div className="admin-quick-action-icon" style={{ background: 'var(--admin-blue-light)', color: 'var(--admin-blue)' }}>
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                          <circle cx="9" cy="7" r="4" />
                        </svg>
                      </div>
                      <div>
                        <div className="admin-quick-action-title">
                          <span>Physician Directory</span>
                          <span style={{ fontSize: '0.8rem', color: 'var(--admin-blue)' }}>&rarr;</span>
                        </div>
                        <div className="admin-quick-action-desc">Inspect profiles &amp; access status</div>
                      </div>
                    </div>

                    <div
                      className="admin-quick-action-card"
                      onClick={() => setActiveTab('verification')}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter') setActiveTab('verification') }}
                    >
                      <div className="admin-quick-action-icon" style={{ background: 'var(--admin-amber-light)', color: 'var(--admin-amber)' }}>
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                      </div>
                      <div>
                        <div className="admin-quick-action-title">
                          <span>Verification Queue</span>
                          {pendingDocs > 0 && (
                            <span style={{ background: 'var(--admin-rose)', color: '#fff', fontSize: '0.68rem', padding: '1px 6px', borderRadius: '10px' }}>
                              {pendingDocs} New
                            </span>
                          )}
                          <span style={{ fontSize: '0.8rem', color: 'var(--admin-amber)' }}>&rarr;</span>
                        </div>
                        <div className="admin-quick-action-desc">Approve or reject doctor credentials</div>
                      </div>
                    </div>

                    <div
                      className="admin-quick-action-card"
                      onClick={() => setActiveTab('activity')}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter') setActiveTab('activity') }}
                    >
                      <div className="admin-quick-action-icon" style={{ background: 'var(--admin-cyan-light)', color: 'var(--admin-cyan)' }}>
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                        </svg>
                      </div>
                      <div>
                        <div className="admin-quick-action-title">
                          <span>Doctor Activity</span>
                          <span style={{ fontSize: '0.8rem', color: 'var(--admin-cyan)' }}>&rarr;</span>
                        </div>
                        <div className="admin-quick-action-desc">Login telemetry &amp; patient inferences</div>
                      </div>
                    </div>

                    <div
                      className="admin-quick-action-card"
                      onClick={() => setActiveTab('performance')}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter') setActiveTab('performance') }}
                    >
                      <div className="admin-quick-action-icon" style={{ background: 'var(--admin-violet-light)', color: 'var(--admin-violet)' }}>
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                        </svg>
                      </div>
                      <div>
                        <div className="admin-quick-action-title">
                          <span>Model Performance</span>
                          <span style={{ fontSize: '0.8rem', color: 'var(--admin-violet)' }}>&rarr;</span>
                        </div>
                        <div className="admin-quick-action-desc">LR vs ANN cross-validation metrics</div>
                      </div>
                    </div>
                  </section>

                  {/* 6 Core Statistics Cards (Phase 4 Requirement) */}
                  <section className="admin-stats-grid" aria-label="Clinical Registry Statistics">
                    {/* Card 1: Total Registered */}
                    <div className="admin-stat-card stat-blue">
                      <div className="admin-stat-top">
                        <span className="admin-stat-label">Total Registered</span>
                        <div className="admin-stat-icon-wrap" style={{ background: 'var(--admin-blue-light)', color: 'var(--admin-blue)' }}>
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                            <circle cx="9" cy="7" r="4" />
                          </svg>
                        </div>
                      </div>
                      <div className="admin-stat-val">{totalDocs}</div>
                      <div className="admin-stat-desc">Registered physician accounts</div>
                    </div>

                    {/* Card 2: Approved Doctors */}
                    <div className="admin-stat-card stat-emerald">
                      <div className="admin-stat-top">
                        <span className="admin-stat-label">Approved Doctors</span>
                        <div className="admin-stat-icon-wrap" style={{ background: 'var(--admin-emerald-light)', color: 'var(--admin-emerald)' }}>
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </div>
                      </div>
                      <div className="admin-stat-val" style={{ color: 'var(--admin-emerald)' }}>{approvedDocs}</div>
                      <div className="admin-stat-desc">Active verified clinicians</div>
                    </div>

                    {/* Card 3: Pending Review */}
                    <div className="admin-stat-card stat-amber">
                      <div className="admin-stat-top">
                        <span className="admin-stat-label">Pending Review</span>
                        <div className="admin-stat-icon-wrap" style={{ background: 'var(--admin-amber-light)', color: 'var(--admin-amber)' }}>
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <polyline points="12 6 12 12 16 14" />
                          </svg>
                        </div>
                      </div>
                      <div className="admin-stat-val" style={{ color: 'var(--admin-amber)' }}>{pendingDocs}</div>
                      <div className="admin-stat-desc">Awaiting council credential check</div>
                    </div>

                    {/* Card 4: Rejected Doctors */}
                    <div className="admin-stat-card stat-rose">
                      <div className="admin-stat-top">
                        <span className="admin-stat-label">Rejected Applications</span>
                        <div className="admin-stat-icon-wrap" style={{ background: 'var(--admin-rose-light)', color: 'var(--admin-rose)' }}>
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                          </svg>
                        </div>
                      </div>
                      <div className="admin-stat-val" style={{ color: 'var(--admin-rose)' }}>{rejectedDocs}</div>
                      <div className="admin-stat-desc">Unvalidated or denied credentials</div>
                    </div>

                    {/* Card 5: Total Assessments */}
                    <div className="admin-stat-card stat-cyan">
                      <div className="admin-stat-top">
                        <span className="admin-stat-label">Patient Assessments</span>
                        <div className="admin-stat-icon-wrap" style={{ background: 'var(--admin-cyan-light)', color: 'var(--admin-cyan)' }}>
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                            <line x1="16" y1="13" x2="8" y2="13" />
                            <line x1="16" y1="17" x2="8" y2="17" />
                          </svg>
                        </div>
                      </div>
                      <div className="admin-stat-val" style={{ color: 'var(--admin-cyan)' }}>{totalAsms}</div>
                      <div className="admin-stat-desc">Recorded biomarker profiles</div>
                    </div>

                    {/* Card 6: Total Predictions */}
                    <div className="admin-stat-card stat-violet">
                      <div className="admin-stat-top">
                        <span className="admin-stat-label">Model Predictions</span>
                        <div className="admin-stat-icon-wrap" style={{ background: 'var(--admin-violet-light)', color: 'var(--admin-violet)' }}>
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                          </svg>
                        </div>
                      </div>
                      <div className="admin-stat-val" style={{ color: 'var(--admin-violet)' }}>{totalPreds}</div>
                      <div className="admin-stat-desc">Dual LR &amp; ANN inferences</div>
                    </div>
                  </section>

                  {/* Charts & Analytics Section (Phase 4 Requirement) */}
                  <section className="admin-charts-grid" aria-label="Visual Analytics and Telemetry">
                    {/* Chart 1: Physician Credential Breakdown */}
                    <div className="admin-chart-card">
                      <div className="admin-chart-header">
                        <div>
                          <h2 className="admin-chart-title">Physician Verification Distribution</h2>
                          <div className="admin-chart-subtitle">Registry breakdown by validation standing</div>
                        </div>
                        <span style={{ fontSize: '0.74rem', color: 'var(--admin-text-subtle)', fontWeight: 700 }}>
                          {totalDocs} Total
                        </span>
                      </div>

                      {totalDocs > 0 ? (
                        <>
                          <div className="admin-progress-segmented" role="progressbar" aria-label="Physician status distribution">
                            <div
                              className="admin-progress-segment"
                              style={{ width: `${approvedPct}%`, background: 'var(--admin-emerald)' }}
                              title={`Approved: ${approvedDocs} (${approvedPct}%)`}
                            />
                            <div
                              className="admin-progress-segment"
                              style={{ width: `${pendingPct}%`, background: 'var(--admin-amber)' }}
                              title={`Pending: ${pendingDocs} (${pendingPct}%)`}
                            />
                            <div
                              className="admin-progress-segment"
                              style={{ width: `${rejectedPct}%`, background: 'var(--admin-rose)' }}
                              title={`Rejected: ${rejectedDocs} (${rejectedPct}%)`}
                            />
                          </div>

                          <div className="admin-chart-legend-grid">
                            <div className="admin-chart-legend-item">
                              <div className="admin-legend-dot-label">
                                <span className="admin-legend-dot" style={{ background: 'var(--admin-emerald)' }} />
                                <span>Approved</span>
                              </div>
                              <div className="admin-legend-count" style={{ color: 'var(--admin-emerald)' }}>{approvedDocs}</div>
                              <div className="admin-legend-pct">{approvedPct}% of registry</div>
                            </div>

                            <div className="admin-chart-legend-item">
                              <div className="admin-legend-dot-label">
                                <span className="admin-legend-dot" style={{ background: 'var(--admin-amber)' }} />
                                <span>Pending</span>
                              </div>
                              <div className="admin-legend-count" style={{ color: 'var(--admin-amber)' }}>{pendingDocs}</div>
                              <div className="admin-legend-pct">{pendingPct}% of registry</div>
                            </div>

                            <div className="admin-chart-legend-item">
                              <div className="admin-legend-dot-label">
                                <span className="admin-legend-dot" style={{ background: 'var(--admin-rose)' }} />
                                <span>Rejected</span>
                              </div>
                              <div className="admin-legend-count" style={{ color: 'var(--admin-rose)' }}>{rejectedDocs}</div>
                              <div className="admin-legend-pct">{rejectedPct}% of registry</div>
                            </div>
                          </div>
                        </>
                      ) : (
                        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--admin-text-subtle)' }}>
                          No physician records registered yet.
                        </div>
                      )}
                    </div>

                    {/* Chart 2: 7-Day Clinical Throughput */}
                    <div className="admin-chart-card">
                      <div className="admin-chart-header">
                        <div>
                          <h2 className="admin-chart-title">7-Day Clinical Activity Throughput</h2>
                          <div className="admin-chart-subtitle">Real-time assessments and prediction evaluations logged this week</div>
                        </div>
                        <span style={{ fontSize: '0.74rem', color: 'var(--admin-cyan)', fontWeight: 700 }}>
                          Past 7 Days
                        </span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginTop: '0.5rem', marginBottom: '1.25rem' }}>
                        <div style={{ background: 'var(--admin-cyan-light)', border: '1px solid var(--admin-cyan-border)', borderRadius: '12px', padding: '14px' }}>
                          <div style={{ fontSize: '0.72rem', color: 'var(--admin-cyan)', fontWeight: 800, textTransform: 'uppercase' }}>
                            Recent Assessments
                          </div>
                          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--admin-cyan)', marginTop: '4px' }}>
                            {recent7Asms}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-subtle)', marginTop: '2px' }}>
                            {totalAsms > 0 ? `${((recent7Asms / totalAsms) * 100).toFixed(0)}% of all assessments` : '0%'}
                          </div>
                        </div>

                        <div style={{ background: 'var(--admin-violet-light)', border: '1px solid var(--admin-violet-border)', borderRadius: '12px', padding: '14px' }}>
                          <div style={{ fontSize: '0.72rem', color: 'var(--admin-violet)', fontWeight: 800, textTransform: 'uppercase' }}>
                            Recent Predictions
                          </div>
                          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--admin-violet)', marginTop: '4px' }}>
                            {recent7Preds}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-subtle)', marginTop: '2px' }}>
                            {totalPreds > 0 ? `${((recent7Preds / totalPreds) * 100).toFixed(0)}% of all predictions` : '0%'}
                          </div>
                        </div>
                      </div>

                      <div style={{ fontSize: '0.76rem', color: 'var(--admin-text-muted)', lineHeight: '1.5', background: 'rgba(255,255,255,0.02)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--admin-border-subtle)' }}>
                        ℹ Telemetry updates continuously as physicians run assessments and inferences in the clinical portal.
                      </div>
                    </div>
                  </section>

                  {/* Recent Activity Split Grid (Phase 4 Requirement) */}
                  <section className="admin-activity-split-grid" aria-label="Recent Administrative Activity">
                    {/* Left Panel: Recent Doctor Registrations */}
                    <div className="admin-panel-card">
                      <div className="admin-panel-header">
                        <div className="admin-panel-title-group">
                          <h3>Recent Physician Registrations</h3>
                          <span>Latest 5 applicants recorded in registry</span>
                        </div>
                        <button
                          type="button"
                          className="admin-btn-panel-action"
                          onClick={() => setActiveTab('management')}
                        >
                          View All &rarr;
                        </button>
                      </div>

                      {recentActivity?.recent_registrations?.length > 0 ? (
                        <div className="admin-table-responsive">
                          <table className="admin-data-table">
                            <thead>
                              <tr>
                                <th>Physician</th>
                                <th>Email</th>
                                <th>Date</th>
                                <th>Status</th>
                                <th style={{ textAlign: 'right' }}>Action</th>
                              </tr>
                            </thead>
                            <tbody>
                              {recentActivity.recent_registrations.map((doc) => (
                                <tr key={doc.doctor_id}>
                                  <td style={{ fontWeight: 700 }}>{doc.full_name}</td>
                                  <td style={{ color: 'var(--admin-text-muted)', fontSize: '0.78rem' }}>{doc.email}</td>
                                  <td style={{ color: 'var(--admin-text-subtle)', fontSize: '0.76rem' }}>
                                    {formatDate(doc.created_at).split(',')[0]}
                                  </td>
                                  <td>
                                    <span className={`admin-status-pill ${doc.verification_status?.toLowerCase()}`}>
                                      {doc.verification_status}
                                    </span>
                                  </td>
                                  <td style={{ textAlign: 'right' }}>
                                    <button
                                      type="button"
                                      className="admin-btn-secondary"
                                      style={{ padding: '4px 8px', fontSize: '0.72rem' }}
                                      onClick={() => openDoctorDetails(doc)}
                                    >
                                      Inspect
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--admin-text-subtle)', fontSize: '0.84rem' }}>
                          No recent doctor registrations recorded.
                        </div>
                      )}
                    </div>

                    {/* Right Panel: Recent Clinician Logins & Decisions */}
                    <div className="admin-panel-card">
                      <div className="admin-panel-header">
                        <div className="admin-panel-title-group">
                          <h3>Recent Activity Telemetry</h3>
                          <span>Active sessions &amp; latest verification decisions</span>
                        </div>
                        <button
                          type="button"
                          className="admin-btn-panel-action"
                          onClick={() => setActiveTab('activity')}
                        >
                          All Activity &rarr;
                        </button>
                      </div>

                      {/* Recently Active Clinicians */}
                      <div style={{ marginBottom: '1.25rem' }}>
                        <div style={{ fontSize: '0.74rem', fontWeight: 800, color: 'var(--admin-text-subtle)', textTransform: 'uppercase', marginBottom: '8px' }}>
                          Recently Active Physicians
                        </div>
                        {recentActivity?.recently_logged_in?.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {recentActivity.recently_logged_in.slice(0, 3).map((act) => (
                              <div
                                key={act.doctor_id}
                                style={{
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  padding: '8px 12px',
                                  background: 'rgba(255,255,255,0.02)',
                                  borderRadius: '8px',
                                  border: '1px solid var(--admin-border-subtle)',
                                  fontSize: '0.82rem',
                                }}
                              >
                                <div>
                                  <strong style={{ color: 'var(--admin-text-main)' }}>{act.full_name}</strong>
                                  <span style={{ fontSize: '0.74rem', color: 'var(--admin-text-muted)', marginLeft: '6px' }}>
                                    ({act.username || 'dr_physician'})
                                  </span>
                                </div>
                                <div style={{ fontSize: '0.74rem', color: 'var(--admin-blue)', fontWeight: 600 }}>
                                  {act.last_login ? formatDate(act.last_login) : 'Active session'}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div style={{ fontSize: '0.8rem', color: 'var(--admin-text-subtle)' }}>No recent logins logged.</div>
                        )}
                      </div>

                      {/* Latest Verification Decisions */}
                      <div>
                        <div style={{ fontSize: '0.74rem', fontWeight: 800, color: 'var(--admin-text-subtle)', textTransform: 'uppercase', marginBottom: '8px' }}>
                          Latest Verification Decisions
                        </div>
                        {recentActivity?.recent_verifications?.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {recentActivity.recent_verifications.slice(0, 2).map((v) => (
                              <div
                                key={v.doctor_id}
                                style={{
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  padding: '8px 12px',
                                  background: 'rgba(255,255,255,0.02)',
                                  borderRadius: '8px',
                                  border: '1px solid var(--admin-border-subtle)',
                                  fontSize: '0.82rem',
                                }}
                              >
                                <div>
                                  <strong style={{ color: 'var(--admin-text-main)' }}>{v.full_name}</strong>
                                  <span style={{ fontSize: '0.74rem', color: 'var(--admin-text-muted)', marginLeft: '6px' }}>
                                    {v.registration_council}
                                  </span>
                                </div>
                                <span className={`admin-status-pill ${v.verification_status?.toLowerCase()}`}>
                                  {v.verification_status}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div style={{ fontSize: '0.8rem', color: 'var(--admin-text-subtle)' }}>No verifications completed recently.</div>
                        )}
                      </div>
                    </div>
                  </section>
                </>
              )}
            </div>
          )}

          {/* =========================================================================
              PHASE 5 — PAGE 1: PHYSICIAN MANAGEMENT
          ========================================================================= */}
          {activeTab === 'management' && (
            <div className="admin-panel-card">
              {/* Header and Controls */}
              <div className="admin-table-controls-row">
                <div>
                  <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--admin-text-main)', fontWeight: 800 }}>
                    Physician Management Directory
                  </h2>
                  <p style={{ margin: '4px 0 0', color: 'var(--admin-text-muted)', fontSize: '0.82rem' }}>
                    Real-time registry from PostgreSQL. Inspect credential profiles, review assessment counts, and manage access.
                  </p>
                </div>

                {/* Filter and Search */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  <div className="admin-filter-pill-group" role="tablist" aria-label="Status Filters">
                    {['ALL', 'APPROVED', 'PENDING', 'REJECTED'].map((filter) => (
                      <button
                        key={filter}
                        type="button"
                        className={`admin-filter-pill-btn ${statusFilter === filter ? 'active' : ''}`}
                        onClick={() => setStatusFilter(filter)}
                      >
                        {filter}
                      </button>
                    ))}
                  </div>

                  <div className="admin-search-input-wrap">
                    <span className="admin-search-icon" aria-hidden="true">
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                      </svg>
                    </span>
                    <input
                      type="text"
                      placeholder="Search name, email, reg no., username…"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Table */}
              {isLoading ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--admin-text-muted)' }}>
                  Loading physician directory…
                </div>
              ) : listError ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--admin-rose)' }}>
                  {listError}
                </div>
              ) : filteredManagementDoctors.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--admin-text-subtle)' }}>
                  No doctors found matching the filter criteria.
                </div>
              ) : (
                <div className="admin-table-responsive">
                  <table className="admin-data-table">
                    <thead>
                      <tr>
                        <th>Doctor ID</th>
                        <th>Physician Name</th>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Medical Degree</th>
                        <th>Reg Number</th>
                        <th>Reg Council</th>
                        <th>Reg Date</th>
                        <th>Status</th>
                        <th>Last Login</th>
                        <th style={{ textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredManagementDoctors.map((doc) => {
                        return (
                          <tr key={doc.doctor_id}>
                            <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--admin-text-subtle)' }}>
                              {doc.doctor_id.substring(0, 8)}…
                            </td>
                            <td style={{ fontWeight: 700 }}>{doc.full_name}</td>
                            <td>
                              {doc.username ? (
                                <code style={{ background: 'var(--admin-blue-light)', color: 'var(--admin-blue)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.78rem' }}>
                                  {doc.username}
                                </code>
                              ) : (
                                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.78rem', fontStyle: 'italic' }}>Pending</span>
                              )}
                            </td>
                            <td style={{ color: 'var(--admin-text-muted)' }}>{doc.email}</td>
                            <td>{doc.medical_degree}</td>
                            <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{doc.registration_number}</td>
                            <td style={{ color: 'var(--admin-text-muted)', fontSize: '0.78rem' }}>{doc.registration_council}</td>
                            <td style={{ color: 'var(--admin-text-subtle)', fontSize: '0.76rem' }}>
                              {formatDate(doc.created_at).split(',')[0]}
                            </td>
                            <td>
                              <span className={`admin-status-pill ${doc.verification_status?.toLowerCase()}`}>
                                {doc.verification_status}
                              </span>
                            </td>
                            <td style={{ fontSize: '0.78rem', color: doc.last_login ? 'var(--admin-text-main)' : 'var(--admin-text-subtle)' }}>
                              {doc.last_login ? formatDate(doc.last_login) : 'Never'}
                            </td>
                            <td style={{ textAlign: 'right' }}>
                              <div style={{ display: 'inline-flex', gap: '6px' }}>
                                <button
                                  type="button"
                                  className="admin-btn-secondary"
                                  style={{ padding: '4px 10px', fontSize: '0.74rem' }}
                                  onClick={() => openDoctorDetails(doc)}
                                >
                                  View
                                </button>
                                <button
                                  type="button"
                                  style={{
                                    padding: '4px 10px',
                                    borderRadius: '6px',
                                    fontSize: '0.74rem',
                                    fontWeight: 700,
                                    border: '1px solid',
                                    cursor: 'pointer',
                                    borderColor: doc.is_active ? 'var(--admin-rose-border)' : 'var(--admin-emerald-border)',
                                    background: doc.is_active ? 'var(--admin-rose-light)' : 'var(--admin-emerald-light)',
                                    color: doc.is_active ? 'var(--admin-rose)' : 'var(--admin-emerald)',
                                  }}
                                  onClick={() => promptToggleActive(doc)}
                                  disabled={actionInProgress}
                                >
                                  {doc.is_active ? 'Suspend' : 'Activate'}
                                </button>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* =========================================================================
              PHASE 5 — PAGE 2: PHYSICIAN VERIFICATION QUEUE
          ========================================================================= */}
          {activeTab === 'verification' && (
            <div className="admin-panel-card">
              {/* Header and Filter */}
              <div className="admin-table-controls-row">
                <div>
                  <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--admin-text-main)', fontWeight: 800 }}>
                    Medical Credential Verification Queue
                  </h2>
                  <p style={{ margin: '4px 0 0', color: 'var(--admin-text-muted)', fontSize: '0.82rem' }}>
                    Inspect applicant credentials, verify medical certificates, and grant authorized clinical portal access.
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  <div className="admin-filter-pill-group">
                    {['PENDING', 'APPROVED', 'REJECTED', 'ALL'].map((f) => (
                      <button
                        key={f}
                        type="button"
                        className={`admin-filter-pill-btn ${verificationFilter === f ? 'active' : ''}`}
                        onClick={() => setVerificationFilter(f)}
                      >
                        {f}
                      </button>
                    ))}
                  </div>

                  <div className="admin-search-input-wrap">
                    <span className="admin-search-icon" aria-hidden="true">
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                      </svg>
                    </span>
                    <input
                      type="text"
                      placeholder="Search applicant name, reg no.…"
                      value={verificationSearch}
                      onChange={(e) => setVerificationSearch(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Application Cards */}
              {isLoading ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--admin-text-muted)' }}>
                  Loading credential verification queue…
                </div>
              ) : filteredVerificationDoctors.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--admin-text-subtle)' }}>
                  No applications found in the <strong>{verificationFilter}</strong> queue.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {filteredVerificationDoctors.map((doc) => (
                    <div
                      key={doc.doctor_id}
                      style={{
                        border: '1px solid var(--admin-border-subtle)',
                        borderRadius: '14px',
                        padding: '1.5rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: '1.25rem',
                        background: 'var(--admin-bg-card)',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                      }}
                    >
                      <div style={{ maxWidth: '680px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
                          <h3 style={{ margin: 0, fontSize: '1.15rem', color: 'var(--admin-text-main)', fontWeight: 800 }}>
                            {doc.full_name}
                          </h3>
                          <span className={`admin-status-pill ${doc.email_verified ? 'approved' : 'pending'}`}>
                            {doc.email_verified ? '✓ Email Verified' : '⚠ Email Unverified'}
                          </span>
                          <span className={`admin-status-pill ${doc.verification_status?.toLowerCase()}`}>
                            Status: {doc.verification_status}
                          </span>
                        </div>

                        {/* Detailed Fields Grid */}
                        <div style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                          gap: '10px',
                          fontSize: '0.84rem',
                          color: 'var(--admin-text-muted)',
                          marginTop: '10px',
                        }}>
                          <div><strong>Degree:</strong> {doc.medical_degree}</div>
                          <div><strong>Council:</strong> {doc.registration_council}</div>
                          <div><strong>Registration No:</strong> <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--admin-text-main)' }}>{doc.registration_number}</span></div>
                          <div><strong>Email:</strong> {doc.email}</div>
                          <div><strong>Mobile:</strong> {doc.mobile || '—'}</div>
                          <div><strong>Applied On:</strong> {formatDate(doc.created_at)}</div>
                          {doc.username && (
                            <div><strong>Username:</strong> <code style={{ color: 'var(--admin-blue)' }}>{doc.username}</code></div>
                          )}
                        </div>

                        {/* Rejection notice if present */}
                        {doc.rejection_reason && (
                          <div style={{
                            marginTop: '12px',
                            padding: '8px 12px',
                            borderRadius: '8px',
                            background: 'var(--admin-rose-light)',
                            border: '1px solid var(--admin-rose-border)',
                            color: 'var(--admin-rose)',
                            fontSize: '0.82rem',
                          }}>
                            <strong>Rejection Reason:</strong> {doc.rejection_reason}
                          </div>
                        )}
                      </div>

                      {/* Action Buttons */}
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                        {doc.has_document && (
                          <button
                            type="button"
                            className="admin-btn-secondary"
                            onClick={() => handleViewDocument(doc)}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                          >
                            <span>📄</span>
                            <span>View Certificate</span>
                          </button>
                        )}

                        {doc.verification_status === 'PENDING' && (
                          <>
                            <button
                              type="button"
                              className="admin-btn-approve"
                              onClick={() => { setSelectedDoctor(doc); setApproveModalOpen(true); }}
                            >
                              ✓ Approve
                            </button>
                            <button
                              type="button"
                              className="admin-btn-reject"
                              onClick={() => { setSelectedDoctor(doc); setRejectModalOpen(true); }}
                            >
                              ✕ Reject
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* =========================================================================
              PHASE 5 — PAGE 3: DOCTOR CLINICAL ACTIVITY
          ========================================================================= */}
          {activeTab === 'activity' && (
            <div className="admin-panel-card">
              <div className="admin-table-controls-row">
                <div>
                  <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--admin-text-main)', fontWeight: 800 }}>
                    Doctor Clinical Activity Analytics
                  </h2>
                  <p style={{ margin: '4px 0 0', color: 'var(--admin-text-muted)', fontSize: '0.82rem' }}>
                    Real session activity and patient evaluation volumes recorded per registered clinician.
                  </p>
                </div>

                <div className="admin-search-input-wrap">
                  <span className="admin-search-icon" aria-hidden="true">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                  </span>
                  <input
                    type="text"
                    placeholder="Search doctor name, username, email…"
                    value={activitySearch}
                    onChange={(e) => setActivitySearch(e.target.value)}
                  />
                </div>
              </div>

              {activityLoading ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--admin-text-muted)' }}>
                  Loading clinical activity logs…
                </div>
              ) : filteredActivities.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--admin-text-subtle)' }}>
                  No clinician activity records found.
                </div>
              ) : (
                <div className="admin-table-responsive">
                  <table className="admin-data-table">
                    <thead>
                      <tr>
                        <th>Physician</th>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Last Login Timestamp</th>
                        <th style={{ textAlign: 'center' }}>Total Assessments</th>
                        <th style={{ textAlign: 'center' }}>Total Predictions</th>
                        <th style={{ textAlign: 'right' }}>Account Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredActivities.map((act) => (
                        <tr key={act.doctor_id}>
                          <td>
                            <div style={{ fontWeight: 700 }}>{act.full_name}</div>
                            <div style={{ fontSize: '0.74rem', color: 'var(--admin-text-subtle)' }}>
                              {act.medical_degree} &bull; {act.registration_number}
                            </div>
                          </td>
                          <td>
                            {act.username ? (
                              <code style={{ background: 'var(--admin-blue-light)', color: 'var(--admin-blue)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.78rem' }}>
                                {act.username}
                              </code>
                            ) : (
                              <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.78rem' }}>—</span>
                            )}
                          </td>
                          <td style={{ color: 'var(--admin-text-muted)' }}>{act.email}</td>
                          <td style={{ color: act.last_login ? 'var(--admin-text-main)' : 'var(--admin-text-subtle)' }}>
                            {act.last_login ? formatDate(act.last_login) : 'Never logged in'}
                          </td>
                          <td style={{ textAlign: 'center', fontWeight: 800, color: 'var(--admin-cyan)', fontSize: '1.05rem' }}>
                            {act.total_assessments}
                          </td>
                          <td style={{ textAlign: 'center', fontWeight: 800, color: 'var(--admin-violet)', fontSize: '1.05rem' }}>
                            {act.total_predictions}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <span className={`admin-status-pill ${act.is_active ? 'approved' : 'rejected'}`}>
                              {act.is_active ? 'Active' : 'Suspended'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* =========================================================================
              PHASE 5 — PAGE 4: MODEL PERFORMANCE BENCHMARKS
          ========================================================================= */}
          {activeTab === 'performance' && (
            <div className="admin-panel-card">
              <div style={{ marginBottom: '1.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px', flexWrap: 'wrap' }}>
                  <h2 style={{ margin: 0, fontSize: '1.35rem', color: 'var(--admin-text-main)', fontWeight: 800 }}>
                    Predictive Model Benchmark Validation
                  </h2>
                  <span style={{ background: 'var(--admin-blue-light)', color: 'var(--admin-blue)', border: '1px solid var(--admin-blue-border)', padding: '2px 8px', borderRadius: '12px', fontSize: '0.72rem', fontWeight: 700 }}>
                    5-Fold Stratified Cross-Validation (299 Patients)
                  </span>
                </div>
                <p style={{ margin: 0, color: 'var(--admin-text-muted)', fontSize: '0.86rem' }}>
                  Rigorous statistical comparison between the classical Logistic Regression baseline and the deep Artificial Neural Network.
                </p>
              </div>

              {/* Side-by-Side Model Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                {/* Logistic Regression Card */}
                <div style={{
                  border: '2px solid var(--admin-blue-border)',
                  borderRadius: '14px',
                  padding: '1.5rem',
                  background: 'var(--admin-bg-card)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ background: 'var(--admin-blue-light)', color: 'var(--admin-blue)', padding: '4px 10px', borderRadius: '12px', fontSize: '0.74rem', fontWeight: 700 }}>
                      Baseline Linear Model
                    </span>
                    <span style={{ fontSize: '0.76rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>Scikit-Learn Pipeline</span>
                  </div>
                  <h3 style={{ margin: '12px 0 4px', fontSize: '1.25rem', color: 'var(--admin-text-main)', fontWeight: 800 }}>
                    Logistic Regression
                  </h3>
                  <p style={{ margin: '0 0 16px', fontSize: '0.8rem', color: 'var(--admin-text-muted)' }}>
                    StandardScaler &bull; L2 Ridge Regularization (C=1.0) &bull; Threshold 0.50
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>Accuracy</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--admin-blue)' }}>75.60%</div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--admin-text-subtle)' }}>± 6.87% CV std</div>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>ROC-AUC</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--admin-blue)' }}>77.17%</div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--admin-text-subtle)' }}>± 5.51% CV std</div>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>Precision</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--admin-text-main)' }}>67.55%</div>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>Sensitivity (Recall)</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--admin-text-main)' }}>48.11%</div>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>Specificity</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--admin-text-main)' }}>88.67%</div>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>F1-Score</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--admin-text-main)' }}>55.76%</div>
                    </div>
                  </div>
                </div>

                {/* Artificial Neural Network Card */}
                <div style={{
                  border: '2px solid var(--admin-violet-border)',
                  borderRadius: '14px',
                  padding: '1.5rem',
                  background: 'var(--admin-bg-card)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ background: 'var(--admin-violet-light)', color: 'var(--admin-violet)', padding: '4px 10px', borderRadius: '12px', fontSize: '0.74rem', fontWeight: 700 }}>
                      Deep Learning Architecture
                    </span>
                    <span style={{ fontSize: '0.76rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>PyTorch (32-16)</span>
                  </div>
                  <h3 style={{ margin: '12px 0 4px', fontSize: '1.25rem', color: 'var(--admin-text-main)', fontWeight: 800 }}>
                    Artificial Neural Network
                  </h3>
                  <p style={{ margin: '0 0 16px', fontSize: '0.8rem', color: 'var(--admin-text-muted)' }}>
                    11 Inputs &bull; Dense 32 &bull; ReLU &bull; Dense 16 &bull; Sigmoid Output &bull; Dropout 0.2
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>Accuracy</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--admin-violet)' }}>74.60%</div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--admin-text-subtle)' }}>± 9.56% CV std</div>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>ROC-AUC</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--admin-violet)' }}>75.68%</div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--admin-text-subtle)' }}>± 6.53% CV std</div>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>Precision</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--admin-text-main)' }}>63.51%</div>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>Sensitivity (Recall)</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--admin-text-main)' }}>47.11%</div>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>Specificity</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--admin-text-main)' }}>87.67%</div>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid var(--admin-border-subtle)' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--admin-text-muted)', fontWeight: 600 }}>F1-Score</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--admin-text-main)' }}>53.97%</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Visual Metric Comparison Bars */}
              <div style={{
                background: 'var(--admin-bg-card)',
                borderRadius: '14px',
                border: '1px solid var(--admin-border-subtle)',
                padding: '1.5rem',
              }}>
                <h4 style={{ margin: '0 0 1.25rem', fontSize: '1.05rem', color: 'var(--admin-text-main)', fontWeight: 700 }}>
                  Side-by-Side Metric Comparison (LR vs ANN)
                </h4>

                {[
                  { name: 'Accuracy', lr: 75.60, ann: 74.60, desc: 'Overall percentage of correct mortality/survival classifications' },
                  { name: 'ROC-AUC', lr: 77.17, ann: 75.68, desc: 'Discriminative capacity across all potential classification thresholds' },
                  { name: 'Precision', lr: 67.55, ann: 63.51, desc: 'Probability that a high-risk prediction represents true mortality event' },
                  { name: 'Sensitivity', lr: 48.11, ann: 47.11, desc: 'True positive rate: detecting patients who actually experience mortality' },
                  { name: 'Specificity', lr: 88.67, ann: 87.67, desc: 'True negative rate: correctly identifying surviving patients' },
                  { name: 'F1 Score', lr: 55.76, ann: 53.97, desc: 'Harmonic mean of precision and recall under class imbalance' },
                ].map((m) => (
                  <div key={m.name} style={{ marginBottom: '1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '0.84rem' }}>
                      <span style={{ fontWeight: 700, color: 'var(--admin-text-main)' }}>{m.name}</span>
                      <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.76rem' }}>{m.desc}</span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {/* LR Bar */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ width: '38px', fontSize: '0.72rem', fontWeight: 700, color: 'var(--admin-blue)' }}>LR</span>
                        <div style={{ flex: 1, height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{ width: `${m.lr}%`, height: '100%', background: 'var(--admin-blue)', borderRadius: '4px' }} />
                        </div>
                        <span style={{ width: '48px', textAlign: 'right', fontSize: '0.76rem', fontWeight: 700, color: 'var(--admin-blue)' }}>{m.lr}%</span>
                      </div>

                      {/* ANN Bar */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ width: '38px', fontSize: '0.72rem', fontWeight: 700, color: 'var(--admin-violet)' }}>ANN</span>
                        <div style={{ flex: 1, height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{ width: `${m.ann}%`, height: '100%', background: 'var(--admin-violet)', borderRadius: '4px' }} />
                        </div>
                        <span style={{ width: '48px', textAlign: 'right', fontSize: '0.76rem', fontWeight: 700, color: 'var(--admin-violet)' }}>{m.ann}%</span>
                      </div>
                    </div>
                  </div>
                ))}

                <div style={{ marginTop: '1.25rem', padding: '10px 14px', borderRadius: '8px', background: 'var(--admin-blue-light)', border: '1px solid var(--admin-blue-border)', fontSize: '0.76rem', color: 'var(--admin-blue)' }}>
                  💡 Cross-validation metrics are measured across 5 random validation splits and serve to quantify baseline ML performance. Real-time patient predictions compute risk independently using standardized input weights.
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────────
          MODAL 1: DOCTOR FULL PROFILE DETAIL MODAL
      ────────────────────────────────────────────────────────────────────────── */}
      {detailModalOpen && selectedDoctor && (
        <div className="admin-modal-overlay" onClick={() => setDetailModalOpen(false)}>
          <div className="admin-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="detail-modal-title">
            <div className="admin-modal-header">
              <div>
                <h3 id="detail-modal-title">Physician Profile &amp; Credentials</h3>
                <span>Doctor ID: <code>{selectedDoctor.doctor_id}</code></span>
              </div>
              <button
                type="button"
                className="admin-modal-close-btn"
                onClick={() => setDetailModalOpen(false)}
                aria-label="Close modal"
              >
                &times;
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '0.86rem', color: 'var(--admin-text-main)' }}>
              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Full Name</span>
                <strong>{selectedDoctor.full_name}</strong>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>System Username</span>
                <code>{selectedDoctor.username || 'Not assigned yet'}</code>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Email Address</span>
                <span>{selectedDoctor.email}</span>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Mobile Number</span>
                <span>{selectedDoctor.mobile || '—'}</span>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Medical Degree</span>
                <span>{selectedDoctor.medical_degree}</span>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Registration Number</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{selectedDoctor.registration_number}</span>
              </div>

              <div style={{ gridColumn: 'span 2' }}>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Medical Council</span>
                <span>{selectedDoctor.registration_council}</span>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Email Verification</span>
                <span style={{ color: selectedDoctor.email_verified ? 'var(--admin-emerald)' : 'var(--admin-amber)', fontWeight: 700 }}>
                  {selectedDoctor.email_verified ? '✓ Verified' : '⚠ Unverified'}
                </span>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Verification Status</span>
                <span className={`admin-status-pill ${selectedDoctor.verification_status?.toLowerCase()}`}>
                  {selectedDoctor.verification_status}
                </span>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Account Access</span>
                <span style={{ color: selectedDoctor.is_active ? 'var(--admin-emerald)' : 'var(--admin-rose)', fontWeight: 700 }}>
                  {selectedDoctor.is_active ? 'Active' : 'Suspended'}
                </span>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Last Login</span>
                <span>{selectedDoctor.last_login ? formatDate(selectedDoctor.last_login) : 'Never logged in'}</span>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Registered On</span>
                <span>{formatDate(selectedDoctor.created_at)}</span>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Patient Assessments</span>
                <strong>{selectedDoctor.total_assessments ?? 0}</strong>
              </div>

              <div>
                <span style={{ color: 'var(--admin-text-subtle)', fontSize: '0.74rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Total Predictions</span>
                <strong>{selectedDoctor.total_predictions ?? 0}</strong>
              </div>
            </div>

            {selectedDoctor.rejection_reason && (
              <div style={{ marginTop: '1.25rem', padding: '12px', background: 'var(--admin-rose-light)', border: '1px solid var(--admin-rose-border)', borderRadius: '8px', color: 'var(--admin-rose)', fontSize: '0.84rem' }}>
                <strong>Rejection Reason:</strong> {selectedDoctor.rejection_reason}
              </div>
            )}

            <div className="admin-modal-actions">
              {selectedDoctor.has_document && (
                <button
                  type="button"
                  className="admin-btn-secondary"
                  onClick={() => { setDetailModalOpen(false); handleViewDocument(selectedDoctor); }}
                >
                  📄 View Certificate
                </button>
              )}
              <button
                type="button"
                className="admin-btn-secondary"
                onClick={() => setDetailModalOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          MODAL 2: APPROVE DOCTOR CONFIRMATION DIALOG
      ────────────────────────────────────────────────────────────────────────── */}
      {approveModalOpen && selectedDoctor && (
        <div className="admin-modal-overlay" onClick={() => setApproveModalOpen(false)}>
          <div className="admin-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <h3 style={{ margin: '0 0 10px', color: 'var(--admin-emerald)', fontSize: '1.25rem', fontWeight: 800 }}>
              Approve Physician Credentials
            </h3>
            <p style={{ fontSize: '0.88rem', color: 'var(--admin-text-muted)', lineHeight: '1.5', margin: '0 0 1rem' }}>
              Confirm approval for <strong>Dr. {selectedDoctor.full_name}</strong> ({selectedDoctor.medical_degree}, Reg No: <code>{selectedDoctor.registration_number}</code>).
            </p>
            <div style={{ background: 'var(--admin-emerald-light)', border: '1px solid var(--admin-emerald-border)', borderRadius: '8px', padding: '12px', fontSize: '0.8rem', color: 'var(--admin-emerald)', marginBottom: '1.25rem' }}>
              ✓ Status will be updated to <strong>APPROVED</strong><br />
              ✓ A unique portal username will be generated<br />
              ✓ An automated approval email with login access details will be dispatched to <strong>{selectedDoctor.email}</strong>
            </div>
            <div className="admin-modal-actions">
              <button
                type="button"
                className="admin-btn-secondary"
                onClick={() => setApproveModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="admin-btn-approve"
                onClick={handleApprove}
                disabled={actionInProgress}
              >
                {actionInProgress ? 'Approving…' : 'Confirm & Dispatch Email'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          MODAL 3: REJECT DOCTOR CONFIRMATION DIALOG
      ────────────────────────────────────────────────────────────────────────── */}
      {rejectModalOpen && selectedDoctor && (
        <div className="admin-modal-overlay" onClick={() => setRejectModalOpen(false)}>
          <div className="admin-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <h3 style={{ margin: '0 0 10px', color: 'var(--admin-rose)', fontSize: '1.25rem', fontWeight: 800 }}>
              Reject Registration Application
            </h3>
            <p style={{ fontSize: '0.88rem', color: 'var(--admin-text-muted)', margin: '0 0 1rem' }}>
              Enter the clinical or council verification reason for rejecting <strong>Dr. {selectedDoctor.full_name}</strong>:
            </p>
            <textarea
              rows={4}
              placeholder="e.g., Medical registration number could not be validated against the State Medical Council directory."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '8px',
                border: '1px solid var(--admin-border-subtle)',
                background: 'var(--admin-bg-base)',
                color: 'var(--admin-text-main)',
                fontSize: '0.88rem',
                fontFamily: 'inherit',
                outline: 'none',
              }}
            />
            <div style={{ fontSize: '0.76rem', color: 'var(--admin-text-subtle)', marginTop: '6px', marginBottom: '1.25rem' }}>
              * This reason will be recorded in the audit log and dispatched directly to the doctor's registered email.
            </div>
            <div className="admin-modal-actions">
              <button
                type="button"
                className="admin-btn-secondary"
                onClick={() => setRejectModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="admin-btn-reject"
                onClick={handleReject}
                disabled={actionInProgress || !rejectionReason.trim()}
              >
                {actionInProgress ? 'Rejecting…' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          MODAL 4: SUSPEND / ACTIVATE CONFIRMATION DIALOG (Phase 5 Requirement)
      ────────────────────────────────────────────────────────────────────────── */}
      {suspendModalOpen && doctorToToggle && (
        <div className="admin-modal-overlay" onClick={() => setSuspendModalOpen(false)}>
          <div className="admin-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <h3 style={{
              margin: '0 0 10px',
              color: doctorToToggle.is_active ? 'var(--admin-rose)' : 'var(--admin-emerald)',
              fontSize: '1.25rem',
              fontWeight: 800,
            }}>
              {doctorToToggle.is_active ? 'Suspend Physician Account' : 'Reactivate Physician Account'}
            </h3>
            <p style={{ fontSize: '0.88rem', color: 'var(--admin-text-muted)', lineHeight: '1.5', margin: '0 0 1rem' }}>
              Are you sure you want to {doctorToToggle.is_active ? 'suspend' : 'reactivate'} the clinical access for <strong>Dr. {doctorToToggle.full_name}</strong> ({doctorToToggle.email})?
            </p>
            <div style={{
              background: doctorToToggle.is_active ? 'var(--admin-rose-light)' : 'var(--admin-emerald-light)',
              border: `1px solid ${doctorToToggle.is_active ? 'var(--admin-rose-border)' : 'var(--admin-emerald-border)'}`,
              borderRadius: '8px',
              padding: '12px',
              fontSize: '0.8rem',
              color: doctorToToggle.is_active ? 'var(--admin-rose)' : 'var(--admin-emerald)',
              marginBottom: '1.25rem',
            }}>
              {doctorToToggle.is_active ? (
                <>⚠ <strong>Suspension Impact:</strong> The physician will be prevented from logging in or computing clinical risk predictions until reactivated.</>
              ) : (
                <>✓ <strong>Reactivation Impact:</strong> The physician will regain full access to patient assessments and mortality risk prediction workspaces.</>
              )}
            </div>
            <div className="admin-modal-actions">
              <button
                type="button"
                className="admin-btn-secondary"
                onClick={() => setSuspendModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className={doctorToToggle.is_active ? 'admin-btn-reject' : 'admin-btn-approve'}
                onClick={confirmToggleActive}
                disabled={actionInProgress}
              >
                {actionInProgress ? 'Processing…' : (doctorToToggle.is_active ? 'Confirm Suspension' : 'Confirm Reactivation')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          MODAL 5: DOCUMENT VIEWER MODAL
      ────────────────────────────────────────────────────────────────────────── */}
      {documentModalOpen && (
        <div className="admin-modal-overlay" onClick={() => setDocumentModalOpen(false)}>
          <div className="admin-modal-card" style={{ maxWidth: '800px', width: '100%' }} onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal-header">
              <div>
                <h3 style={{ fontSize: '1.15rem' }}>Medical Registration Certificate</h3>
                <span>{selectedDoctor?.full_name} &bull; Reg: {selectedDoctor?.registration_number}</span>
              </div>
              <button
                type="button"
                className="admin-modal-close-btn"
                onClick={() => setDocumentModalOpen(false)}
                aria-label="Close document"
              >
                &times;
              </button>
            </div>
            <div style={{ padding: '1.25rem 0', textAlign: 'center' }}>
              {documentLoading ? (
                <div style={{ padding: '3.5rem', color: 'var(--admin-text-muted)' }}>Streaming document securely…</div>
              ) : documentUrl ? (
                <iframe
                  src={documentUrl}
                  title="Medical Registration Certificate"
                  style={{ width: '100%', height: '520px', border: '1px solid var(--admin-border-subtle)', borderRadius: '8px', background: '#ffffff' }}
                />
              ) : (
                <div style={{ padding: '3.5rem', color: 'var(--admin-rose)' }}>Document could not be previewed or file is missing on storage disk.</div>
              )}
            </div>
            <div className="admin-modal-actions">
              <button
                type="button"
                className="admin-btn-secondary"
                onClick={() => setDocumentModalOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
