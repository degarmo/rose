import type { Page } from '@playwright/test'
import { allowedHosts, expect, fixtures, mailLink, personPage, staffLogin, test, twoStepLogin, uniqueEmail, uniqueName } from './support'

const PASSWORD = 'a-long-e2e-password-42'

/** Admin pages in Rose's look, as the owner sees them. */
const ADMIN_PAGES = [
  '',
  'accounts/user/',
  'memberships/membership/',
  'memberships/payment/',
  'memberships/tier/',
  'memberships/membership/summary/',
  'events/event/',
  'events/event/add/',
  'events/event/rsvp-counts/',
  'journal/post/add/',
  'newsletter/newsletter/add/',
  'feed/feedpost/moderation/',
  'safety/memberaction/',
  'image-review/',
  'auth/group/',
  'pages/sitesettings/',
  'pages/siteimage/',
  'core/auditlog/',
  'staff-guide/',
]

interface Watch {
  offsite: string[]
  problems: string[]
}

function watch(page: Page, baseURL: string): Watch {
  const seen: Watch = { offsite: [], problems: [] }
  const allowed = allowedHosts(baseURL)
  page.on('request', (request) => {
    const url = request.url()
    if (url.startsWith('data:') || url.startsWith('blob:')) return
    if (!allowed.has(new URL(url).host)) seen.offsite.push(url)
  })
  page.on('console', (message) => {
    if (message.type() === 'error') seen.problems.push(message.text())
  })
  page.on('pageerror', (error) => seen.problems.push(error.message))
  return seen
}

test.describe('The admin in Rose’s look', () => {
  test('every admin page loads only from this site, with no script or style errors', async ({ browser, baseURL }) => {
    const data = fixtures()
    const page = await personPage(browser, baseURL!)
    const seen = watch(page, baseURL!)

    // The sign-in screens: the emblem and nothing else about the club.
    await page.goto(`${data.admin_path}login/`)
    await expect(page.locator('.rose-emblem').first()).toBeVisible()
    await expect(page.locator('#nav-sidebar')).toHaveCount(0)
    await twoStepLogin(page, data.owner)
    await expect(page.getByRole('heading', { name: 'Today' })).toBeVisible()

    for (const path of ADMIN_PAGES) {
      const response = await page.goto(`${data.admin_path}${path}`)
      expect(response?.status(), path).toBe(200)
      await page.waitForLoadState('networkidle')
      // Rose's fonts, not Django's or Unfold's defaults.
      const font = await page.evaluate(() => getComputedStyle(document.body).fontFamily)
      expect(font, path).toMatch(/^"?Manrope/)
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
      expect(overflow, path).toBeLessThanOrEqual(1)
    }

    // One member's page, with its tabs.
    await page.goto(`${data.admin_path}accounts/user/`)
    await page.locator('#result_list tbody tr a').first().click()
    const privateTab = page.getByRole('button', { name: 'Private details' })
    await expect(privateTab).toHaveAttribute('aria-pressed', 'false')
    await privateTab.focus()
    await page.keyboard.press('Enter')
    await expect(privateTab).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByLabel('Legal name')).toBeVisible()

    expect(seen.offsite, 'requests to other sites').toEqual([])
    expect(seen.problems, 'console errors (CSP included)').toEqual([])
    await page.context().close()
  })

  test('a door volunteer activates someone at the tablet door desk, as the admin would', async ({ browser, baseURL }) => {
    // Someone joins and gets their reference code.
    const member = await personPage(browser, baseURL!)
    const email = uniqueEmail('e2e.door')
    const name = uniqueName('tablet')
    await member.goto('/account/register')
    await member.getByLabel('Email').fill(email)
    await member.getByLabel('Display name').fill(name)
    await member.getByLabel('Password').fill(PASSWORD)
    await member.getByRole('button', { name: 'Create account' }).click()
    const link = new URL(await mailLink(email, '/account/verify#token='))
    await member.goto(link.pathname + link.hash)
    await expect(member.getByText('Your email is confirmed.')).toBeVisible()
    await member.goto('/account/login?next=%2Fjoin')
    await member.getByLabel('Email').fill(email)
    await member.getByLabel('Password').fill(PASSWORD)
    await member.getByRole('button', { name: 'Log in' }).click()
    await member.getByRole('button', { name: /^(Choose|Continue with) Rose$/ }).filter({ visible: true }).click()
    const agreement = member.getByRole('region', { name: 'Agreement text' })
    await agreement.evaluate((element) => element.scrollTo(0, element.scrollHeight))
    await expect(member.getByText('You have reached the end.')).toBeAttached()
    await member.getByLabel('I have read the agreement and I agree to it.').check()
    await member.getByLabel(/Type your full name to sign/).fill('Riley Testperson')
    await member.getByRole('button', { name: 'Agree and continue' }).click()
    await member.getByRole('button', { name: 'Get my reference code' }).click()
    await expect(member.getByText("You're in")).toBeVisible()
    const code = (await member.getByAltText(/QR code for/).getAttribute('alt'))!.replace('QR code for ', '')

    // The volunteer, after the two-step login, works from the staff section's door desk.
    const desk = await personPage(browser, baseURL!)
    const seen = watch(desk, baseURL!)
    await staffLogin(desk)
    await desk.goto('/members/staff/door')
    await expect(desk.getByRole('navigation', { name: 'Staff' }).getByRole('link')).toHaveText(['Door desk'])
    const search = desk.getByRole('search')
    await search.getByLabel('Reference code or display name').fill(code)
    await search.getByRole('button', { name: 'Search' }).click()
    const card = desk.getByRole('article', { name })
    await expect(card.getByText('ID check needed')).toBeVisible()
    await expect(desk.getByText('Riley Testperson')).toHaveCount(0)
    await card.getByRole('button', { name: 'Record payment and activate' }).click()
    const dialog = desk.getByRole('dialog', { name: 'Record payment and activate' })
    await expect(dialog.getByRole('button', { name: 'Record payment and activate' })).toBeDisabled()
    await dialog.getByLabel('Photo ID checked, 18+').check()
    await dialog.getByRole('button', { name: 'Record payment and activate' }).click()
    await expect(desk.getByText(`${code} is active.`)).toBeVisible()
    await expect(card.getByText('ID verified')).toBeVisible()

    // The signature name is shown only when asked for.
    await card.getByRole('button', { name: 'Show signature name' }).click()
    await expect(card.getByText('Riley Testperson')).toBeVisible()

    // The admin's membership list sees the same result.
    const data = fixtures()
    await desk.goto(`${data.admin_path}memberships/membership/?q=${code}`)
    await expect(desk.locator('#result_list tbody tr', { hasText: code }).getByText('Active', { exact: true })).toBeVisible()

    expect(seen.offsite).toEqual([])
    await member.context().close()
    await desk.context().close()
  })
})
