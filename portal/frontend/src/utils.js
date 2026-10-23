export function formatTime(unixSeconds) {
  if (!unixSeconds) return '—'
  return new Date(unixSeconds * 1000).toLocaleTimeString([], { hour12: false })
}
