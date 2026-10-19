import { api, type Account, type Appearance } from './api'

/**
 * Light or dark, for the website and the member app alike. Light is the default,
 * whatever the device prefers. Signed-in people keep their choice on their account;
 * a first-party cookie remembers it for this browser, so it also applies when nobody is
 * signed in and before the session check has answered.
 */
const COOKIE = 'appearance'
const ONE_YEAR = 60 * 60 * 24 * 365

export function cookieAppearance(): Appearance {
  return document.cookie.split('; ').includes(`${COOKIE}=dark`) ? 'dark' : 'light'
}

export function applyAppearance(appearance: Appearance) {
  const root = document.documentElement
  if (appearance === 'dark') root.dataset.appearance = 'dark'
  else delete root.dataset.appearance
  document.head
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', appearance === 'dark' ? '#0c0c0c' : '#ffffff')
}

function rememberAppearance(appearance: Appearance) {
  const secure = window.location.protocol === 'https:' ? '; Secure' : ''
  document.cookie = `${COOKIE}=${appearance}; Max-Age=${ONE_YEAR}; Path=/; SameSite=Lax${secure}`
}

/** Follow the signed-in account's choice, and remember it for this browser. */
export function adoptAccountAppearance(user: Account | null) {
  if (!user) return
  applyAppearance(user.appearance)
  rememberAppearance(user.appearance)
}

/** Change it now; saved on the account when someone is signed in. */
export async function chooseAppearance(appearance: Appearance, signedIn: boolean) {
  applyAppearance(appearance)
  rememberAppearance(appearance)
  return signedIn ? api.changeAppearance(appearance) : null
}
