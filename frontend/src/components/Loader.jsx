import React from 'react'
import './Loader.css'

export default function Loader({ text = 'Analyzing…' }) {
  return (
    <div className="loader-container">
      <div className="spinner"></div>
      <span className="loader-text">{text}</span>
    </div>
  )
}
