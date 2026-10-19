import { EyeOff } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

/** A heavy blur over sensitive images until the viewer chooses to look. */
export function SensitiveBlur({ blurred, children }: { blurred: boolean; children: ReactNode }) {
  const [revealed, setRevealed] = useState(false)
  const hidden = blurred && !revealed
  return (
    <div className="relative size-full overflow-hidden">
      <div className={cn('size-full', hidden && 'pointer-events-none select-none blur-3xl saturate-50')} aria-hidden={hidden || undefined}>
        {children}
      </div>
      {hidden && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-ink-950/50 p-6 text-center">
          <EyeOff aria-hidden="true" className="size-6 text-white" />
          <p className="text-sm font-semibold text-white">Marked sensitive by the author</p>
          <button
            type="button"
            onClick={() => setRevealed(true)}
            className="min-h-11 rounded-lg border border-white/70 px-5 text-sm font-semibold text-white hover:bg-white/15"
          >
            View
          </button>
        </div>
      )}
    </div>
  )
}
