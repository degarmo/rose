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

/**
 * The club's name. The server writes it into the page (`rose-site-name`, from the
 * SITE_NAME setting or Admin > Site settings), so it never lives in the repository and
 * is known before the age gate makes any request. The Vite dev server, which serves
 * the page itself, takes VITE_SITE_NAME from .env.local instead.
 */
function siteNameFromPage(): string {
  const meta = typeof document === 'undefined' ? null : document.querySelector('meta[name="rose-site-name"]')
  return meta?.getAttribute('content')?.trim() || import.meta.env.VITE_SITE_NAME?.trim() || 'Rose'
}

export const config = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, ''),
  quickExitUrl: safeHttpsUrl(import.meta.env.VITE_QUICK_EXIT_URL, DEFAULT_QUICK_EXIT_URL),
  siteName: siteNameFromPage(),
}

export { safeHttpsUrl }
