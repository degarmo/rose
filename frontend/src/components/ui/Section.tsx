import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

type Tone = 'canvas' | 'surface'
type Width = 'narrow' | 'default' | 'full'

interface SectionProps extends HTMLAttributes<HTMLElement> {
  tone?: Tone
  width?: Width
  spacing?: 'default' | 'tight' | 'none'
  /** A 1px rule along the top, as between the home page's sections. */
  rule?: boolean
  innerClassName?: string
}

const widths: Record<Width, string> = {
  narrow: 'max-w-[860px]',
  default: 'max-w-[1440px]',
  full: 'max-w-none',
}

const spacings = {
  default: 'py-10 lg:py-16',
  tight: 'py-8 lg:py-12',
  none: '',
}

/** The page gutter: 20px on phones, 32px on tablets, 48px from 1280px (design: "48px page gutter"). */
export const GUTTER = 'px-5 sm:px-8 xl:px-12'

export function Section({ tone = 'canvas', width = 'default', spacing = 'default', rule = false, className, innerClassName, children, ...rest }: SectionProps) {
  return (
    <section className={cn(tone === 'surface' ? 'bg-surface' : 'bg-canvas', rule && 'border-t border-border', spacings[spacing], className)} {...rest}>
      <div className={cn('mx-auto', widths[width], width !== 'full' && GUTTER, width === 'narrow' && 'box-content', innerClassName)}>{children}</div>
    </section>
  )
}
