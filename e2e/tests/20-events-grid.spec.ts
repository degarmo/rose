import type { Page } from '@playwright/test'
import { confirmAge, expect, seriousA11yViolations, test } from './support'

/** How many cards sit side by side in the grid's first row. */
async function columns(page: Page) {
  const cards = page.locator('main ul').getByRole('article')
  await expect(cards.first()).toBeVisible()
  const tops = await cards.evaluateAll((elements) => elements.slice(0, 4).map((element) => Math.round(element.getBoundingClientRect().top)))
  return tops.filter((top) => top === tops[0]).length
}

/** Where the banner's picture sits against its words: beside them, or above. */
async function bannerLayout(page: Page) {
  const banner = page.getByRole('article', { name: 'Grid evening 2' })
  await expect(banner).toBeVisible()
  const picture = await banner.locator(':scope > div').first().boundingBox()
  const words = await banner.locator(':scope > div').nth(1).boundingBox()
  return words!.x >= picture!.x + picture!.width - 1 ? 'side by side' : words!.y >= picture!.y + picture!.height - 1 ? 'stacked' : 'other'
}

test.describe('The Events grid', () => {
  test('a category that leaves the featured event out hides its banner', async ({ page, baseURL }) => {
    await confirmAge(page.context(), baseURL!)
    await page.goto('/events?category=special')
    await expect(page.locator('main ul').getByRole('article').first()).toBeVisible()
    await expect(page.getByRole('article', { name: 'Grid evening 2' })).toHaveCount(0)
    await page.goto('/')
    await expect(page.getByRole('article', { name: 'Grid evening 2' })).toBeVisible()
  })

  for (const [width, expected] of [
    [1440, 3],
    [800, 2],
    [390, 1],
  ] as const) {
    test(`${expected} column${expected > 1 ? 's' : ''} at ${width} wide, 15 cards, nothing sideways`, async ({ browser, baseURL }) => {
      const context = await browser.newContext({ baseURL, viewport: { width, height: 1000 } })
      await confirmAge(context, baseURL!)
      const page = await context.newPage()
      await page.goto('/events')
      expect(await columns(page)).toBe(expected)
      // The featured event's banner sits above the grid, and is not repeated in it.
      await expect(page.getByRole('main').getByRole('article', { name: 'Grid evening 2' })).toHaveCount(1)
      expect(await bannerLayout(page)).toBe(width >= 768 ? 'side by side' : 'stacked')
      await expect(page.locator('main ul').getByRole('article')).toHaveCount(15)
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
      await context.close()
    })
  }

  test('Load more adds 15 and moves the URL on; a card opens its event; no serious axe findings', async ({ page, baseURL }) => {
    await confirmAge(page.context(), baseURL!)
    await page.goto('/events')
    const cards = page.locator('main ul').getByRole('article')
    await expect(cards).toHaveCount(15)
    const total = Number((await page.getByText(/^Showing 1–15 of \d+$/).textContent())!.split(' of ')[1])
    expect(total).toBeGreaterThan(15)
    expect(await seriousA11yViolations(page)).toEqual([])

    await page.getByRole('button', { name: 'Load more' }).click()
    await expect(cards).toHaveCount(Math.min(30, total))
    await expect(page).toHaveURL(/[?&]page=2\b/)
    await expect(page.getByText(`Showing 1–${Math.min(30, total)} of ${total}`)).toBeVisible()

    // Pictures are WebP copies chosen from srcset; cards without one show their category's.
    await expect(cards.locator('img').first()).toHaveAttribute('srcset', /\.webp 400w/)
    expect(await page.locator('[data-fallback]').count()).toBeGreaterThan(0)

    // The back button returns to the first page.
    await page.goBack()
    await expect(page).not.toHaveURL(/page=2/)
    await expect(cards).toHaveCount(15)

    const first = cards.first()
    const title = (await first.getByRole('heading').textContent())!
    await first.click({ position: { x: 20, y: 20 } })
    await expect(page.getByRole('heading', { name: title, level: 1 })).toBeVisible()
  })
})
