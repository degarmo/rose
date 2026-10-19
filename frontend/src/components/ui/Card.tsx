import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface CardProps extends HTMLAttributes<HTMLElement> {
  as?: 'div' | 'article' | 'section'
  /** `panel` is the larger 20px-cornered box (RSVP, forms); `card` is the 16px one. */
  shape?: 'card' | 'panel'
}

/** A white box with a 1px border (design system: "Cards"). Callers set the padding. */
export function Card({ as: Tag = 'div', shape = 'card', className, ...rest }: CardProps) {
  return (
    <Tag
      className={cn('relative flex flex-col overflow-hidden border border-border bg-canvas', shape === 'card' ? 'rounded-card' : 'rounded-panel', className)}
      {...rest}
    />
  )
}
