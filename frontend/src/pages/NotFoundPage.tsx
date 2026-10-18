import { ButtonLink, ImageFrame } from '@/components/ui'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

export function NotFoundPage() {
  useDocumentMeta({ title: 'Not found', noindex: true })

  return (
    <section className="relative isolate flex min-h-svh items-center overflow-hidden px-5 pb-20 pt-32 sm:px-8">
      <ImageFrame alt="" fill placeholder="rose" reveal={false} className="-z-20 opacity-60" />
      <div aria-hidden="true" className="absolute inset-0 -z-10 bg-gradient-to-r from-canvas via-canvas/85 to-canvas/30" />
      <div className="mx-auto w-full max-w-6xl">
        <p className="font-display text-8xl text-highlight/80 sm:text-9xl">404</p>
        <h1 className="mt-6 max-w-xl text-5xl leading-tight text-fg sm:text-6xl">This room is not on the map.</h1>
        <p className="mt-6 max-w-md text-lg leading-relaxed text-fg-muted">
          The page you were looking for has moved, or perhaps it was never here. Let us show you back to the parlor.
        </p>
        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <ButtonLink to="/" size="lg">
            Return home
          </ButtonLink>
          <ButtonLink to="/contact" size="lg" variant="ghost">
            Ask a host
          </ButtonLink>
        </div>
      </div>
    </section>
  )
}
