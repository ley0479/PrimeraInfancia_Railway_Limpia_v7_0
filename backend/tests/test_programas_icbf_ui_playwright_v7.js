'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..', '..');
const FRONTEND = path.join(ROOT, 'frontend');
const EVIDENCE = path.join(ROOT, 'docs', 'evidencias', 'multiprograma');
const VIEWPORTS = [
    [320, 640], [360, 800], [390, 844], [412, 915],
    [768, 1024], [820, 1180], [1024, 768],
    [1280, 720], [1366, 768], [1920, 1080],
];

function serveFile(request, response) {
    const raw = request.url === '/' ? '/index.html' : request.url.split('?')[0];
    const candidate = path.resolve(FRONTEND, `.${decodeURIComponent(raw)}`);
    if (!candidate.startsWith(FRONTEND) || !fs.existsSync(candidate) || fs.statSync(candidate).isDirectory()) {
        response.statusCode = 404;
        response.end();
        return;
    }
    fs.createReadStream(candidate).pipe(response);
}

(async () => {
    fs.mkdirSync(EVIDENCE, { recursive: true });
    const server = http.createServer(serveFile);
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const browser = await chromium.launch({ headless: true });
    try {
        const page = await browser.newPage();
        await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'domcontentloaded' });
        await page.evaluate(() => {
            const card = document.querySelector('#sn-icbf-program-context');
            document.body.replaceChildren(card);
            document.documentElement.removeAttribute('data-workspace-theme');
            document.body.style.cssText = 'margin:0;padding:16px;background:#020617;box-sizing:border-box;';
            card.classList.remove('hidden');
            card.style.width = '100%';
            card.style.boxSizing = 'border-box';
        });
        for (const [width, height] of VIEWPORTS) {
            await page.setViewportSize({ width, height });
            const result = await page.locator('#sn-icbf-program-context').evaluate(card => {
                const visible = element => {
                    const style = getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
                };
                const bounds = card.getBoundingClientRect();
                const controls = [...card.querySelectorAll('button,input,select')];
                const labels = [...card.querySelectorAll('label')];
                return {
                    cardRight: bounds.right,
                    viewport: document.documentElement.clientWidth,
                    globalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                    controlsInside: controls.every(item => {
                        const rect = item.getBoundingClientRect();
                        return visible(item) && rect.left >= bounds.left - 1 && rect.right <= bounds.right + 1;
                    }),
                    labelsVisible: labels.length === 5 && labels.every(visible),
                    title: card.querySelector('#sn-icbf-program-title')?.textContent.trim(),
                    columns: getComputedStyle(labels[0].parentElement).gridTemplateColumns.split(' ').length,
                };
            });
            assert.equal(result.title, 'Servicio Integrado ICBF');
            assert.equal(result.labelsVisible, true, `Etiquetas no visibles en ${width}x${height}`);
            assert.equal(result.controlsInside, true, `Control fuera de la tarjeta en ${width}x${height}`);
            assert.ok(result.cardRight <= result.viewport + 1, `Tarjeta fuera del viewport en ${width}x${height}`);
            assert.ok(result.globalOverflow <= 1, `Desbordamiento horizontal en ${width}x${height}`);
            assert.equal(result.columns, width < 768 ? 1 : width < 1280 ? 2 : 5, `Columnas incorrectas en ${width}x${height}`);
            if ([320, 768, 1280, 1920].includes(width)) {
                await page.screenshot({ path: path.join(EVIDENCE, `contexto-${width}x${height}.png`), fullPage: true });
            }
        }
        console.log(`PASS test_programas_icbf_ui_playwright_v7 (${VIEWPORTS.length} viewports)`);
    } finally {
        await browser.close();
        await new Promise(resolve => server.close(resolve));
    }
})().catch(error => { console.error(error); process.exit(1); });
