import { useState, type FormEvent } from 'react'
import { useAuth } from '@/components/layout/authContext'
import { Button, FormField, Input, Select, Textarea } from '@/components/ui'
import { ApiError, request, type EventSummary } from '@/lib/api'
import { formatDay } from '@/lib/format'
import { safetyApi } from '@/lib/safetyApi'
import { useAsync } from '@/lib/useAsync'

const LIMIT = 4000

/**
 * Report a concern: something that happened at an event or the club. Signed in, it is
 * sent from the account (only an admin can ever see who sent it); signed out, an email is
 * optional and gets two neutral updates, never the outcome. Staff are told something is
 * waiting, without the words.
 */
export function ConcernForm({ onSent, submitClass }: { onSent: () => void; submitClass?: string }) {
  const auth = useAuth()
  const events = useAsync(() => request<EventSummary[]>('/events/?past=1'), 'concern-events')
  const [details, setDetails] = useState('')
  const [event, setEvent] = useState('')
  const [date, setDate] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [website, setWebsite] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)
  const signedIn = Boolean(auth.user)

  async function submit(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault()
    if (!details.trim()) return setError('Tell us what happened.')
    setBusy(true)
    try {
      await safetyApi.concern({
        details: details.trim(),
        event: event || undefined,
        event_date: date || undefined,
        reported_name: name.trim() || undefined,
        contact_email: signedIn ? undefined : email.trim() || undefined,
        website,
      })
      onSent()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'It was not sent. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const eventOptions = [
    { value: '', label: 'Not about a particular event' },
    ...(events.status === 'success' ? events.data : []).map((item) => ({ value: item.slug, label: `${item.title}, ${formatDay(item.starts_at)}` })),
  ]

  return (
    <form noValidate onSubmit={submit} className="relative flex flex-col gap-5" aria-label="Report a concern">
      <FormField label="What happened?" hint="Only our team reads this." required error={error}>
        {(field) => <Textarea {...field} rows={6} maxLength={LIMIT} value={details} onChange={(e) => setDetails(e.target.value)} />}
      </FormField>
      <FormField label="Which event" optionalLabel="Optional">
        {(field) => <Select {...field} value={event} options={eventOptions} onChange={(e) => setEvent(e.target.value)} />}
      </FormField>
      <FormField label="When" optionalLabel="Optional">
        {(field) => <Input {...field} type="date" value={date} onChange={(e) => setDate(e.target.value)} />}
      </FormField>
      <FormField label="Their display name, if you know it" optionalLabel="Optional" hint="Never shown to them, and never who you are.">
        {(field) => <Input {...field} maxLength={60} value={name} onChange={(e) => setName(e.target.value)} />}
      </FormField>
      {!signedIn && (
        <FormField label="Your email" optionalLabel="Optional" hint="Only to tell you it arrived and when it has been reviewed.">
          {(field) => <Input {...field} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />}
        </FormField>
      )}
      {/* Honeypot: hidden from people and assistive tech, tempting to bots. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label>
          Website
          <input type="text" name="website" tabIndex={-1} autoComplete="off" value={website} onChange={(e) => setWebsite(e.target.value)} />
        </label>
      </div>
      <Button type="submit" size="lg" disabled={busy} aria-busy={busy} className={submitClass}>
        {busy ? 'Sending' : 'Send to the team'}
      </Button>
    </form>
  )
}
