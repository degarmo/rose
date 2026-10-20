import { ChevronDown } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { cn } from '@/lib/cn'
import { memberAppPath } from '@/lib/memberApp'
import { ROLE_LABELS } from '@/lib/safetyApi'

const ITEM = 'flex min-h-10 items-center px-4 text-sm font-medium text-fg hover:bg-surface'
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

  const staff = auth.user?.staff ?? null
  if (auth.status === 'loading') return <span className={cn('inline-block w-12', className)} aria-hidden="true" />

  if (!auth.user) {
    return (
      <Link
        to={`/account/login?next=${encodeURIComponent(pathname)}`}
        className={cn('inline-flex min-h-10 items-center text-sm font-semibold text-fg hover:text-link', className)}
      >
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
        className="inline-flex min-h-10 max-w-48 items-center gap-1 text-sm font-semibold text-fg hover:text-link"
      >
        <span className="truncate">{auth.user.display_name}</span>
        <ChevronDown aria-hidden="true" strokeWidth={2} className="size-3.5 shrink-0" />
      </button>
      {open && (
        <ul
          id={menuId}
          className="absolute right-0 top-full mt-2 w-60 overflow-hidden rounded-sheet border border-border bg-canvas py-1 shadow-sheet"
        >
          {staff ? (
            <li className="border-b border-border pb-1">
              <p className="flex items-center gap-2 px-4 pb-1 pt-2 text-xs text-fg-muted">
                <span className="rounded-full bg-fg px-2 py-0.5 font-semibold uppercase tracking-[0.06em] text-canvas">Staff</span>
                {staff.role ? ROLE_LABELS[staff.role] : 'Door desk'}
              </p>
              <ul aria-label="Staff">
                {staff.door_desk && (
                  <li>
                    <Link to="/members/staff/door" reloadDocument className={ITEM}>
                      Door desk
                    </Link>
                  </li>
                )}
                {staff.role && (
                  <>
                    <li>
                      {/* The admin dashboard: the only one. */}
                      <a href={staff.admin_url} className={ITEM}>
                        Dashboard
                      </a>
                    </li>
                    <li>
                      <Link to="/members/staff/reports" className={ITEM}>
                        Reports
                      </Link>
                    </li>
                  </>
                )}
                <li>
                  <Link to={memberAppPath(auth.user)} className={ITEM}>
                    Member app
                  </Link>
                </li>
                <li>
                  <Link to="/" className={ITEM}>
                    Website
                  </Link>
                </li>
              </ul>
            </li>
          ) : (
            <li>
              <Link to={memberAppPath(auth.user)} className="flex min-h-11 items-center px-4 text-sm font-semibold text-link hover:bg-surface">
                Member app
              </Link>
            </li>
          )}
          <li>
            <Link to="/members/settings" className="flex min-h-11 items-center px-4 text-sm font-medium text-fg hover:bg-surface">
              Settings
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
              className="flex min-h-11 w-full items-center px-4 text-sm font-medium text-fg hover:bg-surface"
            >
              Log out
            </button>
          </li>
        </ul>
      )}
    </div>
  )
}
