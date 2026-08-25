/* Motor maestro de impresión para vistas HTML imprimibles — v2.3.0-alpha.13. */
(function () {
    const STYLE_ID = 'print-manager-dynamic-style';
    const BODY_CLASS = 'pi-printing';
    const HEADER_ID = 'pi-print-institutional-header';

    function getConfig(tipoFormato) {
        const key = String(tipoFormato || '').trim().toLowerCase();
        return window.PRINT_MASTER_CONFIG?.[key] || null;
    }

    function marginRule(cfg) {
        if (!cfg?.margins) return '';
        const m = cfg.margins;
        return `margin: ${m.top}cm ${m.right}cm ${m.bottom}cm ${m.left}cm;`;
    }

    function scaleRule(cfg) {
        const scale = Number(cfg?.scale || 100) / 100;
        if (!scale || scale === 1) return '';
        const width = (100 / scale).toFixed(4).replace(/\.0+$/, '');
        return `
            transform: scale(${scale});
            transform-origin: top left;
            width: ${width}%;
        `;
    }

    function ensureStyle(cfg, tipoFormato) {
        let style = document.getElementById(STYLE_ID);
        if (!style) {
            style = document.createElement('style');
            style.id = STYLE_ID;
            document.head.appendChild(style);
        }

        style.innerHTML = `
            @page {
                size: ${cfg.cssPageSize};
                ${marginRule(cfg)}
            }

            @media print {
                html[data-print-format="${tipoFormato}"],
                html[data-print-format="${tipoFormato}"] body {
                    background: #fff !important;
                    color: #000 !important;
                    margin: 0 !important;
                    padding: 0 !important;
                }

                body.${BODY_CLASS} .print-area,
                body.${BODY_CLASS} .formato-${tipoFormato.replace('_', '-')},
                body.${BODY_CLASS} [data-print-format="${tipoFormato}"] {
                    ${scaleRule(cfg)}
                }

                body.${BODY_CLASS} .pi-print-institutional-header {
                    display: flex !important;
                    align-items: center;
                    gap: 12px;
                    min-height: 54px;
                    margin: 0 0 12px;
                    padding: 0 0 8px;
                    border-bottom: 1px solid #555;
                    color: #111;
                    font-family: Arial, sans-serif;
                }
                body.${BODY_CLASS} .pi-print-institutional-header img {
                    width: 52px;
                    height: 52px;
                    object-fit: contain;
                }
                body.${BODY_CLASS} .pi-print-institutional-header strong,
                body.${BODY_CLASS} .pi-print-institutional-header span { display: block; }
            }
        `;
    }

    function cleanup() {
        document.body.classList.remove(BODY_CLASS);
        document.documentElement.removeAttribute('data-print-format');
        document.querySelectorAll('.print-target-active').forEach((el) => el.classList.remove('print-target-active'));
        document.getElementById(HEADER_ID)?.remove();
    }

    function ensureInstitutionalHeader() {
        document.getElementById(HEADER_ID)?.remove();
        const identity = window.obtenerIdentidadInstitucionalActual?.() || {};
        const visibleLogo = document.getElementById('institucional-logo-sidebar');
        const logoSrc = !visibleLogo?.classList.contains('hidden') ? visibleLogo?.src : '';
        const header = document.createElement('header');
        header.id = HEADER_ID;
        header.className = 'pi-print-institutional-header';
        const escape = (value) => String(value || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
        const logo = logoSrc ? `<img src="${escape(logoSrc)}" alt="Logo institucional">` : '';
        const nombre = identity.nombre_corporacion || identity.nombre_plataforma || 'Primera Infancia';
        const sigla = identity.sigla || '';
        header.innerHTML = `${logo}<div><strong>${escape(nombre)}</strong>${sigla ? `<span>${escape(sigla)}</span>` : ''}</div>`;
        document.body.prepend(header);
    }

    window.imprimirFormato = function imprimirFormato(tipoFormato, options = {}) {
        const cfg = getConfig(tipoFormato);
        if (!cfg) {
            alert(`No existe configuración de impresión para: ${tipoFormato}`);
            return false;
        }

        ensureStyle(cfg, tipoFormato);
        document.documentElement.setAttribute('data-print-format', tipoFormato);
        document.body.classList.add(BODY_CLASS);
        ensureInstitutionalHeader();

        const targetSelector = options.targetSelector || options.selector || null;
        if (targetSelector) {
            const target = document.querySelector(targetSelector);
            if (target) target.classList.add('print-target-active');
        }

        setTimeout(() => window.print(), 150);
        return true;
    };

    window.addEventListener('afterprint', cleanup);
    window.PrintManager = {
        config: window.PRINT_MASTER_CONFIG,
        imprimirFormato: window.imprimirFormato,
        cleanup
    };
})();
