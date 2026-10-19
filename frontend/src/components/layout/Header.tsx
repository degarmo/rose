import { Menu } from 'lucide-react'
import { useState } from 'react'
import { NavLink, useLocation } from 'react-router'
import { cn } from '@/lib/cn'
import { ButtonLink, GUTTER, Modal } from '../ui'
import { AccountMenu } from './AccountMenu'
import { useAuth } from './authContext'
import { NavDropdown } from './NavDropdown'
import { isGroup, JOIN_LINK, NAV, type NavLinkItem } from './navigation'
import { QuickExit } from './QuickExit'
import { Wordmark } from './Wordmark'

/** "My feed": shown only to people the member app opens for. */
function MyFeedLink({ onNavigate, className }: { onNavigate?: () => void; className: string }) {
  const auth = useAuth()
  if (!auth.user?.feed_access) return null
  return (
    <NavLink to="/members/feed" onClick={onNavigate} className={className}>
      My feed
    </NavLink>
  )
}

const NAV_LINK = 'inline-flex min-h-10 items-center text-sm font-medium transition-colors duration-150'

function MobileLink({ item, onNavigate }: { item: NavLinkItem; onNavigate: () => void }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === '/'}
      onClick={onNavigate}
      className={({ isActive }) => cn('flex min-h-12 items-center font-display text-[1.625rem] font-light', isActive ? 'text-link' : 'text-fg hover:text-link')}
    >
      {item.label}
    </NavLink>
  )
}

function MobileMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  const auth = useAuth()
  const { pathname } = useLocation()
  return (
    <Modal open={open} onClose={onClose} title="Menu" hideTitle variant="sheet">
      <nav aria-label="Main" className="flex min-h-full flex-col">
        <ul className="flex flex-col">
          {NAV.map((entry) =>
            isGroup(entry) ? (
              <li key={entry.label} className="border-b border-border py-3">
                <h2 className="font-sans text-label font-semibold uppercase text-fg-muted">{entry.label}</h2>
                <ul className="mt-1 flex flex-col">
                  {entry.items.map((item) => (
                    <li key={item.to}>
                      <MobileLink item={item} onNavigate={onClose} />
                    </li>
                  ))}
                </ul>
              </li>
            ) : (
              <li key={entry.to} className="border-b border-border">
                <MobileLink item={entry} onNavigate={onClose} />
              </li>
            ),
          )}
        </ul>
        {auth.status !== 'loading' && (
          <div className="mt-6 flex flex-col gap-3">
            <MyFeedLink onNavigate={onClose} className="text-[0.9375rem] font-semibold text-link" />
            {auth.user ? (
              <NavLink to="/account" onClick={onClose} className="text-[0.9375rem] font-semibold text-fg">
                {auth.user.display_name}
              </NavLink>
            ) : (
              <NavLink to={`/account/login?next=${encodeURIComponent(pathname)}`} onClick={onClose} className="text-[0.9375rem] font-semibold text-fg">
                Log in
              </NavLink>
            )}
          </div>
        )}
        <div className="mt-auto flex flex-col gap-3 pt-10">
          <ButtonLink to={JOIN_LINK.to} size="lg" className="w-full">
            {JOIN_LINK.label}
          </ButtonLink>
          <p className="text-[0.8125rem] text-fg-muted">Press Esc twice to leave quickly.</p>
        </div>
      </nav>
    </Modal>
  )
}

/**
 * The website header (design: 72px on desktop, 56px on phones, 1px rule below): the
 * wordmark, the navigation, then Log in, Join and the Leave control. Below 1280px the
 * navigation moves into a menu and Leave stays beside the menu button.
 */
/** Where the join flow shows its steps (design: the Join header). Filled by `JoinSteps`. */
export const JOIN_STEPS_SLOT = 'join-steps'

export function Header() {
  const { pathname } = useLocation()
  // The menu belongs to the page it was opened on, so any navigation closes it.
  const [menuPath, setMenuPath] = useState<string | null>(null)

  if (pathname === '/join' || pathname.startsWith('/join/')) {
    // Joining has its own quiet header: the wordmark, the steps and Leave, nothing to wander off to.
    return (
      <header className="sticky top-0 z-30 border-b border-border bg-canvas print:hidden">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-4 focus:py-2 focus:text-on-primary"
        >
          Skip to content
        </a>
        <div className={cn('mx-auto flex h-14 max-w-[1440px] items-center justify-between gap-7 xl:h-18', GUTTER)}>
          <Wordmark />
          <div id={JOIN_STEPS_SLOT} className="hidden lg:block" />
          <QuickExit />
        </div>
      </header>
    )
  }

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-canvas print:hidden">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-4 focus:py-2 focus:text-on-primary"
      >
        Skip to content
      </a>
      <div className={cn('mx-auto flex h-14 max-w-[1440px] items-center gap-7 xl:h-18', GUTTER)}>
        <Wordmark />
        <nav aria-label="Main" className="hidden flex-1 items-center gap-6 xl:flex">
          {NAV.map((entry) => {
            if (isGroup(entry)) return <NavDropdown key={entry.label} group={entry} />
            if (entry.to === '/') return null
            return (
              <NavLink key={entry.to} to={entry.to} className={({ isActive }) => cn(NAV_LINK, isActive ? 'text-link' : 'text-fg hover:text-link')}>
                {entry.label}
              </NavLink>
            )
          })}
        </nav>
        <div className="hidden items-center gap-7 xl:flex">
          <MyFeedLink className="inline-flex min-h-10 items-center text-sm font-semibold text-link hover:text-primary-hover" />
          <AccountMenu />
          <ButtonLink to={JOIN_LINK.to}>{JOIN_LINK.label}</ButtonLink>
          <QuickExit />
        </div>
        <div className="ml-auto flex items-center gap-2 xl:hidden">
          <QuickExit />
          <button
            type="button"
            onClick={() => setMenuPath(pathname)}
            aria-expanded={menuPath === pathname}
            className="-mr-2 inline-flex size-10 items-center justify-center text-fg"
          >
            <Menu aria-hidden="true" className="size-[22px]" strokeWidth={1.8} />
            <span className="sr-only">Open menu</span>
          </button>
        </div>
      </div>
      <MobileMenu open={menuPath === pathname} onClose={() => setMenuPath(null)} />
    </header>
  )
}
