import { Bell, LayoutList, Plus, Search, UserRound } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Outlet, ScrollRestoration, useLocation } from 'react-router'
import { LoadingState } from '@/components/content/States'
import { QuickExit } from '@/components/layout/QuickExit'
import { Wordmark } from '@/components/layout/Wordmark'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { members, type Me } from '@/lib/membersApi'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { Composer } from './Composer'
import { MembersContext } from './membersContext'

type LoadState = { status: 'loading' } | { status: 'ready'; me: Me } | { status: 'denied' } | { status: 'error' }

/** Quieter chrome for the members area. Anyone without access sees the site's 404. */
export function MembersLayout() {
  const { pathname } = useLocation()
  const [state, setState] = useState<LoadState>({ status: 'loading' })
  const [composerOpen, setComposerOpen] = useState(false)
  const [postsVersion, setPostsVersion] = useState(0)

  const load = useCallback(async () => {
    try {
      setState({ status: 'ready', me: await members.me() })
    } catch (error) {
      setState(error instanceof ApiError && (error.isNotFound || error.status === 403) ? { status: 'denied' } : { status: 'error' })
    }
  }, [])

  useEffect(() => {
    let active = true
    members.me().then(
      (me) => active && setState({ status: 'ready', me }),
      (error: unknown) =>
        active &&
        setState(error instanceof ApiError && (error.isNotFound || error.status === 403) ? { status: 'denied' } : { status: 'error' }),
    )
    return () => {
      active = false
    }
  }, [pathname])

  useEffect(() => {
    document.head.querySelector('meta[name="robots"]')?.setAttribute('content', 'noindex, nofollow')
  }, [pathname])

  const me = state.status === 'ready' ? state.me : null
  const value = useMemo(
    () =>
      me && {
        me,
        refreshMe: load,
        setMe: (next: Me) => setState({ status: 'ready', me: next }),
        openComposer: () => setComposerOpen(true),
        postsVersion,
        notePosted: () => setPostsVersion((n) => n + 1),
      },
    [me, load, postsVersion],
  )

  if (state.status === 'denied') {
    return (
      <div className="min-h-dvh">
        <NotFoundPage />
      </div>
    )
  }
  if (!value) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        {state.status === 'error' ? (
          <p className="text-fg-muted">
            Something went wrong.{' '}
            <button type="button" onClick={() => void load()} className="underline">
              Try again
            </button>
          </p>
        ) : (
          <LoadingState label="Loading" />
        )}
        <QuickExit />
      </div>
    )
  }

  const tabs = [
    { to: '/members/feed', label: 'Feed', icon: LayoutList },
    { to: '/members/directory', label: 'Directory', icon: Search },
    { to: '/members/notifications', label: 'Notifications', icon: Bell, badge: value.me.unread_notifications },
    { to: `/members/u/${encodeURIComponent(value.me.handle)}`, label: 'Profile', icon: UserRound },
  ]

  return (
    <MembersContext.Provider value={value}>
      <div className="flex min-h-dvh flex-col bg-canvas">
        <header className="sticky top-0 z-30 border-b border-border/60 bg-canvas/95 backdrop-blur-md">
          <div className="mx-auto flex h-14 max-w-2xl items-center justify-between px-4">
            <div className="scale-90 origin-left">
              <Wordmark />
            </div>
            <div className="flex items-center gap-2">
              <Link to="/account" className="hidden min-h-11 items-center px-2 text-sm text-fg-muted hover:text-fg sm:inline-flex">
                Account
              </Link>
              <QuickExit variant="compact" />
            </div>
          </div>
          <nav aria-label="Members" className="mx-auto max-w-2xl px-2">
            <ul className="grid grid-cols-4">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <li key={tab.to}>
                    <NavLink
                      to={tab.to}
                      className={({ isActive }) =>
                        cn(
                          'relative flex min-h-12 flex-col items-center justify-center gap-0.5 text-[0.7rem] tracking-wide transition-colors',
                          isActive ? 'text-fg' : 'text-fg-subtle hover:text-fg',
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <span className="relative">
                            <Icon aria-hidden="true" className="size-5" />
                            {tab.badge ? (
                              <span className="absolute -right-2 -top-1.5 min-w-4 rounded-full bg-primary px-1 text-center text-[0.6rem] font-semibold leading-4 text-on-primary">
                                {tab.badge > 9 ? '9+' : tab.badge}
                              </span>
                            ) : null}
                          </span>
                          <span>
                            {tab.label}
                            {tab.badge ? <span className="sr-only">, {tab.badge} unread</span> : null}
                          </span>
                          {isActive && <span aria-hidden="true" className="absolute inset-x-6 bottom-0 h-0.5 bg-highlight" />}
                        </>
                      )}
                    </NavLink>
                  </li>
                )
              })}
            </ul>
          </nav>
        </header>

        <main id="main" className="mx-auto w-full max-w-2xl flex-1 px-3 pb-32 pt-4 sm:px-4">
          <Outlet />
        </main>

        <button
          type="button"
          onClick={() => setComposerOpen(true)}
          disabled={!value.me.can_post}
          title={value.me.can_post ? 'New post' : 'Posting is paused on your account'}
          className="fixed bottom-6 right-5 z-30 inline-flex size-14 items-center justify-center rounded-full bg-primary text-on-primary shadow-xl shadow-black/50 transition-colors hover:bg-primary-hover disabled:opacity-40 xl:bottom-24"
        >
          <Plus aria-hidden="true" className="size-6" />
          <span className="sr-only">New post</span>
        </button>
        <div className="hidden xl:block">
          <QuickExit />
        </div>
        <Composer open={composerOpen} onClose={() => setComposerOpen(false)} onPosted={() => setPostsVersion((n) => n + 1)} />
        <ScrollRestoration />
      </div>
    </MembersContext.Provider>
  )
}
