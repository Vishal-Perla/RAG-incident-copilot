import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Analyze an alert with optional JSON logs.
 * Expects backend response shape:
 * { alert, context, response (markdown), sources[], structured? }
 */
export async function analyzeAlert(alertText, logJson) {
  const payload = {
    alertText: alertText || '',
    logFile: logJson || null,
  }
  const { data } = await axios.post(`${BASE}/analyze`, payload, {
    headers: { 'Content-Type': 'application/json' },
    timeout: 30000,
  })
  return data
}

/** Fetch last N requests (most recent first). */
export async function fetchMetrics(limit = 50) {
  const { data } = await axios.get(`${BASE}/metrics`, { params: { limit } })
  return data
}

/** Fetch summary stats over last N rows. */
export async function fetchMetricsSummary(limit = 200) {
  const { data } = await axios.get(`${BASE}/metrics/summary`, { params: { limit } })
  return data
}
