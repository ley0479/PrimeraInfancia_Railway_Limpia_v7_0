(function () {
    const api = () => `${window.backendUrl || window.getBackendUrl?.() || window.getConfiguredBackendUrl?.() || window.location.origin}/api/base-maestra`;
    const universalApi = () => `${window.backendUrl || window.getBackendUrl?.() || window.getConfiguredBackendUrl?.() || window.location.origin}/api/importaciones`;
    const state = { initialized: false, dashboard: null, universalImportId: null, universalResult: null, talentTeams: [] };

    function el(id) { return document.getElementById(id); }

    function esc(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function badge(text) {
        const t = String(text || '').toUpperCase();
        let cls = 'bm-badge-info';
        if (['ACTIVA', 'VALIDADO', 'PUBLICADA', 'VERDE'].some(k => t.includes(k))) cls = 'bm-badge-ok';
        if (['ADVERTENCIA', 'AMARILLO', 'BORRADOR', 'CARGADO'].some(k => t.includes(k))) cls = 'bm-badge-warn';
        if (['CRITICA', 'CRÍTICA', 'ROJO', 'RECHAZADO', 'ERROR'].some(k => t.includes(k))) cls = 'bm-badge-danger';
        return `<span class="bm-badge ${cls}">${esc(text || '—')}</span>`;
    }

    function setText(id, value) {
        const node = el(id);
        if (node) node.textContent = value ?? '0';
    }

    function mensaje(texto, tipo = 'info') {
        const box = el('bm-alerta');
        if (!box) return;
        const styles = {
            success: 'bg-emerald-500/10 text-emerald-200 border border-emerald-500/20',
            error: 'bg-rose-500/10 text-rose-200 border border-rose-500/20',
            warning: 'bg-amber-500/10 text-amber-200 border border-amber-500/20',
            info: 'bg-cyan-500/10 text-cyan-200 border border-cyan-500/20'
        };
        box.className = `rounded-2xl px-4 py-3 text-sm ${styles[tipo] || styles.info}`;
        box.textContent = texto;
        box.classList.remove('hidden');
    }


    function renderResumenCargaFuente(data) {
        const box = el('bm-carga-resumen-unidades');
        if (!box) return;
        const resumen = data?.resumen_unidades || {};
        const unidades = resumen.unidades_detectadas || data?.unidades_detectadas || [];
        const alertas = resumen.alertas || data?.alertas_unidades || [];
        const nombresFuente = { cuentame: 'Base Cuéntame / Niños', talento_humano: 'Talento Humano', salud_nutricion: 'Salud y Nutrición' };
        const tipoFuente = data?.tipo_fuente || el('bm-tipo-fuente')?.value || 'cuentame';
        if (!resumen || !Object.keys(resumen).length) {
            box.classList.add('hidden');
            box.innerHTML = '';
            return;
        }
        const preview = unidades.slice(0, 40).map(u => `
            <tr class="hover:bg-slate-900/60">
                <td class="px-3 py-2 text-slate-200">${esc(u.unidad || u.unidad_normalizada || 'SIN UNIDAD')}</td>
                <td class="px-3 py-2 text-right text-cyan-200">${esc(u.registros || 0)}</td>
            </tr>
        `).join('');
        const mas = unidades.length > 40 ? `<p class="mt-2 text-xs text-slate-500">Se muestran 40 de ${esc(unidades.length)} unidades detectadas.</p>` : '';
        box.className = 'mt-4 rounded-2xl border border-cyan-500/20 bg-slate-950/80 p-4 text-sm text-slate-300';
        box.innerHTML = `
            <div class="flex flex-col gap-1 mb-3">
                <strong class="text-cyan-200">Resumen de lectura: ${esc(nombresFuente[tipoFuente] || tipoFuente)}</strong>
                <span class="text-xs font-semibold text-cyan-300">Registro independiente · ${esc(String(tipoFuente).toUpperCase())}</span>
                <span class="text-xs text-slate-400">Hoja seleccionada: ${esc(resumen.hoja_seleccionada || '—')} · Unidades detectadas: ${esc(resumen.total_unidades_detectadas ?? unidades.length)} · Registros sin unidad: ${esc(resumen.registros_sin_unidad || 0)}</span>
            </div>
            ${alertas.length ? `<div class="mb-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-amber-200 text-xs">${alertas.map(esc).join('<br>')}</div>` : ''}
            <div class="overflow-auto max-h-72 rounded-xl border border-slate-800">
                <table class="w-full text-xs">
                    <thead class="bg-slate-900 text-slate-400"><tr><th class="px-3 py-2 text-left">Unidad detectada</th><th class="px-3 py-2 text-right">Registros</th></tr></thead>
                    <tbody>${preview || '<tr><td colspan="2" class="px-3 py-4 text-center text-slate-500">No se detectaron unidades.</td></tr>'}</tbody>
                </table>
            </div>
            ${mas}
        `;
        box.classList.remove('hidden');
    }

    async function fetchJson(url, options = {}) {
        const res = await fetch(url, options);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || 'Error consultando Base Maestra');
        return data;
    }

    async function download(url, filenameFallback) {
        const res = await fetch(url);
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.error || 'No se pudo descargar el archivo.');
        }
        const blob = await res.blob();
        const disposition = res.headers.get('Content-Disposition') || '';
        const match = disposition.match(/filename="?([^";]+)"?/i);
        const filename = match?.[1] || filenameFallback || 'base_maestra.xlsx';
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        setTimeout(() => {
            URL.revokeObjectURL(link.href);
            link.remove();
        }, 500);
    }

    function renderCargas(cargas) {
        const tbody = el('bm-cargas-list');
        if (!tbody) return;
        if (!cargas || !cargas.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="px-4 py-8 text-center text-slate-500">Sin cargas.</td></tr>';
            return;
        }
        const nombresFuente = { cuentame: 'Cuéntame', talento_humano: 'Talento Humano', salud_nutricion: 'Salud y Nutrición' };
        tbody.innerHTML = cargas.map(c => `
            <tr class="hover:bg-slate-900/60">
                <td class="px-4 py-3 text-slate-300">${esc(c.id)}</td>
                <td class="px-4 py-3"><div class="font-medium text-slate-200">${esc(nombresFuente[c.tipo_fuente] || c.tipo_fuente)}</div><div class="text-[10px] uppercase tracking-wider text-slate-500">${esc(c.tipo_fuente)}</div></td>
                <td class="px-4 py-3">${esc(c.total_registros || 0)}</td>
                <td class="px-4 py-3">${badge(c.estado)}</td>
                <td class="px-4 py-3">
                    <button onclick="baseMaestraValidarCarga(${Number(c.id)})" class="rounded-lg border border-amber-500/40 px-3 py-1 text-xs text-amber-200 hover:bg-amber-500/10">Validar</button>
                </td>
            </tr>
        `).join('');
    }

    function renderResumenFuentes(fuentes) {
        const box = el('bm-resumen-fuentes');
        if (!box) return;
        box.innerHTML = (fuentes || []).map(fuente => {
            const ultima = fuente.ultima_carga || {};
            return `<div class="rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
                <div class="flex items-start justify-between gap-3">
                    <div><div class="font-semibold text-slate-100">${esc(fuente.nombre_fuente)}</div><div class="mt-1 text-[10px] uppercase tracking-wider text-cyan-300">${esc(fuente.identificador)}</div></div>
                    ${badge(fuente.estado)}
                </div>
                <div class="mt-3 text-2xl font-semibold text-white">${esc(fuente.total_registros || 0)}</div>
                <div class="text-xs text-slate-400">registros de la última carga vigente</div>
                <div class="mt-1 text-xs text-slate-500">Historial conservado: ${esc(fuente.total_cargas || 0)} carga(s), sin sumarlas al total.</div>
                <div class="mt-2 text-xs text-slate-500">Última carga: ${esc(ultima.nombre_archivo_original || 'Sin archivo cargado')} ${ultima.id ? `· #${esc(ultima.id)}` : ''}</div>
            </div>`;
        }).join('');
    }

    function renderResumenUnidadesFuentes(resumen) {
        const box = el('bm-carga-resumen-unidades');
        if (!box) return;
        const unidades = resumen?.unidades || [];
        const cargas = resumen?.cargas_fuente || {};
        const filas = unidades.map(item => `<tr class="cursor-pointer hover:bg-cyan-500/10" title="Doble clic para descargar el Excel de esta unidad" ondblclick="baseMaestraDescargarUnidad(decodeURIComponent('${encodeURIComponent(item.unidad)}'))">
            <td class="px-3 py-2 text-slate-200">${esc(item.unidad)}</td>
            <td class="px-3 py-2 text-right text-cyan-200">${esc(item.cuentame || 0)}</td>
            <td class="px-3 py-2 text-right text-violet-200">${esc(item.talento_humano || 0)}</td>
            <td class="px-3 py-2 text-right text-emerald-200">${esc(item.salud_nutricion || 0)}</td>
        </tr>`).join('');
        box.className = 'mt-4 rounded-2xl border border-cyan-500/20 bg-slate-950/80 p-4 text-sm text-slate-300';
        box.innerHTML = `<div class="mb-3 flex flex-col gap-1">
            <strong class="text-cyan-200">Usuarios detectados por unidad y por fuente</strong>
            <span class="text-xs font-semibold text-emerald-300">Haz doble clic sobre una unidad para descargar su Excel detallado.</span>
            <span class="text-xs text-slate-400">Cada persona se cuenta una sola vez por documento dentro de su unidad. Cargas usadas: Cuéntame #${esc(cargas.cuentame || '—')} · Talento Humano #${esc(cargas.talento_humano || '—')} · Salud y Nutrición #${esc(cargas.salud_nutricion || '—')}.</span>
        </div>
        <div class="overflow-auto max-h-80 rounded-xl border border-slate-800"><table class="w-full min-w-[650px] text-xs">
            <thead class="sticky top-0 bg-slate-900 text-slate-300"><tr><th class="px-3 py-2 text-left">Unidad de atención</th><th class="px-3 py-2 text-right">Usuarios Cuéntame</th><th class="px-3 py-2 text-right">Talento Humano</th><th class="px-3 py-2 text-right">Salud y Nutrición</th></tr></thead>
            <tbody>${filas || '<tr><td colspan="4" class="px-3 py-4 text-center text-slate-500">Aún no hay registros por unidad.</td></tr>'}</tbody>
        </table></div>`;
        box.classList.remove('hidden');
    }

    function renderEstructuraTalento(data) {
        const box = el('bm-estructura-talento');
        if (!box) return;
        const equipos = data?.equipos || [];
        state.talentTeams = equipos;
        box.innerHTML = equipos.map((equipo, equipoIndex) => {
            const cargos = Object.entries(equipo.cargos || {}).sort((a, b) => a[0].localeCompare(b[0]));
            const resumenCargos = `<button type="button" onclick="baseMaestraFiltrarEquipo(${equipoIndex}, '')" class="rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-1 text-xs text-cyan-200">Ver todos: ${esc(equipo.total_personas)}</button>` + cargos.map(([cargo, total]) => `<button type="button" onclick="baseMaestraFiltrarEquipo(${equipoIndex}, decodeURIComponent('${encodeURIComponent(cargo)}'))" class="rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-1 text-xs text-violet-200 hover:bg-violet-500/20">${esc(cargo)}: ${esc(total)}</button>`).join('');
            const integrantes = (equipo.integrantes || []).map(persona => `<tr data-talento-rol="${esc(persona.rol_normalizado)}"><td class="px-3 py-2 text-slate-200">${esc(persona.nombre)}</td><td class="px-3 py-2">${esc(persona.cargo || persona.rol_normalizado)}</td><td class="px-3 py-2">${esc(persona.unidad_servicio || '—')}</td><td class="px-3 py-2">${esc(persona.telefono || persona.correo || '—')}</td><td class="px-3 py-2 text-slate-500">${esc(persona.origen_asignacion || '—')}</td></tr>`).join('');
            return `<details data-talento-equipo="${equipoIndex}" data-filtro-rol="" class="rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
                <summary class="cursor-pointer list-none"><div class="flex flex-wrap items-center justify-between gap-3"><div><div class="font-semibold text-slate-100">${esc(equipo.coordinador)}</div><div class="text-xs text-slate-500">${esc(equipo.total_personas)} integrantes</div></div><div class="flex flex-wrap gap-1">${resumenCargos}</div></div></summary>
                <div class="mt-3 flex flex-wrap items-center justify-between gap-2"><span data-talento-resultado class="text-xs font-semibold text-emerald-300">Mostrando todo el equipo</span><button type="button" onclick="baseMaestraImprimirEquipo(${equipoIndex})" class="bm-btn bm-btn-secondary text-xs">Imprimir selección</button></div>
                <div class="mt-4 overflow-auto"><table class="w-full min-w-[760px] text-xs"><thead class="bg-slate-900 text-slate-300"><tr><th class="px-3 py-2 text-left">Nombre</th><th class="px-3 py-2 text-left">Cargo</th><th class="px-3 py-2 text-left">Unidad</th><th class="px-3 py-2 text-left">Contacto</th><th class="px-3 py-2 text-left">Asignación</th></tr></thead><tbody>${integrantes}</tbody></table></div>
            </details>`;
        }).join('') || '<div class="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">No hay personal de Talento Humano mapeado todavía.</div>';
        const estado = el('bm-estructura-talento-estado');
        if (estado) estado.textContent = `Carga #${data?.carga_id || '—'} · ${data?.total_coordinadores || 0} coordinadores · ${data?.total_personas || 0} personas únicas · ${data?.asignados_por_unidad || 0} integrantes vinculados por unidad · ${data?.duplicados_omitidos || 0} duplicados omitidos · ${(data?.unidades_ambiguas || []).length} unidades requieren revisión`;
    }

    function baseMaestraFiltrarEquipo(equipoIndex, rol) {
        const panel = document.querySelector(`[data-talento-equipo="${Number(equipoIndex)}"]`);
        if (!panel) return;
        panel.open = true;
        panel.dataset.filtroRol = rol || '';
        let visibles = 0;
        panel.querySelectorAll('[data-talento-rol]').forEach(fila => {
            const mostrar = !rol || fila.dataset.talentoRol === rol;
            fila.classList.toggle('hidden', !mostrar);
            if (mostrar) visibles += 1;
        });
        const resultado = panel.querySelector('[data-talento-resultado]');
        if (resultado) resultado.textContent = rol ? `${rol}: ${visibles} personas` : `Mostrando todo el equipo: ${visibles} personas`;
    }

    function baseMaestraImprimirEquipo(equipoIndex) {
        const equipo = state.talentTeams?.[Number(equipoIndex)];
        const panel = document.querySelector(`[data-talento-equipo="${Number(equipoIndex)}"]`);
        if (!equipo || !panel) return;
        const rol = panel.dataset.filtroRol || '';
        const personas = (equipo.integrantes || []).filter(persona => !rol || persona.rol_normalizado === rol);
        const filas = personas.map(persona => `<tr><td>${esc(persona.nombre)}</td><td>${esc(persona.cargo || persona.rol_normalizado)}</td><td>${esc(persona.unidad_servicio || '—')}</td><td>${esc(persona.telefono || persona.correo || '—')}</td><td>${esc(persona.origen_asignacion || '—')}</td></tr>`).join('');
        const ventana = window.open('', '_blank', 'width=1000,height=750');
        if (!ventana) return mensaje('El navegador bloqueó la ventana de impresión.', 'warning');
        ventana.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Equipo ${esc(equipo.coordinador)}</title><style>body{font-family:Arial,sans-serif;margin:28px;color:#111}h1{font-size:20px;margin-bottom:4px}p{margin:4px 0 18px;color:#444}table{width:100%;border-collapse:collapse;font-size:12px}th,td{border:1px solid #bbb;padding:7px;text-align:left}th{background:#eee}@media print{button{display:none}}</style></head><body><h1>${esc(equipo.coordinador)}</h1><p>${rol ? `Cargo seleccionado: ${esc(rol)}` : 'Equipo completo'} · ${personas.length} personas</p><table><thead><tr><th>Nombre</th><th>Cargo</th><th>Unidad</th><th>Contacto</th><th>Asignación</th></tr></thead><tbody>${filas}</tbody></table><script>window.onload=()=>window.print()<\/script></body></html>`);
        ventana.document.close();
    }

    function renderBorradores(borradores) {
        const select = el('bm-version-borrador');
        if (!select) return;
        const current = select.value;
        select.innerHTML = '<option value="">Selecciona versión borrador</option>' + (borradores || []).map(v => {
            let resumen = {};
            try { resumen = JSON.parse(v.resumen_json || '{}'); } catch (_) {}
            return `<option value="${esc(v.id)}">v${esc(v.version_numero)} · ${esc(v.estado)} · ${esc(resumen.total_ninos || 0)} niños · ${esc(v.fecha_creacion || '')}</option>`;
        }).join('');
        if (current) select.value = current;
    }

    function renderInconsistencias(items) {
        const tbody = el('bm-inconsistencias-list');
        if (!tbody) return;
        if (!items || !items.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="px-4 py-8 text-center text-slate-500">Sin inconsistencias.</td></tr>';
            return;
        }
        tbody.innerHTML = items.slice(0, 80).map(i => `
            <tr class="hover:bg-slate-900/60">
                <td class="px-4 py-3">${badge(i.severidad)}</td>
                <td class="px-4 py-3 text-slate-300">${esc(i.tipo)}</td>
                <td class="px-4 py-3">${esc(i.documento || '—')}</td>
                <td class="px-4 py-3">${esc(i.descripcion)}</td>
            </tr>
        `).join('');
    }

    function renderMovimientos(items) {
        const tbody = el('bm-movimientos-list');
        if (!tbody) return;
        if (!items || !items.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="px-4 py-8 text-center text-slate-500">Sin movimientos.</td></tr>';
            return;
        }
        tbody.innerHTML = items.slice(0, 80).map(i => `
            <tr class="hover:bg-slate-900/60">
                <td class="px-4 py-3">${badge(i.tipo_movimiento)}</td>
                <td class="px-4 py-3">${esc(i.documento || '—')}</td>
                <td class="px-4 py-3 text-slate-300">${esc(i.nombre || '—')}</td>
                <td class="px-4 py-3">${esc(i.detalle || '')}</td>
            </tr>
        `).join('');
    }

    function renderHistorial(items) {
        const tbody = el('bm-historial-list');
        if (!tbody) return;
        if (!items || !items.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="px-4 py-8 text-center text-slate-500">Sin historial.</td></tr>';
            return;
        }
        tbody.innerHTML = items.slice(0, 80).map(i => `
            <tr class="hover:bg-slate-900/60">
                <td class="px-4 py-3">${esc(i.documento || '—')}</td>
                <td class="px-4 py-3 text-slate-300">${esc(i.campo)}</td>
                <td class="px-4 py-3 text-rose-200">${esc(i.valor_anterior || '—')}</td>
                <td class="px-4 py-3 text-emerald-200">${esc(i.valor_nuevo || '—')}</td>
            </tr>
        `).join('');
    }

    function renderResumen(data) {
        const resumen = data?.resumen || {};
        const version = data?.version_activa;
        setText('bm-version', version ? `v${version.version_numero}` : 'Sin publicar');
        setText('bm-total-ninos', resumen.total_ninos || 0);
        setText('bm-total-unidades', resumen.total_unidades || 0);
        setText('bm-total-coordinadores', resumen.total_coordinadores || 0);
        setText('bm-total-alertas', resumen.total_alertas || 0);
        setText('bm-calidad', `${resumen.calidad_porcentaje || 0}%`);
        const box = el('bm-resumen-publicacion');
        if (box) {
            if (version) {
                const alimentacion = data?.alimentacion_modulos || [];
                const estados = alimentacion.length
                    ? alimentacion.map(item => {
                        const ok = item.estado === 'COMPLETADA';
                        const color = ok ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100' : 'border-rose-500/30 bg-rose-500/10 text-rose-100';
                        const nombre = String(item.modulo || '').replaceAll('_', ' ');
                        const detalle = item.error ? ` · ${esc(item.error)}` : '';
                        return `<div class="rounded-xl border ${color} p-3"><div class="font-semibold">${esc(nombre)}</div><div class="mt-1 text-xs">${esc(item.estado)} · ${esc(item.total_registros || 0)} registros${detalle}</div></div>`;
                    }).join('')
                    : '<div class="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-amber-100"><strong>Propagación pendiente de registrar</strong><div class="mt-1 text-xs">Vuelve a publicar una versión validada para aplicar y verificar la alimentación uniforme.</div></div>';
                box.innerHTML = `
                    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                        <div>
                            <div class="text-slate-100 font-semibold">Versión activa v${esc(version.version_numero)} ${badge(version.estado)}</div>
                            <div class="text-xs text-slate-400 mt-1">Publicada: ${esc(version.fecha_publicacion || 'pendiente')} · Usuario: ${esc(version.usuario || 'sistema')}</div>
                        </div>
                        <div class="text-xs text-slate-400">Errores críticos: ${esc(resumen.errores_criticos || 0)} · Advertencias: ${esc(resumen.advertencias || 0)}</div>
                    </div>
                    <div class="mt-4"><div class="mb-2 text-xs font-semibold uppercase tracking-wide text-cyan-200">Alimentación uniforme de módulos</div><div class="grid gap-2 md:grid-cols-2 xl:grid-cols-3">${estados}</div></div>`;
            } else {
                box.textContent = 'Sin versión activa publicada todavía. Puedes consolidar un borrador y publicarlo cuando la validación esté correcta.';
            }
        }
        renderCargas(data?.cargas || []);
        renderResumenFuentes(data?.resumen_fuentes || []);
        renderResumenUnidadesFuentes(data?.resumen_unidades_fuentes || {});
        renderEstructuraTalento(data?.estructura_talento || {});
        renderBorradores(data?.borradores || []);
    }

    async function baseMaestraCargarResumen() {
        try {
            const [dashboard, inconsistencias, movimientos, historial] = await Promise.all([
                fetchJson(`${api()}/resumen`),
                fetchJson(`${api()}/inconsistencias?limit=100`),
                fetchJson(`${api()}/movimientos?limit=100`),
                fetchJson(`${api()}/historial?limit=100`)
            ]);
            state.dashboard = dashboard;
            renderResumen(dashboard);
            renderInconsistencias(inconsistencias.inconsistencias || []);
            renderMovimientos(movimientos.movimientos || []);
            renderHistorial(historial.historial || []);
            if (typeof lucide !== 'undefined') lucide.createIcons();
        } catch (error) {
            mensaje(error.message || 'No se pudo cargar Base Maestra.', 'error');
        }
    }

    async function baseMaestraCargarFuente() {
        const file = el('bm-file')?.files?.[0];
        const tipo = el('bm-tipo-fuente')?.value || 'cuentame';
        if (!file) {
            mensaje('Selecciona primero un archivo para cargar.', 'warning');
            return;
        }
        const fd = new FormData();
        fd.append('file', file);
        fd.append('tipo_fuente', tipo);
        try {
            if (typeof mostrarCargando === 'function') mostrarCargando('Cargando fuente temporal de Base Maestra...');
            const data = await fetchJson(`${api()}/cargar-fuente`, { method: 'POST', body: fd });
            const totalUds = data.total_unidades_detectadas ?? data.resumen_unidades?.total_unidades_detectadas ?? 0;
            const hoja = data.hoja_seleccionada || data.resumen_unidades?.hoja_seleccionada || '—';
            mensaje(`${data.message} Carga #${data.carga_id} · ${data.registros_cargados} registros · ${totalUds} unidades detectadas · hoja: ${hoja}.`, totalUds && totalUds < 30 && tipo === 'cuentame' ? 'warning' : 'success');
            renderResumenCargaFuente(data);
            if (el('bm-file')) el('bm-file').value = '';
            await baseMaestraCargarResumen();
        } catch (error) {
            mensaje(error.message || 'No se pudo cargar la fuente.', 'error');
        } finally {
            if (typeof ocultarCargando === 'function') ocultarCargando();
        }
    }

    function renderUniversal(data) {
        const status = el('bm-universal-status');
        const mappingBox = el('bm-universal-mapping');
        if (!status || !mappingBox) return;
        const inspection = data.inspection || {};
        const units = data.units || {};
        status.className = 'mt-4 rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-3 text-sm text-cyan-100';
        status.innerHTML = `<strong>${esc(data.estado || 'ANALIZADO')}</strong> · Hoja: ${esc(data.selected_table || '—')} · Encabezado fila ${esc(data.preview?.header_row || '—')} · ${esc(data.preview?.rows?.length || 0)} registros de vista · ${esc(units.count || 0)} unidades. ${data.requires_confirmation ? '<span class="text-amber-200">Requiere confirmación.</span>' : '<span class="text-emerald-200">Mapeo de unidad con confianza alta.</span>'}`;
        status.classList.remove('hidden');
        const important = ['regional.nombre', 'municipio.codigo', 'municipio.nombre', 'centro_zonal.nombre', 'unidad.codigo', 'unidad.nombre', 'participante.numero_documento', 'participante.nombre_completo'];
        const columns = data.preview?.columns || [];
        const rows = important.map(field => {
            const decision = data.mapping?.[field] || {};
            const selected = decision.selected;
            const rejected = (decision.rejected || []).map(item => `${item.original_header}: ${item.reasons?.join(', ')}`).join(' · ');
            const options = ['<option value="">No existe en esta base</option>', ...columns.map(column => `<option value="${esc(column.id)}" ${column.id === selected?.column_id ? 'selected' : ''}>${esc(column.original_header || column.flattened_header)}</option>`)].join('');
            return `<tr class="border-b border-slate-800"><td class="px-3 py-2 text-slate-200">${esc(field)}</td><td class="px-3 py-2"><select class="bm-input text-xs" data-universal-field="${esc(field)}">${options}</select></td><td class="px-3 py-2">${esc(selected?.score ?? '—')} · ${badge(selected?.confidence || decision.status)}</td><td class="px-3 py-2 text-xs text-slate-500">${esc((selected?.reasons || []).join(', '))}${rejected ? `<br>Descartadas: ${esc(rejected)}` : ''}</td></tr>`;
        }).join('');
        mappingBox.innerHTML = `<table class="w-full min-w-[760px] text-sm"><thead class="bg-slate-900 text-slate-300"><tr><th class="px-3 py-2 text-left">Campo canónico</th><th class="px-3 py-2 text-left">Columna propuesta</th><th class="px-3 py-2 text-left">Confianza</th><th class="px-3 py-2 text-left">Explicación</th></tr></thead><tbody>${rows}</tbody></table><div class="mt-3 flex flex-wrap gap-2"><button onclick="baseMaestraConfirmarMapeoUniversal()" class="bm-btn bm-btn-warning">Guardar y validar mapeo</button><button onclick="baseMaestraImportarUniversal()" class="bm-btn bm-btn-success">Importar a staging de Base Maestra</button></div>`;
        mappingBox.classList.remove('hidden');
    }

    async function baseMaestraAnalizarUniversal() {
        const file = el('bm-universal-file')?.files?.[0];
        if (!file) return mensaje('Selecciona una fuente para analizar.', 'warning');
        const form = new FormData(); form.append('file', file);
        try {
            if (typeof mostrarCargando === 'function') mostrarCargando('Inspeccionando hojas, encabezados y columnas...');
            const data = await fetchJson(`${universalApi()}/analizar`, { method: 'POST', body: form });
            state.universalImportId = data.importacion_id; state.universalResult = data;
            renderUniversal(data);
            mensaje(`Análisis #${data.importacion_id} terminado. No se escribió en Base Maestra.`, data.requires_confirmation ? 'warning' : 'success');
        } catch (error) {
            if (/404/.test(String(error.message))) mensaje('El Motor Universal está desactivado. Se habilitará al final del despliegue.', 'info');
            else mensaje(error.message || 'No se pudo analizar la fuente.', 'error');
        } finally { if (typeof ocultarCargando === 'function') ocultarCargando(); }
    }

    async function baseMaestraConfirmarMapeoUniversal() {
        if (!state.universalImportId) return mensaje('Analiza primero una fuente.', 'warning');
        const mapping = {};
        document.querySelectorAll('[data-universal-field]').forEach(select => { if (select.value) mapping[select.dataset.universalField] = select.value; });
        try {
            const data = await fetchJson(`${universalApi()}/${state.universalImportId}/mapeo`, {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({mapping})});
            state.universalResult.mapping = data.mapping; state.universalResult.units = data.units; state.universalResult.requires_confirmation = false;
            renderUniversal(state.universalResult);
            const validation = await fetchJson(`${universalApi()}/${state.universalImportId}/validar`, {method:'POST'});
            mensaje(`Mapeo v${data.version} guardado. ${validation.errores?.length || 0} errores y ${validation.advertencias?.length || 0} advertencias.`, validation.errores?.length ? 'warning' : 'success');
        } catch (error) { mensaje(error.message || 'No se pudo confirmar el mapeo.', 'error'); }
    }

    async function baseMaestraImportarUniversal() {
        if (!state.universalImportId) return mensaje('Analiza y confirma primero una fuente.', 'warning');
        if (!confirm('¿Importar los registros validados al staging de Base Maestra? Aún no se publicarán.')) return;
        try {
            const data = await fetchJson(`${universalApi()}/${state.universalImportId}/confirmar`, {method:'POST'});
            mensaje(`${data.registros_importados} registros importados; ${data.registros_omitidos} omitidos. ${data.siguiente_paso}.`, data.registros_omitidos ? 'warning' : 'success');
            await baseMaestraCargarResumen();
        } catch (error) { mensaje(error.message || 'No se pudo importar el staging.', 'error'); }
    }

    async function baseMaestraValidarCarga(cargaId) {
        try {
            if (typeof mostrarCargando === 'function') mostrarCargando('Validando datos de Base Maestra...');
            const data = await fetchJson(`${api()}/validar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ carga_id: Number(cargaId) })
            });
            const r = data.resumen || {};
            mensaje(`Validación #${data.validacion_id}: ${r.semaforo} · ${r.registros_validos}/${r.total_registros} válidos · ${r.errores_criticos} críticos.`, r.errores_criticos ? 'warning' : 'success');
            await baseMaestraCargarResumen();
        } catch (error) {
            mensaje(error.message || 'No se pudo validar.', 'error');
        } finally {
            if (typeof ocultarCargando === 'function') ocultarCargando();
        }
    }

    async function baseMaestraValidarPendientes() {
        try {
            if (typeof mostrarCargando === 'function') mostrarCargando('Validando fuentes pendientes...');
            const data = await fetchJson(`${api()}/validar`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
            mensaje(`Validaciones ejecutadas: ${data.total_validaciones || 0}.`, 'success');
            await baseMaestraCargarResumen();
        } catch (error) {
            mensaje(error.message || 'No se pudieron validar fuentes pendientes.', 'error');
        } finally {
            if (typeof ocultarCargando === 'function') ocultarCargando();
        }
    }

    async function baseMaestraConsolidar() {
        try {
            if (typeof mostrarCargando === 'function') mostrarCargando('Consolidando Base Maestra en borrador...');
            const data = await fetchJson(`${api()}/consolidar`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
            mensaje(`${data.message} Versión borrador #${data.version_id}. ${data.puede_publicar ? 'Lista para publicar.' : 'Requiere corregir críticos.'}`, data.puede_publicar ? 'success' : 'warning');
            await baseMaestraCargarResumen();
            const select = el('bm-version-borrador');
            if (select) select.value = String(data.version_id);
        } catch (error) {
            mensaje(error.message || 'No se pudo consolidar.', 'error');
        } finally {
            if (typeof ocultarCargando === 'function') ocultarCargando();
        }
    }

    async function baseMaestraPublicarSeleccionada() {
        const versionId = Number(el('bm-version-borrador')?.value || 0);
        if (!versionId) {
            mensaje('Selecciona primero una versión borrador para publicar.', 'warning');
            return;
        }
        if (!confirm('¿Publicar esta versión como Base Maestra oficial activa? La versión anterior quedará archivada.')) return;
        try {
            if (typeof mostrarCargando === 'function') mostrarCargando('Publicando Base Maestra activa...');
            const data = await fetchJson(`${api()}/publicar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ version_id: versionId })
            });
            const fallidas = (data.alimentacion_modulos || []).filter(item => item.estado !== 'COMPLETADA');
            mensaje(data.message || 'Base Maestra publicada correctamente.', fallidas.length ? 'warning' : 'success');
            await baseMaestraCargarResumen();
        } catch (error) {
            mensaje(error.message || 'No se pudo publicar.', 'error');
        } finally {
            if (typeof ocultarCargando === 'function') ocultarCargando();
        }
    }

    async function baseMaestraDescargarInconsistencias() {
        try {
            await download(`${api()}/inconsistencias/descargar`, 'BASE_MAESTRA_INCONSISTENCIAS.xlsx');
        } catch (error) {
            mensaje(error.message || 'No se pudo descargar inconsistencias.', 'error');
        }
    }

    async function baseMaestraDescargarUnidad(unidad) {
        try {
            await download(`${api()}/unidad-registros/descargar?unidad=${encodeURIComponent(unidad)}`, `REGISTROS_UNIDAD_${unidad}.xlsx`);
            mensaje(`Excel generado para la unidad ${unidad}.`, 'success');
        } catch (error) {
            mensaje(error.message || 'No se pudo descargar el Excel de la unidad.', 'error');
        }
    }

    function baseMaestraInit() {
        if (!state.initialized) state.initialized = true;
        baseMaestraCargarResumen();
    }

    window.baseMaestraInit = baseMaestraInit;
    window.baseMaestraCargarResumen = baseMaestraCargarResumen;
    window.baseMaestraCargarFuente = baseMaestraCargarFuente;
    window.baseMaestraAnalizarUniversal = baseMaestraAnalizarUniversal;
    window.baseMaestraConfirmarMapeoUniversal = baseMaestraConfirmarMapeoUniversal;
    window.baseMaestraImportarUniversal = baseMaestraImportarUniversal;
    window.baseMaestraValidarCarga = baseMaestraValidarCarga;
    window.baseMaestraValidarPendientes = baseMaestraValidarPendientes;
    window.baseMaestraConsolidar = baseMaestraConsolidar;
    window.baseMaestraPublicarSeleccionada = baseMaestraPublicarSeleccionada;
    window.baseMaestraDescargarInconsistencias = baseMaestraDescargarInconsistencias;
    window.baseMaestraDescargarUnidad = baseMaestraDescargarUnidad;
    window.baseMaestraFiltrarEquipo = baseMaestraFiltrarEquipo;
    window.baseMaestraImprimirEquipo = baseMaestraImprimirEquipo;
})();
