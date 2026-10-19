import { Clock, IdCard, MapPin, MessageCircle, ScrollText, Sparkles, Users } from 'lucide-react'
import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { Reveal } from '@/components/content/Reveal'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useSiteSettings } from '@/components/layout/siteSettingsContext'
import { ButtonLink, Card, Section } from '@/components/ui'
import { usePageContent } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

// Icons for the "what to expect" steps, in order. Their words are editable copy.
const STEP_ICONS = [MessageCircle, Users, Sparkles]

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

export function VisitPage() {
  useDocumentMeta({
    title: 'Plan Your Visit',
    description: 'What to expect on your first visit, what to bring, hours and how to find us.',
  })
  const copy = usePageContent('visit')
  const steps = copy.status === 'loading' ? [1, 2, 3] : copy.items('steps')

  return (
    <>
      <PageHero copy={copy} image="visit-hero.webp" placeholder="shadow" />

      <Section aria-labelledby="expect" className="scroll-mt-24">
        <CopyHeading copy={copy} prefix="expect" id="expect" />
        <ol className="mt-14 grid gap-6 md:grid-cols-3">
          {steps.map((n, index) => {
            const Icon = STEP_ICONS[index % STEP_ICONS.length]
            return (
              <Reveal as="li" key={n} delay={(index % 3) as 0 | 1 | 2}>
                <Card className="h-full p-8">
                  <div className="flex items-center justify-between">
                    <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
                    <span aria-hidden="true" className="font-display text-5xl text-ink-600">
                      {index + 1}
                    </span>
                  </div>
                  <Copy copy={copy} k={`steps.${n}.title`} as="h3" className="mt-6 text-2xl text-fg" />
                  <Copy copy={copy} k={`steps.${n}.body`} lines={3} className="mt-3 leading-relaxed text-fg-muted" />
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
              <Copy copy={copy} k="id.title" as="h2" id="id-required" className="text-3xl text-fg" />
              <Copy copy={copy} k="id.body" lines={3} className="mt-4 max-w-2xl leading-relaxed text-fg-muted" />
            </div>
          </div>
        </Reveal>
      </Section>

      <Section aria-label="Hours and directions" id="directions" className="scroll-mt-24">
        <div className="grid gap-12 md:grid-cols-2">
          <Reveal>
            <h2 className="flex items-center gap-3 text-3xl text-fg">
              <Clock aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
              <Copy copy={copy} k="hours.title" as="span" />
            </h2>
            <div className="mt-6">
              <Hours />
            </div>
          </Reveal>
          <Reveal delay={1}>
            <h2 className="flex items-center gap-3 text-3xl text-fg">
              <MapPin aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
              <Copy copy={copy} k="directions.title" as="span" />
            </h2>
            <div className="mt-6">
              <Directions />
            </div>
          </Reveal>
        </div>
      </Section>

      <Section tone="surface" aria-labelledby="rules">
        <div className="flex flex-col gap-8 md:flex-row md:items-end md:justify-between">
          <div className="flex gap-5">
            <ScrollText aria-hidden="true" className="mt-2 size-8 shrink-0 text-highlight" strokeWidth={1.25} />
            <CopyHeading copy={copy} prefix="rules" id="rules" />
          </div>
          <ButtonLink to="/house-rules" size="lg" variant="ghost">
            Read the house rules
          </ButtonLink>
        </div>
      </Section>

      <Section tone="sunken" width="narrow" aria-labelledby="faq">
        <CopyHeading copy={copy} prefix="faq" id="faq" />
        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <ButtonLink to="/faq" size="lg">
            Read the FAQ
          </ButtonLink>
          <ButtonLink to="/guests" size="lg" variant="ghost">
            Coming as a guest
          </ButtonLink>
          <ButtonLink to="/contact" size="lg" variant="ghost">
            Send us a note
          </ButtonLink>
        </div>
      </Section>
    </>
  )
}
