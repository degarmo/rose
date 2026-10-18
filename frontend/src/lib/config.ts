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

export const config = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, ''),
  quickExitUrl: safeHttpsUrl(import.meta.env.VITE_QUICK_EXIT_URL, DEFAULT_QUICK_EXIT_URL),
  siteName: 'Rose',
}

export { safeHttpsUrl }
