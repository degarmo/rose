import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it } from 'vitest'
import { ToastProvider } from '@/components/ui'
import type { Account } from '@/lib/api'
import { verifiedUser } from '@/test/render'
import { AuthContext, type AuthState } from './authContext'
import { Layout } from './Layout'
import { SiteSettingsContext, type SiteSettingsState } from './siteSettingsContext'

const settings = { status: 'loading', retry: () => undefined } as SiteSettingsState

function renderSite(path: string, user: Account | null) {
  const auth: AuthState = { status: 'ready', user, applySession: () => undefined, refresh: async () => undefined, logout: async () => undefined }
  const router = createMemoryRouter([{ path: '/', element: <Layout />, children: [{ index: true, element: <p>Page body</p> }, { path: '*', element: <p>Page body</p> }] }], {
    initialEntries: [path],
  })
  render(
    <SiteSettingsContext.Provider value={settings}>
      <AuthContext.Provider value={auth}>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </AuthContext.Provider>
    </SiteSettingsContext.Provider>,
  )
}

const entitled = { ...verifiedUser, feed_access: true }

describe('website and member app boundary', () => {
  it.each(['/', '/events', '/journal', '/account'])('%s is the website, never the app shell, even for members', (path) => {
    renderSite(path, entitled)
    expect(screen.getByText('Page body')).toBeInTheDocument()
    expect(document.querySelector('.ig-app')).toBeNull()
    expect(screen.queryByRole('navigation', { name: 'Members', hidden: true })).not.toBeInTheDocument()
    expect(screen.getAllByRole('navigation', { name: 'Main', hidden: true }).length).toBeGreaterThan(0)
  })

  it('shows "My feed" to members the feed opens for', () => {
    renderSite('/', entitled)
    expect(screen.getAllByRole('link', { name: 'My feed', hidden: true })[0]).toHaveAttribute('href', '/members/feed')
  })

  it.each([
    ['visitors', null],
    ['signed-in people without feed access', verifiedUser],
  ])('hides "My feed" from %s', (_, user) => {
    renderSite('/', user)
    expect(screen.queryByRole('link', { name: 'My feed', hidden: true })).not.toBeInTheDocument()
  })
})
