import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

type Tone = 'canvas' | 'surface' | 'sunken'
type Width = 'narrow' | 'default' | 'wide' | 'full'

interface SectionProps extends HTMLAttributes<HTMLElement> {
  tone?: Tone
  width?: Width
  spacing?: 'default' | 'tight' | 'none'
  innerClassName?: string
}

const tones: Record<Tone, string> = {
  canvas: 'bg-canvas',
  surface: 'bg-surface',
  sunken: 'bg-surface-sunken',
}

const widths: Record<Width, string> = {
  narrow: 'max-w-3xl',
  default: 'max-w-6xl',
  wide: 'max-w-7xl',
  full: 'max-w-none',
}

const spacings = {
  default: 'py-20 sm:py-28',
  tight: 'py-12 sm:py-16',
  none: '',
}

export function Section({
  tone = 'canvas',
  width = 'default',
  spacing = 'default',
  className,
  innerClassName,
  children,
  ...rest
}: SectionProps) {
  return (
    <section className={cn(tones[tone], spacings[spacing], className)} {...rest}>
      <div className={cn('mx-auto px-5 sm:px-8', widths[width], width === 'full' && 'px-0 sm:px-0', innerClassName)}>
        {children}
      </div>
    </section>
  )
}
