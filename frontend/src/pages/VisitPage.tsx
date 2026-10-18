import { Clock, IdCard, MapPin, MessageCircle, Sparkles, Users } from 'lucide-react'
import { FAQAccordion } from '@/components/content/FAQAccordion'
import { PageHero } from '@/components/content/PageHero'
import { Reveal } from '@/components/content/Reveal'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { useSiteSettings } from '@/components/layout/siteSettingsContext'
import { ButtonLink, Card, Section, SectionHeading } from '@/components/ui'
import { api } from '@/lib/api'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const STEPS = [
  {
    icon: MessageCircle,
    title: 'Say hello first',
    body: 'Send us a short note through the contact form. We will reply with the next orientation date and the street address.',
  },
  {
    icon: Users,
    title: 'Arrive for orientation',
    body: 'A host meets you at the door, checks your ID and walks you through our community agreements in a relaxed, seated conversation.',
  },
  {
    icon: Sparkles,
    title: 'Stay as long as you like',
    body: 'Join the class that follows, have a drink at the bar, or head home. There is no pressure to do anything more than look around.',
  },
]

function Hours() {
  const settings = useSiteSettings()
  if (settings.status === 'loading') return <LoadingState label="Loading hours" className="py-2" />
  if (settings.status === 'error') return <ErrorState title="Hours did not load" onRetry={settings.retry} />
  return (
    <p className="whitespace-pre-line leading-relaxed text-fg-muted">
      {settings.data.hours_text || 'Hours are announced each season.'}
    </p>
  )
}

function Directions() {
  const settings = useSiteSettings()
  if (settings.status === 'loading') return <LoadingState label="Loading location" className="py-2" />
  if (settings.status === 'error') return <ErrorState title="Location did not load" onRetry={settings.retry} />
  return (
    <div className="space-y-3 leading-relaxed text-fg-muted">
      {settings.data.address_text && <p className="whitespace-pre-line text-fg">{settings.data.address_text}</p>}
      {settings.data.directions_text && <p className="whitespace-pre-line">{settings.data.directions_text}</p>}
      {!settings.data.address_text && !settings.data.directions_text && (
        <p>Directions are shared with confirmed visitors.</p>
      )}
    </div>
  )
}

function FAQs() {
  const state = useAsync(() => api.faqs(), 'faqs')
  if (state.status === 'loading') return <LoadingState label="Loading questions" />
  if (state.status === 'error') return <ErrorState title="Questions did not load" onRetry={state.retry} />
  if (state.data.length === 0) {
    return <EmptyState title="No questions yet" message="Send us yours and we will answer it." />
  }
  return <FAQAccordion items={state.data} />
}

export function VisitPage() {
  useDocumentMeta({
    title: 'Plan Your Visit',
    description: 'What to expect on your first visit, what to bring, hours and how to find us.',
  })

  return (
    <>
      <PageHero
        eyebrow="Plan your visit"
        title="Your first evening, without surprises."
        lede="Here is everything that happens between your first message and the moment you feel at home."
        image="visit-hero.webp"
        placeholder="shadow"
      />

      <Section aria-labelledby="expect">
        <SectionHeading id="expect" eyebrow="What to expect" title="Three easy steps." />
        <ol className="mt-14 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, index) => {
            const Icon = step.icon
            return (
              <Reveal as="li" key={step.title} delay={index as 0 | 1 | 2}>
                <Card className="h-full p-8">
                  <div className="flex items-center justify-between">
                    <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
                    <span aria-hidden="true" className="font-display text-5xl text-ink-600">
                      {index + 1}
                    </span>
                  </div>
                  <h3 className="mt-6 text-2xl text-fg">{step.title}</h3>
                  <p className="mt-3 leading-relaxed text-fg-muted">{step.body}</p>
                </Card>
              </Reveal>
            )
          })}
        </ol>
      </Section>

      <Section tone="surface" spacing="tight" aria-labelledby="id-required">
        <Reveal>
          <div className="flex flex-col gap-6 rounded-2xl border border-highlight/40 bg-primary-deep/40 p-8 sm:flex-row sm:items-start sm:p-10">
            <IdCard aria-hidden="true" className="size-10 shrink-0 text-highlight" strokeWidth={1.25} />
            <div>
              <h2 id="id-required" className="text-3xl text-fg">
                Bring a valid photo ID
              </h2>
              <p className="mt-4 max-w-2xl leading-relaxed text-fg-muted">
                Everyone must be 18 or older, every time, with no exceptions. Please bring a current, government-issued
                photo ID such as a driver&rsquo;s license, state ID or passport. We check it at the door and hand it
                straight back. We never photograph, scan or copy it.
              </p>
            </div>
          </div>
        </Reveal>
      </Section>

      <Section aria-label="Hours and directions">
        <div className="grid gap-12 md:grid-cols-2">
          <Reveal>
            <h2 className="flex items-center gap-3 text-3xl text-fg">
              <Clock aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
              Hours
            </h2>
            <div className="mt-6">
              <Hours />
            </div>
          </Reveal>
          <Reveal delay={1}>
            <h2 className="flex items-center gap-3 text-3xl text-fg">
              <MapPin aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
              Getting here
            </h2>
            <div className="mt-6">
              <Directions />
            </div>
          </Reveal>
        </div>
      </Section>

      <Section tone="sunken" width="narrow" aria-labelledby="faq">
        <SectionHeading id="faq" eyebrow="Questions" title="Things people often ask" />
        <div className="mt-10">
          <FAQs />
        </div>
        <div className="mt-12 flex flex-col gap-3 sm:flex-row">
          <ButtonLink to="/contact" size="lg">
            Send us a note
          </ButtonLink>
          <ButtonLink to="/education" size="lg" variant="ghost">
            See upcoming classes
          </ButtonLink>
        </div>
      </Section>
    </>
  )
}
