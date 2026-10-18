import { CircleAlert, Receipt as ReceiptIcon } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { Toggle } from '@/components/members/Toggle'
import { ReferenceCode } from '@/components/membership/ReferenceCode'
import { Badge, Button, ButtonLink, Card, useToast } from '@/components/ui'
import { formatDay, formatMoney } from '@/lib/format'
import { goTo, isOpen, membershipApi, priceLabel, type MembershipPayload, type MyMembership } from '@/lib/membershipApi'
import { useAsync } from '@/lib/useAsync'
import { WhatToBring } from '../join/JoinConfirmation'

const TONES: Record<MyMembership['status'], 'brass' | 'rose' | 'neutral'> = {
  active: 'brass',
  grace: 'rose',
  pending_payment: 'neutral',
  suspended: 'rose',
  expired: 'neutral',
  cancelled: 'neutral',
}

function periodLine(m: MyMembership) {
  if (!m.current_period_end) return null
  const day = formatDay(m.current_period_end)
  if (m.status === 'expired' || m.status === 'cancelled') return `Ended ${day}`
  if (m.status === 'grace') return `Renewal was due ${day}. Renew soon to keep your access.`
  if (m.cancel_at_period_end) return `Ends ${day}. It will not renew.`
  if (m.auto_renew) return `Renews automatically on ${day}`
  if (m.tier.interval === 'once') return `Your pass runs until ${day}`
  return `Paid through ${day}`
}

function Status({ membership }: { membership: MyMembership }) {
  if (membership.status === 'pending_payment' && membership.paid_awaiting_id_check) {
    return <p className="text-fg-muted">Paid. Staff will start your membership after a quick photo ID check on your first visit.</p>
  }
  if (membership.status === 'pending_payment') {
    return <p className="text-fg-muted">Waiting for payment. Bring your code on your first visit and staff will start your membership.</p>
  }
  if (membership.status === 'suspended') {
    return <p className="text-fg-muted">Your membership is paused. A member of staff will be in touch, or use the contact page.</p>
  }
  const line = periodLine(membership)
  return line ? <p className="text-fg-muted">{line}</p> : null
}

function Payments({ membership }: { membership: MyMembership }) {
  if (membership.payments.length === 0) return <p className="text-sm text-fg-subtle">No payments yet.</p>
  return (
    <ul className="divide-y divide-border">
      {membership.payments.map((payment) => (
        <li key={payment.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
          <div>
            <p className="text-fg">
              {payment.status === 'refunded' ? 'Refund' : payment.status === 'failed' ? 'Failed payment' : 'Payment'} &middot;{' '}
              {payment.method_label}
            </p>
            <p className="text-fg-subtle">
              <time dateTime={payment.created_at}>{formatDay(payment.created_at)}</time>
            </p>
          </div>
          <div className="flex items-center gap-4">
            <span className={payment.status === 'failed' ? 'text-fg-subtle line-through' : 'text-fg'}>
              {payment.status === 'refunded' ? '−' : ''}
              {formatMoney(payment.amount_cents, membership.tier.currency)}
            </span>
            {payment.status !== 'failed' && payment.method !== 'comp' && (
              <Link
                to={`/account/receipts/${payment.id}`}
                className="inline-flex min-h-11 items-center gap-1.5 text-accent underline decoration-highlight/60 underline-offset-4"
              >
                <ReceiptIcon aria-hidden="true" className="size-4" />
                Receipt
              </Link>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}

export function MembershipDetails({ payload, onChange }: { payload: MembershipPayload; onChange: (next: MembershipPayload) => void }) {
  const toast = useToast()
  const auth = useAuth()
  const [busy, setBusy] = useState(false)
  const [confirmCancel, setConfirmCancel] = useState(false)
  const membership = payload.membership

  if (!membership) {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-fg-muted">
          You are not a member yet. Membership opens members&rsquo; evenings, members-only classes and the member community.
        </p>
        <ButtonLink to="/join" className="self-start">
          Become a member
        </ButtonLink>
      </div>
    )
  }

  async function run(action: () => Promise<MembershipPayload>, success: string) {
    setBusy(true)
    try {
      onChange(await action())
      setConfirmCancel(false)
      toast.show({ tone: 'success', title: success })
    } catch (error) {
      toast.show({ tone: 'error', title: 'That did not work', message: error instanceof Error ? error.message : undefined })
    } finally {
      setBusy(false)
    }
  }

  async function payOnline() {
    setBusy(true)
    try {
      const online = (await membershipApi.options()).methods.find((method) => method.online)
      if (!online) throw new Error('Online payment is not available right now. You can pay in person instead.')
      goTo((await membershipApi.checkout(online.key)).redirect_url)
    } catch (error) {
      toast.show({ tone: 'error', title: 'Checkout did not start', message: error instanceof Error ? error.message : undefined })
      setBusy(false)
    }
  }

  const open = isOpen(membership)
  const running = membership.status === 'active' || membership.status === 'grace'
  const pending = membership.status === 'pending_payment' && !membership.paid_awaiting_id_check
  const canCancel = (running && !membership.cancel_at_period_end) || pending

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <p className="font-display text-2xl text-fg">{membership.tier.name}</p>
          <Badge tone={TONES[membership.status]}>{membership.status_label}</Badge>
        </div>
        <p className="text-sm text-fg-subtle">{priceLabel(membership.tier)}</p>
        <Status membership={membership} />
      </div>

      {membership.last_payment_failed && open && (
        <div role="alert" className="flex flex-col gap-3 rounded-xl border border-danger/40 p-4 sm:flex-row sm:items-center">
          <CircleAlert aria-hidden="true" className="size-5 shrink-0 text-danger" />
          <p className="flex-1 text-sm text-fg-muted">Your last online payment did not go through. Nothing was charged.</p>
          <Button variant="ghost" onClick={() => void payOnline()} disabled={busy}>
            Try again
          </Button>
        </div>
      )}

      {open && (
        <div className="border-t border-border pt-6">
          <ReferenceCode code={membership.reference_code} size="md" />
          <p className="mt-3 text-sm text-fg-subtle">Show this at the door. It identifies your membership, not you.</p>
        </div>
      )}

      {membership.status === 'pending_payment' && (
        <div className="border-t border-border pt-6">
          <h3 className="font-display text-xl text-fg">What to bring</h3>
          <div className="mt-4">
            <WhatToBring membership={membership} />
          </div>
          {membership.code_expires_at && (
            <p className="mt-4 text-sm text-fg-subtle">This code stays open until {formatDay(membership.code_expires_at)}.</p>
          )}
        </div>
      )}

      {membership.online && running && (
        <div className="border-t border-border pt-6">
          <Toggle
            label="Renew automatically"
            hint={membership.auto_renew ? 'Your card is charged at the end of each period.' : 'Your membership ends at the end of this period.'}
            checked={membership.auto_renew}
            disabled={busy}
            onChange={(enabled) =>
              void run(() => membershipApi.setAutoRenew(enabled), enabled ? 'Automatic renewal is on' : 'Automatic renewal is off')
            }
          />
        </div>
      )}

      <div className="border-t border-border pt-6">
        <h3 className="font-display text-xl text-fg">Payments</h3>
        <div className="mt-3">
          <Payments membership={membership} />
        </div>
      </div>

      {(membership.status === 'expired' || membership.status === 'cancelled') && (
        <ButtonLink to="/join" className="self-start">
          Join again
        </ButtonLink>
      )}

      {canCancel && (
        <div className="border-t border-border pt-6">
          <Button variant="ghost" className="border-danger/60 text-danger" onClick={() => setConfirmCancel(true)} disabled={busy}>
            Cancel membership
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={confirmCancel}
        title="Cancel your membership?"
        confirmLabel={pending ? 'Yes, cancel' : 'Cancel at period end'}
        busy={busy}
        onClose={() => setConfirmCancel(false)}
        onConfirm={() =>
          void run(async () => {
            const next = await membershipApi.cancel()
            await auth.refresh()
            return next
          }, 'Your membership is cancelled')
        }
      >
        {pending ? (
          <p>Your reference code stops working straight away. You can join again whenever you like.</p>
        ) : (
          <p>
            You keep access until {membership.current_period_end ? formatDay(membership.current_period_end) : 'the end of this period'}
            , and nothing renews after that. Payments already made are not refunded automatically.
          </p>
        )}
      </ConfirmDialog>
    </div>
  )
}

/** The membership card on /account. */
export function MembershipCard() {
  const state = useAsync(() => membershipApi.me(), 'my-membership')
  const [override, setOverride] = useState<MembershipPayload | null>(null)
  const payload = override ?? (state.status === 'success' ? state.data : null)

  return (
    <Card as="article" id="membership" aria-labelledby="membership-heading" className="scroll-mt-28 p-6 sm:p-8">
      <h2 id="membership-heading" className="text-3xl text-fg">
        Membership
      </h2>
      <div className="mt-6">
        {state.status === 'loading' && !override && <LoadingState label="Loading your membership" />}
        {state.status === 'error' && !override && <ErrorState title="Your membership did not load" onRetry={state.retry} />}
        {payload && <MembershipDetails payload={payload} onChange={setOverride} />}
      </div>
    </Card>
  )
}
