/* ALPHA51 - Entregables Salud y Nutrición.
   Extiende el módulo Salud/Nutrición sin tocar carga Cuéntame, CoreCursor ni formatos oficiales. */
let snEntEstado = {
    inicializado: false,
    entregables: [],
    resumen: {},
    anio: new Date().getFullYear(),
    mes: new Date().getMonth() + 1,
    catalogosCargados: false
};

function snEntMsg(texto, tipo = 'success') {
    const box = document.getElementById('sn-ent-message');
    if (!box) return;
    box.className = `rounded-xl px-4 py-3 text-sm ${tipo === 'success' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'}`;
    box.innerText = texto;
    box.classList.remove('hidden');
}

function snEntregablesInit() {
    if (!snEntEstado.inicializado) {
        snEntEstado.inicializado = true;
        const mes = document.getElementById('sn-ent-mes');
        const anio = document.getElementById('sn-ent-anio');
        if (mes) mes.value = String(snEntEstado.mes);
        if (anio) anio.value = String(snEntEstado.anio);
    }
    snEntCargarCatalogosMaestros();
    snEntCargar();
    if (window.lucide) lucide.createIcons();
}

function snEntFiltros() {
    return {
        mes: document.getElementById('sn-ent-mes')?.value || String(new Date().getMonth() + 1),
        anio: document.getElementById('sn-ent-anio')?.value || String(new Date().getFullYear()),
        uds: document.getElementById('sn-ent-uds')?.value?.trim() || '',
        coordinador: document.getElementById('sn-ent-coordinador')?.value?.trim() || '',
        estado: document.getElementById('sn-ent-estado')?.value || ''
    };
}

function snEntQuery(filtros = snEntFiltros()) {
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => { if (v !== undefined && v !== null && String(v).trim() !== '') params.set(k, v); });
    return params.toString();
}

function snEntActualizarStats(resumen = {}) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    set('sn-ent-stat-total', resumen.total || 0);
    set('sn-ent-stat-completos', resumen.completos || 0);
    set('sn-ent-stat-pendientes', resumen.pendientes || 0);
    set('sn-ent-stat-avance', `${resumen.porcentaje || 0}%`);
}

function snEntBadge(estado) {
    const e = String(estado || 'pendiente').toLowerCase();
    const cls = e === 'completo' ? 'sn-badge-verde' : e === 'observado' ? 'sn-badge-amarillo' : e === 'vencido' ? 'sn-badge-rojo' : 'sn-badge-amarillo';
    return `<span class="sn-badge ${cls}">${escaparHtml(estado || 'pendiente')}</span>`;
}

function snEntAcciones(row) {
    const id = Number(row.id);
    const acciones = [];
    const plantillas = new Set(String(row.plantillas_cargadas || '').split(',').filter(Boolean));
    const plantillaBtn = (tipo, extension) => `<button onclick="snEntSubirPlantilla('${escaparHtml(row.codigo)}', '${tipo}', '${extension}')" class="sn-ent-btn ${plantillas.has(tipo) ? 'sn-ent-btn-validar' : ''}" title="${plantillas.has(tipo) ? 'Plantilla oficial registrada' : 'Falta plantilla oficial'}">${plantillas.has(tipo) ? '✓ ' : '+ '}Plantilla ${tipo}</button>`;
    acciones.push(`<button onclick="snEntAbrirActividad(${id})" class="sn-ent-btn sn-ent-btn-validar">Registrar actividad</button>`);
    if (Number(row.requiere_acta || 0)) acciones.push(plantillaBtn('acta', '.docx'), `<button onclick="snEntGenerar(${id}, 'acta')" class="sn-ent-btn">Generar acta oficial</button>`);
    if (Number(row.requiere_listado || 0)) acciones.push(plantillaBtn('listado', '.xlsx'), `<button onclick="snEntGenerar(${id}, 'listado')" class="sn-ent-btn">Listado oficial</button>`);
    if (Number(row.requiere_oficio || 0)) acciones.push(`<button onclick="snEntGenerar(${id}, 'oficio')" class="sn-ent-btn">Oficio</button>`);
    if (Number(row.requiere_formato_excel || 0)) acciones.push(plantillaBtn('formato', '.xlsx'), `<button onclick="snEntGenerar(${id}, 'formato')" class="sn-ent-btn">Formato oficial</button>`);
    if (Number(row.requiere_fotos || 0)) acciones.push(`<button onclick="snEntSubirEvidencia(${id})" class="sn-ent-btn sn-ent-btn-foto">Fotos</button>`);
    acciones.push(`<button onclick="snEntValidar(${id})" class="sn-ent-btn sn-ent-btn-validar">Validar</button>`);
    return `<div class="flex flex-wrap gap-1.5">${acciones.join('')}</div>`;
}

function snEntOpcion(valor, etiqueta) {
    return `<option value="${escaparHtml(valor || '')}">${escaparHtml(etiqueta || valor || '')}</option>`;
}

function snEntCargarCatalogosMaestros() {
    const udsSelect = document.getElementById('sn-ent-uds');
    const coordinadorSelect = document.getElementById('sn-ent-coordinador');
    if (!udsSelect || !coordinadorSelect) return;
    const udsActual = udsSelect.value;
    const coordinadorActual = coordinadorSelect.value;
    Promise.all([
        fetch(`${backendUrl}/api/base-maestra/unidades`).then(manejarRespuestaJson),
        fetch(`${backendUrl}/api/base-maestra/coordinadores`).then(manejarRespuestaJson)
    ])
        .then(([unidadesData, coordinadoresData]) => {
            const unidades = (unidadesData.unidades || []).filter((item) => String(item.nombre || '').trim());
            const coordinadores = (coordinadoresData.coordinadores || []).filter((item) => String(item.coordinador || '').trim());
            udsSelect.innerHTML = snEntOpcion('TODAS', 'Todas las UDS/UCA') + unidades
                .map((item) => snEntOpcion(item.nombre, item.codigo_unidad ? `${item.nombre} · ${item.codigo_unidad}` : item.nombre))
                .join('');
            coordinadorSelect.innerHTML = snEntOpcion('', 'Seleccione un coordinador') + coordinadores
                .map((item) => snEntOpcion(item.coordinador, item.coordinador))
                .join('');
            udsSelect.value = Array.from(udsSelect.options).some((option) => option.value === udsActual) ? udsActual : 'TODAS';
            coordinadorSelect.value = Array.from(coordinadorSelect.options).some((option) => option.value === coordinadorActual) ? coordinadorActual : '';
            snEntEstado.catalogosCargados = true;
            if (!unidades.length) snEntMsg('La Base Maestra no tiene UDS/UCA activas. Carga y publica la Base Maestra para habilitar la selección.', 'error');
        })
        .catch((error) => {
            udsSelect.innerHTML = snEntOpcion('TODAS', 'Todas las UDS/UCA');
            coordinadorSelect.innerHTML = snEntOpcion('', 'Sin coordinadores disponibles');
            snEntMsg(error.message || 'No se pudieron leer las UDS/UCA y coordinadores de la Base Maestra.', 'error');
        });
}

function snEntSubirPlantilla(codigo, tipo, extension) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = extension;
    input.onchange = () => {
        const file = input.files?.[0];
        if (!file) return;
        const fd = new FormData();
        fd.append('file', file);
        mostrarCargando(`Registrando plantilla oficial de ${tipo}...`);
        fetch(`${backendUrl}/api/salud-nutricion/entregables/plantillas/${encodeURIComponent(codigo)}/${tipo}`, { method: 'POST', body: fd })
            .then(manejarRespuestaJson)
            .then((data) => {
                ocultarCargando();
                snEntMsg(data.message || 'Plantilla oficial registrada.', 'success');
                snEntCargar();
            })
            .catch((error) => {
                ocultarCargando();
                snEntMsg(error.message || 'No se pudo registrar la plantilla.', 'error');
            });
    };
    input.click();
}

function snEntAbrirActividad(id) {
    const row = snEntEstado.entregables.find((item) => Number(item.id) === Number(id));
    if (!row) return;
    const form = document.getElementById('sn-ent-activity-form');
    document.getElementById('sn-ent-activity-id').value = String(id);
    document.getElementById('sn-ent-activity-title').innerText = `${row.nombre || row.codigo} · ${row.uds || 'TODAS'}`;
    document.getElementById('sn-ent-act-fecha').value = new Date().toISOString().slice(0, 10);
    document.getElementById('sn-ent-act-lugar').value = row.uds || '';
    document.getElementById('sn-ent-act-responsable').value = row.responsable || '';
    document.getElementById('sn-ent-act-objetivo').value = row.actividad || '';
    ['inicio', 'final', 'dirigido', 'desarrollo', 'resultados', 'compromisos', 'dificultades', 'mejoras'].forEach((suffix) => {
        const input = document.getElementById(`sn-ent-act-${suffix}`);
        if (input) input.value = '';
    });
    document.getElementById('sn-ent-act-agenda').value = 'Saludo y bienvenida\nSocialización del tema\nDesarrollo de la actividad\nCompromisos\nCierre';
    document.getElementById('sn-ent-act-participantes').value = '0';
    document.getElementById('sn-ent-act-confirmado').checked = false;
    form?.classList.remove('hidden');
    form?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function snEntCerrarActividad() {
    document.getElementById('sn-ent-activity-form')?.classList.add('hidden');
}

function snEntGuardarActividad(confirmar = false) {
    const id = Number(document.getElementById('sn-ent-activity-id')?.value || 0);
    if (!id) return snEntMsg('Selecciona un entregable.', 'error');
    const value = (suffix) => document.getElementById(`sn-ent-act-${suffix}`)?.value?.trim() || '';
    const payload = {
        fecha_actividad: value('fecha'),
        hora_inicio: value('inicio'),
        hora_final: value('final'),
        lugar: value('lugar'),
        dirigido_a: value('dirigido'),
        responsable: value('responsable'),
        objetivo: value('objetivo'),
        agenda: value('agenda'),
        desarrollo: value('desarrollo'),
        resultados: value('resultados'),
        compromisos: value('compromisos'),
        dificultades: value('dificultades'),
        acciones_mejora: value('mejoras'),
        participantes_total: Number(value('participantes') || 0),
        confirmado: Boolean(confirmar)
    };
    if (confirmar && !document.getElementById('sn-ent-act-confirmado')?.checked) {
        return snEntMsg('Marca la confirmación de actividad realizada.', 'error');
    }
    mostrarCargando(confirmar ? 'Confirmando actividad...' : 'Guardando borrador...');
    fetch(`${backendUrl}/api/salud-nutricion/entregables/${id}/actividades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(manejarRespuestaJson)
        .then((data) => {
            ocultarCargando();
            snEntMsg(data.message || 'Actividad guardada.', 'success');
            snEntCerrarActividad();
            snEntCargar();
        })
        .catch((error) => {
            ocultarCargando();
            snEntMsg(error.message || 'No se pudo guardar la actividad.', 'error');
        });
}

function snEntRender(rows = [], resumen = {}) {
    const body = document.getElementById('sn-ent-list');
    snEntActualizarStats(resumen);
    if (!body) return;
    if (!rows.length) {
        body.innerHTML = '<tr><td colspan="8" class="text-center text-slate-500">No hay entregables creados para los filtros seleccionados.</td></tr>';
        return;
    }
    body.innerHTML = rows.map((row, idx) => {
        const fotos = Number(row.fotos_cargadas || 0);
        const minimo = Number(row.requiere_fotos || 0) ? Number(row.minimo_fotos || 4) : 0;
        const fotoTxt = minimo ? `${fotos}/${minimo}` : 'No aplica';
        return `
            <tr>
                <td>${idx + 1}</td>
                <td><div class="font-semibold text-slate-100">${escaparHtml(row.nombre || '')}</div><div class="mt-1 text-[11px] text-slate-500">${escaparHtml(row.codigo || '')}</div></td>
                <td>${escaparHtml(row.uds || 'TODAS')}</td>
                <td>${snEntBadge(row.estado)}</td>
                <td>${Number(row.actividades_confirmadas || 0)}</td>
                <td class="${minimo && fotos < minimo ? 'text-amber-300' : 'text-emerald-300'}">${fotoTxt}</td>
                <td>${Number(row.archivos_generados || 0)}</td>
                <td>${snEntAcciones(row)}</td>
            </tr>`;
    }).join('');
}

function snEntCargar() {
    const filtros = snEntFiltros();
    fetch(`${backendUrl}/api/salud-nutricion/entregables?${snEntQuery(filtros)}`)
        .then(manejarRespuestaJson)
        .then((data) => {
            snEntEstado.entregables = data.entregables || [];
            snEntEstado.resumen = data.resumen || {};
            snEntRender(snEntEstado.entregables, snEntEstado.resumen);
        })
        .catch((error) => snEntMsg(error.message || 'No se pudieron cargar entregables.', 'error'));
}

function snEntCrearMes() {
    const payload = snEntFiltros();
    payload.uds = payload.uds || 'TODAS';
    if (!payload.coordinador) return snEntMsg('Seleccione el coordinador responsable del informe.', 'error');
    mostrarCargando('Creando entregables de Salud y Nutrición...');
    fetch(`${backendUrl}/api/salud-nutricion/entregables/crear-mes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(manejarRespuestaJson)
        .then((data) => {
            ocultarCargando();
            snEntMsg(data.message || 'Entregables creados.', 'success');
            snEntCargar();
        })
        .catch((error) => {
            ocultarCargando();
            snEntMsg(error.message || 'No se pudieron crear entregables.', 'error');
        });
}

function snEntGenerar(id, tipo) {
    mostrarCargando(`Generando ${tipo}...`);
    fetch(`${backendUrl}/api/salud-nutricion/entregables/${id}/${tipo}`, { method: 'POST' })
        .then(manejarRespuestaJson)
        .then((data) => {
            ocultarCargando();
            snEntMsg(data.message || 'Archivo generado.', 'success');
            if (data.archivo?.download_url) {
                setTimeout(() => { window.descargarArchivoAutenticado(`${backendUrl}${data.archivo.download_url}`).catch((error) => snEntMsg(error.message, 'error')); }, 250);
            }
            snEntCargar();
        })
        .catch((error) => {
            ocultarCargando();
            snEntMsg(error.message || `No se pudo generar ${tipo}.`, 'error');
        });
}

function snEntSubirEvidencia(id) {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = '.png,.jpg,.jpeg,.webp,.pdf,.doc,.docx,.xlsx,.xls';
    input.onchange = () => {
        const files = Array.from(input.files || []);
        if (!files.length) return;
        const filtros = snEntFiltros();
        const fd = new FormData();
        files.forEach((f) => fd.append('files', f));
        fd.append('uds', filtros.uds || 'TODAS');
        fd.append('actividad', 'ENTREGABLE_SALUD_NUTRICION');
        fd.append('fecha', new Date().toISOString().slice(0, 10));
        mostrarCargando('Subiendo evidencias...');
        fetch(`${backendUrl}/api/salud-nutricion/entregables/${id}/evidencias`, { method: 'POST', body: fd })
            .then(manejarRespuestaJson)
            .then((data) => {
                ocultarCargando();
                snEntMsg(data.message || 'Evidencias cargadas.', 'success');
                snEntCargar();
            })
            .catch((error) => {
                ocultarCargando();
                snEntMsg(error.message || 'No se pudieron subir evidencias.', 'error');
            });
    };
    input.click();
}

function snEntValidar(id) {
    fetch(`${backendUrl}/api/salud-nutricion/entregables/${id}/validar`, { method: 'POST' })
        .then((response) => response.json().then((data) => ({ ok: response.ok, status: response.status, data })))
        .then(({ ok, data }) => {
            if (ok) {
                snEntMsg(data.message || 'Entregable validado.', 'success');
            } else {
                const pendientes = (data.pendientes || []).join(' · ');
                snEntMsg(pendientes || data.message || data.error || 'Entregable con pendientes.', 'error');
            }
            snEntCargar();
        })
        .catch((error) => snEntMsg(error.message || 'No se pudo validar.', 'error'));
}

function snEntPostArchivo(endpoint, mensaje) {
    const payload = snEntFiltros();
    mostrarCargando(mensaje);
    fetch(`${backendUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(manejarRespuestaJson)
        .then((data) => {
            ocultarCargando();
            snEntMsg(data.message || 'Archivo generado.', 'success');
            if (data.archivo?.download_url) {
                setTimeout(() => { window.descargarArchivoAutenticado(`${backendUrl}${data.archivo.download_url}`).catch((error) => snEntMsg(error.message, 'error')); }, 250);
            }
        })
        .catch((error) => {
            ocultarCargando();
            snEntMsg(error.message || 'No se pudo generar archivo.', 'error');
        });
}

function snEntGenerarMatriz() { snEntPostArchivo('/api/salud-nutricion/entregables/matriz', 'Generando matriz de control...'); }
function snEntGenerarInforme() { snEntPostArchivo('/api/salud-nutricion/entregables/informe', 'Generando informe Word...'); }
function snEntGenerarZip() { snEntPostArchivo('/api/salud-nutricion/entregables/zip', 'Generando paquete ZIP...'); }

window.snEntregablesInit = snEntregablesInit;
window.snEntCrearMes = snEntCrearMes;
window.snEntCargar = snEntCargar;
window.snEntGenerar = snEntGenerar;
window.snEntSubirEvidencia = snEntSubirEvidencia;
window.snEntSubirPlantilla = snEntSubirPlantilla;
window.snEntValidar = snEntValidar;
window.snEntGenerarMatriz = snEntGenerarMatriz;
window.snEntGenerarInforme = snEntGenerarInforme;
window.snEntGenerarZip = snEntGenerarZip;
window.snEntAbrirActividad = snEntAbrirActividad;
window.snEntCerrarActividad = snEntCerrarActividad;
window.snEntGuardarActividad = snEntGuardarActividad;
window.snEntCargarCatalogosMaestros = snEntCargarCatalogosMaestros;
