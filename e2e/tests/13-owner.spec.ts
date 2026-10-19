import { enterTwoStepCode, expect, fixtures, personPage, test } from './support'

test.describe('The owner', () => {
  test('logs in, lands on the dashboard with real numbers, then the inbox and the feed', async ({ browser, baseURL }) => {
    const { owner, password } = fixtures()
    const page = await personPage(browser, baseURL!)
    await page.goto('/account/login')
    await page.getByLabel('Email').fill(owner.email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Log in' }).click()

    // Straight to the staff section, which asks for the two-step login first.
    await expect(page).toHaveURL(/\/members\/staff$/)
    await expect(page.getByRole('heading', { name: 'Confirm it is you' })).toBeVisible()
    await page.getByRole('link', { name: 'Continue' }).click()
    await enterTwoStepCode(page, owner.totp_secret)

    // The dashboard, with numbers and bars rather than an empty page.
    await expect(page).toHaveURL(/\/members\/staff$/)
    await expect(page.getByText(/^Members · /)).toBeVisible()
    const active = page.getByRole('region', { name: /^Members · / }).locator('div', { hasText: /^Active members/ }).first()
    await expect(active).toContainText(/\d/)
    await expect(page.getByRole('figure').filter({ hasText: 'RSVPs' }).locator('.bg-primary').first()).toBeAttached()
    await expect(page.getByRole('figure').filter({ hasText: 'Revenue' }).locator('.bg-primary').first()).toBeAttached()

    // The reports inbox has reports in it.
    await page.getByRole('navigation', { name: 'Staff' }).getByRole('link', { name: 'Reports' }).click()
    await expect(page.getByRole('tab', { name: 'Open' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.locator('main a[href^="/members/staff/reports/"]').first()).toBeVisible()

    // And the member feed opens, with posts.
    await page.goto('/members/feed')
    await expect(page.locator('main article').first()).toBeVisible()
    await page.context().close()
  })
})
