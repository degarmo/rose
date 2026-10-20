import { enterWebsiteCode, expect, fixtures, personPage, test } from './support'

test.describe('The owner', () => {
  test('logs in, lands on the dashboard with real numbers, then the inbox and the feed', async ({ browser, baseURL }) => {
    const { owner, password } = fixtures()
    const page = await personPage(browser, baseURL!)
    await page.goto('/account/login')
    await page.getByLabel('Email').fill(owner.email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Log in' }).click()

    // The authenticator code at sign-in, then straight to the admin dashboard (the only one).
    await enterWebsiteCode(page, owner.totp_secret)
    await expect(page).toHaveURL(new RegExp(`${fixtures().admin_path}$`))
    const active = page.locator('.rose-kpi', { hasText: 'Active members' })
    await expect(active.locator('.rose-kpi-value')).toHaveText(/\d/)
    await expect(page.getByRole('heading', { name: /^Members · / })).toBeVisible()
    await expect(page.locator('canvas').first()).toBeVisible()

    // The reports inbox has reports in it.
    await page.goto('/members/staff/reports')
    await expect(page.getByRole('tab', { name: 'Open' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.locator('main a[href^="/members/staff/reports/"]').first()).toBeVisible()

    // And the member feed opens, with posts.
    await page.goto('/members/feed')
    await expect(page.locator('main article').first()).toBeVisible()
    await page.context().close()
  })
})
