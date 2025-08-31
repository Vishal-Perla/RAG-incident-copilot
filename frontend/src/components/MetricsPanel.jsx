import React, { useEffect, useState } from 'react'
import { fetchMetrics, fetchMetricsSummary } from '../api'
import './MetricsPanel.css'

export default function MetricsPanel() {
  const [rows, setRows] = useState([])
  const [summary, setSummary] = useState(null)
  const [limit, setLimit] = useState(50)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const load = async () => {
    setLoading(true)
    setErr('')
    try {
      const [m, s] = await Promise.all([fetchMetrics(limit), fetchMetricsSummary(200)])
      setRows(m)
      setSummary(s)
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="card slide-up">
      <div className="row space">
        <h2>📊 Metrics</h2>
        <div className="row">
          <input
            type="number"
            value={limit}
            min={1}
            max={500}
            onChange={(e) => setLimit(Number(e.target.value))}
            style={{
              width: 80,
              background: '#0e111b',
              color: 'white',
              border: '1px solid #262a38',
              borderRadius: 6,
              padding: '6px 8px'
            }}
          />
          <button onClick={load}>Refresh</button>
        </div>
      </div>

      {summary && (
        <div className="block fade-in">
          <div className="tag">Summary</div>
          <ul className="sources">
            <li><strong>Total:</strong> {summary.count}</li>
            <li><strong>Success rate:</strong> {(summary.success_rate * 100).toFixed(1)}%</li>
            <li><strong>Avg latency:</strong> {summary.avg_latency_ms} ms</li>
            <li><strong>P95 latency:</strong> {summary.p95_latency_ms} ms</li>
          </ul>
        </div>
      )}

      {err && (
        <div className="card error" style={{ marginTop: 10 }}>
          <strong>Error:</strong> {err}
        </div>
      )}

      <div style={{ overflowX: 'auto', marginTop: 10 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left' }}>
              <th style={{ padding: '8px 6px' }}>ID</th>
              <th style={{ padding: '8px 6px' }}>Time</th>
              <th style={{ padding: '8px 6px' }}>Success</th>
              <th style={{ padding: '8px 6px' }}>Latency (ms)</th>
              <th style={{ padding: '8px 6px' }}>Sources</th>
              <th style={{ padding: '8px 6px' }}>TopK</th>
              <th style={{ padding: '8px 6px' }}>Error</th>
              <th style={{ padding: '8px 6px' }}>Alert (trimmed)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} style={{ borderTop: '1px solid #262a38' }}>
                <td style={{ padding: '8px 6px' }}>{r.id}</td>
                <td style={{ padding: '8px 6px' }}>{r.ts}</td>
                <td style={{ padding: '8px 6px' }}>{r.success ? '✅' : '❌'}</td>
                <td style={{ padding: '8px 6px' }}>{r.latency_ms}</td>
                <td style={{ padding: '8px 6px' }}>{r.num_sources ?? '-'}</td>
                <td style={{ padding: '8px 6px' }}>{r.top_k ?? '-'}</td>
                <td style={{ padding: '8px 6px', color: '#ffb3b3' }}>{r.error || ''}</td>
                <td style={{
                  padding: '8px 6px',
                  maxWidth: 420,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}>
                  {r.alert_text}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan="8" style={{ padding: '10px' }}>No data yet. Run some analyses.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {loading && <div className="tag" style={{ marginTop: 10 }}>Loading…</div>}
    </div>
  )
}
