/**
 * Light, dark or automatic (follow the device) for the members area. The choice
 * is a convenience kept in this browser only and never sent anywhere. Storage
 * can be unavailable (private windows), so every access is guarded.
 */
export type Appearance = 'auto' | 'light' | 'dark'

const KEY = 'members-appearance'
const ORDER: Appearance[] = ['auto', 'light', 'dark']

export const APPEARANCE_LABELS: Record<Appearance, string> = {
  auto: 'Automatic',
  light: 'Light',
  dark: 'Dark',
}

export function storedAppearance(): Appearance {
  try {
    const value = window.localStorage.getItem(KEY)
    return value === 'light' || value === 'dark' ? value : 'auto'
  } catch {
    return 'auto'
  }
}

export function storeAppearance(appearance: Appearance) {
  try {
    if (appearance === 'auto') window.localStorage.removeItem(KEY)
    else window.localStorage.setItem(KEY, appearance)
  } catch {
    // Storage blocked: the choice still applies until the page is closed.
  }
}

export function nextAppearance(current: Appearance): Appearance {
  return ORDER[(ORDER.indexOf(current) + 1) % ORDER.length]
}
