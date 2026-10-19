import { CalendarDays, Minus, Plus } from 'lucide-react'
import { useId, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { Badge, Button, ButtonLink, Card, Checkbox, Modal, Textarea, useToast } from '@/components/ui'
import { api, ApiError, type EventDetail, type RSVPState } from '@/lib/api'
import { rsvpBadge } from '@/lib/events'
import { formatEventDate } from '@/lib/format'

const NOTE_LIMIT = 280

interface RSVPPanelProps {
  event: EventDetail
  onChange: (rsvp: RSVPState) => void
}

/** The party-size row (design: a 12px-cornered box with round − and + steppers). */
function PartySize({ value, max, onChange }: { value: number; max: number; onChange: (value: number) => void }) {
  const labelId = useId()
  const step = 'inline-flex size-8 items-center justify-center rounded-full border transition-colors disabled:cursor-not-allowed'
  return (
    <div role="group" aria-labelledby={labelId} className="flex items-center justify-between rounded-field border border-border px-3.5 py-2.5 sm:px-4 sm:py-3">
      <div>
        <p id={labelId} className="text-sm font-semibold text-fg">
          Party size
        </p>
        <p className="hidden text-[0.8125rem] text-fg-muted sm:block">Guests must be 18+</p>
      </div>
      <div className="flex items-center gap-3.5 sm:gap-4">
        <button type="button" onClick={() => onChange(value - 1)} disabled={value <= 1} className={`${step} border-fg disabled:border-border disabled:text-fg-muted`}>
          <Minus aria-hidden="true" className="size-3.5" />
          <span className="sr-only">One fewer</span>
        </button>
        <output aria-live="polite" className="w-4 text-center font-semibold text-fg">
          {value}
        </output>
        <button type="button" onClick={() => onChange(value + 1)} disabled={value >= max} className={`${step} border-fg disabled:border-border disabled:text-fg-muted`}>
          <Plus aria-hidden="true" className="size-3.5" />
          <span className="sr-only">One more</span>
        </button>
      </div>
    </div>
  )
}

/** The calendar file: discreet ("Rose - Evening", no place) unless the box is ticked. */
function CalendarDownload({ slug }: { slug: string }) {
  const [details, setDetails] = useState(false)
  return (
    <div className="flex flex-col gap-2.5">
      <a
        href={api.icsUrl(slug, details)}
        download="evening.ics"
        className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-border text-sm font-semibold text-fg hover:border-fg-muted"
      >
        <CalendarDays aria-hidden="true" className="size-4" strokeWidth={1.8} />
        Add to calendar
      </a>
      <Checkbox
        label={<span className="text-[0.8125rem] text-fg-muted">Include the event name and address. Leave this off and your calendar just says &ldquo;Rose - Evening&rdquo;.</span>}
        checked={details}
        onChange={(event) => setDetails(event.target.checked)}
      />
    </div>
  )
}

function Note({ children }: { children: ReactNode }) {
  return <p className="text-[0.8125rem] text-fg-muted">{children}</p>
}

const UPGRADE_LINK = 'font-semibold text-link hover:text-primary-hover'

/** "Your membership includes one guest here." when the plan, not the event, sets the limit. */
function PlanGuests({ limit }: { limit: number }) {
  const guests = limit - 1
  return (
    <Note>
      {guests === 0 ? 'Your membership does not include guests here.' : `Your membership includes ${guests === 1 ? 'one guest' : `${guests} guests`} here.`}{' '}
      <Link to="/membership" className={UPGRADE_LINK}>
        See plans with guests
      </Link>
    </Note>
  )
}

/**
 * The RSVP panel (design system: "RSVP panel · every state"): "RSVP" with a status badge,
 * the party size, the main action, the calendar file and a short note.
 */
export function RSVPPanel({ event, onChange }: RSVPPanelProps) {
  const auth = useAuth()
  const toast = useToast()
  const rsvp = event.rsvp
  const mine = rsvp.mine
  const [partySize, setPartySize] = useState(mine?.party_size ?? 1)
  const [note, setNote] = useState(mine?.note_to_hosts ?? '')
  const [noteOpen, setNoteOpen] = useState(Boolean(mine?.note_to_hosts))
  const [noteError, setNoteError] = useState<string>()
  const [editing, setEditing] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [confirmCancel, setConfirmCancel] = useState(false)
  const [resent, setResent] = useState(false)
  const noteId = useId()
  const next = encodeURIComponent(`/events/${event.slug}`)
  const badge = rsvpBadge(rsvp)
  // A membership can allow a smaller party than the event does.
  const planLimited = rsvp.plan_party_limit !== null && rsvp.plan_party_limit < rsvp.max_party_size
  const maxParty = planLimited ? (rsvp.plan_party_limit ?? rsvp.max_party_size) : rsvp.max_party_size

  async function submit(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault()
    if (note.length > NOTE_LIMIT) {
      setNoteError(`Please keep your note under ${NOTE_LIMIT} characters.`)
      return
    }
    setSubmitting(true)
    try {
      const result = await api.rsvp(event.slug, partySize, note.trim())
      setEditing(false)
      onChange(result.rsvp)
      toast.show({
        tone: 'success',
        title: result.rsvp.state === 'going' ? 'You are on the list' : result.rsvp.state === 'waitlisted' ? 'You are on the waitlist' : 'Your RSVP is saved',
        message: 'A confirmation is on its way to your email.',
      })
    } catch (error) {
      toast.show({ tone: 'error', title: 'Your RSVP was not saved', message: error instanceof Error ? error.message : 'Please try again.' })
    } finally {
      setSubmitting(false)
    }
  }

  async function cancel() {
    setSubmitting(true)
    try {
      const result = await api.cancelRSVP(event.slug)
      setConfirmCancel(false)
      setEditing(false)
      onChange(result.rsvp)
      toast.show({ tone: 'success', title: 'Your RSVP is cancelled', message: 'Thank you for letting us know.' })
    } catch (error) {
      toast.show({ tone: 'error', title: 'We could not cancel your RSVP', message: error instanceof Error ? error.message : 'Please try again.' })
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

  const rsvpForm = (label: string, primary: boolean) => (
    <form onSubmit={submit} className="flex flex-col gap-4" aria-label="RSVP">
      {maxParty > 1 && <PartySize value={partySize} max={maxParty} onChange={setPartySize} />}
      {planLimited && <PlanGuests limit={maxParty} />}
      {noteOpen ? (
        <div className="flex flex-col gap-1.5 text-sm">
          <label htmlFor={noteId} className="font-semibold text-fg">
            Note to hosts <span className="font-normal text-fg-muted">(optional)</span>
          </label>
          <Textarea
            id={noteId}
            name="note_to_hosts"
            rows={3}
            className="min-h-24"
            value={note}
            maxLength={NOTE_LIMIT}
            invalid={Boolean(noteError)}
            aria-describedby={`${noteId}-count`}
            onChange={(e) => {
              setNote(e.target.value)
              setNoteError(undefined)
            }}
          />
          <p id={`${noteId}-count`} className="flex justify-between text-[0.8125rem] text-fg-muted">
            <span className={noteError ? 'text-danger' : undefined}>{noteError ?? 'Access needs, first visit nerves, anything that helps.'}</span>
            <span>
              {note.length} / {NOTE_LIMIT}
            </span>
          </p>
        </div>
      ) : (
        <button type="button" onClick={() => setNoteOpen(true)} className="self-start text-sm font-semibold text-link hover:text-primary-hover">
          Add a note for the hosts
        </button>
      )}
      <Button type="submit" size="lg" variant={primary ? 'primary' : 'outline'} disabled={submitting} aria-busy={submitting} className="w-full">
        {submitting ? 'Saving' : label}
      </Button>
    </form>
  )

  let body: ReactNode
  if (rsvp.state === 'going' || rsvp.state === 'waitlisted') {
    const going = rsvp.state === 'going'
    body = (
      <>
        <Note>
          {going
            ? `${mine && mine.party_size > 1 ? `You are going, party of ${mine.party_size}.` : 'You are going.'} Bring a valid photo ID. The confirmation in your email has the details.`
            : 'You are on the waitlist. We will email you straight away if a place opens up.'}
        </Note>
        {editing && rsvp.can_rsvp ? (
          <>
            {rsvpForm('Update RSVP', true)}
            <Button variant="secondary" size="lg" className="w-full" onClick={() => setConfirmCancel(true)} disabled={submitting}>
              Cancel my RSVP
            </Button>
          </>
        ) : (
          <Button variant="outline" size="lg" className="w-full" onClick={() => (rsvp.can_rsvp ? setEditing(true) : setConfirmCancel(true))}>
            {rsvp.can_rsvp ? 'Change or cancel' : 'Cancel my RSVP'}
          </Button>
        )}
        {going && <CalendarDownload slug={event.slug} />}
        <Modal
          open={confirmCancel}
          onClose={() => setConfirmCancel(false)}
          title="Cancel your RSVP?"
          footer={
            <>
              <Button variant="secondary" onClick={() => setConfirmCancel(false)}>
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
        <Note>This night is for members and their guests. Join or log in to RSVP.</Note>
        {auth.user?.has_membership ? (
          <ButtonLink to="/account#membership" size="lg" variant="outline" className="w-full">
            See my membership
          </ButtonLink>
        ) : (
          <ButtonLink to="/membership" size="lg" className="w-full">
            Join to RSVP
          </ButtonLink>
        )}
        {!auth.user && auth.status !== 'loading' && (
          <ButtonLink to={`/account/login?next=${next}`} size="lg" variant="secondary" className="w-full">
            Log in
          </ButtonLink>
        )}
      </>
    )
  } else if (rsvp.state === 'tier_event_not_included') {
    body = (
      <>
        <Note>This event is not part of your membership. Some plans include it.</Note>
        <ButtonLink to="/membership" size="lg" className="w-full">
          See plans that include it
        </ButtonLink>
      </>
    )
  } else if (rsvp.state === 'monthly_limit_reached') {
    body = (
      <>
        <Note>You have used this month&rsquo;s events on your membership. They start again on the first of next month.</Note>
        <ButtonLink to="/membership" size="lg" className="w-full">
          See plans with more events
        </ButtonLink>
      </>
    )
  } else if (rsvp.state === 'restricted') {
    body = (
      <>
        <Note>RSVPs are paused on your account. Your account page explains why.</Note>
        <ButtonLink to="/account/notices" size="lg" variant="outline" className="w-full">
          See my account
        </ButtonLink>
      </>
    )
  } else if (rsvp.state === 'closed' || rsvp.state === 'unavailable' || rsvp.state === 'full') {
    body = (
      <>
        <Note>
          {rsvp.state === 'full' ? 'No spots and the waitlist is closed. We hope to see you at another evening.' : 'RSVPs for this evening are closed.'}
        </Note>
        <ButtonLink to="/events" size="lg" variant="outline" className="w-full">
          See other events
        </ButtonLink>
      </>
    )
  } else if (rsvp.state === 'not_open_yet') {
    body = (
      <Note>
        RSVPs open soon
        {rsvp.opens_at && (
          <>
            : <time dateTime={rsvp.opens_at}>{formatEventDate(rsvp.opens_at)}</time>
          </>
        )}
        .
      </Note>
    )
  } else if (auth.status === 'loading') {
    body = <Note>Checking your account</Note>
  } else if (rsvp.reason === 'login_required' || !auth.user) {
    body = (
      <>
        <Note>Log in or create a free account to RSVP. Only our hosts see who is coming.</Note>
        <ButtonLink to={`/account/login?next=${next}`} size="lg" className="w-full">
          Log in to RSVP
        </ButtonLink>
        <ButtonLink to={`/account/register?next=${next}`} size="lg" variant="secondary" className="w-full">
          Create an account
        </ButtonLink>
      </>
    )
  } else if (rsvp.reason === 'unverified') {
    body = (
      <>
        <p className="font-semibold text-fg">Confirm your email</p>
        <Note>Open the link we sent to {auth.user.email} to RSVP. It only takes a moment.</Note>
        {resent ? (
          <p role="status" className="text-sm text-link">
            A new link is on its way.
          </p>
        ) : (
          <Button variant="outline" size="lg" className="w-full" onClick={resend} disabled={submitting} aria-busy={submitting}>
            {submitting ? 'Sending' : 'Send a new link'}
          </Button>
        )}
      </>
    )
  } else {
    const waitlist = rsvp.state === 'waitlist'
    body = (
      <>
        {waitlist && <Note>This evening is full. Join the waitlist and we will email you if a place opens up.</Note>}
        {rsvpForm(waitlist ? 'Join the waitlist' : partySize > 1 ? `RSVP for ${partySize}` : 'RSVP', !waitlist)}
        {!waitlist && <CalendarDownload slug={event.slug} />}
        {rsvp.events_remaining !== null && (
          <Note>
            {rsvp.events_remaining === 1 ? 'This uses your last event' : `You have ${rsvp.events_remaining} events left`} this month on your
            membership.
          </Note>
        )}
        {!waitlist && <Note>Photo ID is checked at the door. Only our hosts see who is on the list.</Note>}
      </>
    )
  }

  return (
    <Card as="article" shape="panel" className="gap-4 p-5 sm:gap-5 sm:p-7" aria-label="RSVP">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-[1.375rem] text-fg sm:text-2xl">RSVP</h2>
        <Badge tone={badge.tone}>{mine && rsvp.state === 'going' && mine.party_size > 1 ? `Going · party of ${mine.party_size}` : badge.label}</Badge>
      </div>
      {body}
      {event.attendee_count !== null && <p className="border-t border-border pt-3 text-[0.8125rem] text-fg-muted">{event.attendee_count} going</p>}
    </Card>
  )
}
