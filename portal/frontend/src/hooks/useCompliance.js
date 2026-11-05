import { fetchCompliance } from '../api.js'
import usePolling from './usePolling.js'

export default function useCompliance() {
  return usePolling(fetchCompliance)
}
