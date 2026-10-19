import { useState } from 'react'
import { ConcernForm } from '@/components/content/ConcernForm'
import { PageHero } from '@/components/content/PageHero'
import { ButtonLink, Section } from '@/components/ui'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** Report a concern (no design of its own; laid out like Contact). Open to anyone. */
export function ConcernPage() {
  useDocumentMeta({ title: 'Report a concern', description: 'Tell our team about something that happened at an event or the club, in confidence.' })
  const [sent, setSent] = useState(false)
  return (
    <>
      <PageHero
        title="Report a concern"
        lede="Something happened at an event or the club that you want our team to know about. You do not need an account, and the person you mention is never told who wrote."
      />
      <Section spacing="none" className="pb-16 lg:pb-24">
        <div className="max-w-[640px]">
          {sent ? (
            <div role="status" className="flex flex-col items-start gap-3 rounded-panel bg-blush p-6 lg:p-8">
              <h2 className="text-2xl text-fg">Thank you. Our team has it.</h2>
              <p className="text-fg-muted-tint">Someone will look at it soon. If you left an email, we will write when it has been reviewed.</p>
              <ButtonLink to="/" variant="outline">
                Back to home
              </ButtonLink>
            </div>
          ) : (
            <ConcernForm onSent={() => setSent(true)} submitClass="self-start" />
          )}
        </div>
      </Section>
    </>
  )
}
