import { NavLink } from 'react-router-dom'

function DevicesIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="6" rx="1.5" />
      <rect x="3" y="14" width="18" height="6" rx="1.5" />
      <path d="M7 7h.01M7 17h.01" />
    </svg>
  )
}

function ShieldAlertIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6z" />
      <path d="M12 8v4M12 16h.01" />
    </svg>
  )
}

function ShieldCheckIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  )
}

export default function Sidebar() {
  return (
    <nav className="sidebar" aria-label="Main">
      <div className="brand">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
          <path d="M16 4 L29 27 H3 Z" stroke="var(--accent)" strokeWidth="2.4" strokeLinejoin="round" />
          <path d="M16 13 V20" stroke="var(--accent)" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
        <div>
          <div className="brand-name">DELTASTREAM AI</div>
          <div className="brand-sub">Compliance Portal</div>
        </div>
      </div>

      <div className="nav-links">
        <NavLink to="/devices" className="nav-link"><DevicesIcon />Devices</NavLink>
        <NavLink to="/non-compliance" className="nav-link"><ShieldAlertIcon />Non-Compliance</NavLink>
        <NavLink to="/compliance" className="nav-link"><ShieldCheckIcon />Compliance</NavLink>
      </div>

      <div className="env-box">
        Environment
        <strong>Local lab · agent-discovered</strong>
      </div>
    </nav>
  )
}
