import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, type Account, type Session } from '@/lib/api'
import { AuthContext, type AuthState } from './authContext'

/** Session cookie auth. Nothing about the account is stored in the browser. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthState['status']>('loading')
  const [user, setUser] = useState<Account | null>(null)

  const applySession = useCallback((session: Session) => {
    setUser(session.user)
    setStatus('ready')
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
    api.session().then(
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
