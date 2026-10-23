import { fetchDevices } from '../api.js'
import usePolling from './usePolling.js'

export default function useDevices() {
  return usePolling(fetchDevices)
}
