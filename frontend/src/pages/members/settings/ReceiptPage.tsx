import { Printer } from 'lucide-react'
import { useParams } from 'react-router'
import { PhoneBar } from '@/components/members/app/Nav'
import { AppButton } from '@/components/members/app/primitives'
import { LoadError, Skeleton } from '@/components/members/settings/ui'
import { ApiError } from '@/lib/api'
import { formatDay, formatMoney } from '@/lib/format'
import { membershipApi } from '@/lib/membershipApi'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '@/pages/NotFoundPage'

/** A neutral, printable receipt: merchant name, date, amount, reference and "Membership". */
export function ReceiptPage() {
  useDocumentMeta({ title: 'Receipt', noindex: true })
  const { id = '' } = useParams()
  const receipt = useAsync(() => membershipApi.receipt(id), `receipt:${id}`)
  if (receipt.status === 'error' && receipt.error instanceof ApiError && receipt.error.isNotFound) return <NotFoundPage />

  return (
    <>
      <PhoneBar back="/members/settings/membership" title={<h1 className="truncate">Receipt</h1>} />
      <div className="mx-auto w-full max-w-[600px] px-4 pb-12 pt-3 md:pt-10 print:max-w-none print:p-0">
        <div className="mb-4 flex items-center justify-between gap-3 print:hidden">
          <h1 className="hidden text-xl font-semibold text-fg md:block">Receipt</h1>
          <AppButton variant="secondary" onClick={() => window.print()} disabled={receipt.status !== 'success'} className="ml-auto">
            <Printer aria-hidden="true" className="size-4" />
            Print
          </AppButton>
        </div>
        {receipt.status === 'loading' && (
          <div className="rounded-app border border-border p-6">
            <Skeleton lines={5} />
          </div>
        )}
        {receipt.status === 'error' && <LoadError title="This receipt did not load" onRetry={receipt.retry} />}
        {receipt.status === 'success' && (
          <article aria-labelledby="receipt-title" className="receipt rounded-app border border-border bg-canvas p-6 print:border-0 print:p-0 print:text-black">
            <header className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
              <div>
                <h2 id="receipt-title" className="text-xl font-semibold text-fg print:text-black">
                  {receipt.data.kind === 'Refund' ? 'Refund receipt' : receipt.data.title}
                </h2>
                <p className="mt-1 text-fg-muted print:text-black">{receipt.data.merchant}</p>
              </div>
              <time dateTime={receipt.data.date} className="text-fg-muted print:text-black">
                {formatDay(receipt.data.date)}
              </time>
            </header>
            <ul className="mt-2">
              {[
                ['Description', receipt.data.description],
                ['Reference', receipt.data.reference],
                ['Payment method', receipt.data.method],
                [receipt.data.kind === 'Refund' ? 'Amount refunded' : 'Amount paid', formatMoney(receipt.data.amount_cents, receipt.data.currency)],
              ].map(([label, value]) => (
                <li key={label} className="flex min-h-12 items-center justify-between gap-4 border-b border-border py-2 last:border-b-0">
                  <span className="text-fg-muted print:text-black/60">{label}</span>
                  <span className="text-right font-semibold text-fg print:text-black">{value}</span>
                </li>
              ))}
            </ul>
          </article>
        )}
      </div>
    </>
  )
}
