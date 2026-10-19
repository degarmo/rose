import { Link } from 'react-router'
import { Copy } from '@/components/content/Copy'
import { EventCard } from '@/components/content/EventCard'
import { JournalStrip } from '@/components/content/JournalStrip'
import { OpportunityCard } from '@/components/content/OpportunityCard'
import { ErrorState, SkeletonCards, EmptyState } from '@/components/content/States'
import { ValuesStrip } from '@/components/content/ValuesStrip'
import { ButtonLink, GradientBackground, GUTTER, ImageFrame, Section, SectionHeading } from '@/components/ui'
import { api } from '@/lib/api'
import { cn } from '@/lib/cn'
import { usePageContent, type PageCopy } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const FEATURED_COUNT = 3

const UPCOMING_COUNT = 3

const CARD_GRID = 'grid gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6'

function UpcomingEvents() {
  const state = useAsync(() => api.events(), 'home-events')
  if (state.status === 'loading') return <SkeletonCards count={UPCOMING_COUNT} />
  if (state.status === 'error') return <ErrorState title="Events did not load" onRetry={state.retry} />
  const upcoming = state.data.slice(0, UPCOMING_COUNT)
  if (upcoming.length === 0) {
    return <EmptyState title="The calendar is being planned" message="New evenings are added every week." />
  }
  return (
    <ul className={CARD_GRID}>
      {upcoming.map((event) => (
        <li key={event.id}>
          <EventCard event={event} />
        </li>
      ))}
    </ul>
  )
}

function FeaturedOpportunities() {
  const state = useAsync(() => api.opportunities(), 'featured')

  if (state.status === 'loading') return <SkeletonCards count={FEATURED_COUNT} />
  if (state.status === 'error') {
    return <ErrorState title="Classes did not load" onRetry={state.retry} />
  }
  const featured = state.data.slice(0, FEATURED_COUNT)
  if (featured.length === 0) {
    return <EmptyState title="New classes are on the way" message="Check back soon for the next season." />
  }
  return (
    <ul className={CARD_GRID}>
      {featured.map((opportunity, index) => (
        // Phones and tablets show two classes, desktop three (design: "Learn with us").
        <li key={opportunity.id} className={cn(index >= 2 && 'max-lg:hidden')}>
          <OpportunityCard opportunity={opportunity} />
        </li>
      ))}
    </ul>
  )
}

/** A home section title from the editable copy, with an optional rose link on the right. */
function HomeHeading({ copy, prefix, id, action }: { copy: PageCopy; prefix: string; id: string; action?: { to: string; label: string } }) {
  return <SectionHeading id={id} action={action} title={<Copy copy={copy} k={`${prefix}.title`} as="span" />} />
}

// Get involved: the cards' words are editable copy (involved.1 to involved.3); the links are interface text.
const INVOLVED = [
  { to: '/get-involved/volunteer', action: 'See roles' },
  { to: '/get-involved/donate', action: 'Give' },
  { to: '/rentals', action: 'Ask about rentals' },
]

function GetInvolved({ copy }: { copy: PageCopy }) {
  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6">
      {INVOLVED.map((item, index) => {
        const n = index + 1
        return (
          <li key={item.to} className="flex flex-col gap-1.5 rounded-card bg-surface p-6 lg:gap-3 lg:p-8">
            <Copy copy={copy} k={`involved.${n}.title`} as="h3" className="text-[1.375rem] leading-[1.2] text-fg lg:text-[1.625rem]" />
            <Copy copy={copy} k={`involved.${n}.body`} lines={2} className="flex-1 text-sm text-fg-muted lg:text-body" />
            <Link to={item.to} className="self-start text-sm font-semibold text-link hover:text-primary-hover">
              {item.action} <span aria-hidden="true">→</span>
            </Link>
          </li>
        )
      })}
    </ul>
  )
}

/** The home page (design: Public Site, section 02, "Home"). */
export function HomePage() {
  const copy = usePageContent('home')
  useDocumentMeta({
    description: 'A volunteer-run members’ club in Chicago for education, social nights and consent-first community.',
  })

  return (
    <>
      <section aria-labelledby="home-title" className="relative isolate overflow-hidden">
        <GradientBackground />
        <div className={cn('mx-auto grid max-w-[1440px] items-center gap-5 pb-10 pt-12 lg:grid-cols-2 lg:gap-16 lg:py-24', GUTTER)}>
          <div className="flex flex-col gap-5 lg:gap-6">
            <h1 id="home-title" className="text-[2.625rem] font-light leading-[1.05] tracking-[-0.01em] text-fg lg:text-display">
              {copy.status === 'loading' && <span className="sr-only">Loading</span>}
              <Copy copy={copy} k="hero.title" as="span" lines={2} />
            </h1>
            <Copy copy={copy} k="hero.lede" lines={2} className="max-w-[460px] text-base text-fg lg:text-lg" />
            <div className="flex flex-col gap-2.5 sm:flex-row sm:gap-3">
              <ButtonLink to="/visit" size="lg">
                Plan a Visit
              </ButtonLink>
              <ButtonLink to="/membership" size="lg" variant="secondary">
                Become a Member
              </ButtonLink>
            </div>
          </div>
          <ImageFrame
            image="home-hero.webp"
            alt=""
            ratio="4/5"
            placeholder="rose"
            priority
            className="rounded-card lg:aspect-[5/4]"
            sizes="(min-width: 1024px) 50vw, 100vw"
          />
        </div>
      </section>

      <Section rule aria-labelledby="who-we-are">
        <div className="grid gap-3 lg:grid-cols-[1fr_2fr] lg:gap-16">
          <Copy copy={copy} k="who.title" as="h2" id="who-we-are" className="text-[1.75rem] font-light leading-[1.2] text-fg lg:text-h2" />
          <Copy
            copy={copy}
            k="who.lede"
            lines={4}
            className="max-w-[680px] lg:text-lead [&>p:first-child]:text-fg"
          />
        </div>
      </Section>

      <Section tone="surface" aria-labelledby="week">
        <HomeHeading copy={copy} prefix="week" id="week" action={{ to: '/events', label: 'All events' }} />
        <UpcomingEvents />
      </Section>

      <Section aria-labelledby="featured">
        <HomeHeading copy={copy} prefix="education" id="featured" action={{ to: '/education', label: 'All education' }} />
        <FeaturedOpportunities />
      </Section>

      <Section rule aria-labelledby="journal">
        <HomeHeading copy={copy} prefix="journal" id="journal" action={{ to: '/journal', label: 'Read the Journal' }} />
        <JournalStrip />
      </Section>

      <ValuesStrip />

      <Section aria-labelledby="involved">
        <HomeHeading copy={copy} prefix="involved" id="involved" />
        <GetInvolved copy={copy} />
      </Section>

      <Section rule spacing="none" aria-labelledby="closing" className="py-14 lg:py-24">
        <div className="flex flex-col items-center gap-4 text-center lg:gap-6">
          <Copy
            copy={copy}
            k="closing.title"
            as="h2"
            id="closing"
            lines={2}
            className="w-full max-w-[640px] text-[2.125rem] font-light leading-[1.1] text-fg lg:text-h2-lg"
          />
          <Copy copy={copy} k="closing.lede" className="hidden text-fg-muted lg:block lg:text-lead" />
          <ButtonLink to="/visit" size="lg">
            Plan a Visit
          </ButtonLink>
        </div>
      </Section>
    </>
  )
}
