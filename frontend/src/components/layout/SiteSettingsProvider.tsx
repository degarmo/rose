import { useEffect, type ReactNode } from 'react'
import { api } from '@/lib/api'
import { setQuickExitUrl } from '@/lib/quickExit'
import { useAsync } from '@/lib/useAsync'
import { SiteSettingsContext } from './siteSettingsContext'

export function SiteSettingsProvider({ children }: { children: ReactNode }) {
  const state = useAsync(() => api.siteSettings(), 'site-settings')

  useEffect(() => {
    if (state.status === 'success') setQuickExitUrl(state.data.quick_exit_url)
  }, [state.status, state.data])

  return <SiteSettingsContext.Provider value={state}>{children}</SiteSettingsContext.Provider>
}
