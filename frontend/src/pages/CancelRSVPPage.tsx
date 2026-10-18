import { CircleCheck } from 'lucide-react'
import { useState } from 'react'
import { PageHero } from '@/components/content/PageHero'
import { Button, ButtonLink, Card, Section } from '@/components/ui'
import { api } from '@/lib/api'
import { formatEventDate, fragmentParams } from '@/lib/format'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** Reached from the cancel link in an email; the token lives in the URL fragment. */
export function CancelRSVPPage() {
  useDocumentMeta({ title: 'Cancel RSVP', noindex: true })
  const token = fragmentParams(window.location.hash).get('token') ?? ''
  const [status, setStatus] = useState<'idle' | 'working' | 'done' | 'error'>(token ? 'idle' : 'error')
  const [message, setMessage] = useState(token ? '' : 'This link is incomplete. Open it again from your email.')
  const [event, setEvent] = useState<{ title: string; starts_at: string; slug: string } | null>(null)

  async function cancel() {
    setStatus('working')
    try {
      const result = await api.cancelByToken(token)
      setEvent(result.event)
      setMessage(result.detail)
      setStatus('done')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Please try again.')
      setStatus('error')
    }
  }

  return (
    <>
      <PageHero eyebrow="Your plans" title="Change of plans?" placeholder="shadow" />
      <Section width="narrow" spacing="tight">
        <Card className="p-8">
          {status === 'done' ? (
            <div role="status">
              <CircleCheck aria-hidden="true" className="size-8 text-success" />
              <p className="mt-4 text-2xl text-fg">{message}</p>
              {event && (
                <p className="mt-2 text-fg-muted">
                  {event.title}, <time dateTime={event.starts_at}>{formatEventDate(event.starts_at)}</time>
                </p>
              )}
              <ButtonLink to="/events" variant="ghost" className="mt-8">
                See other events
              </ButtonLink>
            </div>
          ) : status === 'error' ? (
            <div role="alert">
              <p className="font-display text-2xl text-fg">We could not cancel this RSVP</p>
              <p className="mt-2 text-fg-muted">{message}</p>
              <ButtonLink to="/account" variant="ghost" className="mt-8">
                Manage RSVPs in your account
              </ButtonLink>
            </div>
          ) : (
            <div>
              <p className="font-display text-2xl text-fg">Cancel your RSVP?</p>
              <p className="mt-2 text-fg-muted">Your place will go to the next person on the waitlist.</p>
              <Button size="lg" className="mt-8" onClick={cancel} disabled={status === 'working'} aria-busy={status === 'working'}>
                {status === 'working' ? 'Cancelling' : 'Yes, cancel my RSVP'}
              </Button>
            </div>
          )}
        </Card>
      </Section>
    </>
  )
}
