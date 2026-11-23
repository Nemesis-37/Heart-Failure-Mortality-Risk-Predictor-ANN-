import React, { useState, useEffect } from 'react'
import { MODEL_DATA } from './pages/ModelPerformancePage.jsx'
import ThemeToggle from './components/ThemeToggle.jsx'
import { apiUrl } from './apiConfig.js'

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

  const handleToggleActive = async (doctor) => {
    setActionInProgress(true)
    try {
      const res = await fetch(apiUrl(`/admin/doctors/${doctor.doctor_id}/toggle-active`), {
        method: 'POST',
        headers: { Authorization: `Bearer ${adminToken}` },
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to update account status.')

      setActionFeedback(data.message)
      if (activeTab === 'management') {
        fetchDoctors(statusFilter)
      } else {
        fetchDoctors(verificationFilter)
      }
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
      setActionFeedback(`Dr. ${selectedDoctor.full_name} has been APPROVED. Assigned username: ${data.username || 'dr_' + selectedDoctor.full_name.toLowerCase().replace(/\\s+/g, '')}. Confirmation email dispatched.`)
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
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'management', label: 'Doctor Management', icon: '👥' },
    { id: 'verification', label: 'Doctor Verification', icon: '🛡️' },
    { id: 'activity', label: 'Doctor Activity', icon: '📈' },
    { id: 'performance', label: 'Model Performance', icon: '⚡' },
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

  return (
    <div className="admin-dashboard-root" style={{ display: 'flex', minHeight: '100vh', background: '#F3F7FC', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* ──────────────────────────────────────────────────────────────────────────
          1. LEFT SIDEBAR NAVIGATION
      ────────────────────────────────────────────────────────────────────────── */}
      <aside style={{
        width: '280px',
        background: '#0B1F3A',
        color: '#FFFFFF',
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid #102F56',
        flexShrink: 0,
      }}>
        {/* Brand Header */}
        <div style={{
          padding: '1.75rem 1.5rem',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #1565D8 0%, #38BDF8 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.25rem',
            boxShadow: '0 4px 12px rgba(21, 101, 216, 0.35)',
          }}>
            🛡️
          </div>
          <div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, letterSpacing: '0.02em', color: '#FFFFFF' }}>
              CardioPredict
            </div>
            <div style={{ fontSize: '0.72rem', color: '#38BDF8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Admin Console
            </div>
          </div>
        </div>

        {/* Sidebar Nav Items */}
        <nav style={{ flex: 1, padding: '1.25rem 0.85rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ padding: '0.5rem 0.75rem', fontSize: '0.68rem', fontWeight: 700, color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Administrative Control
          </div>

          {navItems.map((item) => {
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '11px 16px',
                  borderRadius: '10px',
                  border: 'none',
                  background: isActive ? '#1565D8' : 'transparent',
                  color: isActive ? '#FFFFFF' : '#CBD5E1',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s ease',
                  boxShadow: isActive ? '0 4px 12px rgba(21, 101, 216, 0.3)' : 'none',
                }}
              >
                <span style={{ fontSize: '1.15rem' }}>{item.icon}</span>
                <span>{item.label}</span>
                {item.id === 'verification' && overviewStats?.pending_doctors > 0 && (
                  <span style={{
                    marginLeft: 'auto',
                    background: '#EF4444',
                    color: '#FFFFFF',
                    fontSize: '0.7rem',
                    fontWeight: 800,
                    padding: '2px 7px',
                    borderRadius: '10px',
                  }}>
                    {overviewStats.pending_doctors}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {/* Sidebar Footer with Logout */}
        <div style={{
          padding: '1.25rem',
          borderTop: '1px solid rgba(255,255,255,0.08)',
          background: '#08172C',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: '#102F56',
              border: '1.5px solid #38BDF8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.85rem',
              fontWeight: 700,
              color: '#38BDF8',
            }}>
              {adminProfile?.username ? adminProfile.username.substring(0, 2).toUpperCase() : 'AD'}
            </div>
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#FFFFFF', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                {adminProfile?.full_name || 'Hospital Admin'}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#94A3B8' }}>
                {adminProfile?.role || 'Super Administrator'}
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={handleAdminLogout}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '9px 14px',
              borderRadius: '8px',
              border: '1px solid #1E3A5F',
              background: 'rgba(239, 68, 68, 0.1)',
              color: '#F87171',
              fontWeight: 600,
              fontSize: '0.82rem',
              cursor: 'pointer',
              transition: 'background 0.15s ease',
            }}
          >
            <span>🚪</span>
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* ──────────────────────────────────────────────────────────────────────────
          2. MAIN CONTENT AREA
      ────────────────────────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflowY: 'auto' }}>
        {/* Top Header */}
        <header className="admin-header" style={{
          background: '#FFFFFF',
          borderBottom: '1px solid #DBEAFE',
          padding: '1.25rem 2.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          boxShadow: '0 2px 6px rgba(11, 31, 58, 0.03)',
        }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.45rem', fontWeight: 800, color: '#0B1F3A' }}>
              {activeTab === 'overview' && 'System Overview & Clinical Intelligence'}
              {activeTab === 'management' && 'Physician Credential Directory'}
              {activeTab === 'verification' && 'Doctor Credential Verification Queue'}
              {activeTab === 'activity' && 'Doctor Clinical Activity Analytics'}
              {activeTab === 'performance' && 'Machine Learning Model Performance & Benchmarks'}
            </h1>
            <p style={{ margin: '4px 0 0', fontSize: '0.82rem', color: '#64748B' }}>
              Heart Failure Mortality Risk Predictor &bull; Administrative Governance
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <ThemeToggle />
            <div style={{
              background: '#EFF6FF',
              border: '1px solid #BFDBFE',
              borderRadius: '10px',
              padding: '6px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.82rem',
              color: '#1565D8',
            }}>
              <span style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#10B981',
                boxShadow: '0 0 6px #10B981',
              }} />
              <span>Session: <strong>admin</strong></span>
            </div>

            {onExitAdmin && (
              <button
                type="button"
                onClick={onExitAdmin}
                style={{
                  background: '#1565D8',
                  color: '#FFFFFF',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 2px 6px rgba(21, 101, 216, 0.25)',
                }}
              >
                <span>&larr;</span>
                <span>Switch to Doctor Portal</span>
              </button>
            )}
          </div>
        </header>

        {/* Main Body Content */}
        <main style={{ flex: 1, padding: '2rem 2.25rem' }}>
          {/* Action Feedback Toast */}
          {actionFeedback && (
            <div style={{
              background: '#EFF6FF',
              border: '1.5px solid #93C5FD',
              borderRadius: '12px',
              padding: '1rem 1.5rem',
              marginBottom: '1.5rem',
              color: '#1565D8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.88rem',
              fontWeight: 600,
              boxShadow: '0 4px 12px rgba(21, 101, 216, 0.08)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '1.1rem' }}>🔔</span>
                <span>{actionFeedback}</span>
              </div>
              <button
                type="button"
                onClick={() => setActionFeedback('')}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#1565D8', fontSize: '1.25rem', lineHeight: 1 }}
              >
                &times;
              </button>
            </div>
          )}

          {/* =========================================================================
              SECTION 1: OVERVIEW
          ========================================================================= */}
          {activeTab === 'overview' && (
            <div>
              {overviewLoading ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: '#64748B' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⏳</div>
                  <div>Loading live database statistics from {overviewStats?.database_engine || 'PostgreSQL'}…</div>
                </div>
              ) : (
                <>
                  {/* 6 Core Statistics Cards */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: '1.25rem',
                    marginBottom: '2rem',
                  }}>
                    {/* Card 1: Total Registered */}
                    <div className="admin-stat-card" style={{
                      background: '#FFFFFF',
                      borderRadius: '14px',
                      padding: '1.5rem',
                      border: '1px solid #DBEAFE',
                      boxShadow: '0 2px 8px rgba(11, 31, 58, 0.04)',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Total Registered
                        </span>
                        <span style={{ background: '#DBEAFE', color: '#1565D8', padding: '4px 8px', borderRadius: '8px', fontSize: '0.85rem' }}>👥</span>
                      </div>
                      <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#0B1F3A', marginTop: '8px' }}>
                        {overviewStats?.total_doctors ?? '—'}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#64748B', marginTop: '4px' }}>
                        Total physicians in database
                      </div>
                    </div>

                    {/* Card 2: Approved Doctors */}
                    <div className="admin-stat-card" style={{
                      background: '#FFFFFF',
                      borderRadius: '14px',
                      padding: '1.5rem',
                      border: '1px solid #BBF7D0',
                      boxShadow: '0 2px 8px rgba(16, 185, 129, 0.06)',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#166534', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Approved Doctors
                        </span>
                        <span style={{ background: '#DCFCE7', color: '#16A34A', padding: '4px 8px', borderRadius: '8px', fontSize: '0.85rem' }}>✓</span>
                      </div>
                      <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#16A34A', marginTop: '8px' }}>
                        {overviewStats?.approved_doctors ?? '—'}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#166534', marginTop: '4px' }}>
                        Active clinical predictors
                      </div>
                    </div>

                    {/* Card 3: Pending Review */}
                    <div className="admin-stat-card" style={{
                      background: '#FFFFFF',
                      borderRadius: '14px',
                      padding: '1.5rem',
                      border: '1px solid #FEF08A',
                      boxShadow: '0 2px 8px rgba(202, 138, 4, 0.06)',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#854D0E', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Pending Review
                        </span>
                        <span style={{ background: '#FEF9C3', color: '#CA8A04', padding: '4px 8px', borderRadius: '8px', fontSize: '0.85rem' }}>⏳</span>
                      </div>
                      <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#CA8A04', marginTop: '8px' }}>
                        {overviewStats?.pending_doctors ?? '—'}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#854D0E', marginTop: '4px' }}>
                        Awaiting council verification
                      </div>
                    </div>

                    {/* Card 4: Rejected Doctors */}
                    <div className="admin-stat-card" style={{
                      background: '#FFFFFF',
                      borderRadius: '14px',
                      padding: '1.5rem',
                      border: '1px solid #FECACA',
                      boxShadow: '0 2px 8px rgba(220, 38, 38, 0.06)',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#991B1B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Rejected
                        </span>
                        <span style={{ background: '#FEE2E2', color: '#DC2626', padding: '4px 8px', borderRadius: '8px', fontSize: '0.85rem' }}>✕</span>
                      </div>
                      <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#DC2626', marginTop: '8px' }}>
                        {overviewStats?.rejected_doctors ?? '—'}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#991B1B', marginTop: '4px' }}>
                        Access denied or unvalidated
                      </div>
                    </div>

                    {/* Card 5: Total Assessments */}
                    <div className="admin-stat-card" style={{
                      background: '#FFFFFF',
                      borderRadius: '14px',
                      padding: '1.5rem',
                      border: '1px solid #DBEAFE',
                      boxShadow: '0 2px 8px rgba(11, 31, 58, 0.04)',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#1E40AF', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Assessments
                        </span>
                        <span style={{ background: '#DBEAFE', color: '#1D4ED8', padding: '4px 8px', borderRadius: '8px', fontSize: '0.85rem' }}>📋</span>
                      </div>
                      <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#1565D8', marginTop: '8px' }}>
                        {overviewStats?.total_assessments ?? '—'}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#64748B', marginTop: '4px' }}>
                        Recorded patient profiles
                      </div>
                    </div>

                    {/* Card 6: Total Predictions */}
                    <div className="admin-stat-card" style={{
                      background: '#FFFFFF',
                      borderRadius: '14px',
                      padding: '1.5rem',
                      border: '1px solid #DDD6FE',
                      boxShadow: '0 2px 8px rgba(124, 58, 237, 0.06)',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#6D28D9', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Total Predictions
                        </span>
                        <span style={{ background: '#EDE9FE', color: '#7C3AED', padding: '4px 8px', borderRadius: '8px', fontSize: '0.85rem' }}>⚡</span>
                      </div>
                      <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#7C3AED', marginTop: '8px' }}>
                        {overviewStats?.total_predictions ?? '—'}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#64748B', marginTop: '4px' }}>
                        Dual model inferences
                      </div>
                    </div>
                  </div>

                  {/* Two-Column Activity Dashboard */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))', gap: '1.75rem', marginBottom: '2rem' }}>
                    {/* Left Panel: Recent Doctor Registrations */}
                    <div className="admin-panel-card" style={{
                      background: '#FFFFFF',
                      borderRadius: '16px',
                      border: '1px solid #DBEAFE',
                      padding: '1.5rem',
                      boxShadow: '0 2px 10px rgba(11, 31, 58, 0.04)',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                        <div>
                          <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#0B1F3A', fontWeight: 800 }}>
                            Recent Doctor Registrations
                          </h3>
                          <span style={{ fontSize: '0.78rem', color: '#64748B' }}>Latest 5 applicants in registry</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => setActiveTab('management')}
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
                          View All Doctors &rarr;
                        </button>
                      </div>

                      {recentActivity?.recent_registrations?.length > 0 ? (
                        <div style={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.84rem' }}>
                            <thead>
                              <tr style={{ background: '#F8FAFC', borderBottom: '2px solid #E2E8F0', color: '#64748B' }}>
                                <th style={{ padding: '8px 10px' }}>Doctor Name</th>
                                <th style={{ padding: '8px 10px' }}>Email</th>
                                <th style={{ padding: '8px 10px' }}>Date</th>
                                <th style={{ padding: '8px 10px' }}>Status</th>
                                <th style={{ padding: '8px 10px', textAlign: 'right' }}>Action</th>
                              </tr>
                            </thead>
                            <tbody>
                              {recentActivity.recent_registrations.map((doc) => (
                                <tr key={doc.doctor_id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                                  <td style={{ padding: '10px 10px', fontWeight: 700, color: '#0B1F3A' }}>
                                    {doc.full_name}
                                  </td>
                                  <td style={{ padding: '10px 10px', color: '#64748B', fontSize: '0.8rem' }}>
                                    {doc.email}
                                  </td>
                                  <td style={{ padding: '10px 10px', color: '#64748B', fontSize: '0.78rem' }}>
                                    {formatDate(doc.created_at).split(',')[0]}
                                  </td>
                                  <td style={{ padding: '10px 10px' }}>
                                    <span style={{
                                      padding: '3px 8px',
                                      borderRadius: '12px',
                                      fontSize: '0.72rem',
                                      fontWeight: 700,
                                      background: doc.verification_status === 'APPROVED' ? '#DCFCE7' : doc.verification_status === 'PENDING' ? '#FEF9C3' : '#FEE2E2',
                                      color: doc.verification_status === 'APPROVED' ? '#166534' : doc.verification_status === 'PENDING' ? '#854D0E' : '#991B1B',
                                    }}>
                                      {doc.verification_status}
                                    </span>
                                  </td>
                                  <td style={{ padding: '10px 10px', textAlign: 'right' }}>
                                    <button
                                      type="button"
                                      onClick={() => openDoctorDetails(doc)}
                                      style={{
                                        background: '#F1F5F9',
                                        color: '#1565D8',
                                        border: '1px solid #CBD5E1',
                                        padding: '4px 10px',
                                        borderRadius: '6px',
                                        fontSize: '0.75rem',
                                        fontWeight: 600,
                                        cursor: 'pointer',
                                      }}
                                    >
                                      Details
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div style={{ textAlign: 'center', padding: '2rem', color: '#94A3B8', fontSize: '0.85rem' }}>
                          No recent doctor registrations recorded.
                        </div>
                      )}
                    </div>

                    {/* Right Panel: Recent Activity Summary */}
                    <div className="admin-panel-card" style={{
                      background: '#FFFFFF',
                      borderRadius: '16px',
                      border: '1px solid #DBEAFE',
                      padding: '1.5rem',
                      boxShadow: '0 2px 10px rgba(11, 31, 58, 0.04)',
                    }}>
                      <div style={{ marginBottom: '1.25rem' }}>
                        <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#0B1F3A', fontWeight: 800 }}>
                          Recent Activity Summary
                        </h3>
                        <span style={{ fontSize: '0.78rem', color: '#64748B' }}>Actual telemetry from {overviewStats?.database_engine || 'PostgreSQL'}</span>
                      </div>

                      {/* 7-Day Volume Ticker */}
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: '12px',
                        marginBottom: '1.25rem',
                      }}>
                        <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '10px', padding: '12px' }}>
                          <div style={{ fontSize: '0.74rem', color: '#1E40AF', fontWeight: 700, textTransform: 'uppercase' }}>
                            Assessments (Past 7 Days)
                          </div>
                          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#1565D8', marginTop: '4px' }}>
                            {recentActivity?.total_assessments_last_7_days ?? 0}
                          </div>
                        </div>

                        <div style={{ background: '#F5F3FF', border: '1px solid #DDD6FE', borderRadius: '10px', padding: '12px' }}>
                          <div style={{ fontSize: '0.74rem', color: '#6D28D9', fontWeight: 700, textTransform: 'uppercase' }}>
                            Predictions (Past 7 Days)
                          </div>
                          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#7C3AED', marginTop: '4px' }}>
                            {recentActivity?.total_predictions_last_7_days ?? 0}
                          </div>
                        </div>
                      </div>

                      {/* Recently Logged-in Clinicians */}
                      <div style={{ marginBottom: '1rem' }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#475569', marginBottom: '8px', textTransform: 'uppercase' }}>
                          Recently Logged-In Doctors
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
                                  background: '#F8FAFC',
                                  borderRadius: '8px',
                                  border: '1px solid #E2E8F0',
                                  fontSize: '0.82rem',
                                }}
                              >
                                <div>
                                  <strong style={{ color: '#0B1F3A' }}>{act.full_name}</strong>
                                  <span style={{ fontSize: '0.74rem', color: '#64748B', marginLeft: '6px' }}>({act.username || 'dr_physician'})</span>
                                </div>
                                <div style={{ fontSize: '0.75rem', color: '#1565D8', fontWeight: 600 }}>
                                  {act.last_login ? formatDate(act.last_login) : 'Active session'}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div style={{ fontSize: '0.82rem', color: '#94A3B8' }}>No recent logins logged.</div>
                        )}
                      </div>

                      {/* Latest Verifications */}
                      <div>
                        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#475569', marginBottom: '8px', textTransform: 'uppercase' }}>
                          Latest Decisions (Approvals / Rejections)
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
                                  background: v.verification_status === 'APPROVED' ? '#F0FDF4' : '#FEF2F2',
                                  borderRadius: '8px',
                                  border: `1px solid ${v.verification_status === 'APPROVED' ? '#BBF7D0' : '#FECACA'}`,
                                  fontSize: '0.82rem',
                                }}
                              >
                                <div>
                                  <strong style={{ color: '#0B1F3A' }}>{v.full_name}</strong>
                                  <span style={{ fontSize: '0.74rem', color: '#64748B', marginLeft: '6px' }}>{v.registration_council}</span>
                                </div>
                                <span style={{
                                  padding: '2px 8px',
                                  borderRadius: '10px',
                                  fontSize: '0.7rem',
                                  fontWeight: 800,
                                  background: v.verification_status === 'APPROVED' ? '#DCFCE7' : '#FEE2E2',
                                  color: v.verification_status === 'APPROVED' ? '#166534' : '#DC2626',
                                }}>
                                  {v.verification_status}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div style={{ fontSize: '0.82rem', color: '#94A3B8' }}>No verifications completed recently.</div>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* =========================================================================
              SECTION 2: DOCTOR MANAGEMENT
          ========================================================================= */}
          {activeTab === 'management' && (
            <div className="admin-panel-card" style={{ background: '#FFFFFF', borderRadius: '16px', border: '1px solid #DBEAFE', padding: '1.75rem', boxShadow: '0 2px 10px rgba(11, 31, 58, 0.04)' }}>
              {/* Header and Controls */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#0B1F3A', fontWeight: 800 }}>
                    Physician Management Directory
                  </h2>
                  <p style={{ margin: '4px 0 0', color: '#64748B', fontSize: '0.84rem' }}>
                    Search, filter, inspect full credential profiles, and manage system access status.
                  </p>
                </div>

                {/* Status Filter Tabs & Search */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', gap: '4px', background: '#F1F5F9', padding: '4px', borderRadius: '10px' }}>
                    {['ALL', 'APPROVED', 'PENDING', 'REJECTED'].map((filter) => (
                      <button
                        key={filter}
                        type="button"
                        onClick={() => setStatusFilter(filter)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '8px',
                          fontSize: '0.78rem',
                          fontWeight: 700,
                          border: 'none',
                          cursor: 'pointer',
                          background: statusFilter === filter ? '#1565D8' : 'transparent',
                          color: statusFilter === filter ? '#FFFFFF' : '#64748B',
                          transition: 'background 0.15s ease',
                        }}
                      >
                        {filter}
                      </button>
                    ))}
                  </div>

                  <input
                    type="text"
                    placeholder="Search name, email, reg no., username…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{
                      padding: '8px 14px',
                      borderRadius: '8px',
                      border: '1px solid #CBD5E1',
                      width: '280px',
                      fontSize: '0.85rem',
                      outline: 'none',
                    }}
                  />
                </div>
              </div>

              {/* Table */}
              {isLoading ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: '#64748B' }}>Loading physician directory…</div>
              ) : listError ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: '#DC2626' }}>{listError}</div>
              ) : filteredManagementDoctors.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: '#94A3B8' }}>
                  No doctors found matching the search criteria.
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.84rem' }}>
                    <thead>
                      <tr style={{ background: '#F8FAFC', borderBottom: '2px solid #E2E8F0', color: '#475569' }}>
                        <th style={{ padding: '12px 10px' }}>Doctor ID</th>
                        <th style={{ padding: '12px 10px' }}>Doctor Name</th>
                        <th style={{ padding: '12px 10px' }}>Username</th>
                        <th style={{ padding: '12px 10px' }}>Email</th>
                        <th style={{ padding: '12px 10px' }}>Medical Degree</th>
                        <th style={{ padding: '12px 10px' }}>Reg Number</th>
                        <th style={{ padding: '12px 10px' }}>Reg Council</th>
                        <th style={{ padding: '12px 10px' }}>Reg Date</th>
                        <th style={{ padding: '12px 10px' }}>Status</th>
                        <th style={{ padding: '12px 10px' }}>Last Login</th>
                        <th style={{ padding: '12px 10px', textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredManagementDoctors.map((doc) => {
                        const isApproved = doc.verification_status === 'APPROVED'
                        const isPending = doc.verification_status === 'PENDING'
                        return (
                          <tr key={doc.doctor_id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                            <td style={{ padding: '12px 10px', fontFamily: 'monospace', fontSize: '0.78rem', color: '#64748B' }}>
                              {doc.doctor_id.substring(0, 8)}…
                            </td>
                            <td style={{ padding: '12px 10px', fontWeight: 700, color: '#0B1F3A' }}>
                              {doc.full_name}
                            </td>
                            <td style={{ padding: '12px 10px' }}>
                              {doc.username ? (
                                <code style={{ background: '#EFF6FF', color: '#1565D8', padding: '2px 6px', borderRadius: '4px', fontSize: '0.78rem' }}>
                                  {doc.username}
                                </code>
                              ) : (
                                <span style={{ color: '#94A3B8', fontSize: '0.78rem', fontStyle: 'italic' }}>Pending</span>
                              )}
                            </td>
                            <td style={{ padding: '12px 10px', color: '#64748B' }}>
                              {doc.email}
                            </td>
                            <td style={{ padding: '12px 10px', color: '#0B1F3A' }}>
                              {doc.medical_degree}
                            </td>
                            <td style={{ padding: '12px 10px', fontFamily: 'monospace', fontWeight: 600 }}>
                              {doc.registration_number}
                            </td>
                            <td style={{ padding: '12px 10px', color: '#64748B', fontSize: '0.8rem' }}>
                              {doc.registration_council}
                            </td>
                            <td style={{ padding: '12px 10px', color: '#64748B', fontSize: '0.78rem' }}>
                              {formatDate(doc.created_at).split(',')[0]}
                            </td>
                            <td style={{ padding: '12px 10px' }}>
                              <span style={{
                                padding: '4px 9px',
                                borderRadius: '12px',
                                fontSize: '0.72rem',
                                fontWeight: 700,
                                background: isApproved ? '#DCFCE7' : isPending ? '#FEF9C3' : '#FEE2E2',
                                color: isApproved ? '#166534' : isPending ? '#854D0E' : '#991B1B',
                              }}>
                                {doc.verification_status}
                              </span>
                            </td>
                            <td style={{ padding: '12px 10px', fontSize: '0.78rem', color: doc.last_login ? '#0B1F3A' : '#94A3B8' }}>
                              {doc.last_login ? formatDate(doc.last_login) : 'Never'}
                            </td>
                            <td style={{ padding: '12px 10px', textAlign: 'right' }}>
                              <div style={{ display: 'inline-flex', gap: '6px' }}>
                                <button
                                  type="button"
                                  onClick={() => openDoctorDetails(doc)}
                                  style={{
                                    padding: '5px 10px',
                                    borderRadius: '6px',
                                    fontSize: '0.76rem',
                                    fontWeight: 600,
                                    border: '1px solid #CBD5E1',
                                    background: '#FFFFFF',
                                    color: '#1565D8',
                                    cursor: 'pointer',
                                  }}
                                >
                                  View
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleToggleActive(doc)}
                                  disabled={actionInProgress}
                                  style={{
                                    padding: '5px 10px',
                                    borderRadius: '6px',
                                    fontSize: '0.76rem',
                                    fontWeight: 600,
                                    border: '1px solid #CBD5E1',
                                    background: doc.is_active ? '#FEF2F2' : '#F0FDF4',
                                    color: doc.is_active ? '#DC2626' : '#16A34A',
                                    cursor: 'pointer',
                                  }}
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
              SECTION 3: DOCTOR VERIFICATION
          ========================================================================= */}
          {activeTab === 'verification' && (
            <div className="admin-panel-card" style={{ background: '#FFFFFF', borderRadius: '16px', border: '1px solid #DBEAFE', padding: '1.75rem', boxShadow: '0 2px 10px rgba(11, 31, 58, 0.04)' }}>
              {/* Header and Filter */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#0B1F3A', fontWeight: 800 }}>
                    Medical Credential Verification Queue
                  </h2>
                  <p style={{ margin: '4px 0 0', color: '#64748B', fontSize: '0.84rem' }}>
                    Inspect registration certificates, cross-reference state councils, and issue approvals or rejections.
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', gap: '4px', background: '#F1F5F9', padding: '4px', borderRadius: '10px' }}>
                    {['PENDING', 'APPROVED', 'REJECTED', 'ALL'].map((f) => (
                      <button
                        key={f}
                        type="button"
                        onClick={() => setVerificationFilter(f)}
                        style={{
                          padding: '6px 14px',
                          borderRadius: '8px',
                          fontSize: '0.78rem',
                          fontWeight: 700,
                          border: 'none',
                          cursor: 'pointer',
                          background: verificationFilter === f ? '#1565D8' : 'transparent',
                          color: verificationFilter === f ? '#FFFFFF' : '#64748B',
                        }}
                      >
                        {f}
                      </button>
                    ))}
                  </div>

                  <input
                    type="text"
                    placeholder="Search applicant name, reg no.…"
                    value={verificationSearch}
                    onChange={(e) => setVerificationSearch(e.target.value)}
                    style={{
                      padding: '8px 14px',
                      borderRadius: '8px',
                      border: '1px solid #CBD5E1',
                      width: '260px',
                      fontSize: '0.85rem',
                      outline: 'none',
                    }}
                  />
                </div>
              </div>

              {/* Application Cards */}
              {isLoading ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: '#64748B' }}>Loading credential queue…</div>
              ) : filteredVerificationDoctors.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: '#94A3B8' }}>
                  No applications found in the <strong>{verificationFilter}</strong> queue.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {filteredVerificationDoctors.map((doc) => (
                    <div
                      key={doc.doctor_id}
                      style={{
                        border: '1px solid #E2E8F0',
                        borderRadius: '12px',
                        padding: '1.5rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: '1.25rem',
                        background: '#FFFFFF',
                        transition: 'box-shadow 0.15s ease',
                      }}
                    >
                      <div style={{ maxWidth: '650px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                          <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#0B1F3A', fontWeight: 800 }}>
                            {doc.full_name}
                          </h3>
                          <span style={{
                            padding: '3px 9px',
                            borderRadius: '12px',
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            background: doc.email_verified ? '#DCFCE7' : '#FEF3C7',
                            color: doc.email_verified ? '#15803D' : '#B45309',
                          }}>
                            {doc.email_verified ? '✓ Email Verified' : '⚠ Email Unverified'}
                          </span>
                          <span style={{
                            padding: '3px 9px',
                            borderRadius: '12px',
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            background: doc.verification_status === 'APPROVED' ? '#DCFCE7' : doc.verification_status === 'PENDING' ? '#FEF9C3' : '#FEE2E2',
                            color: doc.verification_status === 'APPROVED' ? '#166534' : doc.verification_status === 'PENDING' ? '#854D0E' : '#991B1B',
                          }}>
                            Status: {doc.verification_status}
                          </span>
                        </div>

                        {/* Detailed Fields Grid */}
                        <div style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                          gap: '10px',
                          fontSize: '0.84rem',
                          color: '#475569',
                          marginTop: '10px',
                        }}>
                          <div><strong>Medical Degree:</strong> {doc.medical_degree}</div>
                          <div><strong>Council:</strong> {doc.registration_council}</div>
                          <div><strong>Registration No:</strong> <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#0B1F3A' }}>{doc.registration_number}</span></div>
                          <div><strong>Email:</strong> {doc.email}</div>
                          <div><strong>Mobile:</strong> {doc.mobile}</div>
                          <div><strong>Applied On:</strong> {formatDate(doc.created_at)}</div>
                          {doc.username && (
                            <div><strong>Username:</strong> <code style={{ color: '#1565D8' }}>{doc.username}</code></div>
                          )}
                        </div>

                        {/* Rejection notice if present */}
                        {doc.rejection_reason && (
                          <div style={{
                            marginTop: '12px',
                            padding: '8px 12px',
                            borderRadius: '8px',
                            background: '#FEF2F2',
                            border: '1px solid #FECACA',
                            color: '#991B1B',
                            fontSize: '0.82rem',
                          }}>
                            <strong>Rejection Reason Recorded:</strong> {doc.rejection_reason}
                          </div>
                        )}
                      </div>

                      {/* Action Buttons */}
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        {doc.has_document && (
                          <button
                            type="button"
                            onClick={() => handleViewDocument(doc)}
                            style={{
                              padding: '9px 16px',
                              borderRadius: '8px',
                              border: '1px solid #CBD5E1',
                              background: '#FFFFFF',
                              color: '#334155',
                              fontSize: '0.84rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                            }}
                          >
                            <span>📄</span>
                            <span>View Certificate</span>
                          </button>
                        )}

                        {doc.verification_status === 'PENDING' && (
                          <>
                            <button
                              type="button"
                              onClick={() => { setSelectedDoctor(doc); setApproveModalOpen(true); }}
                              style={{
                                padding: '9px 18px',
                                borderRadius: '8px',
                                border: 'none',
                                background: '#16A34A',
                                color: '#FFFFFF',
                                fontSize: '0.84rem',
                                fontWeight: 700,
                                cursor: 'pointer',
                                boxShadow: '0 2px 6px rgba(22, 163, 74, 0.25)',
                              }}
                            >
                              ✓ Approve
                            </button>
                            <button
                              type="button"
                              onClick={() => { setSelectedDoctor(doc); setRejectModalOpen(true); }}
                              style={{
                                padding: '9px 18px',
                                borderRadius: '8px',
                                border: 'none',
                                background: '#DC2626',
                                color: '#FFFFFF',
                                fontSize: '0.84rem',
                                fontWeight: 700,
                                cursor: 'pointer',
                                boxShadow: '0 2px 6px rgba(220, 38, 38, 0.25)',
                              }}
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
              SECTION 4: DOCTOR ACTIVITY
          ========================================================================= */}
          {activeTab === 'activity' && (
            <div className="admin-panel-card" style={{ background: '#FFFFFF', borderRadius: '16px', border: '1px solid #DBEAFE', padding: '1.75rem', boxShadow: '0 2px 10px rgba(11, 31, 58, 0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#0B1F3A', fontWeight: 800 }}>
                    Doctor Clinical Activity Analytics
                  </h2>
                  <p style={{ margin: '4px 0 0', color: '#64748B', fontSize: '0.84rem' }}>
                    Overview of clinician login timestamps, total patient assessments, and generated risk predictions.
                  </p>
                </div>

                <input
                  type="text"
                  placeholder="Search doctor name, username, email…"
                  value={activitySearch}
                  onChange={(e) => setActivitySearch(e.target.value)}
                  style={{
                    padding: '8px 14px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    width: '300px',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
              </div>

              {activityLoading ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: '#64748B' }}>Loading activity logs…</div>
              ) : filteredActivities.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: '#94A3B8' }}>No clinician activity recorded.</div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.86rem' }}>
                    <thead>
                      <tr style={{ background: '#F8FAFC', borderBottom: '2px solid #E2E8F0', color: '#475569' }}>
                        <th style={{ padding: '12px 14px' }}>Physician</th>
                        <th style={{ padding: '12px 14px' }}>Username</th>
                        <th style={{ padding: '12px 14px' }}>Email</th>
                        <th style={{ padding: '12px 14px' }}>Last Login Timestamp</th>
                        <th style={{ padding: '12px 14px', textAlign: 'center' }}>Total Assessments</th>
                        <th style={{ padding: '12px 14px', textAlign: 'center' }}>Total Predictions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredActivities.map((act) => (
                        <tr key={act.doctor_id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                          <td style={{ padding: '12px 14px' }}>
                            <div style={{ fontWeight: 700, color: '#0B1F3A' }}>{act.full_name}</div>
                            <div style={{ fontSize: '0.78rem', color: '#64748B' }}>{act.medical_degree} &bull; {act.registration_number}</div>
                          </td>
                          <td style={{ padding: '12px 14px' }}>
                            {act.username ? (
                              <code style={{ background: '#EFF6FF', color: '#1565D8', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem' }}>
                                {act.username}
                              </code>
                            ) : (
                              <span style={{ color: '#94A3B8', fontSize: '0.78rem' }}>—</span>
                            )}
                          </td>
                          <td style={{ padding: '12px 14px', color: '#64748B' }}>
                            {act.email}
                          </td>
                          <td style={{ padding: '12px 14px', color: act.last_login ? '#0B1F3A' : '#94A3B8', fontWeight: act.last_login ? 600 : 400 }}>
                            {act.last_login ? formatDate(act.last_login) : 'Never logged in'}
                          </td>
                          <td style={{ padding: '12px 14px', textAlign: 'center', fontWeight: 800, color: '#1565D8', fontSize: '1.05rem' }}>
                            {act.total_assessments}
                          </td>
                          <td style={{ padding: '12px 14px', textAlign: 'center', fontWeight: 800, color: '#7C3AED', fontSize: '1.05rem' }}>
                            {act.total_predictions}
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
              SECTION 5: MODEL PERFORMANCE
          ========================================================================= */}
          {activeTab === 'performance' && (
            <div className="admin-panel-card" style={{ background: '#FFFFFF', borderRadius: '16px', border: '1px solid #DBEAFE', padding: '1.75rem', boxShadow: '0 2px 10px rgba(11, 31, 58, 0.04)' }}>
              <div style={{ marginBottom: '1.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <h2 style={{ margin: 0, fontSize: '1.35rem', color: '#0B1F3A', fontWeight: 800 }}>
                    Predictive Model Benchmark Validation
                  </h2>
                  <span style={{ background: '#EFF6FF', color: '#1565D8', border: '1px solid #BFDBFE', padding: '2px 8px', borderRadius: '12px', fontSize: '0.72rem', fontWeight: 700 }}>
                    10-Fold Stratified CV
                  </span>
                </div>
                <p style={{ margin: 0, color: '#64748B', fontSize: '0.86rem' }}>
                  Comparative statistical validation metrics for Logistic Regression (Baseline) versus Deep Artificial Neural Network (ANN 32-16).
                </p>
              </div>

              {/* Side-by-Side Model Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                {/* Logistic Regression Card */}
                <div style={{
                  border: '2px solid #93C5FD',
                  borderRadius: '14px',
                  padding: '1.5rem',
                  background: '#F8FAFC',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ background: '#DBEAFE', color: '#1565D8', padding: '4px 10px', borderRadius: '12px', fontSize: '0.74rem', fontWeight: 700 }}>
                      Baseline Linear Model
                    </span>
                    <span style={{ fontSize: '0.78rem', color: '#64748B', fontWeight: 600 }}>Scikit-Learn Pipeline</span>
                  </div>
                  <h3 style={{ margin: '12px 0 4px', fontSize: '1.25rem', color: '#0B1F3A', fontWeight: 800 }}>
                    Logistic Regression
                  </h3>
                  <p style={{ margin: '0 0 16px', fontSize: '0.82rem', color: '#64748B' }}>
                    StandardScaler &bull; L2 Ridge Regularization (C=1.0) &bull; Threshold 0.50
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>Accuracy</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#1565D8' }}>75.60%</div>
                      <div style={{ fontSize: '0.7rem', color: '#94A3B8' }}>± 6.87% CV std</div>
                    </div>

                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>ROC-AUC</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#1565D8' }}>77.17%</div>
                      <div style={{ fontSize: '0.7rem', color: '#94A3B8' }}>± 5.51% CV std</div>
                    </div>

                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>Precision</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0B1F3A' }}>67.55%</div>
                    </div>

                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>Sensitivity (Recall)</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0B1F3A' }}>48.11%</div>
                    </div>

                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>Specificity</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0B1F3A' }}>88.67%</div>
                    </div>

                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>F1-Score</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0B1F3A' }}>55.76%</div>
                    </div>
                  </div>
                </div>

                {/* Artificial Neural Network Card */}
                <div style={{
                  border: '2px solid #DDD6FE',
                  borderRadius: '14px',
                  padding: '1.5rem',
                  background: '#FDF4FF',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ background: '#EDE9FE', color: '#7C3AED', padding: '4px 10px', borderRadius: '12px', fontSize: '0.74rem', fontWeight: 700 }}>
                      Deep Learning Architecture
                    </span>
                    <span style={{ fontSize: '0.78rem', color: '#64748B', fontWeight: 600 }}>PyTorch (32-16)</span>
                  </div>
                  <h3 style={{ margin: '12px 0 4px', fontSize: '1.25rem', color: '#0B1F3A', fontWeight: 800 }}>
                    Artificial Neural Network
                  </h3>
                  <p style={{ margin: '0 0 16px', fontSize: '0.82rem', color: '#64748B' }}>
                    11 Inputs &bull; Dense 32 &bull; ReLU &bull; Dense 16 &bull; Sigmoid Output &bull; Dropout 0.2
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>Accuracy</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#7C3AED' }}>74.60%</div>
                      <div style={{ fontSize: '0.7rem', color: '#94A3B8' }}>± 7.12% CV std</div>
                    </div>

                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>ROC-AUC</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#7C3AED' }}>75.68%</div>
                      <div style={{ fontSize: '0.7rem', color: '#94A3B8' }}>± 6.30% CV std</div>
                    </div>

                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>Precision</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0B1F3A' }}>63.51%</div>
                    </div>

                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>Sensitivity (Recall)</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0B1F3A' }}>47.11%</div>
                    </div>

                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>Specificity</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0B1F3A' }}>87.67%</div>
                    </div>

                    <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <div style={{ fontSize: '0.74rem', color: '#64748B', fontWeight: 600 }}>F1-Score</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0B1F3A' }}>53.97%</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Visual Metric Comparison Bars */}
              <div style={{
                background: '#FFFFFF',
                borderRadius: '14px',
                border: '1px solid #E2E8F0',
                padding: '1.5rem',
                marginBottom: '1.75rem',
              }}>
                <h4 style={{ margin: '0 0 1.25rem', fontSize: '1.05rem', color: '#0B1F3A', fontWeight: 700 }}>
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
                      <span style={{ fontWeight: 700, color: '#0B1F3A' }}>{m.name}</span>
                      <span style={{ color: '#64748B', fontSize: '0.78rem' }}>{m.desc}</span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {/* LR Bar */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ width: '38px', fontSize: '0.72rem', fontWeight: 700, color: '#1565D8' }}>LR</span>
                        <div style={{ flex: 1, height: '8px', background: '#F1F5F9', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{ width: `${m.lr}%`, height: '100%', background: '#1565D8', borderRadius: '4px' }} />
                        </div>
                        <span style={{ width: '48px', textAlign: 'right', fontSize: '0.78rem', fontWeight: 700, color: '#1565D8' }}>{m.lr}%</span>
                      </div>

                      {/* ANN Bar */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ width: '38px', fontSize: '0.72rem', fontWeight: 700, color: '#7C3AED' }}>ANN</span>
                        <div style={{ flex: 1, height: '8px', background: '#F1F5F9', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{ width: `${m.ann}%`, height: '100%', background: '#7C3AED', borderRadius: '4px' }} />
                        </div>
                        <span style={{ width: '48px', textAlign: 'right', fontSize: '0.78rem', fontWeight: 700, color: '#7C3AED' }}>{m.ann}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────────
          MODAL 1: DOCTOR FULL PROFILE DETAIL MODAL
      ────────────────────────────────────────────────────────────────────────── */}
      {detailModalOpen && selectedDoctor && (
        <div className="admin-modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(11, 31, 58, 0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', zIndex: 100 }}>
          <div className="admin-modal-card" style={{ background: '#FFFFFF', borderRadius: '16px', maxWidth: '640px', width: '100%', maxHeight: '90vh', overflowY: 'auto', padding: '2rem', boxShadow: '0 20px 50px rgba(0,0,0,0.25)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid #E2E8F0', paddingBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.3rem', color: '#0B1F3A', fontWeight: 800 }}>
                  Physician Profile & Credentials
                </h3>
                <span style={{ fontSize: '0.78rem', color: '#64748B' }}>
                  Doctor ID: <code>{selectedDoctor.doctor_id}</code>
                </span>
              </div>
              <button
                type="button"
                onClick={() => setDetailModalOpen(false)}
                style={{ background: 'transparent', border: 'none', fontSize: '1.4rem', cursor: 'pointer', color: '#64748B' }}
              >
                &times;
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '0.86rem', color: '#334155' }}>
              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Full Name</span>
                <strong>{selectedDoctor.full_name}</strong>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>System Username</span>
                <code>{selectedDoctor.username || 'Not assigned yet'}</code>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Email Address</span>
                <span>{selectedDoctor.email}</span>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Mobile Number</span>
                <span>{selectedDoctor.mobile || '—'}</span>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Medical Degree</span>
                <span>{selectedDoctor.medical_degree}</span>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Registration Number</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{selectedDoctor.registration_number}</span>
              </div>

              <div style={{ gridColumn: 'span 2' }}>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Medical Council</span>
                <span>{selectedDoctor.registration_council}</span>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Email Verification</span>
                <span style={{ color: selectedDoctor.email_verified ? '#16A34A' : '#CA8A04', fontWeight: 700 }}>
                  {selectedDoctor.email_verified ? '✓ Verified' : '⚠ Unverified'}
                </span>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Verification Status</span>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: '10px',
                  fontSize: '0.74rem',
                  fontWeight: 800,
                  background: selectedDoctor.verification_status === 'APPROVED' ? '#DCFCE7' : selectedDoctor.verification_status === 'PENDING' ? '#FEF9C3' : '#FEE2E2',
                  color: selectedDoctor.verification_status === 'APPROVED' ? '#166534' : selectedDoctor.verification_status === 'PENDING' ? '#854D0E' : '#991B1B',
                }}>
                  {selectedDoctor.verification_status}
                </span>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Account Access</span>
                <span style={{ color: selectedDoctor.is_active ? '#1565D8' : '#DC2626', fontWeight: 700 }}>
                  {selectedDoctor.is_active ? 'Active' : 'Suspended'}
                </span>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Last Login</span>
                <span>{selectedDoctor.last_login ? formatDate(selectedDoctor.last_login) : 'Never logged in'}</span>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Registered On</span>
                <span>{formatDate(selectedDoctor.created_at)}</span>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Approved At</span>
                <span>{selectedDoctor.approved_at ? formatDate(selectedDoctor.approved_at) : '—'}</span>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Patient Assessments</span>
                <strong>{selectedDoctor.total_assessments ?? 0}</strong>
              </div>

              <div>
                <span style={{ color: '#64748B', fontSize: '0.76rem', display: 'block', textTransform: 'uppercase', fontWeight: 700 }}>Total Predictions</span>
                <strong>{selectedDoctor.total_predictions ?? 0}</strong>
              </div>
            </div>

            {selectedDoctor.rejection_reason && (
              <div style={{ marginTop: '1.25rem', padding: '12px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '8px', color: '#991B1B', fontSize: '0.84rem' }}>
                <strong>Rejection Reason:</strong> {selectedDoctor.rejection_reason}
              </div>
            )}

            <div style={{ marginTop: '1.75rem', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              {selectedDoctor.has_document && (
                <button
                  type="button"
                  onClick={() => { setDetailModalOpen(false); handleViewDocument(selectedDoctor); }}
                  style={{ padding: '8px 16px', borderRadius: '8px', border: '1px solid #CBD5E1', background: '#FFFFFF', color: '#1565D8', fontWeight: 600, cursor: 'pointer' }}
                >
                  📄 View Document
                </button>
              )}
              <button
                type="button"
                onClick={() => setDetailModalOpen(false)}
                style={{ padding: '8px 18px', borderRadius: '8px', border: 'none', background: '#0B1F3A', color: '#FFFFFF', fontWeight: 700, cursor: 'pointer' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          MODAL 2: APPROVE DOCTOR MODAL
      ────────────────────────────────────────────────────────────────────────── */}
      {approveModalOpen && selectedDoctor && (
        <div className="admin-modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(11, 31, 58, 0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', zIndex: 100 }}>
          <div className="admin-modal-card" style={{ background: '#FFFFFF', borderRadius: '16px', maxWidth: '480px', width: '100%', padding: '2rem', boxShadow: '0 20px 40px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 10px', color: '#0B1F3A', fontSize: '1.25rem', fontWeight: 800 }}>
              Approve Physician Credentials
            </h3>
            <p style={{ fontSize: '0.88rem', color: '#475569', lineHeight: '1.5', margin: '0 0 1rem' }}>
              Confirm approval for <strong>Dr. {selectedDoctor.full_name}</strong> ({selectedDoctor.medical_degree}, Reg No: <code>{selectedDoctor.registration_number}</code>).
            </p>
            <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '8px', padding: '12px', fontSize: '0.8rem', color: '#1E40AF', marginBottom: '1.25rem' }}>
              ✓ Status will be updated to <strong>APPROVED</strong><br />
              ✓ A unique portal username will be generated<br />
              ✓ An automated approval email with access details will be dispatched to <strong>{selectedDoctor.email}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setApproveModalOpen(false)}
                style={{ padding: '8px 16px', borderRadius: '8px', border: '1px solid #CBD5E1', background: '#FFFFFF', cursor: 'pointer', fontWeight: 600 }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApprove}
                disabled={actionInProgress}
                style={{
                  padding: '8px 18px',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#16A34A',
                  color: '#FFFFFF',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {actionInProgress ? 'Approving…' : 'Confirm & Dispatch Email'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          MODAL 3: REJECT DOCTOR MODAL
      ────────────────────────────────────────────────────────────────────────── */}
      {rejectModalOpen && selectedDoctor && (
        <div className="admin-modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(11, 31, 58, 0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', zIndex: 100 }}>
          <div className="admin-modal-card" style={{ background: '#FFFFFF', borderRadius: '16px', maxWidth: '480px', width: '100%', padding: '2rem', boxShadow: '0 20px 40px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 10px', color: '#DC2626', fontSize: '1.25rem', fontWeight: 800 }}>
              Reject Registration Application
            </h3>
            <p style={{ fontSize: '0.88rem', color: '#475569', margin: '0 0 1rem' }}>
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
                border: '1px solid #CBD5E1',
                fontSize: '0.88rem',
                fontFamily: 'inherit',
                outline: 'none',
              }}
            />
            <div style={{ fontSize: '0.78rem', color: '#64748B', marginTop: '6px', marginBottom: '1.25rem' }}>
              * This explanation will be recorded and dispatched directly to the doctor's registered email.
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setRejectModalOpen(false)}
                style={{ padding: '8px 16px', borderRadius: '8px', border: '1px solid #CBD5E1', background: '#FFFFFF', cursor: 'pointer', fontWeight: 600 }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReject}
                disabled={actionInProgress || !rejectionReason.trim()}
                style={{
                  padding: '8px 18px',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#DC2626',
                  color: '#FFFFFF',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {actionInProgress ? 'Rejecting…' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          MODAL 4: DOCUMENT VIEWER MODAL
      ────────────────────────────────────────────────────────────────────────── */}
      {documentModalOpen && (
        <div className="admin-modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(11, 31, 58, 0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', zIndex: 100 }}>
          <div className="admin-modal-card" style={{ background: '#FFFFFF', borderRadius: '16px', maxWidth: '780px', width: '100%', maxHeight: '90vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '1.25rem 1.75rem', borderBottom: '1px solid #E2E8F0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h4 style={{ margin: 0, color: '#0B1F3A', fontSize: '1.1rem', fontWeight: 700 }}>
                  Medical Registration Certificate
                </h4>
                <span style={{ fontSize: '0.78rem', color: '#64748B' }}>
                  {selectedDoctor?.full_name} &bull; Reg: {selectedDoctor?.registration_number}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setDocumentModalOpen(false)}
                style={{ background: 'transparent', border: 'none', fontSize: '1.4rem', cursor: 'pointer', color: '#64748B' }}
              >
                &times;
              </button>
            </div>
            <div style={{ flex: 1, padding: '1.5rem', overflowY: 'auto', textAlign: 'center', background: '#F8FAFC' }}>
              {documentLoading ? (
                <div style={{ padding: '3rem', color: '#64748B' }}>Loading document securely…</div>
              ) : documentUrl ? (
                <iframe
                  src={documentUrl}
                  title="Medical Registration Certificate"
                  style={{ width: '100%', height: '540px', border: '1px solid #E2E8F0', borderRadius: '8px', background: '#FFFFFF' }}
                />
              ) : (
                <div style={{ padding: '3rem', color: '#DC2626' }}>Document could not be previewed or file is missing.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
