import { useEffect, useState } from 'react'
import { Navigate, useSearchParams } from 'react-router'
import { LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { Button, ButtonLink, useToast } from '@/components/ui'
import { goTo, membershipApi, type MembershipPayload } from '@/lib/membershipApi'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { DoorWelcome } from './JoinConfirmation'
import { JOIN_FRAME } from './joinParts'
import { JoinProgress, JoinSteps } from './JoinSteps'

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

  if (auth.status === 'loading') {
    return (
      <div className={JOIN_FRAME}>
        <LoadingState label="Loading" />
      </div>
    )
  }
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
  const confirmed = (outcome === 'active' || outcome === 'awaiting_id') && membership

  return (
    <>
      <JoinSteps current={confirmed ? 3 : 2} />
      <div className={JOIN_FRAME} aria-live="polite">
        {confirmed ? (
          <DoorWelcome
            membership={membership}
            label={outcome === 'active' ? "You're in" : 'Payment received'}
            lead={
              outcome === 'active'
                ? `Your ${membership.tier.name.toLowerCase()} membership is active. Show this code at the door.`
                : 'One last step: staff check a photo ID once, at your first visit, and your membership starts then.'
            }
            secondary={{ to: '/events', label: 'Find an evening' }}
            bring={outcome === 'awaiting_id'}
          />
        ) : (
          <article className="mx-auto flex max-w-[560px] flex-col gap-3 lg:gap-4 lg:py-12">
            <JoinProgress current={2} caption="Payment" />
            {outcome === 'failed' ? (
              <>
                <h1 className="text-[2rem] font-light leading-[1.05] text-fg lg:text-h2-lg">Payment did not go through</h1>
                <p className="text-fg-muted lg:text-lead">Nothing was charged. You can try again, or pay in person on your first visit instead.</p>
                <div className="mt-2 flex flex-col gap-2.5 sm:flex-row sm:gap-3">
                  <Button size="lg" onClick={() => void retry()} disabled={retrying} aria-busy={retrying}>
                    {retrying ? 'Opening checkout' : 'Try again'}
                  </Button>
                  <ButtonLink to="/members/settings/membership" size="lg" variant="secondary">
                    Pay in person instead
                  </ButtonLink>
                </div>
              </>
            ) : outcome === 'slow' ? (
              <>
                <h1 className="text-[2rem] font-light leading-[1.05] text-fg lg:text-h2-lg">Still confirming</h1>
                <p className="text-fg-muted lg:text-lead">
                  This is taking longer than usual. If your payment went through, your membership in Settings will show it
                  within a few minutes. You have not been charged twice by waiting.
                </p>
                <ButtonLink to="/members/settings/membership" size="lg" className="mt-2 self-start">
                  See my membership
                </ButtonLink>
              </>
            ) : (
              <>
                <h1 className="text-[2rem] font-light leading-[1.05] text-fg lg:text-h2-lg">Confirming your payment&hellip;</h1>
                <p className="text-fg-muted lg:text-lead">This usually takes a few seconds. Please keep this page open.</p>
                <LoadingState label="Waiting for confirmation" />
              </>
            )}
          </article>
        )}
      </div>
    </>
  )
}
