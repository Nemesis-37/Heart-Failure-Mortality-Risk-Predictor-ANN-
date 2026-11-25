import React, { useState, useEffect } from 'react'
import UnifiedLogin from './UnifiedLogin.jsx'
import DoctorRegister from './DoctorRegister.jsx'
import DoctorOtpVerification from './DoctorOtpVerification.jsx'
import AdminDashboard from './AdminDashboard.jsx'
import DoctorDashboard from './DoctorDashboard.jsx'
import AppLayout from './layouts/AppLayout.jsx'
import DashboardHome from './pages/DashboardHome.jsx'
import PatientAssessmentsPage from './pages/PatientAssessmentsPage.jsx'
import ClinicalGuidePage from './pages/ClinicalGuidePage.jsx'
import PredictionHistoryPage from './pages/PredictionHistoryPage.jsx'
import HeartHealthCounsellingPage from './pages/HeartHealthCounsellingPage.jsx'
import { apiUrl } from './apiConfig.js'

const DOCTOR_AUTH_KEY = 'hf_predictor_doctor_auth_v1'

export default function App() {
  const [doctorUser, setDoctorUser] = useState(() => {
    try {
      const stored = localStorage.getItem(DOCTOR_AUTH_KEY) || sessionStorage.getItem(DOCTOR_AUTH_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        const localSavedPhoto =
          localStorage.getItem('cardiopredict_doctor_profile_photo') ||
          localStorage.getItem('cardiopredict_doctor_profile_photo_base64') ||
          (parsed?.email ? localStorage.getItem(`cardiopredict_photo_${parsed.email}`) : null)
        if (localSavedPhoto) {
          parsed.profilePhotoUrl = parsed.profilePhotoUrl || localSavedPhoto
          parsed.profile_photo_url = parsed.profile_photo_url || localSavedPhoto
        }
        return parsed
      }
    } catch {
      // Ignore storage parse errors
    }
    return null
  })

  const [activePage, setActivePage] = useState('dashboard')
  const [selectedRecordForPrediction, setSelectedRecordForPrediction] = useState(null)
  const [authMode, setAuthMode] = useState(() =>
    sessionStorage.getItem('cardiopredict_admin_token') ? 'admin' : 'login',
  )
  const [pendingDoctor, setPendingDoctor] = useState(null)

  // Sync latest doctor profile (including profile photo) on mount if logged in
  useEffect(() => {
    const token = localStorage.getItem('cardiopredict_access_token')
    if (token && doctorUser) {
      fetch(apiUrl('/auth/me'), {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data) {
            const localSavedPhoto =
              localStorage.getItem('cardiopredict_doctor_profile_photo') ||
              localStorage.getItem('cardiopredict_doctor_profile_photo_base64') ||
              localStorage.getItem(`cardiopredict_photo_${data.email}`)
            const finalPhoto =
              data.profile_photo_url ||
              localSavedPhoto ||
              doctorUser?.profilePhotoUrl ||
              doctorUser?.profile_photo_url ||
              null
            handleUpdateDoctorUser({
              name: data.full_name,
              email: data.email,
              role: data.role || 'Attending Physician',
              licenseNumber: data.license_number,
              specialty: data.specialty,
              profilePhotoUrl: finalPhoto,
              profile_photo_url: finalPhoto,
            })
          }
        })
        .catch(() => {})
    }
  }, [])

  const handleUpdateDoctorUser = (updatedFields) => {
    setDoctorUser((prev) => {
      if (!prev) return null
      const merged = { ...prev, ...updatedFields }
      try {
        if (localStorage.getItem(DOCTOR_AUTH_KEY)) {
          localStorage.setItem(DOCTOR_AUTH_KEY, JSON.stringify(merged))
        } else if (sessionStorage.getItem(DOCTOR_AUTH_KEY)) {
          sessionStorage.setItem(DOCTOR_AUTH_KEY, JSON.stringify(merged))
        }
      } catch {
        // Storage fallback
      }
      return merged
    })
  }

  const handleLogin = (role, profile, authResponse, rememberMe) => {
    if (role === 'ADMIN') {
      sessionStorage.setItem('cardiopredict_admin_token', authResponse.access_token)
      sessionStorage.setItem('cardiopredict_admin_profile', JSON.stringify(profile))
      localStorage.removeItem(DOCTOR_AUTH_KEY)
      sessionStorage.removeItem(DOCTOR_AUTH_KEY)
      localStorage.removeItem('cardiopredict_access_token')
      localStorage.removeItem('cardiopredict_refresh_token')
      localStorage.removeItem('cardiopredict_current_doctor')
      setDoctorUser(null)
      setAuthMode('admin')
      return
    }

    const localSavedPhoto =
      localStorage.getItem('cardiopredict_doctor_profile_photo') ||
      (profile?.email ? localStorage.getItem(`cardiopredict_photo_${profile.email}`) : null)
    const effectiveProfile = {
      ...profile,
      profilePhotoUrl: profile?.profilePhotoUrl || profile?.profile_photo_url || localSavedPhoto || null,
      profile_photo_url: profile?.profile_photo_url || profile?.profilePhotoUrl || localSavedPhoto || null,
    }

    setDoctorUser(effectiveProfile)
    setActivePage('dashboard')
    try {
      sessionStorage.removeItem('cardiopredict_admin_token')
      sessionStorage.removeItem('cardiopredict_admin_profile')
      if (rememberMe) {
        localStorage.setItem(DOCTOR_AUTH_KEY, JSON.stringify(effectiveProfile))
        sessionStorage.removeItem(DOCTOR_AUTH_KEY)
      } else {
        sessionStorage.setItem(DOCTOR_AUTH_KEY, JSON.stringify(effectiveProfile))
        localStorage.removeItem(DOCTOR_AUTH_KEY)
      }
    } catch {
      // Storage unavailable fallback
    }
  }

  const handleLogout = async () => {
    const refreshToken = localStorage.getItem('cardiopredict_refresh_token')
    if (refreshToken) {
      try {
        await fetch(apiUrl('/auth/logout'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
      } catch (err) {
        console.warn('Backend logout revocation notice:', err)
      }
    }

    setDoctorUser(null)
    setActivePage('dashboard')
    setSelectedRecordForPrediction(null)
    try {
      localStorage.removeItem(DOCTOR_AUTH_KEY)
      sessionStorage.removeItem(DOCTOR_AUTH_KEY)
      localStorage.removeItem('cardiopredict_access_token')
      localStorage.removeItem('cardiopredict_refresh_token')
      localStorage.removeItem('cardiopredict_current_doctor')
      sessionStorage.removeItem('cardiopredict_admin_token')
      sessionStorage.removeItem('cardiopredict_admin_profile')
    } catch {
      // Storage unavailable fallback
    }
  }

  const handleSelectRecordForPrediction = (record) => {
    setSelectedRecordForPrediction(record)
    setActivePage('prediction')
  }

  if (!doctorUser) {
    if (authMode === 'register') {
      return (
        <DoctorRegister
          onNavigateToLogin={() => setAuthMode('login')}
          onRegisterSuccess={(doctor) => {
            setPendingDoctor(doctor)
            setAuthMode('otp')
          }}
        />
      )
    }

    if (authMode === 'otp') {
      return (
        <DoctorOtpVerification
          email={pendingDoctor?.email || ''}
          doctorData={pendingDoctor}
          onVerifiedSuccess={() => {
            // Keep on verification page to display success screen with instructions
          }}
          onNavigateToLogin={() => setAuthMode('login')}
        />
      )
    }

    if (authMode === 'admin') {
      return (
        <AdminDashboard
          onExitAdmin={() => setAuthMode('login')}
        />
      )
    }

    return (
      <UnifiedLogin
        onLogin={handleLogin}
        onNavigateToRegister={() => setAuthMode('register')}
      />
    )
  }

  return (
    <AppLayout
      doctorUser={doctorUser}
      onLogout={handleLogout}
      activePage={activePage}
      onNavigate={(page) => {
        if (page !== 'prediction') {
          setSelectedRecordForPrediction(null)
        }
        setActivePage(page)
      }}
      onUpdateDoctorUser={handleUpdateDoctorUser}
    >
      {activePage === 'dashboard' && (
        <DashboardHome doctorUser={doctorUser} onNavigate={setActivePage} />
      )}

      {activePage === 'prediction' && (
        <DoctorDashboard
          key={selectedRecordForPrediction ? selectedRecordForPrediction.id : 'default-pred'}
          doctorUser={doctorUser}
          onLogout={handleLogout}
          embedded={true}
          initialRecord={selectedRecordForPrediction}
          onUpdateDoctorUser={handleUpdateDoctorUser}
        />
      )}

      {activePage === 'assessments' && (
        <PatientAssessmentsPage
          doctorUser={doctorUser}
          onNavigate={setActivePage}
          onSelectForPrediction={handleSelectRecordForPrediction}
        />
      )}

      {activePage === 'parameters' && (
        <ClinicalGuidePage onNavigate={setActivePage} />
      )}

      {activePage === 'history' && (
        <PredictionHistoryPage
          doctorUser={doctorUser}
          onNavigate={setActivePage}
          onSelectAssessment={() => {
            setActivePage('assessments')
          }}
        />
      )}

      {activePage === 'counselling' && (
        <HeartHealthCounsellingPage onNavigate={setActivePage} />
      )}
    </AppLayout>
  )
}
