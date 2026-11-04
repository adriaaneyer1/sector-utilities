import ComplianceBadge from './ComplianceBadge.jsx'
import ViolationList from './ViolationList.jsx'

export default function ComplianceCard({ device }) {
  const offBaseline = device.firmware_approved && device.findings.some((f) => f.title.startsWith('Firmware '))
  return (
    <article className="compliance-card">
      <div className="card-head">
        <div>
          <h2 className="card-title">{device.name}</h2>
          <span className="mono muted card-endpoint">{device.protocol} · {device.endpoint}</span>
          <span className="mono muted card-endpoint card-fw">
            Firmware {device.firmware ?? 'not reported'}
            {offBaseline && <> · approved {device.firmware_approved}</>}
          </span>
        </div>
        <ComplianceBadge value={device.status} className="result-badge" />
      </div>

      <div className="findings">
        <span className="findings-label">Findings · {device.findings.length}</span>
        {device.findings.length === 0 && <p className="no-findings">No issues found on the active profile.</p>}
        {device.findings.map((f) => (
          <div className="finding" key={f.title}>
            <span className={`severity sev-${f.severity}`}>{f.severity.toUpperCase()}</span>
            {f.title}
          </div>
        ))}
      </div>

      {device.violations?.length > 0 && (
        <div className="findings">
          <span className="findings-label">Standard &amp; requirement violated</span>
          <ViolationList violations={device.violations} />
        </div>
      )}

      {device.remediation && (
        <div className="remediation">
          <span className="remediation-label">Remediation</span>
          {device.remediation}
        </div>
      )}
    </article>
  )
}
