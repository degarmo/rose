import { HeartHandshake, Landmark } from 'lucide-react'
import { PageHero } from '@/components/content/PageHero'
import { Reveal } from '@/components/content/Reveal'
import { ButtonLink, Card, Section, SectionHeading } from '@/components/ui'
import { VALUES } from '@/content/values'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

// Display names only. Real names never appear on the site.
const STAFF = [
  { name: 'Marlowe', role: 'Board chair' },
  { name: 'Sable', role: 'Education lead' },
  { name: 'Juniper', role: 'Volunteer coordinator' },
  { name: 'Ash', role: 'Safety team lead' },
  { name: 'Wren', role: 'Hosting lead' },
  { name: 'Calloway', role: 'Treasurer' },
]

export function AboutPage() {
  useDocumentMeta({
    title: 'About',
    description: 'Our mission, our values and the volunteers who keep the house running.',
  })

  return (
    <>
      <PageHero
        eyebrow="About"
        title="Built by volunteers. Kept by its members."
        lede="We exist so that adults can learn, connect and explore in a space that treats consent, privacy and kindness as non-negotiable."
        image="about-hero.webp"
        placeholder="architecture"
      />

      <Section width="narrow" aria-labelledby="mission">
        <Reveal>
          <SectionHeading id="mission" eyebrow="Our mission" title="Education first, community always." />
          <div className="mt-8 space-y-5 text-lg leading-relaxed text-fg-muted">
            <p>
              Our mission is to provide a welcoming, well-run space where adults can learn about communication, consent
              and the practices that interest them, guided by people with real experience and good judgment.
            </p>
            <p>
              We believe people make better choices when they have accurate information, a supportive community and
              room to ask any question without embarrassment. Everything we do, from Thursday classes to how we train
              our door team, follows from that.
            </p>
          </div>
        </Reveal>
      </Section>

      <Section tone="surface" spacing="tight">
        <div className="grid gap-6 md:grid-cols-2">
          <Reveal>
            <Card className="h-full p-8">
              <Landmark aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
              <h2 className="mt-6 text-3xl text-fg">A registered nonprofit</h2>
              <p className="mt-4 leading-relaxed text-fg-muted">
                We are a 501(c)(3) charitable organization. Membership dues and donations cover rent, insurance, safety
                equipment and the education program. Nobody profits from the house.
              </p>
            </Card>
          </Reveal>
          <Reveal delay={1}>
            <Card className="h-full p-8">
              <HeartHandshake aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
              <h2 className="mt-6 text-3xl text-fg">Entirely volunteer-run</h2>
              <p className="mt-4 leading-relaxed text-fg-muted">
                Every host, teacher, mentor and board member gives their time freely. If you would like to help, there is
                a place for you, whether that is one shift a month or leading a class.
              </p>
              <ButtonLink to="/education?category=volunteer" variant="link" className="mt-4">
                Volunteer opportunities
              </ButtonLink>
            </Card>
          </Reveal>
        </div>
      </Section>

      <Section aria-labelledby="values">
        <SectionHeading id="values" eyebrow="What we stand for" title="Four promises we keep." />
        <ul className="mt-14 grid gap-x-12 gap-y-14 md:grid-cols-2">
          {VALUES.map((value, index) => {
            const Icon = value.icon
            return (
              <Reveal as="li" key={value.title} delay={(index % 2) as 0 | 1} className="border-t border-border pt-8">
                <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
                <h3 className="mt-5 text-3xl text-fg">{value.title}</h3>
                <p className="mt-4 leading-relaxed text-fg-muted">{value.long}</p>
              </Reveal>
            )
          })}
        </ul>
      </Section>

      <Section tone="sunken" aria-labelledby="people">
        <SectionHeading
          id="people"
          eyebrow="The people"
          title="Who you will meet"
          lede="Our volunteers are known here by the names they choose. Ask for any of them at the door."
        />
        <ul className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-3">
          {STAFF.map((person, index) => (
            <Reveal as="li" key={person.name} delay={(index % 3) as 0 | 1 | 2}>
              <Card className="items-start p-6">
                <span
                  aria-hidden="true"
                  className="inline-flex size-14 items-center justify-center rounded-full border border-highlight/50 bg-primary-deep font-display text-2xl text-fg"
                >
                  {person.name[0]}
                </span>
                <p className="mt-5 font-display text-2xl text-fg">{person.name}</p>
                <p className="mt-1 text-sm text-fg-muted">{person.role}</p>
              </Card>
            </Reveal>
          ))}
        </ul>
      </Section>
    </>
  )
}
