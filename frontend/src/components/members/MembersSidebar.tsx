import { Globe, Heart, House, LogOut, ScrollText, Search, Settings, SquarePlus, SunMoon, UserRound, type LucideIcon } from 'lucide-react'
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { cn } from '@/lib/cn'
import type { Me } from '@/lib/membersApi'
import { leaveNow, quickExitUrl } from '@/lib/quickExit'
import { APPEARANCE_LABELS, type Appearance } from './appearance'
import { Avatar } from './Avatar'

/** Space the fixed sidebar takes on the left: labels from 1264px (the wide breakpoint), an icon rail below that. */
export const SIDEBAR_OFFSET = 'pl-14 md:pl-[73px] wide:pl-[245px]'

const row =
  'group flex min-h-12 w-full items-center justify-center gap-4 rounded-lg p-2 text-[0.95rem] text-fg transition-colors hover:bg-primary-deep disabled:cursor-not-allowed disabled:opacity-40 md:p-3 wide:justify-start'

/** Visible beside the icon from 1264px; below that the rail shows icons and the name is for screen readers. */
function Label({ children, bold }: { children: ReactNode; bold?: boolean }) {
  return (
    <>
      <span className={cn('hidden wide:inline', bold && 'font-bold')}>{children}</span>
      <span className="sr-only wide:hidden">{children}</span>
    </>
  )
}

function Icon({ icon: Glyph, active }: { icon: LucideIcon; active: boolean }) {
  return <Glyph aria-hidden="true" className="size-6 shrink-0 transition-transform group-hover:scale-105" strokeWidth={active ? 2.6 : 1.9} />
}

function Item({ to, label, icon, end, badge }: { to: string; label: string; icon: LucideIcon; end?: boolean; badge?: number }) {
  return (
    <NavLink to={to} end={end} title={label} className={row}>
      {({ isActive }) => (
        <>
          <span className="relative shrink-0">
            <Icon icon={icon} active={isActive} />
            {badge ? (
              <span
                aria-hidden="true"
                className="absolute -right-2 -top-1.5 min-w-[1.125rem] rounded-full bg-rose px-1 text-center text-[0.65rem] font-semibold leading-[1.125rem] text-white ring-2 ring-canvas"
              >
                {badge > 9 ? '9+' : badge}
              </span>
            ) : null}
          </span>
          <Label bold={isActive}>{label}</Label>
          {badge ? <span className="sr-only">, {badge} unread</span> : null}
        </>
      )}
    </NavLink>
  )
}

function leave(event: { preventDefault: () => void }) {
  event.preventDefault()
  leaveNow()
}

const menuRow = 'flex min-h-12 w-full items-center gap-3 rounded-md px-4 text-left text-sm text-fg hover:bg-primary-deep'

/** Settings with a gear at the bottom left. The menu opens upwards. */
function SettingsMenu({ me, appearance, onAppearance }: { me: Me; appearance: Appearance; onAppearance: () => void }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  // The menu belongs to the page it was opened on, so any navigation closes it.
  const [openOn, setOpenOn] = useState<string | null>(null)
  const open = openOn === pathname
  const menuId = useId()
  const wrapper = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    function onPointer(event: PointerEvent) {
      if (!wrapper.current?.contains(event.target as Node)) setOpenOn(null)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpenOn(null)
        button.current?.focus()
      }
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
        ref={button}
        type="button"
        aria-expanded={open}
        aria-controls={menuId}
        title="Settings"
        onClick={() => setOpenOn(open ? null : pathname)}
        className={row}
      >
        <Icon icon={Settings} active={open} />
        <Label bold={open}>Settings</Label>
      </button>
      {open && (
        <div id={menuId} className="absolute bottom-full left-0 z-40 mb-2 w-64 rounded-2xl bg-surface-raised p-2 shadow-[var(--ig-shadow)] ring-1 ring-border">
          <p className="truncate px-4 pb-1 pt-2 text-xs text-fg-muted">{me.handle}</p>
          <ul>
            <li>
              <Link to="/account" className={menuRow}>
                <UserRound aria-hidden="true" className="size-5" />
                Your account
              </Link>
            </li>
            <li>
              <button type="button" className={menuRow} onClick={onAppearance}>
                <SunMoon aria-hidden="true" className="size-5" />
                Appearance: {APPEARANCE_LABELS[appearance]}
              </button>
            </li>
            <li>
              <Link to="/members/join-feed?guidelines=1" className={menuRow}>
                <ScrollText aria-hidden="true" className="size-5" />
                Community guidelines
              </Link>
            </li>
            <li>
              <Link to="/" className={menuRow}>
                <Globe aria-hidden="true" className="size-5" />
                Back to the website
              </Link>
            </li>
          </ul>
          <div className="mt-1 border-t border-border pt-1">
            <button
              type="button"
              className={menuRow}
              onClick={async () => {
                setOpenOn(null)
                await auth.logout()
                navigate('/', { replace: true })
              }}
            >
              Log out
            </button>
            <a href={quickExitUrl()} onClick={leave} rel="noreferrer" className={cn(menuRow, 'font-semibold text-rose')}>
              Leave this site now
            </a>
          </div>
        </div>
      )}
    </div>
  )
}

interface MembersSidebarProps {
  me: Me
  onCreate: () => void
  appearance: Appearance
  onAppearance: () => void
}

/** The members area's left sidebar: logo, Leave, the main places, then profile and settings at the bottom. */
export function MembersSidebar({ me, onCreate, appearance, onAppearance }: MembersSidebarProps) {
  const profile = `/members/u/${encodeURIComponent(me.handle)}`
  return (
    <nav
      aria-label="Members"
      className="fixed inset-y-0 left-0 z-30 flex w-14 flex-col border-r border-border bg-canvas px-1 pb-3 md:w-[73px] md:px-3 wide:w-[245px] print:hidden"
    >
      <Link
        to="/members/feed"
        className="flex min-h-12 items-center justify-center pb-3 pt-6 wide:justify-start wide:px-3 wide:pt-8"
      >
        <span aria-hidden="true" className="hidden font-script text-[1.9rem] leading-none text-fg wide:inline">
          Rose
        </span>
        <span
          aria-hidden="true"
          className="inline-flex size-9 items-center justify-center rounded-lg border-2 border-fg font-script text-xl leading-none text-fg wide:hidden"
        >
          R
        </span>
        <span className="sr-only">Feed home</span>
      </Link>

      <ul className="-mx-1 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-1 py-2 md:-mx-3 md:px-3">
        <li className="mb-1">
          {/* The quick exit stays in view on every page and at every width. */}
          <a
            href={quickExitUrl()}
            onClick={leave}
            rel="noreferrer"
            title="Leave this site now. Shortcut: press Esc twice."
            className={cn(row, 'font-semibold text-rose')}
          >
            <LogOut aria-hidden="true" className="size-6 shrink-0" strokeWidth={2.2} />
            <Label>Leave</Label>
            <span className="sr-only"> this site now. Shortcut: press Escape twice.</span>
          </a>
        </li>
        <li>
          <Item to="/members/feed" label="Home" icon={House} />
        </li>
        <li>
          <Item to="/members/directory" label="Search" icon={Search} />
        </li>
        <li>
          <button
            type="button"
            onClick={onCreate}
            disabled={!me.can_post}
            title={me.can_post ? 'New post' : 'Posting is paused on your account'}
            className={row}
          >
            <Icon icon={SquarePlus} active={false} />
            <Label>Create</Label>
          </button>
        </li>
        <li>
          <Item to="/members/notifications" label="Notifications" icon={Heart} badge={me.unread_notifications} />
        </li>
        <li>
          <NavLink to={profile} title="Profile" className={row}>
            {({ isActive }) => (
              <>
                <span aria-hidden="true" className={cn('inline-flex shrink-0 rounded-full', isActive && 'ring-2 ring-fg ring-offset-1 ring-offset-canvas')}>
                  <Avatar member={me} size="xs" />
                </span>
                <Label bold={isActive}>Profile</Label>
              </>
            )}
          </NavLink>
        </li>
      </ul>

      <SettingsMenu me={me} appearance={appearance} onAppearance={onAppearance} />
    </nav>
  )
}
