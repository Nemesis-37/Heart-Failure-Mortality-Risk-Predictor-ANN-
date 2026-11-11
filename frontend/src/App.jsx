import React, { useState, useEffect } from 'react'
import DoctorLogin from './DoctorLogin.jsx'
import DoctorDashboard from './DoctorDashboard.jsx'

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

  const handleLogin = (profile, rememberMe) => {
    setDoctorUser(profile)
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

  const handleLogout = () => {
    setDoctorUser(null)
    try {
      localStorage.removeItem(DOCTOR_AUTH_KEY)
      sessionStorage.removeItem(DOCTOR_AUTH_KEY)
    } catch {
      // Storage unavailable fallback
    }
  }

  if (!doctorUser) {
    return <DoctorLogin onLogin={handleLogin} />
  }

  return <DoctorDashboard doctorUser={doctorUser} onLogout={handleLogout} />
}
