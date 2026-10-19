/**
 * The design sweep: every public and member route, and every designed state, at 390x844
 * and 1440x900. For each page it records console errors, failed requests, third-party
 * requests, a blank view, sideways overflow, a covered or missing Leave control, missing
 * styles and serious or critical axe findings, then saves a screenshot to
 * docs/design/<folder>/. Designed screens are named like the reference images in
 * docs/design/reference/; other routes are named route--<path>-<viewport>.png. After the
 * pages it follows every internal link it saw and submits the public forms.
 *
 * Run it against a local app loaded with `seed_demo`:
 *
 *   node e2e/scripts/design-sweep.mjs --base http://localhost:5175 --out before \
 *     --accounts path/to/seed-output.txt --backend backend
 *
 * --accounts  the output of `manage.py seed_demo` (demo account emails and passwords)
 * --backend   the backend folder; the sweep creates one fresh verified account there to
 *             walk the join flow, using the same environment as the running server
 * CHROMIUM_PATH picks a Chromium build; without it the installed Chrome is used.
 */
import { execFileSync } from 'node:child_process'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import AxeBuilder from '@axe-core/playwright'
import { chromium } from 'playwright-core'

const args = {}
for (let index = 2; index < process.argv.length; index += 2) args[process.argv[index].replace(/^--/, '')] = process.argv[index + 1]
const base = args.base ?? 'http://localhost:5175'
const folder = args.out ?? 'before'
const only = args.only ? new RegExp(args.only) : null
const docs = resolve(fileURLToPath(new URL('../../docs/design/', import.meta.url)))
const out = resolve(docs, folder)
mkdirSync(out, { recursive: true })
const photo = fileURLToPath(new URL('../fixtures/photo.jpg', import.meta.url))

const VIEWPORTS = {
  phone: { width: 390, height: 844, isMobile: true, hasTouch: true },
  desktop: { width: 1440, height: 900 },
}

function accounts() {
  const text = readFileSync(args.accounts, 'utf8')
  const found = {}
  for (const match of text.matchAll(/^\s+(\S+@example\.org)\s+(\S+)\s+\((.+)\)$/gm)) found[match[3]] = { email: match[1], password: match[2] }
  return found
}

/** A fresh verified account with no membership, for walking the join flow. */
function freshAccount() {
  const email = `sweep.${Date.now().toString(36)}@example.org`
  const password = `sweep-${Date.now().toString(36)}-password`
  execFileSync(
    join(args.backend, '.venv/bin/python'),
    [
      'manage.py',
      'shell',
      '-c',
      `from apps.accounts.models import User; u = User.objects.create_user(email=${JSON.stringify(email)}, display_name="Jules " + ${JSON.stringify(Date.now().toString(36))}, password=${JSON.stringify(password)}); u.mark_email_verified()`,
    ],
    { cwd: args.backend, stdio: 'pipe' },
  )
  return { email, password }
}

const report = { base, folder, pages: [], links: [], forms: [] }
const allowedHost = new URL(base).host
const seenLinks = new Map()

function slugPath(path) {
  return path.replace(/^\//, '').replace(/[^a-z0-9]+/gi, '-').replace(/-$/, '') || 'home'
}

async function settle(page) {
  await page.waitForLoadState('load')
  await page.evaluate(() => document.fonts.ready)
  await page
    .waitForFunction(
      () =>
        [...document.images].every((image) => {
          const box = image.getBoundingClientRect()
          const onScreen = box.width > 0 && box.bottom > 0 && box.top < innerHeight && box.right > 0 && box.left < innerWidth
          return image.complete || !onScreen
        }),
      undefined,
      { timeout: 15_000 },
    )
    .catch(() => {})
  await page.waitForTimeout(500)
}

async function loadAllImages(page) {
  await page.evaluate(async () => {
    for (let y = 0; y < document.documentElement.scrollHeight; y += innerHeight / 2) {
      scrollTo(0, y)
      await new Promise((done) => setTimeout(done, 60))
    }
    scrollTo(0, 0)
  })
  await page.waitForFunction(() => [...document.images].every((image) => image.complete), undefined, { timeout: 15_000 }).catch(() => {})
}

/** Attaches listeners that collect problems while a page is open. */
function watch(page) {
  const problems = { console: [], failed: [], thirdParty: [] }
  page.on('console', (message) => {
    if (message.type() === 'error') problems.console.push(message.text().slice(0, 300))
  })
  page.on('pageerror', (error) => problems.console.push(`pageerror: ${error.message.slice(0, 300)}`))
  page.on('requestfailed', (request) => {
    const failure = request.failure()?.errorText ?? ''
    // Navigations and lazy images abandoned by the next page are not failures.
    if (!failure.includes('ERR_ABORTED')) problems.failed.push(`${request.method()} ${request.url()} ${failure}`)
  })
  page.on('response', (response) => {
    if (response.status() >= 400) problems.failed.push(`${response.request().method()} ${response.url()} ${response.status()}`)
  })
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (/^https?:$/.test(url.protocol) && url.host !== allowedHost) problems.thirdParty.push(request.url())
  })
  return problems
}

async function inspect(page) {
  return page.evaluate(() => {
    const candidates = [...document.querySelectorAll('a, button')].filter(
      (element) => /Leave/.test(element.textContent ?? '') || /Leave/.test(element.getAttribute('aria-label') ?? ''),
    )
    // Fine when any Leave control is on screen and nothing covers it.
    const states = candidates.map((leave) => {
      const box = leave.getBoundingClientRect()
      if (box.width === 0 || box.height === 0) return 'hidden'
      if (box.top >= innerHeight || box.bottom <= 0) return 'off screen'
      const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2)
      return hit && (leave === hit || leave.contains(hit)) ? 'ok' : 'covered'
    })
    const leaveState = states.includes('ok') ? 'ok' : (states.find((state) => state === 'covered') ?? states[0] ?? 'missing')
    const overflowing = [...document.querySelectorAll('body *')]
      .filter((element) => {
        const box = element.getBoundingClientRect()
        return box.width > 0 && box.right > document.documentElement.clientWidth + 1 && getComputedStyle(element).position !== 'fixed'
      })
      .slice(0, 5)
      .map((element) => `${element.tagName.toLowerCase()}.${String(element.className).split(' ').slice(0, 3).join('.')}`)
    const main = document.querySelector('main') ?? document.body
    return {
      title: document.title,
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      overflowing,
      textLength: (main.innerText ?? '').trim().length,
      notFound: Boolean(document.title.startsWith('Not found')),
      leave: leaveState,
      styled: document.styleSheets.length > 0 && getComputedStyle(document.body).fontFamily.length > 0 && getComputedStyle(document.body).margin === '0px',
      bodyFont: getComputedStyle(document.body).fontFamily,
      links: [...document.querySelectorAll('a[href^="/"]')].map((a) => a.getAttribute('href')),
    }
  })
}

async function axe(page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze()
  return results.violations
    .filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')
    .map((violation) => `${violation.id}: ${violation.nodes.slice(0, 4).map((node) => node.target.join(' ')).join(', ')}`)
}

/** Opens a page (or runs `steps` on an open one), checks it and saves a screenshot. */
async function shot(page, problems, { name, vp, path, steps, full = false, context, expectStatus, noLeave = false }) {
  if (only && !only.test(name)) return
  const entry = { name, vp, path, context }
  problems.console.length = 0
  problems.failed.length = 0
  problems.thirdParty.length = 0
  try {
    if (path) await page.goto(path)
    if (steps) await steps(page)
    if (vp === 'desktop') await page.mouse.move(1439, 899)
    if (full) await loadAllImages(page)
    await settle(page)
    Object.assign(entry, await inspect(page))
    // The neutral exit page carries nothing from the site, the Leave control included.
    if (noLeave) entry.leave = entry.leave === 'missing' ? 'ok' : 'present on the exit page'
    for (const link of entry.links) if (!seenLinks.has(link)) seenLinks.set(link, context)
    delete entry.links
    entry.axe = await axe(page)
    await page.screenshot({ path: join(out, `${name}.png`), fullPage: full })
  } catch (error) {
    entry.error = String(error.message ?? error).split('\n')[0]
  }
  // An expected status (the 404 for a member path) is also logged by the browser.
  entry.console = [...problems.console].filter((line) => !(expectStatus && line.includes(`status of ${expectStatus}`)))
  entry.failed = [...problems.failed].filter((line) => !(expectStatus && line.endsWith(` ${expectStatus}`)))
  entry.thirdParty = [...new Set(problems.thirdParty)]
  report.pages.push(entry)
  const flags = [
    entry.error && `ERROR ${entry.error}`,
    entry.console.length && `console ${entry.console.length}`,
    entry.failed.length && `failed ${entry.failed.length}`,
    entry.thirdParty.length && `third-party ${entry.thirdParty.length}`,
    entry.overflow && 'overflow',
    entry.textLength < 40 && 'blank?',
    entry.leave !== 'ok' && `leave ${entry.leave}`,
    entry.axe?.length && `axe ${entry.axe.length}`,
  ].filter(Boolean)
  console.log(`${flags.length ? '!!' : 'ok'} ${name} ${flags.join(', ')}`)
}

const sessions = new Map()

/** Signs in once per account (logins are rate limited) and reuses the cookies after that. */
async function login(context, account) {
  if (sessions.has(account.email)) {
    await context.addCookies(sessions.get(account.email))
    return
  }
  const page = await context.newPage()
  await page.goto(base + '/api/csrf/')
  const { csrfToken } = JSON.parse(await page.locator('body').innerText())
  const response = await context.request.post(base + '/api/account/login/', {
    data: { email: account.email, password: account.password },
    headers: { 'X-CSRFToken': csrfToken, Origin: base },
  })
  if (response.status() !== 200) throw new Error(`login ${account.email}: ${response.status()}`)
  sessions.set(account.email, (await context.cookies()).filter((cookie) => cookie.name !== 'age_ok' && cookie.name !== 'appearance'))
  await page.close()
}

async function newContext(browser, vp, { age = true, appearance } = {}) {
  const context = await browser.newContext({ viewport: VIEWPORTS[vp], isMobile: VIEWPORTS[vp].isMobile, hasTouch: VIEWPORTS[vp].hasTouch, baseURL: base, reducedMotion: 'reduce' })
  const cookies = []
  if (age) cookies.push({ name: 'age_ok', value: '1', url: base, sameSite: 'Strict' })
  if (appearance) cookies.push({ name: 'appearance', value: appearance, url: base, sameSite: 'Lax' })
  if (cookies.length) await context.addCookies(cookies)
  return context
}

const PUBLIC_ROUTES = [
  '/about',
  '/about/staff',
  '/guests',
  '/faq',
  '/house-rules',
  '/rentals',
  '/get-involved/volunteer',
  '/get-involved/donate',
  '/journal',
  '/privacy',
  '/subscribe/confirm',
  '/unsubscribe',
  '/events/cancel',
  '/account/login',
  '/account/register',
  '/account/forgot',
  '/account/reset',
  '/account/verify',
  '/exit',
  '/no-such-page',
  '/members/feed',
]

async function publicSweep(browser, vp, data) {
  // The age gate, before the cookie exists.
  {
    const context = await newContext(browser, vp, { age: false })
    const page = await context.newPage()
    const problems = watch(page)
    await shot(page, problems, { name: `site--age-gate-${vp}`, vp, path: '/', context: 'anonymous' })
    await context.close()
  }
  const context = await newContext(browser, vp)
  const page = await context.newPage()
  const problems = watch(page)
  const designed = [
    ['home', '/'],
    ['events', '/events'],
    ['event-detail', `/events/${data.event}`],
    ['education', '/education'],
    ['plan-your-visit', '/visit'],
  ]
  for (const [key, path] of designed) await shot(page, problems, { name: `site--${key}-${vp}`, vp, path, full: true, context: 'anonymous' })
  await shot(page, problems, {
    name: `site--events-${vp}-month-view`,
    vp,
    path: '/events',
    context: 'anonymous',
    steps: async (p) => {
      await p.getByRole('button', { name: 'Month' }).click()
      await p.waitForTimeout(800)
    },
  })
  await shot(page, problems, {
    name: `site--contact-${vp}`,
    vp,
    path: '/contact',
    context: 'anonymous',
    steps: async (p) => {
      const form = p.getByRole('form', { name: 'Contact form' })
      await form.locator('[name="name"]').fill('Jules')
      await form.locator('[name="email"]').fill('jules@')
      await form.locator('[name="message"]').click()
    },
  })
  await shot(page, problems, {
    name: `site--contact-${vp}-success`,
    vp,
    path: '/contact',
    context: 'anonymous',
    steps: async (p) => {
      const form = p.getByRole('form', { name: 'Contact form' })
      await form.locator('[name="name"]').fill('Jules')
      await form.locator('[name="email"]').fill('jules@example.com')
      const topic = form.locator('[name="topic"]')
      if ((await topic.evaluate((element) => element.tagName)) === 'SELECT') await topic.selectOption({ index: 1 })
      await form.locator('[name="message"]').fill('How does it work if I come alone and do not know anyone?')
      await form.getByRole('button', { name: /^Send/ }).click()
      await p.getByRole('status').or(p.getByRole('heading', { name: /Thanks|sent|got it/i })).first().waitFor({ timeout: 10_000 })
    },
  })
  await shot(page, problems, { name: `site--join-step-1-${vp}`, vp, path: '/join', full: true, context: 'anonymous' })
  await shot(page, problems, { name: `route--education-detail-${vp}`, vp, path: `/education/${data.opportunity}`, full: true, context: 'anonymous' })
  await shot(page, problems, { name: `route--journal-post-${vp}`, vp, path: `/journal/${data.journal}`, full: true, context: 'anonymous' })
  for (const path of PUBLIC_ROUTES) {
    await shot(page, problems, { name: `route--${slugPath(path)}-${vp}`, vp, path, full: true, context: 'anonymous', expectStatus: path.startsWith('/members') ? 404 : undefined, noLeave: path === '/exit' })
  }
  await context.close()
}

async function joinSweep(browser, vp) {
  const context = await newContext(browser, vp)
  await login(context, freshAccount())
  const page = await context.newPage()
  const problems = watch(page)
  await shot(page, problems, {
    name: `site--join-step-2-${vp}`,
    vp,
    path: '/join',
    context: 'verified',
    steps: async (p) => {
      // Desktop shows a card per tier; phones a list and one "Continue with …" button.
      await p.locator('button:visible', { hasText: /^(Choose|Continue with) / }).first().click()
      await p.waitForTimeout(600)
    },
  })
  await shot(page, problems, {
    name: `site--join-step-3-${vp}`,
    vp,
    context: 'verified',
    full: true,
    steps: async (p) => {
      const scroller = p.getByRole('region', { name: 'Agreement text' })
      await scroller.evaluate((element) => element.scrollTo(0, element.scrollHeight))
      await p.waitForTimeout(300)
      await p.getByRole('checkbox').first().check()
      await p.locator('[name="typed_name"]').fill('Jules Example')
      await p.getByRole('button', { name: /^(Sign|Agree) and continue$/ }).click()
      await p.waitForTimeout(600)
      const method = p.getByRole('radio', { name: /door|cash|person/i }).first()
      if (await method.count()) await method.check()
      await p.getByRole('button', { name: /reference code/i }).click()
      await p.waitForTimeout(1500)
    },
  })
  await shot(page, problems, { name: `route--account-${vp}`, vp, path: '/account', full: true, context: 'verified' })
  await context.close()
}

async function memberSweep(browser, vp, member, data, appearance) {
  const context = await newContext(browser, vp, { appearance })
  await login(context, member)
  const page = await context.newPage()
  const problems = watch(page)
  if (appearance === 'dark') {
    // The account's own setting wins over the cookie after sign-in, so set it, then put it back.
    const setAppearance = async (value) => {
      const { csrfToken } = await (await context.request.get(base + '/api/csrf/')).json()
      await context.request.patch(base + '/api/account/session/', { data: { appearance: value }, headers: { 'X-CSRFToken': csrfToken, Origin: base } })
    }
    await setAppearance('dark')
    await shot(page, problems, { name: `app--home-dark-${vp}`, vp, path: '/members/feed', context: 'member' })
    await setAppearance('light')
    await context.close()
    return
  }
  const ctx = 'member'
  await shot(page, problems, { name: `app--home-${vp}`, vp, path: '/members/feed', context: ctx })
  if (vp === 'desktop') {
    await shot(page, problems, {
      name: `app--post-detail-desktop-modal`,
      vp,
      path: `/members/feed?post=${data.ownPost}`,
      context: ctx,
      steps: (p) => p.getByRole('dialog').first().waitFor(),
    })
  } else {
    await shot(page, problems, { name: `app--post-detail-phone`, vp, path: `/members/p/${data.ownPost}`, context: ctx })
  }
  await shot(page, problems, {
    name: `app--story-${vp}`,
    vp,
    path: '/members/feed',
    context: ctx,
    steps: async (p) => {
      await p.getByRole('region', { name: 'Stories' }).getByRole('button').first().click()
      await p.getByRole('dialog').first().waitFor()
    },
  })
  await shot(page, problems, { name: `app--profile-own-${vp}`, vp, path: `/members/u/${data.handle}`, context: ctx })
  await shot(page, problems, { name: `app--profile-other-member-${vp}`, vp, path: `/members/u/${data.other}`, context: ctx })
  await shot(page, problems, { name: `app--explore-${vp}`, vp, path: '/members/explore', context: ctx })
  if (vp === 'desktop') {
    for (const [name, button] of [
      ['app--search-desktop-slide-out', /^Search$/],
      ['app--notifications-desktop-slide-out', /^Notifications/],
    ]) {
      await shot(page, problems, {
        name,
        vp,
        path: '/members/feed',
        context: ctx,
        steps: async (p) => {
          await p.getByRole('navigation', { name: 'Members' }).getByRole('button', { name: button }).click()
          await p.waitForTimeout(600)
        },
      })
    }
  } else {
    await shot(page, problems, {
      name: 'app--search-phone',
      vp,
      path: '/members/search',
      context: ctx,
      steps: async (p) => {
        await p.getByRole('searchbox').fill(data.other.slice(0, 3))
        await p.waitForTimeout(800)
      },
    })
    await shot(page, problems, { name: 'app--notifications-phone', vp, path: '/members/notifications', context: ctx })
  }
  await shot(page, problems, { name: `app--settings-${vp}`, vp, path: '/members/settings', context: ctx })
  await shot(page, problems, { name: `route--members-saved-${vp}`, vp, path: `/members/u/${data.handle}/saved`, context: ctx })
  await shot(page, problems, { name: `route--members-join-feed-${vp}`, vp, path: '/members/join-feed', context: ctx })
  await shot(page, problems, { name: `route--member-website-home-${vp}`, vp, path: '/', context: ctx, full: true })
  await shot(page, problems, { name: `route--member-event-detail-${vp}`, vp, path: `/events/${data.event}`, context: ctx, full: true })

  // Create, step by step.
  const names =
    vp === 'desktop'
      ? ['app--create-step-1-select-desktop-modal', 'app--create-desktop-step-2-in-context', 'app--create-step-3-details-desktop-modal', 'app--create-step-4-share-desktop-modal']
      : ['app--create-phone-step-1-select', 'app--create-phone-step-2-crop-redact', 'app--create-phone-step-3-details', 'app--create-phone-step-4-share']
  await shot(page, problems, {
    name: names[0],
    vp,
    path: '/members/feed',
    context: ctx,
    steps: async (p) => {
      await p.getByRole('button', { name: /^(Create|New post)$/ }).first().click()
      await p.waitForTimeout(600)
    },
  })
  await shot(page, problems, {
    name: names[1],
    vp,
    context: ctx,
    steps: async (p) => {
      await p.locator('input[type="file"]').first().setInputFiles(photo)
      await p.waitForTimeout(400)
      const next = p.getByRole('button', { name: 'Next', exact: true })
      if (await next.isVisible()) await next.click()
      await p.waitForTimeout(800)
      const surface = p.getByTestId('redaction-surface')
      const box = await surface.boundingBox()
      if (box) {
        await p.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.3)
        await p.mouse.down()
        await p.mouse.move(box.x + box.width * 0.55, box.y + box.height * 0.6, { steps: 5 })
        await p.mouse.up()
      }
    },
  })
  await shot(page, problems, {
    name: names[2],
    vp,
    context: ctx,
    steps: async (p) => {
      await p.getByRole('button', { name: 'Next', exact: true }).click()
      await p.waitForTimeout(600)
    },
  })
  await shot(page, problems, {
    name: names[3],
    vp,
    context: ctx,
    steps: async (p) => {
      const describe = p.getByLabel(/Describe photo/).first()
      if (await describe.count()) await describe.fill('Gold stripes on red')
      await p.getByRole('textbox', { name: /Caption/ }).fill('A quiet evening in.')
      await p.getByLabel(/Everyone identifiable/).check()
      const next = p.getByRole('button', { name: 'Next', exact: true })
      if (await next.isVisible()) await next.click()
      await p.getByRole('button', { name: 'Share', exact: true }).click()
      await p.waitForTimeout(2000)
    },
  })
  // Delete what Create shared, so the next run starts from the same feed.
  const { csrfToken } = await (await context.request.get(base + '/api/csrf/')).json()
  const own = await (await context.request.get(`${base}/api/members/u/${data.handle}/posts/`)).json()
  for (const post of (own.results ?? own).filter((item) => item.caption === 'A quiet evening in.')) {
    await context.request.delete(`${base}/api/members/posts/${post.id}/`, { headers: { 'X-CSRFToken': csrfToken, Origin: base } })
  }
  await context.close()
}

async function followLinks(browser, member) {
  for (const [context, vp] of [['anonymous', 'desktop'], ['member', 'desktop']]) {
    const ctx = await newContext(browser, vp)
    if (context === 'member') await login(ctx, member)
    const page = await ctx.newPage()
    for (const [link, from] of seenLinks) {
      if (from !== context || link.startsWith('/api') || link.startsWith('/media') || link.includes('#')) continue
      const response = await page.goto(link).catch((error) => ({ status: () => String(error.message).split('\n')[0] }))
      await page.waitForTimeout(400)
      const title = await page.title().catch(() => '')
      const ok = response?.status?.() === 200 && !title.startsWith('Not found')
      report.links.push({ link, context, ok, status: response?.status?.(), title })
      if (!ok) console.log(`!! link ${link} (${context}) ${title}`)
    }
    await ctx.close()
  }
}

async function forms(browser) {
  const context = await newContext(browser, 'desktop')
  const page = await context.newPage()
  const problems = watch(page)
  const check = async (name, run) => {
    problems.console.length = 0
    problems.failed.length = 0
    try {
      await run()
      report.forms.push({ name, ok: problems.failed.length === 0 && problems.console.length === 0, failed: [...problems.failed], console: [...problems.console] })
    } catch (error) {
      report.forms.push({ name, ok: false, error: String(error.message).split('\n')[0] })
    }
    console.log(`${report.forms.at(-1).ok ? 'ok' : '!!'} form ${name}`)
  }
  await check('newsletter sign-up (footer)', async () => {
    await page.goto('/')
    const footer = page.locator('footer')
    await footer.getByRole('textbox').first().fill(`sweep.${Date.now()}@example.org`)
    await footer.getByRole('button', { name: /Sign up|Subscribe/ }).click()
    await footer.getByText(/check your (inbox|email)|almost|confirm/i).first().waitFor({ timeout: 10_000 })
  })
  await check('log in with a wrong password', async () => {
    await page.goto('/account/login')
    await page.getByLabel(/Email/).fill('nobody@example.org')
    await page.getByLabel(/Password/).fill('not-the-password-123')
    await page.getByRole('button', { name: /^Log in/ }).click()
    await page.getByRole('alert').first().waitFor({ timeout: 10_000 })
    // The expected answer to a wrong password is a 400; only other failures count.
    const others = problems.failed.filter((line) => !/account\/login\/ 400$/.test(line))
    problems.failed.splice(0, problems.failed.length, ...others)
    const logged = problems.console.filter((line) => !line.includes('status of 400'))
    problems.console.splice(0, problems.console.length, ...logged)
  })
  await context.close()
}

async function discover(browser, member) {
  const context = await newContext(browser, 'desktop')
  await login(context, member)
  const get = async (path) => (await context.request.get(base + path)).json()
  const events = await get('/api/events/')
  const opportunities = await get('/api/education/opportunities/')
  const journal = await get('/api/journal/posts/')
  const me = await get('/api/members/me/')
  const own = await get(`/api/members/u/${me.handle}/posts/`)
  const feed = await get('/api/members/feed/?tab=everyone')
  const list = (value) => value.results ?? value
  const other = list(feed).map((post) => post.author?.handle).find((handle) => handle && handle !== me.handle)
  await context.close()
  return {
    event: list(events).find((event) => !event.members_only)?.slug ?? list(events)[0].slug,
    opportunity: list(opportunities)[0].slug,
    journal: list(journal)[0].slug,
    handle: me.handle,
    other,
    ownPost: list(own)[0]?.id,
  }
}

const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : { channel: 'chrome' })
try {
  const found = accounts()
  const member = found['feed member']
  const data = await discover(browser, member)
  console.log('data', JSON.stringify(data))
  for (const vp of ['desktop', 'phone']) {
    await publicSweep(browser, vp, data)
    if (args.backend) await joinSweep(browser, vp).catch((error) => console.log(`!! join flow ${vp}: ${String(error.message).split('\n')[0]}`))
    await memberSweep(browser, vp, member, data)
    await memberSweep(browser, vp, member, data, 'dark')
  }
  if (!only) {
    await followLinks(browser, member)
    await forms(browser)
  }
} finally {
  await browser.close()
  writeFileSync(join(out, 'sweep.json'), JSON.stringify(report, null, 2))
}
const bad = report.pages.filter((p) => p.error || p.console.length || p.failed.length || p.thirdParty.length || p.overflow || p.axe?.length || p.leave !== 'ok')
console.log(`${report.pages.length} pages, ${bad.length} with problems; ${report.links.filter((l) => !l.ok).length} broken links; ${report.forms.filter((f) => !f.ok).length} failing forms`)
