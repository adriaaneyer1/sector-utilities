import { useEffect, useState } from 'react'
import AgentPanel from '../components/AgentPanel.jsx'
import RemediationCard, { STAGES } from '../components/RemediationCard.jsx'
import StatCard from '../components/StatCard.jsx'
import { resetRemediation } from '../api.js'
import { matchesFilters, useFilters } from '../context/FilterContext.jsx'
import useAgent from '../hooks/useAgent.js'
import useRemediation from '../hooks/useRemediation.js'
import { formatTime } from '../utils.js'

const STEP_TEXT = {
  check_version: 'Read the firmware version each device reports.',
  check_repository: 'Look up the approved firmware that fixes its findings.',
  apply_update: 'Install the new firmware. Devices that need change control are never touched.',
  reboot: 'Restart the device and wait until it answers again.',
  recheck: 'Run the compliance checks again on the updated device.',
  report: 'Publish the new status: Compliant, Partially compliant, Needs change control or Non-compliant.',
}

const SEARCH_FIELDS = ['name', 'type', 'protocol', 'endpoint', 'company', 'note']

function FlowExplainer({ ready }) {
  return (
    <section className="flow-panel" aria-label="AI remediation flow">
      <h2 className="agent-title">{ready ? 'Ready to remediate' : 'Select a site to begin'}</h2>
      <p className="agent-desc">
        {ready
          ? 'Press Run agent. For every device that is not compliant, the agent runs these steps on its own:'
          : 'Choose a sector, location and company above. For every device that is not compliant, the agent then runs these steps on its own:'}
      </p>
      <ol className="flow-steps">
        {STAGES.map((s, i) => (
          <li key={s.key} className="flow-step">
            <span className="flow-num mono">{i + 1}</span>
            <div>
              <div className="device-name">{s.title}</div>
              <div className="device-desc">{STEP_TEXT[s.key]}</div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

export default function CompliancePage() {
  const { data, error, refresh } = useRemediation()
  const { agent, running } = useAgent('remediation')
  const { filters } = useFilters()
  const [resetting, setResetting] = useState(false)
  const [resetError, setResetError] = useState(null)

  // same flow as the other pages: pick a site, run the agent, then see results
  const ready = Boolean(filters.sector && filters.location && filters.company)
  const selection = `${filters.sector}|${filters.location}|${filters.company}`
  const [startedFor, setStartedFor] = useState(null)
  const [shownFor, setShownFor] = useState(null)
  const started = ready && startedFor === selection
  const revealed = ready && shownFor === selection && !running

  useEffect(() => {
    setStartedFor(null)
    setShownFor(null)
  }, [selection])

  // while the agent works, show each device's live progress
  const live = Object.entries(agent?.progress ?? {}).map(([id, p]) => ({ id, ...p }))
  const finished = (data?.devices ?? []).filter((d) => matchesFilters(d, filters, SEARCH_FIELDS))
  const summary = data?.summary

  async function reset() {
    setResetting(true)
    setResetError(null)
    try {
      await resetRemediation()
      await refresh()
      setShownFor(null)
      setStartedFor(null)
    } catch (e) {
      setResetError(e.message)
    } finally {
      setResetting(false)
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Compliance</h1>
          <p className="subtitle">The AI Remediation Agent brings non-compliant devices into compliance</p>
        </div>
        {revealed && <span className="mono muted">Report {formatTime(data?.finished_at)}</span>}
      </header>

      {(error || resetError) && (
        <div className="alert" role="alert">
          {resetError ?? `Can’t reach the portal API (${error}). Is the backend running on port 8000?`}
        </div>
      )}

      <AgentPanel
        name="remediation"
        description="Checks firmware, installs the approved update from the repository, reboots and re-checks every non-compliant device."
        locked={!ready}
        lockedHint="Select a sector, location and company to run the agent"
        showLog={started}
        onStart={() => setStartedFor(selection)}
        onDone={() => { refresh(); setShownFor(selection) }}
      />

      {!started && !revealed && <FlowExplainer ready={ready} />}

      {started && running && (
        <section className="card-grid" aria-label="Remediation in progress" aria-live="polite">
          {live.length === 0 && <p className="muted">Checking compliance of every device…</p>}
          {live.map((d) => <RemediationCard key={d.id} device={d} />)}
        </section>
      )}

      {revealed && summary && <>
        <section className="stats status-stats" aria-label="Remediation summary">
          <StatCard label="Devices checked" value={summary.checked} />
          <StatCard label="Remediated" value={summary.remediated} tone="good" />
          <StatCard label="Change approval required" value={summary.change_control} tone="info" />
          <StatCard
            label="Compliant now"
            value={`${summary.after.Compliant} of ${summary.checked}`}
            tone="good"
          />
        </section>

        <div className="table-caption caption-plain">
          <span className="muted">
            Before: {summary.before.Compliant} compliant · After: {summary.after.Compliant} compliant
          </span>
          <button type="button" className="link-button" onClick={reset} disabled={resetting}>
            {resetting ? 'Resetting…' : 'Undo updates and start again'}
          </button>
        </div>

        {finished.length === 0 && <p className="muted">No remediated devices match this search.</p>}
        <section className="card-grid" aria-label="Remediation results">
          {finished.map((d) => <RemediationCard key={d.id} device={d} />)}
        </section>
      </>}
    </>
  )
}
