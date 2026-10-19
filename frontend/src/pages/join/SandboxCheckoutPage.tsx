import { FlaskConical } from 'lucide-react'
import { useState } from 'react'
import { useParams } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { Badge, Button, Card, Section, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { formatMoney } from '@/lib/format'
import { goTo, membershipApi } from '@/lib/membershipApi'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '../NotFoundPage'

type Outcome = 'pay' | 'fail' | 'cancel'

/**
 * Development only. Stands in for a processor's hosted checkout: each button
 * makes the server send the signed webhooks a real processor would. The API
 * behind it does not exist with DEBUG off, so in production this is a 404.
 */
export default function SandboxCheckoutPage() {
  useDocumentMeta({ title: 'Sandbox checkout', noindex: true })
  const { token = '' } = useParams()
  const toast = useToast()
  const session = useAsync(() => membershipApi.sandboxSession(token), token)
  const [busy, setBusy] = useState<Outcome | null>(null)

  if (session.status === 'error' && session.error instanceof ApiError && session.error.isNotFound) return <NotFoundPage />

  async function choose(outcome: Outcome) {
    setBusy(outcome)
    try {
      goTo((await membershipApi.sandboxOutcome(token, outcome)).redirect_url)
    } catch (error) {
      toast.show({ tone: 'error', title: 'The sandbox did not respond', message: error instanceof Error ? error.message : undefined })
      setBusy(null)
    }
  }

  return (
    <Section className="pt-32" width="narrow">
      <Card as="article" className="p-6 sm:p-8">
        <Badge tone="rose" className="self-start">
          <FlaskConical aria-hidden="true" className="size-3.5" />
          Development sandbox
        </Badge>
        <h1 className="mt-5 text-4xl text-fg">Test checkout</h1>
        <p className="mt-3 text-fg-muted">No money moves. Choose what the payment processor should report back.</p>
        {session.status === 'loading' && <LoadingState label="Loading checkout" />}
        {session.status === 'error' && <ErrorState title="This checkout did not load" onRetry={session.retry} />}
        {session.status === 'success' && (
          <>
            <dl className="mt-6 grid gap-4 border-y border-border py-5 sm:grid-cols-3">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle">For</dt>
                <dd className="mt-1 font-display text-3xl text-fg">{session.data.description}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle">Amount</dt>
                <dd className="mt-1 font-display text-3xl text-fg">{formatMoney(session.data.amount_cents)}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle">Reference</dt>
                <dd className="mt-1 font-mono text-xl tracking-[0.18em] text-fg">{session.data.reference}</dd>
              </div>
            </dl>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button size="lg" onClick={() => void choose('pay')} disabled={busy !== null} aria-busy={busy === 'pay'}>
                {busy === 'pay' ? 'Paying' : 'Pay'}
              </Button>
              <Button size="lg" variant="ghost" onClick={() => void choose('fail')} disabled={busy !== null} aria-busy={busy === 'fail'}>
                Fail payment
              </Button>
              <Button size="lg" variant="ghost" onClick={() => void choose('cancel')} disabled={busy !== null} aria-busy={busy === 'cancel'}>
                Cancel
              </Button>
            </div>
          </>
        )}
      </Card>
    </Section>
  )
}
