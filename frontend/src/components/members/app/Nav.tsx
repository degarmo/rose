import { Compass, Globe, Heart, House, LogOut, Menu, Moon, Search, Settings, SquarePlus, type LucideIcon } from 'lucide-react'
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { chooseAppearance } from '@/lib/appearance'
import { cn } from '@/lib/cn'
import type { Me } from '@/lib/membersApi'
import { leaveNow, quickExitUrl } from '@/lib/quickExit'
import { Avatar } from '../Avatar'
import { profilePath } from './postUtils'
import { RoseMark, Wordmark } from './primitives'
import { ICON } from './ui'

export type Panel = 'search' | 'notifications' | null

function leave(event: { preventDefault: () => void }) {
  event.preventDefault()
  leaveNow()
}

/** 48px rows with a 12px gap; labels from 1264px unless a panel has collapsed the sidebar. */
function rowClass(collapsed: boolean, tone = 'text-fg') {
  return cn(
    'group flex h-12 w-full items-center gap-3 rounded-lg p-3 text-[0.95rem] transition-colors duration-150 ease-out hover:bg-surface disabled:cursor-not-allowed disabled:opacity-40',
    tone,
    !collapsed && 'wide:my-0.5',
  )
}

function Label({ children, active, collapsed }: { children: ReactNode; active: boolean; collapsed: boolean }) {
  return (
    <>
      <span className={cn('hidden', !collapsed && 'wide:inline', active && 'font-semibold')}>{children}</span>
      <span className={cn('sr-only', !collapsed && 'wide:hidden')}>{children}</span>
    </>
  )
}

function Glyph({ icon: Icon, active }: { icon: LucideIcon; active: boolean }) {
  return (
    <Icon
      aria-hidden="true"
      size={ICON.size}
      strokeWidth={active ? ICON.activeStroke : ICON.stroke}
      className="shrink-0 transition-transform duration-150 ease-out group-hover:scale-105"
    />
  )
}

function UnreadBadge({ count }: { count: number }) {
  if (!count) return null
  return (
    <span
      aria-hidden="true"
      className="absolute -right-1.5 -top-1.5 min-w-[1.125rem] rounded-full bg-primary px-1 text-center text-[0.6875rem] font-semibold leading-[1.125rem] text-on-primary ring-2 ring-canvas"
    >
      {count > 9 ? '9+' : count}
    </span>
  )
}

/** Opens upwards from the bottom of the sidebar: Settings, Appearance, Website, Log out. */
function MoreMenu({ collapsed }: { collapsed: boolean }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [openOn, setOpenOn] = useState<string | null>(null)
  const open = openOn === pathname
  const menuId = useId()
  const wrapper = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)
  const dark = auth.user?.appearance === 'dark'

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

  const item = 'flex h-12 w-full items-center gap-3 rounded-lg px-4 text-left text-sm text-fg hover:bg-surface'

  return (
    <div ref={wrapper} className="relative">
      <button
        ref={button}
        type="button"
        aria-expanded={open}
        aria-controls={menuId}
        title="More"
        onClick={() => setOpenOn(open ? null : pathname)}
        className={rowClass(collapsed)}
      >
        <Glyph icon={Menu} active={open} />
        <Label active={open} collapsed={collapsed}>
          More
        </Label>
      </button>
      {open && (
        <div id={menuId} className="absolute bottom-full left-0 z-50 mb-2 w-[266px] rounded-2xl bg-surface-raised p-2 shadow-[var(--ui-shadow)] ring-1 ring-border">
          <ul>
            <li>
              <Link to="/members/settings" className={item}>
                <Settings aria-hidden="true" size={20} strokeWidth={ICON.stroke} />
                Settings
              </Link>
            </li>
            <li>
              <button
                type="button"
                role="switch"
                aria-checked={dark}
                className={item}
                onClick={() => {
                  const next = dark ? 'light' : 'dark'
                  void chooseAppearance(next, Boolean(auth.user)).then((session) => session && auth.applySession(session))
                }}
              >
                <Moon aria-hidden="true" size={20} strokeWidth={ICON.stroke} />
                <span className="flex-1">Dark appearance</span>
                <span aria-hidden="true" className={cn('relative h-5 w-9 rounded-full transition-colors duration-150', dark ? 'bg-primary' : 'bg-border-strong')}>
                  <span className={cn('absolute top-0.5 size-4 rounded-full bg-knob transition-transform duration-150', dark ? 'translate-x-[18px]' : 'translate-x-0.5')} />
                </span>
              </button>
            </li>
            <li>
              <Link to="/" className={item}>
                <Globe aria-hidden="true" size={20} strokeWidth={ICON.stroke} />
                Website
              </Link>
            </li>
          </ul>
          <div className="mt-1 border-t border-border pt-1">
            <button
              type="button"
              className={item}
              onClick={async () => {
                setOpenOn(null)
                await auth.logout()
                navigate('/', { replace: true })
              }}
            >
              Log out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

interface SidebarProps {
  me: Me
  panel: Panel
  onPanel: (panel: Panel) => void
  onCreate: () => void
}

/**
 * Tablets and up: fixed on the left. 245px with labels from 1264px, a 72px icon rail
 * below that, and a rail whenever the Search or Notifications panel is open.
 */
export function Sidebar({ me, panel, onPanel, onCreate }: SidebarProps) {
  const collapsed = panel !== null
  const { pathname } = useLocation()
  const link = (to: string, label: string, icon: LucideIcon, end = false) => (
    <li>
      <NavLink to={to} end={end} title={label} onClick={() => onPanel(null)} className={rowClass(collapsed)}>
        {({ isActive }) => {
          const active = isActive && !collapsed
          return (
            <>
              <Glyph icon={icon} active={active} />
              <Label active={active} collapsed={collapsed}>
                {label}
              </Label>
            </>
          )
        }}
      </NavLink>
    </li>
  )
  const toggle = (kind: Exclude<Panel, null>, label: string, icon: LucideIcon, badge = 0) => (
    <li>
      <button type="button" title={label} aria-expanded={panel === kind} onClick={() => onPanel(panel === kind ? null : kind)} className={rowClass(collapsed)}>
        <span className="relative">
          <Glyph icon={icon} active={panel === kind} />
          <UnreadBadge count={badge} />
        </span>
        <Label active={panel === kind} collapsed={collapsed}>
          {label}
        </Label>
        {badge ? <span className="sr-only">, {badge} unread</span> : null}
      </button>
    </li>
  )
  const profile = profilePath(me.handle)
  const onProfile = pathname.startsWith(profile)

  return (
    <nav
      aria-label="Members"
      className={cn(
        'fixed inset-y-0 left-0 z-40 hidden w-[72px] flex-col border-r border-border bg-canvas px-3 pb-5 pt-2 transition-[width] duration-200 ease-out md:flex print:hidden',
        !collapsed && 'wide:w-[245px]',
      )}
    >
      <Link to="/members/feed" onClick={() => onPanel(null)} className="mb-5 flex h-[73px] items-center px-1 pt-3">
        <Wordmark className={cn('hidden pl-2', !collapsed && 'wide:inline')} />
        <span className={cn('flex size-12 items-center justify-center', !collapsed && 'wide:hidden')}>
          <RoseMark className="size-8 text-base" />
        </span>
        <span className="sr-only">Home</span>
      </Link>
      <ul className="flex flex-1 flex-col gap-0.5">
        {link('/members/feed', 'Home', House)}
        {toggle('search', 'Search', Search)}
        {link('/members/explore', 'Explore', Compass)}
        {toggle('notifications', 'Notifications', Heart, me.unread_notifications)}
        <li>
          <button
            type="button"
            title={me.can_post ? 'Create' : 'Posting is paused on your account'}
            disabled={!me.can_post}
            onClick={onCreate}
            className={rowClass(collapsed)}
          >
            <Glyph icon={SquarePlus} active={false} />
            <Label active={false} collapsed={collapsed}>
              Create
            </Label>
          </button>
        </li>
        <li>
          <NavLink to={profile} title="Profile" onClick={() => onPanel(null)} className={rowClass(collapsed)}>
            <span aria-hidden="true" className={cn('inline-flex rounded-full', onProfile && !collapsed && 'ring-2 ring-fg ring-offset-1 ring-offset-canvas')}>
              <Avatar member={me} size="xs" />
            </span>
            <Label active={onProfile && !collapsed} collapsed={collapsed}>
              Profile
            </Label>
          </NavLink>
        </li>
      </ul>
      <MoreMenu collapsed={collapsed} />
      {/* The quick exit is always the last item. */}
      <a
        href={quickExitUrl()}
        onClick={leave}
        rel="noreferrer"
        title="Leave this site now. Shortcut: press Esc twice."
        className={cn(rowClass(collapsed, 'text-danger'), 'font-semibold')}
      >
        <LogOut aria-hidden="true" size={ICON.size} strokeWidth={ICON.activeStroke} className="shrink-0" />
        <span className={cn('hidden', !collapsed && 'wide:inline')}>Leave</span>
        <span className={cn('sr-only', !collapsed && 'wide:hidden')}>Leave</span>
        <span className="sr-only"> this site now. Shortcut: press Escape twice.</span>
      </a>
    </nav>
  )
}

/** Phones: a 44px top bar with the wordmark, Notifications and the quick exit. */
export function TopBar({ me }: { me: Me }) {
  return (
    <header className="fixed inset-x-0 top-0 z-40 flex h-11 items-center justify-between border-b border-border bg-canvas px-4 md:hidden print:hidden">
      <Link to="/members/feed" className="flex items-center">
        <Wordmark className="text-2xl" />
        <span className="sr-only">Home</span>
      </Link>
      <div className="-mr-2 flex items-center">
        <NavLink to="/members/notifications" className="relative inline-flex size-11 items-center justify-center text-fg">
          {({ isActive }) => (
            <>
              <span className="relative">
                <Heart aria-hidden="true" size={ICON.size} strokeWidth={isActive ? ICON.activeStroke : ICON.stroke} />
                <UnreadBadge count={me.unread_notifications} />
              </span>
              <span className="sr-only">
                Notifications{me.unread_notifications ? `, ${me.unread_notifications} unread` : ''}
              </span>
            </>
          )}
        </NavLink>
        <a
          href={quickExitUrl()}
          onClick={leave}
          rel="noreferrer"
          title="Leave this site now. Shortcut: press Esc twice."
          className="inline-flex size-11 items-center justify-center text-danger"
        >
          <LogOut aria-hidden="true" size={ICON.size} strokeWidth={ICON.activeStroke} />
          <span className="sr-only">Leave this site now. Shortcut: press Escape twice.</span>
        </a>
      </div>
    </header>
  )
}

/** Phones: a 50px tab bar above the home indicator. */
export function TabBar({ me, onCreate }: { me: Me; onCreate: () => void }) {
  const { pathname } = useLocation()
  const profile = profilePath(me.handle)
  const tab = (to: string, label: string, icon: LucideIcon) => (
    <li className="flex-1">
      <NavLink to={to} className="flex h-[50px] items-center justify-center text-fg">
        {({ isActive }) => (
          <>
            <Glyph icon={icon} active={isActive} />
            <span className="sr-only">{label}</span>
          </>
        )}
      </NavLink>
    </li>
  )
  return (
    <nav
      aria-label="Members"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-canvas pb-[env(safe-area-inset-bottom)] md:hidden print:hidden"
    >
      <ul className="flex">
        {tab('/members/feed', 'Home', House)}
        {tab('/members/search', 'Search', Search)}
        <li className="flex-1">
          <button
            type="button"
            onClick={onCreate}
            disabled={!me.can_post}
            title={me.can_post ? 'Create' : 'Posting is paused on your account'}
            className="flex h-[50px] w-full items-center justify-center text-fg disabled:opacity-40"
          >
            <Glyph icon={SquarePlus} active={false} />
            <span className="sr-only">Create</span>
          </button>
        </li>
        {tab('/members/explore', 'Explore', Compass)}
        <li className="flex-1">
          <NavLink to={profile} className="flex h-[50px] items-center justify-center">
            <span aria-hidden="true" className={cn('inline-flex rounded-full', pathname.startsWith(profile) && 'ring-2 ring-fg ring-offset-1 ring-offset-canvas')}>
              <Avatar member={me} size="xs" />
            </span>
            <span className="sr-only">Profile</span>
          </NavLink>
        </li>
      </ul>
    </nav>
  )
}
