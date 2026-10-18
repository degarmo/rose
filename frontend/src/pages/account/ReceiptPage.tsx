import { ArrowLeft, Printer } from 'lucide-react'
import { Navigate, useParams } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { Button, ButtonLink, Section } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { formatDay, formatMoney } from '@/lib/format'
import { membershipApi } from '@/lib/membershipApi'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '../NotFoundPage'

/** A neutral, printable receipt: merchant name, date, amount, reference and "Membership". */
export default function ReceiptPage() {
  useDocumentMeta({ title: 'Receipt', noindex: true })
  const auth = useAuth()
  const { id = '' } = useParams()
  const signedIn = Boolean(auth.user)
  const receipt = useAsync(() => (signedIn ? membershipApi.receipt(id) : Promise.resolve(null)), `${id}:${signedIn}`)

  if (auth.status === 'loading') return <Section className="pt-32"><LoadingState label="Loading" /></Section>
  if (!auth.user) return <Navigate to={`/account/login?next=${encodeURIComponent(`/account/receipts/${id}`)}`} replace />
  if (receipt.status === 'error' && receipt.error instanceof ApiError && receipt.error.isNotFound) return <NotFoundPage />

  return (
    <Section className="pt-32 print:bg-white print:pt-0" width="narrow">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3 print:hidden">
        <ButtonLink to="/account#membership" variant="link">
          <ArrowLeft aria-hidden="true" className="size-4" />
          My account
        </ButtonLink>
        <Button variant="ghost" onClick={() => window.print()} disabled={receipt.status !== 'success'}>
          <Printer aria-hidden="true" className="size-4" />
          Print
        </Button>
      </div>
      {receipt.status === 'loading' && <LoadingState label="Loading receipt" />}
      {receipt.status === 'error' && <ErrorState title="This receipt did not load" onRetry={receipt.retry} />}
      {receipt.status === 'success' && receipt.data && (
        <article
          aria-labelledby="receipt-title"
          className="receipt rounded-2xl border border-border bg-surface p-6 sm:p-10 print:rounded-none print:border-0 print:bg-white print:p-0 print:text-black"
        >
          <header className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-6 print:border-black/30">
            <div>
              <h1 id="receipt-title" className="text-4xl text-fg print:text-black">
                {receipt.data.kind === 'Refund' ? 'Refund receipt' : receipt.data.title}
              </h1>
              <p className="mt-2 text-lg text-fg-muted print:text-black">{receipt.data.merchant}</p>
            </div>
            <p className="text-right text-fg-muted print:text-black">
              <time dateTime={receipt.data.date}>{formatDay(receipt.data.date)}</time>
            </p>
          </header>
          <dl className="mt-6 grid gap-5 sm:grid-cols-2">
            {[
              ['Description', receipt.data.description],
              ['Reference', receipt.data.reference],
              ['Payment method', receipt.data.method],
              [receipt.data.kind === 'Refund' ? 'Amount refunded' : 'Amount paid', formatMoney(receipt.data.amount_cents, receipt.data.currency)],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle print:text-black/60">{label}</dt>
                <dd className="mt-1 text-xl text-fg print:text-black">{value}</dd>
              </div>
            ))}
          </dl>
        </article>
      )}
    </Section>
  )
}
