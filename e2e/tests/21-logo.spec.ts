import { confirmAge, expect, test } from './support'

/** Every logo file is made by scripts/build_brand_assets.py; none is over 150 KB. */
const LARGEST_LOGO_FILE = 150 * 1024

test.describe('The logo', () => {
  test('the website header holds the emblem and Leave at every width, nothing sideways', async ({ browser, baseURL }) => {
    const context = await browser.newContext({ baseURL })
    await confirmAge(context, baseURL!)
    const page = await context.newPage()
    for (const width of [360, 390, 414, 768, 1023, 1024, 1279, 1280, 1440, 1920]) {
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/')
      const header = page.getByRole('banner')
      const logo = header.getByRole('link', { name: /./ }).filter({ has: page.locator('img[src^="/brand/emblem-"]') })
      const leave = header.getByRole('link', { name: /Leave/ }).first()
      await expect(logo, `${width}: the emblem`).toBeVisible()
      await expect(leave, `${width}: Leave`).toBeInViewport({ ratio: 1 })
      const emblem = (await logo.locator('img').boundingBox())!
      const exit = (await leave.boundingBox())!
      expect(Math.round(emblem.height), `${width}: emblem height`).toBe(width >= 1024 ? 44 : 36)
      expect(emblem.x + emblem.width, `${width}: the emblem clears Leave`).toBeLessThan(exit.x)
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), `${width}: sideways`).toBeLessThanOrEqual(0)
    }
    await context.close()
  })

  test('only the generated files load, each small, and the icons are served', async ({ page, baseURL, request }) => {
    await confirmAge(page.context(), baseURL!)
    const loaded: { path: string; bytes: number }[] = []
    page.on('requestfinished', async (finished) => {
      const sizes = await finished.sizes()
      loaded.push({ path: new URL(finished.url()).pathname, bytes: sizes.responseBodySize })
    })
    await page.goto('/')
    await expect(page.getByRole('banner').locator('img[src^="/brand/"]').first()).toBeVisible()
    await page.getByRole('contentinfo').scrollIntoViewIfNeeded()
    await page.waitForLoadState('networkidle')
    const logos = loaded.filter((entry) => entry.path.startsWith('/brand/'))
    expect(logos.length).toBeGreaterThan(0)
    for (const entry of logos) expect(entry.bytes, entry.path).toBeLessThan(LARGEST_LOGO_FILE)
    // The owner's source emblem never leaves their machine.
    expect(loaded.filter((entry) => /photos|neon/i.test(decodeURIComponent(entry.path)))).toEqual([])

    const icons = await page.locator('link[rel~="icon"], link[rel="apple-touch-icon"], link[rel="manifest"]').evaluateAll((links) => links.map((link) => link.getAttribute('href')))
    expect(icons).toEqual(['/favicon.ico', '/brand/favicon-32.png', '/brand/apple-touch-icon.png', '/manifest.webmanifest'])
    const favicon = await request.get('/favicon.ico')
    expect(favicon.headers()['content-type']).toBe('image/x-icon')
    const manifest = await request.get('/manifest.webmanifest')
    expect(manifest.headers()['content-type']).toContain('application/manifest+json')
    const { name, icons: manifestIcons } = await manifest.json()
    // The name under a home-screen icon is the neutral one (decision 502).
    expect(name).toBe('Rose')
    for (const icon of [...manifestIcons.map((entry: { src: string }) => entry.src), '/brand/apple-touch-icon.png', '/brand/favicon-32.png']) {
      const response = await request.get(icon)
      expect(response.status(), icon).toBe(200)
      expect(response.headers()['content-type'], icon).toBe('image/png')
    }
  })

  test('public pages preview the emblem when shared; the member app does not', async ({ request }) => {
    const visit = await (await request.get('/visit')).text()
    expect(visit).toMatch(/<meta property="og:image" content="https?:\/\/[^"]+\/brand\/og-image\.jpg" \/>/)
    const image = await request.get('/brand/og-image.jpg')
    expect(image.headers()['content-type']).toBe('image/jpeg')
    expect(await (await request.get('/members/feed')).text()).not.toContain('og:image')
  })
})
