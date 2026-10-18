import { BadgeCheck, CircleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Navigate, useSearchParams } from 'react-router'
import { LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { ReferenceCode } from '@/components/membership/ReferenceCode'
import { Button, ButtonLink, Card, Section, useToast } from '@/components/ui'
import { goTo, membershipApi, type MembershipPayload } from '@/lib/membershipApi'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { WhatToBring } from './JoinConfirmation'

const POLL_MS = 2000
const GIVE_UP_AFTER = 30

type Outcome = 'waiting' | 'active' | 'awaiting_id' | 'failed' | 'slow'

function outcomeOf(payload: MembershipPayload | null, ref: string): Outcome {
  const membership = payload?.membership
  if (!membership || membership.reference_code !== ref) return 'waiting'
  if (membership.status === 'active' || membership.status === 'grace') return 'active'
  if (membership.paid_awaiting_id_check) return 'awaiting_id'
  if (membership.last_payment_failed) return 'failed'
  return 'waiting'
}

/**
 * Back from the hosted checkout. Coming back proves nothing, so this page only
 * watches for the provider's webhook to have been applied on the server.
 */
export function ConfirmingPage() {
  useDocumentMeta({ title: 'Confirming', noindex: true })
  const auth = useAuth()
  const toast = useToast()
  const [params] = useSearchParams()
  const ref = params.get('ref') ?? ''
  const [payload, setPayload] = useState<MembershipPayload | null>(null)
  const [polls, setPolls] = useState(0)
  const [retrying, setRetrying] = useState(false)
  const found = outcomeOf(payload, ref)
  const outcome: Outcome = found === 'waiting' && polls >= GIVE_UP_AFTER ? 'slow' : found
  const signedIn = Boolean(auth.user)
  const refreshSession = auth.refresh

  useEffect(() => {
    if (!signedIn || outcome !== 'waiting') return
    let active = true
    const timer = window.setTimeout(
      () => {
        membershipApi.me().then(
          (next) => {
            if (!active) return
            setPayload(next)
            setPolls((n) => n + 1)
            // The header's "Join" becomes "Membership" once there is one.
            if (outcomeOf(next, ref) !== 'waiting') void refreshSession()
          },
          () => {
            if (active) setPolls((n) => n + 1)
          },
        )
      },
      polls === 0 ? 0 : POLL_MS,
    )
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [signedIn, outcome, polls, ref, refreshSession])

  if (auth.status === 'loading') return <Section className="pt-32"><LoadingState label="Loading" /></Section>
  if (!auth.user) return <Navigate to={`/account/login?next=${encodeURIComponent(`/join/confirming?ref=${ref}`)}`} replace />

  async function retry() {
    setRetrying(true)
    try {
      const online = (await membershipApi.options()).methods.find((method) => method.online)
      if (!online) throw new Error('Online payment is not available right now. You can pay in person instead.')
      goTo((await membershipApi.checkout(online.key)).redirect_url)
    } catch (error) {
      toast.show({ tone: 'error', title: 'Checkout did not start', message: error instanceof Error ? error.message : undefined })
      setRetrying(false)
    }
  }

  const membership = payload?.membership

  return (
    <Section className="pt-32" width="narrow">
      <Card as="article" aria-live="polite" className="p-6 sm:p-8">
        {outcome === 'waiting' && (
          <>
            <h1 className="text-4xl text-fg">Confirming your payment&hellip;</h1>
            <p className="mt-3 text-fg-muted">This usually takes a few seconds. Please keep this page open.</p>
            <LoadingState label="Waiting for confirmation" />
          </>
        )}
        {outcome === 'slow' && (
          <>
            <h1 className="text-4xl text-fg">Still confirming</h1>
            <p className="mt-3 text-fg-muted">
              This is taking longer than usual. If your payment went through, your account page will show it within a
              few minutes. You have not been charged twice by waiting.
            </p>
            <ButtonLink to="/account#membership" size="lg" className="mt-6 self-start">
              Go to my account
            </ButtonLink>
          </>
        )}
        {outcome === 'active' && membership && (
          <>
            <h1 className="flex items-center gap-3 text-4xl text-fg">
              <BadgeCheck aria-hidden="true" className="size-8 text-success" />
              Welcome in
            </h1>
            <p className="mt-3 text-fg-muted">Your {membership.tier.name.toLowerCase()} membership is active.</p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <ButtonLink to="/account#membership" size="lg">
                See my membership
              </ButtonLink>
              <ButtonLink to="/events" size="lg" variant="ghost">
                Find an evening
              </ButtonLink>
            </div>
          </>
        )}
        {outcome === 'awaiting_id' && membership && (
          <>
            <h1 className="flex items-center gap-3 text-4xl text-fg">
              <BadgeCheck aria-hidden="true" className="size-8 text-success" />
              Payment received
            </h1>
            <p className="mt-3 text-fg-muted">
              One last step: staff check a photo ID once, at your first visit, and your membership starts then.
            </p>
            <ReferenceCode code={membership.reference_code} className="mt-8" />
            <h2 className="mt-10 text-xl text-fg">What to bring</h2>
            <div className="mt-4">
              <WhatToBring membership={membership} />
            </div>
          </>
        )}
        {outcome === 'failed' && (
          <>
            <h1 className="flex items-center gap-3 text-4xl text-fg">
              <CircleAlert aria-hidden="true" className="size-8 text-danger" />
              Payment did not go through
            </h1>
            <p className="mt-3 text-fg-muted">Nothing was charged. You can try again, or pay in person on your first visit instead.</p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Button size="lg" onClick={() => void retry()} disabled={retrying} aria-busy={retrying}>
                {retrying ? 'Opening checkout' : 'Try again'}
              </Button>
              <ButtonLink to="/account#membership" size="lg" variant="ghost">
                Pay in person instead
              </ButtonLink>
            </div>
          </>
        )}
      </Card>
    </Section>
  )
}
