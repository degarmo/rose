import { Check } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { PageHero } from '@/components/content/PageHero'
import { Button, ButtonLink, GUTTER } from '@/components/ui'
import { api } from '@/lib/api'
import { cn } from '@/lib/cn'
import { formatEventDate, fragmentParams } from '@/lib/format'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** The centred blush panel of Contact · phone (success). */
function Panel({ role, children }: { role?: 'status' | 'alert'; children: ReactNode }) {
  return (
    <div role={role} className="flex max-w-[640px] flex-col items-center gap-3 rounded-panel bg-blush px-6 py-8 text-center lg:px-10 lg:py-12">
      {children}
    </div>
  )
}

const TITLE = 'text-[1.625rem] leading-[1.15] text-fg'
const TEXT = 'text-sm leading-[1.6] text-fg-muted-tint lg:text-[0.9375rem]'

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
      <PageHero title="Change of plans?" />
      <div className={cn('mx-auto max-w-[1440px] pb-12 pt-2 lg:pb-20 lg:pt-4', GUTTER)}>
        {status === 'done' ? (
          <Panel role="status">
            <span aria-hidden="true" className="flex size-14 items-center justify-center rounded-full border-[1.5px] border-primary bg-canvas text-link">
              <Check strokeWidth={2} className="size-6" />
            </span>
            <h2 className={TITLE}>{message}</h2>
            {event && (
              <p className={TEXT}>
                {event.title}, <time dateTime={event.starts_at}>{formatEventDate(event.starts_at)}</time>
              </p>
            )}
            <ButtonLink to="/events" variant="outline" className="mt-2">
              See other events
            </ButtonLink>
          </Panel>
        ) : status === 'error' ? (
          <Panel role="alert">
            <h2 className={TITLE}>We could not cancel this RSVP</h2>
            <p className={TEXT}>{message}</p>
            <ButtonLink to="/members/home" variant="outline" className="mt-2">
              See your plans
            </ButtonLink>
          </Panel>
        ) : (
          <Panel>
            <h2 className={TITLE}>Cancel your RSVP?</h2>
            <p className={TEXT}>Your place will go to the next person on the waitlist.</p>
            <Button size="lg" className="mt-2" onClick={cancel} disabled={status === 'working'} aria-busy={status === 'working'}>
              {status === 'working' ? 'Cancelling' : 'Yes, cancel my RSVP'}
            </Button>
          </Panel>
        )}
      </div>
    </>
  )
}
