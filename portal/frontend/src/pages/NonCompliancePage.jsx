import { useEffect, useState } from 'react'
import AgentPanel from '../components/AgentPanel.jsx'
import { STATUSES } from '../components/ComplianceBadge.jsx'
import ComplianceCard from '../components/ComplianceCard.jsx'
import { matchesFilters, useFilters } from '../context/FilterContext.jsx'
import useCompliance from '../hooks/useCompliance.js'
import { formatTime } from '../utils.js'

const SEARCH_FIELDS = ['name', 'type', 'protocol', 'endpoint', 'firmware', 'company', 'status', 'violationsText']

// worst status first, so the devices that need attention lead the report
const RANK = Object.fromEntries(STATUSES.map((s, i) => [s.label, -i]))

function EmptyState({ ready }) {
  return (
    <section className="empty-state" aria-live="polite">
      <span className="empty-icon" aria-hidden="true">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6z" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </span>
      <h2 className="empty-title">{ready ? 'Ready to check compliance' : 'Select a site to begin'}</h2>
      <p className="empty-text">
        {ready
          ? 'Press Run agent to let the Compliance Agent check every device of this company against the standards.'
          : 'Choose a sector, location and company above. The Compliance Agent then checks the devices of that site.'}
      </p>
    </section>
  )
}

export default function NonCompliancePage() {
  const { data, error, refresh } = useCompliance()
  const { filters } = useFilters()
  const [statusFilter, setStatusFilter] = useState('')

  // same flow as the Devices page: pick a site, run the agent, then see results
  const ready = Boolean(filters.sector && filters.location && filters.company)
  const selection = `${filters.sector}|${filters.location}|${filters.company}`
  const [startedFor, setStartedFor] = useState(null)
  const [shownFor, setShownFor] = useState(null)
  const revealed = ready && shownFor === selection
  const showLog = ready && startedFor === selection

  useEffect(() => {
    setStartedFor(null)
    setShownFor(null)
  }, [selection])

  const all = (data?.devices ?? []).map((d) => ({
    ...d,
    violationsText: (d.violations ?? []).map((v) => `${v.standard} ${v.requirement} ${v.vector}`).join(' '),
  }))
  const inScope = all.filter((d) => matchesFilters(d, filters, SEARCH_FIELDS))
  const counts = Object.fromEntries(STATUSES.map((s) => [s.label, inScope.filter((d) => d.status === s.label).length]))
  const devices = inScope
    .filter((d) => !statusFilter || d.status === statusFilter)
    .sort((a, b) => (RANK[a.status] ?? 1) - (RANK[b.status] ?? 1))
  const scope = [filters.company, filters.sector, filters.location].filter(Boolean).join(' · ')

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Non-Compliance</h1>
          <p className="subtitle">
            Compliance status of every device, referenced to NERC CIP and {data?.standard ?? 'IEC 62443'}
          </p>
        </div>
        {revealed && <span className="mono muted">Report {formatTime(data?.finished_at)}</span>}
      </header>

      {error && (
        <div className="alert" role="alert">
          Can’t reach the portal API ({error}). Is the backend running on port 8000?
        </div>
      )}

      <AgentPanel
        name="compliance"
        description="Checks every discovered device against the compliance rules and the approved firmware baseline."
        locked={!ready}
        lockedHint="Select a sector, location and company to run the agent"
        showLog={showLog}
        onStart={() => setStartedFor(selection)}
        onDone={() => { refresh(); setShownFor(selection) }}
      />

      {!revealed && <EmptyState ready={ready} />}

      {revealed && <>
        <section className="stats status-stats" aria-label="Devices per compliance status">
          {STATUSES.map((s) => {
            const active = statusFilter === s.label
            return (
              <button
                key={s.label}
                type="button"
                className={`stat-card stat-button ${active ? 'is-active' : ''}`}
                aria-pressed={active}
                onClick={() => setStatusFilter(active ? '' : s.label)}
              >
                <span className="stat-label">{s.label}</span>
                <span className={`stat-value text-${s.tone}`}>{counts[s.label]}</span>
              </button>
            )
          })}
        </section>

        <div className="table-caption caption-plain">
          <span className="scope">{scope}</span>
          <span className="muted">
            Showing {devices.length} of {all.length} audited devices
            {statusFilter && <> · <button type="button" className="link-button" onClick={() => setStatusFilter('')}>show all</button></>}
          </span>
        </div>

        {all.length === 0 && (
          <p className="muted">No devices to check yet. Run the Discovery Agent on the Devices page first.</p>
        )}
        {all.length > 0 && devices.length === 0 && (
          <p className="muted">No audited devices match this search.</p>
        )}
        <section className="card-grid" aria-label="Devices">
          {devices.map((d) => <ComplianceCard key={d.id} device={d} />)}
        </section>
      </>}
    </>
  )
}
