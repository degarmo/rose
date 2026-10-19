import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { Reveal } from '@/components/content/Reveal'
import { ButtonLink, Section } from '@/components/ui'
import { usePageContent } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

export function HouseRulesPage() {
  useDocumentMeta({
    title: 'House Rules',
    description: 'The agreements everyone keeps at the house, so every evening is safe and comfortable.',
  })
  const copy = usePageContent('rules')
  const sections = copy.status === 'loading' ? [1, 2, 3] : copy.items('rules')
  return (
    <>
      <PageHero copy={copy} image="visit-hero.webp" placeholder="leather" />
      <Section width="narrow" aria-label="House rules">
        <Copy copy={copy} k="intro" lines={3} className="text-lg" />
        <div className="mt-14 space-y-14">
          {sections.map((n) => (
            <section key={n} className="border-t border-border pt-10" aria-labelledby={`rule-${n}`}>
              <Reveal>
                <Copy copy={copy} k={`rules.${n}.title`} as="h2" id={`rule-${n}`} className="text-3xl text-fg" />
                <Copy copy={copy} k={`rules.${n}.body`} lines={4} className="mt-6" />
              </Reveal>
            </section>
          ))}
        </div>
      </Section>
      <Section tone="sunken" width="narrow" aria-labelledby="rules-help">
        <CopyHeading copy={copy} prefix="help" id="rules-help" />
        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <ButtonLink to="/contact" size="lg">
            Contact us
          </ButtonLink>
          <ButtonLink to="/faq" size="lg" variant="ghost">
            Read the FAQ
          </ButtonLink>
        </div>
      </Section>
    </>
  )
}
