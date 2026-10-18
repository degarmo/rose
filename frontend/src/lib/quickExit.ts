import { config, safeHttpsUrl } from './config'

let overrideUrl: string | null = null

/** Site settings may replace the build-time default once they load. */
export function setQuickExitUrl(url: string | null | undefined) {
  overrideUrl = url ? safeHttpsUrl(url, config.quickExitUrl) : null
}

export function quickExitUrl(): string {
  return overrideUrl ?? config.quickExitUrl
}

/** Leave immediately, replacing this page in history so Back does not return here. */
export function leaveNow() {
  document.documentElement.style.visibility = 'hidden'
  document.title = 'New Tab'
  window.location.replace(quickExitUrl())
}

export const DOUBLE_ESCAPE_WINDOW_MS = 800
