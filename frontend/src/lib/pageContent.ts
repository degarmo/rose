import { useAsync } from './useAsync'
import { request } from './api'

export type CopyFormat = 'plain' | 'rich'

export interface CopyEntry {
  value: string
  format: CopyFormat
}

export interface PageContentResponse {
  page: string
  entries: Record<string, CopyEntry>
}

const cache = new Map<string, Promise<PageContentResponse>>()

/** One request per page per visit; a failed request is forgotten so Try again works. */
export function fetchPageContent(page: string): Promise<PageContentResponse> {
  let pending = cache.get(page)
  if (!pending) {
    pending = request<PageContentResponse>(`/content/${encodeURIComponent(page)}/`).catch((error: unknown) => {
      cache.delete(page)
      throw error
    })
    cache.set(page, pending)
  }
  return pending
}

/** Test helper: forget every cached page. */
export function clearPageContentCache() {
  cache.clear()
}

export interface PageCopy {
  status: 'loading' | 'success' | 'error'
  retry: () => void
  /** The entry for a key, or null when it is missing (or still loading). */
  entry: (key: string) => CopyEntry | null
  /** Plain text for a key; '' when missing or still loading. */
  text: (key: string) => string
  /** The numbers n for which `${prefix}.${n}` or `${prefix}.${n}.*` exists, in order. */
  items: (prefix: string) => number[]
}

/**
 * Staff-editable copy for one page, from /api/content/<page>/. Pages render
 * skeletons while it loads; they keep no copy of their own.
 */
export function usePageContent(page: string): PageCopy {
  const state = useAsync(() => fetchPageContent(page), `copy:${page}`)
  const entries = state.status === 'success' ? state.data.entries : {}
  return {
    status: state.status,
    retry: state.retry,
    entry: (key) => entries[key] ?? null,
    text: (key) => entries[key]?.value ?? '',
    items: (prefix) => {
      const found = new Set<number>()
      const pattern = new RegExp(`^${prefix.replace(/\./g, '\\.')}\\.(\\d+)(?:\\.|$)`)
      for (const key of Object.keys(entries)) {
        const match = pattern.exec(key)
        if (match) found.add(Number(match[1]))
      }
      return [...found].sort((a, b) => a - b)
    },
  }
}
