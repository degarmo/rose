import { useEffect, useId, useState } from 'react'
import { Button, Checkbox, FormField, Input, Modal, Textarea, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { staffApi, type ActionKind, type MemberActionData } from '@/lib/safetyApi'

const KINDS: Array<{ value: ActionKind; label: string; hint: string }> = [
  { value: 'warning', label: 'Warning', hint: 'A notice in the app and a discreet email, naming the rule.' },
  { value: 'remove_content', label: 'Remove content', hint: 'Takes the reported post or comment down.' },
  { value: 'feed_suspension', label: 'Feed suspension', hint: 'The member app closes for them until it ends.' },
  { value: 'event_suspension', label: 'Event suspension', hint: 'No RSVPs, and the door desk shows the flag.' },
  { value: 'ban', label: 'Ban', hint: 'Ends their membership, closes the app and shows Do not admit at the door.' },
]

const LENGTHS = [
  { value: '7', label: '7 days' },
  { value: '30', label: '30 days' },
  { value: 'custom', label: 'Until a date' },
]

interface ActionDialogProps {
  open: boolean
  onClose: () => void
  handle: string
  /** From a report: its id, and whether it is about a post or comment (so content can be removed). */
  reportId?: number
  canRemoveContent?: boolean
  onDone: (action: MemberActionData) => void
}

/** Take an action on a member. A reason and the rule it relates to are always required. */
export function ActionDialog({ open, onClose, handle, reportId, canRemoveContent = false, onDone }: ActionDialogProps) {
  const toast = useToast()
  const groupId = useId()
  const rulesId = useId()
  const [kind, setKind] = useState<ActionKind>('warning')
  const [rule, setRule] = useState('')
  const [reason, setReason] = useState('')
  const [length, setLength] = useState('7')
  const [until, setUntil] = useState('')
  const [blockEmail, setBlockEmail] = useState(false)
  const [rules, setRules] = useState<string[]>([])
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)
  const suspension = kind === 'feed_suspension' || kind === 'event_suspension'

  useEffect(() => {
    if (open && rules.length === 0) staffApi.rules().then(setRules, () => setRules([]))
  }, [open, rules.length])

  async function submit() {
    if (!rule.trim()) return setError('Choose the rule this relates to.')
    if (!reason.trim()) return setError('Give a reason.')
    if (suspension && length === 'custom' && !until) return setError('Choose an end date.')
    setBusy(true)
    try {
      const action = await staffApi.act(handle, {
        kind,
        rule: rule.trim(),
        reason: reason.trim(),
        report_id: reportId,
        days: suspension && length !== 'custom' ? Number(length) : undefined,
        until: suspension && length === 'custom' ? until : undefined,
        block_email: kind === 'ban' ? blockEmail : undefined,
      })
      toast.show({ tone: 'success', title: `${action.kind_label} recorded`, message: 'The member has been told, and it is in the log.' })
      onDone(action)
      onClose()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'That did not work. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Action on ${handle}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={busy} aria-busy={busy}>
            {busy ? 'Saving' : 'Record action'}
          </Button>
        </>
      }
    >
      <fieldset>
        <legend className="mb-2 text-sm text-fg-muted">What should happen?</legend>
        <div className="flex flex-col gap-1">
          {KINDS.filter((option) => option.value !== 'remove_content' || canRemoveContent).map((option) => (
            <label key={option.value} className="flex items-start gap-3 rounded-app px-2 py-2 hover:bg-surface">
              <input
                type="radio"
                name={`${groupId}-kind`}
                value={option.value}
                checked={kind === option.value}
                onChange={() => {
                  setKind(option.value)
                  setError(undefined)
                }}
                className="mt-1 size-4 accent-[var(--color-primary)]"
              />
              <span>
                <span className="block font-semibold text-fg">{option.label}</span>
                <span className="block text-sm text-fg-muted">{option.hint}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>
      {suspension && (
        <fieldset className="mt-4">
          <legend className="mb-2 text-sm font-semibold text-fg">How long</legend>
          <div className="flex flex-wrap gap-2">
            {LENGTHS.map((option) => (
              <label key={option.value} className="flex items-center gap-2 rounded-app border border-border px-3 py-2 text-sm has-[:checked]:border-fg">
                <input type="radio" name={`${groupId}-length`} value={option.value} checked={length === option.value} onChange={() => setLength(option.value)} className="accent-[var(--color-primary)]" />
                {option.label}
              </label>
            ))}
          </div>
          {length === 'custom' && (
            <div className="mt-3">
              <FormField label="Ends on">{(field) => <Input {...field} type="date" value={until} onChange={(e) => setUntil(e.target.value)} />}</FormField>
            </div>
          )}
        </fieldset>
      )}
      {kind === 'ban' && (
        <div className="mt-4">
          <Checkbox label="Also stop this email address from registering again" checked={blockEmail} onChange={(e) => setBlockEmail(e.target.checked)} />
        </div>
      )}
      <div className="mt-4 flex flex-col gap-4">
        <FormField label="Rule" hint="The house rule or guideline this relates to." required>
          {(field) => <Input {...field} list={rulesId} value={rule} onChange={(e) => setRule(e.target.value)} />}
        </FormField>
        <datalist id={rulesId}>
          {rules.map((title) => (
            <option key={title} value={title} />
          ))}
        </datalist>
        <FormField label="Reason" hint="The member reads this on their account page. Emails never include it." required>
          {(field) => <Textarea {...field} rows={3} maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)} />}
        </FormField>
      </div>
      {error && (
        <p role="alert" className="mt-3 text-sm text-danger">
          {error}
        </p>
      )}
    </Modal>
  )
}
