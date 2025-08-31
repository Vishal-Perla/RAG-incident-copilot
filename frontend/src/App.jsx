import React, { useState } from 'react'
import { analyzeAlert } from './api'
import LogUploader from './components/LogUploader'
import ResultCard from './components/ResultCard'
import MetricsPanel from './components/MetricsPanel'
import Loader from './components/Loader'

export default function App() {
  const [alertText, setAlertText] = useState('')
  const [logJson, setLogJson] = useState(null)
  const [logFileName, setLogFileName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const handleAnalyze = async () => {
    setIsLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await analyzeAlert(alertText, logJson)
      setResult(res)
    } catch (e) {
      setError(
        e?.response?.data?.detail ||
        e?.message ||
        'Failed to analyze. Is the backend running on VITE_API_URL?'
      )
    } finally {
      setIsLoading(false)
    }
  }

  const loadSample = () => {
    setAlertText('Multiple failed logins detected from several IPs targeting user admin.')
    setLogJson({
      source: 'auth.service',
      events: [
        { ts: '2025-08-21T10:15:00Z', user: 'admin', ip: '203.0.113.5', outcome: 'FAIL' },
        { ts: '2025-08-21T10:15:05Z', user: 'admin', ip: '203.0.113.5', outcome: 'FAIL' },
        { ts: '2025-08-21T10:16:00Z', user: 'admin', ip: '198.51.100.7', outcome: 'FAIL' },
      ],
    })
    setLogFileName('sample-auth-log.json')
    setResult(null)
    setError('')
  }

  return (
    <div className="container">
      <header>
        <h1>🔐 AI Incident Response Copilot</h1>
        <p>Paste an alert, upload a JSON log, and get contextual recommendations (RAG-powered).</p>
      </header>

      <section className="card">
        <label htmlFor="alertText">Alert (free text)</label>
        <textarea
          id="alertText"
          placeholder="e.g., Multiple failed logins detected from several IPs targeting user admin..."
          value={alertText}
          onChange={(e) => setAlertText(e.target.value)}
          rows={6}
        />
        <div className="row gap">
          <button onClick={loadSample} type="button">Load Sample</button>
          <button
            onClick={handleAnalyze}
            type="button"
            disabled={!alertText || isLoading}
            className="primary"
          >
            {isLoading ? 'Analyzing…' : 'Analyze'}
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Upload JSON Log (optional)</h2>
        <LogUploader
          onLoad={(json, name) => { setLogJson(json); setLogFileName(name) }}
          onClear={() => { setLogJson(null); setLogFileName('') }}
        />
        {logJson && (
          <pre className="preview">
{JSON.stringify(logJson, null, 2)}
          </pre>
        )}
      </section>

      {isLoading && (
        <section className="card">
          <Loader text="Analyzing alert..." />
        </section>
      )}

      {error && (
        <section className="card error">
          <strong>Error:</strong> {error}
        </section>
      )}

      {result && !isLoading && (
        <section className="card">
          <ResultCard result={result} />
        </section>
      )}

      {/* Metrics panel with animation */}
      <MetricsPanel />

      <footer>
        <small>
          Backend URL: <code>{import.meta.env.VITE_API_URL || '(not set)'}</code>
        </small>
      </footer>
    </div>
  )
}
