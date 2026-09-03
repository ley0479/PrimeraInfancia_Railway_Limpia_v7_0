(function () {
    'use strict';

    const DEFAULT_ENABLED = true;
    const STORAGE_KEY = 'pi_executive_theme_preview_v1';
    const CONTROL_ID = 'pi-executive-preview-control';
    const THEMES = Object.freeze({
        institutional: 'Tema Institucional',
        executive: 'Tema Ejecutivo',
        'corporate-glass': 'Corporate Glass',
        'quantum-dark': 'Quantum Dark',
        biotech: 'Bio-Tech Precision',
        creator: 'Creator Market'
    });
    const enabled = typeof window.__PI_EXECUTIVE_PREVIEW_ENABLED__ === 'boolean'
        ? window.__PI_EXECUTIVE_PREVIEW_ENABLED__
        : DEFAULT_ENABLED;

    function shellElement() { return document.getElementById('app-shell'); }

    function storedUser() {
        try {
            if (typeof usuarioActual !== 'undefined' && usuarioActual) return usuarioActual;
        } catch (_) {}
        for (const storage of [sessionStorage, localStorage]) {
            for (const key of ['primeraInfanciaAuthUser', 'authUser', 'usuario', 'user']) {
                try {
                    const value = JSON.parse(storage.getItem(key) || 'null');
                    if (value) return value;
                } catch (_) {}
            }
        }
        return null;
    }

    function isSuperadmin() {
        return String(storedUser()?.rol || '').trim().toUpperCase() === 'SUPERADMIN';
    }

    function readPreference() {
        try {
            const value = localStorage.getItem(STORAGE_KEY);
            if (!value) return 'institutional';
            if (Object.hasOwn(THEMES, value) && value !== 'institutional') return value;
            localStorage.removeItem(STORAGE_KEY);
        } catch (_) {}
        return 'institutional';
    }

    function removeControl() { document.getElementById(CONTROL_ID)?.remove(); }

    function applyTheme(theme, persist = true) {
        const shell = shellElement();
        const safeTheme = Object.hasOwn(THEMES, theme) ? theme : 'institutional';
        if (!enabled || !isSuperadmin() || safeTheme === 'institutional') {
            if (shell) delete shell.dataset.previewTheme;
            if (persist) {
                try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
            }
        } else if (shell) {
            shell.dataset.previewTheme = safeTheme;
            if (persist) {
                try { localStorage.setItem(STORAGE_KEY, safeTheme); } catch (_) {}
            }
        }
        renderControl();
    }

    function restoreTheme(removePreference = true) { applyTheme('institutional', removePreference); }
    function activateTheme(theme = 'executive') { applyTheme(theme, true); }

    function renderControl() {
        const shell = shellElement();
        if (!enabled || !shell || shell.classList.contains('hidden') || !isSuperadmin()) {
            removeControl();
            return;
        }
        let control = document.getElementById(CONTROL_ID);
        if (!control) {
            control = document.createElement('aside');
            control.id = CONTROL_ID;
            control.className = 'pi-executive-preview-control no-print';
            control.setAttribute('aria-label', 'Selector de temas visuales');
            control.innerHTML = '<label for="pi-theme-selector"><strong>Diseño de la plataforma</strong><small data-preview-status aria-live="polite"></small></label><select id="pi-theme-selector" data-preview-selector aria-label="Seleccionar tema"></select>';
            const selector = control.querySelector('[data-preview-selector]');
            selector.innerHTML = Object.entries(THEMES).map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
            selector.addEventListener('change', event => applyTheme(event.target.value, true));
            shell.appendChild(control);
        }
        const active = shell.dataset.previewTheme || 'institutional';
        control.dataset.state = active;
        control.querySelector('[data-preview-selector]').value = active;
        control.querySelector('[data-preview-status]').textContent = active === 'institutional'
            ? 'Diseño original activo.'
            : `${THEMES[active]} activo solo en este navegador.`;
    }

    function synchronize() {
        const shell = shellElement();
        if (!enabled || !shell || !isSuperadmin()) {
            restoreTheme(true);
            removeControl();
            return;
        }
        applyTheme(readPreference(), false);
    }

    document.addEventListener('click', event => {
        if (event.target.closest('[onclick*="cerrarSesion"]')) restoreTheme(true);
    }, true);
    window.addEventListener('storage', event => { if (event.key === STORAGE_KEY) synchronize(); });
    window.addEventListener('DOMContentLoaded', () => {
        const shell = shellElement();
        if (!shell) return;
        new MutationObserver(synchronize).observe(shell, { attributes: true, attributeFilter: ['class'] });
        synchronize();
    });

    window.ExecutiveThemePreview = Object.freeze({ activate: activateTheme, restore: restoreTheme, synchronize, themes: THEMES });
})();
