import { Menu, User } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router'
import { cn } from '@/lib/cn'
import { Modal } from '../ui'
import { AccountMenu } from './AccountMenu'
import { useAuth } from './authContext'
import { NAV_ITEMS } from './navigation'
import { QuickExit } from './QuickExit'
import { Wordmark } from './Wordmark'

function MobileAccountLinks({ onNavigate }: { onNavigate: () => void }) {
  const auth = useAuth()
  const { pathname } = useLocation()
  if (auth.status === 'loading') return null
  return (
    <p className="mt-8 flex items-center gap-2 text-fg-muted">
      <User aria-hidden="true" className="size-4 text-highlight" />
      {auth.user ? (
        <NavLink to="/account" onClick={onNavigate} className="text-lg text-fg hover:text-accent">
          {auth.user.display_name}
        </NavLink>
      ) : (
        <NavLink
          to={`/account/login?next=${encodeURIComponent(pathname)}`}
          onClick={onNavigate}
          className="text-lg text-fg hover:text-accent"
        >
          Log in
        </NavLink>
      )}
    </p>
  )
}

export function Header() {
  const { pathname } = useLocation()
  // The menu belongs to the page it was opened on, so any navigation closes it.
  const [menuPath, setMenuPath] = useState<string | null>(null)
  const menuOpen = menuPath === pathname
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={cn(
        'fixed inset-x-0 top-0 z-30 transition-colors duration-500 ease-velvet',
        scrolled ? 'border-b border-border/60 bg-canvas/90 backdrop-blur-md' : 'bg-gradient-to-b from-canvas/80 to-transparent',
      )}
    >
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-4 focus:py-2"
      >
        Skip to content
      </a>
      <div className="mx-auto flex h-18 max-w-7xl items-center justify-between px-5 sm:px-8">
        <Wordmark />
        <nav aria-label="Main" className="hidden xl:flex xl:items-center">
          <ul className="flex items-center gap-0.5">
            {NAV_ITEMS.filter((item) => item.to !== '/').map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      'relative inline-flex min-h-11 items-center px-2.5 text-sm tracking-wide transition-colors duration-300',
                      isActive ? 'text-fg' : 'text-fg-muted hover:text-fg',
                      item.to === '/join' &&
                        'ml-1 rounded-full border border-highlight/50 px-5 text-fg hover:border-highlight',
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {item.label}
                      {isActive && item.to !== '/join' && (
                        <span aria-hidden="true" className="absolute inset-x-2.5 bottom-2 h-px bg-highlight" />
                      )}
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
          <AccountMenu className="ml-2" />
        </nav>
        <div className="flex items-center gap-2 xl:hidden">
          <QuickExit variant="compact" />
          <button
            type="button"
            onClick={() => setMenuPath(pathname)}
            aria-expanded={menuOpen}
            className="-mr-2 inline-flex size-11 items-center justify-center rounded-full text-fg"
          >
            <Menu aria-hidden="true" className="size-6" />
            <span className="sr-only">Open menu</span>
          </button>
        </div>
      </div>

      <Modal open={menuOpen} onClose={() => setMenuPath(null)} title="Menu" hideTitle variant="sheet">
        <nav aria-label="Main" className="flex h-full flex-col">
          <ul className="mt-6 flex flex-col">
            {NAV_ITEMS.map((item) => (
              <li key={item.to} className="border-b border-border/60">
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => setMenuPath(null)}
                  className={({ isActive }) =>
                    cn(
                      'flex min-h-16 items-center font-display text-3xl transition-colors',
                      isActive ? 'text-accent' : 'text-fg hover:text-accent',
                    )
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <MobileAccountLinks onNavigate={() => setMenuPath(null)} />
          <div className="mt-auto flex items-center justify-between gap-4 pt-10">
            <p className="text-sm text-fg-subtle">Press Esc twice to leave quickly.</p>
            <QuickExit variant="inline" />
          </div>
        </nav>
      </Modal>
    </header>
  )
}
