import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

/** Status badges (design system: "Badges"): 12px/600 filled pills. */
export type BadgeTone = 'open' | 'wait' | 'full' | 'members' | 'going'

const tones: Record<BadgeTone, string> = {
  open: 'bg-tint text-tint-fg',
  wait: 'bg-wait text-wait-fg',
  full: 'bg-control text-full-fg',
  members: 'bg-fg text-canvas',
  going: 'bg-primary text-on-primary',
}

export function Badge({ tone, children, className }: { tone: BadgeTone; children: ReactNode; className?: string }) {
  return (
    <span className={cn('inline-flex items-center whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold', tones[tone], className)}>
      {children}
    </span>
  )
}

/**
 * Category and level chips: 11px caps with .06em tracking. `outline` sits on the page
 * (muted text, 1px border); `solid` sits on a picture (page background, no border).
 */
export function Chip({ variant = 'outline', children, className }: { variant?: 'outline' | 'solid'; children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center whitespace-nowrap rounded-full text-label font-semibold uppercase leading-[1.5]',
        variant === 'outline' ? 'border border-border px-2.5 py-[3px] text-fg-muted' : 'bg-canvas px-2.5 py-1 text-fg',
        className,
      )}
    >
      {children}
    </span>
  )
}
