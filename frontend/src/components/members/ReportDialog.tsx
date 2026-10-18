import { useId, useState } from 'react'
import { members, REPORT_REASONS, type ReportReason, type ReportTarget } from '@/lib/membersApi'
import { Button, FormField, Modal, Textarea, useToast } from '../ui'

interface ReportDialogProps {
  open: boolean
  onClose: () => void
  targetType: ReportTarget
  targetId: string
}

/** Reports are private. The reporter never learns the outcome or who else reported. */
export function ReportDialog({ open, onClose, targetType, targetId }: ReportDialogProps) {
  const toast = useToast()
  const groupId = useId()
  const [reason, setReason] = useState<ReportReason | ''>('')
  const [details, setDetails] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  async function submit() {
    if (!reason) return setError('Choose a reason.')
    if (reason === 'other' && !details.trim()) return setError('Tell us a little about what is wrong.')
    setBusy(true)
    try {
      const result = await members.report(targetType, targetId, reason, details.trim())
      toast.show({ tone: 'success', title: result.detail })
      setReason('')
      setDetails('')
      onClose()
    } catch {
      toast.show({ tone: 'error', title: 'Your report was not sent', message: 'Please try again.' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Report this ${targetType}`}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={busy} aria-busy={busy}>
            {busy ? 'Sending' : 'Send report'}
          </Button>
        </>
      }
    >
      <fieldset aria-describedby={error ? `${groupId}-error` : undefined}>
        <legend className="mb-3 text-sm text-fg-muted">What is wrong? Only our team sees this.</legend>
        <div className="flex flex-col gap-1">
          {REPORT_REASONS.map((option) => (
            <label key={option.value} className="flex min-h-11 items-center gap-3 rounded-lg px-2 text-fg hover:bg-surface-raised">
              <input
                type="radio"
                name={`${groupId}-reason`}
                value={option.value}
                checked={reason === option.value}
                onChange={() => {
                  setReason(option.value)
                  setError(undefined)
                }}
                className="size-4 accent-[var(--color-primary)]"
              />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="mt-4">
        <FormField label="More detail" optionalLabel={reason === 'other' ? '' : 'Optional'} required={reason === 'other'}>
          {(field) => <Textarea {...field} rows={3} maxLength={500} value={details} onChange={(e) => setDetails(e.target.value)} />}
        </FormField>
      </div>
      {error && (
        <p id={`${groupId}-error`} role="alert" className="mt-3 text-sm text-danger">
          {error}
        </p>
      )}
    </Modal>
  )
}
