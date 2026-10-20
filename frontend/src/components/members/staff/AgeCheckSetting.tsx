import { IdCard, TriangleAlert } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useAuth } from '@/components/layout/authContext'
import { appButtonClasses } from '@/components/members/app/ui'
import { Button, FormField, Input, Modal, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { staffApi, type AgeCheckSetting } from '@/lib/safetyApi'
import { useAsync } from '@/lib/useAsync'

/**
 * Turning the member feed's age check on or off (admins only): what changes, a reason for
 * the audit log and a fresh code from the authenticator app. The server checks all three.
 */
export function AgeCheckDialog({ setting, onClose, onDone }: { setting: AgeCheckSetting; onClose: () => void; onDone: (next: AgeCheckSetting) => void }) {
  const auth = useAuth()
  const toast = useToast()
  const [reason, setReason] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)
  const turningOn = !setting.required
  const people = setting.unchecked_with_feed === 1 ? '1 person' : `${setting.unchecked_with_feed} people`

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!reason.trim()) return setError('Give a reason for the change.')
    if (!/^\d{6,8}$/.test(code.trim())) return setError('Enter the six-digit code from your authenticator app.')
    setBusy(true)
    try {
      const next = await staffApi.setAgeCheck({ required: turningOn, reason: reason.trim(), code: code.trim() })
      await auth.refresh()
      toast.show({ tone: 'success', title: turningOn ? 'Age verification is on' : 'Age verification is off' })
      onDone(next)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'That did not work. Please try again.')
      setBusy(false)
    }
  }

  return (
    <Modal open onClose={onClose} title={turningOn ? 'Turn age verification on?' : 'Turn age verification off?'}>
      <form noValidate onSubmit={(e) => void submit(e)} className="flex flex-col gap-4">
        {turningOn ? (
          <p className="text-fg">
            The member feed closes at once to the {people} with feed access and no ID check on file. Each gets one plain email and a note on their Home page, and the feed opens again as soon as the door desk records their check. Nothing they shared is lost.
          </p>
        ) : (
          <p className="text-fg">
            The member feed opens at once to everyone with feed access, ID check or not. The door desk still checks ID before any membership starts, uploads still need the promise that everyone pictured is 18 or older, and &ldquo;possibly under 18&rdquo; reports still hide content at once. A banner stays on every staff page while it is off.
          </p>
        )}
        <FormField label="Reason for the change" hint="Goes in the audit log with your name, the time and the old and new value." required>
          {(field) => <Input {...field} maxLength={300} value={reason} onChange={(e) => setReason(e.target.value)} />}
        </FormField>
        <FormField label="Six-digit code from your authenticator app" hint="A new code, not one you have just used to log in." required>
          {(field) => <Input {...field} inputMode="numeric" autoComplete="one-time-code" maxLength={8} value={code} onChange={(e) => setCode(e.target.value)} />}
        </FormField>
        {error && (
          <p role="alert" className="rounded-app bg-tint px-4 py-3 font-semibold text-tint-fg">
            {error}
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy} aria-busy={busy}>
            {busy ? 'Saving' : turningOn ? 'Turn it on' : 'Turn it off'}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </Modal>
  )
}

/** The setting as a card (Dashboard, Reports): its state for everyone, Change for admins. */
export function AgeCheckSettingCard() {
  const state = useAsync(() => staffApi.ageCheck(), 'staff-age-check')
  const [override, setOverride] = useState<AgeCheckSetting | null>(null)
  const [open, setOpen] = useState(false)
  const setting = override ?? (state.status === 'success' ? state.data : null)
  if (!setting) return null
  return (
    <section aria-labelledby="age-check-setting" className="flex flex-wrap items-center justify-between gap-3 rounded-app border border-border p-4">
      <div className="flex min-w-0 items-start gap-3">
        <IdCard aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-fg-muted" />
        <div className="min-w-0">
          <h2 id="age-check-setting" className="font-semibold text-fg">
            Age verification for the member feed: <span className={setting.required ? 'text-link' : 'text-wait-fg'}>{setting.required ? 'On' : 'Off'}</span>
          </h2>
          <p className="text-sm text-fg-muted">
            {setting.required
              ? 'The feed opens only after an ID check at the door desk.'
              : `The feed is open without an ID check. ${setting.unchecked_with_feed} with feed access have none on file.`}
          </p>
        </div>
      </div>
      {setting.can_change ? (
        <button type="button" onClick={() => setOpen(true)} className={appButtonClasses('secondary')}>
          Change
        </button>
      ) : (
        <p className="text-sm text-fg-muted">Only an admin can change this.</p>
      )}
      {open && (
        <AgeCheckDialog
          setting={setting}
          onClose={() => setOpen(false)}
          onDone={(next) => {
            setOverride(next)
            setOpen(false)
          }}
        />
      )}
    </section>
  )
}

/** On every staff page while the age check is off. Admins can open it to change the setting. */
export function AgeCheckOffBanner({ canChange }: { canChange: boolean }) {
  const [open, setOpen] = useState(false)
  const setting = useAsync(() => (open ? staffApi.ageCheck() : Promise.resolve(null)), `staff-age-check-banner:${open}`)
  const text = 'Age verification for the member feed is off'
  const classes = 'flex w-full items-center justify-center gap-2 rounded-app border border-wait bg-wait px-4 py-3 text-center font-semibold text-wait-fg'
  return (
    <>
      {canChange ? (
        <button type="button" onClick={() => setOpen(true)} className={cn(classes, 'hover:brightness-95')}>
          <TriangleAlert aria-hidden="true" className="size-5 shrink-0" />
          {text}
          <span className="underline underline-offset-4">Change</span>
        </button>
      ) : (
        <p role="status" className={classes}>
          <TriangleAlert aria-hidden="true" className="size-5 shrink-0" />
          {text}
        </p>
      )}
      {open && setting.status === 'success' && setting.data && <AgeCheckDialog setting={setting.data} onClose={() => setOpen(false)} onDone={() => setOpen(false)} />}
    </>
  )
}
