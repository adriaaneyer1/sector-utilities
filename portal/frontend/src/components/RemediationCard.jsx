import ComplianceBadge from './ComplianceBadge.jsx'

export const STAGES = [
  { key: 'check_version', title: 'Check version' },
  { key: 'check_repository', title: 'Check repository' },
  { key: 'apply_update', title: 'Apply update' },
  { key: 'reboot', title: 'Reboot' },
  { key: 'recheck', title: 'Re-check' },
  { key: 'report', title: 'Report' },
]

const MARKS = { pending: '', running: '', done: '✓', skipped: '–', failed: '✕' }

const OUTCOME_LABEL = {
  remediated: 'Remediated',
  change_control: 'Change approval required',
  manual: 'Manual action needed',
  failed: 'Update failed',
}

// One device's walk through the remediation flow. `device` is either a live
// progress entry ({name, stages}) or a finished report entry (adds before/after).
export default function RemediationCard({ device }) {
  const { before, after, outcome } = device
  return (
    <article className={`compliance-card remediation-card ${outcome ? `outcome-${outcome}` : ''}`}>
      <div className="card-head">
        <div>
          <h2 className="card-title">{device.name}</h2>
          {device.endpoint && <span className="mono muted card-endpoint">{device.protocol} · {device.endpoint}</span>}
        </div>
        {outcome && <span className={`outcome-label outcome-label-${outcome}`}>{OUTCOME_LABEL[outcome]}</span>}
      </div>

      {before && (
        <div className="before-after">
          <div>
            <span className="findings-label">Before</span>
            <ComplianceBadge value={before.status} />
            <span className="mono muted card-endpoint">{before.firmware ?? 'firmware not reported'}</span>
          </div>
          <span className="before-after-arrow" aria-hidden="true">→</span>
          <div>
            <span className="findings-label">After</span>
            <ComplianceBadge value={after.status} />
            <span className="mono muted card-endpoint">{after.firmware ?? 'firmware not reported'}</span>
          </div>
        </div>
      )}

      <ol className="pipeline" aria-label={`Remediation steps for ${device.name}`}>
        {STAGES.map((s) => {
          const stage = device.stages?.[s.key] ?? { state: 'pending' }
          return (
            <li key={s.key} className={`pipeline-step is-${stage.state}`}>
              <span className="pipeline-mark" aria-hidden="true">{MARKS[stage.state]}</span>
              <div className="pipeline-text">
                <span className="pipeline-title">{s.title}</span>
                {stage.detail && <span className="pipeline-detail">{stage.detail}</span>}
                <span className="visually-hidden">{stage.state}</span>
              </div>
            </li>
          )
        })}
      </ol>

      {before && after.findings.length > 0 && (
        <div className="findings">
          <span className="findings-label">Still open · {after.findings.length}</span>
          {after.findings.map((f) => (
            <div className="finding" key={f.code}>
              <span className={`severity sev-${f.severity}`}>{f.severity.toUpperCase()}</span>
              {f.title}
            </div>
          ))}
        </div>
      )}
    </article>
  )
}
