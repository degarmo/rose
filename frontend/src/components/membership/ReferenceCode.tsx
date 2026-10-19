import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'
import { useAsync } from '@/lib/useAsync'

interface ReferenceCodeProps {
  code: string
  /** `lg` is the confirmation's door reference; `md` sits inside the account's membership card. */
  size?: 'md' | 'lg'
  /** Lines under the QR, e.g. the tier and how long the code is good for. */
  children?: ReactNode
  className?: string
}

/**
 * The door reference (design: "Join step 3", "Door reference"): a blush card with the code in
 * Fraunces and a QR made on this device. Nothing is sent anywhere.
 */
export function ReferenceCode({ code, size = 'lg', children, className }: ReferenceCodeProps) {
  // Loaded on demand: only people with a code need the QR encoder.
  const qr = useAsync(
    () =>
      import('qrcode').then(({ default: QRCode }) =>
        QRCode.toString(code, { type: 'svg', margin: 0, errorCorrectionLevel: 'M', color: { dark: '#262626', light: '#ffffff' } }),
      ),
    code,
  )
  const lg = size === 'lg'
  return (
    <div
      className={cn(
        'flex w-full flex-col items-center border border-border bg-blush text-center',
        lg ? 'gap-4 rounded-panel px-5 py-7 lg:max-w-[400px] lg:gap-6 lg:rounded-[24px] lg:p-10' : 'gap-4 rounded-card px-5 py-6 sm:max-w-[360px]',
        className,
      )}
    >
      <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-fg-muted-tint lg:text-xs">Door reference</p>
      <p className={cn('font-display leading-none tracking-[0.06em] text-fg', lg ? 'text-[2.125rem] lg:text-[2.75rem]' : 'text-[2rem]')}>{code}</p>
      {/* Always dark on white, in either appearance, so door scanners can read it. */}
      <div
        className={cn(
          'flex shrink-0 items-center justify-center rounded-field border border-border bg-white',
          lg ? 'size-[200px] p-3.5 lg:size-[220px] lg:p-4' : 'size-40 p-3',
        )}
      >
        {qr.status === 'success' ? (
          <img src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(qr.data)}`} alt={`QR code for ${code}`} className="size-full" />
        ) : (
          <span aria-hidden="true" className="size-full animate-pulse rounded-lg bg-control" />
        )}
      </div>
      {children && <div className={cn('text-fg-muted-tint', lg ? 'text-xs lg:text-[0.8125rem]' : 'text-[0.8125rem]')}>{children}</div>}
    </div>
  )
}
