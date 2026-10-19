import { readFileSync } from 'node:fs'
import { confirmAge, expect, fixtures, mailLink, mailLinks, personPage, test, uniqueEmail, uniqueName } from './support'

const PASSWORD = 'a-long-e2e-password-42'
const EXPORT_LINK = '/members/settings/privacy/export#token='

test.describe('Settings in the member app', () => {
  test('a plain account lands on Home, opens Settings and turns off event reminders', async ({ page, context, baseURL }) => {
    await confirmAge(context, baseURL!)
    const email = uniqueEmail('e2e.plain')
    const name = uniqueName('plain')
    await page.goto('/account/register')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Display name').fill(name)
    await page.getByLabel('Password').fill(PASSWORD)
    await page.getByRole('button', { name: 'Create account' }).click()
    const verify = new URL(await mailLink(email, '/account/verify#token='))
    await page.goto(verify.pathname + verify.hash)
    await expect(page.getByText('Your email is confirmed.')).toBeVisible()

    await page.goto('/account/login')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill(PASSWORD)
    await page.getByRole('button', { name: 'Log in' }).click()
    await expect(page).toHaveURL(/\/members\/home$/)
    await expect(page.getByRole('heading', { level: 1, name })).toBeVisible()
    await expect(page.getByText("You don't have a membership yet")).toBeVisible()
    await expect(page.getByRole('link', { name: 'See plans', exact: true })).toHaveAttribute('href', '/membership')
    // No feed for this account: its pages are the website's 404.
    await expect(page.locator('a[href="/members/explore"]')).toHaveCount(0)

    await page.locator('nav[aria-label="Members"]:visible').getByRole('link', { name: 'Settings' }).click()
    await expect(page).toHaveURL(/\/members\/settings$/)
    await page.getByRole('navigation', { name: 'Settings' }).getByRole('link', { name: /^Notifications/ }).click()
    await expect(page).toHaveURL(/\/members\/settings\/notifications$/)
    const reminders = page.getByRole('switch', { name: /Event reminders/ })
    await expect(reminders).toBeChecked()
    const saved = page.waitForResponse((response) => response.url().endsWith('/api/account/preferences/') && response.request().method() === 'PATCH')
    await reminders.click()
    expect((await saved).status()).toBe(200)
    await expect(page.getByRole('switch', { name: /Discreet subject lines/ })).toBeDisabled()
    await page.reload()
    await expect(page.getByRole('switch', { name: /Event reminders/ })).not.toBeChecked()

    const response = await page.goto('/members/feed')
    expect(response!.status()).toBe(200)
    await expect(page.getByRole('heading', { name: 'This room is not on the map.' })).toBeVisible()
  })

  test('a member asks for their data and downloads it from the emailed link', async ({ browser, baseURL }, info) => {
    const email = fixtures().viewports[info.project.name].feed.friend
    const page = await personPage(browser, baseURL!, email)
    const earlier = await mailLinks(email, EXPORT_LINK)
    await page.goto('/members/settings/privacy')
    await page.getByRole('button', { name: /Export my data/ }).click()
    await expect(page.getByText(/Your copy is being prepared|Your link is in your inbox/)).toBeVisible()

    const link = new URL(await mailLink(email, EXPORT_LINK, earlier))
    await page.goto(link.pathname + link.hash)
    await expect(page.getByRole('heading', { name: 'Your data' })).toBeVisible()
    const download = page.waitForEvent('download')
    await page.getByRole('button', { name: 'Download my data' }).click()
    const file = await download
    expect(file.suggestedFilename()).toBe('my-data.zip')
    expect(readFileSync(await file.path()).subarray(0, 2).toString()).toBe('PK')
    await expect(page.getByText('Your download has started. The link has now been used up.')).toBeVisible()
    // The token left the address bar, and the link works only once.
    await expect(page).toHaveURL(/\/members\/settings\/privacy\/export$/)
    await page.context().close()
  })
})
