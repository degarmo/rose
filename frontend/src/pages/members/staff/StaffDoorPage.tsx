import { BadgeCheck, CalendarCheck, Camera, CircleAlert, CreditCard, HandHeart, IdCard, ListChecks, Repeat, ScanLine, Search, ShieldX, UserCheck, type LucideIcon } from 'lucide-react'
import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { appButtonClasses } from '@/components/members/app/ui'
import { StaffFrame } from '@/components/members/staff/StaffFrame'
import { Button, Checkbox, FormField, Input, Modal, Select, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { formatDay } from '@/lib/format'
import { doorApi, type DoorAction, type DoorCard, type DoorPerson, type DoorRequest, type DoorSearch } from '@/lib/safetyApi'
import { useAsync } from '@/lib/useAsync'
import { useSearchParams } from 'react-router'

/** A reference code as printed: three letters or digits, a dash, three more (no 0, O, 1, I, L). */
const CODE = /^[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{3}-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{3}$/
const BIG = 'h-14 px-6 text-base'
const METHODS = [
  { value: 'cash', label: 'Cash' },
  { value: 'card_in_person', label: 'Card in person' },
]

interface ActionSpec {
  label: string
  title: string
  icon: LucideIcon
  /** Takes a payment (method and amount). */
  pays?: boolean
  /** The first activation needs the photo ID check if none is on file. */
  checksId?: boolean
  reason?: boolean
  submit: string
  tone?: 'primary' | 'secondary' | 'danger'
}

const ACTIONS: Record<DoorAction, ActionSpec> = {
  walk_in: { label: 'Check in', title: 'Check in tonight', icon: CalendarCheck, submit: 'Check in' },
  activate_paid: { label: 'ID check', title: 'Check ID and activate', icon: BadgeCheck, checksId: true, submit: 'Activate' },
  activate: { label: 'Record payment and activate', title: 'Record payment and activate', icon: CreditCard, pays: true, checksId: true, submit: 'Record payment and activate' },
  guest_visit: { label: 'Guest visit', title: 'Guest visit', icon: UserCheck, pays: true, checksId: true, submit: 'Record payment, in for tonight' },
  renew: { label: 'Renew', title: 'Renew', icon: Repeat, pays: true, checksId: true, submit: 'Renew' },
  comp: { label: 'Comp membership', title: 'Complimentary membership', icon: IdCard, reason: true, checksId: true, submit: 'Comp membership', tone: 'secondary' },
  suspend: { label: 'Suspend', title: 'Suspend', icon: CircleAlert, reason: true, submit: 'Suspend', tone: 'danger' },
  reinstate: { label: 'Reinstate', title: 'Reinstate', icon: BadgeCheck, reason: true, checksId: true, submit: 'Reinstate', tone: 'secondary' },
  verify: { label: 'Record ID check', title: 'Record ID check', icon: BadgeCheck, checksId: true, submit: 'Record ID check', tone: 'secondary' },
  revoke: { label: 'Revoke ID check', title: 'Revoke the ID check', icon: ShieldX, reason: true, submit: 'Revoke', tone: 'danger' },
}
/** The big buttons, in the order the door uses them; the rest sit below. */
const MAIN: DoorAction[] = ['walk_in', 'activate_paid', 'activate', 'guest_visit', 'renew']

function money(value: string) {
  return `$${value}`
}

/** Decodes QR codes on this device (jsQR, loaded only when scanning); nothing is sent until a code is found. */
function Scanner({ onCode, onClose }: { onCode: (code: string) => void; onClose: () => void }) {
  const video = useRef<HTMLVideoElement>(null)
  const [status, setStatus] = useState('Point the camera at the member’s code.')

  useEffect(() => {
    let stream: MediaStream | null = null
    let frame = 0
    let stopped = false
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d', { willReadFrequently: true })
    async function start() {
      if (!navigator.mediaDevices?.getUserMedia || !context) {
        setStatus('The camera is not available here. Type the code instead.')
        return
      }
      try {
        const { default: jsQR } = await import('jsqr')
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
        if (stopped || !video.current) return
        video.current.srcObject = stream
        await video.current.play()
        const tick = () => {
          const element = video.current
          if (stopped || !element) return
          if (element.readyState === element.HAVE_ENOUGH_DATA) {
            canvas.width = element.videoWidth
            canvas.height = element.videoHeight
            context.drawImage(element, 0, 0, canvas.width, canvas.height)
            const image = context.getImageData(0, 0, canvas.width, canvas.height)
            const found = jsQR(image.data, image.width, image.height, { inversionAttempts: 'dontInvert' })
            const text = found?.data.trim()
            if (text && CODE.test(text)) {
              onCode(text)
              return
            }
          }
          frame = requestAnimationFrame(tick)
        }
        frame = requestAnimationFrame(tick)
      } catch {
        setStatus('The camera is not available. Type the code instead.')
      }
    }
    void start()
    return () => {
      stopped = true
      cancelAnimationFrame(frame)
      stream?.getTracks().forEach((track) => track.stop())
    }
  }, [onCode])

  return (
    <div className="flex flex-col items-start gap-3 rounded-app border border-border p-4">
      <video ref={video} playsInline muted className="aspect-video w-full max-w-[480px] rounded-app bg-black" />
      <p role="status" className="text-fg-muted">
        {status}
      </p>
      <button type="button" onClick={onClose} className={appButtonClasses('secondary', BIG)}>
        Stop camera
      </button>
    </div>
  )
}

function Chip({ tone = 'off', children }: { tone?: 'ok' | 'wait' | 'alert' | 'off'; children: string }) {
  const tones = { ok: 'bg-tint text-tint-fg', wait: 'bg-wait text-wait-fg', alert: 'bg-danger text-white', off: 'bg-control text-fg' }
  return <span className={cn('inline-flex h-7 items-center rounded-full px-3 text-sm font-semibold', tones[tone])}>{children}</span>
}

function statusTone(card: DoorCard) {
  if (card.status === 'active') return 'ok'
  if (card.status === 'grace' || card.status === 'pending_payment') return 'wait'
  if (card.status === 'suspended') return 'alert'
  return 'off'
}

interface Dialog {
  /** A membership card, or an account with no membership (only verify and revoke). */
  card?: DoorCard
  person?: DoorPerson
  action: DoorAction | 'refund'
  paymentId?: number
}

function ActionDialog({ dialog, search, onClose, onDone }: { dialog: Dialog; search: DoorSearch; onClose: () => void; onDone: (message: string) => void }) {
  const { card, person, action } = dialog
  const subject = (card ?? person)!
  const spec = action === 'refund' ? null : ACTIONS[action]
  const [method, setMethod] = useState('cash')
  const [amount, setAmount] = useState(action === 'refund' || !card ? '' : card.default_amount)
  const [witness, setWitness] = useState('')
  const [note, setNote] = useState('')
  const [reason, setReason] = useState('')
  const [idChecked, setIdChecked] = useState(false)
  const [event, setEvent] = useState(String(search.tonight_events[0]?.id ?? ''))
  const [party, setParty] = useState('1')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)
  const needsId = Boolean(spec?.checksId && !subject.id_checked)
  // Your own ID check needs a second team member there with you.
  const needsWitness = needsId && subject.is_you
  const title = action === 'refund' ? 'Refund' : (spec?.title ?? '')

  async function submit(formEvent: FormEvent) {
    formEvent.preventDefault()
    if (needsId && !idChecked) return setError('Check a photo ID showing 18+ first.')
    if (needsWitness && !witness) return setError('Choose the team member witnessing your check.')
    const payload: DoorRequest = card ? { action, membership: card.id } : { action, person: subject.id }
    if (needsWitness) payload.witness = Number(witness)
    if (action === 'refund') Object.assign(payload, { payment: dialog.paymentId, amount, note })
    if (spec?.pays) Object.assign(payload, { method, amount, note })
    if (spec?.reason) payload.reason = reason
    if (needsId) payload.id_checked = true
    if (action === 'walk_in') Object.assign(payload, { event: Number(event), party_size: Number(party) })
    setBusy(true)
    try {
      const result = await doorApi.act(payload)
      onDone(result.message ?? 'Done.')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'That did not work. Please try again.')
      setBusy(false)
    }
  }

  return (
    <Modal open onClose={onClose} title={title}>
      <form noValidate onSubmit={(e) => void submit(e)} className="flex flex-col gap-4">
        <p className="text-fg-muted">
          <span className="font-semibold text-fg">{subject.display_name}</span> · {card ? `${card.reference_code} · ${card.tier.name}` : 'No membership'}
        </p>
        {action === 'revoke' && <p className="text-fg">The member feed closes for them at once. The reason goes in the log.</p>}
        {action === 'walk_in' && (
          <>
            <FormField label="Event" required>
              {(field) => <Select {...field} value={event} onChange={(e) => setEvent(e.target.value)} options={search.tonight_events.map((item) => ({ value: String(item.id), label: `${item.title} (${new Date(item.starts_at).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/Chicago' })})` }))} />}
            </FormField>
            <FormField label="Party" hint={card ? `${card.tier.guests_included} guest${card.tier.guests_included === 1 ? '' : 's'} included per event on ${card.tier.name}.` : undefined}>
              {(field) => <Select {...field} value={party} onChange={(e) => setParty(e.target.value)} options={[{ value: '1', label: 'Just them' }, { value: '2', label: 'With a guest' }]} />}
            </FormField>
          </>
        )}
        {(spec?.pays || action === 'refund') && (
          <div className="grid gap-4 sm:grid-cols-2">
            {spec?.pays && <FormField label="Method">{(field) => <Select {...field} value={method} onChange={(e) => setMethod(e.target.value)} options={METHODS} />}</FormField>}
            <FormField label="Amount" required>
              {(field) => <Input {...field} inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />}
            </FormField>
          </div>
        )}
        {(spec?.pays || action === 'refund') && (
          <FormField label="Note" optionalLabel="Optional">
            {(field) => <Input {...field} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} />}
          </FormField>
        )}
        {spec?.reason && (
          <FormField label="Reason" required>
            {(field) => <Input {...field} maxLength={300} value={reason} onChange={(e) => setReason(e.target.value)} />}
          </FormField>
        )}
        {needsWitness && (
          <FormField label="Witness" hint="Your own check needs another team member, here with you. Both of you are named in the log." required>
            {(field) => <Select {...field} value={witness} onChange={(e) => setWitness(e.target.value)} options={[{ value: '', label: 'Choose a team member' }, ...search.witnesses.map((w) => ({ value: String(w.id), label: w.display_name }))]} />}
          </FormField>
        )}
        {needsId && <Checkbox label="Photo ID checked, 18+" hint="Only that it was seen. Nothing is copied or kept." checked={idChecked} onChange={(e) => setIdChecked(e.target.checked)} />}
        {action === 'activate_paid' && subject.id_checked && <p className="text-fg-muted">An ID check is already on file.</p>}
        {error && (
          <p role="alert" className="rounded-app bg-tint px-4 py-3 font-semibold text-tint-fg">
            {error}
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" size="lg" disabled={busy || (needsId && !idChecked) || (needsWitness && !witness)} aria-busy={busy}>
            {busy ? 'Working' : action === 'refund' ? 'Record refund' : spec?.submit}
          </Button>
          <Button type="button" variant="secondary" size="lg" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function DonationDialog({ search, onClose, onDone }: { search: DoorSearch | null; onClose: () => void; onDone: (message: string) => void }) {
  const methods = search?.donation_methods ?? [...METHODS, { value: 'check', label: 'Check' }]
  const [method, setMethod] = useState(methods[0].value)
  const [amount, setAmount] = useState('')
  const [donor, setDonor] = useState('')
  const [email, setEmail] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  async function submit(formEvent: FormEvent) {
    formEvent.preventDefault()
    setBusy(true)
    try {
      const result = await doorApi.act({ action: 'record_donation', method, amount, donor_display: donor, acknowledgement_email: email, note })
      onDone(result.message ?? 'Donation recorded.')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'That did not work. Please try again.')
      setBusy(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Record a donation">
      <form noValidate onSubmit={(e) => void submit(e)} className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Method">{(field) => <Select {...field} value={method} onChange={(e) => setMethod(e.target.value)} options={methods} />}</FormField>
          <FormField label="Amount" required>{(field) => <Input {...field} inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />}</FormField>
        </div>
        <FormField label="Name to record" hint="Leave empty for Anonymous.">{(field) => <Input {...field} maxLength={60} value={donor} onChange={(e) => setDonor(e.target.value)} />}</FormField>
        <FormField label="Email for an acknowledgement" optionalLabel="Optional">{(field) => <Input {...field} type="email" maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} />}</FormField>
        <FormField label="Note" optionalLabel="Optional">{(field) => <Input {...field} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} />}</FormField>
        {error && (
          <p role="alert" className="rounded-app bg-tint px-4 py-3 font-semibold text-tint-fg">
            {error}
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" size="lg" disabled={busy} aria-busy={busy}>
            {busy ? 'Working' : 'Record donation'}
          </Button>
          <Button type="button" variant="secondary" size="lg" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function ResultCard({ card, search, onOpen, signature, onReveal }: { card: DoorCard; search: DoorSearch; onOpen: (dialog: Dialog) => void; signature?: string; onReveal: () => void }) {
  const available = card.do_not_admit ? [] : card.actions
  const main = MAIN.filter((action) => available.includes(action))
  const more = available.filter((action) => !MAIN.includes(action))
  const noEventTonight = main.includes('walk_in') && search.tonight_events.length === 0
  return (
    <article aria-labelledby={`card-${card.id}`} className={cn('flex flex-col gap-4 rounded-app border bg-canvas p-5', card.do_not_admit ? 'border-2 border-danger' : 'border-border')}>
      {card.do_not_admit && (
        <p role="alert" className="rounded-app bg-danger px-4 py-3 text-lg font-semibold text-white">
          Do not admit. Ask a member of the team.
        </p>
      )}
      {card.events_suspended_until && (
        <p role="alert" className="rounded-app bg-wait px-4 py-3 font-semibold text-wait-fg">
          Event access suspended until {formatDay(card.events_suspended_until)}
        </p>
      )}
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-lg tracking-[0.08em] text-fg-muted">{card.reference_code}</p>
          <h2 id={`card-${card.id}`} className="text-2xl font-semibold text-fg">
            {card.display_name}
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {card.is_guest_pass && <Chip>Guest pass</Chip>}
          <Chip tone={statusTone(card)}>{card.status_label}</Chip>
          {card.id_checked ? <Chip tone="ok">ID verified</Chip> : <Chip tone="alert">ID check needed</Chip>}
          {card.paid_awaiting_id_check && <Chip tone="wait">{card.tier.is_free ? 'Free, waiting for ID' : 'Paid online, waiting for ID'}</Chip>}
        </div>
      </header>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Tier</dt>
          <dd className="font-semibold text-fg">{card.tier.name}</dd>
        </div>
        {!card.is_guest_pass && (
          <>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Events this month</dt>
              <dd className="font-semibold text-fg">{card.events_remaining === null ? 'Unlimited' : `${card.events_remaining} left`}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Guests included</dt>
              <dd className="font-semibold text-fg">
                {card.tier.guests_included} per event{card.tier.guest_discount ? ' · discount' : ''}
              </dd>
            </div>
          </>
        )}
        <div>
          <dt className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Period ends</dt>
          <dd className="font-semibold text-fg">{card.period_end ? formatDay(card.period_end) : 'Not started'}</dd>
        </div>
      </dl>
      {main.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {main.map((action) => {
            const spec = ACTIONS[action]
            const disabled = action === 'walk_in' && noEventTonight
            return (
              <button key={action} type="button" disabled={disabled} onClick={() => onOpen({ card, action })} className={appButtonClasses('primary', cn(BIG, 'w-full justify-start gap-3'))}>
                <spec.icon aria-hidden="true" className="size-5" />
                {disabled ? 'No members-only event tonight' : spec.label}
              </button>
            )
          })}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {more.map((action) => {
          const spec = ACTIONS[action]
          return (
            <button key={action} type="button" onClick={() => onOpen({ card, action })} className={appButtonClasses(spec.tone === 'danger' ? 'outline' : 'secondary', cn('h-12 px-5', spec.tone === 'danger' && 'border-danger text-danger'))}>
              {spec.label}
            </button>
          )
        })}
        {signature ? (
          <p className="flex h-12 items-center rounded-app bg-surface px-4">
            Signature name: <strong className="ml-1">{signature}</strong>
            <span className="ml-2 text-meta text-fg-muted">(this view was logged)</span>
          </p>
        ) : (
          <button type="button" onClick={onReveal} className={appButtonClasses('secondary', 'h-12 px-5')}>
            Show signature name
          </button>
        )}
      </div>
      {card.is_guest_pass && search.join_qr && (
        <details className="rounded-app border border-border p-4">
          <summary className="cursor-pointer font-semibold text-fg">Convert to member</summary>
          <p className="mt-2 text-fg-muted">They scan this on their own phone, signed in to the same account, choose a membership and sign there. Then search for them here and record the payment. Their ID check carries over.</p>
          <img src={search.join_qr} alt={`QR code for ${search.join_url}`} width={180} height={180} className="mt-3 rounded-app border border-border bg-white p-2" />
        </details>
      )}
      {card.payments.length > 0 && (
        <section aria-label="Recent payments">
          <h3 className="mb-1 text-sm font-semibold text-fg-muted">Recent payments</h3>
          <ul className="divide-y divide-border rounded-app border border-border">
            {card.payments.map((payment) => (
              <li key={payment.id} className="flex min-h-14 flex-wrap items-center gap-3 px-4 py-2">
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold text-fg">
                    {payment.status_label} · {payment.method_label}
                  </span>
                  <span className="block text-meta text-fg-muted">{formatDay(payment.date)}</span>
                </span>
                <span className="font-semibold text-fg">{money(payment.amount)}</span>
                {payment.refundable && (
                  <button type="button" onClick={() => onOpen({ card, action: 'refund', paymentId: payment.id })} className={appButtonClasses('secondary', 'h-11 px-4')}>
                    Refund
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  )
}

/** An account with no membership: a team member, or someone the staff granted the feed to. */
function PersonCard({ person, onOpen }: { person: DoorPerson; onOpen: (dialog: Dialog) => void }) {
  const verify = person.actions.includes('verify')
  return (
    <article aria-labelledby={`person-${person.id}`} className={cn('flex flex-col gap-4 rounded-app border bg-canvas p-5', person.do_not_admit ? 'border-2 border-danger' : 'border-border')}>
      {person.do_not_admit && (
        <p role="alert" className="rounded-app bg-danger px-4 py-3 text-lg font-semibold text-white">
          Do not admit. Ask a member of the team.
        </p>
      )}
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold uppercase tracking-[0.06em] text-fg-muted">No membership</p>
          <h2 id={`person-${person.id}`} className="text-2xl font-semibold text-fg">
            {person.display_name}
            {person.is_you && <span className="ml-2 text-base font-normal text-fg-muted">(you)</span>}
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {person.team_account && <Chip>Team</Chip>}
          {person.feed_granted && <Chip tone={person.id_checked ? 'ok' : 'wait'}>{person.id_checked ? 'Feed granted' : 'Granted, awaiting ID check'}</Chip>}
          {person.id_checked ? <Chip tone="ok">ID verified</Chip> : <Chip tone="alert">ID check needed</Chip>}
        </div>
      </header>
      {verify ? (
        <button type="button" onClick={() => onOpen({ person, action: 'verify' })} className={appButtonClasses('primary', cn(BIG, 'w-full justify-start gap-3 sm:w-auto'))}>
          <BadgeCheck aria-hidden="true" className="size-5" />
          Record ID check
        </button>
      ) : (
        <button type="button" onClick={() => onOpen({ person, action: 'revoke' })} className={appButtonClasses('outline', 'h-12 self-start border-danger px-5 text-danger')}>
          Revoke ID check
        </button>
      )}
    </article>
  )
}

/**
 * The door desk for a tablet (1024×768) or a phone: search or scan a reference code, see
 * who it is and what they may do, and act with large buttons. The admin's door desk runs
 * the same code (apps.memberships.desk), with the same permissions and audit log.
 */
export function StaffDoorPage() {
  const toast = useToast()
  const inputId = useId()
  // The admin links here with ?q=<code> (a membership's row) or ?needs_id=1 (its card).
  const [params] = useSearchParams()
  const [typed, setTyped] = useState(params.get('q') ?? '')
  const [query, setQuery] = useState((params.get('q') ?? '').trim())
  const [needsId, setNeedsId] = useState(params.get('needs_id') === '1')
  const [version, setVersion] = useState(0)
  const [scanning, setScanning] = useState(false)
  const [dialog, setDialog] = useState<Dialog | null>(null)
  const [donation, setDonation] = useState(false)
  const [signatures, setSignatures] = useState<Record<number, string>>({})
  const results = useAsync(() => (needsId ? doorApi.search('', true) : query ? doorApi.search(query) : Promise.resolve(null)), `door:${needsId ? '!needs-id' : query}:${version}`)
  const search = results.status === 'success' ? results.data : null

  function find(value: string) {
    const next = value.trim()
    setTyped(next)
    setQuery(next)
    setNeedsId(false)
    setSignatures({})
  }

  function done(message: string) {
    setDialog(null)
    setDonation(false)
    toast.show({ tone: 'success', title: message })
    setVersion((n) => n + 1)
  }

  async function reveal(card: DoorCard) {
    try {
      const result = await doorApi.act({ action: 'show_signature', membership: card.id })
      if (result.signature) setSignatures((all) => ({ ...all, [card.id]: result.signature!.name }))
    } catch {
      toast.show({ tone: 'error', title: 'That did not work' })
    }
  }

  return (
    <StaffFrame title="Door desk" minimum="door" wide>
      <div className="flex flex-col gap-5">
        <p className="rounded-app bg-wait px-4 py-3 text-base font-semibold text-wait-fg">Check a valid photo ID showing 18+ before any first activation.</p>
        <form
          role="search"
          onSubmit={(event) => {
            event.preventDefault()
            find(typed)
          }}
          className="flex flex-col gap-2"
        >
          <label htmlFor={inputId} className="font-semibold text-fg">
            Reference code or display name
          </label>
          <div className="flex flex-wrap gap-3">
            <input
              id={inputId}
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              className="h-16 min-w-0 flex-[1_1_16rem] rounded-app border border-border bg-canvas px-4 text-2xl tracking-[0.08em] text-fg outline-none focus:border-fg"
            />
            <button type="submit" className={appButtonClasses('primary', 'h-16 px-7 text-lg')}>
              <Search aria-hidden="true" className="size-5" />
              Search
            </button>
            <button type="button" onClick={() => setScanning(true)} className={appButtonClasses('secondary', 'h-16 px-7 text-lg')}>
              <ScanLine aria-hidden="true" className="size-5" />
              Scan QR
            </button>
          </div>
        </form>
        {scanning && (
          <Scanner
            onClose={() => setScanning(false)}
            onCode={(code) => {
              setScanning(false)
              find(code)
            }}
          />
        )}
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            aria-pressed={needsId}
            onClick={() => {
              setNeedsId((on) => !on)
              setSignatures({})
            }}
            className={appButtonClasses(needsId ? 'primary' : 'secondary', 'h-12 px-5')}
          >
            <ListChecks aria-hidden="true" className="size-5" />
            Needs ID check
          </button>
          <button type="button" onClick={() => setDonation(true)} className={appButtonClasses('secondary', 'h-12 px-5')}>
            <HandHeart aria-hidden="true" className="size-5" />
            Record donation
          </button>
        </div>

        {!query && !needsId && (
          <div className="flex flex-col items-center gap-2 rounded-app border border-dashed border-border px-6 py-12 text-center">
            <Camera aria-hidden="true" className="size-10 text-fg-muted" strokeWidth={1.5} />
            <p className="text-lg font-semibold text-fg">Scan a code or type it in</p>
            <p className="max-w-[420px] text-fg-muted">Search by the reference code on the member’s phone, or by part of their display name.</p>
          </div>
        )}
        {(query || needsId) && results.status === 'loading' && <LoadingState label="Searching" />}
        {search?.needs_id && <h2 className="text-lg font-semibold text-fg">Waiting for an ID check</h2>}
        {results.status === 'error' && <ErrorState title="The search did not work" onRetry={results.retry} />}
        {search && search.results.length === 0 && search.people.length === 0 &&
          (search.needs_id ? (
            <EmptyState title="Nobody is waiting for an ID check" message="Everyone with a current membership or feed access has one on file." />
          ) : (
            <EmptyState title={`Nothing found for “${search.query}”`} message="Check the code, or try part of the display name." />
          ))}
        {search?.results.map((card) => (
          <ResultCard key={card.id} card={card} search={search} onOpen={setDialog} signature={signatures[card.id]} onReveal={() => void reveal(card)} />
        ))}
        {search?.people.map((person) => <PersonCard key={`person-${person.id}`} person={person} onOpen={setDialog} />)}
      </div>
      {dialog && search && <ActionDialog dialog={dialog} search={search} onClose={() => setDialog(null)} onDone={done} />}
      {donation && <DonationDialog search={search} onClose={() => setDonation(false)} onDone={done} />}
    </StaffFrame>
  )
}
