import type { Page, Response } from '@playwright/test'
import { allowedHosts, apiLogin, confirmAge, expect, fixtures, seriousA11yViolations, test } from './support'

const PUBLIC_ROUTES = [
  '/',
  '/about',
  '/events',
  '/education',
  '/journal',
  '/visit',
  '/contact',
  '/join',
  '/privacy',
  '/about/staff',
  '/guests',
  '/faq',
  '/house-rules',
  '/rentals',
  '/get-involved/volunteer',
  '/get-involved/donate',
  '/account/login',
  '/account/register',
  '/account/forgot',
  '/no-such-page',
]
const MEMBER_ROUTES = ['/account', '/members/feed', '/members/directory', '/members/notifications']

function expectDocumentHeaders(response: Response | null, referrer = 'no-referrer') {
  expect(response, 'navigation response').not.toBeNull()
  const headers = response!.headers()
  const csp = headers['content-security-policy'] ?? ''
  expect(csp).toContain("default-src 'self'")
  expect(csp).toContain("script-src 'self'")
  expect(csp).not.toMatch(/script-src[^;]*'unsafe-(inline|eval)'/)
  expect(csp).toContain("frame-ancestors 'none'")
  expect(headers['x-content-type-options']).toBe('nosniff')
  expect(headers['x-frame-options']).toBe('DENY')
  expect(headers['referrer-policy']).toBe(referrer)
  expect(headers['cross-origin-opener-policy']).toBe('same-origin')
  expect(headers['permissions-policy']).toContain('camera=()')
  expect(headers['permissions-policy']).toContain('geolocation=()')
}

interface Watch {
  offsite: string[]
  errors: string[]
}

/** Visit a route, failing on any request that leaves the site (or its storage
 * bucket) and on any browser console error, which includes CSP violations. */
async function visit(page: Page, path: string, watch: Watch) {
  const response = await page.goto(path, { waitUntil: 'networkidle' })
  await expect(page.locator('#root')).not.toBeEmpty()
  expect(watch.offsite, `requests leaving the site from ${path}`).toEqual([])
  expect(watch.errors, `console errors on ${path}`).toEqual([])
  return response
}

function watchRequests(page: Page, baseURL: string): Watch {
  const watch: Watch = { offsite: [], errors: [] }
  const allowed = allowedHosts(baseURL)
  page.on('request', (request) => {
    const url = request.url()
    if (url.startsWith('data:') || url.startsWith('blob:')) return
    if (!allowed.has(new URL(url).host)) watch.offsite.push(url)
  })
  page.on('console', (message) => {
    // The 404 page's own document is expected to be a 404.
    if (message.type() === 'error' && !/status of 404/.test(message.text())) watch.errors.push(message.text())
  })
  page.on('pageerror', (error) => watch.errors.push(error.message))
  return watch
}

test.describe('Privacy and accessibility on every page @smoke', () => {
  for (const path of PUBLIC_ROUTES) {
    test(`public ${path}`, async ({ page, baseURL }) => {
      await confirmAge(page.context(), baseURL!)
      const watch = watchRequests(page, baseURL!)
      const response = await visit(page, path, watch)
      expectDocumentHeaders(response)
      const robots = response!.headers()['x-robots-tag']
      if (path.startsWith('/account')) expect(robots).toBe('noindex, nofollow')
      expect(await seriousA11yViolations(page)).toEqual([])
    })
  }

  test('the age gate itself', async ({ page, baseURL }) => {
    const watch = watchRequests(page, baseURL!)
    const response = await visit(page, '/', watch)
    expectDocumentHeaders(response)
    await expect(page.getByRole('button', { name: 'I am 18 or older' })).toBeVisible()
    expect(await seriousA11yViolations(page)).toEqual([])
  })

  test('an event and a class page', async ({ page, baseURL, request }) => {
    await confirmAge(page.context(), baseURL!)
    const watch = watchRequests(page, baseURL!)
    const events = (await (await request.get('/api/events/')).json()) as Array<{ slug: string }>
    const classes = (await (await request.get('/api/education/opportunities/')).json()) as Array<{ slug: string }>
    for (const path of [`/events/${events[0].slug}`, ...(classes[0] ? [`/education/${classes[0].slug}`] : [])]) {
      expectDocumentHeaders(await visit(page, path, watch))
      expect(await seriousA11yViolations(page)).toEqual([])
    }
  })

  test('admin login page', async ({ page }) => {
    test.skip(process.env.E2E_SMOKE === '1', 'The admin path is private on staging.')
    const response = await page.goto(`${fixtures().admin_path}login/`)
    // Django's own admin forms need an Origin header, which no-referrer would null.
    expectDocumentHeaders(response, 'same-origin')
    expect(response!.headers()['x-robots-tag']).toBe('noindex, nofollow')
  })
})

test.describe('Members area', () => {
  test('member pages, and private images behind a short signed link', async ({ page, baseURL }, info) => {
    const data = fixtures().viewports[info.project.name]
    await confirmAge(page.context(), baseURL!)
    await apiLogin(page, baseURL!, data.feed.friend, fixtures().password)
    const watch = watchRequests(page, baseURL!)
    for (const path of MEMBER_ROUTES) {
      const response = await visit(page, path, watch)
      expectDocumentHeaders(response)
      expect(response!.headers()['x-robots-tag']).toBe('noindex, nofollow')
      expect(await seriousA11yViolations(page), path).toEqual([])
    }
    const feed = (await (await page.request.get('/api/members/feed/')).json()) as {
      results: Array<{ images: Array<{ url: string }> }>
    }
    const image = feed.results.flatMap((post) => post.images)[0]
    if (image) {
      const media = await page.request.get(image.url, { maxRedirects: 0 })
      expect(media.status()).toBe(302)
      expect(media.headers()['cache-control']).toBe('private, no-store, max-age=0')
      const signed = new URL(media.headers()['location'])
      expect(signed.searchParams.get('X-Amz-Expires')).toBe('60')
      expect(allowedHosts(baseURL!).has(signed.host)).toBe(true)
    }
  })

  test('feed paths are a plain 404 for people without access', async ({ page, baseURL }) => {
    await confirmAge(page.context(), baseURL!)
    for (const path of ['/api/members/feed/', '/api/members/directory/?q=e2e', '/api/account/feed/']) {
      const response = await page.request.get(path)
      expect(response.status(), path).toBe(404)
    }
  })
})
