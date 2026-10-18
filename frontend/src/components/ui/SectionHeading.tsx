import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface SectionHeadingProps {
  eyebrow?: string
  title: ReactNode
  lede?: ReactNode
  as?: 'h1' | 'h2' | 'h3'
  align?: 'start' | 'center'
  id?: string
  className?: string
}

export function SectionHeading({
  eyebrow,
  title,
  lede,
  as: Heading = 'h2',
  align = 'start',
  id,
  className,
}: SectionHeadingProps) {
  return (
    <header className={cn('max-w-2xl', align === 'center' && 'mx-auto text-center', className)}>
      {eyebrow && (
        <p className="mb-4 flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.28em] text-highlight">
          <span aria-hidden="true" className={cn('h-px w-8 bg-highlight/70', align === 'center' && 'hidden')} />
          {eyebrow}
        </p>
      )}
      <Heading
        id={id}
        className={cn(
          'text-fg',
          Heading === 'h1' ? 'text-5xl leading-[1.05] sm:text-6xl lg:text-7xl' : 'text-4xl leading-tight sm:text-5xl',
        )}
      >
        {title}
      </Heading>
      {lede && <div className="mt-6 text-lg leading-relaxed text-fg-muted">{lede}</div>}
    </header>
  )
}
