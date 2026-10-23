// Standards a device breaks, e.g. "NERC CIP-012-2 (Data Protection in Transit)".
export default function ViolationList({ violations }) {
  if (!violations?.length) return <span className="muted">—</span>
  return (
    <ul className="violation-list">
      {violations.map((v) => (
        <li key={v.standard} title={v.vector}>
          <span className="violation-standard">{v.standard}</span>
          <span className="violation-requirement">{v.requirement}</span>
        </li>
      ))}
    </ul>
  )
}
