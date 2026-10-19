import { Banknote, Globe, Mail, MapPin, type LucideIcon } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { Button, Card, Checkbox, FormField, Input, Section, useToast } from '@/components/ui'
import { api, ApiError, type DonationOptions } from '@/lib/api'
import { cn } from '@/lib/cn'
import { formatMoney } from '@/lib/format'
import { goTo } from '@/lib/membershipApi'
import { usePageContent, type PageCopy } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { amountError, parseAmount } from './donationAmount'
import { SentPanel } from './SentPanel'

const CUSTOM = 'custom'

export function DonationForm({ options }: { options: DonationOptions }) {
  const auth = useAuth()
  const toast = useToast()
  const [choice, setChoice] = useState<string>(String(options.presets_cents[1] ?? options.presets_cents[0] ?? CUSTOM))
  const [custom, setCustom] = useState('')
  const [email, setEmail] = useState('')
  const [showName, setShowName] = useState(false)
  const [website, setWebsite] = useState('')
  const [error, setError] = useState<string | undefined>()
  const [busy, setBusy] = useState(false)

  const cents = choice === CUSTOM ? parseAmount(custom) : Number(choice)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const problem = amountError(cents, options.minimum_cents, options.maximum_cents)
    setError(problem)
    if (problem || cents === null) {
      if (choice === CUSTOM) document.querySelector<HTMLInputElement>('input[name="custom_amount"]')?.focus()
      return
    }
    setBusy(true)
    try {
      const { redirect_url } = await api.startDonation({ amount_cents: cents, email, show_name: showName, website })
      goTo(redirect_url)
    } catch (caught) {
      const message =
        caught instanceof ApiError && caught.fieldErrors.email
          ? caught.fieldErrors.email
          : caught instanceof Error
            ? caught.message
            : 'Please try again.'
      toast.show({ tone: 'error', title: 'Your gift did not go through', message })
      setBusy(false)
    }
  }

  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-5" aria-label="Give online">
      <fieldset>
        <legend className="mb-2 text-sm font-semibold text-fg">Amount</legend>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {[...options.presets_cents.map(String), CUSTOM].map((value) => (
            <label
              key={value}
              className={cn(
                'flex h-[72px] cursor-pointer items-center justify-center rounded-card border-[1.5px] font-display text-fg transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-link',
                value === CUSTOM ? 'text-[1.375rem]' : 'text-[1.75rem]',
                choice === value ? 'border-primary bg-tier-selected' : 'border-border bg-canvas hover:border-fg-muted',
              )}
            >
              <input
                type="radio"
                name="amount"
                value={value}
                checked={choice === value}
                onChange={() => {
                  setChoice(value)
                  setError(undefined)
                }}
                className="sr-only"
              />
              {value === CUSTOM ? 'Other' : formatMoney(Number(value))}
            </label>
          ))}
        </div>
      </fieldset>
      {choice === CUSTOM && (
        <FormField label="Your amount, in dollars" hint={`At least ${formatMoney(options.minimum_cents)}.`} error={error} required>
          {(field) => (
            <Input
              {...field}
              name="custom_amount"
              inputMode="decimal"
              autoComplete="off"
              value={custom}
              onChange={(event) => {
                setCustom(event.target.value)
                setError(undefined)
              }}
            />
          )}
        </FormField>
      )}
      {choice !== CUSTOM && error && <p className="text-[0.8125rem] text-danger">{error}</p>}
      <FormField label="Email for an acknowledgement" hint="Only if you would like one for your records. We forget it once it is sent.">
        {(field) => (
          <Input
            {...field}
            name="email"
            type="email"
            inputMode="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        )}
      </FormField>
      {auth.user && (
        <Checkbox
          name="show_name"
          label={`Record this gift under my display name (${auth.user.display_name})`}
          hint="Off means it is recorded as Anonymous. Either way, no list of donors is ever published."
          checked={showName}
          onChange={(event) => setShowName(event.target.checked)}
        />
      )}
      {/* Honeypot: hidden from people and assistive tech, tempting to bots. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label>
          Website
          <input type="text" name="website" tabIndex={-1} autoComplete="off" value={website} onChange={(event) => setWebsite(event.target.value)} />
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <Button type="submit" size="lg" disabled={busy} aria-busy={busy}>
          {busy ? 'Opening checkout' : cents && !amountError(cents, options.minimum_cents, options.maximum_cents) ? `Give ${formatMoney(cents)}` : 'Give'}
        </Button>
        <p className="text-[0.8125rem] text-fg-muted">You finish on a secure checkout page. Card details never touch this site.</p>
      </div>
    </form>
  )
}

function Way({ icon: Icon, copy, k, children }: { icon: LucideIcon; copy: PageCopy; k: string; children?: ReactNode }) {
  return (
    <Card className="h-full p-5 lg:p-6">
      <Icon aria-hidden="true" className="size-6 text-link" strokeWidth={1.5} />
      <Copy copy={copy} k={`${k}.title`} as="h3" className="mt-4 text-xl text-fg lg:text-card-title" />
      <Copy copy={copy} k={`${k}.body`} lines={3} className="mt-2 text-sm text-fg-muted" />
      {children}
    </Card>
  )
}

/** Donate (no design: amounts chosen like the Join tiers, the thanks like Contact's confirmation). */
export function DonatePage() {
  useDocumentMeta({
    title: 'Donate',
    description: 'What donations pay for, and how to give: at the door, by check or online.',
  })
  const copy = usePageContent('donate')
  const [params] = useSearchParams()
  const options = useAsync(() => api.donationOptions(), 'donation-options')
  const funds = copy.status === 'loading' ? [1, 2, 3, 4, 5] : copy.items('funds')

  return (
    <>
      <PageHero copy={copy} image="home-closing.webp" placeholder="rose">
        {options.status === 'success' && options.data.nonprofit_status && (
          <p className="text-sm text-fg-muted">{options.data.nonprofit_status}</p>
        )}
      </PageHero>

      {params.get('thanks') === '1' && (
        <Section width="narrow" spacing="tight" aria-label="Thank you">
          <SentPanel title="Thank you for your gift.">
            It is recorded once the payment provider confirms it. If you asked for an acknowledgement, it will arrive by email.
          </SentPanel>
        </Section>
      )}
      {params.get('cancelled') === '1' && (
        <Section width="narrow" spacing="tight" aria-label="Checkout cancelled">
          <p role="status" className="rounded-card bg-blush p-5 text-center text-sm text-fg-muted-tint">
            Checkout was cancelled and nothing was charged.
          </p>
        </Section>
      )}

      <Section aria-labelledby="funds">
        <CopyHeading copy={copy} prefix="funds" id="funds" />
        <ul className="mt-8 grid gap-6 sm:grid-cols-2 lg:mt-10 lg:grid-cols-5">
          {funds.map((n) => (
            <li key={n} className="border-t border-border pt-5">
              <Copy copy={copy} k={`funds.${n}.title`} as="h3" className="text-xl text-fg" />
              <Copy copy={copy} k={`funds.${n}.body`} lines={2} className="mt-2 text-sm text-fg-muted" />
            </li>
          ))}
        </ul>
      </Section>

      <Section tone="surface" aria-labelledby="ways">
        <CopyHeading copy={copy} prefix="ways" id="ways" />
        <div className="mt-8 grid gap-4 md:grid-cols-3 lg:mt-10 lg:gap-6">
          <Way icon={Banknote} copy={copy} k="ways.door" />
          <Way icon={Mail} copy={copy} k="ways.check">
            {options.status === 'success' && (options.data.check_payable_to || options.data.mailing_address) && (
              <dl className="mt-4 space-y-3 text-sm">
                {options.data.check_payable_to && (
                  <div>
                    <dt className="text-fg-muted">Payable to</dt>
                    <dd className="text-fg">{options.data.check_payable_to}</dd>
                  </div>
                )}
                {options.data.mailing_address && (
                  <div>
                    <dt className="flex items-center gap-2 text-fg-muted">
                      <MapPin aria-hidden="true" className="size-3.5" />
                      Mail to
                    </dt>
                    <dd className="whitespace-pre-line text-fg">{options.data.mailing_address}</dd>
                  </div>
                )}
              </dl>
            )}
          </Way>
          <Way icon={Globe} copy={copy} k="ways.online" />
        </div>
      </Section>

      <Section aria-labelledby="give">
        <div className="grid gap-8 lg:grid-cols-2 lg:gap-24">
          <CopyHeading copy={copy} prefix="form" id="give" />
          <div className="w-full lg:max-w-[520px]">
            {options.status === 'loading' && <LoadingState label="Loading ways to give" />}
            {options.status === 'error' && <ErrorState title="Giving options did not load" onRetry={options.retry} />}
            {options.status === 'success' &&
              (options.data.online ? (
                <DonationForm options={options.data} />
              ) : (
                <p className="rounded-card bg-surface p-5 text-fg-muted">
                  Online giving is not open yet. You can give in person at the door or by check, as above.
                </p>
              ))}
          </div>
        </div>
      </Section>
    </>
  )
}
