import { Search, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { members } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { Avatar } from '../Avatar'
import { profilePath } from './postUtils'

const MIN_QUERY = 3

/**
 * Search by display name. The directory rules apply: at least three characters, and
 * members who hid themselves never appear. There is no way to browse everyone.
 */
export function SearchContent({ onNavigate, autoFocus = false }: { onNavigate?: () => void; autoFocus?: boolean }) {
  const inputId = useId()
  const input = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const trimmed = query.trim()
  const ready = trimmed.length >= MIN_QUERY
  const state = useAsync(
    () => (ready ? members.directory(trimmed) : Promise.resolve({ results: [], min_query: MIN_QUERY })),
    ready ? trimmed : '',
  )

  useEffect(() => {
    // Opening the desktop panel is a request to type.
    if (autoFocus) input.current?.focus()
  }, [autoFocus])

  return (
    <div role="search" className="flex min-h-0 flex-1 flex-col">
      <div className="px-4 pb-6">
        <label htmlFor={inputId} className="sr-only">
          Search members by display name
        </label>
        <div className="flex h-10 items-center gap-2 rounded-lg bg-hover px-4 text-fg">
          <Search aria-hidden="true" className="size-4 shrink-0 text-fg-muted" />
          <input
            ref={input}
            id={inputId}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search"
            autoComplete="off"
            spellCheck={false}
            className="min-w-0 flex-1 bg-transparent text-sm text-fg placeholder:text-[#525252] dark:placeholder:text-fg-muted focus:outline-none [&::-webkit-search-cancel-button]:hidden"
          />
          {query && (
            <button type="button" onClick={() => setQuery('')} className="inline-flex size-6 items-center justify-center rounded-full text-fg">
              <X aria-hidden="true" className="size-4" />
              <span className="sr-only">Clear search</span>
            </button>
          )}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto border-t border-border pt-3" aria-live="polite">
        {!ready && (
          <p className="px-6 py-2 text-fg-muted">Type at least {MIN_QUERY} characters of a display name. Members who chose not to be listed never appear.</p>
        )}
        {ready && state.status === 'loading' && <LoadingState label="Searching" />}
        {state.status === 'error' && <ErrorState title="Search did not work" onRetry={state.retry} />}
        {ready && state.status === 'success' && state.data.results.length === 0 && <p className="px-6 py-2 text-fg-muted">Nobody listed matches that.</p>}
        {state.status === 'success' && state.data.results.length > 0 && (
          <ul>
            {state.data.results.map((member) => (
              <li key={member.handle}>
                <Link to={profilePath(member.handle)} onClick={onNavigate} className="flex min-h-[60px] items-center gap-3 px-6 py-2 hover:bg-surface">
                  <Avatar member={member} size="md" />
                  <span className="font-semibold text-fg">{member.handle}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
