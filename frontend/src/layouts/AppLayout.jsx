import React, { useState, useEffect } from 'react'

export default function AppLayout({
  doctorUser,
  onLogout,
  activePage,
  onNavigate,
  children,
}) {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')

  // Clean doctor name to prevent duplicate "Dr. Dr" prefixes
  const cleanDoctorName = (doctorUser?.name || 'Doctor')
    .replace(/^Dr\.\s*Dr\.\s*/i, 'Dr. ')
    .replace(/^Dr\.\s*Dr\b/i, 'Dr. ')

  const cleanRole = doctorUser?.role || 'Attending Physician'

  const avatarInitials =
    doctorUser?.avatarInitials ||
    cleanDoctorName
      .replace(/^Dr\.\s*/i, '')
      .trim()
      .split(/\s+/)
      .map((w) => w[0])
      .join('')
      .slice(0, 2)
      .toUpperCase() ||
    'DR'

  // Health check on mount and interval
  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const checkHealth = async () => {
    setBackendStatus('checking')
    try {
      const response = await fetch('/api/health')
      if (response.ok) {
        setBackendStatus('online')
        return
      }
    } catch {
      // Fallback probe direct to local FastAPI backend
    }

    try {
      const response = await fetch('http://127.0.0.1:8000/health')
      setBackendStatus(response.ok ? 'online' : 'offline')
    } catch {
      setBackendStatus('offline')
    }
  }

  const handleNavClick = (pageId) => {
    onNavigate(pageId)
    setMobileMenuOpen(false)
  }

  const navItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
        </svg>
      ),
      badge: null,
    },
    {
      id: 'prediction',
      label: 'New Prediction',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      ),
      badge: 'Dual Model',
    },
    {
      id: 'assessments',
      label: 'Patient Assessments',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
          <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
          <path d="M9 14h6" />
          <path d="M9 18h6" />
          <path d="M9 10h6" />
        </svg>
      ),
      badge: null,
    },
    {
      id: 'parameters',
      label: 'Clinical Parameters Guide',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          <line x1="9" y1="7" x2="15" y2="7" />
          <line x1="9" y1="11" x2="15" y2="11" />
        </svg>
      ),
      badge: '11 Biomarkers',
    },
    {
      id: 'history',
      label: 'Prediction History',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      ),
      badge: null,
    },
    {
      id: 'performance',
      label: 'Model Performance',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
      ),
      badge: 'LR vs ANN',
    },
  ]

  const getPageTitle = () => {
    switch (activePage) {
      case 'dashboard':
        return 'Clinical Dashboard'
      case 'prediction':
        return 'Heart Failure Risk Prediction'
      case 'assessments':
        return 'Patient Assessments'
      case 'parameters':
        return 'Clinical Parameters Guide'
      case 'history':
        return 'Prediction History'
      case 'performance':
        return 'Model Performance'
      default:
        return 'Clinical Decision Support'
    }
  }

  const getPageSubtitle = () => {
    switch (activePage) {
      case 'dashboard':
        return 'Overview of clinical risk assessments and predictive analytics'
      case 'prediction':
        return 'Enter clinical parameters to generate a model-based prediction.'
      case 'assessments':
        return 'View and manage recorded clinical assessment details.'
      case 'parameters':
        return 'Understand the clinical measurements and variables used by the prediction models.'
      case 'history':
        return 'Review previous assessments and model-generated prediction results.'
      case 'performance':
        return 'Evaluation and comparison of trained prediction models.'
      default:
        return 'Clinical Decision Support Workspace'
    }
  }

  return (
    <div className={`app-layout ${collapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Mobile Drawer Backdrop */}
      {mobileMenuOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Left Application Sidebar */}
      <aside className={`sidebar ${mobileMenuOpen ? 'open' : ''}`} aria-label="Main Navigation">
        {/* Sidebar Brand Header */}
        <div className="sidebar-header">
          <div className="sidebar-brand" onClick={() => handleNavClick('dashboard')} role="button" tabIndex={0}>
            <div className="sidebar-brand-icon" aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
              </svg>
            </div>
            {!collapsed && (
              <div className="sidebar-brand-text">
                <span className="brand-name">HF Risk Predictor</span>
                <span className="brand-tag">Clinical Intelligence</span>
              </div>
            )}
          </div>

          {/* Desktop Collapse Toggle */}
          <button
            type="button"
            className="sidebar-collapse-btn"
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            aria-label={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ transform: collapsed ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 200ms ease' }}
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        </div>

        {/* Sidebar Navigation */}
        <nav className="sidebar-nav">
          <div className="sidebar-section-title">
            {!collapsed ? <span>Clinical Navigation</span> : <span className="section-divider-dot" />}
          </div>

          {navItems.map((item) => {
            const isActive = activePage === item.id
            return (
              <button
                key={item.id}
                type="button"
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => handleNavClick(item.id)}
                title={collapsed ? item.label : undefined}
                aria-current={isActive ? 'page' : undefined}
              >
                <span className="nav-item-icon" aria-hidden="true">
                  {item.icon}
                </span>
                {!collapsed && (
                  <>
                    <span className="nav-item-label">{item.label}</span>
                    {item.badge && <span className="nav-item-badge">{item.badge}</span>}
                  </>
                )}
                {isActive && <span className="active-indicator" aria-hidden="true" />}
              </button>
            )
          })}
        </nav>

        {/* Sidebar Footer / Physician Profile & Logout */}
        <div className="sidebar-footer">
          {!collapsed ? (
            <div className="sidebar-doctor-card">
              <div className="doctor-avatar-small" aria-hidden="true">
                {avatarInitials}
              </div>
              <div className="sidebar-doctor-meta">
                <span className="doctor-display-name" title={cleanDoctorName}>
                  {cleanDoctorName}
                </span>
                <span className="doctor-display-role">{cleanRole}</span>
              </div>
            </div>
          ) : (
            <div className="doctor-avatar-collapsed" title={`${cleanDoctorName} (${cleanRole})`} aria-hidden="true">
              {avatarInitials}
            </div>
          )}

          <button
            type="button"
            className="sidebar-logout-btn"
            onClick={onLogout}
            title="Sign out of clinical workspace"
            aria-label="Logout"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            {!collapsed && <span>Sign Out</span>}
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="app-main-wrapper">
        {/* Top Header Bar */}
        <header className="app-top-header">
          <div className="header-left">
            {/* Mobile Hamburger Toggle */}
            <button
              type="button"
              className="mobile-hamburger-btn"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open Navigation Drawer"
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>

            <div className="header-title-block">
              <div className="header-title-row">
                <h1 className="header-page-title">{getPageTitle()}</h1>
                <span className="header-env-badge">Clinical Mode</span>
              </div>
              <p className="header-page-subtitle">{getPageSubtitle()}</p>
            </div>
          </div>

          <div className="header-right">
            {/* Fast Action: New Assessment */}
            {activePage !== 'prediction' && (
              <button
                type="button"
                className="header-quick-action-btn"
                onClick={() => handleNavClick('prediction')}
                title="Launch patient risk assessment form"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                <span>New Prediction</span>
              </button>
            )}

            {/* API Health Status Indicator */}
            <button
              type="button"
              className={`header-status-pill ${backendStatus}`}
              onClick={checkHealth}
              title={`Inference API is ${backendStatus}. Click to refresh health check.`}
              aria-label={`API Status: ${backendStatus}. Click to refresh.`}
            >
              <span className={`status-pulse-dot ${backendStatus}`} aria-hidden="true" />
              <span className="status-label-text">
                {backendStatus === 'online'
                  ? 'API Online'
                  : backendStatus === 'offline'
                  ? 'API Offline'
                  : 'Checking…'}
              </span>
            </button>

            {/* Doctor Profile Header Pill */}
            <div className="header-doctor-pill" title={`${cleanDoctorName} — ${cleanRole}`}>
              <div className="header-doctor-avatar" aria-hidden="true">
                {avatarInitials}
              </div>
              <div className="header-doctor-info">
                <span className="header-doctor-name">{cleanDoctorName}</span>
                <span className="header-doctor-role">{cleanRole}</span>
              </div>
            </div>
          </div>
        </header>

        {/* Dynamic Page Content */}
        <main className="app-content-body">
          {children}
        </main>

        {/* Global Footer */}
        <footer className="app-global-footer">
          <p>
            Heart Failure Mortality Risk Predictor &bull; Clinical Decision Support Workspace &bull; Educational Machine Learning Research Prototype
          </p>
        </footer>
      </div>
    </div>
  )
}
