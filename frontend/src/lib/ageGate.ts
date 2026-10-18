const COOKIE_NAME = 'age_ok'
const MAX_AGE_SECONDS = 12 * 60 * 60

export function hasConfirmedAge(): boolean {
  return document.cookie.split('; ').some((part) => part === `${COOKIE_NAME}=1`)
}

export function confirmAge(): void {
  const secure = window.location.protocol === 'https:' ? '; Secure' : ''
  document.cookie = `${COOKIE_NAME}=1; Max-Age=${MAX_AGE_SECONDS}; Path=/; SameSite=Strict${secure}`
}

export const AGE_GATE_HOURS = MAX_AGE_SECONDS / 3600
