export default function StatCard({ label, value, tone }) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <span className={`stat-value ${tone ? `text-${tone}` : ''}`}>{value ?? '–'}</span>
    </div>
  )
}
