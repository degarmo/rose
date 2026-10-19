import type { Page } from '@playwright/test'
import { loadAllImages, screenshotFolder, useShotViewport } from './screenshots'
import { apiLogin, confirmAge, expect, fixtures, test } from './support'

/**
 * Prompt 07b screenshots, saved to docs/screenshots/07b/ at 390x844 and 1440x900, with
 * each checklist item measured: the website's journal strip has pictures, the phone
 * profile header is laid out as asked, the tabs sit 8px under the stories, the sample
 * pictures are light and varied, and the Leave control covers nothing.
 */
const snap = screenshotFolder('07b')

test.skip(process.env.E2E_SMOKE === '1', 'Screenshots use the end-to-end fixtures.')

/**
 * Average brightness (0 to 255) of each image matching `selector`. The bytes are fetched
 * with the signed-in session and measured from a local blob, because the pictures come
 * from the storage host and a page may not read pixels from another origin.
 */
async function brightness(page: Page, selector: string) {
  const sources = await page
    .locator(selector)
    .evaluateAll((images) => images.map((image) => (image as HTMLImageElement).getAttribute('src') ?? ''))
  const values: number[] = []
  for (const source of sources) {
    const body = await (await page.request.get(source)).body()
    values.push(
      await page.evaluate(async (bytes) => {
        const bitmap = await createImageBitmap(new Blob([new Uint8Array(bytes)]))
        const canvas = document.createElement('canvas')
        canvas.width = 32
        canvas.height = 32
        const context = canvas.getContext('2d')!
        context.drawImage(bitmap, 0, 0, 32, 32)
        const { data } = context.getImageData(0, 0, 32, 32)
        let total = 0
        for (let i = 0; i < data.length; i += 4) total += 0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2]
        return total / (data.length / 4)
      }, [...body]),
    )
  }
  return values
}

test.describe('Member app polish', () => {
  test.beforeEach(async ({ page, baseURL }, info) => {
    test.setTimeout(240_000)
    await useShotViewport(page, info)
    await confirmAge(page.context(), baseURL!)
    await apiLogin(page, baseURL!, fixtures().showcase.viewer, fixtures().password)
  })

  test('home feed: tabs close under the stories, light pictures', async ({ page }, info) => {
    await page.goto('/members/feed')
    const stories = page.getByRole('region', { name: 'Stories' })
    await expect(stories.getByRole('button').first()).toBeVisible()
    await expect(page.getByRole('article').first()).toBeVisible()

    const story = stories.getByRole('button').first()
    const circle = await story.locator('span').first().boundingBox()
    // 64px at every width (design: story circles).
    expect(circle!.width).toBe(64)
    // The button ends at the bottom of its visible label.
    const label = await story.boundingBox()
    const tabs = await page.getByRole('tablist', { name: 'Feed' }).boundingBox()
    const gap = tabs!.y - (label!.y + label!.height)
    expect(gap).toBeGreaterThanOrEqual(6)
    // Design: 12px on phones; 8px under the tray plus the column's 12px gap from 768px.
    expect(gap).toBeLessThanOrEqual(info.project.name === 'phone' ? 12 : 20)

    const light = await brightness(page, 'article img[src*="/api/members/media/"]')
    expect(light.length).toBeGreaterThan(0)
    expect(Math.min(...light)).toBeGreaterThan(170)
    await snap(page, 'member-home-feed', info)
  })

  test('own profile header', async ({ page }, info) => {
    const me = fixtures().showcase.viewer_handle
    await page.goto(`/members/u/${me}`)
    await expect(page.getByRole('heading', { level: 1, name: me })).toBeVisible()
    if (info.project.name === 'phone') {
      // The handle is the top bar's title; the profile header holds the rest.
      const header = page.locator('header').filter({ has: page.getByText(/^posts?$/) })
      const avatar = (await header.locator('span.rounded-full').first().boundingBox())!
      const stats = (await header.getByText(/^posts?$/).locator('..').boundingBox())!
      const heading = (await header.getByRole('region', { name: 'About' }).getByText(me, { exact: true }).boundingBox())!
      const edit = (await page.getByRole('button', { name: 'Edit profile' }).boundingBox())!
      const settings = (await page.getByRole('link', { name: 'Settings', exact: true }).last().boundingBox())!
      expect(avatar.width).toBe(77)
      // Posts count to the right of the avatar, centred on it.
      expect(stats.x).toBeGreaterThan(avatar.x + avatar.width)
      expect(Math.abs(stats.y + stats.height / 2 - (avatar.y + avatar.height / 2))).toBeLessThan(4)
      // Name below that row, buttons below the name, side by side, filling the width.
      expect(heading.y).toBeGreaterThan(avatar.y + avatar.height)
      expect(edit.y).toBeGreaterThan(heading.y)
      expect(Math.abs(edit.y - settings.y)).toBeLessThan(1)
      expect(Math.abs(edit.width - settings.width)).toBeLessThan(2)
      expect(edit.x).toBeLessThan(20)
      expect(settings.x + settings.width).toBeGreaterThan(390 - 20)
    }
    await snap(page, 'member-own-profile', info)
  })

  test("another member's profile", async ({ page }, info) => {
    await page.goto(`/members/u/${fixtures().showcase.other_handle}`)
    await expect(page.getByRole('button', { name: 'Profile options' })).toBeVisible()
    await snap(page, 'member-other-profile', info)
  })

  test('explore: light, varied pictures', async ({ page }, info) => {
    await page.goto('/members/explore')
    const tiles = page.locator('ul.grid > li img')
    await expect(tiles.first()).toBeVisible()
    await loadAllImages(page)
    const light = await brightness(page, 'ul.grid > li img')
    expect(Math.min(...light)).toBeGreaterThan(170)
    // No two tiles show the same picture (each is a different stored image).
    const sources = await tiles.evaluateAll((images) => images.map((image) => (image as HTMLImageElement).currentSrc))
    expect(new Set(sources).size).toBe(sources.length)
    expect(sources.length).toBeGreaterThanOrEqual(12)
    await snap(page, 'member-explore', info)
  })

  test('post modal', async ({ page }, info) => {
    test.skip(info.project.name === 'phone', 'Phones open posts as a page, not a modal.')
    await page.goto('/members/feed')
    await page
      .getByRole('article', { name: `Post by ${fixtures().showcase.viewer_handle}` })
      .filter({ hasText: 'Candlelight and a good book' })
      .getByRole('button', { name: /^View (all \d+ comments|1 comment)$/ })
      .click()
    await expect(page.getByRole('dialog', { name: 'Post' })).toBeVisible()
    await snap(page, 'member-post-modal', info)
  })
})

test.describe('Website polish', () => {
  test('home: journal strip filled, Leave covers nothing', async ({ page, baseURL }, info) => {
    test.setTimeout(240_000)
    await useShotViewport(page, info)
    await confirmAge(page.context(), baseURL!)
    await page.goto('/')
    const strip = page.getByRole('list', { name: 'Latest journal posts' })
    await strip.scrollIntoViewIfNeeded()
    await expect(strip.locator('img').first()).toBeVisible()
    await expect
      .poll(() => strip.locator('img').evaluateAll((images) => images.every((image) => (image as HTMLImageElement).naturalWidth > 0)))
      .toBe(true)

    // The Leave control lives in the header, clear of every section of the page.
    const leave = page.getByRole('link', { name: /Leave/ }).first()
    await expect(leave).toBeVisible()
    const leaveBox = (await leave.boundingBox())!
    const headerBox = (await page.locator('header').first().boundingBox())!
    expect(leaveBox.y + leaveBox.height).toBeLessThanOrEqual(headerBox.y + headerBox.height)
    await page.evaluate(() => window.scrollTo(0, 0))
    await snap(page, 'website-home', info, true)
  })
})
