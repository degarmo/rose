import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'
import { useReveal } from '@/lib/useReveal'

interface RevealProps {
  children: ReactNode
  className?: string
  delay?: 0 | 1 | 2 | 3
  as?: 'div' | 'li'
}

const delays = ['', 'delay-150', 'delay-300', 'delay-500']

export function Reveal({ children, className, delay = 0, as: Tag = 'div' }: RevealProps) {
  const ref = useReveal<HTMLDivElement & HTMLLIElement>()
  return (
    <Tag ref={ref} className={cn('reveal', delays[delay], className)}>
      {children}
    </Tag>
  )
}
