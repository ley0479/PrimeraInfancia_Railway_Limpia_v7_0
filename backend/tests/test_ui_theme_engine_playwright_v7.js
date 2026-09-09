'use strict';

const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..', '..');
const KEYS = ['ocean-deep', 'neutral-professional', 'natura-green', 'aurora-violet', 'warm-sand', 'executive-premium'];
const COLORS = {
    'ocean-deep': ['#061326', '#0c2340', '#f3f8ff'], 'neutral-professional': ['#f4f7fb', '#ffffff', '#17243b'],
    'natura-green': ['#f4f7f0', '#fffef9', '#183428'], 'aurora-violet': ['#120a2d', '#24104c', '#faf6ff'],
    'warm-sand': ['#f6efe5', '#fffaf2', '#3c2d20'], 'executive-premium': ['#08090b', '#111318', '#f7f3e9']
};

function context(code) {
    const [background, surface, text] = COLORS[code];
    const themes = KEYS.map(key => ({ codigo: key, nombre: key, activo: true, es_sistema: true, configuracion: { colors: {} } }));
    return {
        tema: { codigo: code, nombre: code, configuracion: { colorMode: ['neutral-professional', 'natura-green', 'warm-sand'].includes(code) ? 'light' : 'dark' } },
        preferencia: { tema_codigo: code, modo: 'auto', contraste: 'normal', layout: 'normal', densidad: 'comfortable', radio: 12 },
        variables: { '--pi-bg': background, '--pi-surface': surface, '--pi-text': text, '--pi-muted': '#64748b', '--pi-border': '#334155', '--pi-primary': '#2563eb', '--pi-accent': '#0ea5e9' },
        permisos: { puede_cambiar_tema: true, puede_administrar: true }, temas: themes
    };
}

const fixture = `<!doctype html><html><head><link rel="stylesheet" href="/engine.css"></head><body><div id="app-shell"><aside id="sidebar-institucional"><button class="pi-menu-item active">Panel</button></aside><main><section class="bg-slate-900 text-slate-100">Contenido</section></main></div><script>window.backendUrl='';</script><script src="/manager.js"></script></body></html>`;

(async () => {
    let selected = 'ocean-deep';
    const server = http.createServer((request, response) => {
        if (request.url === '/') return response.end(fixture);
        if (request.url === '/manager.js') return fs.createReadStream(path.join(ROOT, 'frontend/js/modules/theme-manager.js')).pipe(response);
        if (request.url === '/engine.css') return fs.createReadStream(path.join(ROOT, 'frontend/css/design-system/theme-engine.css')).pipe(response);
        if (request.url === '/api/theme-manager/actual') { response.setHeader('Content-Type', 'application/json'); return response.end(JSON.stringify(context(selected))); }
        if (request.url === '/api/theme-manager/preferencia' && request.method === 'POST') {
            let body = ''; request.on('data', chunk => { body += chunk; }); request.on('end', () => {
                selected = JSON.parse(body).tema_codigo; response.setHeader('Content-Type', 'application/json'); response.end(JSON.stringify(context(selected)));
            }); return;
        }
        response.statusCode = 404; response.end();
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const browser = await chromium.launch({ headless: true });
    try {
        const page = await browser.newPage();
        await page.goto(`http://127.0.0.1:${server.address().port}/`);
        await page.evaluate(() => ThemeManager.initSessionTheme());
        for (const key of KEYS) {
            await page.evaluate(theme => {
                ThemeManager.abrirSelector(); ThemeManager.seleccionarTema(theme);
                return ThemeManager.guardarPreferenciaUsuario();
            }, key);
            assert.equal(await page.locator('html').getAttribute('data-theme'), key);
        }
        assert.equal(await page.locator('html').getAttribute('data-bs-theme'), 'light');
        assert.equal(await page.locator('#app-shell main').evaluate(el => getComputedStyle(el).backgroundColor), 'rgb(8, 9, 11)');
        await page.emulateMedia({ media: 'print' });
        assert.equal(await page.locator('html').evaluate(el => getComputedStyle(el).colorScheme), 'normal');
        console.log('6 temas persistentes Playwright OK');
    } finally {
        await browser.close(); await new Promise(resolve => server.close(resolve));
    }
})().catch(error => { console.error(error); process.exit(1); });
