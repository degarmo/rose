import { useCallback, useEffect, useRef, useState } from 'react'
import { useAsync } from './useAsync'

export interface CursorPage<T> {
  items: T[]
  nextCursor: string | null
}

type Status = 'loading' | 'idle' | 'error' | 'done'

/**
 * First page through useAsync; later pages appended from callbacks. Returns a
 * callback ref for a sentinel that loads more when it scrolls into view, plus loadMore() for
 * the visible "Load more" button.
 */
export function useCursorList<T>(loader: (cursor: string | null) => Promise<CursorPage<T>>, key: string) {
  const first = useAsync(() => loader(null), key)
  const [extra, setExtra] = useState<{ key: string; items: T[]; cursor: string | null | undefined; status: 'idle' | 'loading' | 'error' }>({
    key,
    items: [],
    cursor: undefined,
    status: 'idle',
  })
  const [replaced, setReplaced] = useState<{ key: string; map: Map<unknown, T>; removed: Set<unknown> }>({
    key,
    map: new Map(),
    removed: new Set(),
  })
  const loaderRef = useRef(loader)
  const loading = useRef(false)
  const [sentinel, setSentinel] = useState<HTMLElement | null>(null)

  useEffect(() => {
    loaderRef.current = loader
  })

  const current = extra.key === key ? extra : { key, items: [], cursor: undefined, status: 'idle' as const }
  const edits = replaced.key === key ? replaced : { key, map: new Map(), removed: new Set() }
  const base = first.status === 'success' ? [...first.data.items, ...current.items] : []
  const cursor = current.cursor !== undefined ? current.cursor : first.status === 'success' ? first.data.nextCursor : null

  const status: Status =
    first.status === 'loading' || current.status === 'loading'
      ? 'loading'
      : first.status === 'error' || current.status === 'error'
        ? 'error'
        : cursor
          ? 'idle'
          : 'done'

  const loadMore = useCallback(async () => {
    if (loading.current || !cursor) return
    loading.current = true
    setExtra((state) => ({ ...(state.key === key ? state : { key, items: [], cursor: undefined }), status: 'loading' }))
    try {
      const page = await loaderRef.current(cursor)
      setExtra((state) => ({
        key,
        items: [...(state.key === key ? state.items : []), ...page.items],
        cursor: page.nextCursor,
        status: 'idle',
      }))
    } catch {
      setExtra((state) => ({ ...(state.key === key ? state : { key, items: [], cursor: undefined }), status: 'error' }))
    } finally {
      loading.current = false
    }
  }, [cursor, key])

  useEffect(() => {
    const element = sentinel
    if (!element || status !== 'idle' || !('IntersectionObserver' in window)) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) void loadMore()
      },
      { rootMargin: '800px 0px' },
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [sentinel, status, loadMore])

  /** Swap in an updated item (after a like or an edit) or drop one (after delete or block). */
  const update = useCallback(
    (id: unknown, next: T | null) => {
      setReplaced((state) => {
        const fresh = state.key === key ? state : { key, map: new Map(), removed: new Set() }
        const map = new Map(fresh.map)
        const removed = new Set(fresh.removed)
        if (next === null) removed.add(id)
        else map.set(id, next)
        return { key, map, removed }
      })
    },
    [key],
  )

  function retry() {
    if (first.status === 'error') first.retry()
    else void loadMore()
  }

  return { base, edits, status, loadMore, retry, bindSentinel: setSentinel, update, cursor }
}

/** Apply in-place edits to a list of items that have an `id`. */
export function applyEdits<T extends { id: unknown }>(items: T[], edits: { map: Map<unknown, T>; removed: Set<unknown> }): T[] {
  return items.filter((item) => !edits.removed.has(item.id)).map((item) => edits.map.get(item.id) ?? item)
}
