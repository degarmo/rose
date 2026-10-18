import { useEffect, useRef } from 'react'
import { AGE_GATE_HOURS } from '@/lib/ageGate'
import { Button } from '../ui'
import { QuickExit } from './QuickExit'

interface AgeGateProps {
  onConfirm: () => void
  onDecline: () => void
}

/** Rendered instead of the whole site until the visitor confirms they are 18 or older. */
export function AgeGate({ onConfirm, onDecline }: AgeGateProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    document.title = 'Rose'
    headingRef.current?.focus()
  }, [])

  return (
    <main className="texture-velvet grain relative flex min-h-dvh items-center justify-center px-6 py-16">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="age-gate-title"
        aria-describedby="age-gate-copy"
        className="relative z-10 w-full max-w-md text-center"
      >
        <p className="text-xs font-semibold uppercase tracking-[0.4em] text-highlight">Rose</p>
        <div aria-hidden="true" className="mx-auto mt-6 h-px w-16 bg-highlight/60" />
        <h1
          id="age-gate-title"
          ref={headingRef}
          tabIndex={-1}
          className="mt-8 text-4xl leading-tight text-fg focus:outline-none sm:text-5xl"
        >
          For adults only
        </h1>
        <p id="age-gate-copy" className="mt-6 text-base leading-relaxed text-fg-muted">
          This site is intended for people aged 18 and over. Please confirm your age to continue.
        </p>
        <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Button size="lg" onClick={onConfirm}>
            I am 18 or older
          </Button>
          <Button size="lg" variant="ghost" onClick={onDecline}>
            I am under 18
          </Button>
        </div>
        <p className="mt-8 text-xs text-fg-subtle">
          We remember your answer on this device for {AGE_GATE_HOURS} hours using a single cookie.
        </p>
      </div>
      <QuickExit />
    </main>
  )
}
