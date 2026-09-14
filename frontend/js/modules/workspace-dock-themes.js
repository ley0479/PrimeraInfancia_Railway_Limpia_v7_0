// Dock compacto y selector visual del espacio de trabajo.
(function () {
    'use strict';

    const STORAGE_KEY = 'primeraInfanciaWorkspaceThemeV1';
    const THEMES = ['slate-light', 'light-emerald'];
    let openGroup = null;

    function savedTheme() {
        try {
            const value = localStorage.getItem(STORAGE_KEY);
            return THEMES.includes(value) ? value : THEMES[0];
        } catch (_) {
            return THEMES[0];
        }
    }

    function applyTheme(theme, persist) {
        const selected = THEMES.includes(theme) ? theme : THEMES[0];
        document.documentElement.dataset.workspaceTheme = selected;
        document.documentElement.dataset.workspaceNav = 'dock';
        const button = document.getElementById('workspace-theme-toggle');
        if (button) {
            const emerald = selected === 'light-emerald';
            button.setAttribute('aria-pressed', emerald ? 'true' : 'false');
            button.setAttribute('aria-label', emerald ? 'Cambiar a tema Slate y claro' : 'Cambiar a tema claro esmeralda');
            button.title = emerald ? 'Vista clara esmeralda' : 'Vista azul pizarra';
            const label = button.querySelector('[data-theme-label]');
            if (label) label.textContent = emerald ? 'Claro' : 'Azul';
            const icon = button.querySelector('[data-theme-icon]');
            if (icon) icon.setAttribute('data-lucide', emerald ? 'leaf' : 'moon-star');
            if (window.lucide) window.lucide.createIcons({ nodes: [button] });
        }
        if (persist) {
            try { localStorage.setItem(STORAGE_KEY, selected); } catch (_) {}
        }
        document.dispatchEvent(new CustomEvent('workspace:theme-changed', { detail: { theme: selected } }));
    }

    function closeFlyout(group) {
        const target = group || openGroup;
        if (!target) return;
        target.classList.remove('dock-flyout-open');
        target.querySelector('.pi-menu-group-toggle')?.setAttribute('aria-expanded', 'false');
        if (target === openGroup) openGroup = null;
    }

    function openFlyout(group) {
        if (!group || window.matchMedia('(max-width: 1024px)').matches) return;
        if (openGroup && openGroup !== group) closeFlyout(openGroup);
        const toggle = group.querySelector('.pi-menu-group-toggle');
        const flyout = group.querySelector('.pi-menu-group-items');
        if (!toggle || !flyout) return;
        const rect = toggle.getBoundingClientRect();
        const available = window.innerHeight - 16;
        flyout.style.top = `${Math.max(8, Math.min(rect.top, available - Math.min(flyout.scrollHeight || 360, 520)))}px`;
        group.classList.add('dock-flyout-open');
        toggle.setAttribute('aria-expanded', 'true');
        openGroup = group;
    }

    function configureFlyoutItems(group, flyout) {
        flyout.querySelectorAll('[data-menu-item]').forEach((item) => {
            if (item.dataset.dockDoubleClickReady === '1') return;
            item.dataset.dockDoubleClickReady = '1';
            const originalAction = item.onclick;
            item.onclick = null;
            item.title = `${item.textContent.trim()}: doble clic para abrir`;
            item.setAttribute('aria-description', 'Doble clic para abrir. También puede usar Enter.');

            const execute = (event) => {
                event.preventDefault();
                event.stopPropagation();
                if (typeof originalAction === 'function') originalAction.call(item, event);
                closeFlyout(group);
            };

            item.addEventListener('click', (event) => {
                if (window.matchMedia('(max-width: 1024px)').matches) {
                    execute(event);
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                flyout.querySelectorAll('[data-dock-selected="true"]').forEach((node) => {
                    if (node !== item) node.removeAttribute('data-dock-selected');
                });
                item.dataset.dockSelected = 'true';
            });
            item.addEventListener('dblclick', execute);
            item.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') execute(event);
            });
        });
    }

    function configureDock(nav) {
        nav.querySelectorAll('.pi-menu-group').forEach((group) => {
            const toggle = group.querySelector('.pi-menu-group-toggle');
            const label = toggle?.querySelector('span')?.textContent.trim() || 'Módulo';
            const flyout = group.querySelector('.pi-menu-group-items');
            if (!toggle || !flyout) return;
            group.dataset.groupLabel = label;
            flyout.dataset.flyoutLabel = label;
            toggle.setAttribute('aria-label', `Abrir ${label}`);
            toggle.title = label;
            group.addEventListener('pointerleave', (event) => {
                if (!group.contains(event.relatedTarget)) closeFlyout(group);
            });
            toggle.addEventListener('click', (event) => {
                if (window.matchMedia('(max-width: 1024px)').matches) return;
                event.preventDefault();
                event.stopImmediatePropagation();
                group.classList.contains('dock-flyout-open') ? closeFlyout(group) : openFlyout(group);
            }, true);
            toggle.addEventListener('focus', () => openFlyout(group));
            configureFlyoutItems(group, flyout);
        });
    }

    function addToggle() {
        const headerActions = document.querySelector('#app-shell > main > header > .flex.items-center.gap-4');
        if (!headerActions || document.getElementById('workspace-theme-toggle')) return;
        const button = document.createElement('button');
        button.id = 'workspace-theme-toggle';
        button.type = 'button';
        button.className = 'workspace-theme-toggle';
        button.innerHTML = '<i data-lucide="moon-star" data-theme-icon></i><span data-theme-label>Azul</span><span class="workspace-theme-switch" aria-hidden="true"><span></span></span>';
        button.addEventListener('click', () => {
            const current = document.documentElement.dataset.workspaceTheme;
            applyTheme(current === 'light-emerald' ? 'slate-light' : 'light-emerald', true);
        });
        headerActions.prepend(button);
    }

    function init() {
        const nav = document.getElementById('menu-lateral-institucional');
        if (!nav || nav.dataset.workspaceDockReady === '1') return;
        nav.dataset.workspaceDockReady = '1';
        addToggle();
        configureDock(nav);
        applyTheme(savedTheme(), false);
        document.addEventListener('click', (event) => {
            if (openGroup && !openGroup.contains(event.target)) closeFlyout(openGroup);
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && openGroup) {
                const toggle = openGroup.querySelector('.pi-menu-group-toggle');
                closeFlyout(openGroup);
                toggle?.focus();
            }
        });
        window.addEventListener('resize', () => closeFlyout());
    }

    window.WorkspaceAppearance = { applyTheme, init };
    document.addEventListener('DOMContentLoaded', init);
})();
