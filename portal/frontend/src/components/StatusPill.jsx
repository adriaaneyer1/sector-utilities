const LABELS = {
  online: 'Online',
  streaming: 'Streaming',
  no_stream: 'No stream',
  offline: 'Offline',
  unknown: 'Checking…',
}

const TONES = {
  online: 'good',
  streaming: 'good',
  no_stream: 'warn',
  offline: 'bad',
  unknown: 'muted',
}

export default function StatusPill({ status }) {
  const tone = TONES[status] ?? 'muted'
  return (
    <span className={`pill pill-${tone}`}>
      <span className={`pill-dot dot-${tone}`} aria-hidden="true" />
      {LABELS[status] ?? status}
    </span>
  )
}
