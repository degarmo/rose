import { cn } from '@/lib/cn'

/** Lucide at 24px with a 1.8 stroke; active items 2.4, active phone tabs 2.6 (design: Icons). */
export const ICON = { size: 24, stroke: 1.8, activeStroke: 2.4, tabStroke: 2.6 } as const

/** App buttons (design system: "Member app · 32px, 8px radius"). */
export type Variant = 'primary' | 'secondary' | 'outline' | 'plain'

export const variants: Record<Variant, string> = {
  primary: 'bg-primary px-4 text-on-primary hover:bg-primary-hover disabled:bg-control disabled:text-fg-faint',
  secondary: 'bg-control px-4 text-fg hover:bg-border disabled:text-fg-faint',
  outline: 'border border-fg px-4 text-fg hover:bg-surface disabled:border-control disabled:text-fg-faint',
  plain: 'px-2 text-link hover:text-primary-hover disabled:text-fg-faint',
}

export function appButtonClasses(variant: Variant = 'primary', className?: string) {
  return cn(
    'inline-flex h-8 items-center justify-center gap-1.5 whitespace-nowrap rounded-app text-sm font-semibold transition-colors duration-150 ease-out disabled:cursor-not-allowed',
    variants[variant],
    className,
  )
}
