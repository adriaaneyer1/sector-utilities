const PLANNED = [
  { title: 'Compliance report per device', text: 'Every discovered device with its findings, the standard it violates and a remediation plan.' },
  { title: 'Four compliance states', text: 'Compliant, Partially compliant, Needs change control and Non-compliant.' },
  { title: 'Compliance Agent on demand', text: 'Run the Compliance Agent for the selected sector, location and company.' },
  { title: 'Filters and search', text: 'Uses the same global search and dropdowns as the Devices page.' },
]

// Milestone 2: the full Non-Compliance report is delivered in the next milestone.
export default function NonCompliancePage() {
  return (
    <>
      <header className="page-header">
        <div>
          <h1>Non-Compliance</h1>
          <p className="subtitle">Detailed compliance report for every discovered device</p>
        </div>
        <span className="pill pill-warn">Milestone 2</span>
      </header>

      <section className="flow-panel" aria-label="Planned for Milestone 2">
        <h2 className="agent-title">Coming in Milestone 2</h2>
        <p className="agent-desc">
          The Compliance Agent already runs in the background: its verdict and the standards each device
          violates are shown on the Devices page. This page will present the full report:
        </p>
        <ol className="flow-steps">
          {PLANNED.map((s, i) => (
            <li key={s.title} className="flow-step">
              <span className="flow-num mono">{i + 1}</span>
              <div>
                <div className="device-name">{s.title}</div>
                <div className="device-desc">{s.text}</div>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </>
  )
}
