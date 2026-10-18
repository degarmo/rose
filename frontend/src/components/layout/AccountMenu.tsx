import { ChevronDown, LogOut, User } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { cn } from '@/lib/cn'
import { useAuth } from './authContext'

/** Log in link, or the signed-in person's display name with a small menu. */
export function AccountMenu({ className }: { className?: string }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [openOn, setOpenOn] = useState<string | null>(null)
  const open = openOn === pathname
  const menuId = useId()
  const wrapper = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onPointer(event: PointerEvent) {
      if (!wrapper.current?.contains(event.target as Node)) setOpenOn(null)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpenOn(null)
    }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  if (auth.status === 'loading') return <span className={cn('inline-block w-24', className)} aria-hidden="true" />

  if (!auth.user) {
    return (
      <Link
        to={`/account/login?next=${encodeURIComponent(pathname)}`}
        className={cn('inline-flex min-h-11 items-center gap-2 px-3 text-sm text-fg-muted hover:text-fg', className)}
      >
        <User aria-hidden="true" className="size-4" />
        Log in
      </Link>
    )
  }

  return (
    <div ref={wrapper} className={cn('relative', className)}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpenOn(open ? null : pathname)}
        className="inline-flex min-h-11 max-w-48 items-center gap-2 rounded-full px-3 text-sm text-fg hover:text-accent"
      >
        <User aria-hidden="true" className="size-4 shrink-0 text-highlight" />
        <span className="truncate">{auth.user.display_name}</span>
        <ChevronDown aria-hidden="true" className="size-4 shrink-0" />
      </button>
      {open && (
        <ul
          id={menuId}
          className="absolute right-0 top-full mt-2 w-48 overflow-hidden rounded-xl border border-border-strong bg-surface-raised py-1 shadow-2xl shadow-black/50"
        >
          <li>
            <Link to="/account" className="flex min-h-11 items-center gap-2 px-4 text-sm text-fg hover:bg-primary-deep">
              <User aria-hidden="true" className="size-4 text-highlight" />
              My account
            </Link>
          </li>
          <li>
            <button
              type="button"
              onClick={async () => {
                setOpenOn(null)
                await auth.logout()
                navigate('/', { replace: true })
              }}
              className="flex min-h-11 w-full items-center gap-2 px-4 text-sm text-fg hover:bg-primary-deep"
            >
              <LogOut aria-hidden="true" className="size-4 text-highlight" />
              Log out
            </button>
          </li>
        </ul>
      )}
    </div>
  )
}
