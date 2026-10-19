import { EyeOff } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

/**
 * A heavy blur over sensitive images until the viewer chooses to look. The blurred
 * picture is inert, so nothing inside it can be focused or read out, and a veil in the
 * page colour keeps the notice readable on any photograph.
 */
export function SensitiveBlur({ blurred, children }: { blurred: boolean; children: ReactNode }) {
  const [revealed, setRevealed] = useState(false)
  const hidden = blurred && !revealed
  return (
    <div className="relative size-full overflow-hidden">
      <div className={cn('size-full', hidden && 'pointer-events-none scale-110 select-none blur-[28px]')} inert={hidden || undefined}>
        {children}
      </div>
      {hidden && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2.5 bg-canvas/55 p-6 text-center text-fg">
          <EyeOff aria-hidden="true" className="size-7" strokeWidth={1.6} />
          <p className="text-base font-semibold">Sensitive content</p>
          <p className="max-w-60 text-fg-muted">This post was marked sensitive by its author.</p>
          <button
            type="button"
            onClick={() => setRevealed(true)}
            className="mt-1.5 h-8 rounded-app border border-fg px-4 text-sm font-semibold hover:bg-fg/5"
          >
            View
          </button>
        </div>
      )}
    </div>
  )
}
