import { useId, useState } from 'react'
import { Link, useParams } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { AppButton } from '@/components/members/app/primitives'
import { StaffFrame } from '@/components/members/staff/StaffFrame'
import { FormField, Textarea, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { formatDay } from '@/lib/format'
import { staffApi, type Appeal } from '@/lib/safetyApi'
import { useAsync } from '@/lib/useAsync'
import { NotFoundPage } from '@/pages/NotFoundPage'

function Decide({ appeal, onDone }: { appeal: Appeal; onDone: (next: Appeal) => void }) {
  const toast = useToast()
  const groupId = useId()
  const [decision, setDecision] = useState<'uphold' | 'reverse' | ''>('')
  const [note, setNote] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  if (!appeal.may_decide) {
    return <p className="text-sm text-fg-muted">You took this action, so someone else on the team reviews the appeal.</p>
  }

  async function submit() {
    if (!decision) return setError('Choose to uphold or reverse the decision.')
    if (!note.trim()) return setError('Give a reason for the decision.')
    setBusy(true)
    try {
      onDone(await staffApi.decide(appeal.id, decision, note.trim()))
      toast.show({ tone: 'success', title: decision === 'reverse' ? 'Reversed' : 'Upheld', message: 'The member has been told, and it is in the log.' })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'That did not work. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <fieldset>
        <legend className="mb-2 text-sm font-semibold text-fg">Decision</legend>
        <div className="flex flex-wrap gap-2">
          {(
            [
              ['uphold', 'Uphold the decision'],
              ['reverse', 'Reverse it'],
            ] as const
          ).map(([value, label]) => (
            <label key={value} className="flex items-center gap-2 rounded-app border border-border px-3 py-2 text-sm has-[:checked]:border-fg">
              <input type="radio" name={`${groupId}-decision`} value={value} checked={decision === value} onChange={() => setDecision(value)} className="accent-[var(--color-primary)]" />
              {label}
            </label>
          ))}
        </div>
      </fieldset>
      <FormField label="Reason" hint="The member reads this on their account page." required error={error}>
        {(field) => <Textarea {...field} rows={3} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />}
      </FormField>
      <AppButton className="self-start" onClick={() => void submit()} disabled={busy}>
        {busy ? 'Saving' : 'Record decision'}
      </AppButton>
    </div>
  )
}

/** One appeal: what the member wrote, the action, and the decision by someone other than who acted. */
export function StaffAppealPage() {
  const { id = '' } = useParams()
  const appealId = Number(id)
  const state = useAsync(() => staffApi.appeal(appealId), `appeal:${appealId}`)
  const [current, setCurrent] = useState<Appeal | null>(null)
  const appeal = current?.id === appealId ? current : state.status === 'success' ? state.data : null

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) return <NotFoundPage />

  return (
    <StaffFrame title="Appeal">
      <Link to="/members/staff/reports?tab=appeals" className="text-sm font-semibold text-link">
        Back to appeals
      </Link>
      {state.status === 'loading' && <LoadingState label="Loading the appeal" />}
      {state.status === 'error' && <ErrorState title="The appeal did not load" onRetry={state.retry} />}
      {appeal && (
        <div className="mt-3 flex max-w-[640px] flex-col gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Appeal · {appeal.status_label}</p>
            <p className="text-lg font-semibold text-fg">
              {appeal.action.kind_label}
              {appeal.action.member && (
                <>
                  {' · '}
                  <Link to={`/members/staff/members/${encodeURIComponent(appeal.action.member.display_name)}`} className="text-link">
                    {appeal.action.member.display_name}
                  </Link>
                </>
              )}
            </p>
            <p className="text-sm text-fg-muted">
              Sent {formatDay(appeal.created_at)}
              {appeal.assigned_to && ` · for ${appeal.assigned_to.display_name}`}
            </p>
          </div>
          <section aria-label="What the member wrote" className="rounded-app border border-border p-4">
            <h2 className="text-sm font-semibold text-fg">What the member wrote</h2>
            <p className="mt-1 whitespace-pre-line text-fg">{appeal.text}</p>
          </section>
          <section aria-label="The action" className="rounded-app border border-border p-4">
            <h2 className="text-sm font-semibold text-fg">The action</h2>
            <p className="mt-1 text-sm text-fg-muted">
              {appeal.action.rule} · {formatDay(appeal.action.created_at)}
              {appeal.action.created_by && ` · by ${appeal.action.created_by.display_name}`}
              {appeal.action.ends_at && ` · until ${formatDay(appeal.action.ends_at)}`}
            </p>
            <p className="mt-1 text-fg">{appeal.action.reason}</p>
          </section>
          <section aria-label="Decision" className="rounded-app border border-border p-4">
            {appeal.status === 'open' ? (
              <Decide appeal={appeal} onDone={setCurrent} />
            ) : (
              <p className="text-fg">
                {appeal.status_label}
                {appeal.decided_by && ` by ${appeal.decided_by.display_name}`}
                {appeal.decided_at && `, ${formatDay(appeal.decided_at)}`}: {appeal.decision_note}
              </p>
            )}
          </section>
        </div>
      )}
    </StaffFrame>
  )
}
