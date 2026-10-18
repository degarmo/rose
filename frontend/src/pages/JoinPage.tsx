import { CalendarHeart, GraduationCap, KeyRound, Lock } from 'lucide-react'
import { PageHero } from '@/components/content/PageHero'
import { Reveal } from '@/components/content/Reveal'
import { Button, ButtonLink, Card, Section, SectionHeading } from '@/components/ui'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const BENEFITS = [
  {
    icon: CalendarHeart,
    title: 'Weekend socials',
    body: 'Friday and Saturday evenings at the house, with volunteer hosts on the floor all night.',
  },
  {
    icon: GraduationCap,
    title: 'Member pricing on education',
    body: 'Reduced rates on workshops and first access to classes with limited space.',
  },
  {
    icon: KeyRound,
    title: 'Members-only events',
    body: 'Seasonal gatherings, community meetings and a say in how the house is run.',
  },
  {
    icon: Lock,
    title: 'Private by design',
    body: 'You are known by a display name you choose. Social features are off until you turn them on.',
  },
]

export function JoinPage() {
  useDocumentMeta({
    title: 'Join',
    description: 'What membership includes and how to become a member.',
  })

  return (
    <>
      <PageHero
        eyebrow="Membership"
        title="Become part of the house."
        lede="Membership supports a volunteer-run nonprofit and opens the door to weekend socials, members' events and the full education program."
        image="join-hero.webp"
        placeholder="rose"
      />

      <Section aria-labelledby="benefits">
        <SectionHeading
          id="benefits"
          eyebrow="What membership includes"
          title="Everything you love about Thursdays, all week long."
        />
        <ul className="mt-14 grid gap-6 sm:grid-cols-2">
          {BENEFITS.map((benefit, index) => {
            const Icon = benefit.icon
            return (
              <Reveal as="li" key={benefit.title} delay={(index % 2) as 0 | 1}>
                <Card className="h-full p-8">
                  <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
                  <h3 className="mt-6 text-2xl text-fg">{benefit.title}</h3>
                  <p className="mt-3 leading-relaxed text-fg-muted">{benefit.body}</p>
                </Card>
              </Reveal>
            )
          })}
        </ul>
      </Section>

      <Section tone="surface" width="narrow" aria-labelledby="how">
        <Reveal className="text-center">
          <h2 id="how" className="text-4xl text-fg sm:text-5xl">
            Online membership is almost here.
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-fg-muted">
            We are preparing a simple, private way to join and renew online. Until then, start with a newcomer
            orientation on any Thursday and our hosts will walk you through membership in person.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button size="lg" disabled aria-disabled="true">
              Membership opens soon
            </Button>
            <ButtonLink to="/visit" size="lg" variant="ghost">
              Plan a Visit
            </ButtonLink>
          </div>
        </Reveal>
      </Section>
    </>
  )
}
