const { test, expect } = require('@playwright/test');

const URL = 'https://primerainfanciarailwaylimpiav236-production.up.railway.app/';

async function mockIanApi(page) {
  let profile = {
    assistant_name: 'IAN', avatar_gender: 'male',
    avatar_variant: 'afro_colombian_institutional', voice_gender: 'male',
    motion_level: 'full', primary_color: '#123A63', secondary_color: '#16C6D8'
  };
  await page.route('**/api/asistente-capacitacion/config', route => route.fulfill({ json: {
    elian: { enabled: true, voice_enabled: true, animation_enabled: true, walk_enabled: true,
      teleport_enabled: true, lip_sync_enabled: true, hologram_enabled: true,
      platform_tour_enabled: true, tours_enabled: true }
  }}));
  await page.route('**/api/asistente-capacitacion/elian/visual-config', async route => {
    if (route.request().method() === 'PUT') profile = { ...profile, ...route.request().postDataJSON() };
    await route.fulfill({ json: { configuration: profile, editable: true, asset_ready: true } });
  });
  await page.route('**/api/asistente-capacitacion/contexto**', route => route.fulfill({ json: {
    rol: 'SUPERADMIN', guia: { titulo: 'Centro de Control', resumen: 'Panel principal.', pasos: ['Revisar estado.'] }
  }}));
  await page.addInitScript(() => sessionStorage.setItem('primeraInfanciaAuthToken', 'token-prueba-ian'));
}

test('apariencia, gestos, labios y movimiento de IAN funcionan con el SVG por capas', async ({ page }) => {
  await mockIanApi(page);
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#liam-tab .ian-avatar-svg')).toBeVisible({ timeout: 15000 });
  await page.waitForFunction(() => Boolean(window.LIAM_ANIMATION && window.LIAM_MOVEMENT && window.LIAM_LIP_SYNC), null, { timeout: 15000 });
  await expect(page.locator('#liam-tab')).toHaveAttribute('data-profile-ready', 'true', { timeout: 15000 });
  await page.locator('#liam-tab').click();
  await page.locator('#elian-inline-config summary').click();
  await page.locator('#elian-inline-gender').selectOption('female');
  await page.locator('#elian-inline-variant').selectOption('afro_colombian_technological');
  await page.locator('[data-action="elian-save-visual"]').click();
  await expect(page.locator('#liam-avatar-wrap .ian-avatar-svg')).toHaveAttribute('data-gender', 'female');
  await expect(page.locator('#liam-avatar-wrap .ian-avatar-svg')).toHaveAttribute('data-variant', 'afro_colombian_technological');
  await expect(page.locator('#liam-avatar-wrap .ian-hair-female')).toBeVisible();

  await expect(page.locator('#liam-avatar-wrap')).toHaveAttribute('data-state', 'idle', { timeout: 4000 });
  const greeting = await page.evaluate(() => {
    const accepted = window.LIAM_STATE.set('greeting');
    const wrap = document.getElementById('liam-avatar-wrap');
    return { accepted, machine: window.LIAM_STATE.get(), states: window.LIAM_STATE.states, runtimeWarning: document.getElementById('liam-tab').dataset.runtimeWarning || '', animationApi: Boolean(window.LIAM_ANIMATION), movementApi: Boolean(window.LIAM_MOVEMENT), state: wrap.dataset.state, animation: getComputedStyle(wrap.querySelector('.ian-arm-right')).animationName };
  });
  console.log('IAN greeting diagnostic', greeting);
  expect(greeting.state).toBe('greeting');
  expect(greeting.animation).toContain('ian-wave');
  await page.evaluate(() => { window.LIAM_STATE.set('speaking'); window.LIAM_LIP_SYNC.start('Hola, te acompaño.'); });
  await expect.poll(() => page.locator('#liam-avatar-wrap').evaluate(el => Number(getComputedStyle(el).getPropertyValue('--liam-mouth')))).toBeGreaterThan(0);
  await page.evaluate(() => window.LIAM_LIP_SYNC.pause());
  await expect.poll(() => page.locator('#liam-avatar-wrap').evaluate(el => Number(getComputedStyle(el).getPropertyValue('--liam-mouth')))).toBe(0);

  await page.evaluate(async () => {
    const target = document.createElement('button');
    target.dataset.helpId = 'dashboard.cuentame.upload';
    target.textContent = 'Cargar Base Cuéntame';
    target.style.cssText = 'position:fixed;left:80px;top:180px;width:180px;height:52px;z-index:10';
    document.body.appendChild(target);
    await window.LIAM_MOVEMENT.moveToControl('dashboard.cuentame.upload', { mode: 'teleport', walk_enabled: false });
  });
  await expect(page.locator('#ian-tour-avatar')).toBeVisible();
  await expect(page.locator('#ian-tour-avatar')).toHaveAttribute('data-state', /pointing_/);
  await page.screenshot({ path: 'docs/ian/evidence/ian-female-technological-guiding.png', fullPage: false });
});

test('silueta y accesibilidad no se superponen en celular', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockIanApi(page);
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  const ian = page.locator('#liam-tab');
  const a11y = page.locator('#pi-a11y-toggle');
  await expect(ian.locator('.ian-avatar-svg')).toBeVisible({ timeout: 15000 });
  await expect(a11y).toBeVisible();
  const a = await ian.boundingBox();
  const b = await a11y.boundingBox();
  const separated = a.x + a.width <= b.x || b.x + b.width <= a.x;
  expect(separated).toBeTruthy();
  await ian.click();
  await expect(page.locator('#liam-panel')).toBeVisible();
  await expect(a11y).toBeHidden();
  const panel = await page.locator('#liam-panel').boundingBox();
  expect(panel.x).toBeGreaterThanOrEqual(0);
  expect(panel.x + panel.width).toBeLessThanOrEqual(390);
});
