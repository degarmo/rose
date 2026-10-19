import { cn } from '@/lib/cn'

/** Lucide at 24px with a 1.75 stroke; active items get a heavier stroke. */
export const ICON = { size: 24, stroke: 1.75, activeStroke: 2.5 } as const

export type Variant = 'primary' | 'secondary' | 'plain'

export const variants: Record<Variant, string> = {
  primary: 'bg-primary px-4 text-on-primary hover:bg-primary-hover',
  secondary: 'bg-hover px-4 text-fg hover:bg-border',
  plain: 'px-2 text-accent hover:text-fg',
}

export function igButtonClasses(variant: Variant = 'primary', className?: string) {
  return cn(
    'inline-flex h-8 items-center justify-center gap-1.5 rounded-lg text-sm font-semibold transition-colors duration-150 ease-out',
    variants[variant],
    className,
  )
}
