import { expect, fixtures, personPage, PHOTO, test, twoStepLogin } from './support'

test.describe('Page images', () => {
  test('replace the home banner in the admin, then see it on Home', async ({ browser, baseURL }) => {
    const data = fixtures()
    const admin = await personPage(browser, baseURL!)
    await twoStepLogin(admin, data.team.admin)

    await admin.goto(`${data.admin_path}pages/siteimage/?page=home`)
    const home = admin.locator('#page-home')
    await expect(home.getByRole('heading', { name: 'Home' })).toBeVisible()
    await home.getByRole('link', { name: 'Replace' }).click()

    const alt = `A test banner ${Date.now()}`
    await admin.locator('#id_image').setInputFiles(PHOTO)
    await admin.getByLabel('Alt text').fill(alt)
    // The picker previews the chosen file straight away; a click sets the focal point.
    const stage = admin.locator('[data-focal-stage]')
    await expect(stage).toBeVisible()
    await stage.locator('img').click({ position: { x: 10, y: 10 } })
    await expect(admin.locator('#id_focal_x')).not.toHaveValue('0.50')
    await admin.locator('button[name="_save"]').click()
    await expect(admin.getByText(/was changed successfully/)).toBeVisible()

    const visitor = await personPage(browser, baseURL!)
    await visitor.goto('/')
    const banner = visitor.getByRole('img', { name: alt })
    await expect(banner).toBeVisible()
    await expect.poll(() => banner.evaluate((image: HTMLImageElement) => image.complete && image.naturalWidth > 0)).toBe(true)

    // Put the banner back for the other tests.
    await admin.goto(`${data.admin_path}pages/siteimage/?page=home`)
    await admin.locator('#page-home').getByRole('button', { name: 'Restore previous' }).click()
    await expect(admin.getByText('the previous picture is back')).toBeVisible()
    await visitor.reload()
    await expect(visitor.getByRole('img', { name: alt })).toHaveCount(0)
  })
})
