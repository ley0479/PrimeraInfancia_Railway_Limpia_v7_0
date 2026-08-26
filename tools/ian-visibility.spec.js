const { test, expect } = require('@playwright/test');

const URL = 'https://primerainfanciarailwaylimpiav236-production.up.railway.app/';

test('IAN se monta, se ve y abre el panel aun si la configuración avanzada falla', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    sessionStorage.setItem('primeraInfanciaAuthToken', 'token-de-prueba-visual');
  });
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  const shell = page.locator('#liam-shell');
  await expect(shell).toBeVisible({ timeout: 10000 });
  const tab = page.locator('#liam-tab');
  await expect(tab).toBeVisible();
  const box = await tab.boundingBox();
  expect(box && box.width >= 44 && box.height >= 44).toBeTruthy();
  const accessibility = page.locator('#pi-a11y-toggle');
  await expect(accessibility).toBeVisible({ timeout: 10000 });
  const accessibilityBox = await accessibility.boundingBox();
  expect(box.x + box.width).toBeLessThanOrEqual(accessibilityBox.x + 2);
  expect(box.x + box.width).toBeGreaterThan(accessibilityBox.x - 32);
  await page.screenshot({ path: 'docs/ian/evidence/ian-launcher-production.png', fullPage: false });
  await tab.click();
  await expect(page.locator('#liam-panel')).toBeVisible();
  await expect(page.locator('#liam-avatar-wrap .ian-avatar-svg')).toBeVisible();
  await page.screenshot({ path: 'docs/ian/evidence/ian-panel-production.png', fullPage: false });
  await page.locator('#liam-close').click();
  await expect(page.locator('#liam-panel')).toBeHidden();
  await expect(tab).toBeVisible();
  expect(errors.filter(message => /IAN|LIAM|ian|liam/.test(message))).toEqual([]);
});
