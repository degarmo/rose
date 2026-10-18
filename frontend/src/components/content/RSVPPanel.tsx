import { CalendarPlus, CircleCheck, Clock, Lock, MailCheck, UserPlus } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import { useAuth } from '@/components/layout/authContext'
import { Button, ButtonLink, Card, FormField, Modal, Select, Textarea, useToast } from '@/components/ui'
import { api, ApiError, type EventDetail, type RSVPState } from '@/lib/api'
import { formatEventDate } from '@/lib/format'

const NOTE_LIMIT = 280

interface RSVPPanelProps {
  event: EventDetail
  onChange: (rsvp: RSVPState) => void
}

function partyOptions(max: number) {
  return Array.from({ length: max }, (_, index) => ({
    value: String(index + 1),
    label: index === 0 ? 'Just me' : `Me and ${index} guest${index > 1 ? 's' : ''}`,
  }))
}

function CalendarDownload({ slug }: { slug: string }) {
  const [details, setDetails] = useState(false)
  const id = useId()
  return (
    <div className="mt-6 border-t border-border pt-6">
      <a
        href={api.icsUrl(slug, details)}
        download="evening.ics"
        className="inline-flex min-h-11 items-center gap-2 text-sm font-medium text-accent underline decoration-highlight/60 underline-offset-[6px] hover:text-fg"
      >
        <CalendarPlus aria-hidden="true" className="size-4" />
        Add to calendar
      </a>
      <div className="mt-2 flex items-start gap-3">
        <input
          id={id}
          type="checkbox"
          checked={details}
          onChange={(event) => setDetails(event.target.checked)}
          className="mt-1 size-4 accent-[var(--color-primary)]"
        />
        <label htmlFor={id} className="text-sm text-fg-muted">
          Include the event name and address. Leave this off and your calendar just says &ldquo;Rose -
          Evening&rdquo;.
        </label>
      </div>
    </div>
  )
}

export function RSVPPanel({ event, onChange }: RSVPPanelProps) {
  const auth = useAuth()
  const toast = useToast()
  const rsvp = event.rsvp
  const mine = rsvp.mine
  const [partySize, setPartySize] = useState(String(mine?.party_size ?? 1))
  const [note, setNote] = useState(mine?.note_to_hosts ?? '')
  const [noteError, setNoteError] = useState<string>()
  const [submitting, setSubmitting] = useState(false)
  const [confirmCancel, setConfirmCancel] = useState(false)
  const [resent, setResent] = useState(false)
  const next = encodeURIComponent(`/events/${event.slug}`)

  async function submit(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault()
    if (note.length > NOTE_LIMIT) {
      setNoteError(`Please keep your note under ${NOTE_LIMIT} characters.`)
      return
    }
    setSubmitting(true)
    try {
      const result = await api.rsvp(event.slug, Number(partySize), note.trim())
      onChange(result.rsvp)
      toast.show({
        tone: 'success',
        title:
          result.rsvp.state === 'going'
            ? 'You are on the list'
            : result.rsvp.state === 'waitlisted'
              ? 'You are on the waitlist'
              : 'Your RSVP is saved',
        message: 'A confirmation is on its way to your email.',
      })
    } catch (error) {
      toast.show({
        tone: 'error',
        title: 'Your RSVP was not saved',
        message: error instanceof Error ? error.message : 'Please try again.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  async function cancel() {
    setSubmitting(true)
    try {
      const result = await api.cancelRSVP(event.slug)
      setConfirmCancel(false)
      onChange(result.rsvp)
      toast.show({ tone: 'success', title: 'Your RSVP is cancelled', message: 'Thank you for letting us know.' })
    } catch (error) {
      toast.show({
        tone: 'error',
        title: 'We could not cancel your RSVP',
        message: error instanceof Error ? error.message : 'Please try again.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  async function resend() {
    setSubmitting(true)
    try {
      await api.resendVerification()
      setResent(true)
    } catch (error) {
      toast.show({
        tone: 'error',
        title: 'We could not send a new link',
        message: error instanceof ApiError && error.isRateLimited ? 'Please wait a little before trying again.' : 'Please try again.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  const rsvpForm = (label: string) => (
    <form onSubmit={submit} className="mt-6 flex flex-col gap-5" aria-label="RSVP">
      {rsvp.max_party_size > 1 && (
        <FormField label="Party size" required>
          {(field) => (
            <Select
              {...field}
              name="party_size"
              options={partyOptions(rsvp.max_party_size)}
              value={partySize}
              onChange={(e) => setPartySize(e.target.value)}
            />
          )}
        </FormField>
      )}
      <FormField label="Note to hosts" hint="Access needs, first visit nerves, anything that helps." error={noteError}>
        {(field) => (
          <Textarea
            {...field}
            name="note_to_hosts"
            rows={3}
            value={note}
            maxLength={NOTE_LIMIT}
            onChange={(e) => {
              setNote(e.target.value)
              setNoteError(undefined)
            }}
          />
        )}
      </FormField>
      <p className="-mt-3 text-right text-xs text-fg-subtle">
        {note.length} / {NOTE_LIMIT}
      </p>
      <Button type="submit" size="lg" disabled={submitting} aria-busy={submitting}>
        {submitting ? 'Saving' : label}
      </Button>
    </form>
  )

  let body
  if (rsvp.state === 'going' || rsvp.state === 'waitlisted') {
    const going = rsvp.state === 'going'
    body = (
      <>
        <p className="flex items-center gap-3 font-display text-2xl text-fg">
          {going ? (
            <CircleCheck aria-hidden="true" className="size-6 text-success" />
          ) : (
            <Clock aria-hidden="true" className="size-6 text-rose" />
          )}
          {going ? 'You are going' : 'You are on the waitlist'}
        </p>
        <p className="mt-2 text-sm text-fg-muted">
          {going
            ? 'Bring a valid photo ID. You can change your party size or note below.'
            : 'We will email you straight away if a place opens up.'}
        </p>
        {rsvp.can_rsvp && rsvpForm('Update RSVP')}
        <Button variant="ghost" className="mt-4 w-full" onClick={() => setConfirmCancel(true)} disabled={submitting}>
          Cancel my RSVP
        </Button>
        {going && <CalendarDownload slug={event.slug} />}
        <Modal
          open={confirmCancel}
          onClose={() => setConfirmCancel(false)}
          title="Cancel your RSVP?"
          footer={
            <>
              <Button variant="ghost" onClick={() => setConfirmCancel(false)}>
                Keep it
              </Button>
              <Button onClick={cancel} disabled={submitting} aria-busy={submitting}>
                {submitting ? 'Cancelling' : 'Yes, cancel'}
              </Button>
            </>
          }
        >
          <p className="text-fg-muted">Your place will be offered to the next person on the waitlist.</p>
        </Modal>
      </>
    )
  } else if (rsvp.state === 'members_only') {
    body = (
      <>
        <p className="flex items-center gap-3 font-display text-2xl text-fg">
          <Lock aria-hidden="true" className="size-5 text-highlight" />
          For members
        </p>
        <p className="mt-2 text-sm text-fg-muted">This evening is open to members of the house.</p>
        <Button size="lg" className="mt-6 w-full" disabled aria-disabled="true">
          Members only
        </Button>
      </>
    )
  } else if (rsvp.state === 'closed' || rsvp.state === 'unavailable') {
    body = (
      <>
        <p className="font-display text-2xl text-fg">RSVPs are closed</p>
        <p className="mt-2 text-sm text-fg-muted">Take a look at what else is coming up.</p>
        <ButtonLink to="/events" variant="ghost" className="mt-6 w-full">
          See all events
        </ButtonLink>
      </>
    )
  } else if (rsvp.state === 'not_open_yet') {
    body = (
      <>
        <p className="font-display text-2xl text-fg">RSVPs open soon</p>
        {rsvp.opens_at && (
          <p className="mt-2 text-sm text-fg-muted">
            Opening <time dateTime={rsvp.opens_at}>{formatEventDate(rsvp.opens_at)}</time>.
          </p>
        )}
      </>
    )
  } else if (rsvp.state === 'full') {
    body = (
      <>
        <p className="font-display text-2xl text-fg">This evening is full</p>
        <p className="mt-2 text-sm text-fg-muted">There is no waitlist for this one. We hope to see you at another.</p>
        <ButtonLink to="/events" variant="ghost" className="mt-6 w-full">
          See all events
        </ButtonLink>
      </>
    )
  } else if (auth.status === 'loading') {
    body = <p className="text-sm text-fg-muted">Checking your account</p>
  } else if (rsvp.reason === 'login_required' || !auth.user) {
    body = (
      <>
        <p className="font-display text-2xl text-fg">{rsvp.state === 'waitlist' ? 'Join the waitlist' : 'RSVP for this evening'}</p>
        <p className="mt-2 text-sm text-fg-muted">Sign in or create a free account to RSVP. It takes a minute.</p>
        <div className="mt-6 flex flex-col gap-3">
          <ButtonLink to={`/account/login?next=${next}`} size="lg">
            Log in to RSVP
          </ButtonLink>
          <ButtonLink to={`/account/register?next=${next}`} size="lg" variant="ghost">
            <UserPlus aria-hidden="true" className="size-4" />
            Create an account
          </ButtonLink>
        </div>
      </>
    )
  } else if (rsvp.reason === 'unverified') {
    body = (
      <>
        <p className="flex items-center gap-3 font-display text-2xl text-fg">
          <MailCheck aria-hidden="true" className="size-6 text-highlight" />
          Confirm your email
        </p>
        <p className="mt-2 text-sm text-fg-muted">
          Open the link we sent to {auth.user.email} to RSVP. It only takes a moment.
        </p>
        {resent ? (
          <p role="status" className="mt-6 text-sm text-success">
            A new link is on its way.
          </p>
        ) : (
          <Button variant="ghost" className="mt-6 w-full" onClick={resend} disabled={submitting} aria-busy={submitting}>
            {submitting ? 'Sending' : 'Send a new link'}
          </Button>
        )}
      </>
    )
  } else {
    const waitlist = rsvp.state === 'waitlist'
    body = (
      <>
        <p className="font-display text-2xl text-fg">{waitlist ? 'Join the waitlist' : 'RSVP for this evening'}</p>
        <p className="mt-2 text-sm text-fg-muted">
          {waitlist
            ? 'This evening is full. Join the waitlist and we will email you if a place opens up.'
            : 'Let us know you are coming. Only our hosts see who is on the list.'}
        </p>
        {rsvpForm(waitlist ? 'Join the waitlist' : 'RSVP')}
      </>
    )
  }

  return (
    <Card as="article" className="p-6 sm:p-8" aria-label="RSVP">
      {body}
      {event.attendee_count !== null && (
        <p className="mt-6 border-t border-border pt-4 text-sm text-fg-subtle">{event.attendee_count} going</p>
      )}
    </Card>
  )
}
