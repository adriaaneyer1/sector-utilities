import { useState } from 'react'
import { fetchAgents, runAgent } from '../api.js'
import usePolling from './usePolling.js'

// Live status of one agent (polled every 1.5 s so its steps appear as they
// happen) plus a run() that starts it and calls onDone with the new report.
export default function useAgent(name, onDone) {
  const { data, error, refresh } = usePolling(fetchAgents, 1500)
  const [starting, setStarting] = useState(false)
  const [runError, setRunError] = useState(null)

  async function run() {
    setStarting(true)
    setRunError(null)
    const pending = runAgent(name)
    setTimeout(refresh, 200) // show "running" right away
    try {
      await pending
      onDone?.()
    } catch (e) {
      setRunError(e.message)
    } finally {
      setStarting(false)
      refresh()
    }
  }

  return { agent: data?.[name], error: error ?? runError, running: starting || data?.[name]?.running, run }
}
