import { ArrowRight, BookOpen, GlassWater } from 'lucide-react'
import { OpportunityCard } from '@/components/content/OpportunityCard'
import { Reveal } from '@/components/content/Reveal'
import { ErrorState, SkeletonCards, EmptyState } from '@/components/content/States'
import { ValuesStrip } from '@/components/content/ValuesStrip'
import { useSiteSettings } from '@/components/layout/siteSettingsContext'
import { ButtonLink, Card, ImageFrame, Section, SectionHeading } from '@/components/ui'
import { api } from '@/lib/api'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const FEATURED_COUNT = 3

const WEEK = [
  {
    day: 'Thursdays',
    title: 'Education nights',
    body: 'Classes, workshops and open discussion led by experienced members. Come to learn, ask questions, or simply listen from a comfortable chair.',
    detail: 'Orientation for newcomers runs most weeks.',
    image: 'week-thursday.webp',
    placeholder: 'candle' as const,
    icon: BookOpen,
  },
  {
    day: 'Fridays and Saturdays',
    title: 'Weekend socials',
    body: 'Unhurried evenings for conversation and connection, with volunteer hosts on hand all night and quiet corners whenever you want them.',
    detail: 'Open to members and their invited guests.',
    image: 'week-weekend.webp',
    placeholder: 'silk' as const,
    icon: GlassWater,
  },
]

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

export function HomePage() {
  const settings = useSiteSettings()
  useDocumentMeta({
    description: 'A volunteer-run members’ house in Chicago for learning, connection and consent-first community.',
  })

  return (
    <>
      <section className="relative isolate flex min-h-svh items-end overflow-hidden pb-20 pt-32 sm:items-center sm:pb-24">
        <ImageFrame image="home-hero.webp" alt="" fill placeholder="velvet" priority reveal={false} className="-z-20" />
        <div aria-hidden="true" className="absolute inset-0 -z-10 bg-gradient-to-t from-canvas via-canvas/60 to-canvas/20" />
        <div className="mx-auto w-full max-w-6xl px-5 sm:px-8">
          <Reveal>
            <p className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.32em] text-highlight">
              <span aria-hidden="true" className="h-px w-10 bg-highlight/70" />
              Chicago, after dark
            </p>
          </Reveal>
          <Reveal delay={1}>
            <h1 className="mt-6 max-w-4xl text-[clamp(3rem,10vw,6.5rem)] leading-[0.98] text-fg">
              A house for <em className="text-accent">curiosity</em>, care and good company.
            </h1>
          </Reveal>
          <Reveal delay={2}>
            <p className="mt-8 max-w-xl text-lg leading-relaxed text-fg-muted sm:text-xl">
              {settings.status === 'success' && settings.data.tagline
                ? settings.data.tagline
                : 'A volunteer-run members’ house for learning, connection and consent-first community.'}
            </p>
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
            <SectionHeading
              id="who-we-are"
              eyebrow="Who we are"
              title="A private club with an open door."
              lede={
                <>
                  <p>
                    We are a nonprofit community of adults who believe exploration is better with education, honesty and
                    people who look out for one another.
                  </p>
                  <p className="mt-4">
                    Whether this is your first time anywhere like us or you have been part of community spaces for years,
                    you will find hosts who remember your name and a pace that lets you settle in.
                  </p>
                </>
              }
            />
            <ButtonLink to="/about" variant="link" className="mt-8">
              More about us
              <ArrowRight aria-hidden="true" className="size-4" />
            </ButtonLink>
          </Reveal>
        </div>
      </Section>

      <Section tone="surface" aria-labelledby="week">
        <SectionHeading
          id="week"
          eyebrow="A week at the house"
          title="Learn on Thursdays. Unwind on weekends."
          lede="Two rhythms, one community. Most people start with an education night, then find their way to the weekends."
        />
        <div className="mt-14 grid gap-6 md:grid-cols-2">
          {WEEK.map((item, index) => {
            const Icon = item.icon
            return (
              <Reveal key={item.title} delay={index as 0 | 1}>
                <Card className="h-full">
                  <ImageFrame image={item.image} alt="" ratio="4/3" placeholder={item.placeholder} reveal={false} />
                  <div className="p-6 sm:p-8">
                    <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.24em] text-highlight">
                      <Icon aria-hidden="true" className="size-4" />
                      {item.day}
                    </p>
                    <h3 className="mt-4 text-3xl text-fg">{item.title}</h3>
                    <p className="mt-4 leading-relaxed text-fg-muted">{item.body}</p>
                    <p className="mt-4 text-sm text-fg-subtle">{item.detail}</p>
                  </div>
                </Card>
              </Reveal>
            )
          })}
        </div>
      </Section>

      <Section aria-labelledby="featured">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <SectionHeading
            id="featured"
            eyebrow="Education"
            title="Coming up"
            lede="Every class is beginner-friendly unless it says otherwise."
          />
          <ButtonLink to="/education" variant="link">
            All opportunities
            <ArrowRight aria-hidden="true" className="size-4" />
          </ButtonLink>
        </div>
        <div className="mt-12">
          <FeaturedOpportunities />
        </div>
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
          <h2 className="text-4xl leading-tight text-fg sm:text-6xl">Your first evening starts with a conversation.</h2>
          <p className="mx-auto mt-6 max-w-xl text-lg text-fg-muted">
            Tell us a little about yourself, and we will help you find the right night to begin.
          </p>
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
