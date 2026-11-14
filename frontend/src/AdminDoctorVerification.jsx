import React, { useState, useEffect } from 'react'

const ADMIN_TOKEN_KEY = 'cardiopredict_admin_token'
const ADMIN_PROFILE_KEY = 'cardiopredict_admin_profile'

export default function AdminDoctorVerification({ onExitAdmin }) {
  const [adminToken, setAdminToken] = useState(() => sessionStorage.getItem(ADMIN_TOKEN_KEY))
  const [adminProfile, setAdminProfile] = useState(() => {
    try {
      const p = sessionStorage.getItem(ADMIN_PROFILE_KEY)
      return p ? JSON.parse(p) : null
    } catch {
      return null
    }
  })

  // Admin login states
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [isLoggingIn, setIsLoggingIn] = useState(false)

  // Doctor list & review states
  const [doctors, setDoctors] = useState([])
  const [statusFilter, setStatusFilter] = useState('PENDING')
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [listError, setListError] = useState('')

  // Action modals
  const [selectedDoctor, setSelectedDoctor] = useState(null)
  const [documentModalOpen, setDocumentModalOpen] = useState(false)
  const [documentUrl, setDocumentUrl] = useState(null)
  const [documentLoading, setDocumentLoading] = useState(false)

  const [approveModalOpen, setApproveModalOpen] = useState(false)
  const [rejectModalOpen, setRejectModalOpen] = useState(false)
  const [rejectionReason, setRejectionReason] = useState('')
  const [actionInProgress, setActionInProgress] = useState(false)
  const [actionFeedback, setActionFeedback] = useState('')

  // Fetch doctors list whenever status filter changes
  useEffect(() => {
    if (adminToken) {
      fetchDoctors(statusFilter)
    }
  }, [adminToken, statusFilter])

  const handleAdminLogin = async (e) => {
    e.preventDefault()
    if (!loginUsername.trim() || !loginPassword) {
      setLoginError('Please enter administrator username and password.')
      return
    }

    setIsLoggingIn(true)
    setLoginError('')

    try {
      const res = await fetch('http://127.0.0.1:8000/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: loginUsername.trim(),
          password: loginPassword,
        }),
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Administrator login failed.')
      }

      setAdminToken(data.token)
      setAdminProfile(data.admin)
      sessionStorage.setItem(ADMIN_TOKEN_KEY, data.token)
      sessionStorage.setItem(ADMIN_PROFILE_KEY, JSON.stringify(data.admin))
    } catch (err) {
      setLoginError(err.message || 'Unable to connect to administration service.')
    } finally {
      setIsLoggingIn(false)
    }
  }

  const handleAdminLogout = () => {
    setAdminToken(null)
    setAdminProfile(null)
    sessionStorage.removeItem(ADMIN_TOKEN_KEY)
    sessionStorage.removeItem(ADMIN_PROFILE_KEY)
  }

  const fetchDoctors = async (status) => {
    setIsLoading(true)
    setListError('')
    try {
      const res = await fetch(`http://127.0.0.1:8000/admin/doctors?status_filter=${status}`, {
        headers: {
          Authorization: `Bearer ${adminToken}`,
        },
      })

      if (res.status === 401 || res.status === 403) {
        handleAdminLogout()
        throw new Error('Administrator session expired. Please sign in again.')
      }

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to fetch doctor registrations.')
      }

      setDoctors(data)
    } catch (err) {
      setListError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleViewDocument = async (doctor) => {
    setSelectedDoctor(doctor)
    setDocumentModalOpen(true)
    setDocumentLoading(true)
    setDocumentUrl(null)

    try {
      const res = await fetch(`http://127.0.0.1:8000/admin/doctors/${doctor.doctor_id}/document`, {
        headers: {
          Authorization: `Bearer ${adminToken}`,
        },
      })

      if (!res.ok) {
        throw new Error('Failed to retrieve medical registration document.')
      }

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      setDocumentUrl(url)
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
      const res = await fetch(`http://127.0.0.1:8000/admin/doctors/${selectedDoctor.doctor_id}/approve`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${adminToken}`,
        },
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Approval failed.')

      setApproveModalOpen(false)
      setActionFeedback(`Dr. ${selectedDoctor.full_name} has been APPROVED successfully.`)
      fetchDoctors(statusFilter)
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
      const res = await fetch(`http://127.0.0.1:8000/admin/doctors/${selectedDoctor.doctor_id}/reject`, {
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
      setActionFeedback(`Dr. ${selectedDoctor.full_name} has been REJECTED. Reason recorded.`)
      fetchDoctors(statusFilter)
    } catch (err) {
      setActionFeedback(`Error: ${err.message}`)
    } finally {
      setActionInProgress(false)
    }
  }

  const filteredDoctors = doctors.filter((doc) => {
    const q = searchQuery.toLowerCase()
    return (
      doc.full_name.toLowerCase().includes(q) ||
      doc.email.toLowerCase().includes(q) ||
      doc.registration_number.toLowerCase().includes(q) ||
      doc.registration_council.toLowerCase().includes(q)
    )
  })

  // -------------------------------------------------------------------------
  // Render: Administrator Login Form (if not authenticated)
  // -------------------------------------------------------------------------
  if (!adminToken) {
    return (
      <div className="login-page">
        <div className="login-left-panel">
          <div className="left-panel-bg-layer" aria-hidden="true" />
          <div className="left-panel-glow-1" aria-hidden="true" />
          <div className="left-panel-glow-2" aria-hidden="true" />

          <div className="left-panel-brand">
            <div className="brand-icon-shield">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
            <div className="brand-text-block">
              <span className="brand-name">CardioPredict SaaS</span>
              <span className="brand-edition">Credentialing Control Center</span>
            </div>
          </div>

          <div className="left-panel-body">
            <div className="left-badge-tag" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5' }}>
              <span>Restricted Administration</span>
            </div>

            <h1 className="left-panel-headline">
              Physician Credential Verification Governance
            </h1>

            <p className="left-panel-description">
              Medical safety protocols mandate that artificial neural network clinical tools
              can only be accessed by credentialed practitioners verified against official
              state and national medical registration registries.
            </p>
          </div>

          <div className="left-panel-footer">
            <span>Hospital Administrator Access Only &bull; Controlled Environment</span>
          </div>
        </div>

        <div className="login-right-panel" style={{ padding: '2.5rem 1.5rem' }}>
          <div className="login-form-wrapper" style={{ maxWidth: '460px' }}>
            <div className="login-form-card" style={{ padding: '2.5rem' }}>
              <div className="login-card-header">
                <span className="login-access-kicker" style={{ color: '#ef4444' }}>Staff Authorization</span>
                <h2 className="login-card-title" style={{ fontSize: '1.85rem' }}>Administrator Sign In</h2>
                <p className="login-card-subtitle" style={{ fontSize: '0.88rem' }}>
                  Enter your hospital administrative credentials to review pending doctor registrations.
                </p>
              </div>

              {loginError && (
                <div style={{
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: '10px',
                  padding: '0.85rem',
                  marginBottom: '1.25rem',
                  color: '#b91c1c',
                  fontSize: '0.85rem',
                }}>
                  {loginError}
                </div>
              )}

              <form onSubmit={handleAdminLogin} className="login-form">
                <div className="login-field-group">
                  <label className="login-field-label">Admin Username</label>
                  <div className="login-input-container">
                    <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                    <input
                      type="text"
                      className="login-input"
                      placeholder="e.g. admin"
                      value={loginUsername}
                      onChange={(e) => setLoginUsername(e.target.value)}
                      disabled={isLoggingIn}
                    />
                  </div>
                </div>

                <div className="login-field-group">
                  <label className="login-field-label">Password</label>
                  <div className="login-input-container">
                    <svg className="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                    <input
                      type="password"
                      className="login-input"
                      placeholder="Administrator password"
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      disabled={isLoggingIn}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="btn-login-primary"
                  disabled={isLoggingIn}
                  style={{ width: '100%', marginTop: '0.5rem' }}
                >
                  {isLoggingIn ? 'Signing In...' : 'Sign In as Administrator'}
                </button>

                <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.85rem' }}>
                  <button
                    type="button"
                    onClick={onExitAdmin}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#1565D8',
                      cursor: 'pointer',
                      textDecoration: 'underline',
                    }}
                  >
                    &larr; Return to Clinical Doctor Portal
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // -------------------------------------------------------------------------
  // Render: Authenticated Administrator Dashboard
  // -------------------------------------------------------------------------
  return (
    <div style={{ minHeight: '100vh', background: '#F3F7FC', padding: '2rem 2.5rem' }}>
      {/* Top Navigation Bar */}
      <div style={{
        background: '#ffffff',
        borderRadius: '16px',
        padding: '1.25rem 2rem',
        border: '1px solid #DBEAFE',
        boxShadow: '0 4px 14px rgba(11, 31, 58, 0.05)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '2rem',
        flexWrap: 'wrap',
        gap: '1rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #0B1F3A 0%, #1565D8 100%)',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 800, color: '#0B1F3A' }}>
              Physician Credential Review Board
            </h2>
            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
              Medical License Verification & Registry Governance
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            background: '#EFF6FF',
            border: '1px solid #BFDBFE',
            padding: '6px 14px',
            borderRadius: '10px',
            fontSize: '0.82rem',
            color: '#1565D8',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <strong>{adminProfile?.full_name || 'Administrator'}</strong> &bull; {adminProfile?.role || 'Credentialing Officer'}
          </div>

          <button
            type="button"
            onClick={handleAdminLogout}
            style={{
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              padding: '7px 16px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: 600,
              color: '#64748b',
              cursor: 'pointer',
            }}
          >
            Sign Out
          </button>

          {onExitAdmin && (
            <button
              type="button"
              onClick={onExitAdmin}
              style={{
                background: '#1565D8',
                border: 'none',
                padding: '7px 16px',
                borderRadius: '8px',
                fontSize: '0.82rem',
                fontWeight: 600,
                color: '#ffffff',
                cursor: 'pointer',
              }}
            >
              Exit to App
            </button>
          )}
        </div>
      </div>

      {/* Action Feedback Banner */}
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
          fontSize: '0.9rem',
          fontWeight: 600,
        }}>
          <span>{actionFeedback}</span>
          <button
            type="button"
            onClick={() => setActionFeedback('')}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#1565D8', fontSize: '1.2rem' }}
          >
            &times;
          </button>
        </div>
      )}

      {/* Controls & Filter Tabs */}
      <div style={{
        background: '#ffffff',
        borderRadius: '16px',
        padding: '1.25rem 1.75rem',
        border: '1px solid #DBEAFE',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
      }}>
        {/* Filter Pills */}
        <div style={{ display: 'flex', gap: '0.5rem', background: '#F1F5F9', padding: '4px', borderRadius: '10px' }}>
          {['PENDING', 'APPROVED', 'REJECTED', 'ALL'].map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setStatusFilter(tab)}
              style={{
                padding: '6px 16px',
                borderRadius: '8px',
                fontSize: '0.8rem',
                fontWeight: 700,
                border: 'none',
                cursor: 'pointer',
                background: statusFilter === tab ? '#1565D8' : 'transparent',
                color: statusFilter === tab ? '#ffffff' : '#64748b',
                transition: 'all 150ms ease',
              }}
            >
              {tab === 'PENDING' ? 'Pending Review' : tab}
            </button>
          ))}
        </div>

        {/* Search */}
        <div style={{ position: 'relative', width: '320px' }}>
          <input
            type="text"
            placeholder="Search name, email, or reg #..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px 8px 36px',
              borderRadius: '8px',
              border: '1.5px solid #cbd5e1',
              fontSize: '0.85rem',
              outline: 'none',
            }}
          />
          <svg
            style={{ position: 'absolute', left: '12px', top: '10px', color: '#94a3b8' }}
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </div>
      </div>

      {/* Doctor Registrations Table */}
      <div style={{
        background: '#ffffff',
        borderRadius: '16px',
        border: '1px solid #DBEAFE',
        overflow: 'hidden',
        boxShadow: '0 4px 14px rgba(11, 31, 58, 0.03)',
      }}>
        {isLoading ? (
          <div style={{ padding: '4rem', textAlign: 'center', color: '#64748b' }}>
            <span>Loading registered doctor credentials&hellip;</span>
          </div>
        ) : filteredDoctors.length === 0 ? (
          <div style={{ padding: '4rem', textAlign: 'center', color: '#64748b' }}>
            <p style={{ fontSize: '1rem', fontWeight: 600, margin: 0 }}>No doctor registrations found</p>
            <span style={{ fontSize: '0.85rem' }}>No records match filter: {statusFilter}</span>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="assessments-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th>Physician Information</th>
                  <th>Medical Credentials</th>
                  <th>Contact Info</th>
                  <th>Email Verification</th>
                  <th>Credential Status</th>
                  <th>Evidence Document</th>
                  <th style={{ textAlign: 'right', paddingRight: '2rem' }}>Administrative Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredDoctors.map((doc) => (
                  <tr key={doc.doctor_id} className="table-data-row">
                    {/* Physician Name & Degree */}
                    <td>
                      <div style={{ fontWeight: 700, color: '#0B1F3A', fontSize: '0.92rem' }}>
                        {doc.full_name}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
                        {doc.medical_degree}
                      </div>
                    </td>

                    {/* Reg Number & Council */}
                    <td>
                      <div style={{
                        fontFamily: 'Consolas, monospace',
                        fontWeight: 700,
                        fontSize: '0.82rem',
                        color: '#1565D8',
                      }}>
                        {doc.registration_number}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        {doc.registration_council}
                      </div>
                    </td>

                    {/* Email & Phone */}
                    <td>
                      <div style={{ fontSize: '0.82rem', color: '#334155' }}>{doc.email}</div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{doc.mobile}</div>
                    </td>

                    {/* Email Verified Badge */}
                    <td>
                      {doc.email_verified ? (
                        <span style={{
                          background: '#dcfce7',
                          color: '#15803d',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}>
                          ✓ VERIFIED
                        </span>
                      ) : (
                        <span style={{
                          background: '#fef3c7',
                          color: '#b45309',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                        }}>
                          ⏳ UNVERIFIED
                        </span>
                      )}
                    </td>

                    {/* Verification Status Badge */}
                    <td>
                      {doc.verification_status === 'APPROVED' ? (
                        <span style={{
                          background: '#dcfce7',
                          color: '#15803d',
                          padding: '4px 10px',
                          borderRadius: '8px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                        }}>
                          APPROVED
                        </span>
                      ) : doc.verification_status === 'REJECTED' ? (
                        <div>
                          <span style={{
                            background: '#fee2e2',
                            color: '#b91c1c',
                            padding: '4px 10px',
                            borderRadius: '8px',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                          }}>
                            REJECTED
                          </span>
                          {doc.rejection_reason && (
                            <div style={{ fontSize: '0.72rem', color: '#b91c1c', marginTop: '4px', maxWidth: '160px' }}>
                              {doc.rejection_reason}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span style={{
                          background: '#fef3c7',
                          color: '#b45309',
                          padding: '4px 10px',
                          borderRadius: '8px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                        }}>
                          PENDING REVIEW
                        </span>
                      )}
                    </td>

                    {/* Evidence Document Preview */}
                    <td>
                      {doc.has_document ? (
                        <button
                          type="button"
                          onClick={() => handleViewDocument(doc)}
                          style={{
                            background: '#EFF6FF',
                            border: '1px solid #93C5FD',
                            color: '#1565D8',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                          <span>View Proof</span>
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic' }}>
                          No document
                        </span>
                      )}
                    </td>

                    {/* Actions */}
                    <td style={{ textAlign: 'right', paddingRight: '1.5rem' }}>
                      <div style={{ display: 'inline-flex', gap: '0.5rem' }}>
                        {doc.verification_status !== 'APPROVED' && (
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedDoctor(doc)
                              setApproveModalOpen(true)
                            }}
                            style={{
                              background: '#16a34a',
                              color: '#ffffff',
                              border: 'none',
                              padding: '5px 12px',
                              borderRadius: '6px',
                              fontSize: '0.78rem',
                              fontWeight: 700,
                              cursor: 'pointer',
                            }}
                          >
                            Approve
                          </button>
                        )}

                        {doc.verification_status !== 'REJECTED' && (
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedDoctor(doc)
                              setRejectModalOpen(true)
                            }}
                            style={{
                              background: '#ef4444',
                              color: '#ffffff',
                              border: 'none',
                              padding: '5px 12px',
                              borderRadius: '6px',
                              fontSize: '0.78rem',
                              fontWeight: 700,
                              cursor: 'pointer',
                            }}
                          >
                            Reject
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ───── DOCUMENT PREVIEW MODAL ───── */}
      {documentModalOpen && selectedDoctor && (
        <div className="clinical-modal-backdrop" onClick={() => setDocumentModalOpen(false)}>
          <div
            className="clinical-modal-content"
            style={{ width: '90%', maxWidth: '800px', height: '80vh', padding: '1.5rem' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#0B1F3A' }}>
                  Medical Registration Evidence &bull; {selectedDoctor.full_name}
                </h3>
                <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                  Council: {selectedDoctor.registration_council} &bull; Reg #{selectedDoctor.registration_number}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setDocumentModalOpen(false)}
                style={{ background: 'transparent', border: 'none', fontSize: '1.4rem', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>

            <div style={{ flex: 1, background: '#f8fafc', borderRadius: '10px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {documentLoading ? (
                <span>Retrieving document securely from encrypted vault&hellip;</span>
              ) : documentUrl ? (
                <iframe
                  src={documentUrl}
                  title="Document Preview"
                  style={{ width: '100%', height: '100%', border: 'none' }}
                />
              ) : (
                <span style={{ color: '#ef4444' }}>Unable to preview document file.</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ───── APPROVE CONFIRMATION MODAL ───── */}
      {approveModalOpen && selectedDoctor && (
        <div className="clinical-modal-backdrop" onClick={() => setApproveModalOpen(false)}>
          <div
            className="clinical-modal-content form-modal-style"
            style={{ maxWidth: '480px', padding: '2rem' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#0B1F3A' }}>
              Approve Doctor Credentials?
            </h3>
            <p style={{ fontSize: '0.88rem', color: '#64748b', lineHeight: 1.5, margin: '1rem 0 1.5rem' }}>
              Are you sure you wish to grant full clinical access to <strong>Dr. {selectedDoctor.full_name}</strong>?
              You confirm that their medical registration number <strong>{selectedDoctor.registration_number}</strong> has been
              verified with <strong>{selectedDoctor.registration_council}</strong>.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setApproveModalOpen(false)}
                disabled={actionInProgress}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-login-primary"
                onClick={handleApprove}
                disabled={actionInProgress}
                style={{ background: '#16a34a' }}
              >
                {actionInProgress ? 'Approving...' : 'Confirm Approval'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ───── REJECT REASON MODAL ───── */}
      {rejectModalOpen && selectedDoctor && (
        <div className="clinical-modal-backdrop" onClick={() => setRejectModalOpen(false)}>
          <div
            className="clinical-modal-content form-modal-style"
            style={{ maxWidth: '520px', padding: '2rem' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#0B1F3A' }}>
              Reject Doctor Registration
            </h3>
            <p style={{ fontSize: '0.88rem', color: '#64748b', lineHeight: 1.5, margin: '0.5rem 0 1rem' }}>
              Provide the reason for rejecting <strong>Dr. {selectedDoctor.full_name}</strong>'s registration.
              This reason will be recorded in the audit log.
            </p>

            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#334155', display: 'block', marginBottom: '0.35rem' }}>
                Rejection Reason *
              </label>
              <textarea
                rows={3}
                placeholder="e.g. License registration could not be verified on the national council registry."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                style={{
                  width: '100%',
                  borderRadius: '8px',
                  border: '1.5px solid #cbd5e1',
                  padding: '8px 12px',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setRejectModalOpen(false)}
                disabled={actionInProgress}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-login-primary"
                onClick={handleReject}
                disabled={actionInProgress || !rejectionReason.trim()}
                style={{ background: '#ef4444' }}
              >
                {actionInProgress ? 'Rejecting...' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
