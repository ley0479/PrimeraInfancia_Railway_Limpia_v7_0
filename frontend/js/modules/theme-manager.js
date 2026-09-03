(function () {
    'use strict';

    const API = () => `${window.backendUrl || (typeof getBackendUrl === 'function' ? getBackendUrl() : window.getConfiguredBackendUrl?.() || window.location.origin)}/api/theme-manager`;
    const CACHE_KEY = 'primeraInfanciaThemeCacheAlpha29';
    const RESOURCE_ID = 'tm-theme-resource';
    const STYLE_KEYS = ['--pi-bg', '--pi-surface', '--pi-surface-soft', '--pi-border', '--pi-text', '--pi-muted', '--pi-primary', '--pi-primary-hover', '--pi-accent', '--pi-success', '--pi-warning', '--pi-danger', '--pi-radius', '--pi-font-scale', '--pi-font-family'];

    const state = {
        context: null,
        selectedThemeCode: 'base-actual',
        initialized: false,
    };

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function readCache() {
        try {
            return JSON.parse(localStorage.getItem(CACHE_KEY) || sessionStorage.getItem(CACHE_KEY) || 'null');
        } catch (_) {
            return null;
        }
    }

    function writeCache(context) {
        try {
            localStorage.setItem(CACHE_KEY, JSON.stringify({
                tema: context.tema,
                preferencia: context.preferencia,
                variables: context.variables,
                permisos: context.permisos,
                timestamp: Date.now()
            }));
        } catch (_) {}
    }

    function relativeThemeUrl(cssPath) {
        const clean = String(cssPath || '').replace(/^\/+/, '');
        if (!clean) return '';
        if (/^https?:\/\//i.test(clean)) return clean;
        return `../${clean}${clean.includes('?') ? '&' : '?'}v=2.3.0-alpha.29`;
    }

    function loadThemeResource(cssPath) {
        const existing = document.getElementById(RESOURCE_ID);
        if (existing) existing.remove();
        const href = relativeThemeUrl(cssPath);
        if (!href) return;
        const link = document.createElement('link');
        link.id = RESOURCE_ID;
        link.rel = 'stylesheet';
        link.href = href;
        document.head.appendChild(link);
    }

    function applyContext(context) {
        if (!context) return;
        const root = document.documentElement;
        const pref = context.preferencia || {};
        const theme = context.tema || {};
        const variables = context.variables || {};
        root.classList.add('theme-pi', 'tm-active');
        root.dataset.theme = theme.codigo || pref.tema_codigo || 'ocean-deep';
        root.dataset.themeCode = theme.codigo || pref.tema_codigo || 'base-actual';
        root.dataset.tmMode = pref.modo || 'oscuro';
        root.dataset.tmContrast = pref.contraste || 'normal';
        root.dataset.tmLayout = pref.layout || 'normal';
        root.dataset.density = pref.densidad || 'comfortable';
        root.dataset.tmDensity = pref.densidad || 'comfortable';
        root.dataset.tmCards = pref.custom_json?.cards || 'elevated';
        root.dataset.tmMotion = pref.custom_json?.animations === 'reduced' || pref.custom_json?.reduced_motion ? 'reduced' : 'full';
        const configuredMode = theme.configuracion?.colorMode || (pref.modo === 'claro' ? 'light' : 'dark');
        const resolvedMode = pref.modo === 'auto'
            ? (window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
            : (pref.modo === 'claro' ? 'light' : configuredMode);
        root.dataset.bsTheme = resolvedMode;
        root.dataset.sidebar = pref.layout === 'compacto' ? 'compact' : 'normal';
        root.style.setProperty('--pi-density-y', pref.densidad === 'compact' ? '.82' : (pref.densidad === 'spacious' ? '1.18' : '1'));
        STYLE_KEYS.forEach((key) => {
            if (variables[key]) root.style.setProperty(key, variables[key]);
        });
        loadThemeResource(theme.css_path || '');
        state.context = context;
        state.selectedThemeCode = theme.codigo || pref.tema_codigo || 'base-actual';
        writeCache(context);
        syncDashboardButton();
        syncMiniLabels();
        window.dispatchEvent(new CustomEvent('app:theme-changed', { detail: {
            themeKey: root.dataset.theme,
            colorMode: resolvedMode,
            variables: { ...variables }
        }}));
    }

    function applyCachedTheme() {
        const cached = readCache();
        if (cached && cached.variables) applyContext(cached);
    }

    async function fetchContext() {
        const resp = await fetch(`${API()}/actual`);
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || 'No se pudo consultar el gestor de temas.');
        return data;
    }

    async function initSessionTheme() {
        applyCachedTheme();
        try {
            const context = await fetchContext();
            applyContext(context);
            renderAdminIfVisible();
            renderSelectorOptions();
            return context;
        } catch (error) {
            console.warn('Theme Manager no pudo sincronizar:', error.message || error);
            syncDashboardButton();
            return state.context;
        } finally {
            state.initialized = true;
        }
    }

    function canChangeTheme() {
        return !!state.context?.permisos?.puede_cambiar_tema;
    }

    function canAdminThemes() {
        return !!state.context?.permisos?.puede_administrar;
    }

    function syncDashboardButton() {
        const btn = document.getElementById('tm-dashboard-change-btn');
        if (btn) btn.classList.toggle('hidden', !canChangeTheme());
        const adminBtn = document.getElementById('tm-dashboard-admin-btn');
        if (adminBtn) adminBtn.classList.toggle('hidden', !canAdminThemes());
        const adminHint = document.getElementById('tm-admin-only-hint');
        if (adminHint) adminHint.classList.toggle('hidden', canAdminThemes());
    }

    function syncMiniLabels() {
        const theme = state.context?.tema || {};
        const pref = state.context?.preferencia || {};
        const byId = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };
        byId('tm-current-theme-label', theme.nombre || 'Dashboard actual');
        byId('tm-current-mode-label', pref.modo || 'oscuro');
        byId('tm-current-layout-label', pref.layout || 'normal');
        byId('tm-card-tema-activo', theme.nombre || '—');
        byId('tm-card-modo', pref.modo || '—');
        byId('tm-card-contraste', pref.contraste || '—');
        byId('tm-card-fuente', `${pref.font_scale || 100}%`);
    }

    function abrirSelector() {
        if (!state.context) {
            initSessionTheme().then(abrirSelector).catch(() => {});
            return;
        }
        if (!canChangeTheme()) {
            alert('El administrador no ha habilitado el cambio de diseño para tu usuario.');
            return;
        }
        ensureSelectorModal();
        fillPreferenceForm(state.context.preferencia || {});
        renderSelectorOptions();
        document.getElementById('tm-selector-modal')?.classList.remove('hidden');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function cerrarSelector() {
        document.getElementById('tm-selector-modal')?.classList.add('hidden');
    }

    function ensureSelectorModal() {
        if (document.getElementById('tm-selector-modal')) return;
        const modal = document.createElement('div');
        modal.id = 'tm-selector-modal';
        modal.className = 'hidden';
        modal.innerHTML = `
            <div class="tm-modal-card">
                <div class="p-5 border-b border-slate-800 flex items-start justify-between gap-4">
                    <div>
                        <h3 class="text-xl font-bold text-slate-100 flex items-center gap-2"><i data-lucide="palette" class="text-cyan-400"></i> Cambiar diseño</h3>
                        <p class="text-sm text-slate-400 mt-1">Tu preferencia se guarda en base de datos y se mantiene entre sesiones.</p>
                    </div>
                    <button type="button" class="tm-btn tm-btn-secondary" onclick="ThemeManager.cerrarSelector()">Cerrar</button>
                </div>
                <div class="p-5 space-y-5">
                    <div id="tm-selector-options" class="grid gap-3 sm:grid-cols-2"></div>
                    <div class="grid gap-4 md:grid-cols-2">
                        <label><span class="tm-label mb-2">Modo</span><select id="tm-pref-modo" class="tm-select"><option value="oscuro">Oscuro</option><option value="claro">Claro</option><option value="auto">Automático</option></select></label>
                        <label><span class="tm-label mb-2">Contraste</span><select id="tm-pref-contraste" class="tm-select"><option value="normal">Normal</option><option value="alto">Alto contraste</option></select></label>
                        <label><span class="tm-label mb-2">Tamaño de letra</span><input id="tm-pref-font" class="tm-input" type="number" min="85" max="125" step="5"></label>
                        <label><span class="tm-label mb-2">Distribución</span><select id="tm-pref-layout" class="tm-select"><option value="normal">Normal</option><option value="compacto">Compacta</option><option value="amplio">Amplia</option></select></label>
                        <label><span class="tm-label mb-2">Densidad</span><select id="tm-pref-densidad" class="tm-select"><option value="compact">Compacta</option><option value="comfortable">Cómoda</option><option value="spacious">Amplia</option></select></label>
                        <label><span class="tm-label mb-2">Redondez</span><input id="tm-pref-radio" class="tm-input" type="number" min="4" max="32" step="2"></label>
                    </div>
                    <div id="tm-selector-message" class="hidden rounded-xl px-4 py-3 text-sm"></div>
                    <div class="flex flex-wrap justify-end gap-2">
                        <button type="button" onclick="ThemeManager.cerrarSelector()" class="tm-btn tm-btn-secondary">Cancelar</button>
                        <button type="button" onclick="ThemeManager.guardarPreferenciaUsuario()" class="tm-btn tm-btn-primary">Guardar diseño</button>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(modal);
    }

    function renderSelectorOptions() {
        const cont = document.getElementById('tm-selector-options');
        if (!cont || !state.context) return;
        const themes = (state.context.temas || []).filter(t => t.activo !== false);
        const current = state.selectedThemeCode || state.context.preferencia?.tema_codigo || 'base-actual';
        cont.innerHTML = themes.map((theme) => {
            const colors = theme.configuracion?.colors || {};
            return `
                <button type="button" class="tm-theme-option text-left" data-code="${escapeHtml(theme.codigo)}" aria-selected="${theme.codigo === current}" onclick="ThemeManager.seleccionarTema('${escapeHtml(theme.codigo)}')">
                    <div class="flex items-center justify-between gap-2">
                        <div class="font-semibold text-slate-100">${escapeHtml(theme.nombre)}</div>
                        <span class="tm-badge">${theme.es_sistema ? 'Sistema' : 'Personalizado'}</span>
                    </div>
                    <p class="mt-1 text-xs text-slate-400 line-clamp-2">${escapeHtml(theme.descripcion || 'Sin descripción')}</p>
                    <div class="mt-3 grid grid-cols-5 gap-1">
                        ${['primary', 'accent', 'background', 'surface', 'text'].map(k => `<span class="tm-swatch" style="background:${escapeHtml(colors[k] || '#334155')}"></span>`).join('')}
                    </div>
                </button>`;
        }).join('') || '<p class="text-sm text-slate-400">No hay temas activos.</p>';
    }

    function seleccionarTema(codigo) {
        state.selectedThemeCode = codigo;
        document.querySelectorAll('.tm-theme-option').forEach((btn) => {
            btn.setAttribute('aria-selected', btn.dataset.code === codigo ? 'true' : 'false');
        });
    }

    function fillPreferenceForm(pref) {
        const set = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.value = value;
        };
        state.selectedThemeCode = pref.tema_codigo || state.context?.tema?.codigo || 'base-actual';
        set('tm-pref-modo', pref.modo || 'oscuro');
        set('tm-pref-contraste', pref.contraste || 'normal');
        set('tm-pref-font', pref.font_scale || 100);
        set('tm-pref-layout', pref.layout || 'normal');
        set('tm-pref-densidad', pref.densidad || 'comfortable');
        set('tm-pref-radio', pref.radio || 16);
    }

    function readPreferenceForm() {
        return {
            tema_codigo: state.selectedThemeCode || 'base-actual',
            modo: document.getElementById('tm-pref-modo')?.value || 'oscuro',
            contraste: document.getElementById('tm-pref-contraste')?.value || 'normal',
            font_scale: Number(document.getElementById('tm-pref-font')?.value || 100),
            layout: document.getElementById('tm-pref-layout')?.value || 'normal',
            densidad: document.getElementById('tm-pref-densidad')?.value || 'comfortable',
            radio: Number(document.getElementById('tm-pref-radio')?.value || 16)
        };
    }

    function showSelectorMessage(text, type = 'success') {
        const box = document.getElementById('tm-selector-message');
        if (!box) return;
        box.className = `rounded-xl px-4 py-3 text-sm ${type === 'success' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'}`;
        box.textContent = text;
        box.classList.remove('hidden');
    }

    async function guardarPreferenciaUsuario() {
        try {
            const resp = await fetch(`${API()}/preferencia`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(readPreferenceForm())
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'No se pudo guardar el diseño.');
            applyContext(data);
            showSelectorMessage(data.message || 'Diseño guardado.', 'success');
            renderAdminIfVisible();
        } catch (error) {
            showSelectorMessage(error.message || 'No se pudo guardar el diseño.', 'error');
        }
    }

    async function initAdmin() {
        if (!state.context) await initSessionTheme();
        renderAdminIfVisible(true);
    }

    function renderAdminIfVisible(force = false) {
        const section = document.getElementById('administrador-disenos');
        const visible = section && !section.classList.contains('hidden');
        if (!force && !visible && !document.getElementById('tm-card-tema-activo')) return;
        if (!document.getElementById('tm-admin-temas-table')) return;
        const ctx = state.context || {};
        syncMiniLabels();
        const canAdmin = canAdminThemes();
        document.querySelectorAll('[data-tm-admin-only]').forEach(el => el.classList.toggle('hidden', !canAdmin));
        renderThemesTable();
        fillCorpConfigForm();
        renderAuditSummary();
        previewThemeBuilder();
    }

    function renderThemesTable() {
        const tbody = document.getElementById('tm-admin-temas-table');
        if (!tbody || !state.context) return;
        const themes = state.context.temas || [];
        tbody.innerHTML = themes.map((theme) => {
            const colors = theme.configuracion?.colors || {};
            return `
                <tr>
                    <td>
                        <div class="font-semibold text-slate-100">${escapeHtml(theme.nombre)}</div>
                        <div class="text-xs text-slate-500">${escapeHtml(theme.codigo)}</div>
                    </td>
                    <td><span class="tm-badge">${theme.es_sistema ? 'Sistema' : 'Personalizado'}</span></td>
                    <td><div class="flex gap-1">${['primary', 'accent', 'surface', 'text'].map(k => `<span class="inline-block h-6 w-6 rounded-lg border border-white/10" style="background:${escapeHtml(colors[k] || '#334155')}"></span>`).join('')}</div></td>
                    <td>${theme.activo ? '<span class="text-emerald-300">Activo</span>' : '<span class="text-rose-300">Inactivo</span>'}</td>
                    <td class="text-right">
                        <button class="tm-btn tm-btn-secondary text-xs" onclick="ThemeManager.toggleTema('${escapeHtml(theme.codigo)}', ${theme.activo ? 0 : 1})">${theme.activo ? 'Desactivar' : 'Activar'}</button>
                    </td>
                </tr>`;
        }).join('') || '<tr><td colspan="5" class="text-center text-slate-500 py-8">Sin temas registrados.</td></tr>';

        const select = document.getElementById('tm-corp-theme');
        if (select) {
            const activeThemes = themes.filter(t => t.activo !== false);
            select.innerHTML = activeThemes.map(t => `<option value="${escapeHtml(t.codigo)}">${escapeHtml(t.nombre)}</option>`).join('');
        }
    }

    function fillCorpConfigForm() {
        const cfg = state.context?.configuracion_corporacion || {};
        const set = (id, value, prop = 'value') => {
            const el = document.getElementById(id);
            if (el) el[prop] = value;
        };
        set('tm-corp-theme', cfg.tema_default_codigo || 'base-actual');
        set('tm-corp-permitir', !!cfg.permitir_usuario_cambiar, 'checked');
        set('tm-corp-modo', cfg.modo_default || 'oscuro');
        set('tm-corp-contraste', cfg.contraste_default || 'normal');
        set('tm-corp-font', cfg.font_scale_default || 100);
        set('tm-corp-layout', cfg.layout_default || 'normal');
        set('tm-corp-densidad', cfg.densidad_default || 'comfortable');
        set('tm-corp-radio', cfg.radio_default || 16);
    }

    function showAdminMessage(text, type = 'success') {
        const box = document.getElementById('tm-admin-message');
        if (!box) return;
        box.className = `rounded-xl px-4 py-3 text-sm ${type === 'success' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'}`;
        box.textContent = text;
        box.classList.remove('hidden');
    }

    async function guardarConfigCorporacion() {
        try {
            const payload = {
                tema_default_codigo: document.getElementById('tm-corp-theme')?.value || 'base-actual',
                permitir_usuario_cambiar: !!document.getElementById('tm-corp-permitir')?.checked,
                modo_default: document.getElementById('tm-corp-modo')?.value || 'oscuro',
                contraste_default: document.getElementById('tm-corp-contraste')?.value || 'normal',
                font_scale_default: Number(document.getElementById('tm-corp-font')?.value || 100),
                layout_default: document.getElementById('tm-corp-layout')?.value || 'normal',
                densidad_default: document.getElementById('tm-corp-densidad')?.value || 'comfortable',
                radio_default: Number(document.getElementById('tm-corp-radio')?.value || 16)
            };
            const resp = await fetch(`${API()}/corporacion`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'No se pudo guardar la configuración.');
            applyContext(data);
            showAdminMessage(data.message || 'Configuración guardada.', 'success');
            renderAdminIfVisible(true);
        } catch (error) {
            showAdminMessage(error.message || 'No se pudo guardar la configuración.', 'error');
        }
    }

    async function toggleTema(codigo, activo) {
        try {
            const resp = await fetch(`${API()}/temas/${encodeURIComponent(codigo)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ activo })
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'No se pudo actualizar el tema.');
            state.context = await fetchContext();
            applyContext(state.context);
            showAdminMessage(data.message || 'Tema actualizado.', 'success');
            renderAdminIfVisible(true);
        } catch (error) {
            showAdminMessage(error.message || 'No se pudo actualizar el tema.', 'error');
        }
    }

    function readBuilderConfig() {
        const get = (id, fallback = '') => document.getElementById(id)?.value || fallback;
        return {
            colors: {
                primary: get('tm-new-primary', '#4f46e5'),
                primaryHover: get('tm-new-primary-hover', '#4338ca'),
                accent: get('tm-new-accent', '#06b6d4'),
                background: get('tm-new-bg', '#020617'),
                surface: get('tm-new-surface', '#0f172a'),
                surfaceSoft: get('tm-new-soft', '#1e293b'),
                border: get('tm-new-border', '#334155'),
                text: get('tm-new-text', '#f8fafc'),
                muted: get('tm-new-muted', '#94a3b8'),
                success: get('tm-new-success', '#10b981'),
                warning: get('tm-new-warning', '#f59e0b'),
                danger: get('tm-new-danger', '#ef4444'),
            },
            typography: {
                fontFamily: get('tm-new-font-family', 'Inter, system-ui, sans-serif'),
                fontScale: Number(get('tm-new-font-scale', 100)),
            },
            layout: {
                density: get('tm-new-density', 'comfortable'),
                radius: Number(get('tm-new-radius', 16)),
                sidebar: get('tm-new-sidebar', 'normal'),
                cards: get('tm-new-cards', 'rounded'),
            },
            icons: {
                style: get('tm-new-icon-style', 'lucide'),
                accent: get('tm-new-accent', '#06b6d4'),
            },
            accessibility: {
                contrast: get('tm-new-contrast', 'normal'),
                reduceMotion: !!document.getElementById('tm-new-reduce-motion')?.checked,
            }
        };
    }

    function previewThemeBuilder() {
        const preview = document.getElementById('tm-builder-preview');
        if (!preview) return;
        const cfg = readBuilderConfig();
        const c = cfg.colors;
        preview.style.setProperty('--tm-preview-surface', c.surface);
        preview.style.setProperty('--tm-preview-soft', c.surfaceSoft);
        preview.style.setProperty('--tm-preview-text', c.text);
        preview.style.setProperty('--pi-border', c.border);
        preview.style.setProperty('--pi-radius', `${cfg.layout.radius}px`);
        preview.innerHTML = `
            <div class="tm-preview-inner">
                <div class="flex items-center justify-between gap-3">
                    <div>
                        <p class="text-xs" style="color:${escapeHtml(c.muted)}">Vista previa</p>
                        <h4 class="text-lg font-bold" style="color:${escapeHtml(c.text)}">${escapeHtml(document.getElementById('tm-new-name')?.value || 'Nuevo tema institucional')}</h4>
                    </div>
                    <span class="rounded-xl px-3 py-2 text-xs font-bold" style="background:${escapeHtml(c.primary)};color:white">Botón</span>
                </div>
                <div class="mt-4 grid grid-cols-6 gap-2">
                    ${Object.values(c).slice(0, 12).map(color => `<span class="tm-swatch" style="background:${escapeHtml(color)}"></span>`).join('')}
                </div>
            </div>`;
    }

    async function crearTemaDesdeGUI() {
        try {
            const payload = {
                codigo: document.getElementById('tm-new-code')?.value,
                nombre: document.getElementById('tm-new-name')?.value,
                descripcion: document.getElementById('tm-new-description')?.value,
                categoria: 'personalizado',
                icono: document.getElementById('tm-new-icon')?.value || 'palette',
                configuracion: readBuilderConfig()
            };
            const resp = await fetch(`${API()}/temas`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'No se pudo crear el tema.');
            state.context = await fetchContext();
            renderAdminIfVisible(true);
            showAdminMessage(data.message || 'Tema creado correctamente.', 'success');
        } catch (error) {
            showAdminMessage(error.message || 'No se pudo crear el tema.', 'error');
        }
    }

    function autoCodigoTema() {
        const name = document.getElementById('tm-new-name')?.value || '';
        const code = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48);
        const input = document.getElementById('tm-new-code');
        if (input && (!input.value || input.dataset.auto === '1')) {
            input.value = code || 'tema-personalizado';
            input.dataset.auto = '1';
        }
    }

    function renderAuditSummary() {
        const el = document.getElementById('tm-admin-summary');
        if (!el || !state.context) return;
        const total = (state.context.temas || []).length;
        const activos = (state.context.temas || []).filter(t => t.activo !== false).length;
        const custom = (state.context.temas || []).filter(t => !t.es_sistema).length;
        el.innerHTML = `
            <div class="tm-card"><span class="tm-label">Temas registrados</span><strong class="tm-value">${total}</strong></div>
            <div class="tm-card"><span class="tm-label">Temas activos</span><strong class="tm-value text-emerald-300">${activos}</strong></div>
            <div class="tm-card"><span class="tm-label">Personalizados</span><strong class="tm-value text-cyan-300">${custom}</strong></div>
            <div class="tm-card"><span class="tm-label">Cambio por usuario</span><strong class="tm-value">${state.context.configuracion_corporacion?.permitir_usuario_cambiar ? 'Sí' : 'No'}</strong></div>`;
    }

    function bindBuilderEvents() {
        document.querySelectorAll('[data-tm-preview]').forEach(el => {
            if (el.dataset.tmBound === '1') return;
            el.dataset.tmBound = '1';
            el.addEventListener('input', previewThemeBuilder);
            el.addEventListener('change', previewThemeBuilder);
        });
        const name = document.getElementById('tm-new-name');
        if (name && name.dataset.tmBoundName !== '1') {
            name.dataset.tmBoundName = '1';
            name.addEventListener('input', () => { autoCodigoTema(); previewThemeBuilder(); });
        }
    }

    window.ThemeManager = {
        state,
        applyCachedTheme,
        initSessionTheme,
        initAdmin,
        abrirSelector,
        cerrarSelector,
        seleccionarTema,
        guardarPreferenciaUsuario,
        guardarConfigCorporacion,
        toggleTema,
        crearTemaDesdeGUI,
        previewThemeBuilder,
        autoCodigoTema,
        bindBuilderEvents,
    };

    applyCachedTheme();
})();
