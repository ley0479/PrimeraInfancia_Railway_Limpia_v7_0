(function () {
    'use strict';

    const DEFAULT_ENABLED = false;
    const STORAGE_KEY = 'pi_executive_theme_preview_v1';
    const ALLOWED_VALUE = 'executive';
    const CONTROL_ID = 'pi-executive-preview-control';
    const enabled = DEFAULT_ENABLED || window.__PI_EXECUTIVE_PREVIEW_ENABLED__ === true;

    function shellElement() {
        return document.getElementById('app-shell');
    }

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
            if (value === ALLOWED_VALUE) return value;
            localStorage.removeItem(STORAGE_KEY);
        } catch (_) {}
        return 'institutional';
    }

    function removeControl() {
        document.getElementById(CONTROL_ID)?.remove();
    }

    function restoreTheme(removePreference = true) {
        const shell = shellElement();
        if (shell) delete shell.dataset.previewTheme;
        if (removePreference) {
            try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
        }
        renderControl();
    }

    function activateTheme() {
        if (!enabled || !isSuperadmin()) return restoreTheme(true);
        const shell = shellElement();
        if (!shell) return;
        shell.dataset.previewTheme = ALLOWED_VALUE;
        try { localStorage.setItem(STORAGE_KEY, ALLOWED_VALUE); } catch (_) {}
        renderControl();
    }

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
            control.setAttribute('aria-label', 'Vista previa Tema Ejecutivo');
            control.innerHTML = '<div aria-live="polite"><strong>Vista previa Tema Ejecutivo</strong><small data-preview-status></small></div><button type="button" data-preview-toggle></button>';
            shell.appendChild(control);
            control.querySelector('[data-preview-toggle]').addEventListener('click', () => {
                if (shell.dataset.previewTheme === ALLOWED_VALUE) restoreTheme(true);
                else activateTheme();
            });
        }
        const active = shell.dataset.previewTheme === ALLOWED_VALUE;
        control.dataset.state = active ? 'executive' : 'institutional';
        control.querySelector('[data-preview-status]').textContent = active ? 'Activa solo en este navegador.' : 'Tema Institucional activo.';
        control.querySelector('[data-preview-toggle]').textContent = active ? 'Restaurar Tema Institucional' : 'Activar Tema Ejecutivo';
    }

    function synchronize() {
        const shell = shellElement();
        if (!enabled || !shell || !isSuperadmin()) {
            restoreTheme(true);
            removeControl();
            return;
        }
        if (readPreference() === ALLOWED_VALUE) shell.dataset.previewTheme = ALLOWED_VALUE;
        else delete shell.dataset.previewTheme;
        renderControl();
    }

    document.addEventListener('click', (event) => {
        if (event.target.closest('[onclick*="cerrarSesion"]')) restoreTheme(true);
    }, true);

    window.addEventListener('storage', (event) => {
        if (event.key === STORAGE_KEY) synchronize();
    });

    window.addEventListener('DOMContentLoaded', () => {
        const shell = shellElement();
        if (!shell) return;
        new MutationObserver(synchronize).observe(shell, { attributes: true, attributeFilter: ['class'] });
        synchronize();
    });

    window.ExecutiveThemePreview = Object.freeze({ activate: activateTheme, restore: restoreTheme, synchronize });
})();

