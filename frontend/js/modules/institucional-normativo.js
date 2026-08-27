/* ALPHA41 - Configuración Institucional y Motor Normativo base.
   Carga bajo demanda: no lee manuales ni PDFs al iniciar la plataforma. */
(function () {
    let configLoaded = false;
    let manualLoaded = false;
    let configuracionActual = null;
    const protectedAssetObjectUrls = new Map();

    function token() {
        try {
            if (typeof authToken === 'function') return authToken() || '';
        } catch (_) {}
        return localStorage.getItem('primeraInfanciaAuthToken') || localStorage.getItem('token') || '';
    }

    function authHeaders(extra = {}) {
        const t = token();
        return {
            ...extra,
            ...(t ? { Authorization: `Bearer ${t}`, 'X-Auth-Token': t } : {})
        };
    }

    function apiUrl(path) {
        const base = window.backendUrl || (typeof getBackendUrl === 'function' ? getBackendUrl() : window.getConfiguredBackendUrl?.() || window.location.origin);
        return `${base}${path}`;
    }

    function descargarArchivoInstitucional(path) {
        return window.descargarArchivoAutenticado(apiUrl(path)).catch((error) => {
            mostrar('ci-message', error.message || 'No se pudo descargar el archivo.', 'error');
        });
    }

    function qs(id) {
        return document.getElementById(id);
    }

    function escapeHtml(value) {
        if (typeof escaparHtml === 'function') return escaparHtml(value);
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function mostrar(id, texto, tipo = 'success') {
        if (typeof mostrarMensaje === 'function') {
            mostrarMensaje(id, texto, tipo);
            return;
        }
        const box = qs(id);
        if (!box) return;
        box.className = `mt-4 rounded-xl border px-4 py-3 text-sm ${tipo === 'success' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300' : 'border-rose-500/20 bg-rose-500/10 text-rose-300'}`;
        box.textContent = texto;
        box.classList.remove('hidden');
    }

    function limpiarMensaje(id) {
        const box = qs(id);
        if (!box) return;
        box.classList.add('hidden');
        box.textContent = '';
    }

    async function fetchJson(path, options = {}) {
        const response = await fetch(apiUrl(path), {
            ...options,
            headers: authHeaders(options.headers || {})
        });
        let data = {};
        try { data = await response.json(); } catch (_) { data = {}; }
        if (!response.ok) throw new Error(data.error || `Error del servidor (${response.status})`);
        return data;
    }

    function setValue(id, value) {
        const el = qs(id);
        if (el) el.value = value || '';
    }

    function setText(id, value) {
        const el = qs(id);
        if (el) el.textContent = value || '';
    }

    function esAmbitoGlobal() {
        return qs('ci-scope')?.value === 'GLOBAL';
    }

    const IDENTITY_SCOPE_KEY = 'primeraInfanciaIdentityScope';

    function restaurarAmbitoSeleccionado() {
        const scope = qs('ci-scope');
        if (!scope) return;
        try {
            const saved = sessionStorage.getItem(IDENTITY_SCOPE_KEY);
            if (saved === 'GLOBAL' || saved === 'FUNDACION') scope.value = saved;
        } catch (_) {}
    }

    function actualizarAvisoAmbito() {
        setText('ci-scope-target', esAmbitoGlobal()
            ? 'Esta modificación se aplicará a TODA LA PLATAFORMA y será heredada por fundaciones sin personalización.'
            : 'Esta modificación se aplicará a la FUNDACIÓN de la sesión actual.');
    }

    function backendBaseUrl() {
        const base = window.backendUrl || (typeof getBackendUrl === 'function' ? getBackendUrl() : window.getConfiguredBackendUrl?.() || window.location.origin);
        return String(base || '').replace(/\/$/, '');
    }

    function resolveAssetUrl(url) {
        if (!url) return '';
        const value = String(url).trim();
        if (/^(?:https?:|data:|blob:)/i.test(value)) return value;
        const normalized = value.startsWith('/') ? value : `/${value}`;
        return `${backendBaseUrl()}${normalized}`;
    }

    function versionedAssetUrl(url, version) {
        const resolved = resolveAssetUrl(url);
        if (!resolved) return '';
        const separator = resolved.includes('?') ? '&' : '?';
        return `${resolved}${separator}v=${encodeURIComponent(version || 1)}`;
    }

    function isProtectedInstitutionalAsset(url) {
        try {
            const parsed = new URL(url, window.location.origin);
            return parsed.pathname.startsWith('/api/institucional-archivos/');
        } catch (_) {
            return String(url || '').includes('/api/institucional-archivos/');
        }
    }

    async function loadProtectedAsset(url) {
        if (!isProtectedInstitutionalAsset(url)) return url;
        if (protectedAssetObjectUrls.has(url)) return protectedAssetObjectUrls.get(url);
        const response = await fetch(url, { headers: authHeaders() });
        if (!response.ok) {
            let message = `No se pudo cargar el recurso institucional (${response.status}).`;
            try {
                const data = await response.json();
                message = data.error || message;
            } catch (_) {}
            throw new Error(message);
        }
        const objectUrl = URL.createObjectURL(await response.blob());
        protectedAssetObjectUrls.set(url, objectUrl);
        return objectUrl;
    }

    function setImage(id, fallbackId, url, version) {
        const img = qs(id);
        const fallback = qs(fallbackId);
        if (!img) return;
        const requestId = `${Date.now()}-${Math.random()}`;
        img.dataset.identityRequest = requestId;
        const showFallback = () => {
            if (img.dataset.identityRequest !== requestId) return;
            img.removeAttribute('src');
            img.classList.add('hidden');
            if (fallback) fallback.classList.remove('hidden');
        };
        if (!url) { showFallback(); return; }
        img.onerror = showFallback;
        img.onload = () => {
            if (img.dataset.identityRequest !== requestId) return;
            img.classList.remove('hidden');
            if (fallback) fallback.classList.add('hidden');
        };
        const versioned = versionedAssetUrl(url, version);
        loadProtectedAsset(versioned)
            .then((resolved) => {
                if (img.dataset.identityRequest === requestId) img.src = resolved;
            })
            .catch(showFallback);
    }

    function setFavicon(url, version) {
        if (!url) return;
        let link = document.getElementById('institucional-favicon');
        if (!link) {
            link = document.createElement('link');
            link.id = 'institucional-favicon';
            link.rel = 'icon';
            document.head.appendChild(link);
        }
        const versioned = versionedAssetUrl(url, version);
        loadProtectedAsset(versioned)
            .then((resolved) => { link.href = resolved; })
            .catch(() => {});
    }

    function aplicarIdentidadInstitucional(config) {
        const anterior = configuracionActual || {};
        const entrante = config || {};
        configuracionActual = { ...anterior, ...entrante };
        // Al abrir una corporación también se carga su formulario local. Ese
        // registro puede traer campos visuales vacíos, pero no debe borrar la
        // identidad global efectiva que ya está visible en el encabezado.
        [
            'logo_principal_url', 'logo_reportes_url', 'logo_formatos_url',
            'favicon_url', 'foto_admin_url', 'nombre_admin', 'cargo_admin'
        ].forEach((key) => {
            if ((entrante[key] === null || entrante[key] === undefined || entrante[key] === '') && anterior[key]) {
                configuracionActual[key] = anterior[key];
            }
        });
        const plataforma = configuracionActual.nombre_plataforma || 'Primera Infancia';
        const nombre = configuracionActual.nombre_corporacion || 'Organización de prueba';
        const sigla = configuracionActual.sigla || 'ORGDEMO';
        const admin = configuracionActual.nombre_admin || 'Administrador General';
        const cargo = configuracionActual.cargo_admin || 'Administrador Plataforma';

        document.title = `${plataforma} - ${nombre}`;
        setText('institucional-plataforma-login', plataforma);
        setText('institucional-login-subtitle', nombre);
        setText('institucional-nombre-sidebar', nombre);
        setText('institucional-sigla-sidebar', sigla || plataforma);
        setText('institucional-nombre-header', `${nombre} · ${sigla || plataforma}`);
        setText('institucional-admin-nombre-header', admin);
        setText('institucional-admin-cargo-header', cargo);
        setText('ci-preview-nombre', nombre);
        setText('ci-preview-admin', `${admin} · ${cargo}`);

        const brandingVersion = configuracionActual.identity_version || configuracionActual.updated_at || configuracionActual.id || 1;
        setImage('institucional-logo-sidebar', 'institucional-logo-sidebar-fallback', configuracionActual.logo_principal_url, brandingVersion);
        setImage('institucional-logo-header', 'institucional-logo-header-fallback', configuracionActual.logo_principal_url, brandingVersion);
        setImage('institucional-logo-login', 'institucional-logo-login-fallback', configuracionActual.logo_principal_url, brandingVersion);
        setImage('ci-preview-logo', 'ci-preview-logo-fallback', configuracionActual.logo_principal_url, brandingVersion);
        setImage('ci-preview-foto-admin', 'ci-preview-foto-admin-fallback', configuracionActual.foto_admin_url, brandingVersion);
        setImage('institucional-foto-admin-header', 'institucional-foto-admin-fallback', configuracionActual.foto_admin_url, brandingVersion);
        setFavicon(configuracionActual.favicon_url || configuracionActual.logo_principal_url, brandingVersion);

        if (configuracionActual.color_primario) document.documentElement.style.setProperty('--df-blue', configuracionActual.color_primario);
        if (configuracionActual.color_secundario) document.documentElement.style.setProperty('--df-cyan', configuracionActual.color_secundario);

        if (typeof lucide !== 'undefined') {
            try { lucide.createIcons(); } catch (_) {}
        }
    }

    async function cargarConfiguracionInstitucional(silent = true) {
        try {
            const data = await fetchJson(esAmbitoGlobal() ? '/api/configuracion-global' : '/api/configuracion-institucional');
            const c = (esAmbitoGlobal() ? data.efectiva : data.configuracion) || data.configuracion || {};
            aplicarIdentidadInstitucional(c);
            setValue('ci-nombre-plataforma', c.nombre_plataforma);
            setValue('ci-nombre-corporacion', c.nombre_corporacion || c.nombre_plataforma);
            setValue('ci-sigla', c.sigla || c.sigla_plataforma);
            setValue('ci-nit', c.nit);
            setValue('ci-representante', c.representante_legal);
            setValue('ci-direccion', c.direccion);
            setValue('ci-telefono', c.telefono);
            setValue('ci-correo', c.correo);
            setValue('ci-color-primario', c.color_primario || c.color_primario_global);
            setValue('ci-color-secundario', c.color_secundario || c.color_secundario_global);
            setValue('ci-nombre-admin', c.nombre_admin || c.nombre_administrador_general);
            setValue('ci-cargo-admin', c.cargo_admin || c.cargo_administrador_general);
            configLoaded = true;
            if (!silent) mostrar('ci-message', 'Configuración institucional actualizada.', 'success');
        } catch (error) {
            if (!silent) mostrar('ci-message', error.message || 'No se pudo cargar la configuración institucional.', 'error');
        }
    }

    async function cargarIdentidadPublica(silent = true) {
        // La identidad pública pertenece exclusivamente al estado sin sesión.
        // Evita que una respuesta iniciada durante el login sobrescriba después
        // la identidad efectiva (fundación -> global -> fallback).
        if (token()) return cargarIdentidadEfectiva(silent);
        try {
            const data = await fetchJson('/api/configuracion-publica');
            const visual = data.configuracion || data;
            if (token()) return data;
            aplicarIdentidadInstitucional({
                nombre_plataforma: visual.nombre_plataforma,
                nombre_corporacion: visual.nombre_plataforma,
                sigla: visual.sigla_plataforma,
                logo_principal_url: visual.logo_global_url,
                favicon_url: visual.favicon_global_url,
                color_primario: visual.color_primario,
                color_secundario: visual.color_secundario,
                nombre_admin: visual.nombre_admin,
                cargo_admin: visual.cargo_admin,
                foto_admin_url: visual.foto_admin_url,
                identity_version: visual.identity_version
            });
            return data;
        } catch (error) {
            if (!silent) mostrar('ci-message', error.message || 'No se pudo cargar la identidad pública.', 'error');
            return null;
        }
    }

    async function cargarIdentidadEfectiva(silent = true) {
        try {
            const data = await fetchJson('/api/configuracion-institucional/efectiva');
            aplicarIdentidadInstitucional(data.configuracion || data.identidad || {});
            return data;
        } catch (error) {
            if (!silent) mostrar('ci-message', error.message || 'No se pudo cargar la identidad institucional.', 'error');
            return null;
        }
    }

    async function limpiarIdentidadInstitucional() {
        protectedAssetObjectUrls.forEach((objectUrl) => {
            try { URL.revokeObjectURL(objectUrl); } catch (_) {}
        });
        protectedAssetObjectUrls.clear();
        configuracionActual = null;
        configLoaded = false;
        return cargarIdentidadPublica(true);
    }

    async function guardarConfiguracionInstitucional(event, soloAdmin = false) {
        event?.preventDefault();
        limpiarMensaje('ci-message');
        let payload = soloAdmin ? {
            nombre_admin: qs('ci-nombre-admin')?.value.trim(),
            cargo_admin: qs('ci-cargo-admin')?.value.trim()
        } : {
            nombre_plataforma: qs('ci-nombre-plataforma')?.value.trim(),
            nombre_corporacion: qs('ci-nombre-corporacion')?.value.trim(),
            sigla: qs('ci-sigla')?.value.trim(),
            nit: qs('ci-nit')?.value.trim(),
            representante_legal: qs('ci-representante')?.value.trim(),
            direccion: qs('ci-direccion')?.value.trim(),
            telefono: qs('ci-telefono')?.value.trim(),
            correo: qs('ci-correo')?.value.trim(),
            color_primario: qs('ci-color-primario')?.value.trim(),
            color_secundario: qs('ci-color-secundario')?.value.trim()
        };
        if (esAmbitoGlobal()) {
            payload = soloAdmin ? {
                nombre_administrador_general: payload.nombre_admin,
                cargo_administrador_general: payload.cargo_admin
            } : {
                nombre_plataforma: payload.nombre_plataforma,
                sigla_plataforma: payload.sigla,
                color_primario_global: payload.color_primario,
                color_secundario_global: payload.color_secundario
            };
        }
        try {
            const data = await fetchJson(esAmbitoGlobal() ? '/api/configuracion-global' : '/api/configuracion-institucional', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            aplicarIdentidadInstitucional(data.configuracion || {});
            await cargarConfiguracionInstitucional(true);
            await cargarIdentidadEfectiva(true);
            mostrar('ci-message', data.message || 'Configuración guardada.', 'success');
        } catch (error) {
            mostrar('ci-message', error.message || 'No se pudo guardar la configuración.', 'error');
        }
    }

    async function subirArchivoConfiguracion(event, tipo) {
        event?.preventDefault();
        event?.stopPropagation();
        limpiarMensaje('ci-message');
        const input = tipo === 'foto' ? qs('ci-foto-file') : (tipo === 'favicon' ? qs('ci-favicon-file') : qs('ci-logo-file'));
        const file = input?.files?.[0];
        const submitter = event?.submitter || event?.currentTarget?.querySelector?.('button[type="submit"]');
        if (!file) {
            mostrar('ci-message', 'Selecciona un archivo antes de subir.', 'error');
            input?.focus();
            return;
        }
        const form = new FormData();
        form.append('file', file, file.name);
        if (tipo === 'logo') form.append('tipo', qs('ci-logo-tipo')?.value || 'principal');
        const base = esAmbitoGlobal() ? '/api/configuracion-global' : '/api/configuracion-institucional';
        const endpoint = tipo === 'foto' ? `${base}/foto-admin` : (tipo === 'favicon' ? `${base}/favicon` : `${base}/logo`);
        const oldHtml = submitter?.innerHTML;
        try {
            if (submitter) {
                submitter.disabled = true;
                submitter.setAttribute('aria-busy', 'true');
                submitter.textContent = 'Subiendo…';
            }
            mostrar('ci-message', `Subiendo ${file.name}…`, 'info');
            const data = await fetchJson(endpoint, { method: 'POST', body: form });
            if (!data?.configuracion) throw new Error('El servidor no devolvió la configuración actualizada.');
            aplicarIdentidadInstitucional(data.configuracion);
            input.value = '';
            await cargarConfiguracionInstitucional(true);
            await cargarIdentidadEfectiva(true);
            await cargarCatalogoIdentidadVisual(true);
            mostrar('ci-message', data.message || 'Archivo cargado correctamente.', 'success');
        } catch (error) {
            console.error('[Identidad visual] Error de subida:', error);
            mostrar('ci-message', error.message || 'No se pudo cargar el archivo.', 'error');
        } finally {
            if (submitter) {
                submitter.disabled = false;
                submitter.removeAttribute('aria-busy');
                submitter.innerHTML = oldHtml || 'Subir archivo';
                if (typeof lucide !== 'undefined') { try { lucide.createIcons(); } catch (_) {} }
            }
        }
    }

    const assetLabels = {
        logo_principal: 'Logo principal',
        logo_horizontal: 'Logo horizontal / encabezado',
        logo_reportes: 'Logo para reportes PDF',
        logo_formatos: 'Logo para formatos internos',
        logo_documentos: 'Logo para Word, Excel y PowerPoint',
        favicon_ico: 'Favicon ICO',
        favicon_png: 'Favicon PNG',
        logo_impresion: 'Logo para impresión 300 DPI'
        ,foto_admin: 'Foto del administrador general'
        ,'foto-admin': 'Foto del administrador general'
        ,logo: 'Logo global de plataforma'
        ,'logo-reportes': 'Logo global para reportes'
        ,'logo-formatos': 'Logo global para documentos y formatos'
        ,favicon: 'Favicon global'
    };

    function formatBytes(bytes) {
        const value = Number(bytes || 0);
        if (value < 1024) return `${value} B`;
        if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
        return `${(value / (1024 * 1024)).toFixed(1)} MB`;
    }

    function renderAssetCard(asset) {
        const preview = asset.url && !String(asset.nombre_archivo || '').toLowerCase().endsWith('.ico')
            ? `<img src="${escapeHtml(versionedAssetUrl(asset.url, asset.updated_at || asset.id))}" alt="Vista previa ${escapeHtml(assetLabels[asset.tipo] || asset.tipo)}" onerror="this.classList.add('hidden')" class="h-20 w-full rounded-xl bg-white/95 object-contain p-2">`
            : `<div class="h-20 w-full rounded-xl border border-dashed border-slate-700 bg-slate-950/60 flex items-center justify-center text-cyan-300"><i data-lucide="image" class="w-8 h-8"></i></div>`;
        const estado = Number(asset.activo) === 1
            ? '<span class="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold text-emerald-200">ACTIVO</span>'
            : '<span class="rounded-full border border-slate-700 bg-slate-900 px-2 py-1 text-[10px] text-slate-400">HISTÓRICO</span>';
        return `<article class="rounded-2xl border border-slate-800 bg-slate-950/55 p-3 space-y-3">
            ${preview}
            <div class="flex items-start justify-between gap-2">
                <div class="min-w-0"><h4 class="text-sm font-semibold text-white">${escapeHtml(assetLabels[asset.tipo] || asset.tipo)}</h4><p class="mt-1 truncate text-xs text-slate-400" title="${escapeHtml(asset.nombre_original || asset.nombre_archivo)}">${escapeHtml(asset.nombre_original || asset.nombre_archivo)}</p><p class="mt-1 text-[11px] text-slate-500">${formatBytes(asset.tamano_bytes)} · ${asset.ancho && asset.alto ? `${asset.ancho}×${asset.alto}px · ` : ''}${escapeHtml(asset.created_at || '')}</p></div>
                ${estado}
            </div>
            <div class="flex flex-wrap gap-2">
                ${asset.scope === 'GLOBAL' ? `<a href="${escapeHtml(resolveAssetUrl(asset.url))}" target="_blank" rel="noopener" class="pi-alpha41-btn-secondary"><i data-lucide="eye" class="w-4 h-4"></i> Ver archivo</a>` : `<button type="button" onclick="descargarArchivoInstitucional('/api/identidad-visual/${Number(asset.id)}/descargar')" class="pi-alpha41-btn-secondary"><i data-lucide="download" class="w-4 h-4"></i> Descargar</button>`}
                ${asset.scope === 'GLOBAL' || Number(asset.activo) === 1 ? '' : `<button type="button" onclick="activarArchivoIdentidadVisual(${Number(asset.id)})" class="pi-alpha41-btn-secondary"><i data-lucide="rotate-ccw" class="w-4 h-4"></i> Restaurar</button>`}
            </div>
        </article>`;
    }

    async function cargarCatalogoIdentidadVisual(silent = true) {
        const grid = qs('ci-assets-grid');
        if (!grid) return;
        try {
            const scope = esAmbitoGlobal() ? 'GLOBAL' : 'FUNDACION';
            const data = await fetchJson(`/api/identidad-visual?scope=${scope}`);
            const assets = data.archivos || [];
            grid.innerHTML = assets.length ? assets.map(renderAssetCard).join('') : '<div class="md:col-span-2 rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">Aún no hay archivos cargados. Sube un logo o favicon para crear el historial.</div>';
            if (typeof lucide !== 'undefined') lucide.createIcons();
            if (!silent) mostrar('ci-message', 'Catálogo de identidad visual actualizado.', 'success');
        } catch (error) {
            grid.innerHTML = `<div class="md:col-span-2 rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-300">${escapeHtml(error.message || 'No se pudo cargar el catálogo.')}</div>`;
        }
    }

    async function activarArchivoIdentidadVisual(id) {
        try {
            const data = await fetchJson(`/api/identidad-visual/${Number(id)}/activar`, { method: 'POST' });
            aplicarIdentidadInstitucional(data.configuracion || {});
            await cargarIdentidadEfectiva(true);
            mostrar('ci-message', data.message || 'Archivo restaurado.', 'success');
            await cargarCatalogoIdentidadVisual(true);
        } catch (error) {
            mostrar('ci-message', error.message || 'No se pudo restaurar el archivo.', 'error');
        }
    }


    function bindGeneratorPreview() {
        const input = qs('ci-generator-file');
        const preview = qs('ci-generator-preview');
        if (!input || input.dataset.previewBound) return;
        input.addEventListener('change', () => {
            const file = input.files?.[0];
            if (!file || !preview) return;
            const url = URL.createObjectURL(file);
            preview.src = url; preview.classList.remove('hidden');
            preview.onload = () => URL.revokeObjectURL(url);
        });
        input.dataset.previewBound = '1';
    }

    async function generarRecursosIdentidad(event) {
        event?.preventDefault();
        const input = qs('ci-generator-file');
        const file = input?.files?.[0];
        if (!file) { mostrar('ci-message', 'Selecciona una imagen original.', 'error'); return; }
        const form = new FormData();
        form.append('file', file);
        form.append('kind', qs('ci-generator-kind')?.value || 'principal');
        form.append('remove_white', qs('ci-generator-remove-white')?.checked ? '1' : '0');
        try {
            mostrar('ci-message', 'Generando versiones. Esto puede tardar unos segundos…', 'info');
            const data = await fetchJson('/api/identidad-visual/generar', { method: 'POST', body: form });
            const actions = qs('ci-generator-actions');
            const download = qs('ci-generator-download');
            const apply = qs('ci-generator-apply');
            if (download) {
                download.removeAttribute('href');
                download.onclick = (event) => {
                    event.preventDefault();
                    descargarArchivoInstitucional(data.zip_url);
                };
            }
            if (apply) apply.dataset.loteId = data.lote_id || '';
            actions?.classList.remove('hidden');
            const applied = await fetchJson(`/api/identidad-visual/lote/${encodeURIComponent(data.lote_id)}/aplicar`, { method: 'POST' });
            aplicarIdentidadInstitucional(applied.configuracion || {});
            await cargarIdentidadEfectiva(true);
            mostrar('ci-message', `${data.message || 'Recursos generados.'} Recursos activados en toda la plataforma.${data.warning ? ' ' + data.warning : ''}`, data.warning ? 'warning' : 'success');
            await cargarCatalogoIdentidadVisual(true);
            if (typeof lucide !== 'undefined') lucide.createIcons();
        } catch (error) { mostrar('ci-message', error.message || 'No fue posible generar los recursos.', 'error'); }
    }

    async function aplicarLoteIdentidad() {
        const id = qs('ci-generator-apply')?.dataset.loteId;
        if (!id) return;
        try {
            const data = await fetchJson(`/api/identidad-visual/lote/${encodeURIComponent(id)}/aplicar`, { method: 'POST' });
            aplicarIdentidadInstitucional(data.configuracion || {});
            await cargarIdentidadEfectiva(true);
            mostrar('ci-message', data.message || 'Recursos aplicados.', 'success');
            await cargarCatalogoIdentidadVisual(true);
        } catch (error) { mostrar('ci-message', error.message || 'No fue posible aplicar los recursos.', 'error'); }
    }

    function bindConfigForms() {
        bindGeneratorPreview();
        restaurarAmbitoSeleccionado();
        const generator = qs('ci-generator-form');
        if (generator && !generator.dataset.bound) { generator.addEventListener('submit', generarRecursosIdentidad); generator.dataset.bound = '1'; }
        const applyGenerated = qs('ci-generator-apply');
        if (applyGenerated && !applyGenerated.dataset.bound) { applyGenerated.addEventListener('click', aplicarLoteIdentidad); applyGenerated.dataset.bound = '1'; }
        const form = qs('ci-form');
        const scope = qs('ci-scope');
        if (scope && !scope.dataset.bound) {
            scope.addEventListener('change', async () => {
                try { sessionStorage.setItem(IDENTITY_SCOPE_KEY, scope.value); } catch (_) {}
                actualizarAvisoAmbito();
                await cargarConfiguracionInstitucional(true);
                await cargarCatalogoIdentidadVisual(true);
            });
            scope.dataset.bound = '1';
            actualizarAvisoAmbito();
        }
        if (form && !form.dataset.bound) {
            form.addEventListener('submit', (event) => guardarConfiguracionInstitucional(event, false));
            form.dataset.bound = '1';
        }
        const admin = qs('ci-admin-form');
        if (admin && !admin.dataset.bound) {
            admin.addEventListener('submit', (event) => guardarConfiguracionInstitucional(event, true));
            admin.dataset.bound = '1';
        }
        const logo = qs('ci-logo-form');
        if (logo && !logo.dataset.bound) {
            logo.addEventListener('submit', (event) => subirArchivoConfiguracion(event, 'logo'));
            logo.dataset.bound = '1';
        }
        const foto = qs('ci-foto-form');
        if (foto && !foto.dataset.bound) {
            foto.addEventListener('submit', (event) => subirArchivoConfiguracion(event, 'foto'));
            foto.dataset.bound = '1';
        }
        const favicon = qs('ci-favicon-form');
        if (favicon && !favicon.dataset.bound) {
            favicon.addEventListener('submit', (event) => subirArchivoConfiguracion(event, 'favicon'));
            favicon.dataset.bound = '1';
        }
    }

    async function configInstitucionalInit() {
        bindConfigForms();
        await cargarConfiguracionInstitucional(true);
        await cargarCatalogoIdentidadVisual(true);
    }

    function renderManualCard(manual, vigente = false) {
        if (!manual) return '<div class="text-sm text-slate-500">No hay manual registrado.</div>';
        const estadoClass = manual.estado === 'vigente' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' : 'border-slate-700 bg-slate-900/60 text-slate-300';
        const secciones = (manual.secciones || []).slice(0, 9).map((s) => `<span class="pi-alpha41-section-pill">${escapeHtml(s.numero || '')} ${escapeHtml(s.titulo || '')}</span>`).join('');
        const acciones = vigente ? '' : `<button onclick="manualOperativoMarcarVigente(${Number(manual.id)})" class="pi-alpha41-btn-secondary mt-3"><i data-lucide="check-circle" class="w-4 h-4"></i> Marcar vigente</button>`;
        return `<div class="mo-row">
            <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                <div>
                    <h4 class="font-semibold text-white">${escapeHtml(manual.nombre || 'Manual Operativo')}</h4>
                    <p class="mt-1 text-xs text-slate-400">Código ${escapeHtml(manual.codigo || '')} · Versión ${escapeHtml(manual.version || '')} · Fecha ${escapeHtml(manual.fecha_documento || '')} · ${manual.total_paginas || '--'} páginas</p>
                    <span class="pi-alpha41-badge mt-3 ${estadoClass}">${escapeHtml(manual.estado || 'borrador')}</span>
                </div>
                <button type="button" onclick="descargarArchivoInstitucional('/api/manual-operativo/${Number(manual.id)}/descargar')" class="pi-alpha41-btn-secondary"><i data-lucide="download" class="w-4 h-4"></i> Descargar</button>
            </div>
            ${secciones ? `<div class="mt-4">${secciones}</div>` : ''}
            ${acciones}
        </div>`;
    }

    async function manualOperativoCargarDatos(silent = true) {
        try {
            const [lista, vigente] = await Promise.all([
                fetchJson('/api/manual-operativo'),
                fetchJson('/api/manual-operativo/vigente')
            ]);
            const manuales = lista.manuales || [];
            const vigenteManual = vigente.manual || null;
            const vigenteCard = qs('mo-vigente-card');
            if (vigenteCard) vigenteCard.innerHTML = vigenteManual ? renderManualCard(vigenteManual, true) : 'Aún no hay manual vigente cargado.';
            setText('mo-vigente-badge', vigenteManual ? `Vigente: ${vigenteManual.codigo || ''} v${vigenteManual.version || ''}` : 'Sin manual vigente');
            const list = qs('mo-list');
            if (list) {
                list.innerHTML = manuales.length
                    ? manuales.map((manual) => renderManualCard(manual, manual.estado === 'vigente')).join('')
                    : '<div class="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">No hay manuales cargados todavía.</div>';
            }
            manualLoaded = true;
            if (!silent) mostrar('mo-message', 'Listado de manuales actualizado.', 'success');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        } catch (error) {
            mostrar('mo-message', error.message || 'No se pudo cargar el módulo de manual operativo.', 'error');
        }
    }

    async function subirManualOperativo(event) {
        event?.preventDefault();
        limpiarMensaje('mo-message');
        const file = qs('mo-file')?.files?.[0];
        if (!file) {
            mostrar('mo-message', 'Selecciona el PDF del manual operativo.', 'error');
            return;
        }
        const form = new FormData();
        form.append('file', file);
        form.append('nombre', qs('mo-nombre')?.value || 'Manual Operativo');
        form.append('codigo', qs('mo-codigo')?.value || 'MT3.PP');
        form.append('version', qs('mo-version')?.value || '1');
        form.append('fecha_documento', qs('mo-fecha')?.value || '');
        form.append('estado', qs('mo-estado')?.value || 'borrador');
        form.append('observacion', qs('mo-observacion')?.value || '');
        try {
            const data = await fetchJson('/api/manual-operativo/cargar', { method: 'POST', body: form });
            qs('mo-file').value = '';
            mostrar('mo-message', data.message || 'Manual cargado.', 'success');
            await manualOperativoCargarDatos(true);
        } catch (error) {
            mostrar('mo-message', error.message || 'No se pudo cargar el manual.', 'error');
        }
    }

    async function manualOperativoMarcarVigente(id) {
        try {
            const data = await fetchJson(`/api/manual-operativo/${Number(id)}/vigente`, { method: 'POST' });
            mostrar('mo-message', data.message || 'Manual vigente actualizado.', 'success');
            await manualOperativoCargarDatos(true);
        } catch (error) {
            mostrar('mo-message', error.message || 'No se pudo marcar el manual como vigente.', 'error');
        }
    }

    function bindManualForms() {
        const form = qs('mo-upload-form');
        if (form && !form.dataset.bound) {
            form.addEventListener('submit', subirManualOperativo);
            form.dataset.bound = '1';
        }
    }

    async function manualOperativoInit() {
        bindManualForms();
        await manualOperativoCargarDatos(true);
    }

    function initLigero() {
        // Vincula siempre los formularios, incluso si la sección se abre desde
        // Accesibilidad o mediante una URL restaurada antes de navegar por el menú.
        bindConfigForms();
        // Solo consulta datos livianos de configuración para pintar identidad.
        // No carga manuales ni PDFs en memoria al iniciar.
        if (token()) cargarIdentidadEfectiva(true);
        else cargarIdentidadPublica(true);
    }

    window.descargarArchivoInstitucional = descargarArchivoInstitucional;
    window.aplicarIdentidadInstitucional = aplicarIdentidadInstitucional;
    window.cargarConfiguracionInstitucional = cargarConfiguracionInstitucional;
    window.cargarIdentidadPublica = cargarIdentidadPublica;
    window.cargarIdentidadEfectiva = cargarIdentidadEfectiva;
    window.limpiarIdentidadInstitucional = limpiarIdentidadInstitucional;
    window.obtenerIdentidadInstitucionalActual = () => ({ ...(configuracionActual || {}) });
    window.configInstitucionalInit = configInstitucionalInit;
    window.cargarCatalogoIdentidadVisual = cargarCatalogoIdentidadVisual;
    window.activarArchivoIdentidadVisual = activarArchivoIdentidadVisual;
    window.manualOperativoInit = manualOperativoInit;
    window.manualOperativoCargarDatos = manualOperativoCargarDatos;
    window.manualOperativoMarcarVigente = manualOperativoMarcarVigente;

    document.addEventListener('DOMContentLoaded', () => {
        initLigero();
    });
})();
