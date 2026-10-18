import { createContext, useContext } from 'react'
import type { Account, Session } from '@/lib/api'

export interface AuthState {
  status: 'loading' | 'ready'
  user: Account | null
  /** Apply a session returned by login, logout, password or profile changes. */
  applySession: (session: Session) => void
  refresh: () => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
