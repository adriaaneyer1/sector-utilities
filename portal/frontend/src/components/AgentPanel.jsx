import { useEffect, useRef } from 'react'
import useAgent from '../hooks/useAgent.js'
import { formatTime } from '../utils.js'

function AgentIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="4" y="7" width="16" height="12" rx="3" />
      <path d="M12 3v4M9 12h.01M15 12h.01M9 16h6" />
    </svg>
  )
}

// locked:     button is shown but greyed out and inactive (lockedHint says why)
// showLog:    whether the live activity log is visible
// onStart:    called when the user presses Run agent
export default function AgentPanel({ name, description, onDone, onStart, locked = false, lockedHint, showLog = true }) {
  const { agent, error, running, run } = useAgent(name, onDone)
  const steps = agent?.steps ?? []
  const logRef = useRef(null)

  // keep the newest step in view while the agent works
  useEffect(() => {
    const el = logRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [steps.length, showLog])

  return (
    <section className="agent-panel" aria-label={agent?.title ?? 'Agent'}>
      <div className="agent-head">
        <div className="agent-id">
          <span className={`agent-icon ${running ? 'agent-busy' : ''}`}><AgentIcon /></span>
          <div>
            <h2 className="agent-title">{agent?.title ?? 'Agent'}</h2>
            <p className="agent-desc">{description}</p>
          </div>
        </div>
        <div className="header-actions">
          <span className={locked ? 'agent-hint' : 'mono muted'} id={`${name}-run-hint`}>
            {locked
              ? lockedHint
              : running ? 'Running…' : agent?.last_run ? `Run #${agent.run_count} at ${formatTime(agent.last_run)}` : 'Not run yet'}
          </span>
          <button
            type="button"
            className={`btn-primary ${locked ? 'is-locked' : ''}`}
            onClick={() => { onStart?.(); run() }}
            disabled={locked || running}
            aria-describedby={locked ? `${name}-run-hint` : undefined}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M5 3l14 9-14 9z" />
            </svg>
            {running && !locked ? 'Running' : 'Run agent'}
          </button>
        </div>
      </div>

      {error && <div className="alert" role="alert">{error}</div>}

      {showLog && (
        <ol className="agent-log" aria-live="polite" ref={logRef}>
          {steps.length === 0 && <li className="muted">No activity yet.</li>}
          {steps.map((s, i) => (
            <li key={`${s.t}-${i}`}>
              <span className="mono log-time">{formatTime(s.t)}</span>
              <span>{s.message}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
