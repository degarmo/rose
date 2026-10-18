import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router'
import { AuthContext, type AuthState } from '@/components/layout/authContext'
import { ToastProvider } from '@/components/ui'
import type { Account } from '@/lib/api'

export const verifiedUser: Account = { display_name: 'night_owl', email: 'owl@example.org', email_verified: true }
export const unverifiedUser: Account = { ...verifiedUser, email_verified: false }

export function renderWithProviders(ui: ReactElement, { user = null as Account | null, path = '/' } = {}) {
  const auth: AuthState = {
    status: 'ready',
    user,
    applySession: () => undefined,
    refresh: async () => undefined,
    logout: async () => undefined,
  }
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthContext.Provider value={auth}>
        <ToastProvider>{ui}</ToastProvider>
      </AuthContext.Provider>
    </MemoryRouter>,
  )
}
