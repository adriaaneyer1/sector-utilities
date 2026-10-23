import { createContext, useContext, useEffect, useState } from 'react'
import { fetchFilters } from '../api.js'

// Global search shared by every page: free-text query plus
// sector / location / company dropdowns ('' = all).
const FilterContext = createContext(null)

const EMPTY_OPTIONS = { sectors: [], locations: [], companies: [] }

export function FilterProvider({ children }) {
  const [options, setOptions] = useState(EMPTY_OPTIONS)
  const [filters, setFilters] = useState({ query: '', sector: '', location: '', company: '' })

  useEffect(() => {
    const controller = new AbortController()
    // nothing is pre-selected: the user picks sector, location and company
    fetchFilters(controller.signal).then(setOptions).catch(() => {})
    return () => controller.abort()
  }, [])

  const update = (key, value) => setFilters((f) => ({ ...f, [key]: value }))

  return <FilterContext.Provider value={{ options, filters, update }}>{children}</FilterContext.Provider>
}

export function useFilters() {
  return useContext(FilterContext)
}

// True when an item matches the dropdowns and the search text.
// `fields` lists the item properties the free-text query looks in.
export function matchesFilters(item, filters, fields) {
  if (filters.sector && item.sector !== filters.sector) return false
  if (filters.location && item.location !== filters.location) return false
  if (filters.company && item.company !== filters.company) return false
  const q = filters.query.trim().toLowerCase()
  if (!q) return true
  return fields.some((f) => String(item[f] ?? '').toLowerCase().includes(q))
}
