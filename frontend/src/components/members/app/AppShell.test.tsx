import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { render } from '@testing-library/react'
import { useMemo, useState, type ReactNode } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext, type AuthState } from '@/components/layout/authContext'
import { SiteSettingsContext, type SiteSettingsState } from '@/components/layout/siteSettingsContext'
import { ToastProvider } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { makePost, me } from '@/test/members'
import { verifiedUser } from '@/test/render'
import { AppShell } from './AppShell'

const api = vi.hoisted(() => ({ me: vi.fn(), post: vi.fn(), comments: vi.fn(), stories: vi.fn() }))

vi.mock('@/lib/membersApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membersApi')>()
  // The shell's first access check goes through firstMe(), which would otherwise call the real client.
  return { ...actual, members: { ...actual.members, ...api }, firstMe: () => api.me() }
})

const auth: AuthState = {
  status: 'ready',
  user: { ...verifiedUser, feed_access: true },
  applySession: () => undefined,
  refresh: async () => undefined,
  logout: async () => undefined,
}

const settings = { status: 'loading', retry: () => undefined } as SiteSettingsState

/** The session as the app holds it; `refresh` reads `next` (what the server says now). */
function Session({ user, next, children }: { user: AuthState['user']; next: AuthState['user']; children: ReactNode }) {
  const [current, setCurrent] = useState(user)
  const value = useMemo(() => ({ ...auth, user: current, refresh: async () => setCurrent(next) }), [current, next])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

function renderApp(entry: string | { pathname: string; search?: string; state?: unknown }, user: AuthState['user'] = auth.user, next: AuthState['user'] = user) {
  const router = createMemoryRouter(
    [
      {
        path: '/members',
        element: <AppShell />,
        children: [
          { path: 'feed', element: <p>Feed content</p> },
          { path: 'home', element: <p>Home content</p> },
          { path: 'settings/:section', element: <p>Settings content</p> },
        ],
      },
      { path: '/account/login', element: <p>Login page</p> },
    ],
    { initialEntries: [entry] },
  )
  render(
    <SiteSettingsContext.Provider value={settings}>
      <Session user={user} next={next}>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </Session>
    </SiteSettingsContext.Provider>,
  )
  return router
}

const realMatchMedia = window.matchMedia

function screenWidth(px: number) {
  window.matchMedia = (query: string) =>
    ({
      matches: Number(/min-width: (\d+)px/.exec(query)?.[1] ?? Infinity) <= px,
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    }) as unknown as MediaQueryList
}

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset())
  api.comments.mockResolvedValue([])
})
afterEach(() => {
  window.matchMedia = realMatchMedia
})

describe('AppShell', () => {
  it('opens the app, in its own shell, for people the feed opens for', async () => {
    api.me.mockResolvedValue(me)
    renderApp('/members/feed')
    expect(await screen.findByText('Feed content')).toBeInTheDocument()
    expect(document.querySelector('.member-app')).not.toBeNull()
    expect(screen.getAllByRole('navigation', { name: 'Members', hidden: true }).length).toBeGreaterThan(0)
    // The website's header never appears inside the app.
    expect(screen.queryByRole('navigation', { name: 'Main', hidden: true })).not.toBeInTheDocument()
  })

  it('shows everyone else the website 404, with no trace of the app', async () => {
    api.me.mockRejectedValue(new ApiError(404, 'Not found'))
    renderApp('/members/feed')
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(/not on the map/i)
    expect(document.querySelector('.member-app')).toBeNull()
    expect(screen.queryByRole('navigation', { name: 'Members', hidden: true })).not.toBeInTheDocument()
    expect(screen.queryByText('Feed content')).not.toBeInTheDocument()
    // In the website's frame, so the quick exit is there as on every other page.
    expect(screen.getAllByRole('navigation', { name: 'Main', hidden: true }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: /Leave/ }).length).toBeGreaterThan(0)
  })

  describe('without feed access', () => {
    beforeEach(() => {
      api.me.mockRejectedValue(new ApiError(404, 'Not found'))
    })

    it.each(['/members/home', '/members/settings/privacy'])('opens %s in the app shell, with no feed in the navigation', async (path) => {
      renderApp(path, { ...verifiedUser, feed_access: false })
      expect(await screen.findByText(path === '/members/home' ? 'Home content' : 'Settings content')).toBeInTheDocument()
      expect(document.querySelector('.member-app')).not.toBeNull()
      const nav = screen.getAllByRole('navigation', { name: 'Members', hidden: true })[0]
      expect(within(nav).getByRole('link', { name: /Settings/, hidden: true })).toHaveAttribute('href', '/members/settings')
      expect(within(nav).queryByRole('link', { name: /Explore|Search|Notifications/, hidden: true })).not.toBeInTheDocument()
      // No feed request at all for an account the session says has no feed.
      expect(api.me).not.toHaveBeenCalled()
    })

    it('still answers feed pages with the website 404', async () => {
      renderApp('/members/feed', { ...verifiedUser, feed_access: false })
      expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(/not on the map/i)
      expect(screen.queryByText('Feed content')).not.toBeInTheDocument()
      expect(document.querySelector('.member-app')).toBeNull()
      expect(api.me).not.toHaveBeenCalled()
    })

    it('reads an old session again on the way in, and opens the feed it now allows', async () => {
      api.me.mockResolvedValue(me)
      renderApp('/members/feed', { ...verifiedUser, feed_access: false }, { ...verifiedUser, feed_access: true, member_app: 'open' })
      expect(await screen.findByText('Feed content')).toBeInTheDocument()
      expect(api.me).toHaveBeenCalledOnce()
    })

    it('asks someone signed out to log in, then come back', async () => {
      const router = renderApp('/members/settings/security', null)
      expect(await screen.findByText('Login page')).toBeInTheDocument()
      expect(router.state.location.search).toBe(`?next=${encodeURIComponent('/members/settings/security')}`)
    })
  })

  describe('post modal', () => {
    beforeEach(() => {
      screenWidth(1440)
      api.me.mockResolvedValue(me)
      api.post.mockImplementation(async (id: string) => makePost({ id, author: { handle: `author_${id}`, avatar: null } }))
    })

    it('steps through the list with the arrow keys', async () => {
      const router = renderApp({ pathname: '/members/feed', search: '?post=p1', state: { postIds: ['p0', 'p1', 'p2'] } })
      const dialog = await screen.findByRole('dialog', { name: 'Post' })
      expect(await within(dialog).findByRole('heading', { name: 'Post by author_p1' })).toBeInTheDocument()

      fireEvent.keyDown(dialog, { key: 'ArrowRight' })
      await waitFor(() => expect(router.state.location.search).toBe('?post=p2'))
      expect(await within(dialog).findByRole('heading', { name: 'Post by author_p2' })).toBeInTheDocument()

      // At the end of the list there is nothing further to the right.
      fireEvent.keyDown(dialog, { key: 'ArrowRight' })
      expect(router.state.location.search).toBe('?post=p2')

      fireEvent.keyDown(dialog, { key: 'ArrowLeft' })
      await waitFor(() => expect(router.state.location.search).toBe('?post=p1'))
    })

    it('leaves the arrow keys alone while typing a comment', async () => {
      const router = renderApp({ pathname: '/members/feed', search: '?post=p1', state: { postIds: ['p0', 'p1', 'p2'] } })
      const dialog = await screen.findByRole('dialog', { name: 'Post' })
      const input = await within(dialog).findByRole('textbox', { name: 'Add a comment' })
      fireEvent.keyDown(input, { key: 'ArrowRight' })
      expect(router.state.location.search).toBe('?post=p1')
    })

    it('closes with Escape', async () => {
      const router = renderApp({ pathname: '/members/feed', search: '?post=p1' })
      const dialog = await screen.findByRole('dialog', { name: 'Post' })
      // The native dialog fires "close" when Escape is pressed.
      act(() => {
        dialog.dispatchEvent(new Event('close'))
      })
      await waitFor(() => expect(router.state.location.search).toBe(''))
    })

    it('is a page, not a modal, on phones', async () => {
      screenWidth(390)
      renderApp({ pathname: '/members/feed', search: '?post=p1' })
      expect(await screen.findByText('Feed content')).toBeInTheDocument()
      expect(screen.queryByRole('dialog', { name: 'Post' })).not.toBeInTheDocument()
    })
  })
})
