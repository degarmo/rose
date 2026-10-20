import { IdCard } from 'lucide-react'
import { Link } from 'react-router'
import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { ErrorState, LoadingState } from '@/components/content/States'
import { ButtonLink, Card, GUTTER } from '@/components/ui'
import { cn } from '@/lib/cn'
import { membershipApi, priceLabel } from '@/lib/membershipApi'
import { usePageContent } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const BAND = cn('mx-auto max-w-[1440px]', GUTTER)

function GuestPass() {
  const tiers = useAsync(() => membershipApi.tiers(), 'tiers')
  if (tiers.status === 'loading') return <LoadingState label="Loading the guest pass" className="py-2" />
  if (tiers.status === 'error') return <ErrorState title="The guest pass did not load" onRetry={tiers.retry} />
  const pass = tiers.data.find((tier) => tier.is_guest_pass)
  if (!pass) {
    return (
      <p className="text-fg-muted">
        Guest passes are not offered online right now. Come to an open evening and our hosts will help you at the door.
      </p>
    )
  }
  return (
    <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="font-display text-[2rem] font-light leading-[1.1] text-fg lg:text-[2.5rem]">{priceLabel(pass)}</p>
        <p className="mt-1 text-sm text-fg-muted">
          {pass.name}. Paid at the door{pass.is_placeholder ? ' (placeholder price)' : ''}.
        </p>
      </div>
      <ButtonLink to={`/join?tier=${encodeURIComponent(pass.slug)}`} size="lg">
        Sign up as a guest
      </ButtonLink>
    </div>
  )
}

/** Guests (no design of its own; laid out like Plan Your Visit). */
export function GuestsPage() {
  useDocumentMeta({
    title: 'Guests',
    description: 'Visiting as a guest: what to expect, the house rules, what to bring and the guest pass.',
  })
  const copy = usePageContent('guests')

  return (
    <>
      <PageHero copy={copy} image="visit-hero.webp" placeholder="rose" />

      <section aria-labelledby="who" className={cn(BAND, 'pb-6 lg:pb-10')}>
        <CopyHeading copy={copy} prefix="who" id="who" className="mb-0 lg:mb-0" />
      </section>

      <section aria-label="Before you come" className={cn(BAND, 'pb-6 lg:pb-16')}>
        <ul className="grid gap-4 lg:grid-cols-2 lg:gap-12">
          {['expect', 'rules'].map((prefix) => (
            <li key={prefix} className="flex flex-col gap-1 border-t border-border pt-4 lg:gap-2 lg:pt-5">
              <Copy copy={copy} k={`${prefix}.title`} as="h2" className="text-[1.375rem] leading-[1.3] text-fg lg:text-2xl" />
              <Copy copy={copy} k={`${prefix}.body`} lines={3} className="text-sm leading-[1.6] text-fg-muted lg:text-[0.9375rem]" />
              {prefix === 'rules' && (
                <Link to="/house-rules" className="mt-1 inline-flex min-h-6 items-center self-start text-sm font-semibold text-link hover:text-primary-hover">
                  Read the house rules
                </Link>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="guest-id" className={BAND}>
        <div className="flex flex-col gap-2 rounded-card bg-blush p-5 lg:flex-row lg:gap-6 lg:p-8">
          <IdCard aria-hidden="true" strokeWidth={1.5} className="size-8 shrink-0 text-ink" />
          <div className="flex flex-col gap-2 lg:gap-1.5">
            <Copy copy={copy} k="id.title" as="h2" id="guest-id" className="text-xl leading-[1.3] text-fg lg:text-2xl" />
            <Copy copy={copy} k="id.body" lines={2} className="max-w-[720px] text-sm leading-[1.6] text-fg-muted-tint lg:text-[0.9375rem]" />
          </div>
        </div>
      </section>

      <section aria-labelledby="pass" className={cn(BAND, 'pb-12 pt-10 lg:py-16')}>
        <div className="max-w-[860px]">
          <CopyHeading copy={copy} prefix="price" id="pass" />
          <Card shape="panel" className="p-5 sm:p-7">
            <GuestPass />
          </Card>
          <Copy copy={copy} k="steps" lines={3} className="mt-6 text-sm leading-[1.6] lg:text-[0.9375rem]" />
        </div>
      </section>
    </>
  )
}
