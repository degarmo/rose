import { CalendarClock, IdCard, Ticket } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { appButtonClasses, ICON } from '@/components/members/app/ui'
import { formatDay } from '@/lib/format'
import { eventsLeftLabel, isOpen, priceLabel, type MembershipStatus, type MyMembership } from '@/lib/membershipApi'
import { useAsync } from '@/lib/useAsync'
import { EmptyNote, StatusChip, type ChipTone } from './ui'

const TONES: Record<MembershipStatus, ChipTone> = {
  active: 'ok',
  grace: 'wait',
  pending_payment: 'wait',
  suspended: 'off',
  expired: 'off',
  cancelled: 'off',
}

/** When it renews or ends, in one line; null before a first period. */
function periodLine(m: MyMembership) {
  if (m.status === 'pending_payment') {
    if (m.paid_awaiting_id_check) return `${m.tier.is_free ? 'Nothing to pay.' : 'Paid.'} Staff start it after a quick photo ID check on your first visit.`
    return 'Waiting for payment. Bring your code on your first visit and staff will start your membership.'
  }
  if (m.status === 'suspended') return 'Paused. A member of staff will be in touch, or use the contact page.'
  if (!m.current_period_end) return null
  const day = formatDay(m.current_period_end)
  if (m.status === 'expired' || m.status === 'cancelled') return `Ended ${day}`
  if (m.status === 'grace') return `Renewal was due ${day}. Renew soon to keep your access.`
  if (m.cancel_at_period_end) return `Expires ${day}. It will not renew.`
  if (m.auto_renew) return `Renews ${day}`
  if (m.tier.interval === 'once') return `Expires ${day}`
  return `Paid through ${day}`
}

/** The door reference: the code and its QR, made on this device and always dark on white for scanners. */
export function DoorCode({ code }: { code: string }) {
  const qr = useAsync(
    () =>
      import('qrcode').then(({ default: QRCode }) =>
        QRCode.toString(code, {
          type: 'svg',
          margin: 0,
          errorCorrectionLevel: 'M',
          color: { dark: '#262626', light: '#ffffff' },
        }),
      ),
    code,
  )
  return (
    <div className="flex items-center gap-4 rounded-app bg-surface p-3">
      <span className="flex size-28 shrink-0 items-center justify-center rounded-app border border-border bg-white p-2">
        {qr.status === 'success' ? (
          <img src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(qr.data)}`} alt={`QR code for ${code}`} className="size-full" />
        ) : (
          <span aria-hidden="true" className="size-full animate-pulse rounded bg-control" />
        )}
      </span>
      <span className="min-w-0">
        <span className="block text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Door reference</span>
        <span className="mt-1 block text-2xl font-semibold tracking-[0.08em] text-fg">{code}</span>
        <span className="mt-1 block text-meta text-fg-muted">Show this at the door. It identifies your membership, not you.</span>
      </span>
    </div>
  )
}

function Line({ icon: Icon, children }: { icon: typeof Ticket; children: string }) {
  return (
    <p className="flex items-start gap-2 text-fg">
      <Icon aria-hidden="true" size={18} strokeWidth={ICON.stroke} className="mt-px shrink-0 text-fg-muted" />
      {children}
    </p>
  )
}

/** No membership yet, with the way to one. */
export function NoMembership() {
  return (
    <EmptyNote
      icon={IdCard}
      title="You don't have a membership yet"
      action={
        <Link to="/membership" className={appButtonClasses('primary')}>
          See plans
        </Link>
      }
    >
      Membership opens members&rsquo; evenings, members-only classes and, on most plans, the member community.
    </EmptyNote>
  )
}

/**
 * Your membership at a glance (Home and Settings): tier, status, when it renews or expires,
 * events left this month and, while it is open, the door code with its QR (unless something
 * beside it already shows it, Home's checklist or the age check card: `showCode`).
 */
export function MembershipCard({ membership, footer, showCode = true }: { membership: MyMembership; footer?: ReactNode; showCode?: boolean }) {
  const running = membership.status === 'active' || membership.status === 'grace'
  const period = periodLine(membership)
  return (
    <article aria-label="Your membership" className="flex flex-col gap-4 rounded-app border border-border bg-canvas p-4">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Membership</p>
          <h2 className="mt-0.5 text-lg font-semibold text-fg">{membership.tier.name}</h2>
          <p className="text-meta text-fg-muted">{priceLabel(membership.tier)}</p>
        </div>
        <StatusChip tone={TONES[membership.status]}>{membership.status_label}</StatusChip>
      </header>
      {(period || running) && (
        <div className="flex flex-col gap-1.5">
          {period && <Line icon={CalendarClock}>{period}</Line>}
          {running && <Line icon={Ticket}>{eventsLeftLabel(membership)}</Line>}
        </div>
      )}
      {showCode && isOpen(membership) && <DoorCode code={membership.reference_code} />}
      {footer}
    </article>
  )
}
