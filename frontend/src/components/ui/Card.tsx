import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface CardProps extends HTMLAttributes<HTMLElement> {
  interactive?: boolean
  as?: 'div' | 'article'
}

export function Card({ interactive = false, as: Tag = 'div', className, ...rest }: CardProps) {
  return (
    <Tag
      className={cn(
        'relative flex flex-col overflow-hidden rounded-2xl border border-border bg-surface',
        interactive &&
          'transition-[border-color,transform] duration-500 ease-velvet hover:-translate-y-0.5 hover:border-border-strong focus-within:border-border-strong',
        className,
      )}
      {...rest}
    />
  )
}
