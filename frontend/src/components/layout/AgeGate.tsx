import { useEffect, useRef } from 'react'
import { Logo } from '@/components/brand/Logo'
import { tabName } from '@/lib/useDocumentMeta'
import { Button } from '../ui'

interface AgeGateProps {
  onConfirm: () => void
  onDecline: () => void
}

/**
 * Rendered instead of the whole site until the visitor confirms they are 18 or older
 * (design "Age gate"): a white card on the blush backdrop. Leave goes straight to the
 * neutral exit page and replaces this one in the history.
 */
export function AgeGate({ onConfirm, onDecline }: AgeGateProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    document.title = tabName(window.location.pathname)
    headingRef.current?.focus()
  }, [])

  return (
    <main className="flex min-h-dvh items-center justify-center bg-blush p-6">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="age-gate-title"
        aria-describedby="age-gate-copy"
        className="flex w-full max-w-[520px] flex-col items-center gap-[18px] rounded-panel border border-border bg-canvas px-7 pb-8 pt-10 text-center sm:gap-5 sm:px-14 sm:pb-12 sm:pt-14"
      >
        <Logo height={120} priority />
        <h1
          id="age-gate-title"
          ref={headingRef}
          tabIndex={-1}
          className="text-[1.625rem] font-light leading-[1.15] text-fg focus:outline-none sm:text-[1.875rem]"
        >
          A private members' club <br className="hidden sm:inline" />
          for adults in Chicago.
        </h1>
        <p id="age-gate-copy" className="max-w-[380px] text-sm leading-[1.6] text-fg-muted sm:text-[0.9375rem]">
          Everything beyond this page is for people 18 or older. If that's not you, no hard feelings.
        </p>
        <div className="flex w-full flex-col gap-2.5 pt-2 sm:w-auto sm:flex-row sm:gap-3">
          <Button size="lg" onClick={onConfirm}>
            I'm 18 or older
          </Button>
          <Button size="lg" variant="secondary" onClick={onDecline}>
            Leave
          </Button>
        </div>
        <p className="hidden text-xs text-fg-muted sm:block">Leave takes you to a neutral page immediately.</p>
      </div>
    </main>
  )
}
