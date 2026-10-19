import { IdCard, ScrollText, Ticket } from 'lucide-react'
import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { Reveal } from '@/components/content/Reveal'
import { ErrorState, LoadingState } from '@/components/content/States'
import { ButtonLink, Card, Section } from '@/components/ui'
import { membershipApi, priceLabel } from '@/lib/membershipApi'
import { usePageContent } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

function GuestPass() {
  const tiers = useAsync(() => membershipApi.tiers(), 'tiers')
  if (tiers.status === 'loading') return <LoadingState label="Loading the guest pass" />
  if (tiers.status === 'error') return <ErrorState title="The guest pass did not load" onRetry={tiers.retry} />
  const pass = tiers.data.find((tier) => tier.is_guest_pass)
  if (!pass) {
    return (
      <p className="text-fg-muted">
        Guest passes are not offered online right now. Come to an open evening and our hosts will help you at the door.
      </p>
    )
  }
  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="font-display text-4xl text-accent">{priceLabel(pass)}</p>
        <p className="mt-1 text-sm text-fg-muted">
          {pass.name}. Paid at the door{pass.is_placeholder ? ' (placeholder price)' : ''}.
        </p>
      </div>
      <ButtonLink to={`/join?tier=${encodeURIComponent(pass.slug)}`} size="lg">
        Sign up as a guest
      </ButtonLink>
    </div>
  )
}

export function GuestsPage() {
  useDocumentMeta({
    title: 'Guests',
    description: 'Visiting as a guest: what to expect, the house rules, what to bring and the guest pass.',
  })
  const copy = usePageContent('guests')

  return (
    <>
      <PageHero copy={copy} image="visit-hero.webp" placeholder="rose" />

      <Section width="narrow" aria-labelledby="who">
        <CopyHeading copy={copy} prefix="who" id="who" />
      </Section>

      <Section tone="surface" aria-label="Before you come">
        <div className="grid gap-6 md:grid-cols-3">
          {[
            { icon: Ticket, prefix: 'expect' },
            { icon: ScrollText, prefix: 'rules' },
            { icon: IdCard, prefix: 'id' },
          ].map(({ icon: Icon, prefix }, index) => (
            <Reveal key={prefix} delay={index as 0 | 1 | 2}>
              <Card className="h-full p-8">
                <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
                <Copy copy={copy} k={`${prefix}.title`} as="h2" className="mt-6 text-2xl text-fg" />
                <Copy copy={copy} k={`${prefix}.body`} lines={4} className="mt-3 leading-relaxed text-fg-muted" />
                {prefix === 'rules' && (
                  <ButtonLink to="/house-rules" variant="link" className="mt-4">
                    Read the house rules
                  </ButtonLink>
                )}
              </Card>
            </Reveal>
          ))}
        </div>
      </Section>

      <Section width="narrow" aria-labelledby="pass">
        <CopyHeading copy={copy} prefix="price" id="pass" />
        <Card className="mt-10 p-6 sm:p-8">
          <GuestPass />
        </Card>
        <Copy copy={copy} k="steps" lines={3} className="mt-8" />
      </Section>
    </>
  )
}
