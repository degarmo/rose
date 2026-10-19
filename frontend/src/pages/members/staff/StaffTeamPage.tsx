import { useState } from 'react'
import { ErrorState, LoadingState } from '@/components/content/States'
import { AppButton } from '@/components/members/app/primitives'
import { StaffFrame } from '@/components/members/staff/StaffFrame'
import { FormField, Input, Select, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { ROLE_LABELS, staffApi, type Role, type TeamMember } from '@/lib/safetyApi'
import { useAsync } from '@/lib/useAsync'

const ROLE_OPTIONS = [
  { value: 'moderator', label: 'Moderator: reports and member actions' },
  { value: 'staff', label: 'Staff: also the metrics' },
  { value: 'admin', label: 'Admin: everything, and the team' },
]

/** Admins only: who holds which role. Every change is logged. */
export function StaffTeamPage() {
  const toast = useToast()
  const state = useAsync(() => staffApi.team(), 'staff-team')
  const [current, setCurrent] = useState<TeamMember[] | null>(null)
  const [person, setPerson] = useState('')
  const [role, setRole] = useState<Role>('moderator')
  const [busy, setBusy] = useState(false)
  const team = current ?? (state.status === 'success' ? state.data : null)

  async function change(who: string, next: Role | null, done: string) {
    setBusy(true)
    try {
      setCurrent(await staffApi.setRole(who, next))
      toast.show({ tone: 'success', title: done })
      return true
    } catch (error) {
      toast.show({ tone: 'error', title: 'That did not work', message: error instanceof ApiError ? error.message : undefined })
      return false
    } finally {
      setBusy(false)
    }
  }

  return (
    <StaffFrame title="Team" minimum="admin">
      {state.status === 'loading' && <LoadingState label="Loading the team" />}
      {state.status === 'error' && <ErrorState title="The team did not load" onRetry={state.retry} />}
      {team && (
        <div className="flex max-w-[720px] flex-col gap-6">
          <ul className="divide-y divide-border rounded-app border border-border">
            {team.map((member) => (
              <li key={member.display_name} className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                <span className="font-semibold text-fg">
                  {member.display_name}
                  {member.is_self && <span className="font-normal text-fg-muted"> (you)</span>}
                </span>
                {member.is_superuser || member.is_self ? (
                  <span className="text-sm text-fg-muted">{member.role ? ROLE_LABELS[member.role] : 'No role'}</span>
                ) : (
                  <div className="flex items-center gap-2">
                    <Select
                      aria-label={`Role for ${member.display_name}`}
                      value={member.role ?? 'moderator'}
                      disabled={busy}
                      options={ROLE_OPTIONS.map((option) => ({ value: option.value, label: ROLE_LABELS[option.value as Role] }))}
                      onChange={(e) => void change(member.display_name, e.target.value as Role, 'Role changed')}
                      className="h-9"
                    />
                    <AppButton variant="secondary" disabled={busy} onClick={() => void change(member.display_name, null, 'Removed from the team')}>
                      Remove
                    </AppButton>
                  </div>
                )}
              </li>
            ))}
          </ul>
          <form
            className="flex flex-col gap-3 rounded-app border border-border p-4"
            onSubmit={(event) => {
              event.preventDefault()
              if (!person.trim()) return
              void change(person.trim(), role, 'Added to the team').then((ok) => ok && setPerson(''))
            }}
          >
            <h2 className="text-sm font-semibold text-fg">Add someone</h2>
            <FormField label="Email or display name" required>{(field) => <Input {...field} value={person} onChange={(e) => setPerson(e.target.value)} />}</FormField>
            <label className="flex flex-col gap-1 text-sm font-semibold text-fg">
              Role
              <Select value={role} options={ROLE_OPTIONS} onChange={(e) => setRole(e.target.value as Role)} />
            </label>
            <p className="text-sm text-fg-muted">They set up an authenticator app the first time they open the staff section.</p>
            <AppButton type="submit" className="self-start" disabled={busy || !person.trim()}>
              Add to the team
            </AppButton>
          </form>
        </div>
      )}
    </StaffFrame>
  )
}
