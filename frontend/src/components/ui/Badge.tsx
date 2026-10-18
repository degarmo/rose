import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

type Tone = 'neutral' | 'rose' | 'brass'

const tones: Record<Tone, string> = {
  neutral: 'border-border-strong text-fg-muted',
  rose: 'border-rose/50 text-rose',
  brass: 'border-highlight/50 text-highlight',
}

export function Badge({ tone = 'neutral', children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.18em]',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}
