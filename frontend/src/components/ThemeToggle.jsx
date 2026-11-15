import React from 'react'
import { useTheme } from '../context/ThemeContext.jsx'

export default function ThemeToggle({ className = '', style = {}, title }) {
  const { isDark, toggleTheme } = useTheme()

  const tooltipText = title || (isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode')

  return (
    <button
      type="button"
      className={`theme-toggle-btn ${isDark ? 'is-dark' : 'is-light'} ${className}`}
      onClick={toggleTheme}
      title={tooltipText}
      aria-label={tooltipText}
      style={style}
    >
      <span className="theme-toggle-icon-wrap" aria-hidden="true">
        {isDark ? (
          /* Sun icon in Dark Mode with soft golden-cyan glow */
          <svg
            className="theme-icon sun-icon"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="5" />
            <line x1="12" y1="1" x2="12" y2="3" />
            <line x1="12" y1="21" x2="12" y2="23" />
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
            <line x1="1" y1="12" x2="3" y2="12" />
            <line x1="21" y1="12" x2="23" y2="12" />
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
          </svg>
        ) : (
          /* Moon icon in Light Mode with deep navy stroke */
          <svg
            className="theme-icon moon-icon"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        )}
      </span>
      <span className="theme-toggle-sr-label sr-only">
        {isDark ? 'Dark Mode Active' : 'Light Mode Active'}
      </span>
    </button>
  )
}
