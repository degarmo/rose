import { ButtonLink, Section } from '@/components/ui'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** Not found (no design of its own: the blush card of "Contact · phone (success)"). */
export function NotFoundPage() {
  useDocumentMeta({ title: 'Not found', noindex: true })

  return (
    <Section spacing="none" className="pb-16 pt-7 lg:pb-24 lg:pt-16">
      <div className="mx-auto flex max-w-[560px] flex-col items-center gap-3 rounded-panel bg-blush px-6 py-8 text-center lg:px-10 lg:py-12">
        <p className="inline-flex size-14 items-center justify-center rounded-full border-[1.5px] border-primary bg-canvas text-[0.9375rem] font-semibold text-link">
          404
        </p>
        <h1 className="text-[1.625rem] leading-[1.15] text-fg lg:text-[2rem]">This room is not on the map.</h1>
        <p className="text-sm text-fg-muted-tint lg:text-body">
          The page you were looking for has moved, or perhaps it was never here. Let us show you back to the parlor.
        </p>
        <div className="mt-2 flex flex-wrap justify-center gap-3">
          <ButtonLink to="/" variant="outline">
            Return home
          </ButtonLink>
          <ButtonLink to="/contact" variant="secondary">
            Ask a host
          </ButtonLink>
        </div>
      </div>
    </Section>
  )
}
