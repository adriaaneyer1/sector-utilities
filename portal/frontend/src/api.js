// Empty base = same origin (Vite proxy in dev, FastAPI in production).
// Set VITE_API_BASE to point the frontend at a backend on another host.
const API_BASE = import.meta.env.VITE_API_BASE ?? ''

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) throw new Error(`API responded ${res.status}`)
  return res.json()
}

// Latest Discovery Agent report
export function fetchDevices(signal) {
  return request('/api/devices', { signal })
}

// Latest Compliance Agent report
export function fetchCompliance(signal) {
  return request('/api/compliance', { signal })
}

// Sector / location / company options for the global search
export function fetchFilters(signal) {
  return request('/api/filters', { signal })
}

// Status and live activity of every agent
export function fetchAgents(signal) {
  return request('/api/agents', { signal })
}

export function runAgent(name) {
  return request(`/api/agents/${name}/run`, { method: 'POST' })
}
