import React, { useRef } from 'react'

export default function LogUploader({ onLoad, onClear }) {
  const fileRef = useRef(null)

  const handleFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const text = await file.text()
      const json = JSON.parse(text)
      onLoad(json, file.name)
    } catch (err) {
      alert('Invalid JSON file.')
      fileRef.current.value = ''
    }
  }

  return (
    <div className="row">
      <input
        ref={fileRef}
        type="file"
        accept="application/json,.json"
        onChange={handleFile}
      />
      <button
        type="button"
        onClick={() => {
          if (fileRef.current) fileRef.current.value = ''
          onClear?.()
        }}
      >
        Clear
      </button>
    </div>
  )
}
