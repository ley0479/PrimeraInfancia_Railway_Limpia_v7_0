(function () {
    const state = { cruceId: null, resultado: {}, resumen: {}, tipoActual: 'resumen', opcionesInforme: { unidades: [], coordinadores: [], grupos_etarios: [], diagnosticos: [] } };

    function token() {
        if (typeof authToken === 'function') return authToken();
        return localStorage.getItem('primeraInfanciaAuthToken') || localStorage.getItem('token') || '';
    }

    function headersJson() {
        const t = token();
        return t ? { Authorization: `Bearer ${t}`, 'X-Auth-Token': t } : {};
    }

    function setMessage(texto, tipo = 'success') {
        const box = document.getElementById('cb-message');
        if (!box) return;
        box.className = `mt-4 rounded-xl px-4 py-3 text-sm ${tipo === 'success' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'}`;
        box.textContent = texto;
        box.classList.remove('hidden');
    }

    function escape(v) {
        if (typeof escaparHtml === 'function') return escaparHtml(v);
        return String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[c]));
    }


    async function subirLogoCorporacion() {
        const input = document.getElementById('cb-logo-corporacion');
        const file = input?.files?.[0];
        if (!file) {
            setMessage('Selecciona el logo de la corporación en PNG o JPG.', 'error');
            return;
        }
        const form = new FormData();
        form.append('logo', file);
        try {
            const res = await fetch(`${window.backendUrl}/api/corporaciones/logo`, {
                method: 'POST',
                headers: headersJson(),
                body: form
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'No se pudo guardar el logo.');
            setMessage('Logo institucional guardado. Los próximos informes Word/PDF lo usarán en portada y encabezado.', 'success');
            if (input) input.value = '';
        } catch (err) {
            setMessage(err.message, 'error');
        }
    }

    function generarInformeConGraficas(formato = 'docx') {
        generarInforme(formato, { graficas: '1' });
    }

    function generarInformeConAnexos(formato = 'docx') {
        generarInforme(formato, { anexos: '1' });
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value ?? 0;
    }

    function llenarSelect(id, values, placeholder) {
        const el = document.getElementById(id);
        if (!el) return;
        const current = el.value;
        const opts = [`<option value="">${escape(placeholder)}</option>`]
            .concat((values || []).map(v => `<option value="${escape(v)}">${escape(v)}</option>`));
        el.innerHTML = opts.join('');
        if ([...el.options].some(o => o.value === current)) el.value = current;
    }

    function renderOpcionesInforme() {
        const o = state.opcionesInforme || {};
        llenarSelect('cb-informe-unidad', o.unidades || [], 'General - todas las unidades');
        llenarSelect('cb-informe-coordinador', o.coordinadores || [], 'Todos los coordinadores');
        llenarSelect('cb-informe-grupo', o.grupos_etarios || [], 'Todos los grupos etarios');
        llenarSelect('cb-informe-diagnostico', o.diagnosticos || [], 'Todos los diagnósticos');
    }

    async function cargarOpcionesInforme() {
        try {
            const res = await fetch(`${window.backendUrl}/api/cruce-bases/opciones-informe`, { headers: headersJson() });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'No se pudieron cargar las opciones del informe.');
            state.opcionesInforme = data || state.opcionesInforme;
            renderOpcionesInforme();
        } catch (err) {
            console.warn('Opciones informe estadístico:', err.message);
        }
    }

    function filtrosInforme(extra = {}) {
        const params = new URLSearchParams();
        if (state.cruceId) params.set('cruce_id', state.cruceId);
        const unidad = document.getElementById('cb-informe-unidad')?.value || '';
        const coordinador = document.getElementById('cb-informe-coordinador')?.value || '';
        const grupo = document.getElementById('cb-informe-grupo')?.value || '';
        const diagnostico = document.getElementById('cb-informe-diagnostico')?.value || '';
        const alertas = document.getElementById('cb-informe-alertas')?.checked ? '1' : '';
        const faltantes = document.getElementById('cb-informe-faltantes')?.checked ? '1' : '';
        const base = { unidad, coordinador, grupo_etario: grupo, estado_nutricional: diagnostico, alertas, faltantes, ...extra };
        Object.entries(base).forEach(([k, v]) => {
            if (v !== undefined && v !== null && String(v).trim() !== '') params.set(k, v);
        });
        return params.toString();
    }

    function generarInforme(formato = 'docx', extra = {}) {
        if (!state.cruceId) {
            setMessage('Primero ejecuta o carga un cruce mensual para generar el informe.', 'error');
            return;
        }
        const fmt = String(formato || 'docx').toLowerCase() === 'pdf' ? 'pdf' : 'docx';
        const query = filtrosInforme(extra);
        window.descargarArchivoAutenticado(`${window.backendUrl}/api/cruce-bases/informe-estadistico/${fmt}?${query}`).catch((error) => setMessage(error.message, 'error'));
    }

    function generarInformeGeneral(formato = 'docx') {
        limpiarFiltrosInforme(false);
        generarInforme(formato, { alcance: 'general' });
    }

    function generarInformePorUnidad(formato = 'docx') {
        let unidad = document.getElementById('cb-informe-unidad')?.value || '';
        if (!unidad) unidad = prompt('Escribe el nombre exacto de la unidad de servicio para generar el informe:') || '';
        unidad = unidad.trim();
        if (!unidad) {
            setMessage('Selecciona o escribe una unidad de servicio.', 'error');
            return;
        }
        generarInforme(formato, { alcance: 'unidad', unidad });
    }

    function generarInformePorCoordinador(formato = 'docx') {
        let coordinador = document.getElementById('cb-informe-coordinador')?.value || '';
        if (!coordinador) coordinador = prompt('Escribe el nombre del coordinador para generar el informe:') || '';
        coordinador = coordinador.trim();
        if (!coordinador) {
            setMessage('Selecciona o escribe un coordinador.', 'error');
            return;
        }
        generarInforme(formato, { alcance: 'coordinador', coordinador });
    }

    function limpiarFiltrosInforme(showMessage = true) {
        ['cb-informe-unidad', 'cb-informe-coordinador', 'cb-informe-grupo', 'cb-informe-diagnostico'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        ['cb-informe-alertas', 'cb-informe-faltantes'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.checked = false;
        });
        if (showMessage) setMessage('Filtros del informe limpiados. Puedes generar el informe general.', 'success');
    }

    function pintarResumen(resumen = {}) {
        state.resumen = resumen || {};
        setText('cb-stat-anterior', resumen.total_anterior || 0);
        setText('cb-stat-actual', resumen.total_actual || 0);
        setText('cb-stat-nuevos', resumen.nuevos || 0);
        setText('cb-stat-retirados', resumen.retirados || 0);
        setText('cb-stat-reemplazados', resumen.reemplazados || 0);
        setText('cb-stat-trasladados', resumen.trasladados || 0);
        setText('cb-stat-cambios', resumen.cambios_total || resumen.cambios || 0);
    }

    function headersFor(tipo) {
        if (tipo === 'reemplazados') return ['Niño retirado', 'Documento retirado', 'Niño nuevo', 'Documento nuevo', 'Unidad', 'Agente educativo', 'Fecha corte', 'Observación'];
        if (tipo === 'trasladados') return ['Niño', 'Documento', 'Unidad anterior', 'Unidad actual', 'Agente educativo anterior', 'Agente educativo actual'];
        if (tipo === 'cambios') return ['Niño', 'Documento', 'Cambios detectados', 'Unidad actual', 'Agente educativo actual'];
        if ((tipo || '').startsWith('cambios_')) return ['Niño', 'Documento', 'Campo', 'Anterior', 'Actual', 'Unidad', 'Agente educativo'];
        return ['Documento', 'Nombre completo', 'Unidad', 'Agente educativo', 'Acudiente', 'Teléfono', 'Dirección'];
    }

    function rowFor(item, tipo) {
        if (tipo === 'reemplazados') return [item.nombre_retirado, item.documento_retirado, item.nombre_nuevo, item.documento_nuevo, item.unidad, item.docente, item.fecha_corte, item.observacion];
        if (tipo === 'trasladados') return [item.nombre, item.documento, item.unidad_anterior, item.unidad_actual, item.docente_anterior, item.docente_actual];
        if (tipo === 'cambios') return [item.nombre, item.documento, (item.cambios || []).map(c => `${c.campo}: ${c.anterior || ''} → ${c.actual || ''}`).join('; '), item.unidad_actual, item.docente_actual];
        if ((tipo || '').startsWith('cambios_')) return [item.nombre, item.documento, item.campo, item.anterior, item.actual, item.unidad_actual, item.docente_actual];
        return [item.documento, item.nombre, item.unidad, item.docente, item.acudiente, item.telefono, item.direccion];
    }

    function mostrarTabla(tipo, items) {
        state.tipoActual = tipo;
        const head = document.getElementById('cb-detalle-head');
        const body = document.getElementById('cb-detalle-body');
        const title = document.getElementById('cb-detalle-titulo');
        const sub = document.getElementById('cb-detalle-subtitulo');
        if (!head || !body) return;
        const headers = headersFor(tipo);
        head.innerHTML = `<tr>${headers.map(h => `<th class="px-4 py-3">${escape(h)}</th>`).join('')}</tr>`;
        if (title) title.textContent = tipo === 'resumen' ? 'Resumen general del cruce' : `Detalle: ${tipo.replaceAll('_', ' ')}`;
        if (sub) sub.textContent = `${items.length} registro(s) encontrados.`;
        if (!items.length) {
            body.innerHTML = `<tr><td colspan="${headers.length}" class="px-4 py-6 text-center text-slate-500">No hay registros para mostrar.</td></tr>`;
            return;
        }
        body.innerHTML = items.slice(0, 500).map(item => {
            const row = rowFor(item, tipo);
            return `<tr>${row.map(v => `<td class="px-4 py-3">${escape(v || '')}</td>`).join('')}</tr>`;
        }).join('');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function mostrarResumenTabla() {
        const resumen = state.resumen || {};
        const items = Object.entries(resumen).map(([k, v]) => ({ documento: '', nombre: k.replaceAll('_', ' ').toUpperCase(), unidad: v, docente: '', acudiente: '', telefono: '', direccion: '' }));
        mostrarTabla('resumen', items);
    }

    async function cargarUltimoCruce() {
        try {
            const res = await fetch(`${window.backendUrl}/api/cruce-bases/ultimo`, { headers: headersJson() });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'No se pudo cargar el último cruce.');
            state.cruceId = data.cruce?.id || null;
            state.resultado = data.resultado || {};
            state.resumen = data.resultado?.resumen || data.resumen || {};
            pintarResumen(state.resumen);
            if (state.cruceId) mostrarResumenTabla();
            cargarOpcionesInforme();
        } catch (err) {
            console.warn('Cruce bases:', err.message);
        }
    }

    async function ejecutarCruce() {
        const anterior = document.getElementById('cb-base-anterior')?.files?.[0];
        const actual = document.getElementById('cb-base-actual')?.files?.[0];
        if (!anterior || !actual) {
            setMessage('Selecciona base anterior y base actual.', 'error');
            return;
        }
        const form = new FormData();
        form.append('base_anterior', anterior);
        form.append('base_actual', actual);
        form.append('mes', document.getElementById('cb-mes')?.value || new Date().getMonth() + 1);
        form.append('anio', document.getElementById('cb-anio')?.value || new Date().getFullYear());
        try {
            if (typeof mostrarCargando === 'function') mostrarCargando('Comparando base anterior y base actual. Espera mientras se generan reportes.');
            const res = await fetch(`${window.backendUrl}/api/cruce-bases/comparar`, {
                method: 'POST',
                headers: headersJson(),
                body: form
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'No se pudo ejecutar el cruce.');
            state.cruceId = data.cruce_id;
            state.resultado = data.resultado || {};
            state.resumen = data.resumen || state.resultado.resumen || {};
            pintarResumen(state.resumen);
            mostrarResumenTabla();
            setMessage(data.message || 'Cruce generado correctamente.', 'success');
            cargarOpcionesInforme();
        } catch (err) {
            setMessage(err.message || 'Error en el cruce de bases.', 'error');
        } finally {
            if (typeof ocultarCargando === 'function') ocultarCargando();
        }
    }

    async function mostrarDetalle(tipo) {
        if (tipo === 'resumen') return mostrarResumenTabla();
        let items = state.resultado?.[tipo];
        if (!items && state.cruceId) {
            try {
                const res = await fetch(`${window.backendUrl}/api/cruce-bases/detalle/${encodeURIComponent(tipo)}?cruce_id=${state.cruceId}`, { headers: headersJson() });
                const data = await res.json();
                if (res.ok) items = data.items || [];
            } catch (_) {}
        }
        mostrarTabla(tipo, items || []);
    }

    function descargarCruce(tipo = 'resumen', formato = 'excel') {
        if (!state.cruceId) {
            setMessage('Primero ejecuta o carga un cruce mensual.', 'error');
            return;
        }
        window.descargarArchivoAutenticado(`${window.backendUrl}/api/cruce-bases/descargar/${state.cruceId}/${encodeURIComponent(tipo)}/${encodeURIComponent(formato)}`).catch((error) => setMessage(error.message, 'error'));
    }

    function descargarUsuariosUnidad(unidad, formato = 'excel') {
        const mes = document.getElementById('cb-mes')?.value || new Date().getMonth() + 1;
        const anio = document.getElementById('cb-anio')?.value || new Date().getFullYear();
        const query = new URLSearchParams({ mes: String(mes), anio: String(anio) });
        window.descargarArchivoAutenticado(`${window.backendUrl}/api/cruce-bases/usuarios-unidad/${encodeURIComponent(unidad)}/${encodeURIComponent(formato)}?${query}`).catch((error) => setMessage(error.message, 'error'));
    }

    function imprimirUsuariosUnidad(unidad) {
        const mes = document.getElementById('cb-mes')?.value || new Date().getMonth() + 1;
        const anio = document.getElementById('cb-anio')?.value || new Date().getFullYear();
        const query = new URLSearchParams({ mes: String(mes), anio: String(anio) });
        window.abrirArchivoAutenticado(`${window.backendUrl}/api/cruce-bases/usuarios-unidad/${encodeURIComponent(unidad)}/imprimir?${query}`).catch((error) => setMessage(error.message, 'error'));
    }

    function docentePorUnidad(unidad) {
        const data = window.estadoDiagnostico?.unidades?.[unidad] || {};
        return data.docente_asignado || 'Sin agente educativo asignado';
    }

    function init() {
        const mes = document.getElementById('cb-mes');
        const anio = document.getElementById('cb-anio');
        if (mes) mes.value = String(new Date().getMonth() + 1);
        if (anio) anio.value = String(new Date().getFullYear());
        if (document.getElementById('cruce-bases-panel')) {
            cargarUltimoCruce();
            cargarOpcionesInforme();
        }
    }

    window.CruceBases = { init, ejecutarCruce, cargarUltimoCruce, mostrarDetalle, descargarCruce, descargarUsuariosUnidad, imprimirUsuariosUnidad, docentePorUnidad, cargarOpcionesInforme, generarInforme, generarInformeGeneral, generarInformePorUnidad, generarInformePorCoordinador, generarInformeConGraficas, generarInformeConAnexos, subirLogoCorporacion, limpiarFiltrosInforme, get tipoActual() { return state.tipoActual; } };
    document.addEventListener('DOMContentLoaded', init);
})();
