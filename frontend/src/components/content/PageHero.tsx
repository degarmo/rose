import type { ReactNode } from 'react'
import { ImageFrame, type PlaceholderTexture } from '../ui'

interface PageHeroProps {
  eyebrow: string
  title: ReactNode
  lede?: ReactNode
  image?: string
  placeholder: PlaceholderTexture
  children?: ReactNode
}

/** Full-bleed editorial header used at the top of each inner page. */
export function PageHero({ eyebrow, title, lede, image, placeholder, children }: PageHeroProps) {
  return (
    <div className="relative isolate flex min-h-[70svh] items-end overflow-hidden pb-16 pt-32 sm:min-h-[60vh] sm:pb-20">
      <ImageFrame image={image} alt="" fill placeholder={placeholder} priority reveal={false} className="-z-20" />
      <div aria-hidden="true" className="absolute inset-0 -z-10 bg-gradient-to-t from-canvas via-canvas/70 to-canvas/10" />
      <div className="mx-auto w-full max-w-6xl px-5 sm:px-8">
        <p className="mb-5 flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.28em] text-highlight">
          <span aria-hidden="true" className="h-px w-8 bg-highlight/70" />
          {eyebrow}
        </p>
        <h1 className="max-w-3xl text-5xl leading-[1.05] text-fg sm:text-6xl lg:text-7xl">{title}</h1>
        {lede && <div className="mt-6 max-w-2xl text-lg leading-relaxed text-fg-muted sm:text-xl">{lede}</div>}
        {children}
      </div>
    </div>
  )
}
