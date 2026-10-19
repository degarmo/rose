import { ArrowRight, HandCoins, HandHeart, KeyRound } from 'lucide-react'
import { Copy, CopyHeading } from '@/components/content/Copy'
import { EventCard } from '@/components/content/EventCard'
import { JournalStrip } from '@/components/content/JournalStrip'
import { OpportunityCard } from '@/components/content/OpportunityCard'
import { Reveal } from '@/components/content/Reveal'
import { ErrorState, SkeletonCards, EmptyState } from '@/components/content/States'
import { ValuesStrip } from '@/components/content/ValuesStrip'
import { ButtonLink, Card, ImageFrame, Section } from '@/components/ui'
import { api } from '@/lib/api'
import { usePageContent, type PageCopy } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const FEATURED_COUNT = 3

const UPCOMING_COUNT = 3

function UpcomingEvents() {
  const state = useAsync(() => api.events(), 'home-events')
  if (state.status === 'loading') return <SkeletonCards count={UPCOMING_COUNT} />
  if (state.status === 'error') return <ErrorState title="Events did not load" onRetry={state.retry} />
  const upcoming = state.data.slice(0, UPCOMING_COUNT)
  if (upcoming.length === 0) {
    return <EmptyState title="The calendar is being planned" message="New evenings are added every week." />
  }
  return (
    <ul className="grid gap-5 lg:grid-cols-3">
      {upcoming.map((event, index) => (
        <Reveal as="li" key={event.id} delay={index as 0 | 1 | 2}>
          <EventCard event={event} />
        </Reveal>
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
    <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {featured.map((opportunity, index) => (
        <Reveal as="li" key={opportunity.id} delay={index as 0 | 1 | 2}>
          <OpportunityCard opportunity={opportunity} />
        </Reveal>
      ))}
    </ul>
  )
}

// Get involved: the cards' words are editable copy (involved.1 to involved.3).
const INVOLVED = [
  { icon: HandHeart, to: '/get-involved/volunteer', action: 'Volunteer' },
  { icon: HandCoins, to: '/get-involved/donate', action: 'Donate' },
  { icon: KeyRound, to: '/rentals', action: 'Rentals' },
]

function GetInvolved({ copy }: { copy: PageCopy }) {
  return (
    <ul className="mt-12 grid gap-6 md:grid-cols-3">
      {INVOLVED.map((item, index) => {
        const Icon = item.icon
        const n = index + 1
        return (
          <Reveal as="li" key={item.to} delay={index as 0 | 1 | 2}>
            <Card className="h-full p-8">
              <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
              <Copy copy={copy} k={`involved.${n}.title`} as="h3" className="mt-6 text-2xl text-fg" />
              <Copy copy={copy} k={`involved.${n}.body`} lines={3} className="mt-3 leading-relaxed text-fg-muted" />
              <ButtonLink to={item.to} variant="link" className="mt-6">
                {item.action}
                <ArrowRight aria-hidden="true" className="size-4" />
              </ButtonLink>
            </Card>
          </Reveal>
        )
      })}
    </ul>
  )
}

export function HomePage() {
  const copy = usePageContent('home')
  useDocumentMeta({
    description: 'A volunteer-run members’ house in Chicago for learning, connection and consent-first community.',
  })

  return (
    <>
      <section className="relative isolate flex min-h-svh items-end overflow-hidden pb-20 pt-32 sm:items-center sm:pb-24">
        <ImageFrame image="home-hero.webp" alt="" fill placeholder="velvet" priority reveal={false} className="-z-20" />
        <div aria-hidden="true" className="absolute inset-0 -z-10 bg-gradient-to-t from-canvas via-canvas/80 to-canvas/50" />
        <div className="mx-auto w-full max-w-6xl px-5 sm:px-8">
          <Reveal>
            <p className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.32em] text-highlight">
              <span aria-hidden="true" className="h-px w-10 bg-highlight/70" />
              {copy.text('hero.eyebrow')}
            </p>
          </Reveal>
          <Reveal delay={1}>
            <h1 className="mt-6 max-w-4xl text-[clamp(3rem,10vw,6.5rem)] leading-[0.98] text-fg">
              {copy.status === 'loading' && <span className="sr-only">Loading</span>}
              <Copy copy={copy} k="hero.title" as="span" lines={2} />
            </h1>
          </Reveal>
          <Reveal delay={2}>
            <Copy copy={copy} k="hero.lede" lines={2} className="mt-8 max-w-xl text-lg leading-relaxed text-fg-muted sm:text-xl" />
          </Reveal>
          <Reveal delay={3} className="mt-10 flex flex-col gap-3 sm:flex-row">
            <ButtonLink to="/visit" size="lg">
              Plan a Visit
            </ButtonLink>
            <ButtonLink to="/join" size="lg" variant="ghost">
              Become a Member
            </ButtonLink>
          </Reveal>
        </div>
      </section>

      <Section aria-labelledby="who-we-are">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-20">
          <ImageFrame image="home-interior.webp" alt="" ratio="4/5" placeholder="architecture" className="rounded-2xl" />
          <Reveal>
            <CopyHeading copy={copy} prefix="who" id="who-we-are" />
            <ButtonLink to="/about" variant="link" className="mt-8">
              More about us
              <ArrowRight aria-hidden="true" className="size-4" />
            </ButtonLink>
          </Reveal>
        </div>
      </Section>

      <Section tone="surface" aria-labelledby="week">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <CopyHeading copy={copy} prefix="week" id="week" />
          <ButtonLink to="/events" variant="link">
            All events
            <ArrowRight aria-hidden="true" className="size-4" />
          </ButtonLink>
        </div>
        <div className="mt-12">
          <UpcomingEvents />
        </div>
      </Section>

      <Section aria-labelledby="featured">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <CopyHeading copy={copy} prefix="education" id="featured" />
          <ButtonLink to="/education" variant="link">
            All opportunities
            <ArrowRight aria-hidden="true" className="size-4" />
          </ButtonLink>
        </div>
        <div className="mt-12">
          <FeaturedOpportunities />
        </div>
      </Section>

      <Section aria-labelledby="journal" spacing="tight">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <CopyHeading copy={copy} prefix="journal" id="journal" />
          <ButtonLink to="/journal" variant="link">
            See the journal
            <ArrowRight aria-hidden="true" className="size-4" />
          </ButtonLink>
        </div>
        <div className="mt-10">
          <JournalStrip />
        </div>
      </Section>

      <Section tone="surface" aria-labelledby="involved">
        <CopyHeading copy={copy} prefix="involved" id="involved" />
        <GetInvolved copy={copy} />
      </Section>

      <Section tone="sunken" spacing="tight" aria-labelledby="values">
        <h2 id="values" className="sr-only">
          Our values
        </h2>
        <ValuesStrip />
      </Section>

      <section className="relative isolate overflow-hidden py-28 sm:py-36">
        <ImageFrame image="home-closing.webp" alt="" fill placeholder="leather" reveal={false} className="-z-20" />
        <div aria-hidden="true" className="absolute inset-0 -z-10 bg-canvas/70" />
        <Reveal className="mx-auto max-w-3xl px-5 text-center sm:px-8">
          <Copy copy={copy} k="closing.title" as="h2" lines={2} className="text-4xl leading-tight text-fg sm:text-6xl" />
          <Copy copy={copy} k="closing.lede" lines={2} className="mx-auto mt-6 max-w-xl text-lg text-fg-muted" />
          <div className="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
            <ButtonLink to="/visit" size="lg">
              Plan a Visit
            </ButtonLink>
            <ButtonLink to="/contact" size="lg" variant="ghost">
              Ask a question
            </ButtonLink>
          </div>
        </Reveal>
      </section>
    </>
  )
}
