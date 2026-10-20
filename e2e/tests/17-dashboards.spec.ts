import type { Page } from '@playwright/test'
import { enterWebsiteCode, expect, fixtures, personPage, test, twoStepLogin } from './support'

/** The website login with the authenticator code, as each person would sign in. */
async function websiteLogin(page: Page, account: { email: string; totp_secret: string }) {
  await page.goto('/account/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(fixtures().password)
  await page.getByRole('button', { name: 'Log in' }).click()
  await enterWebsiteCode(page, account.totp_secret)
}

test.describe('One dashboard', () => {
  test('each role lands where it works', async ({ browser, baseURL }) => {
    const data = fixtures()
    const admin = await personPage(browser, baseURL!)
    await websiteLogin(admin, data.team.admin)
    await expect(admin).toHaveURL(new RegExp(`${data.admin_path}$`))
    await expect(admin.locator('.rose-kpi', { hasText: 'Revenue this month' })).toBeVisible()

    const moderator = await personPage(browser, baseURL!)
    await websiteLogin(moderator, data.team.moderator)
    await expect(moderator).toHaveURL(/\/members\/staff\/reports$/)
    // No figures in the staff section; Dashboard opens the admin, where a moderator sees
    // only what is waiting.
    await expect(moderator.getByText('Active members')).toHaveCount(0)
    await moderator.goto(data.admin_path)
    await expect(moderator.locator('.rose-kpi-label')).toHaveText(['Open reports', 'Posts awaiting approval', 'ID checks needed'])
    await expect(moderator.getByText('Revenue this month')).toHaveCount(0)

    const volunteer = await personPage(browser, baseURL!)
    await websiteLogin(volunteer, data.staff)
    await expect(volunteer).toHaveURL(/\/members\/staff\/door$/)

    for (const page of [admin, moderator, volunteer]) await page.context().close()
  })

  test('the staff section has no dashboard and the admin door desk sends people to it', async ({ browser, baseURL }) => {
    const data = fixtures()
    const page = await personPage(browser, baseURL!)
    await twoStepLogin(page, data.team.admin)
    await page.goto('/members/staff')
    await expect(page).toHaveURL(/\/members\/staff\/reports$/)
    const tabs = page.getByRole('navigation', { name: 'Staff' }).getByRole('link')
    await expect(tabs.last()).toHaveText(/^Dashboard/)
    await expect(tabs.filter({ hasText: /^Reports$/ })).toHaveCount(1)
    await page.goto(`${data.admin_path}memberships/membership/door-desk/`)
    await expect(page).toHaveURL(/\/members\/staff\/door$/)
    await page.context().close()
  })

  for (const width of [390, 1280, 1440, 1920]) {
    test(`nothing is cut off at ${width} wide`, async ({ browser, baseURL }) => {
      const page = await personPage(browser, baseURL!)
      await page.setViewportSize({ width, height: 900 })
      await twoStepLogin(page, fixtures().owner)
      await page.goto(fixtures().admin_path)
      const cards = page.locator('.rose-kpi')
      await expect(cards.first()).toBeVisible()
      const clipped = await cards.evaluateAll((elements) =>
        elements
          .map((card) => {
            const value = card.querySelector('.rose-kpi-value') as HTMLElement
            const box = card.getBoundingClientRect()
            const text = value.getBoundingClientRect()
            return value.scrollWidth > value.clientWidth + 1 || text.right > box.right + 1 ? card.textContent : null
          })
          .filter(Boolean),
      )
      expect(clipped).toEqual([])
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
      // Nor does any table hide a column in a sideways scroll.
      const hidden = await page.locator('.rose-table-wrap').evaluateAll((wraps) => wraps.filter((wrap) => wrap.scrollWidth > wrap.clientWidth + 1).length)
      expect(hidden).toBe(0)

      // The staff section's tabs, the Dashboard link among them, all sit inside the page.
      await page.goto('/members/staff/reports')
      const nav = page.getByRole('navigation', { name: 'Staff' })
      await expect(nav.getByRole('link').last()).toHaveText(/^Dashboard/)
      const outside = await nav.getByRole('link').evaluateAll((links) =>
        links.filter((link) => link.getBoundingClientRect().right > document.documentElement.clientWidth).map((link) => link.textContent),
      )
      expect(outside).toEqual([])
      await page.context().close()
    })
  }
})
