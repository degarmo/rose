import { cn } from '@/lib/cn'
import { useAsync } from '@/lib/useAsync'

/** The member's reference code with a QR made on this device. Nothing is sent anywhere. */
export function ReferenceCode({ code, size = 'lg', className }: { code: string; size?: 'md' | 'lg'; className?: string }) {
  // Loaded on demand: only people with a code need the QR encoder.
  const qr = useAsync(
    () =>
      import('qrcode').then(({ default: QRCode }) =>
        QRCode.toString(code, { type: 'svg', margin: 1, errorCorrectionLevel: 'M', color: { dark: '#151012', light: '#f2e8da' } }),
      ),
    code,
  )
  return (
    <div className={cn('flex flex-col items-center gap-4 sm:flex-row sm:items-center', className)}>
      <div
        className={cn(
          'flex shrink-0 items-center justify-center overflow-hidden rounded-xl bg-fg p-2',
          size === 'lg' ? 'size-44' : 'size-32',
        )}
      >
        {qr.status === 'success' ? (
          <img src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(qr.data)}`} alt={`QR code for ${code}`} className="size-full" />
        ) : (
          <span aria-hidden="true" className="size-full animate-pulse rounded-lg bg-cream-300/40" />
        )}
      </div>
      <div className="text-center sm:text-left">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-fg-subtle">Reference code</p>
        <p className={cn('mt-1 font-mono tracking-[0.18em] text-fg', size === 'lg' ? 'text-4xl' : 'text-2xl')}>{code}</p>
      </div>
    </div>
  )
}
