
import React, { useState, useEffect } from 'react'

const INITIAL_STATE = {
  age: '60',
  anaemia: 0,
  creatinine_phosphokinase: '250',
  diabetes: 0,
  ejection_fraction: '38',
  high_blood_pressure: 0,
  platelets: '260000',
  serum_creatinine: '1.1',
  serum_sodium: '137',
  sex: 1,
  smoking: 0,
}

const PRESET_LOW_RISK = {
  ...INITIAL_STATE,
  age: '50',
  creatinine_phosphokinase: '168',
  ejection_fraction: '45',
  platelets: '276000',
  serum_creatinine: '0.9',
  serum_sodium: '140',
}

const PRESET_HIGH_RISK = {
  ...INITIAL_STATE,
  age: '75',
  anaemia: 1,
  creatinine_phosphokinase: '582',
  diabetes: 1,
  ejection_fraction: '20',
  high_blood_pressure: 1,
  platelets: '265000',
  serum_creatinine: '2.5',
  serum_sodium: '130',
  smoking: 1,
}

export default function App() {
  const [formData, setFormData] = useState(INITIAL_STATE)
  const [fieldErrors, setFieldErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState(null)
  const [result, setResult] = useState(null)
  const [backendStatus, setBackendStatus] = useState('checking')

  useEffect(() => {
    checkHealth()
  }, [])

  const checkHealth = async () => {
    try {
      const response = await fetch('/api/health')
      setBackendStatus(response.ok ? 'online' : 'offline')
    } catch {
      try {
        const response = await fetch('http://127.0.0.1:8000/health')
        setBackendStatus(response.ok ? 'online' : 'offline')
      } catch {
        setBackendStatus('offline')
      }
    }
  }

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))

    setFieldErrors(prev => {
      const errors = { ...prev }
      delete errors[field]
      return errors
    })
  }

  const validate = () => {
    const errors = {}
    const rules = [
      ['age', 1, 120, 'Age must be between 1 and 120'],
      ['creatinine_phosphokinase', 0, Infinity, 'CPK must be a positive number'],
      ['ejection_fraction', 1, 100, 'Ejection fraction must be between 1% and 100%'],
      ['platelets', 0, Infinity, 'Platelet count must be a positive number'],
      ['serum_creatinine', 0, Infinity, 'Serum creatinine must be a positive number'],
      ['serum_sodium', 0, Infinity, 'Serum sodium must be a positive number'],
    ]

    rules.forEach(([field, min, max, message]) => {
      const value = Number(formData[field])

      if (
        formData[field].trim() === '' ||
        !Number.isFinite(value) ||
        value < min ||
        value > max ||
        (min === 0 && value === 0)
      ) {
        errors[field] = message
      }
    })

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setApiError(null)

    if (!validate()) return

    setLoading(true)

    const payload = Object.fromEntries(
      Object.entries(formData).map(([key, value]) => [
        key,
        ['anaemia', 'diabetes', 'high_blood_pressure', 'sex', 'smoking'].includes(key)
          ? Number.parseInt(value, 10)
          : Number.parseFloat(value),
      ])
    )

    try {
      let response

      try {
        response = await fetch('/api/predict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      } catch {
        response = await fetch('http://127.0.0.1:8000/predict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      }

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || `Server error: ${response.status}`)
      }

      setResult(data)
      setBackendStatus('online')
    } catch (error) {
      setApiError(error.message || 'Could not connect to the prediction API.')
      setBackendStatus('offline')
    } finally {
      setLoading(false)
    }
  }

  const loadPreset = (preset) => {
    setFormData({ ...preset })
    setFieldErrors({})
    setApiError(null)
  }

  const getProbabilityColor = (probability) => {
    if (probability < 0.35) return '#16a34a'
    if (probability < 0.6) return '#d97706'
    return '#dc2626'
  }

  // Keep your existing return (...) JSX here, unchanged.
}
