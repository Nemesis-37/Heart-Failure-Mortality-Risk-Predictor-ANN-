import React, { useState } from 'react'
import DoctorLogin from './DoctorLogin.jsx'
import DoctorRegister from './DoctorRegister.jsx'
import DoctorOtpVerification from './DoctorOtpVerification.jsx'
import AdminDoctorVerification from './AdminDoctorVerification.jsx'
import DoctorDashboard from './DoctorDashboard.jsx'
import AppLayout from './layouts/AppLayout.jsx'
import DashboardHome from './pages/DashboardHome.jsx'
import PatientAssessmentsPage from './pages/PatientAssessmentsPage.jsx'
import ClinicalGuidePage from './pages/ClinicalGuidePage.jsx'
import PredictionHistoryPage from './pages/PredictionHistoryPage.jsx'
import ModelPerformancePage from './pages/ModelPerformancePage.jsx'
import PlaceholderPage from './pages/PlaceholderPage.jsx'

const DOCTOR_AUTH_KEY = 'hf_predictor_doctor_auth_v1'

export default function App() {
  const [doctorUser, setDoctorUser] = useState(() => {
    try {
      const stored = localStorage.getItem(DOCTOR_AUTH_KEY) || sessionStorage.getItem(DOCTOR_AUTH_KEY)
      if (stored) {
        return JSON.parse(stored)
      }
    } catch {
      // Ignore storage parse errors
    }
    return null
  })

  const [activePage, setActivePage] = useState('dashboard')
  const [selectedRecordForPrediction, setSelectedRecordForPrediction] = useState(null)
  const [authMode, setAuthMode] = useState('login')
  const [pendingDoctor, setPendingDoctor] = useState(null)

  const handleLogin = (profile, rememberMe) => {
    setDoctorUser(profile)
    setActivePage('dashboard')
    try {
      if (rememberMe) {
        localStorage.setItem(DOCTOR_AUTH_KEY, JSON.stringify(profile))
        sessionStorage.removeItem(DOCTOR_AUTH_KEY)
      } else {
        sessionStorage.setItem(DOCTOR_AUTH_KEY, JSON.stringify(profile))
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
        await fetch('http://127.0.0.1:8000/auth/logout', {
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
          onVerifiedSuccess={(res) => {
            // Keep on verification page to display success screen with instructions
          }}
          onNavigateToLogin={() => setAuthMode('login')}
        />
      )
    }

    if (authMode === 'admin') {
      return (
        <AdminDoctorVerification
          onExitAdmin={() => setAuthMode('login')}
        />
      )
    }

    return (
      <DoctorLogin
        onLogin={handleLogin}
        onNavigateToRegister={() => setAuthMode('register')}
        onNavigateToAdmin={() => setAuthMode('admin')}
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
          onSelectAssessment={(asmCode) => {
            setActivePage('assessments')
          }}
        />
      )}

      {activePage === 'performance' && (
        <ModelPerformancePage onNavigate={setActivePage} />
      )}
    </AppLayout>
  )
}
