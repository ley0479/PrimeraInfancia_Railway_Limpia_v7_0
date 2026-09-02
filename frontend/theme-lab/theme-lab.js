(function () {
    'use strict';

    const STORAGE_KEY = 'pi_theme_lab_preview';
    const THEMES = new Set(['institutional', 'executive']);
    const lab = document.querySelector('.pi-theme-lab');
    const selector = document.getElementById('pi-lab-theme-select');
    const resetButton = document.getElementById('pi-lab-reset-theme');
    const feedback = document.getElementById('pi-lab-feedback');
    const menuButton = document.querySelector('.pi-lab-menu-toggle');
    const modal = document.getElementById('pi-lab-modal');
    let modalTrigger = null;

    function readTheme() {
        try {
            const stored = window.localStorage.getItem(STORAGE_KEY);
            return THEMES.has(stored) ? stored : 'institutional';
        } catch (_error) {
            return 'institutional';
        }
    }

    function announce(message) {
        if (!feedback) return;
        const text = feedback.querySelector('span:last-child');
        if (text) text.textContent = message;
    }

    function applyTheme(theme, persist) {
        const safeTheme = THEMES.has(theme) ? theme : 'institutional';
        if (!lab || !selector) return;
        lab.dataset.theme = safeTheme;
        selector.value = safeTheme;
        if (persist) {
            try { window.localStorage.setItem(STORAGE_KEY, safeTheme); } catch (_error) { /* Vista previa disponible sin persistencia. */ }
        }
        announce(safeTheme === 'executive' ? 'Tema Ejecutivo aplicado solamente al laboratorio.' : 'Tema Institucional aplicado solamente al laboratorio.');
    }

    function restoreInstitutional() {
        try { window.localStorage.removeItem(STORAGE_KEY); } catch (_error) { /* La restauración visual continúa. */ }
        applyTheme('institutional', false);
        announce('Tema Institucional restaurado. La preferencia temporal del laboratorio fue eliminada.');
    }

    function closeMenu() {
        if (!lab || !menuButton) return;
        lab.classList.remove('is-menu-open');
        menuButton.setAttribute('aria-expanded', 'false');
        menuButton.setAttribute('aria-label', 'Abrir menú del laboratorio');
    }

    function toggleMenu() {
        if (!lab || !menuButton) return;
        const isOpen = lab.classList.toggle('is-menu-open');
        menuButton.setAttribute('aria-expanded', String(isOpen));
        menuButton.setAttribute('aria-label', isOpen ? 'Cerrar menú del laboratorio' : 'Abrir menú del laboratorio');
    }

    function openModal(event) {
        if (!modal) return;
        modalTrigger = event.currentTarget;
        modal.hidden = false;
        modal.querySelector('[data-close-modal]')?.focus();
    }

    function closeModal() {
        if (!modal) return;
        modal.hidden = true;
        modalTrigger?.focus();
    }

    function trapModalFocus(event) {
        if (!modal || modal.hidden || event.key !== 'Tab') return;
        const focusable = Array.from(modal.querySelectorAll('button, input, select, [tabindex]:not([tabindex="-1"])')).filter((element) => !element.disabled);
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }

    selector?.addEventListener('change', (event) => applyTheme(event.target.value, true));
    resetButton?.addEventListener('click', restoreInstitutional);
    menuButton?.addEventListener('click', toggleMenu);
    document.querySelectorAll('.pi-lab-nav a').forEach((link) => link.addEventListener('click', () => {
        document.querySelectorAll('.pi-lab-nav a').forEach((item) => {
            item.classList.toggle('is-active', item === link);
            if (item === link) item.setAttribute('aria-current', 'page');
            else item.removeAttribute('aria-current');
        });
        closeMenu();
    }));
    document.querySelectorAll('[data-open-modal]').forEach((button) => button.addEventListener('click', openModal));
    document.querySelectorAll('[data-close-modal]').forEach((button) => button.addEventListener('click', closeModal));
    document.querySelectorAll('[data-demo-action]').forEach((button) => button.addEventListener('click', () => announce('Acción demostrativa: no se enviaron ni modificaron datos.')));
    modal?.addEventListener('click', (event) => { if (event.target === modal) closeModal(); });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') { closeModal(); closeMenu(); }
        trapModalFocus(event);
    });

    applyTheme(readTheme(), false);
}());
