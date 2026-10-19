import { CircleAlert, CircleCheck, Info, X } from 'lucide-react'
import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import { cn } from '@/lib/cn'
import { ToastContext, type ToastInput, type ToastTone } from './toastContext'

interface ToastItem extends Required<Omit<ToastInput, 'message'>> {
  id: number
  message?: string
}

const DISMISS_AFTER_MS = 7000

const icons = { info: Info, success: CircleCheck, error: CircleAlert }
const accents: Record<ToastTone, string> = {
  info: 'text-link',
  success: 'text-link',
  error: 'text-danger',
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const show = useCallback(
    ({ tone = 'info', title, message }: ToastInput) => {
      const id = nextId.current++
      setToasts((current) => [...current.slice(-2), { id, tone, title, message }])
      window.setTimeout(() => dismiss(id), DISMISS_AFTER_MS)
    },
    [dismiss],
  )

  const value = useMemo(() => ({ show }), [show])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        role="status"
        className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-3 px-4 sm:bottom-6 sm:items-end sm:px-6"
      >
        {toasts.map((toast) => {
          const Icon = icons[toast.tone]
          return (
            <div
              key={toast.id}
              className="pointer-events-auto flex w-full max-w-sm animate-toast-in items-start gap-3 rounded-sheet border border-border bg-canvas p-4 shadow-sheet"
            >
              <Icon aria-hidden="true" className={cn('mt-0.5 size-5 shrink-0', accents[toast.tone])} />
              <div className="flex-1">
                <p className="text-sm font-semibold text-fg">{toast.title}</p>
                {toast.message && <p className="mt-1 text-sm text-fg-muted">{toast.message}</p>}
              </div>
              <button
                type="button"
                onClick={() => dismiss(toast.id)}
                className="-m-2 inline-flex size-9 items-center justify-center rounded-full text-fg-muted hover:text-fg"
              >
                <X aria-hidden="true" className="size-4" />
                <span className="sr-only">Dismiss</span>
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}
