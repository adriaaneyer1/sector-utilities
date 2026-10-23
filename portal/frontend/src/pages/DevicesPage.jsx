import { useEffect, useState } from 'react'
import AgentPanel from '../components/AgentPanel.jsx'
import ComplianceBadge from '../components/ComplianceBadge.jsx'
import StatCard from '../components/StatCard.jsx'
import StatusPill from '../components/StatusPill.jsx'
import ViolationList from '../components/ViolationList.jsx'
import { matchesFilters, useFilters } from '../context/FilterContext.jsx'
import useDevices from '../hooks/useDevices.js'
import { formatTime } from '../utils.js'

const SEARCH_FIELDS = ['name', 'type', 'protocol', 'endpoint', 'firmware', 'compliance', 'company', 'violationsText']

function summarise(devices) {
  const s = { total: devices.length, online: 0, no_stream: 0, offline: 0 }
  for (const d of devices) {
    if (d.status === 'online' || d.status === 'streaming') s.online += 1
    else if (d.status in s) s[d.status] += 1
  }
  return s
}

function EmptyState({ ready }) {
  return (
    <section className="empty-state" aria-live="polite">
      <span className="empty-icon" aria-hidden="true">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="4" width="18" height="6" rx="1.5" />
          <rect x="3" y="14" width="18" height="6" rx="1.5" />
          <path d="M7 7h.01M7 17h.01" />
        </svg>
      </span>
      <h2 className="empty-title">{ready ? 'Ready to discover devices' : 'Select a site to begin'}</h2>
      <p className="empty-text">
        {ready
          ? 'Press Run agent to let the Discovery Agent find the devices provisioned for this company.'
          : 'Choose a sector, location and company above. The Discovery Agent then finds the devices provisioned for that site.'}
      </p>
    </section>
  )
}

export default function DevicesPage() {
  const { data, error, refresh } = useDevices()
  const { filters } = useFilters()

  // Results stay hidden until all three dropdowns are chosen and the agent
  // has been run for exactly that selection; changing a dropdown hides them again.
  const ready = Boolean(filters.sector && filters.location && filters.company)
  const selection = `${filters.sector}|${filters.location}|${filters.company}`
  const [startedFor, setStartedFor] = useState(null)
  const [shownFor, setShownFor] = useState(null)
  const revealed = ready && shownFor === selection
  const showLog = ready && startedFor === selection

  // any dropdown change means the agent must run again
  useEffect(() => {
    setStartedFor(null)
    setShownFor(null)
  }, [selection])

  // flatten violated standards so the global search can find them too
  const all = (data?.devices ?? []).map((d) => ({
    ...d,
    violationsText: (d.violations ?? []).map((v) => `${v.standard} ${v.requirement} ${v.vector}`).join(' '),
  }))
  const devices = all.filter((d) => matchesFilters(d, filters, SEARCH_FIELDS))
  const summary = data ? summarise(devices) : null
  const scope = [filters.company, filters.sector, filters.location].filter(Boolean).join(' · ')

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Devices</h1>
          <p className="subtitle">Devices found by the Discovery Agent, with their live status</p>
        </div>
        {revealed && <span className="mono muted">Report {formatTime(data?.finished_at)}</span>}
      </header>

      {error && (
        <div className="alert" role="alert">
          Can’t reach the portal API ({error}). Is the backend running on port 8000?
        </div>
      )}

      <AgentPanel
        name="discovery"
        description="Scans each provisioned site, recognises every device and checks whether it is online."
        locked={!ready}
        lockedHint="Select a sector, location and company to run the agent"
        showLog={showLog}
        onStart={() => setStartedFor(selection)}
        onDone={() => { refresh(); setShownFor(selection) }}
      />

      {!revealed && <EmptyState ready={ready} />}

      {revealed && <>
      <section className="stats" aria-label="Summary">
        <StatCard label="Devices discovered" value={summary?.total} />
        <StatCard label="Online" value={summary?.online} tone="good" />
        <StatCard label="No data stream" value={summary?.no_stream} tone="warn" />
        <StatCard label="Offline" value={summary?.offline} tone="bad" />
      </section>

      <div className="table-box">
        <div className="table-caption">
          <span className="scope">{scope}</span>
          <span className="muted">Showing {devices.length} of {all.length} provisioned devices</span>
        </div>
        <table>
          <thead>
            <tr>
              <th scope="col">Device</th>
              <th scope="col">Protocol</th>
              <th scope="col">Endpoint</th>
              <th scope="col">Firmware</th>
              <th scope="col">Compliant</th>
              <th scope="col">Standard &amp; Requirement Violated</th>
              <th scope="col">Status</th>
              <th scope="col">Last seen</th>
            </tr>
          </thead>
          <tbody>
            {!data && <tr><td colSpan="8" className="muted">Loading…</td></tr>}
            {data && all.length === 0 && (
              <tr><td colSpan="8" className="muted">No devices discovered yet. Run the Discovery Agent.</td></tr>
            )}
            {data && all.length > 0 && devices.length === 0 && (
              <tr><td colSpan="8" className="muted">No provisioned devices match this search.</td></tr>
            )}
            {devices.map((d) => (
              // data-label is shown next to each value when the table turns into cards on small screens
              <tr key={d.id}>
                <td className="cell-device">
                  <div className="device-name">{d.name}</div>
                  <div className="device-desc">{d.type}</div>
                </td>
                <td data-label="Protocol">{d.protocol}</td>
                <td data-label="Endpoint" className="mono soft">{d.endpoint}</td>
                <td data-label="Firmware" className="mono soft">{d.firmware ?? <span className="muted">{d.firmware_note ?? 'Not reported'}</span>}</td>
                <td data-label="Compliant"><ComplianceBadge value={d.compliance} /></td>
                <td data-label="Standard & Requirement Violated" className="cell-violations"><ViolationList violations={d.violations} /></td>
                <td data-label="Status"><StatusPill status={d.status} /></td>
                <td data-label="Last seen" className="mono soft">{formatTime(d.last_seen)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      </>}
    </>
  )
}
