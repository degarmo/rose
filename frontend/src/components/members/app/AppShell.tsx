import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Outlet, ScrollRestoration, useLocation, useNavigate, useSearchParams } from 'react-router'
import { LoadingState } from '@/components/content/States'
import { SiteFrame } from '@/components/layout/Layout'
import { QuickExit } from '@/components/layout/QuickExit'
import { ApiError } from '@/lib/api'
import { firstMe, members, type FeedPost, type Me } from '@/lib/membersApi'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { MembersContext } from '../membersContext'
import { CreatePost } from './CreatePost'
import { Sidebar, TabBar, TopBar, type Panel } from './Nav'
import { NotificationsContent } from './NotificationsContent'
import { PostDetail } from './PostDetail'
import { LeaveIcon } from './primitives'
import { SearchContent } from './SearchContent'
import { MEDIA, useMediaQuery } from './useMediaQuery'

type LoadState = { status: 'loading' } | { status: 'ready'; me: Me } | { status: 'denied' } | { status: 'error' }

interface PostState {
  /** The ids of the list the post was opened from, for the arrow keys. */
  postIds?: string[]
  /** Set when the app opened the modal, so closing can step back in history. */
  fromApp?: boolean
}

function deniedOrError(error: unknown): LoadState {
  return error instanceof ApiError && (error.isNotFound || error.status === 403) ? { status: 'denied' } : { status: 'error' }
}

/** The 397px panel that slides out beside the collapsed sidebar on tablets and desktops. */
function SidePanel({ panel, onClose }: { panel: Exclude<Panel, null>; onClose: () => void }) {
  const ref = useRef<HTMLElement>(null)
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    function onPointer(event: PointerEvent) {
      const target = event.target as HTMLElement
      if (!ref.current?.contains(target) && !target.closest('nav[aria-label="Members"]')) onClose()
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onPointer)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onPointer)
    }
  }, [onClose])
  const title = panel === 'search' ? 'Search' : 'Notifications'
  return (
    <aside
      ref={ref}
      aria-label={title}
      className="fixed inset-y-0 left-[72px] z-30 hidden w-[397px] animate-panel-in flex-col rounded-r-2xl border-r border-border bg-canvas py-2 shadow-[var(--ui-shadow)] md:flex"
    >
      <h2 className="px-6 pb-9 pt-5 text-2xl font-semibold text-fg">{title}</h2>
      {panel === 'search' ? (
        <SearchContent onNavigate={onClose} autoFocus />
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <NotificationsContent onNavigate={onClose} />
        </div>
      )}
    </aside>
  )
}

/** Desktop and tablet post view over the current page: Esc or a click outside closes, arrows step. */
function PostModal({ id, ids, onClose, onStep }: { id: string; ids: string[]; onClose: () => void; onStep: (id: string) => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const index = ids.indexOf(id)
  const previous = index > 0 ? ids[index - 1] : null
  const next = index >= 0 && index < ids.length - 1 ? ids[index + 1] : null

  useEffect(() => {
    const dialog = ref.current
    if (dialog && !dialog.open) dialog.showModal()
  }, [])

  return (
    <dialog
      ref={ref}
      aria-label="Post"
      onClose={onClose}
      onClick={(event) => {
        if (event.target === ref.current) onClose()
      }}
      onKeyDown={(event) => {
        const target = event.target as HTMLElement
        if (target.closest('input, textarea, [role="region"]')) return
        if (event.key === 'ArrowRight' && next) {
          event.preventDefault()
          onStep(next)
        } else if (event.key === 'ArrowLeft' && previous) {
          event.preventDefault()
          onStep(previous)
        }
      }}
      className="m-0 h-dvh max-h-none w-screen max-w-none items-center justify-center bg-transparent px-16 py-6 open:flex"
    >
      <div className="fixed right-4 top-4 flex items-center gap-1 text-white">
        <LeaveIcon />
        <button type="button" onClick={onClose} className="inline-flex size-10 items-center justify-center">
          <X aria-hidden="true" className="size-7" />
          <span className="sr-only">Close</span>
        </button>
      </div>
      {previous && (
        <button
          type="button"
          onClick={() => onStep(previous)}
          className="fixed left-4 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-full bg-white text-[#262626]"
        >
          <ChevronLeft aria-hidden="true" className="size-5" />
          <span className="sr-only">Previous post</span>
        </button>
      )}
      {next && (
        <button
          type="button"
          onClick={() => onStep(next)}
          className="fixed right-4 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-full bg-white text-[#262626]"
        >
          <ChevronRight aria-hidden="true" className="size-5" />
          <span className="sr-only">Next post</span>
        </button>
      )}
      <div className="h-[min(90dvh,900px)] w-full max-w-[1200px]">
        <PostDetail key={id} id={id} layout="modal" notFound={<p className="bg-canvas p-8 text-fg">This post is no longer available.</p>} />
      </div>
    </dialog>
  )
}

/**
 * The member app: its own shell, never the website's header or footer. Only people who
 * pass can_view_feed get it; for everyone else the API answers 404 and this renders the
 * website's ordinary 404 page. The loading state also looks like the website, so nothing
 * hints that the app exists.
 */
export function AppShell() {
  const location = useLocation()
  const { pathname } = location
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const tablet = useMediaQuery(MEDIA.tablet)
  const [state, setState] = useState<LoadState>({ status: 'loading' })
  const [composerOpen, setComposerOpen] = useState(false)
  const [postsVersion, setPostsVersion] = useState(0)
  const [panelOn, setPanelOn] = useState<{ panel: Panel; path: string }>({ panel: null, path: pathname })
  const [postUpdates, setPostUpdates] = useState<ReadonlyMap<string, FeedPost | null>>(new Map())

  // A panel belongs to the page it was opened on.
  const panel = panelOn.path === pathname && tablet ? panelOn.panel : null
  const setPanel = useCallback((next: Panel) => setPanelOn({ panel: next, path: pathname }), [pathname])

  const load = useCallback(async () => {
    try {
      setState({ status: 'ready', me: await members.me() })
    } catch (error) {
      setState(deniedOrError(error))
    }
  }, [])

  useEffect(() => {
    let active = true
    firstMe().then(
      (me) => active && setState({ status: 'ready', me }),
      (error: unknown) => active && setState(deniedOrError(error)),
    )
    return () => {
      active = false
    }
  }, [pathname])

  useEffect(() => {
    document.head.querySelector('meta[name="robots"]')?.setAttribute('content', 'noindex, nofollow')
  }, [pathname])

  const openPost = useCallback(
    (id: string, listIds?: string[]) => {
      if (!tablet) {
        navigate(`/members/p/${encodeURIComponent(id)}`)
        return
      }
      const next = new URLSearchParams(params)
      next.set('post', id)
      navigate({ pathname, search: `?${next}` }, { state: { postIds: listIds ?? [id], fromApp: true } satisfies PostState })
    },
    [tablet, navigate, params, pathname],
  )

  const me = state.status === 'ready' ? state.me : null
  const value = useMemo(
    () =>
      me && {
        me,
        refreshMe: load,
        setMe: (next: Me) => setState({ status: 'ready', me: next }),
        postsVersion,
        openPost,
        postUpdates,
        updatePost: (id: string, post: FeedPost | null) => setPostUpdates((current) => new Map(current).set(id, post)),
        patchPost: (base: FeedPost, change: (current: FeedPost) => FeedPost) =>
          setPostUpdates((current) => {
            const latest = current.has(base.id) ? current.get(base.id) : base
            if (!latest) return current
            return new Map(current).set(base.id, change(latest))
          }),
      },
    [me, load, postsVersion, openPost, postUpdates],
  )

  if (state.status === 'denied') {
    // The website's ordinary 404, header, footer and Leave included.
    return (
      <SiteFrame>
        <NotFoundPage />
      </SiteFrame>
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

  const modalPost = tablet ? params.get('post') : null
  const postState = (location.state ?? {}) as PostState
  const closePost = () => {
    if (postState.fromApp) {
      navigate(-1)
      return
    }
    const next = new URLSearchParams(params)
    next.delete('post')
    setParams(next, { replace: true })
  }

  return (
    <MembersContext.Provider value={value}>
      <div className="ig-app min-h-dvh pb-[calc(50px+env(safe-area-inset-bottom))] pt-11 md:pb-0 md:pl-[72px] md:pt-0 wide:pl-[245px]">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-on-primary"
        >
          Skip to content
        </a>
        <TopBar me={value.me} />
        <Sidebar me={value.me} panel={panel} onPanel={setPanel} onCreate={() => setComposerOpen(true)} />
        {panel && <SidePanel panel={panel} onClose={() => setPanel(null)} />}
        <main id="main" className="min-w-0">
          <Outlet />
        </main>
        <TabBar me={value.me} onCreate={() => setComposerOpen(true)} />
        <CreatePost
          open={composerOpen}
          fullScreen={!tablet}
          onClose={() => setComposerOpen(false)}
          onPosted={() => setPostsVersion((n) => n + 1)}
        />
        {modalPost && (
          <PostModal
            id={modalPost}
            ids={postState.postIds ?? [modalPost]}
            onClose={closePost}
            onStep={(id) => {
              const next = new URLSearchParams(params)
              next.set('post', id)
              navigate({ pathname, search: `?${next}` }, { replace: true, state: postState })
            }}
          />
        )}
        <ScrollRestoration />
      </div>
    </MembersContext.Provider>
  )
}
