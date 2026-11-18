import { expect, test } from '@playwright/test'

const site = process.env.BRANDGUARD_TEST_WORDPRESS_URL
const reviewerKey = process.env.BRANDGUARD_TEST_REVIEWER_KEY
test('WordPress block editor submits, displays the decision and invalidates edited markup', async ({ page, request }) => {
  test.skip(!site || !reviewerKey, 'Requires a connected disposable WordPress site and a BrandGuard reviewer.')
  test.setTimeout(120000)
  const login = await request.post('/api/login', { data: { key: reviewerKey } })
  expect(login.ok()).toBeTruthy()
  await page.goto(site + '/wp-login.php')
  await page.locator('#user_login').fill(process.env.WP_TEST_USER!)
  await page.locator('#user_pass').fill(process.env.WP_TEST_PASSWORD!)
  await page.locator('#wp-submit').click()
  await page.goto(site + '/wp-admin/post-new.php', {waitUntil: 'domcontentloaded'})
  const panel = page.getByRole('button', {name: 'BrandGuard review', exact: true})
  const dismiss = page.getByRole('dialog').getByRole('button', {name: /close/i}).first()
  await expect(panel.or(dismiss).first()).toBeVisible({timeout: 45000})
  if (await dismiss.isVisible()) await dismiss.click()
  await page.evaluate(() => {
    const wp = (window as any).wp
    wp.data.dispatch('core/editor').editPost({title:'WordPress launch', excerpt:'Launch announcement'})
    wp.data.dispatch('core/block-editor').resetBlocks([wp.blocks.createBlock('core/paragraph', {content:'Explore magic AI.'})])
  })
  await page.evaluate(() => {
    const wp = (window as any).wp
    wp.data.dispatch('core/edit-post').openGeneralSidebar('edit-post/document')
  })
  if (await panel.getAttribute('aria-expanded') !== 'true') await panel.click()
  await expect(page.getByText('Ready to send for review')).toBeVisible({timeout: 20000})
  const reply = page.waitForResponse(res => res.url().includes('brandguard') && res.request().method() === 'POST')
  await page.getByRole('button', {name:'Send draft for review'}).click()
  const queued = await (await reply).json()
  expect(queued.status).toBe('PENDING_APPROVAL')
  await expect(page.getByText('Awaiting reviewer decision')).toBeVisible()
  const submission = await (await request.get('/api/submissions/' + queued.submission_id)).json()
  expect(submission.wordpress.content).toContain('<!-- wp:paragraph -->')
  const decision = await request.post('/api/submissions/' + queued.submission_id + '/decision', {
    data: {generation:submission.generation, action:'APPROVED', comment:'Editorial review complete.'}
  })
  expect(decision.ok()).toBeTruthy()
  await page.getByRole('button', {name:'Refresh decision'}).click()
  await expect(page.getByText('Approved for this exact draft')).toBeVisible()
  await expect(page.getByText('Editorial review complete.')).toBeVisible()
  await page.evaluate(() => {
    const wp = (window as any).wp
    const [block] = wp.data.select('core/block-editor').getBlocks()
    wp.data.dispatch('core/block-editor').updateBlockAttributes(block.clientId, {content:'Explore <strong>magic AI</strong>.'})
  })
  await expect(page.getByText('Draft changed — needs review')).toBeVisible()
  await expect(page.getByText('Approved for this exact draft')).toHaveCount(0)
  await expect(page.getByRole('button', {name:'Send draft for review'})).toBeEnabled()
})
