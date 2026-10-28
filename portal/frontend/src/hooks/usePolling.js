import { useCallback, useEffect, useRef, useState } from 'react'

// Calls fetcher(signal) now and every intervalMs. Keeps the last good data on
// screen if a request fails, and exposes the error separately.
export default function usePolling(fetcher, intervalMs = 5000) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const controller = useRef(null)

  const refresh = useCallback(async () => {
    controller.current?.abort()
    controller.current = new AbortController()
    try {
      setData(await fetcher(controller.current.signal))
      setError(null)
    } catch (e) {
      if (e.name !== 'AbortError') setError(e.message)
    }
  }, [fetcher])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, intervalMs)
    return () => {
      clearInterval(id)
      controller.current?.abort()
    }
  }, [refresh, intervalMs])

  return { data, error, refresh }
}
