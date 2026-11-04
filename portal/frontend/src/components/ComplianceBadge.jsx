// The four compliance statuses, best to worst, with their colour tone.
export const STATUSES = [
  { label: 'Compliant', tone: 'good' },
  { label: 'Partially compliant', tone: 'warn' },
  { label: 'Needs change control', tone: 'info' },
  { label: 'Non-compliant', tone: 'bad' },
]

const TONES = Object.fromEntries(STATUSES.map((s) => [s.label, s.tone]))

// Compliance status for a device, from the Compliance Agent's latest report.
export default function ComplianceBadge({ value, className = 'pill' }) {
  const tone = TONES[value] ?? 'muted'
  return <span className={`${className} pill-${tone}`}>{value ?? 'Not assessed'}</span>
}
