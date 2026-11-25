import React, { useState, useEffect } from 'react'
import { apiUrl } from '../apiConfig.js'

/**
 * DoctorAvatar Component
 * 
 * Secure, resilient avatar rendering for physician profile images.
 * Features:
 * - Checks prop photo, localStorage base64 data, and backend URLs.
 * - Graceful fallback hierarchy: Server URL -> Local Base64 Cache -> Clean Initials.
 * - Zero direct DOM manipulation to maintain strict React virtual DOM integrity.
 */
export default function DoctorAvatar({
  photoUrl,
  initials = 'DR',
  alt = 'Physician',
  className = '',
  style = {},
  email = null,
}) {
  const [hasError, setHasError] = useState(false)
  const [currentSrc, setCurrentSrc] = useState(null)

  useEffect(() => {
    setHasError(false)

    // Resolve most immediate valid photo candidate
    const candidate =
      photoUrl ||
      localStorage.getItem('cardiopredict_doctor_profile_photo') ||
      localStorage.getItem('cardiopredict_doctor_profile_photo_base64') ||
      (email ? localStorage.getItem(`cardiopredict_photo_${email}`) : null)

    if (candidate) {
      if (candidate.startsWith('data:') || candidate.startsWith('blob:') || candidate.startsWith('http')) {
        setCurrentSrc(candidate)
      } else {
        setCurrentSrc(apiUrl(candidate))
      }
    } else {
      setCurrentSrc(null)
    }
  }, [photoUrl, email])

  const handleImgError = () => {
    // Attempt fallback to cached Base64 data if available
    const base64Fallback =
      localStorage.getItem('cardiopredict_doctor_profile_photo_base64') ||
      (email ? localStorage.getItem(`cardiopredict_photo_base64_${email}`) : null)

    if (base64Fallback && base64Fallback.startsWith('data:') && currentSrc !== base64Fallback) {
      setCurrentSrc(base64Fallback)
      return
    }

    setHasError(true)
  }

  if (currentSrc && !hasError) {
    return (
      <img
        src={currentSrc}
        alt={alt}
        className={className}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          borderRadius: 'inherit',
          display: 'block',
          ...style,
        }}
        onError={handleImgError}
      />
    )
  }

  return <span className={`avatar-initials ${className}`}>{initials}</span>
}
