import { Search, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { members } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { cn } from '@/lib/cn'
import { Avatar } from '../Avatar'
import { LeaveButton } from './Nav'
import { profilePath } from './postUtils'

const MIN_QUERY = 3

/**
 * Search by display name. The directory rules apply: at least three characters, and
 * members who hid themselves never appear. There is no way to browse everyone.
 */
export function SearchContent({
  onNavigate,
  autoFocus = false,
  onCancel,
}: {
  onNavigate?: () => void
  autoFocus?: boolean
  /** Phones: a Cancel button beside the field (design: Search · phone). */
  onCancel?: () => void
}) {
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
      <div className={onCancel ? 'flex items-center gap-3 px-4 py-1' : 'mx-4 my-6'}>
        <label htmlFor={inputId} className="sr-only">
          Search members by display name
        </label>
        <div className={cn('flex flex-1 items-center gap-2 rounded-app bg-field text-fg', onCancel ? 'h-9 px-3' : 'h-10 px-4')}>
          {onCancel && <Search aria-hidden="true" strokeWidth={1.8} className="size-4 shrink-0 text-fg-muted" />}
          <input
            ref={input}
            id={inputId}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search members"
            autoComplete="off"
            spellCheck={false}
            className="min-w-0 flex-1 bg-transparent text-sm text-fg placeholder:text-fg-muted focus:outline-none [&::-webkit-search-cancel-button]:hidden"
          />
          {query && (
            <button type="button" onClick={() => setQuery('')} className="inline-flex size-6 items-center justify-center rounded-full text-fg">
              <X aria-hidden="true" className="size-4" />
              <span className="sr-only">Clear search</span>
            </button>
          )}
        </div>
        {onCancel && (
          <>
            <button type="button" onClick={onCancel} className="font-semibold text-fg">
              Cancel
            </button>
            {/* The quick exit stays on every screen. */}
            <LeaveButton className="-ml-1 -mr-2" />
          </>
        )}
      </div>
      <div className={cn('min-h-0 flex-1 overflow-y-auto pt-2', !onCancel && 'border-t border-border pt-3')} aria-live="polite">
        {!ready && (
          <p className={cn('py-2 text-fg-muted', onCancel ? 'px-4' : 'px-6')}>Type at least {MIN_QUERY} characters of a display name. Members who chose not to be listed never appear.</p>
        )}
        {ready && state.status === 'loading' && <LoadingState label="Searching" />}
        {state.status === 'error' && <ErrorState title="Search did not work" onRetry={state.retry} />}
        {ready && state.status === 'success' && state.data.results.length === 0 && <p className={cn('py-2 text-fg-muted', onCancel ? 'px-4' : 'px-6')}>Nobody listed matches that.</p>}
        {state.status === 'success' && state.data.results.length > 0 && (
          <ul>
            {state.data.results.map((member) => (
              <li key={member.handle}>
                <Link to={profilePath(member.handle)} onClick={onNavigate} className={cn('flex items-center gap-3 py-2 hover:bg-surface', onCancel ? 'px-4' : 'px-6')}>
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
