import { useParams } from 'react-router'
import { DetailItem } from '@/components/content/DetailItem'
import { ErrorState, HeroLoading } from '@/components/content/States'
import { PaywallPanel } from '@/components/membership/PaywallPanel'
import { ButtonLink, Card, Chip, GUTTER, ImageFrame } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { formatEventDate, paragraphs } from '@/lib/format'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from './NotFoundPage'

/**
 * A class or workshop, laid out like Event detail: a full-width picture, the title, When /
 * Where and the description, with the sign-up (or the members' paywall) on the right.
 */
export function OpportunityPage() {
  const { slug = '' } = useParams()
  const state = useAsync(() => api.opportunity(slug), slug)
  const opportunity = state.status === 'success' ? state.data : null
  useDocumentMeta({ title: opportunity?.title ?? 'Education', description: opportunity?.summary })

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) {
    return <NotFoundPage />
  }

  const locked = Boolean(opportunity && (opportunity.locked || opportunity.body === null))
  const cta = opportunity?.cta_label && opportunity.cta_url ? { label: opportunity.cta_label, to: opportunity.cta_url } : null

  return (
    <article>
      <ImageFrame
        remote={opportunity?.hero_image}
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
        {state.status === 'loading' && <HeroLoading label="Loading details" />}
        {state.status === 'error' && (
          <ErrorState title="This page did not load" onRetry={state.retry} className="lg:col-span-2" />
        )}
        {opportunity && (
          <>
            <div className="flex min-w-0 flex-col gap-4 lg:gap-6">
              <div className="flex flex-wrap items-center gap-3 text-[0.8125rem] text-fg-muted">
                <Chip>{opportunity.category_label}</Chip>
                <span>{opportunity.level_label}</span>
                {opportunity.members_only && <span>Members only</span>}
              </div>
              <h1 className="text-[2.25rem] font-light leading-[1.05] text-fg lg:text-h1">{opportunity.title}</h1>
              {(opportunity.starts_at || opportunity.location_label) && (
                <dl className="grid gap-1 border-y border-border py-4 text-sm leading-[1.6] lg:grid-cols-3 lg:gap-6 lg:py-6">
                  {opportunity.starts_at && (
                    <DetailItem label="When">
                      <time dateTime={opportunity.starts_at}>{formatEventDate(opportunity.starts_at)}</time>
                    </DetailItem>
                  )}
                  {opportunity.location_label && <DetailItem label="Where">{opportunity.location_label}</DetailItem>}
                </dl>
              )}
              <div className="flex max-w-[640px] flex-col gap-4 leading-relaxed lg:text-[1.0625rem]">
                {opportunity.summary && <p className="text-fg">{opportunity.summary}</p>}
                {!locked &&
                  opportunity.body &&
                  paragraphs(opportunity.body).map((paragraph, index) => (
                    <p key={index} className="text-fg-muted">
                      {paragraph}
                    </p>
                  ))}
              </div>
            </div>
            <aside className="flex flex-col gap-4 lg:sticky lg:top-28 lg:self-start">
              {locked ? (
                <PaywallPanel
                  size="lg"
                  headingLevel="h2"
                  title="For members"
                  benefit={opportunity.paywall?.benefit || 'The full description, readings and sign-up are in the member area.'}
                  tiers={opportunity.paywall?.tiers}
                />
              ) : (
                <Card shape="panel" className="gap-4 p-5 sm:gap-5 sm:p-7">
                  <h2 className="text-[1.375rem] text-fg sm:text-2xl">Take part</h2>
                  {cta && (
                    <ButtonLink to={cta.to} size="lg" className="w-full">
                      {cta.label}
                    </ButtonLink>
                  )}
                  {cta?.to !== '/visit' && (
                    <ButtonLink to="/visit" size="lg" variant="outline" className="w-full">
                      Plan your first visit
                    </ButtonLink>
                  )}
                </Card>
              )}
            </aside>
          </>
        )}
      </div>
    </article>
  )
}
