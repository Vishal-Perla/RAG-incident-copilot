import React from 'react'
import ReactMarkdown from 'react-markdown'
import './ResultCard.css'

export default function ResultCard({ result }) {
  const { alert, context, response, sources } = result || {}

  return (
    <div className="result fade-in">
      <h2>Result</h2>
      {alert && (
        <div className="block">
          <div className="tag">🚨 Alert</div>
          <p>{alert}</p>
        </div>
      )}
      {context && (
        <div className="block">
          <div className="tag">🔎 Context</div>
          <p>{context}</p>
        </div>
      )}
      {response && (
        <div className="block">
          <div className="tag">✅ Suggested Response</div>
          <ReactMarkdown>{response}</ReactMarkdown>
        </div>
      )}
      {Array.isArray(sources) && sources.length > 0 && (
        <div className="block">
          <div className="tag">📖 Sources</div>
          <ul className="sources">
            {sources.map((s, i) => (
              <li key={i}>
                {s.title ? <strong>{s.title}: </strong> : null}
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.url}
                  </a>
                ) : (
                  s.snippet || '—'
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
