import { useSyncExternalStore } from 'react'

/** True while the media query matches; follows resizes. False where matchMedia is missing. */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      if (typeof window.matchMedia !== 'function') return () => undefined
      const list = window.matchMedia(query)
      list.addEventListener('change', onChange)
      return () => list.removeEventListener('change', onChange)
    },
    () => typeof window.matchMedia === 'function' && window.matchMedia(query).matches,
    () => false,
  )
}

/** The app's widths: tablet rail from 768px, right rail from 1160px, labelled sidebar from 1264px. */
export const MEDIA = {
  tablet: '(min-width: 768px)',
  rail: '(min-width: 1160px)',
  wide: '(min-width: 1264px)',
} as const
