import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { Reveal } from '@/components/content/Reveal'
import { StaffCard } from '@/components/content/StaffCard'
import { EmptyState, ErrorState, SkeletonCards } from '@/components/content/States'
import { ButtonLink, Card, Section } from '@/components/ui'
import { api } from '@/lib/api'
import { usePageContent } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

function Team() {
  const state = useAsync(() => api.staff(), 'staff')
  if (state.status === 'loading') return <SkeletonCards count={6} />
  if (state.status === 'error') return <ErrorState title="Our staff did not load" onRetry={state.retry} />
  if (state.data.length === 0) {
    return <EmptyState title="Introductions are on the way" message="Ask for any of our hosts at the door." />
  }
  return (
    <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {state.data.map((person, index) => (
        <Reveal as="li" key={person.slug} delay={(index % 3) as 0 | 1 | 2}>
          <StaffCard person={person} />
        </Reveal>
      ))}
    </ul>
  )
}

export function StaffPage() {
  useDocumentMeta({
    title: 'Our Staff',
    description: 'The volunteers who host, teach and keep the house running, by the names they choose.',
  })
  const copy = usePageContent('staff')
  const roles = copy.status === 'loading' ? [1, 2, 3] : copy.items('roles')

  return (
    <>
      <PageHero copy={copy} image="about-hero.webp" placeholder="architecture" />

      <Section aria-labelledby="team">
        <CopyHeading copy={copy} prefix="team" id="team" />
        <div className="mt-12">
          <Team />
        </div>
      </Section>

      {roles.length > 0 && (
        <Section tone="surface" aria-labelledby="roles">
          <CopyHeading copy={copy} prefix="roles" id="roles" />
          <ul className="mt-12 grid gap-6 md:grid-cols-2">
            {roles.map((n, index) => (
              <Reveal as="li" key={n} delay={(index % 2) as 0 | 1}>
                <Card className="h-full p-8">
                  <Copy copy={copy} k={`roles.${n}.title`} as="h3" className="text-2xl text-fg" />
                  <Copy copy={copy} k={`roles.${n}.body`} lines={3} className="mt-3 leading-relaxed text-fg-muted" />
                </Card>
              </Reveal>
            ))}
          </ul>
        </Section>
      )}

      <Section tone="sunken" width="narrow" aria-labelledby="join-team">
        <CopyHeading copy={copy} prefix="cta" id="join-team" />
        <ButtonLink to="/get-involved/volunteer" size="lg" className="mt-8">
          Volunteer with us
        </ButtonLink>
      </Section>
    </>
  )
}
