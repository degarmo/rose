import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { DetailItem } from '@/components/content/DetailItem'
import { RICH_TEXT } from '@/components/content/richText'
import { RSVPPanel } from '@/components/content/RSVPPanel'
import { ErrorState, HeroLoading } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { Chip, GUTTER, ImageFrame } from '@/components/ui'
import { api, ApiError, type EventDetail, type RSVPState } from '@/lib/api'
import { cn } from '@/lib/cn'
import { formatShortDate, formatTimeRange } from '@/lib/format'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from './NotFoundPage'

/**
 * Event detail (design: "Event detail"): a full-width picture, then the title, the When /
 * Where rules and the description beside the RSVP panel.
 */
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
      <ImageFrame
        remote={event?.hero_image}
        alt=""
        placeholder="warm"
        priority
        className="lg:aspect-auto lg:h-[420px]"
      />

      {/* Room for the details while they load, so the footer does not jump. */}
      <div
        className={cn(
          'mx-auto grid max-w-[1440px] gap-6 pb-12 pt-7 lg:grid-cols-[minmax(0,1fr)_400px] lg:gap-20 lg:pb-20 lg:pt-14',
          GUTTER,
          state.status === 'loading' && 'min-h-[60svh]',
        )}
      >
        {state.status === 'loading' && <HeroLoading label="Loading event" />}
        {state.status === 'error' && (
          <ErrorState title="This event did not load" onRetry={state.retry} className="lg:col-span-2" />
        )}
        {event && (
          <>
            <div className="flex min-w-0 flex-col gap-4 lg:gap-6">
              <div className="flex flex-wrap items-center gap-3 text-[0.8125rem] text-fg-muted">
                <Chip>{event.category_label}</Chip>
              </div>
              <h1 className="text-[2.25rem] font-light leading-[1.05] text-fg lg:text-h1">{event.title}</h1>
              <dl className="grid gap-1 border-y border-border py-4 text-sm leading-[1.6] lg:grid-cols-3 lg:gap-6 lg:py-6">
                <DetailItem label="When">
                  <time dateTime={event.starts_at}>
                    {formatShortDate(event.starts_at)} · {formatTimeRange(event.starts_at, event.ends_at)}
                  </time>
                </DetailItem>
                {event.location_label && <DetailItem label="Where">{event.location_label}</DetailItem>}
              </dl>
              {event.body ? (
                <div
                  className={cn('max-w-[640px] lg:text-[1.0625rem]', RICH_TEXT, '[&>p:first-child]:text-fg')}
                  // Sanitised on the server with a small allow-list of tags.
                  dangerouslySetInnerHTML={{ __html: event.body }}
                />
              ) : (
                event.summary && <p className="max-w-[640px] text-fg lg:text-[1.0625rem]">{event.summary}</p>
              )}
              {event.opportunity && (
                <Link
                  to={`/education/${event.opportunity.slug}`}
                  className="mt-2 flex max-w-[640px] flex-col gap-1 rounded-card border border-border p-5 transition-colors hover:border-fg-muted"
                >
                  <span className="text-[0.8125rem] text-fg-muted">Tonight&rsquo;s class</span>
                  <span className="font-display text-xl leading-[1.2] text-fg lg:text-card-title">{event.opportunity.title}</span>
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
          </>
        )}
      </div>
    </article>
  )
}
