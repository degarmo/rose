import { useState } from 'react'
import { Link } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { Avatar } from '@/components/members/Avatar'
import { FormField, Input } from '@/components/ui'
import { members } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const MIN_QUERY = 3

export function DirectoryPage() {
  useDocumentMeta({ title: 'Search', noindex: true })
  const [query, setQuery] = useState('')
  const trimmed = query.trim()
  const ready = trimmed.length >= MIN_QUERY
  const state = useAsync(() => (ready ? members.directory(trimmed) : Promise.resolve({ results: [], min_query: MIN_QUERY })), ready ? trimmed : '')

  return (
    <div>
      <h1 className="text-2xl text-fg">Search</h1>
      <p className="mt-1 text-sm text-fg-muted">Search by display name. Only members who chose to be listed appear, and there is no browsing the full list.</p>
      <div className="mt-6" role="search">
        <FormField label="Display name" hint={`Type at least ${MIN_QUERY} characters.`} optionalLabel="">
          {(field) => <Input {...field} type="search" autoComplete="off" spellCheck={false} value={query} onChange={(e) => setQuery(e.target.value)} />}
        </FormField>
      </div>
      <div className="mt-6" aria-live="polite">
        {ready && state.status === 'loading' && <LoadingState label="Searching" />}
        {state.status === 'error' && <ErrorState title="Search did not work" onRetry={state.retry} />}
        {ready && state.status === 'success' && state.data.results.length === 0 && <p className="text-sm text-fg-subtle">Nobody listed matches that.</p>}
        {state.status === 'success' && state.data.results.length > 0 && (
          <ul className="flex flex-col">
            {state.data.results.map((member) => (
              <li key={member.handle}>
                <Link
                  to={`/members/u/${encodeURIComponent(member.handle)}`}
                  className="-mx-2 flex min-h-14 items-center gap-3 rounded-lg px-2 py-2 text-sm font-semibold text-fg hover:bg-primary-deep"
                >
                  <Avatar member={member} size="md" />
                  {member.handle}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
