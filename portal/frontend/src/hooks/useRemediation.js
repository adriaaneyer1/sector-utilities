import { fetchRemediation } from '../api.js'
import usePolling from './usePolling.js'

export default function useRemediation() {
  return usePolling(fetchRemediation)
}
