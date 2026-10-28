const STEPS = [
  { title: 'Check version', text: 'Read the firmware version each device reports.' },
  { title: 'Check repository', text: 'Look up the latest approved firmware for that device.' },
  { title: 'Apply update', text: 'Install the new firmware on the non-compliant device.' },
  { title: 'Reboot', text: 'Restart the device so the new firmware takes effect.' },
  { title: 'Re-check', text: 'Run the compliance checks again on the updated device.' },
  { title: 'Report', text: 'Publish the new status: Compliant, Partially compliant, Needs change control or Non-compliant.' },
]

// Milestone 3: the AI model that fixes non-compliant devices;
// this page shows the flow it will run.
export default function CompliancePage() {
  return (
    <>
      <header className="page-header">
        <div>
          <h1>Compliance</h1>
          <p className="subtitle">The AI model brings non-compliant devices into compliance</p>
        </div>
        <span className="pill pill-warn">Milestone 3</span>
      </header>

      <section className="flow-panel" aria-label="AI remediation flow">
        <h2 className="agent-title">AI Remediation Agent</h2>
        <p className="agent-desc">For every non-compliant device, the agent runs these steps on its own:</p>
        <ol className="flow-steps">
          {STEPS.map((s, i) => (
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
