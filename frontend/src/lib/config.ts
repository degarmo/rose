const DEFAULT_QUICK_EXIT_URL = 'https://www.weather.gov/'

function safeHttpsUrl(value: string | undefined, fallback: string): string {
  if (!value) return fallback
  try {
    const url = new URL(value)
    return url.protocol === 'https:' ? url.toString() : fallback
  } catch {
    return fallback
  }
}

function fromPage(name: string): string {
  const meta = typeof document === 'undefined' ? null : document.querySelector(`meta[name="rose-site-${name}"]`)
  return meta?.getAttribute('content')?.trim() ?? ''
}

/**
 * The club's names. The server writes them into the page (`rose-site-display-name` and
 * `rose-site-short-name`, from the SITE_DISPLAY_NAME and SITE_SHORT_NAME settings or
 * Admin > Site settings), so they never live in the repository and are known before the
 * age gate makes any request. The Vite dev server, which serves the page itself, takes
 * VITE_SITE_DISPLAY_NAME and VITE_SITE_SHORT_NAME from .env.local instead.
 *
 * The neutral name is for discreet places: member-app tab titles and calendar files.
 */
const displayName = fromPage('display-name') || import.meta.env.VITE_SITE_DISPLAY_NAME?.trim() || 'Rose'
const shortName = fromPage('short-name') || import.meta.env.VITE_SITE_SHORT_NAME?.trim() || displayName
const neutralName = fromPage('neutral-name') || 'Rose'

export const config = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, ''),
  quickExitUrl: safeHttpsUrl(import.meta.env.VITE_QUICK_EXIT_URL, DEFAULT_QUICK_EXIT_URL),
  displayName,
  shortName,
  neutralName,
}

export { safeHttpsUrl }
