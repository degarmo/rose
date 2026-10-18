import { ArrowLeft, BookOpen, CalendarDays, Clock, MapPin } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { RSVPPanel } from '@/components/content/RSVPPanel'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { Badge, ButtonLink, ImageFrame, Section } from '@/components/ui'
import { api, ApiError, type EventDetail, type RSVPState } from '@/lib/api'
import { formatLongDate, formatTimeRange } from '@/lib/format'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from './NotFoundPage'

export function EventPage() {
  const { slug = '' } = useParams()
  const auth = useAuth()
  // Reload when the person signs in or out, so the RSVP panel reflects them.
  const state = useAsync(() => api.event(slug), `${slug}|${auth.user?.display_name ?? ''}`)
  const [rsvpOverride, setRsvpOverride] = useState<{ slug: string; rsvp: RSVPState } | null>(null)
  const loaded = state.status === 'success' ? state.data : null
  const event: EventDetail | null =
    loaded && rsvpOverride?.slug === loaded.slug ? { ...loaded, rsvp: rsvpOverride.rsvp } : loaded
  useDocumentMeta({ title: event?.title ?? 'Events', description: event?.summary })

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) {
    return <NotFoundPage />
  }

  return (
    <article>
      <div className="relative isolate flex min-h-[50svh] items-end overflow-hidden pb-12 pt-32">
        <ImageFrame remote={event?.hero_image} alt="" fill placeholder="candle" priority reveal={false} className="-z-20" />
        <div aria-hidden="true" className="absolute inset-0 -z-10 bg-gradient-to-t from-canvas via-canvas/70 to-canvas/20" />
        <div className="mx-auto w-full max-w-6xl px-5 sm:px-8">
          <ButtonLink to="/events" variant="link">
            <ArrowLeft aria-hidden="true" className="size-4" />
            All events
          </ButtonLink>
          {state.status === 'loading' && <LoadingState label="Loading event" />}
          {event && (
            <>
              <div className="mt-6 flex flex-wrap gap-2">
                <Badge tone="brass">{event.category_label}</Badge>
                {event.audience === 'members' && <Badge>Members only</Badge>}
              </div>
              <h1 className="mt-6 max-w-3xl text-5xl leading-[1.05] text-fg sm:text-6xl">{event.title}</h1>
              <p className="mt-6 max-w-2xl text-lg leading-relaxed text-fg-muted sm:text-xl">{event.summary}</p>
            </>
          )}
        </div>
      </div>

      <Section spacing="tight">
        {state.status === 'error' && <ErrorState title="This event did not load" onRetry={state.retry} />}
        {event && (
          <div className="grid gap-12 lg:grid-cols-[1.6fr_1fr] lg:gap-16">
            <div>
              <dl className="grid gap-5 border-y border-border py-6 sm:grid-cols-3">
                <div className="flex gap-3">
                  <CalendarDays aria-hidden="true" className="mt-0.5 size-5 text-highlight" />
                  <div>
                    <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle">Date</dt>
                    <dd className="mt-1 text-fg">
                      <time dateTime={event.starts_at}>{formatLongDate(event.starts_at)}</time>
                    </dd>
                  </div>
                </div>
                <div className="flex gap-3">
                  <Clock aria-hidden="true" className="mt-0.5 size-5 text-highlight" />
                  <div>
                    <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle">Time</dt>
                    <dd className="mt-1 text-fg">{formatTimeRange(event.starts_at, event.ends_at)}</dd>
                  </div>
                </div>
                {event.location_label && (
                  <div className="flex gap-3">
                    <MapPin aria-hidden="true" className="mt-0.5 size-5 text-highlight" />
                    <div>
                      <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle">Where</dt>
                      <dd className="mt-1 text-fg">{event.location_label}</dd>
                    </div>
                  </div>
                )}
              </dl>
              <div
                className="mt-10 space-y-5 text-lg leading-relaxed text-fg-muted [&_a]:text-accent [&_a]:underline [&_a]:underline-offset-4 [&_h3]:text-2xl [&_h3]:text-fg [&_li]:ml-5 [&_ol]:list-decimal [&_strong]:text-fg [&_ul]:list-disc"
                // Sanitised on the server with a small allow-list of tags.
                dangerouslySetInnerHTML={{ __html: event.body }}
              />
              {event.opportunity && (
                <Link
                  to={`/education/${event.opportunity.slug}`}
                  className="mt-10 flex items-center gap-4 rounded-2xl border border-border bg-surface p-5 transition-colors hover:border-border-strong"
                >
                  <BookOpen aria-hidden="true" className="size-6 shrink-0 text-highlight" strokeWidth={1.5} />
                  <span>
                    <span className="block text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle">
                      Tonight&rsquo;s class
                    </span>
                    <span className="mt-1 block font-display text-xl text-fg">{event.opportunity.title}</span>
                  </span>
                </Link>
              )}
            </div>
            <aside className="lg:sticky lg:top-28 lg:self-start">
              <RSVPPanel
                key={`${event.slug}|${event.rsvp.state}`}
                event={event}
                onChange={(rsvp) => setRsvpOverride({ slug: event.slug, rsvp })}
              />
            </aside>
          </div>
        )}
      </Section>
    </article>
  )
}
