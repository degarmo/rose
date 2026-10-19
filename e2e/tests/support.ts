import { createHmac, randomInt } from 'node:crypto'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import AxeBuilder from '@axe-core/playwright'
import { test as base, expect, type Browser, type BrowserContext, type Page } from '@playwright/test'

export const FIXTURES_FILE = fileURLToPath(new URL('../.fixtures.json', import.meta.url))
/** The last authenticator code used, shared by every worker (phone and desktop run in turn). */
const LAST_CODE_FILE = fileURLToPath(new URL('../.last-totp-code', import.meta.url))
export const MAILPIT = process.env.E2E_MAILPIT_URL ?? 'http://localhost:8125'
export const PHOTO = fileURLToPath(new URL('../fixtures/photo.jpg', import.meta.url))

export interface Fixtures {
  password: string
  admin_path: string
  staff: { email: string; totp_secret: string }
  viewports: Record<string, { feed: { poster: string; friend: string }; events: Record<string, string> }>
  /** A filled-in member app for the screenshot tests. */
  showcase: { viewer: string; viewer_handle: string; other_handle: string }
}

export function fixtures(): Fixtures {
  return JSON.parse(readFileSync(FIXTURES_FILE, 'utf8')) as Fixtures
}

/** Hosts a page may contact: the site itself and the storage bucket. */
export function allowedHosts(baseURL: string): Set<string> {
  const extra = (process.env.E2E_ALLOWED_HOSTS ?? 'localhost:9100').split(',').filter(Boolean)
  return new Set([new URL(baseURL).host, ...extra])
}

/**
 * Every test gets its own made-up client address (the e2e stack trusts one
 * proxy hop), so per-IP rate limits never leak between tests.
 */
export const test = base.extend<{ clientIp: string }>({
  clientIp: async ({}, use) => {
    await use(`10.${randomInt(1, 250)}.${randomInt(1, 250)}.${randomInt(1, 250)}`)
  },
  context: async ({ context, clientIp }, use) => {
    await context.setExtraHTTPHeaders({ 'X-Forwarded-For': clientIp })
    await use(context)
  },
})
export { expect }

export async function confirmAge(context: BrowserContext, baseURL: string) {
  await context.addCookies([{ name: 'age_ok', value: '1', url: baseURL, sameSite: 'Strict' }])
}

export function uniqueEmail(prefix: string) {
  return `${prefix}.${Date.now().toString(36)}${randomInt(1000, 9999)}@example.org`
}

export function uniqueName(prefix: string) {
  return `${prefix}_${Date.now().toString(36)}${randomInt(10, 99)}`.slice(0, 30)
}

/** The newest link to `path` in mail sent to `to`, read from Mailpit's API. */
export async function mailLink(to: string, path: string): Promise<string> {
  for (let attempt = 0; attempt < 40; attempt++) {
    const search = await fetch(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:"${to}"`)}`)
    const { messages } = (await search.json()) as { messages: Array<{ ID: string }> }
    for (const message of messages ?? []) {
      const detail = (await (await fetch(`${MAILPIT}/api/v1/message/${message.ID}`)).json()) as { Text: string }
      const match = detail.Text.match(new RegExp(`https?://\\S+${path.replace(/[/#]/g, '\\$&')}\\S*`))
      if (match) return match[0]
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(`No mail to ${to} with a ${path} link`)
}

export async function mailSubjects(to: string): Promise<string[]> {
  const search = await fetch(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:"${to}"`)}`)
  const { messages } = (await search.json()) as { messages: Array<{ Subject: string }> }
  return (messages ?? []).map((message) => message.Subject)
}

/** RFC 6238 time-based code, as an authenticator app would show it. */
export function totp(base32: string, at = Date.now()): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
  let bits = ''
  for (const char of base32.replace(/=+$/, '')) bits += alphabet.indexOf(char).toString(2).padStart(5, '0')
  const key = Buffer.from((bits.match(/.{8}/g) ?? []).map((byte) => parseInt(byte, 2)))
  const counter = Buffer.alloc(8)
  counter.writeBigUInt64BE(BigInt(Math.floor(at / 1000 / 30)))
  const digest = createHmac('sha1', key).update(counter).digest()
  const offset = digest[digest.length - 1] & 0xf
  const code = (digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000
  return code.toString().padStart(6, '0')
}

/** Sign in through the API (faster than the form) with the page's own cookies. */
export async function apiLogin(page: Page, baseURL: string, email: string, password: string) {
  const csrf = (await (await page.request.get('/api/csrf/')).json()) as { csrfToken: string }
  const response = await page.request.post('/api/account/login/', {
    data: { email, password },
    headers: { 'X-CSRFToken': csrf.csrfToken, Origin: new URL(baseURL).origin },
  })
  expect(response.status(), await response.text()).toBe(200)
}

/** Serious and critical accessibility problems on the current page. */
export async function seriousA11yViolations(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
  return results.violations
    .filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')
    .map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(', ')}`)
}

/** A code that has not been used yet: the server refuses a code twice in its 30 seconds. */
async function freshCode(secret: string): Promise<string> {
  const lastCode = existsSync(LAST_CODE_FILE) ? readFileSync(LAST_CODE_FILE, 'utf8') : ''
  let code = totp(secret)
  while (code === lastCode) {
    await new Promise((resolve) => setTimeout(resolve, 1000))
    code = totp(secret)
  }
  writeFileSync(LAST_CODE_FILE, code)
  return code
}

/** Open the admin with the two-step login, as door staff would. */
export async function staffLogin(page: Page) {
  const data = fixtures()
  await page.goto(`${data.admin_path}login/`)
  await page.getByLabel('Email').fill(data.staff.email)
  await page.getByLabel('Password').fill(data.password)
  await page.getByRole('button', { name: 'Continue' }).click()
  await page.getByLabel(/Six-digit code/).fill(await freshCode(data.staff.totp_secret))
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page.getByRole('link', { name: 'Door desk' }).first()).toBeVisible()
}

/** A separate signed-in browser (a second person), with its own client address. */
export async function personPage(browser: Browser, baseURL: string, email?: string): Promise<Page> {
  const ip = `10.${randomInt(1, 250)}.${randomInt(1, 250)}.${randomInt(1, 250)}`
  const context = await browser.newContext({ baseURL, extraHTTPHeaders: { 'X-Forwarded-For': ip } })
  await confirmAge(context, baseURL)
  const page = await context.newPage()
  if (email) await apiLogin(page, baseURL, email, fixtures().password)
  return page
}
