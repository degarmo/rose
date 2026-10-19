import { FlaskConical } from 'lucide-react'
import { useState } from 'react'
import { useParams } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { Button, Card, Chip, Section, useToast } from '@/components/ui'
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
    <Section width="narrow" className="lg:py-24">
      <Card as="article" shape="panel" className="mx-auto max-w-[640px] p-6 sm:p-10">
        <Chip className="self-start">
          <FlaskConical aria-hidden="true" className="mr-1.5 size-3.5" />
          Development sandbox
        </Chip>
        <h1 className="mt-5 text-[2rem] font-light leading-[1.05] text-fg lg:text-h2-lg">Test checkout</h1>
        <p className="mt-3 text-fg-muted">No money moves. Choose what the payment processor should report back.</p>
        {session.status === 'loading' && <LoadingState label="Loading checkout" />}
        {session.status === 'error' && <ErrorState className="mt-6" title="This checkout did not load" onRetry={session.retry} />}
        {session.status === 'success' && (
          <>
            <dl className="mt-6 grid gap-4 rounded-card bg-surface p-5 sm:grid-cols-3">
              <div>
                <dt className="text-label font-semibold uppercase text-fg-muted">For</dt>
                <dd className="mt-1 font-display text-2xl text-fg">{session.data.description}</dd>
              </div>
              <div>
                <dt className="text-label font-semibold uppercase text-fg-muted">Amount</dt>
                <dd className="mt-1 font-display text-2xl text-fg">{formatMoney(session.data.amount_cents)}</dd>
              </div>
              <div>
                <dt className="text-label font-semibold uppercase text-fg-muted">Reference</dt>
                <dd className="mt-1 font-display text-xl tracking-[0.06em] text-fg">{session.data.reference}</dd>
              </div>
            </dl>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button size="lg" onClick={() => void choose('pay')} disabled={busy !== null} aria-busy={busy === 'pay'}>
                {busy === 'pay' ? 'Paying' : 'Pay'}
              </Button>
              <Button size="lg" variant="secondary" onClick={() => void choose('fail')} disabled={busy !== null} aria-busy={busy === 'fail'}>
                Fail payment
              </Button>
              <Button size="lg" variant="secondary" onClick={() => void choose('cancel')} disabled={busy !== null} aria-busy={busy === 'cancel'}>
                Cancel
              </Button>
            </div>
          </>
        )}
      </Card>
    </Section>
  )
}
