import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import type { Page } from '@playwright/test'
import { apiLogin, confirmAge, expect, fixtures, PHOTO, seriousA11yViolations, test } from './support'

/**
 * Prompt 07 screenshots, saved to docs/screenshots/07/ at 390x844 and 1440x900, with
 * the checks that can be measured made here: light canvas, the right navigation for
 * the width, a 470px feed column, no follower counts, no like count for non-authors,
 * the quick exit in view, no sideways scrolling, and no serious or critical axe findings.
 */
const OUT = fileURLToPath(new URL('../../docs/screenshots/07/', import.meta.url))
mkdirSync(OUT, { recursive: true })

test.skip(process.env.E2E_SMOKE === '1', 'Screenshots use the end-to-end fixtures.')

function width(info: { project: { name: string } }) {
  return info.project.name === 'phone' ? 390 : 1440
}

async function prepare(page: Page, info: { project: { name: string } }) {
  if (info.project.name === 'desktop') await page.setViewportSize({ width: 1440, height: 900 })
}

async function settle(page: Page) {
  await page.waitForLoadState('networkidle')
  await page.evaluate(() => document.fonts.ready)
  await page.waitForTimeout(400)
}

async function noSidewaysScroll(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
}

async function snap(page: Page, name: string, info: { project: { name: string } }, fullPage = false) {
  // Park the pointer in an empty corner, so no hover state shows.
  if (info.project.name === 'desktop') await page.mouse.move(1439, 899)
  await settle(page)
  await noSidewaysScroll(page)
  // Every screen, dialog and step shown here is also checked with axe.
  expect(await seriousA11yViolations(page), name).toEqual([])
  await page.screenshot({ path: `${OUT}${name}-${width(info)}.png`, fullPage })
}

/** Checks shared by every member app screen. */
async function appChecks(page: Page, info: { project: { name: string } }) {
  const background = await page.locator('.ig-app').first().evaluate((element) => getComputedStyle(element).backgroundColor)
  expect(background).toBe('rgb(255, 255, 255)')
  const navigation = page.getByRole('navigation', { name: 'Members' })
  await expect(navigation).toBeVisible()
  const box = (await navigation.boundingBox())!
  if (info.project.name === 'phone') {
    // A bottom tab bar on phones.
    expect(box.y + box.height).toBeGreaterThanOrEqual(844 - 1)
    expect(box.height).toBeLessThanOrEqual(60)
  } else {
    // A 245px sidebar on the left from 1264px.
    expect(box.x).toBe(0)
    expect(box.width).toBe(245)
  }
  await expect(page.getByRole('link', { name: /Leave this site now/ }).first()).toBeVisible()
  await expect(page.getByText(/followers|following \d|\d+ following/i)).toHaveCount(0)
}

test.describe('Member app screenshots', () => {
  test.beforeEach(async ({ page, baseURL }, info) => {
    test.setTimeout(240_000)
    await prepare(page, info)
    await confirmAge(page.context(), baseURL!)
    await apiLogin(page, baseURL!, fixtures().showcase.viewer, fixtures().password)
  })

  test('home, posts and stories', async ({ page }, info) => {
    await page.goto('/members/feed')
    await expect(page.getByRole('region', { name: 'Stories' })).toBeVisible()
    await expect(page.getByRole('article').first()).toBeVisible()
    await appChecks(page, info)
    const column = await page.getByRole('article').first().boundingBox()
    expect(column!.width).toBeLessThanOrEqual(470)
    // Another member's post never shows its like count to this viewer.
    const others = page.getByRole('article').filter({ hasNot: page.getByText('e2e_night_owl', { exact: true }) })
    await expect(others.first().getByText(/^\d+ likes?$/)).toHaveCount(0)
    await snap(page, 'member-home-feed', info)

    // The post view: a modal on desktop, its own page on phones.
    await page
      .getByRole('article', { name: `Post by ${fixtures().showcase.viewer_handle}` })
      .filter({ hasText: 'Candlelight and a good book' })
      .getByRole('button', { name: /^View (all \d+ comments|1 comment)$/ })
      .click()
    if (info.project.name === 'phone') {
      await expect(page).toHaveURL(/\/members\/p\//)
      await snap(page, 'member-post-page', info)
    } else {
      const modal = page.getByRole('dialog', { name: 'Post' })
      await expect(modal).toBeVisible()
      await snap(page, 'member-post-modal', info)
    }

    await page.goto('/members/feed')
    await page.getByRole('region', { name: 'Stories' }).getByRole('button').first().click()
    await expect(page.getByRole('dialog', { name: /stories$/ })).toBeVisible()
    await snap(page, 'member-story-viewer', info)
  })

  test('profiles, saved and explore', async ({ page }, info) => {
    const { viewer_handle: me, other_handle: other } = fixtures().showcase
    await page.goto(`/members/u/${me}`)
    await expect(page.getByRole('heading', { level: 1, name: me })).toBeVisible()
    await expect(page.getByText(/^\d+ posts?$/)).toHaveCount(1)
    await appChecks(page, info)
    await snap(page, 'member-own-profile', info)

    await page.goto(`/members/u/${other}`)
    await expect(page.getByRole('button', { name: /^Follow(ing)?$/ })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Saved' })).toHaveCount(0)
    await snap(page, 'member-other-profile', info)

    await page.goto(`/members/u/${me}/saved`)
    await expect(page.getByText('Only you can see what you have saved.')).toBeVisible()
    const tiles = page.locator('ul.grid > li a')
    await expect(tiles.first()).toBeVisible()
    const [first, second] = await Promise.all([tiles.nth(0).boundingBox(), tiles.nth(1).boundingBox()])
    // 3:4 portrait tiles with 2px gaps.
    expect(Math.abs(first!.height / first!.width - 4 / 3)).toBeLessThan(0.02)
    expect(Math.round(second!.x - (first!.x + first!.width))).toBe(2)
    await snap(page, 'member-saved', info)

    await page.goto('/members/explore')
    await expect(tiles.first()).toBeVisible()
    await snap(page, 'member-explore', info)
  })

  test('search, notifications and settings', async ({ page }, info) => {
    if (info.project.name === 'phone') {
      await page.goto('/members/search')
      await page.getByRole('searchbox', { name: /Search members/ }).fill('e2e_amb')
    } else {
      await page.goto('/members/feed')
      await page.getByRole('button', { name: 'Search', exact: true }).click()
      await page.keyboard.type('e2e_amb')
    }
    await expect(page.getByRole('search').getByRole('link', { name: 'e2e_amber_glow' })).toBeVisible()
    await snap(page, 'member-search', info)

    if (info.project.name === 'phone') {
      await page.goto('/members/notifications')
    } else {
      await page.goto('/members/feed')
      await page.getByRole('button', { name: /^Notifications/ }).click()
    }
    await expect(page.getByRole('heading', { name: 'This week' })).toBeVisible()
    await snap(page, 'member-notifications', info)

    await page.goto('/members/settings')
    await expect(page.getByRole('radiogroup', { name: 'Appearance' })).toBeVisible()
    await appChecks(page, info)
    await snap(page, 'member-settings', info)
  })

  test('each create step', async ({ page }, info) => {
    await page.goto('/members/feed')
    await page.getByRole('button', { name: 'Create', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Create new post' })).toBeVisible()
    await snap(page, 'member-create-1-select', info)
    await page.locator('#composer-files').setInputFiles(PHOTO)
    await page.getByRole('button', { name: 'Next', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Crop & redact' })).toBeVisible()
    const surface = page.getByTestId('redaction-surface')
    const box = (await surface.boundingBox())!
    await page.mouse.move(box.x + box.width * 0.35, box.y + box.height * 0.3)
    await page.mouse.down()
    await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.55, { steps: 5 })
    await page.mouse.up()
    await snap(page, 'member-create-2-crop-redact', info)
    await page.getByRole('button', { name: 'Next', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Details' })).toBeVisible()
    await page.getByLabel('Describe photo 1').fill('Gold stripes on red')
    await page.getByRole('textbox', { name: /^Caption/ }).fill('A quiet evening in.')
    await page.getByLabel(/Everyone identifiable in these photos agreed/).check()
    await snap(page, 'member-create-3-details', info)
    await page.getByRole('button', { name: 'Next', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Share', exact: true })).toBeEnabled()
    await snap(page, 'member-create-4-share', info)
  })

  test('home feed in dark appearance', async ({ page }, info) => {
    await page.goto('/members/settings')
    await page.getByRole('radio', { name: 'Dark' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-appearance', 'dark')
    await page.goto('/members/feed')
    await expect(page.getByRole('article').first()).toBeVisible()
    await snap(page, 'member-home-feed-dark', info)
    // Back to light, so the next run starts from the default.
    await page.goto('/members/settings')
    await page.getByRole('radio', { name: 'Light' }).click()
    await expect(page.locator('html')).not.toHaveAttribute('data-appearance', 'dark')
  })
})

test.describe('Website screenshots (palette check)', () => {
  test.beforeEach(async ({ page }, info) => {
    test.setTimeout(240_000)
    await prepare(page, info)
  })

  test('public pages and the age gate', async ({ page, baseURL, request }, info) => {
    await page.goto('/')
    await snap(page, 'website-age-gate', info)
    await confirmAge(page.context(), baseURL!)
    const events = (await (await request.get('/api/events/')).json()) as Array<{ slug: string }>
    for (const [name, path] of [
      ['website-home', '/'],
      ['website-events', '/events'],
      ['website-event-detail', `/events/${events[0].slug}`],
      ['website-education', '/education'],
      ['website-visit', '/visit'],
      ['website-contact', '/contact'],
      ['website-join', '/join'],
    ]) {
      await page.goto(path)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
      await expect(page.locator('.ig-app')).toHaveCount(0)
      expect(await page.locator('body').evaluate((element) => getComputedStyle(element).backgroundColor)).toBe('rgb(255, 255, 255)')
      await expect(page.getByRole('link', { name: /Leave/ }).first()).toBeVisible()
      await snap(page, name, info, true)
    }
  })

  test('home for an entitled member shows "My feed"', async ({ page, baseURL }, info) => {
    await confirmAge(page.context(), baseURL!)
    await apiLogin(page, baseURL!, fixtures().showcase.viewer, fixtures().password)
    await page.goto('/')
    if (info.project.name === 'phone') {
      await page.getByRole('button', { name: 'Open menu' }).click()
    }
    const myFeed = page.getByRole('link', { name: 'My feed' })
    await expect(myFeed).toBeVisible()
    await myFeed.scrollIntoViewIfNeeded()
    await snap(page, 'website-home-member', info)
  })
})
