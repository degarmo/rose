import { IdCard } from 'lucide-react'
import { Link } from 'react-router'
import { Copy } from '@/components/content/Copy'
import { FAQAccordion } from '@/components/content/FAQAccordion'
import { PageHero } from '@/components/content/PageHero'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useSiteSettings } from '@/components/layout/siteSettingsContext'
import { GUTTER, SectionHeading } from '@/components/ui'
import { api } from '@/lib/api'
import { cn } from '@/lib/cn'
import { usePageContent, type PageCopy } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** How many questions the page shows; the FAQ page has the rest. */
const FAQ_COUNT = 4

const SUBHEADING = 'text-[1.625rem] font-light leading-[1.2] text-fg lg:text-h2'

/** Each line of the hours text, split at "Day: time" when it has that shape. */
function hourRows(text: string) {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const at = line.indexOf(': ')
      return at > 0 ? { day: line.slice(0, at), time: line.slice(at + 2) } : { day: line, time: '' }
    })
}

function Hours() {
  const settings = useSiteSettings()
  if (settings.status === 'loading') return <LoadingState label="Loading hours" className="py-2" />
  if (settings.status === 'error') return <ErrorState title="Hours did not load" onRetry={settings.retry} />
  const rows = hourRows(settings.data.hours_text)
  if (rows.length === 0) return <p className="text-fg-muted">Hours are announced each season.</p>
  return (
    <dl className="flex flex-col gap-2 text-sm leading-[1.6] lg:gap-4 lg:text-[0.9375rem]">
      {rows.map((row, index) => (
        <div key={index} className="flex justify-between gap-4 border-b border-border py-2.5 lg:py-3">
          <dt className="font-semibold text-fg">{row.day}</dt>
          {row.time && <dd className="text-right text-fg-muted">{row.time}</dd>}
        </div>
      ))}
    </dl>
  )
}

/** The address on one line, its lines joined with commas. */
function oneLineAddress(text: string) {
  return text
    .split('\n')
    .map((line) => line.trim().replace(/,$/, ''))
    .filter(Boolean)
    .join(', ')
}

/** The address and phone number in a small heading size, then the directions in smaller text. */
function Directions() {
  const settings = useSiteSettings()
  if (settings.status === 'loading') return <LoadingState label="Loading location" className="py-2" />
  if (settings.status === 'error') return <ErrorState title="Location did not load" onRetry={settings.retry} />
  const { address_text: address, phone_text: phone, directions_text: directions } = settings.data
  if (!address && !phone && !directions) return <p className="text-fg-muted">Directions are shared with confirmed visitors.</p>
  return (
    <div className="flex flex-col gap-5">
      {(address || phone) && (
        <dl className="flex flex-col gap-1.5 font-display text-xl leading-[1.3] text-fg lg:text-[1.375rem]">
          {address && (
            <div>
              <dt className="inline">Address: </dt>
              <dd className="inline">{oneLineAddress(address)}</dd>
            </div>
          )}
          {phone && (
            <div>
              <dt className="inline">Phone Number: </dt>
              <dd className="inline">
                <a href={`tel:${phone.replace(/[^\d+]/g, '')}`} className="text-link hover:text-primary-hover">
                  {phone}
                </a>
              </dd>
            </div>
          )}
        </dl>
      )}
      {directions && (
        <div className="flex flex-col gap-1.5 text-[0.8125rem] leading-[1.6] lg:text-sm">
          <p className="font-semibold text-fg">Directions:</p>
          <p className="whitespace-pre-line text-fg-muted">{directions}</p>
        </div>
      )}
    </div>
  )
}

function Questions({ copy }: { copy: PageCopy }) {
  const state = useAsync(() => api.faqs(), 'faqs')
  if (state.status === 'success' && state.data.length === 0) return null
  const more = state.status === 'success' && state.data.length > FAQ_COUNT
  return (
    <section aria-labelledby="faq" className={cn('mx-auto max-w-[1440px] pb-12 pt-8 lg:pb-20 lg:pt-0', GUTTER)}>
      <div className="max-w-[860px]">
        <SectionHeading
          id="faq"
          title={<Copy copy={copy} k="faq.title" as="span" />}
          action={more ? { to: '/faq', label: 'All questions' } : undefined}
          className="mb-2 lg:mb-4"
        />
        {state.status === 'loading' && <LoadingState label="Loading questions" className="py-4" />}
        {state.status === 'error' && <ErrorState title="Questions did not load" onRetry={state.retry} />}
        {state.status === 'success' && <FAQAccordion items={state.data.slice(0, FAQ_COUNT)} openFirst />}
      </div>
    </section>
  )
}

/** Plan Your Visit (design: "Plan Your Visit"): steps, the photo-ID callout, hours, directions, questions. */
export function VisitPage() {
  useDocumentMeta({
    title: 'Plan Your Visit',
    description: 'What to expect on your first visit, what to bring, hours and how to find us.',
  })
  const copy = usePageContent('visit')
  const steps = copy.status === 'loading' ? [1, 2, 3] : copy.items('steps')

  return (
    <>
      <PageHero copy={copy} image="visit-plan.webp" placeholder="rose" />

      <section aria-labelledby="expect" className={cn('mx-auto max-w-[1440px] pb-6 lg:pb-16', GUTTER)}>
        <Copy copy={copy} k="expect.title" as="h2" id="expect" className="sr-only" />
        <ol className="grid gap-4 lg:grid-cols-3 lg:gap-12">
          {steps.map((n, index) => (
            <li key={n} className="flex flex-col gap-1 border-t border-border pt-4 lg:gap-2 lg:pt-5">
              <span aria-hidden="true" className="text-xs font-semibold tracking-[0.06em] text-link">
                {String(index + 1).padStart(2, '0')}
              </span>
              <Copy copy={copy} k={`steps.${n}.title`} as="h3" className="text-[1.375rem] leading-[1.3] text-fg lg:text-2xl" />
              <Copy copy={copy} k={`steps.${n}.body`} lines={2} className="text-sm leading-[1.6] text-fg-muted lg:text-[0.9375rem]" />
            </li>
          ))}
        </ol>
        <Link to="/house-rules" className="mt-5 inline-flex min-h-6 items-center text-sm font-semibold text-link hover:text-primary-hover lg:mt-8">
          Read the house rules
        </Link>
      </section>

      <section aria-labelledby="id-required" className={cn('mx-auto max-w-[1440px]', GUTTER)}>
        <div className="flex flex-col gap-2 rounded-card bg-blush p-5 lg:flex-row lg:gap-6 lg:p-8">
          <IdCard aria-hidden="true" strokeWidth={1.5} className="size-8 shrink-0 text-wordmark" />
          <div className="flex flex-col gap-2 lg:gap-1.5">
            <Copy copy={copy} k="id.title" as="h2" id="id-required" className="text-xl leading-[1.3] text-fg lg:text-2xl" />
            <Copy copy={copy} k="id.body" lines={2} className="max-w-[720px] text-sm leading-[1.6] text-fg-muted-tint lg:text-[0.9375rem]" />
          </div>
        </div>
      </section>

      <section
        aria-label="Hours and directions"
        id="directions"
        className={cn('mx-auto grid max-w-[1440px] scroll-mt-24 gap-8 pt-8 lg:grid-cols-2 lg:gap-16 lg:py-16', GUTTER)}
      >
        <div className="flex flex-col gap-2 lg:gap-4">
          <Copy copy={copy} k="hours.title" as="h2" className={SUBHEADING} />
          <Hours />
        </div>
        <div className="flex flex-col gap-2 lg:gap-4">
          <Copy copy={copy} k="directions.title" as="h2" className={SUBHEADING} />
          <Directions />
        </div>
      </section>

      <Questions copy={copy} />
    </>
  )
}
