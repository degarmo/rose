import { useCallback, useEffect, useRef, useState } from 'react'

export type AsyncState<T> =
  | { status: 'loading'; data: null; error: null }
  | { status: 'success'; data: T; error: null }
  | { status: 'error'; data: null; error: Error }

const LOADING = { status: 'loading', data: null, error: null } as const

/**
 * Run an async loader whenever `key` changes. Each result is tagged with the
 * request it answers, so a stale response never shows over a newer one and
 * the state reads as loading the moment the key changes.
 */
export function useAsync<T>(loader: () => Promise<T>, key: string) {
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState<{ request: string; state: AsyncState<T> } | null>(null)
  const loaderRef = useRef(loader)
  const request = `${key}#${attempt}`

  useEffect(() => {
    loaderRef.current = loader
  })

  useEffect(() => {
    let active = true
    loaderRef.current().then(
      (data) => {
        if (active) setResult({ request, state: { status: 'success', data, error: null } })
      },
      (error: unknown) => {
        if (!active) return
        const normalized = error instanceof Error ? error : new Error(String(error))
        setResult({ request, state: { status: 'error', data: null, error: normalized } })
      },
    )
    return () => {
      active = false
    }
  }, [request])

  const retry = useCallback(() => setAttempt((n) => n + 1), [])
  const state: AsyncState<T> = result?.request === request ? result.state : LOADING
  return { ...state, retry }
}
