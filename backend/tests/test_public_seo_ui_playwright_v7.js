'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..', '..');
const FRONTEND = path.join(ROOT, 'frontend');
const VIEWPORTS = [[320, 640], [390, 844], [768, 1024], [1366, 768]];

function serve(request, response) {
    const raw = request.url === '/' ? '/index.html' : request.url.split('?')[0];
    const file = path.resolve(FRONTEND, `.${decodeURIComponent(raw)}`);
    if (!file.startsWith(FRONTEND) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
        response.statusCode = 404;
        return response.end();
    }
    fs.createReadStream(file).pipe(response);
}

(async () => {
    const server = http.createServer(serve);
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const browser = await chromium.launch({ headless: true });
    try {
        const page = await browser.newPage();
        await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'domcontentloaded' });
        for (const [width, height] of VIEWPORTS) {
            await page.setViewportSize({ width, height });
            const result = await page.evaluate(() => {
                const login = document.querySelector('#login-screen');
                const card = login.firstElementChild;
                const rect = card.getBoundingClientRect();
                return {
                    title: document.title,
                    description: document.querySelector('meta[name="description"]')?.content,
                    canonical: document.querySelector('link[rel="canonical"]')?.href,
                    text: login.textContent,
                    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                    inside: rect.left >= -1 && rect.right <= document.documentElement.clientWidth + 1,
                    canScroll: login.scrollHeight <= login.clientHeight || getComputedStyle(login).overflowY !== 'hidden',
                };
            });
            assert.match(result.title, /Primera Infancia/);
            assert.match(result.description, /gestión integral/);
            assert.equal(result.canonical, 'https://primerainfancia.pro/');
            assert.match(result.text, /Plataforma de gestión integral/);
            assert.ok(result.overflow <= 1, `Desbordamiento horizontal en ${width}x${height}`);
            assert.equal(result.inside, true, `Tarjeta fuera del viewport en ${width}x${height}`);
            assert.equal(result.canScroll, true, `Acceso inferior inaccesible en ${width}x${height}`);
        }
        console.log(`PASS test_public_seo_ui_playwright_v7 (${VIEWPORTS.length} viewports)`);
    } finally {
        await browser.close();
        await new Promise(resolve => server.close(resolve));
    }
})().catch(error => { console.error(error); process.exit(1); });
