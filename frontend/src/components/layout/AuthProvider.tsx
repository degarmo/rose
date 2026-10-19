import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, firstSession, noteSession, type Account, type Session } from '@/lib/api'
import { adoptAccountAppearance } from '@/lib/appearance'
import { AuthContext, type AuthState } from './authContext'

/** Session cookie auth. Nothing about the account is stored in the browser. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthState['status']>('loading')
  const [user, setUser] = useState<Account | null>(null)

  const applySession = useCallback((session: Session) => {
    noteSession()
    setUser(session.user)
    setStatus('ready')
    adoptAccountAppearance(session.user)
  }, [])

  const refresh = useCallback(async () => {
    try {
      applySession(await api.session())
    } catch {
      setUser(null)
      setStatus('ready')
    }
  }, [applySession])

  const logout = useCallback(async () => {
    applySession(await api.logout())
  }, [applySession])

  useEffect(() => {
    let active = true
    firstSession().then(
      (session) => active && applySession(session),
      () => {
        if (!active) return
        setUser(null)
        setStatus('ready')
      },
    )
    return () => {
      active = false
    }
  }, [applySession])

  const value = useMemo(
    () => ({ status, user, applySession, refresh, logout }),
    [status, user, applySession, refresh, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
