import { expect, fixtures, personPage, staffLogin, teamLogin, test } from './support'

test.describe('Moderation', () => {
  test('a report, a suspension, the notice, an appeal and its reversal', async ({ browser, baseURL }, info) => {
    const data = fixtures()
    const subjects = data.viewports[info.project.name].moderation

    // A member reports a post.
    const reporter = await personPage(browser, baseURL!, subjects.reporter)
    await reporter.goto(`/members/p/${subjects.post}`)
    await reporter.getByRole('button', { name: 'Post options' }).filter({ visible: true }).first().click()
    await reporter.getByRole('button', { name: 'Report to hosts' }).click()
    const reportDialog = reporter.getByRole('dialog', { name: 'Report this post' })
    await reportDialog.getByLabel('Harassment').check()
    await reportDialog.getByRole('button', { name: 'Send report' }).click()
    await expect(reporter.getByText('Thanks, our team will review this.')).toBeVisible()

    // A moderator opens it, looks at the content and suspends the author.
    const moderator = await personPage(browser, baseURL!)
    await teamLogin(moderator, 'moderator')
    await moderator.getByRole('link', { name: new RegExp(`Harassment · ${subjects.author_handle}`) }).first().click()
    await expect(moderator.getByText('A post the tests report.')).toHaveCount(1)
    await moderator.getByRole('button', { name: 'View reported content' }).click()
    await expect(moderator.getByText('A post the tests report.').first()).toBeVisible()
    await expect(moderator.getByText(/Hidden. The reported member is never told/)).toBeVisible()
    await moderator.getByRole('button', { name: 'Take action' }).click()
    const actionDialog = moderator.getByRole('dialog', { name: `Action on ${subjects.author_handle}` })
    await actionDialog.getByRole('radio', { name: /Feed suspension/ }).check()
    await actionDialog.getByLabel(/^Rule/).fill('Community guidelines')
    await actionDialog.getByLabel(/^Reason/).fill('Unkind post after a reminder.')
    await actionDialog.getByRole('button', { name: 'Record action' }).click()
    await expect(moderator.getByText('Feed suspension recorded')).toBeVisible()

    // The author cannot open the app, sees the notice on their account and appeals.
    const author = await personPage(browser, baseURL!, subjects.author)
    await author.goto('/members')
    await expect(author.getByRole('heading', { name: 'The member app is paused on your account' })).toBeVisible()
    await author.getByRole('link', { name: 'See my account' }).click()
    await expect(author.getByRole('heading', { name: 'Feed suspension' })).toBeVisible()
    await expect(author.getByText('Unkind post after a reminder.')).toBeVisible()
    await expect(author.getByText(subjects.reporter)).toHaveCount(0)
    await expect(author.getByText(`e2e_${info.project.name}_reporter`)).toHaveCount(0)
    await author.getByRole('button', { name: 'Appeal this decision' }).click()
    await author.getByLabel(/Your appeal/).fill('It was a joke between friends; I have taken it down.')
    await author.getByRole('button', { name: 'Send appeal' }).click()
    await expect(author.getByText(/waiting for review/)).toBeVisible()

    // An admin, not the moderator who acted, reverses it.
    const admin = await personPage(browser, baseURL!)
    await teamLogin(admin, 'admin')
    await admin.goto('/members/staff/reports?tab=appeals')
    await admin.getByRole('link', { name: new RegExp(`Feed suspension · ${subjects.author_handle}`) }).first().click()
    await admin.getByLabel('Reverse it').check()
    await admin.getByLabel(/^Reason/).fill('Taken down and apologised.')
    await admin.getByRole('button', { name: 'Record decision' }).click()
    await expect(admin.getByText(/Reversed by e2e_admin/)).toBeVisible()

    // The author is back in.
    await author.goto('/account/notices')
    await expect(author.getByText(/Reversed on/)).toBeVisible()
    await author.goto('/members/feed')
    await expect(author.getByRole('navigation', { name: 'Members' }).first()).toBeAttached()

    for (const page of [reporter, moderator, author, admin]) await page.context().close()
  })

  test('a ban shows Do not admit at the door desk', async ({ browser, baseURL }, info) => {
    const subjects = fixtures().viewports[info.project.name].moderation
    const moderator = await personPage(browser, baseURL!)
    await teamLogin(moderator, 'moderator')
    await moderator.goto(`/members/staff/members/${subjects.banned_handle}`)
    await moderator.getByRole('button', { name: 'Take action' }).click()
    const dialog = moderator.getByRole('dialog', { name: `Action on ${subjects.banned_handle}` })
    await dialog.getByRole('radio', { name: /^Ban/ }).check()
    await dialog.getByLabel(/^Rule/).fill('House rules')
    await dialog.getByLabel(/^Reason/).fill('Serious breach at the door.')
    await dialog.getByRole('button', { name: 'Record action' }).click()
    await expect(moderator.getByText('Ban recorded')).toBeVisible()
    await expect(moderator.getByText('Banned: Do not admit')).toBeVisible()

    const desk = await personPage(browser, baseURL!)
    await staffLogin(desk)
    await desk.getByRole('link', { name: 'Door desk' }).first().click()
    await desk.getByLabel('Reference code or display name').fill(subjects.banned_code)
    await desk.getByRole('button', { name: 'Search', exact: true }).click()
    await expect(desk.getByRole('alert').filter({ hasText: 'Do not admit' })).toBeVisible()

    await moderator.context().close()
    await desk.context().close()
  })
})
