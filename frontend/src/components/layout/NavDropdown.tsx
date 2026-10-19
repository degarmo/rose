import { ChevronDown } from 'lucide-react'
import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { NavLink, useLocation } from 'react-router'
import { cn } from '@/lib/cn'
import type { NavGroup } from './navigation'

/**
 * A disclosure dropdown for the desktop navigation: a button that shows a
 * list of links. Enter, Space or Arrow Down open it and move to the first
 * link; Arrow keys, Home and End move between links; Escape closes it and
 * returns focus to the button. Leaving it with Tab or a click outside closes it.
 */
export function NavDropdown({ group }: { group: NavGroup }) {
  const { pathname } = useLocation()
  const [openOn, setOpenOn] = useState<string | null>(null)
  const open = openOn === pathname
  const listId = useId()
  const wrapper = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)
  const active = group.items.some((item) => pathname === item.to || pathname.startsWith(`${item.to}/`))

  useEffect(() => {
    if (!open) return
    function onPointer(event: PointerEvent) {
      if (!wrapper.current?.contains(event.target as Node)) setOpenOn(null)
    }
    document.addEventListener('pointerdown', onPointer)
    return () => document.removeEventListener('pointerdown', onPointer)
  }, [open])

  function links(): HTMLAnchorElement[] {
    return Array.from(wrapper.current?.querySelectorAll<HTMLAnchorElement>('a') ?? [])
  }

  function focusLink(index: number) {
    // The list renders on the next frame after opening.
    requestAnimationFrame(() => {
      const all = links()
      all[(index + all.length) % all.length]?.focus()
    })
  }

  function onButtonKey(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      setOpenOn(pathname)
      focusLink(0)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setOpenOn(pathname)
      focusLink(-1)
    } else if (event.key === 'Escape' && open) {
      setOpenOn(null)
    }
  }

  function onListKey(event: KeyboardEvent<HTMLUListElement>) {
    const all = links()
    const index = all.indexOf(document.activeElement as HTMLAnchorElement)
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      all[(index + 1) % all.length]?.focus()
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      all[(index - 1 + all.length) % all.length]?.focus()
    } else if (event.key === 'Home') {
      event.preventDefault()
      all[0]?.focus()
    } else if (event.key === 'End') {
      event.preventDefault()
      all[all.length - 1]?.focus()
    } else if (event.key === 'Escape') {
      event.preventDefault()
      setOpenOn(null)
      button.current?.focus()
    }
  }

  return (
    <div
      ref={wrapper}
      className="relative"
      onBlur={(event) => {
        if (!wrapper.current?.contains(event.relatedTarget as Node | null)) setOpenOn(null)
      }}
    >
      <button
        ref={button}
        type="button"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpenOn(open ? null : pathname)}
        onKeyDown={onButtonKey}
        className={cn(
          'inline-flex min-h-10 items-center gap-1 text-sm font-medium transition-colors duration-150',
          active ? 'text-link' : 'text-fg hover:text-link',
        )}
      >
        {group.label}
        <ChevronDown aria-hidden="true" strokeWidth={2} className={cn('size-3.5 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <ul
          id={listId}
          onKeyDown={onListKey}
          className="absolute -left-4 top-full mt-2 min-w-52 overflow-hidden rounded-sheet border border-border bg-canvas py-1 shadow-sheet"
        >
          {group.items.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                onClick={() => setOpenOn(null)}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-11 items-center px-4 text-sm font-medium hover:bg-surface focus-visible:bg-surface focus-visible:outline-none',
                    isActive ? 'text-link' : 'text-fg',
                  )
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
