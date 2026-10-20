import { expect, fixtures, personPage, staffLogin, test } from './support'

test.describe('The age check', () => {
  test('an unchecked paid member sees the age check on Home and no feed, until the door desk checks their ID', async ({ browser, baseURL }, info) => {
    const subject = fixtures().viewports[info.project.name].age_check
    const member = await personPage(browser, baseURL!, subject.email)

    // Home's checklist: the age check is next, with what to bring and the door code; the
    // feed is a 404.
    await member.goto('/members/home')
    const steps = member.getByRole('list').filter({ hasText: 'Age check' })
    await expect(steps.locator('[aria-current="step"]')).toContainText('Age check')
    await expect(steps.getByText(/Bring a valid photo ID showing you are 18 or older/)).toBeVisible()
    await expect(steps.getByText(/We never copy or store your ID/)).toBeVisible()
    await expect(member.getByAltText(`QR code for ${subject.code}`)).toBeVisible()
    expect((await member.request.get('/api/members/feed/')).status()).toBe(404)
    await member.goto('/members/feed')
    await expect(member.getByRole('heading', { name: 'This room is not on the map.' })).toBeVisible()

    // Staff see who is waiting, find them by their code and record the check.
    const desk = await personPage(browser, baseURL!)
    await staffLogin(desk)
    await desk.goto('/members/staff/door')
    await desk.getByRole('button', { name: 'Needs ID check' }).click()
    await expect(desk.getByRole('heading', { name: 'Waiting for an ID check' })).toBeVisible()
    const search = desk.getByRole('search')
    await search.getByLabel('Reference code or display name').fill(subject.code)
    await search.getByRole('button', { name: 'Search' }).click()
    const row = desk.getByRole('article', { name: subject.handle })
    await expect(row.getByText('ID check needed')).toBeVisible()
    await row.getByRole('button', { name: 'Record ID check' }).click()
    const dialog = desk.getByRole('dialog', { name: 'Record ID check' })
    await dialog.getByLabel('Photo ID checked, 18+').check()
    await dialog.getByRole('button', { name: 'Record ID check' }).click()
    await expect(desk.getByText(`${subject.handle}: ID check recorded.`)).toBeVisible()

    // The member opens the feed without logging out.
    await member.goto('/members/feed')
    await expect(member.getByRole('navigation', { name: 'Members' }).first()).toBeVisible()
    expect((await member.request.get('/api/members/feed/')).status()).toBe(200)

    await member.context().close()
    await desk.context().close()
  })
})
