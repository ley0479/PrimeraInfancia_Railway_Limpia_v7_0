/*
Módulo independiente Salud y Nutrición Inteligente.
Depende únicamente de backendUrl y utilidades básicas existentes en app.js.
*/
let snEstado = {
    inicializado: false,
    dashboard: null,
    alertas: [],
    calendario: [],
    integral: { expedientes: [], actividades: [], rutas: [], periodos: [], actas: [] },
    plantillaPendiente: null
};

function snMensaje(texto, tipo = 'success') {
    const box = document.getElementById('sn-message');
    if (!box) return;
    box.className = `rounded-xl px-4 py-3 text-sm ${tipo === 'success' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'}`;
    box.innerText = texto;
    box.classList.remove('hidden');
}

function snInit() {
    if (!snEstado.inicializado) {
        snEstado.inicializado = true;
        snCargarDashboard();
    }
    lucide.createIcons();
}

function snMostrarVista(vista) {
    ['dashboard', 'integral', 'tematicas', 'jornadas', 'mensuales', 'actas', 'rutas', 'importar', 'cruce', 'historial', 'alertas', 'calendario', 'entregables'].forEach((id) => {
        const el = document.getElementById(`sn-view-${id}`);
        if (el) el.classList.toggle('hidden', id !== vista);
    });
    document.querySelectorAll('[data-sn-tab]').forEach((tab) => {
        tab.classList.toggle('active', tab.getAttribute('data-sn-tab') === vista);
    });
    if (vista === 'dashboard') snCargarDashboard();
    if (vista === 'alertas') snCargarAlertas();
    if (vista === 'calendario') snCargarCalendario();
    if (vista === 'integral') snIntegralCargar();
    if (vista === 'tematicas') snTematicasCargar();
    if (vista === 'jornadas') snIntegralCargarActividades();
    if (vista === 'mensuales') snCargarPeriodosMensuales();
    if (vista === 'actas') snCargarActasInstitucionales();
    if (vista === 'rutas') snIntegralCargarRutas();
    if (vista === 'entregables' && typeof snEntregablesInit === 'function') snEntregablesInit();
}

function snBadge(nivel, texto) {
    const n = String(nivel || '').toUpperCase();
    const clase = n === 'ROJO' ? 'sn-badge-rojo' : n === 'AMARILLO' ? 'sn-badge-amarillo' : 'sn-badge-verde';
    return `<span class="sn-badge ${clase}">${escaparHtml(texto || nivel || '')}</span>`;
}

function snRenderDistribucion(contenedorId, data) {
    const cont = document.getElementById(contenedorId);
    if (!cont) return;
    const items = Object.entries(data || {}).sort((a, b) => b[1] - a[1]);
    const total = items.reduce((sum, item) => sum + Number(item[1] || 0), 0);
    if (!items.length) {
        cont.innerHTML = '<p class="text-slate-500">Sin datos.</p>';
        return;
    }
    cont.innerHTML = items.map(([nombre, valor]) => {
        const pct = total ? Math.round((Number(valor) / total) * 100) : 0;
        return `
            <div>
                <div class="mb-1 flex items-center justify-between gap-3">
                    <span class="truncate text-slate-300">${escaparHtml(nombre)}</span>
                    <span class="text-xs text-slate-500">${valor} · ${pct}%</span>
                </div>
                <div class="sn-bar text-cyan-400"><span style="width:${pct}%"></span></div>
            </div>
        `;
    }).join('');
}

function snRenderCasos(rows) {
    const tbody = document.getElementById('sn-dashboard-casos');
    if (!tbody) return;
    const data = Array.isArray(rows) ? rows.slice(0, 120) : [];
    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-slate-500">Sin datos cargados.</td></tr>';
        return;
    }
    tbody.innerHTML = data.map((item) => `
        <tr>
            <td>${escaparHtml(item.unidad || '')}</td>
            <td class="font-medium text-slate-200">${escaparHtml(item.nombre_completo || '')}</td>
            <td>${escaparHtml(item.documento || '')}</td>
            <td>${escaparHtml(item.edad_texto || '')}</td>
            <td>${escaparHtml(item.peso_kg ?? '')}</td>
            <td>${escaparHtml(item.talla_cm ?? '')}</td>
            <td>${snBadge(item.nivel_alerta, item.diagnostico_global || 'Pendiente')}</td>
            <td>${escaparHtml(item.estado_control || '')}</td>
            <td>${escaparHtml(item.proximo_control || '')}</td>
        </tr>
    `).join('');
}

function snCargarDashboard() {
    fetch(`${backendUrl}/api/salud-nutricion/dashboard`)
        .then(manejarRespuestaJson)
        .then((data) => {
            snEstado.dashboard = data;
            document.getElementById('sn-stat-total').innerText = data.total_usuarios || 0;
            document.getElementById('sn-stat-valorados').innerText = data.total_valorados || 0;
            document.getElementById('sn-stat-pendientes').innerText = data.total_pendientes || 0;
            document.getElementById('sn-stat-criticos').innerText = data.casos_criticos || 0;
            document.getElementById('sn-stat-seguimiento').innerText = data.casos_seguimiento || 0;
            document.getElementById('sn-stat-cumplimiento').innerText = `${data.cumplimiento || 0}%`;
            snRenderDistribucion('sn-chart-diagnostico', data.por_diagnostico || {});
            snRenderDistribucion('sn-chart-control', data.por_estado_control || {});
            snRenderCasos(data.ultimos_casos || []);
            lucide.createIcons();
        })
        .catch((error) => snMensaje(error.message || 'No se pudo cargar dashboard nutricional.', 'error'));
}

function snImportarValoraciones() {
    const input = document.getElementById('sn-input-valoraciones');
    const file = input?.files?.[0];
    if (!file) {
        snMensaje('Selecciona un archivo de salud y nutrición.', 'error');
        return;
    }
    const formData = new FormData();
    formData.append('file', file);
    formData.append('usuario', document.getElementById('sn-import-usuario')?.value || 'sistema');
    mostrarCargando('Importando salud y nutrición...');
    fetch(`${backendUrl}/api/salud-nutricion/importar`, { method: 'POST', body: formData })
        .then(manejarRespuestaJson)
        .then((data) => {
            ocultarCargando();
            snMensaje(data.message || 'Importación realizada.', 'success');
            if (input) input.value = '';
            snCargarDashboard();
        })
        .catch((error) => {
            ocultarCargando();
            snMensaje(error.message || 'No se pudo importar.', 'error');
        });
}

function snImportarReferencias() {
    const input = document.getElementById('sn-input-referencias');
    const file = input?.files?.[0];
    if (!file) {
        snMensaje('Selecciona un archivo de referencias OMS/ICBF.', 'error');
        return;
    }
    const formData = new FormData();
    formData.append('file', file);
    mostrarCargando('Importando referencias OMS/ICBF...');
    fetch(`${backendUrl}/api/salud-nutricion/referencias/importar`, { method: 'POST', body: formData })
        .then(manejarRespuestaJson)
        .then((data) => {
            ocultarCargando();
            snMensaje(data.message || 'Referencias importadas.', 'success');
            input.value = '';
        })
        .catch((error) => {
            ocultarCargando();
            snMensaje(error.message || 'No se pudieron importar referencias.', 'error');
        });
}

function snCompararBases() {
    const anterior = document.getElementById('sn-base-anterior')?.files?.[0];
    const actual = document.getElementById('sn-base-actual')?.files?.[0];
    if (!anterior || !actual) {
        snMensaje('Carga base anterior y base actual.', 'error');
        return;
    }
    const formData = new FormData();
    formData.append('base_anterior', anterior);
    formData.append('base_actual', actual);
    mostrarCargando('Comparando bases de datos...');
    fetch(`${backendUrl}/api/salud-nutricion/comparar`, { method: 'POST', body: formData })
        .then(manejarRespuestaJson)
        .then((data) => {
            ocultarCargando();
            snMensaje(data.message || 'Comparación generada.', 'success');
            snRenderComparacion(data);
        })
        .catch((error) => {
            ocultarCargando();
            snMensaje(error.message || 'No se pudo comparar.', 'error');
        });
}

function snRenderComparacion(data) {
    const cont = document.getElementById('sn-comparacion-resultado');
    if (!cont) return;
    const r = data.resumen || {};
    cont.classList.remove('hidden');
    cont.innerHTML = `
        <h3 class="font-semibold mb-3">Resultado de comparación</h3>
        <div class="grid gap-3 md:grid-cols-6 mb-4">
            <div class="sn-card"><p class="text-xs text-slate-500">Anterior</p><p class="text-2xl font-bold">${r.total_anterior || 0}</p></div>
            <div class="sn-card"><p class="text-xs text-slate-500">Actual</p><p class="text-2xl font-bold">${r.total_actual || 0}</p></div>
            <div class="sn-card"><p class="text-xs text-slate-500">Nuevos</p><p class="text-2xl font-bold">${r.nuevos || 0}</p></div>
            <div class="sn-card"><p class="text-xs text-slate-500">Retirados</p><p class="text-2xl font-bold">${r.retirados || 0}</p></div>
            <div class="sn-card"><p class="text-xs text-slate-500">Traslados</p><p class="text-2xl font-bold">${r.trasladados || 0}</p></div>
            <div class="sn-card"><p class="text-xs text-slate-500">Cambios</p><p class="text-2xl font-bold">${r.cambios || 0}</p></div>
        </div>
        <div class="flex flex-wrap gap-2">
            ${data.reporte_excel ? `<button onclick="snDescargarReporte('${escaparHtml(data.reporte_excel)}')" class="rounded-xl bg-emerald-600 hover:bg-emerald-500 px-4 py-2 text-sm font-medium text-white">Descargar Excel</button>` : ''}
            ${data.reporte_pdf ? `<button onclick="snDescargarReporte('${escaparHtml(data.reporte_pdf)}')" class="rounded-xl bg-rose-600 hover:bg-rose-500 px-4 py-2 text-sm font-medium text-white">Descargar PDF</button>` : ''}
        </div>
    `;
}

function snBuscarFicha() {
    const doc = document.getElementById('sn-ficha-documento')?.value?.trim();
    const cont = document.getElementById('sn-ficha-resultado');
    if (!doc) {
        snMensaje('Escribe un documento/NUI.', 'error');
        return;
    }
    fetch(`${backendUrl}/api/salud-nutricion/ficha/${encodeURIComponent(doc)}`)
        .then(manejarRespuestaJson)
        .then((data) => {
            if (!cont) return;
            cont.classList.remove('hidden');
            const b = data.beneficiario || {};
            const historial = data.historial || [];
            cont.innerHTML = `
                <h3 class="font-semibold mb-2">${escaparHtml(b.nombre_completo || '')}</h3>
                <p class="text-sm text-slate-400 mb-4">${escaparHtml(b.documento || '')} · ${escaparHtml(b.unidad || '')} · ${escaparHtml(b.edad_texto || '')}</p>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs sn-table text-slate-400">
                        <thead><tr><th>Fecha</th><th>Peso</th><th>Talla</th><th>IMC</th><th>PB</th><th>Diagnóstico</th><th>Control</th><th>Próximo</th></tr></thead>
                        <tbody>${historial.map((h) => `
                            <tr>
                                <td>${escaparHtml(h.fecha_valoracion || '')}</td>
                                <td>${escaparHtml(h.peso_kg ?? '')}</td>
                                <td>${escaparHtml(h.talla_cm ?? '')}</td>
                                <td>${escaparHtml(h.imc ?? '')}</td>
                                <td>${escaparHtml(h.perimetro_braquial_cm ?? '')}</td>
                                <td>${snBadge(h.nivel_alerta, h.diagnostico_global || 'Pendiente')}</td>
                                <td>${escaparHtml(h.estado_control || '')}</td>
                                <td>${escaparHtml(h.proximo_control || '')}</td>
                            </tr>
                        `).join('')}</tbody>
                    </table>
                </div>
            `;
        })
        .catch((error) => snMensaje(error.message || 'No se encontró ficha.', 'error'));
}

function snCargarAlertas() {
    fetch(`${backendUrl}/api/salud-nutricion/alertas?atendida=0`)
        .then(manejarRespuestaJson)
        .then((data) => {
            const tbody = document.getElementById('sn-alertas-list');
            const alertas = data.alertas || [];
            if (!tbody) return;
            if (!alertas.length) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-slate-500">Sin alertas pendientes.</td></tr>';
                return;
            }
            tbody.innerHTML = alertas.map((a) => `
                <tr>
                    <td>${snBadge(a.nivel, a.nivel)}</td>
                    <td>${escaparHtml(a.tipo || '')}</td>
                    <td>${escaparHtml(a.documento || '')}</td>
                    <td>${escaparHtml(a.unidad || '')}</td>
                    <td>${escaparHtml(a.mensaje || '')}</td>
                    <td>${escaparHtml(a.fecha_creacion || '')}</td>
                    <td><button onclick="snAtenderAlerta(${Number(a.id)})" class="rounded-lg bg-emerald-600 hover:bg-emerald-500 px-2 py-1 text-xs text-white">Atender</button></td>
                </tr>
            `).join('');
        })
        .catch((error) => snMensaje(error.message || 'No se pudieron cargar alertas.', 'error'));
}

function snAtenderAlerta(id) {
    fetch(`${backendUrl}/api/salud-nutricion/alertas/${encodeURIComponent(id)}/atender`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ observaciones: 'Atendida desde dashboard' })
    })
        .then(manejarRespuestaJson)
        .then(() => snCargarAlertas())
        .catch((error) => snMensaje(error.message || 'No se pudo atender alerta.', 'error'));
}

function snCargarCalendario() {
    fetch(`${backendUrl}/api/salud-nutricion/calendario`)
        .then(manejarRespuestaJson)
        .then((data) => {
            const cont = document.getElementById('sn-calendario-list');
            const eventos = data.eventos || [];
            if (!cont) return;
            if (!eventos.length) {
                cont.innerHTML = '<p class="text-slate-500">Sin eventos nutricionales programados.</p>';
                return;
            }
            cont.innerHTML = eventos.slice(0, 200).map((e) => `
                <div class="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                    <div class="flex items-start justify-between gap-3">
                        <div>
                            <p class="text-sm font-semibold text-slate-200">${escaparHtml(e.fecha || '')}</p>
                            <p class="mt-1 text-xs text-slate-400">${escaparHtml(e.tipo || '')}</p>
                        </div>
                        ${snBadge(e.nivel, e.nivel)}
                    </div>
                    <p class="mt-3 text-sm text-slate-300">${escaparHtml(e.nombre || '')}</p>
                    <p class="mt-1 text-xs text-slate-500">${escaparHtml(e.unidad || '')}</p>
                    <p class="mt-2 text-xs text-slate-400">${escaparHtml(e.descripcion || '')}</p>
                </div>
            `).join('');
        })
        .catch((error) => snMensaje(error.message || 'No se pudo cargar calendario nutricional.', 'error'));
}

function snGenerarReporte(formato = 'excel') {
    fetch(`${backendUrl}/api/salud-nutricion/reportes/dashboard?formato=${encodeURIComponent(formato)}`)
        .then(manejarRespuestaJson)
        .then((data) => {
            snMensaje(data.message || 'Reporte generado.', 'success');
            if (data.archivo) snDescargarReporte(data.archivo);
        })
        .catch((error) => snMensaje(error.message || 'No se pudo generar reporte.', 'error'));
}

function snDescargarReporte(nombre) {
    window.descargarArchivoAutenticado(`${backendUrl}/api/salud-nutricion/reportes/${encodeURIComponent(nombre)}`).catch((error) => snMensaje(error.message, 'error'));
}


// ---------------------------------------------------------------------------
// Sistema Integral Salud y Nutrición 2.6.0
// ---------------------------------------------------------------------------
function snIntegralUnidad() {
    return document.getElementById('sn-integral-unidad')?.value?.trim() || '';
}

function snIntegralFetch(path, options = {}) {
    return fetch(`${backendUrl}${path}`, options).then(manejarRespuestaJson);
}

function snIntegralCargar() {
    const unidad = snIntegralUnidad();
    const query = unidad ? `?unidad=${encodeURIComponent(unidad)}` : '';
    snIntegralFetch(`/api/salud-nutricion/integral/dashboard${query}`)
        .then((data) => {
            const r = data.resumen || {};
            const ids = {
                'sn-int-kpi-exp': r.expedientes,
                'sn-int-kpi-docs': r.documentos_pendientes,
                'sn-int-kpi-afiliacion': r.sin_afiliacion,
                'sn-int-kpi-vacunas': r.sin_vacunas,
                'sn-int-kpi-valoracion': r.sin_valoracion_integral,
                'sn-int-kpi-rutas': r.canalizaciones_abiertas,
                'sn-int-kpi-actividades': r.actividades_pendientes,
            };
            Object.entries(ids).forEach(([id, value]) => { const el = document.getElementById(id); if (el) el.innerText = Number(value || 0); });
            snEstado.integral.expedientes = data.expedientes || [];
            snEstado.integral.actividades = data.actividades || [];
            snEstado.integral.rutas = data.canalizaciones || [];
            snIntegralRenderExpedientes();
            snIntegralRenderRutas();
        })
        .catch((error) => snMensaje(error.message || 'No se pudo cargar el expediente integral.', 'error'));
}

function snIntegralRenderExpedientes() {
    const tbody = document.getElementById('sn-integral-expedientes');
    if (!tbody) return;
    const rows = snEstado.integral.expedientes || [];
    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-slate-500">No hay expedientes sincronizados.</td></tr>';
        return;
    }
    tbody.innerHTML = rows.map((row) => {
        const total = Number(row.documentos_total || 0);
        const ok = Number(row.documentos_al_dia || 0);
        return `<tr>
            <td>${escaparHtml(row.unidad_nombre || '')}</td>
            <td>${escaparHtml(row.documento || '')}</td>
            <td>#${Number(row.id || 0)} · ${escaparHtml(row.tipo_participante || '')}</td>
            <td>${ok}/${total}</td>
            <td>${Number(row.alertas_abiertas || 0)}</td>
            <td>${Number(row.canalizaciones_abiertas || 0)}</td>
            <td><button onclick="snIntegralVerExpediente(${Number(row.id)})" class="sn-ent-btn">Abrir</button></td>
        </tr>`;
    }).join('');
}

function snIntegralSincronizar() {
    const unidad = snIntegralUnidad();
    mostrarCargando('Sincronizando expedientes de salud...');
    snIntegralFetch('/api/salud-nutricion/integral/expedientes/sincronizar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ unidad_nombre: unidad || null })
    }).then((data) => {
        ocultarCargando();
        const r = data.resultado || {};
        snMensaje(`${data.message || 'Sincronización completada'} Creados: ${r.creados || 0}; actualizados: ${r.actualizados || 0}.`, 'success');
        snIntegralCargar();
    }).catch((error) => { ocultarCargando(); snMensaje(error.message || 'No se pudo sincronizar.', 'error'); });
}

function snIntegralVerExpediente(id) {
    snIntegralFetch(`/api/salud-nutricion/integral/expedientes/${encodeURIComponent(id)}`)
        .then((data) => {
            const box = document.getElementById('sn-integral-detalle');
            if (!box) return;
            const exp = data.expediente || {};
            const docs = data.documentos || [];
            const vals = data.valoraciones || [];
            const routes = data.canalizaciones || [];
            box.classList.remove('hidden');
            box.innerHTML = `
                <div class="flex items-start justify-between gap-3"><div><h4 class="font-semibold text-slate-100">Expediente #${Number(exp.id || 0)} · ${escaparHtml(exp.documento || '')}</h4><p class="text-xs text-slate-400">${escaparHtml(exp.unidad_nombre || '')} · ${escaparHtml(exp.tipo_participante || '')}</p></div><button onclick="document.getElementById('sn-integral-detalle').classList.add('hidden')" class="sn-ent-btn">Cerrar</button></div>
                <h5 class="mt-4 mb-2 text-sm font-semibold text-emerald-300">Documentos y atenciones priorizadas</h5>
                <div class="overflow-x-auto"><table class="w-full text-left text-xs sn-table text-slate-400"><thead><tr><th>Tipo</th><th>Estado</th><th>Vencimiento</th><th>Acción</th></tr></thead><tbody>${docs.map((d) => `<tr><td>${escaparHtml(d.tipo_documento || '')}</td><td><select id="sn-doc-state-${Number(d.id)}" class="sn-ent-input"><option ${d.estado==='PENDIENTE'?'selected':''}>PENDIENTE</option><option ${d.estado==='EN_TRAMITE'?'selected':''}>EN_TRAMITE</option><option ${d.estado==='VIGENTE'?'selected':''}>VIGENTE</option><option ${d.estado==='VALIDADO'?'selected':''}>VALIDADO</option><option ${d.estado==='VENCIDO'?'selected':''}>VENCIDO</option><option ${d.estado==='NO_APLICA'?'selected':''}>NO_APLICA</option><option ${d.estado==='OBSERVADO'?'selected':''}>OBSERVADO</option></select></td><td>${escaparHtml(d.fecha_vencimiento || '')}</td><td><button onclick="snIntegralActualizarDocumento(${Number(d.id)})" class="sn-ent-btn sn-ent-btn-validar">Guardar</button></td></tr>`).join('')}</tbody></table></div>
                <h5 class="mt-5 mb-2 text-sm font-semibold text-cyan-300">Historia antropométrica</h5>
                <div class="overflow-x-auto"><table class="w-full text-left text-xs sn-table text-slate-400"><thead><tr><th>Fecha</th><th>Peso</th><th>Talla</th><th>PB</th><th>Sugerencia automática</th><th>Validación profesional</th><th>Acción</th></tr></thead><tbody>${vals.length ? vals.map((v) => `<tr><td>${escaparHtml(v.fecha_valoracion || '')}</td><td>${escaparHtml(v.peso_kg ?? '')}</td><td>${escaparHtml(v.talla_cm ?? '')}</td><td>${escaparHtml(v.perimetro_braquial_cm ?? '')}</td><td>${snBadge(v.nivel_alerta, v.diagnostico_global || 'Pendiente')}</td><td>${escaparHtml(v.clasificacion_profesional || v.estado_validacion || 'PENDIENTE')}</td><td><button onclick="snIntegralValidarValoracion(${Number(v.id)}, '${String(v.diagnostico_global || '').replace(/'/g, "\\'")}')" class="sn-ent-btn sn-ent-btn-validar">Validar</button></td></tr>`).join('') : '<tr><td colspan="7" class="text-center text-slate-500">Sin valoraciones.</td></tr>'}</tbody></table></div>
                <p class="mt-3 text-xs text-slate-500">Canalizaciones asociadas: ${routes.length}. Las clasificaciones automáticas no constituyen diagnóstico clínico.</p>`;
            lucide.createIcons();
        })
        .catch((error) => snMensaje(error.message || 'No se pudo abrir el expediente.', 'error'));
}

function snIntegralActualizarDocumento(id) {
    const estado = document.getElementById(`sn-doc-state-${id}`)?.value || 'PENDIENTE';
    snIntegralFetch(`/api/salud-nutricion/integral/documentos/${encodeURIComponent(id)}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ estado, fecha_verificacion: new Date().toISOString().slice(0, 10) })
    }).then((data) => { snMensaje(data.message || 'Documento actualizado.', 'success'); snIntegralCargar(); }).catch((error) => snMensaje(error.message, 'error'));
}

function snIntegralValidarValoracion(id, automatico) {
    const clasificacion = window.prompt('Clasificación profesional. Puedes conservar la sugerencia automática o ajustarla con sustento:', automatico || '');
    if (clasificacion === null) return;
    const observacion = window.prompt('Observación profesional / sustento de la validación:', '') || '';
    snIntegralFetch(`/api/salud-nutricion/integral/valoraciones/${encodeURIComponent(id)}/validar`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ estado_validacion: 'VALIDADA', clasificacion_profesional: clasificacion, observacion_profesional: observacion })
    }).then((data) => { snMensaje(data.message || 'Valoración validada.', 'success'); snIntegralCargar(); }).catch((error) => snMensaje(error.message, 'error'));
}

function snIntegralGenerarCapture() {
    const unidad = snIntegralUnidad();
    const periodo = document.getElementById('sn-capture-periodo')?.value?.trim() || '';
    mostrarCargando('Preparando CAPTURE con valoraciones validadas...');
    snIntegralFetch('/api/salud-nutricion/integral/capture', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ unidad: unidad || null, periodo: periodo || null, formatos: ['XLSX', 'PDF'] })
    }).then((data) => {
        ocultarCargando();
        snMensaje(`${data.message || 'CAPTURE preparado'} ${data.resultado?.advertencia || ''}`, 'success');
        (data.resultado?.productos || []).forEach((p) => window.descargarArchivoAutenticado(`${backendUrl}/api/salud-nutricion/integral/productos/${p.id}/descargar`).catch(() => {}));
    }).catch((error) => { ocultarCargando(); snMensaje(error.message || 'No se pudo generar CAPTURE.', 'error'); });
}

function snIntegralCrearActividad() {
    const payload = {
        unidad_nombre: document.getElementById('sn-act-unidad')?.value?.trim(),
        linea_componente: document.getElementById('sn-act-linea')?.value,
        tipo_actividad: document.getElementById('sn-act-tipo')?.value?.trim() || 'JORNADA',
        fecha_programada: document.getElementById('sn-act-fecha')?.value,
        titulo: document.getElementById('sn-act-titulo')?.value?.trim(),
        objetivo: document.getElementById('sn-act-objetivo')?.value?.trim(),
        incluir_uca_completa: true,
    };
    snIntegralFetch('/api/salud-nutricion/integral/actividades', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
        .then((data) => { snMensaje(data.message || 'Actividad creada.', 'success'); snIntegralCargarActividades(); })
        .catch((error) => snMensaje(error.message || 'No se pudo crear la actividad.', 'error'));
}

function snIntegralCargarActividades() {
    snIntegralFetch('/api/salud-nutricion/integral/actividades')
        .then((data) => { snEstado.integral.actividades = data.actividades || []; snIntegralRenderActividades(); })
        .catch((error) => snMensaje(error.message || 'No se pudieron cargar jornadas.', 'error'));
}

function snIntegralRenderActividades() {
    const tbody = document.getElementById('sn-integral-actividades');
    if (!tbody) return;
    const rows = snEstado.integral.actividades || [];
    if (!rows.length) { tbody.innerHTML = '<tr><td colspan="8" class="text-center text-slate-500">Sin jornadas registradas.</td></tr>'; return; }
    tbody.innerHTML = rows.map((a) => `<tr><td>${escaparHtml(a.fecha_programada || '')}</td><td>${escaparHtml(a.unidad_nombre || '')}</td><td>${escaparHtml(a.linea_componente || '')}</td><td>${escaparHtml(a.titulo || '')}</td><td>${escaparHtml(a.estado || '')}</td><td>${Number(a.asistentes_total || 0)}/${Number(a.participantes_total || 0)}</td><td>${Number(a.evidencias_total || 0)}</td><td class="space-x-1"><button onclick="snIntegralRegistrarEjecucion(${Number(a.id)})" class="sn-ent-btn sn-ent-btn-validar">Ejecución</button><button onclick="snTematicasGenerarInforme(${Number(a.id)})" class="sn-ent-btn">Informe</button><button onclick="snIntegralPrepararDocumentos(${Number(a.id)})" class="sn-ent-btn">Acta/Listado</button><button onclick="snIntegralSubirEvidencia(${Number(a.id)})" class="sn-ent-btn sn-ent-btn-foto">Evidencia</button></td></tr>`).join('');
}

async function snIntegralRegistrarEjecucion(activityId) {
    const fecha=window.prompt('Fecha real de ejecución (AAAA-MM-DD). Déjala vacía si aún no se realizó:','');
    if(fecha===null || !fecha.trim()) return;
    const metodologia=window.prompt('Metodología realmente realizada:',''); if(metodologia===null)return;
    const resultados=window.prompt('Resultados reportados por la persona responsable (no resultados supuestos):',''); if(resultados===null)return;
    const compromisos=window.prompt('Compromisos registrados (opcional):','') || '';
    try { const data=await snIntegralFetch(`/api/salud-nutricion/integral/actividades/${activityId}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({fecha_ejecucion:fecha.trim(),metodologia:metodologia.trim(),resultados:resultados.trim(),compromisos_generales:compromisos.trim(),estado:'REALIZADA'})}); snMensaje(data.message || 'Ejecución registrada para revisión.','success'); snIntegralCargarActividades(); }
    catch(error){snMensaje(error.message,'error');}
}

async function snTematicasGenerarInforme(activityId) {
    try {
        const check=await snTematicasRequest(`/api/salud-nutricion/tematicas/actividades/${activityId}/completitud`);
        if(check.faltantes?.length && !window.confirm(`El borrador quedará INCOMPLETO. Faltan: ${check.faltantes.join(', ')}. ¿Generarlo sin inventar datos?`)) return;
        const data=await snTematicasRequest(`/api/salud-nutricion/tematicas/actividades/${activityId}/informe`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({disparador:'MANUAL_UI'})});
        const formatWarning=data.informe?.formato?.advertencia || '';
        snMensaje(`${data.message} ${(data.faltantes || []).length ? 'Pendientes: '+data.faltantes.join(', ') : ''} ${formatWarning}`,'success');
        const product=data.informe?.producto; if(product?.id) window.descargarArchivoAutenticado(`${backendUrl}/api/salud-nutricion/integral/productos/${product.id}/descargar`).catch(()=>{});
    } catch(error){snMensaje(error.message,'error');}
}

function snIntegralPrepararDocumentos(activityId) {
    snIntegralFetch(`/api/salud-nutricion/integral/actividades/${encodeURIComponent(activityId)}/documentos`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tipos: ['ACTA', 'LISTADO_ASISTENCIA', 'INFORME'] }) })
        .then((data) => {
            snMensaje(`${data.message || 'Documentos preparados.'} ${(data.resultado?.advertencias || []).join(' ')}`, 'success');
            (data.resultado?.documentos || []).forEach((p) => window.descargarArchivoAutenticado(`${backendUrl}/api/salud-nutricion/integral/productos/${p.id}/descargar`).catch(() => {}));
            snIntegralCargarActividades();
        }).catch((error) => snMensaje(error.message, 'error'));
}

async function snTematicasRequest(path, options = {}) {
    const response = await fetch(`${backendUrl}${path}`, { credentials: 'include', ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'No fue posible completar la operación.');
    return data;
}

async function snTematicasCargar() {
    try {
        const [materials, units, assignments, templateStatus, reports] = await Promise.all([
            snTematicasRequest('/api/salud-nutricion/tematicas/materiales'),
            snTematicasRequest('/api/salud-nutricion/tematicas/unidades'),
            snTematicasRequest('/api/salud-nutricion/tematicas/asignaciones'),
            snTematicasRequest('/api/salud-nutricion/tematicas/plantilla-informe'),
            snTematicasRequest('/api/salud-nutricion/tematicas/informes')
        ]);
        snEstado.tematicas = materials.materiales || [];
        const templateBox=document.getElementById('sn-theme-template-status');
        if(templateBox) {
            const actaReady=Boolean(templateStatus.formatos?.ACTA?.disponible);
            const reportReady=Boolean(templateStatus.formatos?.INFORME?.disponible);
            const ready=actaReady && reportReady;
            templateBox.className=`mt-3 rounded-xl border p-3 text-sm ${ready ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' : 'border-amber-500/40 bg-amber-500/10 text-amber-200'}`;
            templateBox.textContent=`Acta institucional: ${actaReady ? 'aprobada' : 'pendiente'} · Informe institucional: ${reportReady ? 'aprobado' : 'pendiente'}. ${templateStatus.advertencia || ''}`;
        }
        const unitBox = document.getElementById('sn-theme-units');
        if (unitBox) unitBox.innerHTML = (units.unidades || []).map((u) => `<label class="flex gap-2"><input type="checkbox" value="${Number(u.id)}"><span>${escaparHtml(u.nombre || '')}</span></label>`).join('') || '<span class="text-amber-300">No hay unidades activas en Base Maestra.</span>';
        const planUnit=document.getElementById('sn-theme-plan-unit');
        if(planUnit) planUnit.innerHTML='<option value="">Unidad</option>'+(units.unidades || []).map((u)=>`<option value="${Number(u.id)}">${escaparHtml(u.nombre || '')}</option>`).join('');
        const published=document.getElementById('sn-theme-published');
        const unique=new Map(); (assignments.asignaciones || []).forEach((a)=>unique.set(`${a.tema_id}:${a.periodo}:${a.unidad_id}`,a));
        if(published) published.innerHTML=[...unique.values()].map((a)=>`<label class="rounded-xl border border-slate-700 p-2"><input type="checkbox" value="${Number(a.tema_id)}" data-period="${escaparHtml(a.periodo || '')}" data-unit="${Number(a.unidad_id)}"> <span>${escaparHtml(a.titulo_normalizado || a.titulo_original || '')}</span><small class="block text-slate-500">${escaparHtml(a.periodo || '')} · ${escaparHtml(a.unidad_nombre || '')}</small></label>`).join('') || '<span class="text-slate-500">Publica temáticas para habilitar la planeación.</span>';
        const host = document.getElementById('sn-theme-materials');
        if (!host) return;
        host.innerHTML = snEstado.tematicas.length ? snEstado.tematicas.map((m) => `<article class="sn-card"><div class="flex flex-wrap justify-between gap-2"><div><strong>${escaparHtml(m.titulo_documento || '')}</strong><p class="text-xs text-slate-400">${escaparHtml(m.estado || '')} · ${escaparHtml(m.metodo_extraccion || '')}</p></div><a class="text-cyan-300" target="_blank" href="${backendUrl}/api/idp/documentos/${Number(m.idp_documento_id)}/vista-previa">Ver original</a></div><div class="mt-3 grid gap-3">${(m.temas || []).map((t) => `<div class="rounded-xl border border-slate-700 p-3"><label class="text-xs text-slate-400">Título extraído</label><p>${escaparHtml(t.titulo_original || '')}</p><label class="mt-2 block text-xs text-slate-400">Denominación normalizada propuesta</label><input class="sn-ent-input w-full" value="${escaparHtml(t.titulo_normalizado || '')}" onchange="snTematicaEditar(${Number(t.id)},${Number(t.revision)},this.value)"><p class="mt-2 text-xs text-slate-500">Procedencia: ${escaparHtml(JSON.stringify(t.procedencia || {}))}</p></div>`).join('') || '<p class="text-amber-300">Sin contenido temático identificado.</p>'}</div><button class="mt-3 rounded-xl bg-emerald-600 px-4 py-2 text-sm" onclick="snTematicasPublicar(${Number(m.id)})">Revisar alcance y publicar</button></article>`).join('') : '<p class="text-slate-400">Aún no hay materiales temáticos.</p>';
        snTematicasRenderInformes(reports.informes || []);
    } catch (error) { snMensaje(error.message, 'error'); }
}

function snTematicasRenderInformes(rows) {
    const body=document.getElementById('sn-theme-reports'); if(!body)return;
    if(!rows.length) { body.innerHTML='<tr><td colspan="7" class="text-center text-slate-500">Aún no hay borradores temáticos.</td></tr>'; return; }
    body.innerHTML=rows.map((r)=>{
        const state=String(r.estado || ''); const revision=Number(r.revision || 1); const missing=r.faltantes || [];
        const institutional=String(r.plantilla_codigo || '')==='INFORME_SALUD_NUTRICION';
        const actions=[`<button onclick="snTematicasDescargarInforme(${Number(r.producto_id)})" class="sn-ent-btn">Descargar</button>`];
        if(['BORRADOR','BORRADOR_INCOMPLETO','DEVUELTO'].includes(state)) actions.push(`<button onclick="snTematicasCambiarInforme(${Number(r.id)},${revision},'EN_REVISION')" class="sn-ent-btn sn-ent-btn-validar">Enviar a revisión</button>`);
        if(state==='EN_REVISION') {
            actions.push(`<button onclick="snTematicasCambiarInforme(${Number(r.id)},${revision},'DEVUELTO')" class="sn-ent-btn">Devolver</button>`);
            if(institutional && !missing.length) actions.push(`<button onclick="snTematicasCambiarInforme(${Number(r.id)},${revision},'APROBADO')" class="sn-ent-btn sn-ent-btn-validar">Aprobar</button>`);
            else actions.push('<span class="text-amber-300">Aprobación bloqueada</span>');
        }
        return `<tr><td>${escaparHtml(r.titulo || `Actividad ${r.actividad_id}`)}</td><td>${escaparHtml(r.unidad_nombre || '')}</td><td>v${Number(r.version || 1)} · rev.${revision}</td><td>${escaparHtml(state)}</td><td>${institutional ? `Institucional ${escaparHtml(r.plantilla_version || '')}` : '<span class="text-amber-300">Interno</span>'}</td><td>${missing.length ? escaparHtml(missing.join(', ')) : 'Completo'}</td><td class="space-x-1">${actions.join('')}</td></tr>`;
    }).join('');
}

function snTematicasDescargarInforme(productId) {
    if(!productId) return snMensaje('El informe no tiene un archivo disponible.','error');
    window.descargarArchivoAutenticado(`${backendUrl}/api/salud-nutricion/integral/productos/${productId}/descargar`).catch((error)=>snMensaje(error.message,'error'));
}

async function snTematicasCambiarInforme(reportId,revision,estado) {
    let observaciones='';
    if(estado==='DEVUELTO') { observaciones=window.prompt('Indica claramente qué debe corregirse:','') || ''; if(!observaciones.trim()) return snMensaje('La devolución requiere una observación.','error'); }
    if(!window.confirm(`Cambiar el informe a ${estado}. Se validará la revisión ${revision}. ¿Continuar?`)) return;
    try {
        const data=await snTematicasRequest(`/api/salud-nutricion/tematicas/informes/${reportId}/estado`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado,revision,observaciones})});
        snMensaje(data.message || 'Estado actualizado.','success'); await snTematicasCargar();
    } catch(error) { snMensaje(error.message,'error'); await snTematicasCargar(); }
}

async function snTematicasSubirPlantilla() {
    const kind=document.getElementById('sn-template-kind')?.value || 'ACTA';
    const version=document.getElementById('sn-template-version')?.value?.trim() || '';
    const file=document.getElementById('sn-template-file')?.files?.[0];
    if(!file || !file.name.toLowerCase().endsWith('.docx')) return snMensaje('Selecciona una plantilla limpia en formato DOCX.','error');
    const code=`${kind}_SALUD_NUTRICION`; const form=new FormData();
    form.append('file',file); form.append('codigo',code); form.append('tipo_documento',code);
    form.append('nombre',kind==='ACTA' ? 'Acta de Salud y Nutrición' : 'Informe de Salud y Nutrición');
    form.append('componente','SALUD_NUTRICION'); if(version) form.append('version',version);
    try {
        const data=await snTematicasRequest('/api/documentos/plantillas',{method:'POST',body:form});
        const pending={versionId:Number(data.plantilla_version?.id || 0),kind,fields:data.mapeo?.mapeo?.campos || []}; snEstado.plantillaPendiente=pending;
        const review=document.getElementById('sn-template-review');
        if(review) { review.classList.remove('hidden'); review.innerHTML=`<strong>Mapeo propuesto para ${escaparHtml(kind)}</strong><p class="mt-1">${pending.fields.length ? pending.fields.map((x)=>escaparHtml(x.field_key || '')).join(' · ') : 'No se detectaron campos automáticos; revisa el documento en Centro Documental.'}</p>${pending.versionId && pending.fields.length ? '<button onclick="snTematicasAprobarPlantilla()" class="mt-3 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white">Confirmar y aprobar este mapeo</button>' : ''}`; }
        snMensaje(`${data.message || 'Plantilla registrada.'} Revisa los campos antes de aprobar.`,'success');
        await snTematicasCargar();
    } catch(error) { snMensaje(error.message,'error'); }
}

async function snTematicasAprobarPlantilla() {
    const pending=snEstado.plantillaPendiente;
    if(!pending?.versionId || !pending.fields?.length) return snMensaje('No hay un mapeo detectable listo para aprobar.','error');
    if(!window.confirm(`Aprobar ${pending.fields.length} campos de la plantilla ${pending.kind}. Esta versión se usará para nuevos documentos. ¿Continuar?`)) return;
    try {
        const data=await snTematicasRequest(`/api/documentos/plantillas/${pending.versionId}/aprobar`,{method:'POST'});
        snMensaje(`${data.message || 'Mapeo aprobado.'} Campos aprobados: ${data.mapeo?.campos_aprobados || pending.fields.length}.`,'success');
        snEstado.plantillaPendiente=null; const review=document.getElementById('sn-template-review'); if(review) review.classList.add('hidden');
        await snTematicasCargar();
    } catch(error) { snMensaje(error.message,'error'); }
}

async function snTematicasPlanificar() {
    const unidad_id=Number(document.getElementById('sn-theme-plan-unit')?.value || 0);
    const selected=[...document.querySelectorAll('#sn-theme-published input:checked')];
    const periodos=[...new Set(selected.map((x)=>x.dataset.period))];
    if(!unidad_id || !selected.length || periodos.length!==1) return snMensaje('Selecciona una unidad y temas de un mismo periodo.','error');
    if(selected.some((x)=>Number(x.dataset.unit)!==unidad_id)) return snMensaje('Todas las temáticas deben estar publicadas para la unidad seleccionada.','error');
    const payload={unidad_id,periodo:periodos[0],tema_ids:[...new Set(selected.map((x)=>Number(x.value)))],linea_componente:document.getElementById('sn-theme-plan-line')?.value,fecha_programada:document.getElementById('sn-theme-plan-date')?.value || null,titulo:document.getElementById('sn-theme-plan-title')?.value?.trim(),objetivo:document.getElementById('sn-theme-plan-objective')?.value?.trim(),metodologia:document.getElementById('sn-theme-plan-method')?.value?.trim()};
    try { const data=await snTematicasRequest('/api/salud-nutricion/tematicas/planificar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); snMensaje(data.message,'success'); }
    catch(error){ snMensaje(error.message,'error'); }
}

async function snTematicasExtraer() {
    const documentoId = Number(document.getElementById('sn-theme-document-id')?.value || 0);
    const periodo = document.getElementById('sn-theme-period')?.value || null;
    if (!documentoId) return snMensaje('Indica el ID del material cargado en Motor Documental.', 'error');
    try {
        const data = await snTematicasRequest('/api/salud-nutricion/tematicas/extraer', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({documento_id:documentoId,periodo}) });
        snMensaje(data.message, 'success'); await snTematicasCargar();
    } catch (error) { snMensaje(error.message, 'error'); }
}

async function snTematicasCargarArchivo() {
    const file = document.getElementById('sn-theme-file')?.files?.[0];
    if (!file) return snMensaje('Selecciona un material JPG, PNG o PDF.', 'error');
    const form=new FormData(); form.append('file',file);
    try {
        snMensaje('Guardando el original privado y ejecutando la lectura…','success');
        let uploaded=await snTematicasRequest('/api/idp/documentos',{method:'POST',body:form});
        let docData=uploaded.documento || {};
        for (let attempt=0; attempt<20 && ['EN_COLA','PROCESANDO','RECIBIDO'].includes(String(docData.estado || '').toUpperCase()); attempt+=1) {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            const status=await snTematicasRequest(`/api/idp/documentos/${Number(docData.id)}`);
            docData=status.documento || docData;
        }
        if (['EN_COLA','PROCESANDO','RECIBIDO'].includes(String(docData.estado || '').toUpperCase())) throw new Error('El material sigue procesándose. Conserva su ID y vuelve a intentar la extracción en unos minutos.');
        if (['REQUIERE_OCR','ERROR'].includes(String(docData.estado || '').toUpperCase())) {
            const retried=await snTematicasRequest(`/api/idp/documentos/${Number(docData.id)}/reintentar-ocr`,{method:'POST'});
            docData=retried.documento || docData;
        }
        const id=Number(docData.id || uploaded.documento?.id || 0);
        if (!id) throw new Error('El Motor Documental no devolvió el identificador del material.');
        const idInput=document.getElementById('sn-theme-document-id'); if(idInput) idInput.value=String(id);
        await snTematicasExtraer();
    } catch(error) { snMensaje(error.message,'error'); }
}

async function snTematicaEditar(id, revision, value) {
    try { await snTematicasRequest(`/api/salud-nutricion/tematicas/temas/${id}`, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision,titulo_normalizado:value,motivo:'Revisión profesional'})}); snMensaje('Corrección guardada con trazabilidad.','success'); await snTematicasCargar(); }
    catch (error) { snMensaje(error.message,'error'); await snTematicasCargar(); }
}

async function snTematicasPublicar(materialId) {
    const periodo = document.getElementById('sn-theme-period')?.value || '';
    const unidad_ids = [...document.querySelectorAll('#sn-theme-units input:checked')].map((x) => Number(x.value));
    if (!periodo || !unidad_ids.length) return snMensaje('Confirma el periodo y al menos una unidad.', 'error');
    if (!window.confirm(`Publicar las temáticas en ${unidad_ids.length} unidad(es) para ${periodo}. Esto no registra ejecución ni asistentes. ¿Continuar?`)) return;
    try { const data=await snTematicasRequest(`/api/salud-nutricion/tematicas/materiales/${materialId}/publicar`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({periodo,unidad_ids,confirmar:true})}); snMensaje(data.message,'success'); await snTematicasCargar(); }
    catch(error){ snMensaje(error.message,'error'); }
}

function snLineas(id) {
    return String(document.getElementById(id)?.value || '').split(/\r?\n/).map((value) => value.trim()).filter(Boolean);
}

function snCargarPeriodosMensuales() {
    snIntegralFetch('/api/salud-nutricion/integral/periodos-mensuales').then((data) => {
        snEstado.integral.periodos = data.periodos || [];
        const body = document.getElementById('sn-month-list');
        if (!body) return;
        body.innerHTML = snEstado.integral.periodos.length ? snEstado.integral.periodos.map((row) => `<tr><td>${escaparHtml(row.anio_mes || '')}</td><td>${escaparHtml(row.estado || '')}</td><td>${escaparHtml((row.temas || []).join(', '))}</td><td>${row.integridad_sha256 ? escaparHtml(row.integridad_sha256.slice(0, 12)) + '…' : 'Pendiente'}</td><td>${row.estado === 'APROBADO' ? `<button class="sn-ent-btn" onclick="snGenerarInformeMensual(${Number(row.id)})">Generar PDF/Excel</button>` : `<button class="sn-ent-btn sn-ent-btn-validar" onclick="snAprobarPeriodoMensual(${Number(row.id)})">Aprobar</button>`}</td></tr>`).join('') : '<tr><td colspan="5" class="text-center text-slate-500">Sin periodos registrados.</td></tr>';
    }).catch((error) => snMensaje(error.message, 'error'));
}

function snGuardarPeriodoMensual() {
    let variables = {};
    try { variables = JSON.parse(document.getElementById('sn-month-variables')?.value || '{}'); }
    catch (_) { snMensaje('Las variables deben estar en formato JSON válido.', 'error'); return; }
    const payload = { anio_mes: document.getElementById('sn-month-period')?.value, temas: String(document.getElementById('sn-month-topics')?.value || '').split(',').map((value) => value.trim()).filter(Boolean), observaciones: document.getElementById('sn-month-observations')?.value?.trim(), variables };
    snIntegralFetch('/api/salud-nutricion/integral/periodos-mensuales', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }).then((data) => { snMensaje(data.message, 'success'); snCargarPeriodosMensuales(); }).catch((error) => snMensaje(error.message, 'error'));
}

function snAprobarPeriodoMensual(id) {
    if (!window.confirm('Al aprobar, el periodo quedará bloqueado e inmutable. ¿Continuar?')) return;
    snIntegralFetch(`/api/salud-nutricion/integral/periodos-mensuales/${encodeURIComponent(id)}/aprobar`, { method: 'POST' }).then((data) => { snMensaje(data.message, 'success'); snCargarPeriodosMensuales(); }).catch((error) => snMensaje(error.message, 'error'));
}

function snGenerarInformeMensual(id) {
    mostrarCargando('Generando informe mensual aprobado...');
    snIntegralFetch(`/api/salud-nutricion/integral/periodos-mensuales/${encodeURIComponent(id)}/generar`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ formatos: ['XLSX', 'PDF'] }) }).then((data) => {
        const complete = (result) => {
            ocultarCargando(); snMensaje('Informe mensual generado correctamente.', 'success');
            (result?.productos || []).forEach((product) => window.descargarArchivoAutenticado(`${backendUrl}/api/salud-nutricion/integral/informes-mensuales/${product.id}/descargar`).catch(() => {}));
        };
        if (data.job_id && typeof esperarJobOperativo === 'function') esperarJobOperativo(data.job_id, complete, 'sn-message');
        else { ocultarCargando(); snMensaje('No fue posible iniciar el procesamiento en segundo plano.', 'error'); }
    }).catch((error) => { ocultarCargando(); snMensaje(error.message, 'error'); });
}

function snCargarActasInstitucionales() {
    snIntegralFetch('/api/salud-nutricion/integral/actas').then((data) => {
        snEstado.integral.actas = data.actas || [];
        const body = document.getElementById('sn-minutes-list');
        if (!body) return;
        body.innerHTML = snEstado.integral.actas.length ? snEstado.integral.actas.map((row) => `<tr><td>${escaparHtml(row.numero_acta || '')}</td><td>${escaparHtml(row.fecha || '')}</td><td>${escaparHtml(row.tema || '')}</td><td>${Number((row.tareas || []).length)}</td><td>${escaparHtml(row.estado || '')}</td><td>${row.estado === 'CERRADO' ? '<span class="text-emerald-300">Sellada</span>' : `<button class="sn-ent-btn sn-ent-btn-validar" onclick="snCerrarActaInstitucional(${Number(row.id)})">Cerrar</button>`}</td></tr>`).join('') : '<tr><td colspan="6" class="text-center text-slate-500">Sin actas registradas.</td></tr>';
    }).catch((error) => snMensaje(error.message, 'error'));
}

function snCrearActaInstitucional() {
    const tasks = snLineas('sn-minutes-tasks').map((line) => { const parts = line.split('|').map((value) => value.trim()); return { descripcion: parts[0], responsable_nombre: parts[1], fecha_limite: parts[2] }; });
    const payload = { fecha: document.getElementById('sn-minutes-date')?.value, lugar: document.getElementById('sn-minutes-place')?.value?.trim(), tema: document.getElementById('sn-minutes-topic')?.value?.trim(), puntos: snLineas('sn-minutes-points'), decisiones: snLineas('sn-minutes-decisions'), tareas: tasks };
    snIntegralFetch('/api/salud-nutricion/integral/actas', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }).then((data) => { snMensaje(`${data.message} ${data.acta?.numero_acta || ''}`, 'success'); snCargarActasInstitucionales(); }).catch((error) => snMensaje(error.message, 'error'));
}

function snCerrarActaInstitucional(id) {
    if (!window.confirm('El acta quedará cerrada, sellada e inmutable. ¿Continuar?')) return;
    snIntegralFetch(`/api/salud-nutricion/integral/actas/${encodeURIComponent(id)}/cerrar`, { method: 'POST' }).then((data) => { snMensaje(data.message, 'success'); snCargarActasInstitucionales(); }).catch((error) => snMensaje(error.message, 'error'));
}

function snIntegralSubirEvidencia(activityId) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.png,.jpg,.jpeg,.xlsx,.docx,.mp4';
    input.onchange = () => {
        const file = input.files?.[0];
        if (!file) return;
        const fd = new FormData(); fd.append('file', file); fd.append('actividad_id', activityId); fd.append('tipo', 'EVIDENCIA_ACTIVIDAD');
        snIntegralFetch('/api/salud-nutricion/integral/evidencias', { method: 'POST', body: fd })
            .then((data) => { snMensaje(data.message || 'Evidencia cargada.', 'success'); snIntegralCargarActividades(); })
            .catch((error) => snMensaje(error.message, 'error'));
    };
    input.click();
}

function snIntegralCrearRuta() {
    const payload = {
        expediente_id: Number(document.getElementById('sn-ruta-expediente')?.value || 0),
        tipo_ruta: document.getElementById('sn-ruta-tipo')?.value?.trim(),
        prioridad: document.getElementById('sn-ruta-prioridad')?.value,
        entidad_destino: document.getElementById('sn-ruta-entidad')?.value?.trim(),
        fecha_limite: document.getElementById('sn-ruta-fecha')?.value,
        motivo: document.getElementById('sn-ruta-motivo')?.value?.trim(),
    };
    snIntegralFetch('/api/salud-nutricion/integral/canalizaciones', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
        .then((data) => { snMensaje(data.message || 'Ruta registrada.', 'success'); snIntegralCargarRutas(); })
        .catch((error) => snMensaje(error.message || 'No se pudo registrar la ruta.', 'error'));
}

function snIntegralCargarRutas() {
    snIntegralFetch('/api/salud-nutricion/integral/canalizaciones')
        .then((data) => { snEstado.integral.rutas = data.canalizaciones || []; snIntegralRenderRutas(); })
        .catch((error) => snMensaje(error.message || 'No se pudieron cargar las rutas.', 'error'));
}

function snIntegralRenderRutas() {
    const tbody = document.getElementById('sn-integral-rutas');
    if (!tbody) return;
    const rows = snEstado.integral.rutas || [];
    if (!rows.length) { tbody.innerHTML = '<tr><td colspan="7" class="text-center text-slate-500">Sin canalizaciones registradas.</td></tr>'; return; }
    tbody.innerHTML = rows.map((r) => `<tr><td>${escaparHtml(r.fecha_activacion || '')}</td><td>${escaparHtml(r.unidad_nombre || '')}</td><td>${escaparHtml(r.tipo_ruta || '')}</td><td>${snBadge(r.prioridad === 'CRITICA' ? 'ROJO' : r.prioridad === 'ALTA' ? 'AMARILLO' : 'VERDE', r.prioridad || '')}</td><td>${escaparHtml(r.entidad_destino || '')}</td><td>${escaparHtml(r.estado || '')}</td><td>${escaparHtml(r.motivo || '')}</td></tr>`).join('');
}
