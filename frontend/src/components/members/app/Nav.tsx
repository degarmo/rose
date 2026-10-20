import { ArrowLeft, Bell, Compass, Globe, House, LogOut, Menu, Moon, ScanLine, Search, Settings, ShieldCheck, SquarePlus, User, type LucideIcon } from 'lucide-react'
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { Switch } from '@/components/ui'
import { chooseAppearance } from '@/lib/appearance'
import { cn } from '@/lib/cn'
import type { Me } from '@/lib/membersApi'
import { leaveNow, quickExitUrl } from '@/lib/quickExit'
import { profilePath } from './postUtils'
import { Wordmark } from './primitives'
import { ICON } from './ui'

export type Panel = 'search' | 'notifications' | null

function leave(event: { preventDefault: () => void }) {
  event.preventDefault()
  leaveNow()
}

/**
 * Sidebar rows (design: 48px tall with 12px padding, 8px corners, the icon 16px from the
 * label, #FAFAFA on hover). They sit 76px apart, as drawn. The labels show from 1264px
 * unless a panel has collapsed the sidebar to its rail.
 */
function rowClass(collapsed: boolean, tone = 'text-fg') {
  return cn(
    'group my-3 flex h-12 w-full items-center gap-4 rounded-app p-3 transition-colors duration-150 ease-out hover:bg-surface disabled:cursor-not-allowed disabled:opacity-40',
    tone,
    collapsed && 'justify-center',
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

function Glyph({ icon: Icon, active, phone = false }: { icon: LucideIcon; active: boolean; phone?: boolean }) {
  return (
    <Icon
      aria-hidden="true"
      size={ICON.size}
      strokeWidth={active ? (phone ? ICON.tabStroke : ICON.activeStroke) : ICON.stroke}
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

/** Opens upwards from the bottom of the sidebar: Settings, Dark appearance, Website, Log out. */
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

  const item = 'flex h-12 w-full items-center gap-3 rounded-app px-4 text-left text-fg hover:bg-surface'
  const onSettings = pathname === '/members/settings'

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
        <Glyph icon={Menu} active={open || onSettings} />
        <Label active={open || onSettings} collapsed={collapsed}>
          More
        </Label>
      </button>
      {open && (
        <div id={menuId} className="absolute bottom-full left-0 z-50 mb-2 w-[266px] rounded-sheet border border-border bg-canvas p-2 shadow-sheet">
          <ul>
            <li>
              <Link to="/members/settings" className={item}>
                <Settings aria-hidden="true" size={20} strokeWidth={ICON.stroke} />
                Settings
              </Link>
            </li>
            <li>
              <label className={cn(item, 'cursor-pointer')}>
                <Moon aria-hidden="true" size={20} strokeWidth={ICON.stroke} />
                <span className="flex-1">Dark appearance</span>
                <Switch
                  checked={dark}
                  onChange={(next) => {
                    void chooseAppearance(next ? 'dark' : 'light', Boolean(auth.user)).then((session) => session && auth.applySession(session))
                  }}
                />
              </label>
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
  /** Null on the account-only screens (no feed access): Home, Settings and Staff only. */
  me: Me | null
  panel: Panel
  onPanel: (panel: Panel) => void
  onCreate: () => void
}

/**
 * Tablets and up (design: "Sidebar 245px, 1px right border"): fixed on the left. Labels
 * and the wordmark from 1264px; below that, and whenever the Search or Notifications panel
 * is open, a 72px icon rail with "R" and the active item outlined.
 */
export function Sidebar({ me, panel, onPanel, onCreate }: SidebarProps) {
  const auth = useAuth()
  const staffRole = auth.user?.staff?.role
  const doorDesk = Boolean(auth.user?.staff?.door_desk)
  const atDoor = (path: string) => path.startsWith('/members/staff/door')
  const doorLink = () => doorDesk && link('/members/staff/door', 'Door desk', ScanLine, atDoor, true)
  const collapsed = panel !== null
  const { pathname } = useLocation()
  const outline = (active: boolean) => active && 'border border-border wide:border-transparent'
  // reloadDocument: the door desk loads afresh, so its camera permission applies.
  const link = (to: string, label: string, icon: LucideIcon, activeFor?: (path: string) => boolean, reloadDocument = false) => (
    <li>
      <NavLink to={to} title={label} reloadDocument={reloadDocument} onClick={() => onPanel(null)} className={({ isActive }) => cn(rowClass(collapsed), outline((activeFor ? activeFor(pathname) : isActive) && !collapsed))}>
        {({ isActive }) => {
          const active = (activeFor ? activeFor(pathname) : isActive) && !collapsed
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
      <button
        type="button"
        title={label}
        aria-expanded={panel === kind}
        onClick={() => onPanel(panel === kind ? null : kind)}
        className={cn(rowClass(collapsed), panel === kind && 'border border-border')}
      >
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
  const home = me ? '/members/feed' : '/members/home'

  return (
    <nav
      aria-label="Members"
      className={cn(
        'fixed inset-y-0 left-0 z-40 hidden w-[72px] flex-col overflow-y-auto border-r border-border bg-canvas px-3 pb-5 pt-2 transition-[width] duration-200 ease-out [scrollbar-width:none] md:flex print:hidden',
        !collapsed && 'wide:w-[245px]',
      )}
    >
      <Link to={home} onClick={() => onPanel(null)} className={cn('flex shrink-0 items-center pb-5 pt-6', collapsed ? 'justify-center' : 'justify-center wide:justify-start wide:px-3')}>
        <Wordmark className={cn('hidden', !collapsed && 'wide:inline')} />
        <span aria-hidden="true" className={cn('font-serif text-2xl leading-none text-wordmark', !collapsed && 'wide:hidden')}>
          R
        </span>
        <span className="sr-only">Home</span>
      </Link>
      <ul className="flex flex-1 flex-col">
        {/* A door volunteer's first item; the team find it beside Staff. */}
        {!staffRole && doorLink()}
        {me ? (
          <>
            {link('/members/feed', 'Home', House)}
            {toggle('search', 'Search', Search)}
            {link('/members/explore', 'Explore', Compass)}
            {toggle('notifications', 'Notifications', Bell, me.unread_notifications)}
            <li>
              <button type="button" title={me.can_post ? 'Create' : 'Posting is paused on your account'} disabled={!me.can_post} onClick={onCreate} className={rowClass(collapsed)}>
                <Glyph icon={SquarePlus} active={false} />
                <Label active={false} collapsed={collapsed}>
                  Create
                </Label>
              </button>
            </li>
            {link(profilePath(me.handle), 'Profile', User, (path) => path.startsWith(profilePath(me.handle)))}
          </>
        ) : (
          <>
            {link('/members/home', 'Home', House)}
            {link('/members/settings', 'Settings', Settings, (path) => path.startsWith('/members/settings'))}
          </>
        )}
        {staffRole && link('/members/staff', 'Staff', ShieldCheck, (path) => path.startsWith('/members/staff') && !atDoor(path))}
        {staffRole && doorLink()}
      </ul>
      <MoreMenu collapsed={collapsed} />
      {/* The quick exit is always the last item. */}
      <a href={quickExitUrl()} onClick={leave} rel="noreferrer" title="Leave this site now. Shortcut: press Esc twice." className={cn(rowClass(collapsed, 'text-fg-muted'), 'mb-0')}>
        <LogOut aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} className="shrink-0" />
        <span className={cn('hidden', !collapsed && 'wide:inline')}>Leave</span>
        <span className={cn('sr-only', !collapsed && 'wide:hidden')}>Leave</span>
        <span className="sr-only"> this site now. Shortcut: press Escape twice.</span>
      </a>
    </nav>
  )
}

/** The quick exit as a muted icon, for the phone bars. */
export function LeaveButton({ className }: { className?: string }) {
  return (
    <a href={quickExitUrl()} onClick={leave} rel="noreferrer" title="Leave this site now. Shortcut: press Esc twice." className={cn('inline-flex size-10 items-center justify-center text-fg-muted', className)}>
      <LogOut aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} />
      <span className="sr-only">Leave this site now. Shortcut: press Escape twice.</span>
    </a>
  )
}

/** Steps back in the app's history, or to the feed when the page was opened directly. */
/** Back one step, or to `to` when given (the account screens' fixed parent). */
export function BackButton({ to }: { to?: string }) {
  const navigate = useNavigate()
  const location = useLocation()
  return (
    <button
      type="button"
      onClick={() => (to ? navigate(to) : location.key === 'default' ? navigate('/members/feed') : navigate(-1))}
      className="-ml-2 inline-flex size-10 items-center justify-center text-fg"
    >
      <ArrowLeft aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} />
      <span className="sr-only">Back</span>
    </button>
  )
}

interface PhoneBarProps {
  /** The bar's title (16/600), or the wordmark when absent. */
  title?: ReactNode
  /** A back arrow: one step back, or to the path given. */
  back?: boolean | string
  /** Icons before the Leave control, which always comes last. */
  actions?: ReactNode
  /** A 1px rule under the bar (design: the Post page). */
  rule?: boolean
  className?: string
}

/**
 * The phone top bar (design: 44px, 16px side padding): a back arrow or nothing, the title,
 * then the page's own icons and the quick exit, 20px apart. Only below 768px.
 */
export function PhoneBar({ title, back = false, actions, rule = false, className }: PhoneBarProps) {
  return (
    <header className={cn('sticky top-0 z-30 flex h-11 items-center gap-3 bg-canvas px-4 md:hidden print:hidden', rule && 'border-b border-border', className)}>
      {back && <BackButton to={typeof back === 'string' ? back : undefined} />}
      <div className="min-w-0 flex-1 truncate text-base font-semibold text-fg">{title}</div>
      <div className="-mr-2 flex items-center gap-1">
        {actions}
        <LeaveButton />
      </div>
    </header>
  )
}

/** The feed's phone bar: the wordmark, Notifications and the quick exit. */
export function HomeBar({ me }: { me: Me }) {
  return (
    <PhoneBar
      title={
        <Link to="/members/feed" className="flex items-center">
          <Wordmark className="text-2xl" />
          <span className="sr-only">Home</span>
        </Link>
      }
      actions={
        <NavLink to="/members/notifications" className="relative inline-flex size-10 items-center justify-center text-fg">
          <span className="relative">
            <Bell aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} />
            <UnreadBadge count={me.unread_notifications} />
          </span>
          <span className="sr-only">Notifications{me.unread_notifications ? `, ${me.unread_notifications} unread` : ''}</span>
        </NavLink>
      }
    />
  )
}

/** Phones: a 50px tab bar (design: Home, Search, Create, Explore, Profile). */
export function TabBar({ me, onCreate }: { me: Me | null; onCreate: () => void }) {
  const { pathname } = useLocation()
  const auth = useAuth()
  const tab = (to: string, label: string, icon: LucideIcon, active?: boolean, reloadDocument = false) => (
    <li className="flex-1">
      <NavLink to={to} reloadDocument={reloadDocument} className="flex h-[50px] items-center justify-center text-fg">
        {({ isActive }) => (
          <>
            <Glyph icon={icon} active={active ?? isActive} phone />
            <span className="sr-only">{label}</span>
          </>
        )}
      </NavLink>
    </li>
  )
  const bar = 'fixed inset-x-0 bottom-0 z-40 border-t border-border bg-canvas px-2 pb-[env(safe-area-inset-bottom)] md:hidden print:hidden'
  if (!me) {
    // The account-only screens: the door desk first for a volunteer, Home, Settings and,
    // for the team, Staff.
    const staff = auth.user?.staff
    return (
      <nav aria-label="Members" className={bar}>
        <ul className="flex">
          {staff?.door_desk && !staff.role && tab('/members/staff/door', 'Door desk', ScanLine, undefined, true)}
          {tab('/members/home', 'Home', House)}
          {tab('/members/settings', 'Settings', Settings, pathname.startsWith('/members/settings'))}
          {staff?.role && tab('/members/staff', 'Staff', ShieldCheck, pathname.startsWith('/members/staff'))}
        </ul>
      </nav>
    )
  }
  const profile = profilePath(me.handle)
  return (
    <nav aria-label="Members" className={bar}>
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
            <Glyph icon={SquarePlus} active={false} phone />
            <span className="sr-only">Create</span>
          </button>
        </li>
        {tab('/members/explore', 'Explore', Compass)}
        {tab(profile, 'Profile', User, pathname.startsWith(profile) || pathname === '/members/settings')}
      </ul>
    </nav>
  )
}
