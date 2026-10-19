import { CircleAlert, Receipt, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { AppButton } from '@/components/members/app/primitives'
import { appButtonClasses } from '@/components/members/app/ui'
import { MembershipCard, NoMembership } from '@/components/members/settings/MembershipCard'
import { Card, EmptyNote, LoadError, Skeleton, StatusChip, SwitchRow } from '@/components/members/settings/ui'
import { UpcomingPlans } from '@/components/members/settings/UpcomingPlans'
import { useToast } from '@/components/ui'
import { formatDay, formatMoney } from '@/lib/format'
import { goTo, membershipApi, type MembershipPayload, type MyMembership } from '@/lib/membershipApi'
import { useAsync } from '@/lib/useAsync'
import { WhatToBring } from '@/pages/join/JoinConfirmation'

/** Payment history: the date and the amount, a receipt for each. */
function Payments({ membership }: { membership: MyMembership }) {
  if (membership.payments.length === 0) {
    return (
      <EmptyNote icon={Receipt} title="No payments yet">
        Each payment shows here with its date, its amount and a receipt.
      </EmptyNote>
    )
  }
  return (
    <ul className="flex flex-col">
      {membership.payments.map((payment) => {
        const receipt = payment.status !== 'failed' && payment.method !== 'comp'
        return (
          <li key={payment.id} className="flex min-h-12 items-center gap-3 border-b border-border py-2 last:border-b-0">
            <time dateTime={payment.created_at} className="min-w-0 flex-1 text-fg">
              {formatDay(payment.created_at)}
            </time>
            {payment.status === 'refunded' && <StatusChip tone="off">Refund</StatusChip>}
            {payment.status === 'failed' && <StatusChip tone="wait">Did not go through</StatusChip>}
            <span className={payment.status === 'failed' ? 'text-fg-muted line-through' : 'font-semibold text-fg'}>
              {payment.status === 'refunded' ? '−' : ''}
              {formatMoney(payment.amount_cents, membership.tier.currency)}
            </span>
            {receipt ? (
              <Link
                to={`/members/settings/membership/receipts/${payment.id}`}
                className="inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-link hover:text-primary-hover"
              >
                <Receipt aria-hidden="true" className="size-4" />
                Receipt
              </Link>
            ) : (
              <span className="w-[4.75rem]" aria-hidden="true" />
            )}
          </li>
        )
      })}
    </ul>
  )
}

function MembershipDetails({ payload, onChange }: { payload: MembershipPayload; onChange: (next: MembershipPayload) => void }) {
  const toast = useToast()
  const auth = useAuth()
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()
  const [dialog, setDialog] = useState<'cancel' | 'how' | null>(null)
  const membership = payload.membership
  if (!membership) return <NoMembership />

  async function run(action: () => Promise<MembershipPayload>, success: string) {
    setBusy(true)
    try {
      onChange(await action())
      setDialog(null)
      toast.show({ tone: 'success', title: success })
    } catch (error) {
      toast.show({
        tone: 'error',
        title: 'That did not work',
        message: error instanceof Error ? error.message : undefined,
      })
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
      toast.show({
        tone: 'error',
        title: 'Checkout did not start',
        message: error instanceof Error ? error.message : undefined,
      })
      setBusy(false)
    }
  }

  const running = membership.status === 'active' || membership.status === 'grace'
  const ended = membership.status === 'expired' || membership.status === 'cancelled'
  // Nothing has been paid on an unpaid code, or on a free tier waiting for its ID check.
  const pending = membership.status === 'pending_payment' && (!membership.paid_awaiting_id_check || membership.tier.is_free)
  const canCancel = (running && !membership.cancel_at_period_end) || pending

  return (
    <div className="flex flex-col gap-4">
      {membership.last_payment_failed && !ended && (
        <div role="alert" className="flex flex-col gap-3 rounded-app border border-danger p-4 sm:flex-row sm:items-center">
          <CircleAlert aria-hidden="true" className="size-5 shrink-0 text-danger" />
          <p className="flex-1 text-sm text-fg">Your last online payment did not go through. Nothing was charged.</p>
          <AppButton variant="secondary" onClick={() => void payOnline()} disabled={busy}>
            <RefreshCw aria-hidden="true" className="size-4" />
            Try again
          </AppButton>
        </div>
      )}

      <MembershipCard
        membership={membership}
        footer={
          <div className="flex flex-wrap gap-2 border-t border-border pt-4">
            <Link to="/membership" className={appButtonClasses('primary')}>
              {ended ? 'Join again' : 'Change plan'}
            </Link>
            {!ended && (
              <AppButton variant="secondary" onClick={() => setDialog(canCancel ? 'cancel' : 'how')} disabled={busy}>
                Cancel
              </AppButton>
            )}
          </div>
        }
      />

      {membership.online && running && (
        <Card>
          <ul>
            <SwitchRow
              icon={RefreshCw}
              label="Renew automatically"
              sub={membership.auto_renew ? 'Your card is charged at the end of each period' : 'Your membership ends at the end of this period'}
              checked={membership.auto_renew}
              disabled={busy}
              onChange={(enabled) => void run(() => membershipApi.setAutoRenew(enabled), enabled ? 'Automatic renewal is on' : 'Automatic renewal is off')}
            />
          </ul>
        </Card>
      )}

      {membership.status === 'pending_payment' && (
        <Card title="What to bring">
          <WhatToBring membership={membership} />
          {membership.code_expires_at && <p className="mt-3 text-meta text-fg-muted">This code stays open until {formatDay(membership.code_expires_at)}.</p>}
        </Card>
      )}

      <Card title="Payment history">
        <Payments membership={membership} />
      </Card>

      <ConfirmDialog
        open={dialog === 'cancel'}
        title="Cancel your membership?"
        confirmLabel={pending ? 'Yes, cancel' : 'Cancel at period end'}
        busy={busy}
        onClose={() => setDialog(null)}
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
            You keep access until {membership.current_period_end ? formatDay(membership.current_period_end) : 'the end of this period'}, and nothing renews
            after that. Payments already made are not refunded automatically.
          </p>
        )}
      </ConfirmDialog>
      <ConfirmDialog
        open={dialog === 'how'}
        title="Cancelling"
        confirmLabel="Contact us"
        onClose={() => setDialog(null)}
        onConfirm={() => navigate('/contact')}
      >
        {membership.cancel_at_period_end ? (
          <p>
            Already done: your membership ends on {membership.current_period_end ? formatDay(membership.current_period_end) : 'the last day of this period'} and
            does not renew.
          </p>
        ) : (
          <p>This membership can&rsquo;t be cancelled online while it is in this state. Send us a message and a member of staff will sort it out.</p>
        )}
      </ConfirmDialog>
    </div>
  )
}

/** Settings · Membership: the card with its door code, plan changes, renewal, payments and your plans. */
export function MembershipSection() {
  const state = useAsync(() => membershipApi.me(), 'my-membership')
  const [override, setOverride] = useState<MembershipPayload | null>(null)
  const payload = override ?? (state.status === 'success' ? state.data : null)

  return (
    <div className="flex flex-col gap-4">
      {state.status === 'loading' && !override && (
        <div className="rounded-app border border-border p-4">
          <Skeleton lines={4} />
        </div>
      )}
      {state.status === 'error' && !override && <LoadError title="Your membership did not load" onRetry={state.retry} />}
      {payload && <MembershipDetails payload={payload} onChange={setOverride} />}
      <Card title="Upcoming plans">
        <UpcomingPlans />
      </Card>
    </div>
  )
}
