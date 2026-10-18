import { confirmAge, expect, mailLink, mailSubjects, test, uniqueEmail, uniqueName } from './support'

const PASSWORD = 'a-long-e2e-password-42'

test.describe('Accounts @smoke', () => {
  test('register, verify by email, log in and log out', async ({ page, context, baseURL }) => {
    await confirmAge(context, baseURL!)
    const email = uniqueEmail('e2e.reg')
    const name = uniqueName('newcomer')

    await page.goto('/account/register')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Display name').fill(name)
    await page.getByLabel('Password').fill(PASSWORD)
    await page.getByRole('button', { name: 'Create account' }).click()
    await expect(page.getByText(/check your email|sent you a link/i).first()).toBeVisible()

    // The token is in the URL fragment, so it never reaches the server's logs.
    const link = await mailLink(email, '/account/verify#token=')
    expect(new URL(link).hash).toMatch(/^#token=/)
    expect(await mailSubjects(email)).toEqual(['Confirm your email'])
    await page.goto(new URL(link).pathname + new URL(link).hash)
    await expect(page.getByText('Your email is confirmed.')).toBeVisible()
    await expect(page).toHaveURL(/\/account\/verify$/) // the token was removed from the address bar

    await page.goto('/account/login?next=%2Faccount')
    await page.getByLabel('Email').fill(email.toUpperCase())
    await page.getByLabel('Password').fill(PASSWORD)
    await page.getByRole('button', { name: 'Log in' }).click()
    await expect(page.getByRole('heading', { level: 1, name })).toBeVisible()

    await page.getByRole('button', { name: 'Log out' }).click()
    await expect(page).toHaveURL(/\/$/)
    await page.goto('/account')
    await expect(page).toHaveURL(/\/account\/login/)
  })

  test('a wrong password says nothing about whether the account exists', async ({ page, context, baseURL }) => {
    await confirmAge(context, baseURL!)
    await page.goto('/account/login')
    await page.getByLabel('Email').fill(uniqueEmail('nobody'))
    await page.getByLabel('Password').fill('not-the-password-123')
    await page.getByRole('button', { name: 'Log in' }).click()
    const message = await page.getByRole('alert').first().textContent()
    await page.getByLabel('Email').fill('e2e.desk@example.org')
    await page.getByLabel('Password').fill('not-the-password-123')
    await page.getByRole('button', { name: 'Log in' }).click()
    await expect(page.getByRole('alert').first()).toHaveText(message ?? '')
  })
})
