import { EyeOff } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

/** A heavy blur over sensitive images until the viewer chooses to look. */
export function SensitiveBlur({ blurred, children }: { blurred: boolean; children: ReactNode }) {
  const [revealed, setRevealed] = useState(false)
  const hidden = blurred && !revealed
  return (
    <div className="relative overflow-hidden rounded-xl">
      <div className={cn(hidden && 'pointer-events-none select-none blur-3xl saturate-50')} aria-hidden={hidden || undefined}>
        {children}
      </div>
      {hidden && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-ink-950/50 p-6 text-center">
          <EyeOff aria-hidden="true" className="size-6 text-highlight" />
          <p className="text-sm text-fg">Marked sensitive by the author</p>
          <button
            type="button"
            onClick={() => setRevealed(true)}
            className="min-h-11 rounded-full border border-highlight/60 px-5 text-sm text-fg hover:bg-primary"
          >
            View
          </button>
        </div>
      )}
    </div>
  )
}
