const TONES = {
  'Compliant': 'good',
  'Non-Compliant': 'bad',
}

// Compliance verdict for a device, from the Compliance Agent's latest report.
export default function ComplianceBadge({ value }) {
  const tone = TONES[value] ?? 'muted'
  return <span className={`pill pill-${tone}`}>{value ?? 'Not assessed'}</span>
}
