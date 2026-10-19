import { useCallback, useEffect, useMemo, useState } from 'react'
import { Outlet, ScrollRestoration, useLocation } from 'react-router'
import { LoadingState } from '@/components/content/States'
import { QuickExit } from '@/components/layout/QuickExit'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { members, type Me } from '@/lib/membersApi'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { nextAppearance, storeAppearance, storedAppearance, type Appearance } from './appearance'
import { Composer } from './Composer'
import { MembersSidebar, SIDEBAR_OFFSET } from './MembersSidebar'
import { MembersContext } from './membersContext'

type LoadState = { status: 'loading' } | { status: 'ready'; me: Me } | { status: 'denied' } | { status: 'error' }

/**
 * The members area, in a photo-app layout of its own (light or dark, left
 * sidebar). Anyone without access sees the site's ordinary 404, and the loading
 * state looks like the rest of the site, so nothing hints the area exists.
 */
export function MembersLayout() {
  const { pathname } = useLocation()
  const [state, setState] = useState<LoadState>({ status: 'loading' })
  const [composerOpen, setComposerOpen] = useState(false)
  const [postsVersion, setPostsVersion] = useState(0)
  const [appearance, setAppearance] = useState<Appearance>(storedAppearance)

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

  return (
    <MembersContext.Provider value={value}>
      <div data-theme={appearance === 'auto' ? undefined : appearance} className={cn('ig-app min-h-dvh', SIDEBAR_OFFSET)}>
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-on-primary"
        >
          Skip to content
        </a>
        <MembersSidebar
          me={value.me}
          onCreate={() => setComposerOpen(true)}
          appearance={appearance}
          onAppearance={() => {
            const next = nextAppearance(appearance)
            storeAppearance(next)
            setAppearance(next)
          }}
        />
        <main id="main" className="mx-auto w-full max-w-[630px] px-2 pb-16 pt-4 sm:px-4 md:pt-8">
          <Outlet />
        </main>
        <Composer open={composerOpen} onClose={() => setComposerOpen(false)} onPosted={() => setPostsVersion((n) => n + 1)} />
        <ScrollRestoration />
      </div>
    </MembersContext.Provider>
  )
}
