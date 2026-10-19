import { ArrowRight, HeartHandshake, Landmark } from 'lucide-react'
import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { Reveal } from '@/components/content/Reveal'
import { StaffCard } from '@/components/content/StaffCard'
import { ErrorState, SkeletonCards } from '@/components/content/States'
import { ButtonLink, Card, Section } from '@/components/ui'
import { valueIcon } from '@/content/values'
import { api } from '@/lib/api'
import { usePageContent } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const STRIP_COUNT = 6

function StaffStrip() {
  const state = useAsync(() => api.staff(), 'staff')
  if (state.status === 'loading') return <SkeletonCards count={3} />
  if (state.status === 'error') return <ErrorState title="Our staff did not load" onRetry={state.retry} />
  if (state.data.length === 0) return null
  return (
    <ul className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-3">
      {state.data.slice(0, STRIP_COUNT).map((person, index) => (
        <Reveal as="li" key={person.slug} delay={(index % 3) as 0 | 1 | 2}>
          <StaffCard person={person} compact />
        </Reveal>
      ))}
    </ul>
  )
}

function Values() {
  const copy = usePageContent('values')
  const items = copy.status === 'loading' ? [1, 2, 3, 4] : copy.items('values')
  return (
    <ul className="mt-14 grid gap-x-12 gap-y-14 md:grid-cols-2">
      {items.map((n, index) => {
        const Icon = valueIcon(n)
        return (
          <Reveal as="li" key={n} delay={(index % 2) as 0 | 1} className="border-t border-border pt-8">
            <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
            <Copy copy={copy} k={`values.${n}.title`} as="h3" className="mt-5 text-3xl text-fg" />
            <Copy copy={copy} k={`values.${n}.long`} lines={3} className="mt-4 leading-relaxed text-fg-muted" />
          </Reveal>
        )
      })}
    </ul>
  )
}

export function AboutPage() {
  useDocumentMeta({
    title: 'About',
    description: 'Our mission, our values and the volunteers who keep the house running.',
  })
  const copy = usePageContent('about')

  return (
    <>
      <PageHero copy={copy} image="about-hero.webp" placeholder="architecture" />

      <Section width="narrow" aria-labelledby="mission">
        <Reveal>
          <CopyHeading copy={copy} prefix="mission" id="mission" />
        </Reveal>
      </Section>

      <Section tone="surface" spacing="tight" aria-label="How we are run">
        <div className="grid gap-6 md:grid-cols-2">
          <Reveal>
            <Card className="h-full p-8">
              <Landmark aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
              <Copy copy={copy} k="nonprofit.title" as="h2" className="mt-6 text-3xl text-fg" />
              <Copy copy={copy} k="nonprofit.body" lines={3} className="mt-4 leading-relaxed text-fg-muted" />
              <ButtonLink to="/get-involved/donate" variant="link" className="mt-4">
                Ways to give
              </ButtonLink>
            </Card>
          </Reveal>
          <Reveal delay={1}>
            <Card className="h-full p-8">
              <HeartHandshake aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
              <Copy copy={copy} k="volunteer.title" as="h2" className="mt-6 text-3xl text-fg" />
              <Copy copy={copy} k="volunteer.body" lines={3} className="mt-4 leading-relaxed text-fg-muted" />
              <ButtonLink to="/get-involved/volunteer" variant="link" className="mt-4">
                Volunteer with us
              </ButtonLink>
            </Card>
          </Reveal>
        </div>
      </Section>

      <Section aria-labelledby="values">
        <CopyHeading copy={copy} prefix="values" id="values" />
        <Values />
      </Section>

      <Section tone="sunken" aria-labelledby="people">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <CopyHeading copy={copy} prefix="people" id="people" />
          <ButtonLink to="/about/staff" variant="link">
            Meet our staff
            <ArrowRight aria-hidden="true" className="size-4" />
          </ButtonLink>
        </div>
        <StaffStrip />
      </Section>
    </>
  )
}
