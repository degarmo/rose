import { confirmAge, deskAction, deskSearch, expect, fixtures, mailLink, personPage, staffLogin, test, uniqueEmail, uniqueName } from './support'

const PASSWORD = 'a-long-e2e-password-42'

const PLANS = ['Community', 'First Fridays', 'Limited', 'Trial', 'Limited +', 'Rose', 'Rose +']

test.describe('Membership plans', () => {
  test('lists the seven plans in price order @smoke', async ({ page, baseURL }) => {
    await confirmAge(page.context(), baseURL!)
    const tiers = await page.request.get('/api/membership/tiers/')
    expect(tiers.status()).toBe(200)
    await page.goto('/membership')
    const cards = page.getByRole('region', { name: 'Plans', exact: true }).getByRole('heading', { level: 2 })
    await expect(cards).toHaveText(PLANS)
    await expect(page.getByText('Membership plans did not load')).toHaveCount(0)
  })

  test('from the plans page to a door activation, then one event a month', async ({ browser, baseURL }, info) => {
    const events = fixtures().viewports[info.project.name].events
    const phone = info.project.name === 'phone'

    // A signed-out visitor finds Membership in the header (the menu on a phone).
    const member = await personPage(browser, baseURL!)
    await member.goto('/')
    if (phone) await member.getByRole('button', { name: 'Open menu' }).click()
    await member.getByRole('link', { name: 'Membership', exact: true }).filter({ visible: true }).first().click()
    await expect(member).toHaveURL(/\/membership$/)
    await expect(member.getByRole('heading', { level: 1, name: 'Find the membership that fits.' })).toBeVisible()
    await expect(member.getByRole('table')).toBeVisible({ visible: !phone })
    expect(await member.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)

    // Choosing Limited asks for an account first.
    await member.getByRole('link', { name: 'Choose Limited', exact: true }).click()
    await expect(member).toHaveURL(/\/account\/register\?next=%2Fjoin%3Ftier%3Dlimited$/)
    const email = uniqueEmail('e2e.plans')
    const name = uniqueName('planner')
    await member.getByLabel('Email').fill(email)
    await member.getByLabel('Display name').fill(name)
    await member.getByLabel('Password').fill(PASSWORD)
    await member.getByRole('button', { name: 'Create account' }).click()
    const link = new URL(await mailLink(email, '/account/verify#token='))
    await member.goto(link.pathname + link.hash)
    await expect(member.getByText('Your email is confirmed.')).toBeVisible()
    await member.goto('/account/login?next=%2Fjoin%3Ftier%3Dlimited')
    await member.getByLabel('Email').fill(email)
    await member.getByLabel('Password').fill(PASSWORD)
    await member.getByRole('button', { name: 'Log in' }).click()

    // Back on the tier chosen: sign the agreement, then get a code to pay at the door.
    const agreement = member.getByRole('region', { name: 'Agreement text' })
    await agreement.evaluate((element) => element.scrollTo(0, element.scrollHeight))
    await member.getByLabel('I have read the agreement and I agree to it.').check()
    await member.getByLabel(/Type your full name to sign/).fill('Riley Testperson')
    await member.getByRole('button', { name: 'Agree and continue' }).click()
    await member.getByRole('button', { name: 'Get my reference code' }).click()
    await expect(member.getByText("You're in")).toBeVisible()
    const code = (await member.getByAltText(/QR code for/).getAttribute('alt'))!.replace('QR code for ', '')

    // The door desk takes payment, checks ID and activates.
    const desk = await personPage(browser, baseURL!)
    await staffLogin(desk)
    await deskSearch(desk, code)
    const person = (await desk.getByRole('article').first().getByRole('heading', { level: 2 }).textContent())!.trim()
    await deskAction(desk, person, 'Record payment and activate', 'Record payment and activate', 'Record payment and activate')
    await expect(desk.getByText(`${code} is active.`)).toBeVisible()
    await expect(desk.getByRole('article', { name: person }).getByText('1 left')).toBeVisible()

    // One members-only evening this month is included...
    await member.goto(`/events/${events.members_early}`)
    const panel = member.getByRole('article', { name: 'RSVP' })
    await panel.getByRole('button', { name: 'RSVP', exact: true }).click()
    await expect(panel.getByText('You are going')).toBeVisible()

    // ...and the second one that month is not.
    await member.goto(`/events/${events.members_late}`)
    await expect(panel.getByText('Monthly limit reached')).toBeVisible()
    await expect(panel.getByText(/used this month.s events on your membership/)).toBeVisible()
    await expect(panel.getByRole('link', { name: 'See plans with more events' })).toHaveAttribute('href', '/membership')
    await expect(panel.getByRole('button', { name: 'RSVP', exact: true })).toHaveCount(0)

    // The plans page shows their plan. (The evenings may fall in next month, so the
    // count of events left is checked by the backend tests, not here.)
    await member.goto('/membership')
    const banner = member.getByRole('region', { name: 'Your membership' })
    await expect(banner).toContainText('Your plan: Limited')
    await expect(banner).toContainText(/events? left this month/)

    await member.context().close()
    await desk.context().close()
  })
})
