// Primera Infancia — Capa responsiva para celulares y tabletas.
// No altera rutas, permisos, datos, IDs existentes ni lógica de negocio.
(function () {
    'use strict';

    const MOBILE_QUERY = '(max-width: 1024px)';
    const media = window.matchMedia(MOBILE_QUERY);
    let menuToggle = null;
    let menuOverlay = null;
    let menuClose = null;
    let sidebar = null;
    let mainContent = null;
    let ultimoFoco = null;
    let enhancementScheduled = false;

    function crearControlesMenu() {
        const header = document.querySelector('#app-shell > main > header');
        mainContent = document.querySelector('#app-shell > main');
        sidebar = document.getElementById('sidebar-institucional');
        if (!header || !sidebar) return;

        menuToggle = document.getElementById('pi-mobile-menu-toggle');
        if (!menuToggle) {
            menuToggle = document.createElement('button');
            menuToggle.type = 'button';
            menuToggle.id = 'pi-mobile-menu-toggle';
            menuToggle.setAttribute('aria-label', 'Abrir menú principal');
            menuToggle.setAttribute('aria-controls', 'sidebar-institucional');
            menuToggle.setAttribute('aria-expanded', 'false');
            menuToggle.innerHTML = '<span class="pi-mobile-menu-icon" aria-hidden="true"><span></span></span>';
            header.insertBefore(menuToggle, header.firstChild);
        }

        menuOverlay = document.getElementById('pi-mobile-menu-overlay');
        if (!menuOverlay) {
            menuOverlay = document.createElement('div');
            menuOverlay.id = 'pi-mobile-menu-overlay';
            menuOverlay.setAttribute('aria-hidden', 'true');
            document.body.appendChild(menuOverlay);
        }

        menuClose = document.getElementById('pi-mobile-menu-close');
        if (!menuClose) {
            menuClose = document.createElement('button');
            menuClose.type = 'button';
            menuClose.id = 'pi-mobile-menu-close';
            menuClose.setAttribute('aria-label', 'Cerrar menú principal');
            menuClose.textContent = 'Cerrar menú';
            sidebar.insertBefore(menuClose, sidebar.firstChild);
        }

        if (menuToggle.dataset.piResponsiveBound !== '1') {
            menuToggle.dataset.piResponsiveBound = '1';
            menuToggle.addEventListener('click', function () {
                if (document.body.classList.contains('pi-mobile-menu-open')) cerrarMenu(true);
                else abrirMenu();
            });
        }

        if (menuOverlay.dataset.piResponsiveBound !== '1') {
            menuOverlay.dataset.piResponsiveBound = '1';
            menuOverlay.addEventListener('click', function () { cerrarMenu(true); });
        }

        if (menuClose.dataset.piResponsiveBound !== '1') {
            menuClose.dataset.piResponsiveBound = '1';
            menuClose.addEventListener('click', function () { cerrarMenu(true); });
        }

        if (sidebar.dataset.piResponsiveBound !== '1') {
            sidebar.dataset.piResponsiveBound = '1';
            sidebar.addEventListener('click', function (event) {
                if (!media.matches) return;
                const opcion = event.target.closest('.pi-menu-item, [data-menu-item]');
                if (opcion) {
                    cerrarMenu(false);
                    window.setTimeout(enfocarContenidoActivo, 0);
                }
            });
        }

        actualizarModoMenu();
    }

    function abrirMenu() {
        if (!media.matches || !sidebar) return;
        ultimoFoco = document.activeElement;
        document.body.classList.add('pi-mobile-menu-open');
        menuToggle?.setAttribute('aria-expanded', 'true');
        menuToggle?.setAttribute('aria-label', 'Cerrar menú principal');
        menuOverlay?.setAttribute('aria-hidden', 'false');
        sidebar.setAttribute('aria-hidden', 'false');
        mainContent?.setAttribute('inert', '');
        window.setTimeout(function () {
            const primerControl = menuClose || sidebar.querySelector('.pi-menu-item:not(.hidden), .pi-menu-group-toggle');
            primerControl?.focus({ preventScroll: true });
        }, 230);
    }

    function cerrarMenu(restaurarFoco) {
        document.body.classList.remove('pi-mobile-menu-open');
        menuToggle?.setAttribute('aria-expanded', 'false');
        menuToggle?.setAttribute('aria-label', 'Abrir menú principal');
        menuOverlay?.setAttribute('aria-hidden', 'true');
        if (sidebar && media.matches) sidebar.setAttribute('aria-hidden', 'true');
        mainContent?.removeAttribute('inert');
        if (restaurarFoco && ultimoFoco && typeof ultimoFoco.focus === 'function') {
            ultimoFoco.focus({ preventScroll: true });
        }
    }

    function enfocarContenidoActivo() {
        const section = document.querySelector('#app-shell > main section:not(.hidden)');
        const heading = section?.querySelector('h1, h2, h3');
        if (!heading) return;
        heading.setAttribute('tabindex', '-1');
        heading.focus({ preventScroll: true });
    }

    function contenerFocoMenu(event) {
        if (event.key !== 'Tab' || !media.matches || !document.body.classList.contains('pi-mobile-menu-open') || !sidebar) return;
        const controls = Array.from(sidebar.querySelectorAll('button:not([disabled]):not(.hidden), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'))
            .filter(function (control) { return control.getClientRects().length > 0; });
        if (!controls.length) return;
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    function actualizarModoMenu() {
        document.body.classList.toggle('pi-mobile-nav-enabled', media.matches);
        if (!sidebar) sidebar = document.getElementById('sidebar-institucional');
        if (media.matches) {
            if (!document.body.classList.contains('pi-mobile-menu-open')) {
                sidebar?.setAttribute('aria-hidden', 'true');
            }
        } else {
            cerrarMenu(false);
            sidebar?.removeAttribute('aria-hidden');
        }
    }

    function numeroColumnas(table) {
        const filas = Array.from(table.rows || []).slice(0, 6);
        return filas.reduce(function (max, row) {
            let total = 0;
            Array.from(row.cells || []).forEach(function (cell) {
                total += Number.parseInt(cell.getAttribute('colspan') || '1', 10) || 1;
            });
            return Math.max(max, total);
        }, 0);
    }

    function mejorarTabla(table) {
        if (!table) return;
        const preparada = table.dataset.piResponsiveReady === '1';

        let wrapper = table.parentElement;
        const parentAlreadyScrolls = wrapper && (
            wrapper.classList.contains('overflow-x-auto') ||
            wrapper.classList.contains('pc-table-wrap') ||
            wrapper.classList.contains('gg-table-wrap') ||
            wrapper.classList.contains('pi-responsive-table-scroll') ||
            window.getComputedStyle(wrapper).overflowX === 'auto' ||
            window.getComputedStyle(wrapper).overflowX === 'scroll'
        );

        if (!preparada && !parentAlreadyScrolls) {
            const nuevoWrapper = document.createElement('div');
            nuevoWrapper.className = 'pi-responsive-table-scroll';
            table.parentNode.insertBefore(nuevoWrapper, table);
            nuevoWrapper.appendChild(table);
            wrapper = nuevoWrapper;
        } else if (wrapper) {
            wrapper.classList.add('pi-responsive-table-scroll');
        }

        table.dataset.piResponsiveReady = '1';

        wrapper.setAttribute('role', 'region');
        wrapper.setAttribute('aria-label', table.getAttribute('aria-label') || 'Tabla con desplazamiento horizontal');
        wrapper.tabIndex = 0;

        const columnas = numeroColumnas(table);
        if (columnas > 4) {
            const anchoMinimo = Math.min(1500, Math.max(700, columnas * 125));
            table.classList.add('pi-responsive-wide-table');
            table.style.setProperty('--pi-responsive-table-min-width', anchoMinimo + 'px');
        } else {
            table.classList.remove('pi-responsive-wide-table');
            table.style.removeProperty('--pi-responsive-table-min-width');
        }

        if (!wrapper.nextElementSibling?.classList.contains('pi-responsive-scroll-hint')) {
            const hint = document.createElement('p');
            hint.className = 'pi-responsive-scroll-hint';
            hint.textContent = 'Desliza horizontalmente para ver todas las columnas.';
            wrapper.insertAdjacentElement('afterend', hint);
        }
    }

    function mejorarCalendarios(root) {
        root.querySelectorAll?.('.ci-calendar-grid:not([data-pi-responsive-ready])').forEach(function (grid) {
            grid.dataset.piResponsiveReady = '1';
            const wrapper = document.createElement('div');
            wrapper.className = 'pi-responsive-calendar-scroll';
            wrapper.setAttribute('role', 'region');
            wrapper.setAttribute('aria-label', 'Calendario con desplazamiento horizontal');
            wrapper.tabIndex = 0;
            grid.parentNode.insertBefore(wrapper, grid);
            wrapper.appendChild(grid);
        });
    }

    function optimizarImagenes(root) {
        root.querySelectorAll?.('img:not([data-pi-responsive-image])').forEach(function (img, index) {
            img.dataset.piResponsiveImage = '1';
            img.decoding = 'async';
            const critica = Boolean(img.closest('#login-screen, #sidebar-institucional, #app-shell > main > header'));
            if (!critica && index > 0) {
                img.loading = 'lazy';
                img.fetchPriority = 'low';
            }
        });
    }

    function mejorarContenido(root) {
        const scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll('table').forEach(mejorarTabla);
        mejorarCalendarios(scope);
        optimizarImagenes(scope);
    }

    function programarMejoras() {
        if (enhancementScheduled) return;
        enhancementScheduled = true;
        const ejecutar = function () {
            enhancementScheduled = false;
            mejorarContenido(document);
        };
        if ('requestIdleCallback' in window) window.requestIdleCallback(ejecutar, { timeout: 700 });
        else window.setTimeout(ejecutar, 90);
    }

    function init() {
        if (document.documentElement.dataset.piResponsiveReady === '1') return;
        document.documentElement.dataset.piResponsiveReady = '1';

        crearControlesMenu();
        mejorarContenido(document);

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && document.body.classList.contains('pi-mobile-menu-open')) {
                cerrarMenu(true);
            }
            contenerFocoMenu(event);
        });

        if (typeof media.addEventListener === 'function') media.addEventListener('change', actualizarModoMenu);
        else if (typeof media.addListener === 'function') media.addListener(actualizarModoMenu);

        const observer = new MutationObserver(function (mutations) {
            const hayNodosNuevos = mutations.some(function (mutation) { return mutation.addedNodes.length > 0; });
            if (hayNodosNuevos) programarMejoras();
        });
        observer.observe(document.body, { childList: true, subtree: true });

        let resizeTimer = null;
        const alCambiarViewport = function () {
            window.clearTimeout(resizeTimer);
            resizeTimer = window.setTimeout(function () {
                actualizarModoMenu();
                programarMejoras();
            }, 100);
        };
        window.addEventListener('resize', alCambiarViewport, { passive: true });
        window.addEventListener('orientationchange', alCambiarViewport, { passive: true });
        window.visualViewport?.addEventListener('resize', alCambiarViewport, { passive: true });

        window.PrimeraInfanciaResponsive = {
            abrirMenu: abrirMenu,
            cerrarMenu: cerrarMenu,
            actualizar: programarMejoras
        };
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
})();
