import { MoreHorizontal } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { cn } from '@/lib/cn'

export interface MenuItem {
  label: string
  onSelect: () => void
  danger?: boolean
}

/** A small "more" menu. Closes on outside click, Escape and selection. */
export function OverflowMenu({ items, label }: { items: MenuItem[]; label: string }) {
  const [open, setOpen] = useState(false)
  const menuId = useId()
  const wrapper = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onPointer(event: PointerEvent) {
      if (!wrapper.current?.contains(event.target as Node)) setOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={wrapper} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
        className="-mr-2 inline-flex size-11 items-center justify-center rounded-full text-fg-muted hover:text-fg"
      >
        <MoreHorizontal aria-hidden="true" className="size-5" />
        <span className="sr-only">{label}</span>
      </button>
      {open && (
        <ul
          id={menuId}
          className="absolute right-0 top-full z-20 mt-1 w-52 overflow-hidden rounded-xl bg-surface-raised py-1 shadow-[var(--ig-shadow)] ring-1 ring-border"
        >
          {items.map((item) => (
            <li key={item.label}>
              <button
                type="button"
                onClick={() => {
                  setOpen(false)
                  item.onSelect()
                }}
                className={cn(
                  'flex min-h-11 w-full items-center px-4 text-left text-sm hover:bg-primary-deep',
                  item.danger ? 'text-danger' : 'text-fg',
                )}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
