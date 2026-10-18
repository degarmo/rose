import { createContext, useContext } from 'react'
import type { SiteSettings } from '@/lib/api'
import type { AsyncState } from '@/lib/useAsync'

export type SiteSettingsState = AsyncState<SiteSettings> & { retry: () => void }

export const SiteSettingsContext = createContext<SiteSettingsState | null>(null)

export function useSiteSettings(): SiteSettingsState {
  const context = useContext(SiteSettingsContext)
  if (!context) throw new Error('useSiteSettings must be used inside SiteSettingsProvider')
  return context
}
