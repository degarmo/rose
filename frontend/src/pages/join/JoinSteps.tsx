import { Check } from 'lucide-react'
import { useState } from 'react'
import { createPortal } from 'react-dom'
import { JOIN_STEPS_SLOT } from '@/components/layout/Header'
import { cn } from '@/lib/cn'
import { priceLabel, type Tier } from '@/lib/membershipApi'

export type JoinStepNumber = 1 | 2 | 3

const LABELS = ['Tier', 'Agreement', 'Confirmation'] as const

/**
 * The join flow's three steps (design: the Join header's "Tier · Agreement ·
 * Confirmation", 24px numbered circles), shown in the middle of the join header on
 * desktop. Phones show `JoinProgress` inside the step instead.
 */
export function JoinSteps({ current }: { current: JoinStepNumber }) {
  // The header is in the page before the join page (a separate chunk) renders.
  const [slot] = useState(() => document.getElementById(JOIN_STEPS_SLOT))
  if (!slot) return null
  return createPortal(
    <nav aria-label="Joining steps">
      <ol className="flex items-center gap-8 text-[0.8125rem] font-semibold">
        {LABELS.map((label, index) => {
          const n = index + 1
          const done = n < current
          const active = n === current
          return (
            <li key={label} aria-current={active ? 'step' : undefined} className={cn('flex items-center gap-2', active ? 'text-fg' : 'text-fg-muted')}>
              <span
                aria-hidden="true"
                className={cn(
                  'flex size-6 items-center justify-center rounded-full border text-xs',
                  active && 'border-primary bg-primary text-on-primary',
                  done && 'border-fg bg-fg text-canvas',
                  !active && !done && 'border-border bg-canvas text-fg-muted',
                )}
              >
                {done ? <Check className="size-3" strokeWidth={3.5} /> : n}
              </span>
              {label}
              {done && <span className="sr-only">(done)</span>}
            </li>
          )
        })}
      </ol>
    </nav>,
    slot,
  )
}

/** Phones: three 3px bars and "Step 1 of 3 · Choose a tier" (design: "Join step 1 · phone"). */
export function JoinProgress({ current, caption, className }: { current: JoinStepNumber; caption?: string; className?: string }) {
  return (
    <div className={cn('flex flex-col gap-3 lg:hidden', className)}>
      <div aria-hidden="true" className="flex gap-1.5">
        {LABELS.map((label, index) => (
          <span key={label} className={cn('h-[3px] flex-1 rounded-sm', index < current ? 'bg-primary' : 'bg-border')} />
        ))}
      </div>
      {caption && (
        <p className="text-xs font-semibold text-fg-muted">
          Step {current} of 3 &middot; {caption}
        </p>
      )}
    </div>
  )
}

/** "Annual · $250 a year": the chosen tier, shown beside the agreement and payment. */
export function TierSummary({ tier }: { tier: Tier }) {
  return (
    <p className="rounded-card bg-surface p-5 text-sm text-fg-muted">
      {tier.name} &middot; {priceLabel(tier)}
    </p>
  )
}
