'use strict';

const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..', '..');
const JS_PATH = '/js/modules/theme-executive-preview.js';
const CSS_PATH = '/css/themes/executive-preview.css';
const KEY = 'pi_executive_theme_preview_v1';

const fixture = `<!doctype html><html><head><link rel="stylesheet" href="${CSS_PATH}"></head>
<body><div id="app-shell" class="flex"><aside id="sidebar-institucional"><button class="pi-menu-item active">Panel</button></aside>
<main><section class="bg-slate-900 text-slate-100 border-slate-800">Contenido productivo</section>
<button id="logout" onclick="cerrarSesion()">Salir</button></main></div><script src="${JS_PATH}"></script></body></html>`;

function serverForFixture() {
    return http.createServer((request, response) => {
        if (request.url === '/') {
            response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            return response.end(fixture);
        }
        const relative = request.url === JS_PATH
            ? 'frontend/js/modules/theme-executive-preview.js'
            : request.url === CSS_PATH
                ? 'frontend/css/themes/executive-preview.css'
                : '';
        if (!relative) {
            response.writeHead(404);
            return response.end();
        }
        response.writeHead(200, { 'Content-Type': relative.endsWith('.js') ? 'text/javascript' : 'text/css' });
        return fs.createReadStream(path.join(ROOT, relative)).pipe(response);
    });
}

async function openPage(browser, baseUrl, { enabled = true, role = 'SUPERADMIN', preference = null } = {}) {
    const page = await browser.newPage();
    await page.addInitScript(({ enabled, role, preference, key }) => {
        window.__PI_EXECUTIVE_PREVIEW_ENABLED__ = enabled;
        sessionStorage.setItem('primeraInfanciaAuthUser', JSON.stringify({ id: 7, rol: role, fundacion_id: 1 }));
        if (preference !== null) localStorage.setItem(key, preference);
    }, { enabled, role, preference, key: KEY });
    await page.goto(baseUrl, { waitUntil: 'networkidle' });
    return page;
}

(async () => {
    const server = serverForFixture();
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const baseUrl = `http://127.0.0.1:${server.address().port}/`;
    const browser = await chromium.launch({ headless: true });
    try {
        let page = await openPage(browser, baseUrl, { enabled: false });
        assert.equal(await page.locator('#pi-executive-preview-control').count(), 0);
        assert.equal(await page.locator('#app-shell').getAttribute('data-preview-theme'), null);
        await page.close();

        page = await openPage(browser, baseUrl, { role: 'DOCENTE', preference: 'executive' });
        assert.equal(await page.locator('#pi-executive-preview-control').count(), 0);
        assert.equal(await page.evaluate(key => localStorage.getItem(key), KEY), null);
        await page.close();

        page = await openPage(browser, baseUrl, { preference: 'desconocido' });
        assert.equal(await page.evaluate(key => localStorage.getItem(key), KEY), null);
        assert.equal(await page.locator('#app-shell').getAttribute('data-preview-theme'), null);
        await page.getByRole('button', { name: 'Activar Tema Ejecutivo' }).click();
        assert.equal(await page.locator('#app-shell').getAttribute('data-preview-theme'), 'executive');
        assert.equal(await page.evaluate(key => localStorage.getItem(key), KEY), 'executive');
        assert.equal(await page.locator('main').evaluate(el => getComputedStyle(el).backgroundColor), 'rgb(244, 246, 249)');
        await page.getByRole('button', { name: 'Restaurar Tema Institucional' }).click();
        assert.equal(await page.locator('#app-shell').getAttribute('data-preview-theme'), null);
        assert.equal(await page.evaluate(key => localStorage.getItem(key), KEY), null);

        await page.getByRole('button', { name: 'Activar Tema Ejecutivo' }).click();
        await page.getByRole('button', { name: 'Salir' }).click();
        assert.equal(await page.evaluate(key => localStorage.getItem(key), KEY), null);
        assert.equal(await page.locator('#app-shell').getAttribute('data-preview-theme'), null);
        await page.close();

        page = await openPage(browser, baseUrl, { preference: 'executive' });
        assert.equal(await page.locator('#app-shell').getAttribute('data-preview-theme'), 'executive');
        await page.emulateMedia({ media: 'print' });
        assert.equal(await page.locator('#app-shell').evaluate(el => getComputedStyle(el).colorScheme), 'normal');
        await page.close();

        console.log('7 escenarios Playwright preview OK');
    } finally {
        await browser.close();
        await new Promise(resolve => server.close(resolve));
    }
})().catch(error => {
    console.error(error);
    process.exit(1);
});
