import { useFilters } from '../context/FilterContext.jsx'
import Dropdown from './Dropdown.jsx'

export default function GlobalSearch() {
  const { options, filters, update } = useFilters()

  return (
    <section className="global-search" aria-label="Global search">
      <div className="filter-field search-field">
        <label htmlFor="global-query">Global search</label>
        <div className="search-input">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.5-3.5" />
          </svg>
          <input
            id="global-query"
            type="search"
            placeholder="Search devices, firmware, protocol…"
            value={filters.query}
            onChange={(e) => update('query', e.target.value)}
          />
        </div>
      </div>
      <Dropdown label="Sector" placeholder="Select sector" value={filters.sector}
        options={options.sectors} onChange={(v) => update('sector', v)} />
      <Dropdown label="Location" placeholder="Select location" value={filters.location}
        options={options.locations} onChange={(v) => update('location', v)} />
      <Dropdown label="Company" placeholder="Select company" value={filters.company}
        options={options.companies} onChange={(v) => update('company', v)} />
    </section>
  )
}
