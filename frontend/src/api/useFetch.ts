import { useEffect, useState } from 'react'

interface FetchState<T> {
  data: T | null
  error: string | null
  loading: boolean
}

/** Liten delad hook: kör `fetcher` en gång, exponera loading/error/data. */
export function useFetch<T>(fetcher: () => Promise<T>): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ data: null, error: null, loading: true })

  useEffect(() => {
    let cancelled = false
    setState({ data: null, error: null, loading: true })

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ data, error: null, loading: false })
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({ data: null, error: err instanceof Error ? err.message : String(err), loading: false })
        }
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return state
}
