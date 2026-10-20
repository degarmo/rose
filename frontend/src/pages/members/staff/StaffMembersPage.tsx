import { useId, useState } from 'react'
import { Link, useParams } from 'react-router'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { AppButton } from '@/components/members/app/primitives'
import { ActionDialog } from '@/components/members/staff/ActionDialog'
import { ActionList } from '@/components/members/staff/ActionList'
import { StaffFrame } from '@/components/members/staff/StaffFrame'
import { Input } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { formatDay } from '@/lib/format'
import { staffApi, type StaffMember } from '@/lib/safetyApi'
import { useAsync } from '@/lib/useAsync'
import { NotFoundPage } from '@/pages/NotFoundPage'

/** Find a member by display name. */
export function StaffMembersPage() {
  const searchId = useId()
  const [query, setQuery] = useState('')
  const trimmed = query.trim()
  const results = useAsync(() => (trimmed.length >= 2 ? staffApi.searchMembers(trimmed) : Promise.resolve([])), `staff-search:${trimmed}`)

  return (
    <StaffFrame title="Members">
      <label htmlFor={searchId} className="text-sm font-semibold text-fg">
        Display name
      </label>
      <Input id={searchId} type="search" className="mt-1 max-w-[420px]" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="At least two letters" />
      <div className="mt-4">
        {trimmed.length < 2 && <p className="text-sm text-fg-muted">Type at least two letters of a display name to find a member and see their record.</p>}
        {results.status === 'error' && <ErrorState title="The search did not work" onRetry={results.retry} />}
        {results.status === 'success' && trimmed.length >= 2 && results.data.length === 0 && <EmptyState title="Nobody found" message="Check the spelling of the display name." />}
        {results.status === 'success' && results.data.length > 0 && (
          <ul className="divide-y divide-border rounded-app border border-border">
            {results.data.map((person) => (
              <li key={person.display_name}>
                <Link to={`/members/staff/members/${encodeURIComponent(person.display_name)}`} className="flex min-h-12 items-center px-3 font-semibold text-fg hover:bg-surface">
                  {person.display_name}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </StaffFrame>
  )
}

function Flags({ member }: { member: StaffMember }) {
  const flags = [
    member.flags.banned && 'Banned: Do not admit',
    member.flags.feed_suspended_until && `Feed suspended until ${formatDay(member.flags.feed_suspended_until)}`,
    member.flags.events_suspended_until && `Events suspended until ${formatDay(member.flags.events_suspended_until)}`,
  ].filter(Boolean)
  if (flags.length === 0) return <p className="text-sm text-fg-muted">No restrictions in force.</p>
  return (
    <ul className="flex flex-wrap gap-2">
      {flags.map((flag) => (
        <li key={String(flag)} className="rounded-full bg-tint px-3 py-1 text-sm font-semibold text-tint-fg">
          {flag}
        </li>
      ))}
    </ul>
  )
}

/** A member's staff view: their restrictions, reports about them and actions. Never their activity. */
export function StaffMemberPage() {
  const { handle = '' } = useParams()
  const state = useAsync(() => staffApi.member(handle), `staff-member:${handle}`)
  const [current, setCurrent] = useState<StaffMember | null>(null)
  const [acting, setActing] = useState(false)
  const member = current?.display_name.toLowerCase() === handle.toLowerCase() ? current : state.status === 'success' ? state.data : null
  const reload = () => void staffApi.member(handle).then(setCurrent)

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) return <NotFoundPage />

  return (
    <StaffFrame title={member?.display_name ?? 'Member'}>
      <Link to="/members/staff/members" className="text-sm font-semibold text-link">
        Back to members
      </Link>
      {state.status === 'loading' && <LoadingState label="Loading" />}
      {state.status === 'error' && <ErrorState title="This member did not load" onRetry={state.retry} />}
      {member && (
        <div className="mt-3 flex max-w-[720px] flex-col gap-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-lg font-semibold text-fg">{member.display_name}</p>
              <p className="text-sm text-fg-muted">
                {member.membership ? `${member.membership.tier} · ${member.membership.status}` : 'No open membership'} ·{' '}
                {member.reports_about === 0 ? 'no reports about them' : `${member.reports_about} ${member.reports_about === 1 ? 'report' : 'reports'} about them`}
              </p>
              <p className="text-sm text-fg-muted">
                {member.age_verified ? 'ID verified' : 'ID check needed'}
                {member.feed_access && ` · Feed access: ${member.feed_access}`}
              </p>
            </div>
            <AppButton onClick={() => setActing(true)}>Take action</AppButton>
          </div>
          <Flags member={member} />
          <section aria-label="Actions" className="flex flex-col gap-2">
            <h2 className="text-sm font-semibold text-fg">Actions</h2>
            <ActionList actions={member.actions} onChange={reload} />
          </section>
          <ActionDialog open={acting} onClose={() => setActing(false)} handle={member.display_name} onDone={reload} />
        </div>
      )}
    </StaffFrame>
  )
}
