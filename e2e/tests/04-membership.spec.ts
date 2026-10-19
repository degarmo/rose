import { expect, fixtures, mailLink, personPage, staffLogin, test, uniqueEmail, uniqueName } from './support'

const PASSWORD = 'a-long-e2e-password-42'

test.describe('Membership', () => {
  test('join, get a code, activated at the door, then see the feed', async ({ browser, baseURL }) => {
    // A brand-new person registers and verifies their email.
    const member = await personPage(browser, baseURL!)
    const email = uniqueEmail('e2e.join')
    const name = uniqueName('joiner')
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

    // Choose, read and sign the agreement, pay at the door.
    // Desktop has a button per tier card; phones pick from a list, then "Continue with …".
    await member.getByRole('button', { name: /^(Choose|Continue with) Rose$/ }).filter({ visible: true }).click()
    const agreement = member.getByRole('region', { name: 'Agreement text' })
    await agreement.evaluate((element) => element.scrollTo(0, element.scrollHeight))
    await expect(member.getByText('You have reached the end.')).toBeAttached()
    await member.getByLabel('I have read the agreement and I agree to it.').check()
    await member.getByLabel(/Type your full name to sign/).fill('Jordan Testperson')
    await member.getByRole('button', { name: 'Agree and continue' }).click()
    await member.getByRole('button', { name: 'Get my reference code' }).click()
    await expect(member.getByText("You're in")).toBeVisible()
    const code = (await member.getByAltText(/QR code for/).getAttribute('alt'))!.replace('QR code for ', '')
    expect(code).toMatch(/^[2-9A-HJKMNP-Z]{3}-[2-9A-HJKMNP-Z]{3}$/)

    // Door staff log in with the second step and activate after checking ID.
    const desk = await personPage(browser, baseURL!)
    await staffLogin(desk)
    await desk.getByRole('link', { name: 'Door desk' }).first().click()
    await desk.getByLabel('Reference code or display name').fill(code)
    await desk.getByRole('button', { name: 'Search', exact: true }).click()
    await expect(desk.getByText(name)).toBeVisible()
    await expect(desk.getByText('Jordan Testperson')).toHaveCount(0)
    const activate = desk.locator('form', { has: desk.getByRole('heading', { name: 'Record payment and activate' }) })
    await activate.getByLabel('Photo ID checked, 18+').check()
    await activate.getByRole('button', { name: 'Record payment and activate' }).click()
    await expect(desk.getByText(`${code} is active.`)).toBeVisible()

    // The member now has the community.
    await member.goto('/account')
    await expect(member.getByText(/Paid through/)).toBeVisible()
    await member.getByRole('link', { name: 'Join the member feed' }).click()
    await member.getByRole('button', { name: 'Read the guidelines' }).click()
    await member
      .getByLabel('Community guidelines', { exact: true })
      .evaluate((element) => element.scrollTo(0, element.scrollHeight))
    await member.getByLabel('I agree to the community guidelines').check()
    await member.getByRole('button', { name: 'Continue' }).click()
    await member.getByRole('button', { name: 'Join the feed' }).click()
    await member.getByRole('button', { name: 'Skip for now' }).click()
    await expect(member).toHaveURL(/\/members\/feed$/)
    await expect(member.getByRole('navigation', { name: 'Members' })).toBeVisible()

    await member.context().close()
    await desk.context().close()
  })

  test('staff without the second step cannot reach the door desk', async ({ browser, baseURL }) => {
    const page = await personPage(browser, baseURL!)
    const data = fixtures()
    await page.goto(`${data.admin_path}memberships/membership/door-desk/`)
    await expect(page).toHaveURL(/\/login\//)
    await page.getByLabel('Email').fill(data.staff.email)
    await page.getByLabel('Password').fill(data.password)
    await page.getByRole('button', { name: 'Continue' }).click()
    await page.getByLabel(/Six-digit code/).fill('000000')
    await page.getByRole('button', { name: 'Log in' }).click()
    await expect(page.getByText('That code did not work.')).toBeVisible()
    await page.goto(`${data.admin_path}memberships/membership/door-desk/`)
    await expect(page).toHaveURL(/\/login\//)
    await page.context().close()
  })
})
