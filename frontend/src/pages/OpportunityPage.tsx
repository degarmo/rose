import { ArrowLeft, CalendarDays, MapPin } from 'lucide-react'
import { useParams } from 'react-router'
import { DetailItem } from '@/components/content/DetailItem'
import { ErrorState, HeroLoading } from '@/components/content/States'
import { PaywallPanel } from '@/components/membership/PaywallPanel'
import { Badge, ButtonLink, ImageFrame, Section } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { formatEventDate, paragraphs } from '@/lib/format'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from './NotFoundPage'

export function OpportunityPage() {
  const { slug = '' } = useParams()
  const state = useAsync(() => api.opportunity(slug), slug)
  const opportunity = state.status === 'success' ? state.data : null
  useDocumentMeta({ title: opportunity?.title ?? 'Education', description: opportunity?.summary })

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) {
    return <NotFoundPage />
  }

  return (
    <article>
      <div className="relative isolate flex min-h-[55svh] items-end overflow-hidden pb-12 pt-32">
        <ImageFrame
          remote={opportunity?.hero_image}
          alt=""
          fill
          placeholder="candle"
          priority
          reveal={false}
          className="-z-20"
        />
        <div aria-hidden="true" className="absolute inset-0 -z-10 bg-gradient-to-t from-canvas via-canvas/70 to-canvas/20" />
        <div className="mx-auto w-full max-w-3xl px-5 sm:px-8">
          <ButtonLink to="/education" variant="link">
            <ArrowLeft aria-hidden="true" className="size-4" />
            All opportunities
          </ButtonLink>
          {state.status === 'loading' && <HeroLoading label="Loading details" />}
          {opportunity && (
            <>
              <div className="mt-6 flex flex-wrap gap-2">
                <Badge tone="brass">{opportunity.level_label}</Badge>
                <Badge>{opportunity.category_label}</Badge>
                {opportunity.members_only && <Badge tone="rose">Members</Badge>}
              </div>
              <h1 className="mt-6 text-5xl leading-[1.05] text-fg sm:text-6xl">{opportunity.title}</h1>
              <p className="mt-6 text-lg leading-relaxed text-fg-muted sm:text-xl">{opportunity.summary}</p>
            </>
          )}
        </div>
      </div>

      {/* Room for the details while they load, so the footer does not jump. */}
      <Section width="narrow" spacing="tight" className={state.status === 'loading' ? 'min-h-[60svh]' : undefined}>
        {state.status === 'error' && <ErrorState title="This page did not load" onRetry={state.retry} />}
        {opportunity && (
          <>
            {(opportunity.starts_at || opportunity.location_label) && (
              <dl className="grid gap-4 border-y border-border py-6 sm:grid-cols-2">
                {opportunity.starts_at && (
                  <DetailItem icon={CalendarDays} label="When">
                    <time dateTime={opportunity.starts_at}>{formatEventDate(opportunity.starts_at)}</time>
                  </DetailItem>
                )}
                {opportunity.location_label && (
                  <DetailItem icon={MapPin} label="Where">
                    {opportunity.location_label}
                  </DetailItem>
                )}
              </dl>
            )}
            {opportunity.locked || opportunity.body === null ? (
              <PaywallPanel
                className="mt-10"
                title="For members"
                benefit={opportunity.paywall?.benefit ?? 'Members-only classes come with membership.'}
                tiers={opportunity.paywall?.tiers}
              />
            ) : (
              <div className="mt-10 space-y-6 text-lg leading-relaxed text-fg-muted">
                {paragraphs(opportunity.body).map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>
            )}
            <div className="mt-12 flex flex-col gap-3 sm:flex-row">
              {opportunity.cta_label && opportunity.cta_url && (
                <ButtonLink to={opportunity.cta_url} size="lg">
                  {opportunity.cta_label}
                </ButtonLink>
              )}
              <ButtonLink to="/visit" size="lg" variant="ghost">
                Plan your first visit
              </ButtonLink>
            </div>
          </>
        )}
      </Section>
    </article>
  )
}
