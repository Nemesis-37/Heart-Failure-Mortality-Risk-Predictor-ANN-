import React, { useState, useRef } from 'react'
import { apiUrl, getAuthCandidateUrls } from '../apiConfig.js'

export default function DoctorProfilePhotoModal({
  isOpen,
  onClose,
  doctorUser,
  currentPhotoUrl: propPhotoUrl,
  onPhotoUpdated,
}) {
  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [base64Data, setBase64Data] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const fileInputRef = useRef(null)

  if (!isOpen) return null

  const cleanName = doctorUser?.name || 'Doctor'
  const cleanRole = doctorUser?.role || 'Attending Physician'
  const initials =
    doctorUser?.avatarInitials ||
    cleanName.replace(/^Dr\.\s*/i, '').trim().slice(0, 2).toUpperCase() ||
    'DR'

  const rawPhoto =
    propPhotoUrl ||
    doctorUser?.profilePhotoUrl ||
    doctorUser?.profile_photo_url ||
    localStorage.getItem('cardiopredict_doctor_profile_photo') ||
    localStorage.getItem('cardiopredict_doctor_profile_photo_base64') ||
    (doctorUser?.email ? localStorage.getItem(`cardiopredict_photo_${doctorUser.email}`) : null)

  const currentPhotoUrl = rawPhoto
    ? (rawPhoto.startsWith('http') || rawPhoto.startsWith('data:') ? rawPhoto : apiUrl(rawPhoto))
    : null

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    setErrorMessage('')
    setSuccessMessage('')
    if (!file) return

    // Validation: Type
    const validTypes = ['image/jpeg', 'image/png', 'image/webp']
    if (!validTypes.includes(file.type.toLowerCase())) {
      setErrorMessage('Please select a valid image file (JPEG, PNG, or WebP).')
      return
    }

    // Validation: Size (Max 5 MB)
    if (file.size > 5 * 1024 * 1024) {
      setErrorMessage('Image size exceeds 5 MB limit. Please select a smaller photo.')
      return
    }

    setSelectedFile(file)
    const objectUrl = URL.createObjectURL(file)
    setPreviewUrl(objectUrl)

    // Convert to Base64 data URL for instant client persistence & offline resilience
    const reader = new FileReader()
    reader.onload = () => {
      setBase64Data(reader.result)
    }
    reader.readAsDataURL(file)
  }

  const handleSave = async () => {
    if (!selectedFile) {
      setErrorMessage('Please select an image file to upload.')
      return
    }

    setIsUploading(true)
    setErrorMessage('')
    setSuccessMessage('')

    try {
      // 1. Ensure Base64 representation is fully available
      let b64 = base64Data
      if (!b64) {
        b64 = await new Promise((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => resolve(reader.result)
          reader.onerror = () => reject(new Error('Unable to read selected photo file.'))
          reader.readAsDataURL(selectedFile)
        })
      }

      if (!b64) {
        throw new Error('Unable to process the selected photo. Please choose a different image.')
      }

      let finalPhotoUrl = b64
      let uploadedToBackend = false

      // 2. Attempt backend upload with network timeout and proxy fallback
      try {
        const token =
          localStorage.getItem('cardiopredict_access_token') ||
          sessionStorage.getItem('cardiopredict_access_token') ||
          'demo-access-token-carter-2026'

        const formData = new FormData()
        formData.append('file', selectedFile)

        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 6000)

        // Try environment-aware candidate URLs without leaking localhost to production
        const uniqueUrls = getAuthCandidateUrls('/auth/profile-photo')

        let res = null
        for (const url of uniqueUrls) {
          try {
            const attempt = await fetch(url, {
              method: 'POST',
              headers: {
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
              },
              body: formData,
              signal: controller.signal,
            })
            if (attempt.ok) {
              res = attempt
              break
            } else if (attempt.status === 400 || attempt.status === 422) {
              const errJson = await attempt.json().catch(() => ({}))
              throw new Error(errJson.detail || 'Invalid image file provided.')
            }
          } catch (innerErr) {
            // Rethrow specific backend validation errors so user is informed of bad files
            if (innerErr.message && (innerErr.message.includes('Invalid') || innerErr.message.includes('limit') || innerErr.message.includes('format'))) {
              throw innerErr
            }
            // Otherwise, network or connection failure: try next candidate URL
          }
        }
        clearTimeout(timeoutId)

        if (res && res.ok) {
          const data = await res.json()
          if (data?.profile_photo_url) {
            finalPhotoUrl = data.profile_photo_url
            uploadedToBackend = true
          }
        }
      } catch (uploadErr) {
        // If it's a validation error, let it propagate to errorMessage
        if (uploadErr.message && (uploadErr.message.includes('Invalid') || uploadErr.message.includes('limit') || uploadErr.message.includes('format'))) {
          throw uploadErr
        }
        // For network/offline/fetch errors, log warning and gracefully persist locally
        console.warn('Backend upload deferred; persisting photo locally in browser storage:', uploadErr)
      }

      // 3. Persist photo in localStorage & session storage for all components and reloads
      try {
        localStorage.setItem('cardiopredict_doctor_profile_photo', finalPhotoUrl)
        localStorage.setItem('cardiopredict_doctor_profile_photo_base64', b64)
        if (doctorUser?.email) {
          localStorage.setItem(`cardiopredict_photo_${doctorUser.email}`, finalPhotoUrl)
          localStorage.setItem(`cardiopredict_photo_base64_${doctorUser.email}`, b64)
        }
        const authKeys = ['hf_predictor_doctor_auth_v1', 'cardiopredict_current_doctor']
        authKeys.forEach((key) => {
          ;[localStorage, sessionStorage].forEach((storage) => {
            const raw = storage.getItem(key)
            if (raw) {
              try {
                const parsed = JSON.parse(raw)
                parsed.profile_photo_url = finalPhotoUrl
                parsed.profilePhotoUrl = finalPhotoUrl
                parsed.profile_photo_base64 = b64
                storage.setItem(key, JSON.stringify(parsed))
              } catch (_) {}
            }
          })
        })
      } catch (storageErr) {
        console.warn('Storage persistence warning:', storageErr)
      }

      setSuccessMessage(
        uploadedToBackend
          ? 'Profile photo updated and synchronized successfully!'
          : 'Profile photo saved and updated successfully!'
      )

      if (onPhotoUpdated) {
        onPhotoUpdated(finalPhotoUrl)
      }

      setTimeout(() => {
        handleClose()
      }, 700)
    } catch (err) {
      setErrorMessage(err.message || 'An error occurred during upload.')
    } finally {
      setIsUploading(false)
    }
  }

  const handleClose = () => {
    if (previewUrl && previewUrl.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl)
    }
    setSelectedFile(null)
    setPreviewUrl(null)
    setErrorMessage('')
    setSuccessMessage('')
    onClose()
  }

  const displayImage = previewUrl || currentPhotoUrl

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(2, 6, 23, 0.75)',
        backdropFilter: 'blur(6px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.25rem',
      }}
      onClick={handleClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="profile-modal-title"
    >
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          background: '#0B1F3A',
          color: '#F8FAFC',
          borderRadius: '16px',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          padding: '1.75rem',
          boxShadow: '0 20px 48px rgba(0, 0, 0, 0.5)',
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div>
            <h3 id="profile-modal-title" style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: '#FFFFFF' }}>
              Physician Profile Photo
            </h3>
            <p style={{ margin: '2px 0 0', fontSize: '0.78rem', color: '#94A3B8' }}>
              {cleanName} &bull; {cleanRole}
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94A3B8',
              fontSize: '1.35rem',
              cursor: 'pointer',
              padding: '4px 8px',
              borderRadius: '6px',
            }}
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        {/* Avatar Display / Preview Area */}
        <div style={{ textAlign: 'center', margin: '1.25rem 0' }}>
          <div
            style={{
              width: '110px',
              height: '110px',
              borderRadius: '50%',
              margin: '0 auto 1rem',
              overflow: 'hidden',
              background: 'linear-gradient(135deg, #1565D8 0%, #38BDF8 100%)',
              border: '3px solid rgba(56, 189, 248, 0.4)',
              boxShadow: '0 8px 24px rgba(21, 101, 216, 0.35)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
            }}
          >
            {displayImage ? (
              <img
                src={displayImage}
                alt={cleanName}
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                onError={(e) => {
                  const fallback =
                    localStorage.getItem('cardiopredict_doctor_profile_photo_base64') ||
                    (doctorUser?.email ? localStorage.getItem(`cardiopredict_photo_base64_${doctorUser.email}`) : null)
                  if (fallback && fallback.startsWith('data:') && e.currentTarget.src !== fallback) {
                    e.currentTarget.src = fallback
                  }
                }}
              />
            ) : (
              <span style={{ fontSize: '2.25rem', fontWeight: 800, color: '#FFFFFF', letterSpacing: '0.02em' }}>
                {initials}
              </span>
            )}
          </div>

          {/* Hidden File Input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
            style={{ display: 'none' }}
          />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            style={{
              background: 'rgba(56, 189, 248, 0.12)',
              color: '#38BDF8',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              padding: '8px 18px',
              borderRadius: '8px',
              fontSize: '0.84rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
            <span>{selectedFile ? 'Choose Different Image' : 'Change Profile Photo'}</span>
          </button>

          <p style={{ margin: '8px 0 0', fontSize: '0.72rem', color: '#64748B' }}>
            Supports JPEG, PNG, or WebP &bull; Maximum 5 MB
          </p>
        </div>

        {/* Feedback Messages */}
        {errorMessage && (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.35)',
              borderRadius: '8px',
              padding: '8px 12px',
              color: '#F87171',
              fontSize: '0.8rem',
              marginBottom: '1rem',
              textAlign: 'center',
            }}
          >
            {errorMessage}
          </div>
        )}

        {successMessage && (
          <div
            style={{
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              borderRadius: '8px',
              padding: '8px 12px',
              color: '#34D399',
              fontSize: '0.8rem',
              marginBottom: '1rem',
              textAlign: 'center',
            }}
          >
            {successMessage}
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '1.25rem' }}>
          <button
            type="button"
            onClick={handleClose}
            disabled={isUploading}
            style={{
              background: 'transparent',
              color: '#94A3B8',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              padding: '9px 18px',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: isUploading ? 'not-allowed' : 'pointer',
            }}
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleSave}
            disabled={!selectedFile || isUploading}
            style={{
              background: selectedFile && !isUploading ? '#1565D8' : 'rgba(21, 101, 216, 0.4)',
              color: '#FFFFFF',
              border: 'none',
              padding: '9px 20px',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: 700,
              cursor: selectedFile && !isUploading ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: selectedFile && !isUploading ? '0 4px 12px rgba(21, 101, 216, 0.3)' : 'none',
            }}
          >
            {isUploading ? (
              <>
                <span>Saving...</span>
              </>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Save Photo</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
