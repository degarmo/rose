import { useState } from 'react'
import { Link } from 'react-router'
import { AppButton } from '@/components/members/app/primitives'
import { Button, FormField, Modal, Textarea, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { formatDay } from '@/lib/format'
import { staffApi, type MemberActionData } from '@/lib/safetyApi'

function ReverseDialog({ action, onClose, onDone }: { action: MemberActionData; onClose: () => void; onDone: (next: MemberActionData) => void }) {
  const toast = useToast()
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  async function submit() {
    if (!reason.trim()) return setError('Give a reason for reversing it.')
    setBusy(true)
    try {
      const next = await staffApi.reverse(action.id, reason.trim())
      toast.show({ tone: 'success', title: 'Reversed', message: 'The member has been told, and it is in the log.' })
      onDone(next)
      onClose()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'That did not work. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Reverse this ${action.kind_label.toLowerCase()}?`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={busy} aria-busy={busy}>
            {busy ? 'Saving' : 'Reverse'}
          </Button>
        </>
      }
    >
      <p className="mb-4 text-fg-muted">It is undone straight away. The log keeps both the action and its reversal.</p>
      <FormField label="Reason" required error={error}>
        {(field) => <Textarea {...field} rows={3} maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)} />}
      </FormField>
    </Modal>
  )
}

/** A member's actions, newest first, each reversible until it is reversed. */
export function ActionList({ actions, onChange, showMember = false }: { actions: MemberActionData[]; onChange: (next: MemberActionData) => void; showMember?: boolean }) {
  const [reversing, setReversing] = useState<MemberActionData | null>(null)
  if (actions.length === 0) return <p className="text-sm text-fg-muted">No actions yet.</p>
  return (
    <>
      <ul className="divide-y divide-border rounded-app border border-border">
        {actions.map((action) => (
          <li key={action.id} className="flex flex-col gap-1 p-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <p className="font-semibold text-fg">
                {action.kind_label}
                {showMember && action.member && (
                  <>
                    {' · '}
                    <Link to={`/members/staff/members/${encodeURIComponent(action.member.display_name)}`} className="text-link">
                      {action.member.display_name}
                    </Link>
                  </>
                )}
              </p>
              <p className="text-sm text-fg-muted">
                {action.rule} · {formatDay(action.created_at)}
                {action.created_by && ` · by ${action.created_by.display_name}`}
                {action.ends_at && ` · until ${formatDay(action.ends_at)}`}
              </p>
              <p className="mt-1 text-sm text-fg">{action.reason}</p>
              {action.reversed_at && (
                <p className="mt-1 text-sm text-fg-muted">
                  Reversed {formatDay(action.reversed_at)}
                  {action.reversed_by && ` by ${action.reversed_by.display_name}`}: {action.reversal_reason}
                </p>
              )}
              {action.appeal && <p className="mt-1 text-sm text-fg-muted">Appeal: {action.appeal.status_label}</p>}
            </div>
            {!action.reversed_at && (
              <AppButton variant="secondary" className="self-start" onClick={() => setReversing(action)}>
                Reverse
              </AppButton>
            )}
          </li>
        ))}
      </ul>
      {reversing && <ReverseDialog action={reversing} onClose={() => setReversing(null)} onDone={onChange} />}
    </>
  )
}
