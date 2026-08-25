// Alpha15: Calendario Inteligente de Entregables y Alertas Operativas.
// Módulo aislado: no modifica plantillas oficiales ni impresión de formatos.
(function () {
    const apiBase = () => window.backendUrl || window.getBackendUrl?.() || window.getConfiguredBackendUrl?.() || window.location.origin;
    const API = `${apiBase()}/api/calendario-inteligente`;
    const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
    const DIAS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
    const state = {
        periodo: new Date().toISOString().slice(0, 7),
        anio: String(new Date().getFullYear()),
        vista: 'mes',
        dashboard: null,
        misPendientes: [],
        checklist: { asignaciones: [], resumen: {} }, checklistImport: null, cumplimiento: {por_uds:[]},
        filtros: {},
        selectedDate: null,
        weekAnchor: new Date().toISOString().slice(0, 10),
        previewCronograma: null,
    };

    function api(path, options = {}) {
        return fetch(`${API}${path}`, options).then((resp) => {
            if (typeof manejarRespuestaJson === 'function') return manejarRespuestaJson(resp);
            return resp.json().then((json) => { if (!resp.ok) throw new Error(json.error || 'Error de calendario'); return json; });
        });
    }

    function apiJob(jobId) {
        const token = typeof authToken === 'function' ? authToken() : '';
        return fetch(`${apiBase()}/api/jobs/${encodeURIComponent(jobId)}`, {
            headers: {
                'Authorization': token ? `Bearer ${token}` : '',
                'X-Auth-Token': token || '',
                'X-Requested-With': 'XMLHttpRequest'
            }
        }).then((resp) => {
            if (typeof manejarRespuestaJson === 'function') return manejarRespuestaJson(resp);
            return resp.json().then((json) => { if (!resp.ok) throw new Error(json.error || 'Error consultando trabajo'); return json; });
        });
    }

    function esperarJobCalendario(jobId) {
        let intentos = 0;
        const maxIntentos = 180;
        const tick = async () => {
            intentos += 1;
            try {
                const data = await apiJob(jobId);
                const job = data.job || data;
                const progreso = Math.round(Number(job.progreso || 0));
                message(`${job.etapa || 'Procesando cronograma'} (${progreso}%)`);
                if (job.estado === 'completado') {
                    const r = job.resultado?.resultado || job.resultado || {};
                    message(`Cronograma procesado: ${r.creados || 0} creados, ${r.duplicados || 0} duplicados, ${r.errores?.length || 0} errores.`);
                    await cargarDashboard();
                    return;
                }
                if (job.estado === 'error') {
                    message(job.error || 'No se pudo procesar el cronograma.', 'error');
                    return;
                }
                if (intentos < maxIntentos) setTimeout(tick, 3000);
                else message('El cronograma sigue tardando demasiado. Revisa los logs del backend.', 'error');
            } catch (err) {
                if (intentos < maxIntentos) setTimeout(tick, 3000);
                else message(err.message || 'No se pudo consultar el avance del cronograma.', 'error');
            }
        };
        tick();
    }

    function esc(v) {
        return typeof escaparHtml === 'function' ? escaparHtml(v) : String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
    }

    function injectNavAndSection() {
        const nav = document.querySelector('aside nav');
        if (nav && !document.getElementById('nav-calendario-inteligente')) {
            const btn = document.createElement('button');
            btn.id = 'nav-calendario-inteligente';
            btn.onclick = () => window.mostrarSeccion ? mostrarSeccion('calendario-inteligente') : null;
            btn.className = 'w-full text-left flex items-center gap-3 px-4 py-3 text-slate-400 hover:bg-slate-900 hover:text-slate-200 rounded-xl transition';
            btn.innerHTML = '<i data-lucide="calendar-days"></i> Calendario Inteligente <span class="ml-auto rounded-full bg-rose-500/20 px-2 py-0.5 text-[10px] text-rose-300">Alertas</span>';
            const dashboard = document.getElementById('nav-dashboard');
            dashboard?.insertAdjacentElement('afterend', btn) || nav.prepend(btn);
        }
        // El contenedor principal cambia de clases según la versión visual.
        // El padre del dashboard es el anclaje estable compartido por todas
        // las secciones de la SPA.
        const main = document.getElementById('dashboard')?.parentElement
            || document.querySelector('main > div[class*="space-y-"]');
        if (main && !document.getElementById('calendario-inteligente')) {
            main.insertAdjacentHTML('beforeend', calendarSectionHtml());
        }
    }

    function calendarSectionHtml() {
        return `
        <section id="calendario-inteligente" class="hidden space-y-6">
            <div class="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
                <div class="flex items-start gap-4">
                    <div class="ci-title-icon"><i data-lucide="calendar-clock" class="w-8 h-8"></i></div>
                    <div>
                        <h2 class="text-3xl font-bold text-slate-100">Calendario Inteligente de Entregables</h2>
                        <p class="text-slate-400 mt-1">Control de actividades, fechas de entrega, evidencias y alertas operativas sincronizadas con la plataforma.</p>
                    </div>
                </div>
                <div class="flex flex-wrap gap-2">
                    <button data-help-id="calendario.activity.create" onclick="ciAbrirModalNuevo()" class="ci-btn ci-btn-primary"><i data-lucide="plus" class="w-4 h-4"></i> Nuevo entregable</button>
                    <label data-help-id="calendario.schedule.upload" class="ci-btn ci-btn-muted cursor-pointer"><i data-lucide="upload" class="w-4 h-4"></i> Cargar cronograma<input id="ci-cronograma-file" type="file" accept=".xlsx,.xls,.xlsm,.ods,.csv,.txt,.tsv,.tab,.dat,.docx,.pdf,.pptx,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff" class="hidden" onchange="ciCargarCronograma()"></label><button onclick="ciExportarExcel()" class="ci-btn ci-btn-muted"><i data-lucide="file-spreadsheet" class="w-4 h-4"></i> Exportar Excel</button><button onclick="ciExportarPdf()" class="ci-btn ci-btn-muted"><i data-lucide="file-text" class="w-4 h-4"></i> Exportar PDF</button>
                </div>
            </div>
            <div id="ci-message" class="hidden rounded-xl px-4 py-3 text-sm"></div>
            <div class="ci-panel ci-help-panel">
                <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                    <div>
                        <h3 class="font-semibold text-slate-100 flex items-center gap-2"><i data-lucide="scan-text" class="w-4 h-4 text-cyan-300"></i> Carga inteligente de cronograma mensual</h3>
                        <p class="text-sm text-slate-400 mt-1">Sube Excel, PDF, Word o imagen. El sistema detecta fechas y actividades, pero siempre muestra una vista previa editable antes de guardar.</p>
                    </div>
                    <span class="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs text-cyan-200">Revisar antes de guardar</span>
                </div>
            </div>
            <div class="grid gap-4 xl:grid-cols-5">
                <div class="ci-metric"><div class="flex items-center gap-3"><i data-lucide="calendar-check" class="text-blue-300"></i><p class="text-sm text-slate-400">Entregables del mes</p></div><p id="ci-stat-total" class="text-3xl font-bold mt-3">0</p><p class="text-xs text-slate-500 mt-1">Total programados</p></div>
                <div class="ci-metric"><div class="flex items-center gap-3"><i data-lucide="clock" class="text-yellow-300"></i><p class="text-sm text-yellow-200">Próximos a vencer</p></div><p id="ci-stat-proximos" class="text-3xl font-bold mt-3 text-yellow-300">0</p><p class="text-xs text-slate-500 mt-1">Amarillo/naranja</p></div>
                <div class="ci-metric"><div class="flex items-center gap-3"><i data-lucide="triangle-alert" class="text-red-300"></i><p class="text-sm text-red-200">Vencidos</p></div><p id="ci-stat-vencidos" class="text-3xl font-bold mt-3 text-red-300">0</p><p class="text-xs text-slate-500 mt-1">Requieren atención</p></div>
                <div class="ci-metric"><div class="flex items-center gap-3"><i data-lucide="circle-check" class="text-green-300"></i><p class="text-sm text-green-200">Entregados</p></div><p id="ci-stat-entregados" class="text-3xl font-bold mt-3 text-green-300">0</p><p class="text-xs text-slate-500 mt-1">Completados</p></div>
                <div class="ci-metric"><div class="flex items-center gap-3"><i data-lucide="percent" class="text-cyan-300"></i><p class="text-sm text-slate-400">Cumplimiento</p></div><p id="ci-stat-cumplimiento" class="text-3xl font-bold mt-3 text-cyan-300">0%</p><p class="text-xs text-slate-500 mt-1">Del mes</p></div>
            </div>
            <div class="ci-panel">
                <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                    <div><h3 class="font-semibold text-slate-100 flex items-center gap-2"><i data-lucide="clipboard-check" class="w-5 h-5 text-emerald-300"></i> Lista de chequeo institucional</h3><p id="ci-checklist-summary" class="text-sm text-slate-400 mt-1">Sin obligaciones para el periodo.</p></div>
                    <div class="flex flex-wrap gap-2"><label class="ci-btn ci-btn-success cursor-pointer"><i data-lucide="scan-text" class="w-4 h-4"></i> Importar checklist<input id="ci-checklist-file" type="file" accept=".xlsx,.xls,.docx,.pdf,.pptx" class="hidden" onchange="ciImportarChecklist()"></label><button onclick="ciNuevaObligacion()" class="ci-btn ci-btn-primary"><i data-lucide="plus" class="w-4 h-4"></i> Nueva obligación</button></div>
                </div>
                <div id="ci-checklist-list" class="ci-checklist-list mt-4"></div>
                <div id="ci-compliance-board" class="mt-5"></div>
            </div>
            <div class="ci-panel">
                <div class="grid gap-3 md:grid-cols-6">
                    <div><label class="text-xs text-slate-400">Mes</label><input id="ci-periodo" type="month" class="ci-input" onchange="ciSetPeriodo(this.value)"></div>
                    <div><label class="text-xs text-slate-400">Año</label><input id="ci-anio" type="number" min="2020" max="2100" class="ci-input" onchange="ciSetAnio(this.value)"></div>
                    <div><label class="text-xs text-slate-400">Coordinador</label><select id="ci-filtro-coordinador" class="ci-input" onchange="ciAplicarFiltros()"><option value="">Todos</option></select></div>
                    <div><label class="text-xs text-slate-400">Unidad/UDS</label><select id="ci-filtro-unidad" class="ci-input" onchange="ciAplicarFiltros()"><option value="">Todas</option></select></div>
                    <div><label class="text-xs text-slate-400">Módulo</label><select id="ci-filtro-modulo" class="ci-input" onchange="ciAplicarFiltros()"><option value="">Todos</option></select></div>
                    <div><label class="text-xs text-slate-400">Estado</label><select id="ci-filtro-estado" class="ci-input" onchange="ciAplicarFiltros()"><option value="">Todos</option></select></div>
                </div>
                <div class="mt-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                    <button onclick="ciLimpiarFiltros()" class="ci-btn ci-btn-muted"><i data-lucide="rotate-ccw" class="w-4 h-4"></i> Limpiar filtros</button>
                    <div class="ci-view-toggle">
                        <button id="ci-vista-mes" data-help-id="calendario.view.month" onclick="ciCambiarVista('mes')" class="ci-active">Mes</button>
                        <button id="ci-vista-semana" onclick="ciCambiarVista('semana')">Semana</button>
                        <button id="ci-vista-anio" onclick="ciCambiarVista('anio')">Año</button>
                        <button id="ci-vista-agenda" onclick="ciCambiarVista('agenda')">Agenda</button>
                    </div>
                </div>
            </div>
            <div class="grid gap-5 xl:grid-cols-[1fr_360px]">
                <div class="ci-panel">
                    <div class="flex items-center justify-between gap-3 mb-4">
                        <button onclick="ciMoverMes(-1)" class="ci-btn ci-btn-muted"><i data-lucide="chevron-left" class="w-4 h-4"></i></button>
                        <h3 id="ci-cal-title" class="text-2xl font-bold text-center">Mes</h3>
                        <button onclick="ciMoverMes(1)" class="ci-btn ci-btn-muted"><i data-lucide="chevron-right" class="w-4 h-4"></i></button>
                    </div>
                    <div id="ci-view-container"></div>
                </div>
                <aside class="space-y-4">
                    <div class="ci-panel">
                        <h3 class="font-semibold text-slate-100 flex items-center gap-2"><i data-lucide="bell-ring" class="w-4 h-4 text-amber-300"></i> Pendientes y alertas</h3>
                        <div id="ci-alertas-list" data-help-id="calendario.alerts.list" class="mt-3 space-y-2"></div>
                    </div>
                    <div class="ci-panel">
                        <h3 class="font-semibold text-slate-100 flex items-center gap-2"><i data-lucide="list-checks" class="w-4 h-4 text-cyan-300"></i> Mis pendientes</h3>
                        <div id="ci-mis-pendientes" data-help-id="calendario.pending.list" class="mt-3 space-y-2"></div>
                    </div>
                    <div class="ci-panel">
                        <h3 class="font-semibold text-slate-100 mb-3">Leyenda de estados</h3>
                        <div class="grid grid-cols-2 gap-2 text-xs text-slate-300">
                            ${legendItem('azul', 'Programado')}${legendItem('verde', 'Entregado')}${legendItem('amarillo', 'Próximo')}${legendItem('naranja', 'Vence pronto')}${legendItem('rojo', 'Vencido/Hoy')}${legendItem('gris', 'Cerrado')}
                        </div>
                    </div>
                    <div class="ci-panel">
                        <h3 class="font-semibold text-slate-100 mb-3">Cumplimiento por coordinador</h3>
                        <div id="ci-cumplimiento-coordinador" class="space-y-3"></div>
                    </div>
                </aside>
            </div>
        </section>`;
    }

    function legendItem(color, label) { return `<div class="flex items-center gap-2"><span class="ci-dot ci-${color}"></span>${label}</div>`; }

    function message(text, type = 'success') {
        const el = document.getElementById('ci-message');
        if (!el) return;
        el.className = `rounded-xl px-4 py-3 text-sm ${type === 'success' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'}`;
        el.textContent = text;
        el.classList.remove('hidden');
    }

    async function init() {
        injectNavAndSection();
        const section = document.getElementById('calendario-inteligente');
        if (section && window.location.hash === '#calendario-inteligente') section.classList.remove('hidden');
        const periodo = document.getElementById('ci-periodo');
        const anio = document.getElementById('ci-anio');
        if (periodo && !periodo.value) periodo.value = state.periodo;
        if (anio && !anio.value) anio.value = state.anio;
        try {
            await cargarDashboard();
        } catch (error) {
            message(error?.message || 'No se pudo cargar la información del calendario. Recarga o inicia sesión nuevamente.', 'error');
            const container = document.getElementById('ci-view-container');
            if (container) container.innerHTML = '<div class="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-center text-rose-200">El calendario está visible, pero sus datos no pudieron cargarse. Revisa el mensaje superior o vuelve a iniciar sesión.</div>';
        }
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    async function cargarDashboard() {
        const qs = new URLSearchParams({ periodo: state.periodo, anio: state.anio, ...state.filtros });
        const data = await api(`/dashboard?${qs.toString()}`);
        state.dashboard = data;
        try {
            const personal = await api('/mis-pendientes');
            state.misPendientes = personal.pendientes || [];
        } catch (_) {
            state.misPendientes = [];
        }
        try {
            state.checklist = await api(`/checklist?periodo=${encodeURIComponent(state.periodo)}`);
        } catch (_) {
            state.checklist = { asignaciones: [], resumen: {} };
        }
        try { state.cumplimiento = await api(`/cumplimiento?periodo=${encodeURIComponent(state.periodo)}`); } catch (_) { state.cumplimiento={por_uds:[]}; }
        renderStats(data.resumen || {});
        renderCatalogos(data.catalogos || {});
        renderVista();
        renderAlertas(data.alertas || []);
        renderMisPendientes();
        renderChecklist();
        renderComplianceBoard();
        renderCumplimiento(data.cumplimiento_coordinador || []);
        renderDashboardWidget(data.resumen || {}, data.alertas || []);
    }

    function renderStats(r) {
        setText('ci-stat-total', r.entregables_mes || 0);
        setText('ci-stat-proximos', r.proximos || 0);
        setText('ci-stat-vencidos', r.vencidos || 0);
        setText('ci-stat-entregados', r.entregados || 0);
        setText('ci-stat-cumplimiento', `${r.cumplimiento_general || 0}%`);
    }
    function setText(id, value) { const el = document.getElementById(id); if (el) el.textContent = value; }

    function renderCatalogos(c) {
        fillSelect('ci-filtro-modulo', c.modulos || [], 'Todos');
        fillSelect('ci-filtro-estado', c.estados || [], 'Todos');
        fillSelect('ci-filtro-coordinador', c.coordinadores || [], 'Todos');
        fillSelect('ci-filtro-unidad', c.unidades || [], 'Todas');
    }
    function fillSelect(id, items, first) {
        const el = document.getElementById(id); if (!el) return;
        const prev = el.value;
        el.innerHTML = `<option value="">${first}</option>` + (items || []).map(x => `<option value="${esc(x)}">${esc(x)}</option>`).join('');
        if ([...el.options].some(o => o.value === prev)) el.value = prev;
    }

    function eventos() { return state.dashboard?.eventos || []; }
    function annual() { return state.dashboard?.annual || []; }

    function renderVista() {
        document.querySelectorAll('#ci-vista-mes,#ci-vista-semana,#ci-vista-anio,#ci-vista-agenda').forEach(b => b?.classList.remove('ci-active'));
        document.getElementById(`ci-vista-${state.vista}`)?.classList.add('ci-active');
        if (state.vista === 'mes') renderMes();
        if (state.vista === 'semana') renderSemana();
        if (state.vista === 'anio') renderAnio();
        if (state.vista === 'agenda') renderAgenda();
    }

    function isoLocal(value) {
        const d = new Date(value);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    }

    function inicioSemana(iso) {
        const d = new Date(`${iso}T12:00:00`);
        const offset = (d.getDay() + 6) % 7;
        d.setDate(d.getDate() - offset);
        return d;
    }

    function renderSemana() {
        const start = inicioSemana(state.weekAnchor || `${state.periodo}-01`);
        const end = new Date(start); end.setDate(end.getDate() + 6);
        setText('ci-cal-title', `Semana ${isoLocal(start)} al ${isoLocal(end)}`);
        const allEvents = annual().length ? annual() : eventos();
        const byDate = groupBy(allEvents, e => e.fecha_limite);
        const today = new Date().toISOString().slice(0, 10);
        const columns = [];
        for (let i = 0; i < 7; i++) {
            const day = new Date(start); day.setDate(start.getDate() + i);
            const iso = isoLocal(day), evs = byDate[iso] || [];
            columns.push(`<section class="ci-week-column ${iso === today ? 'ci-week-today' : ''}">
                <button class="ci-week-heading" onclick="ciAbrirDia('${iso}')"><strong>${DIAS[day.getDay()]}</strong><span>${day.getDate()}</span></button>
                <div class="ci-week-events">${evs.length ? evs.map(e => `<button onclick="ciAbrirEntregable(${Number(e.id)})" class="ci-week-event ci-${e.color || e.color_calculado || 'azul'}"><strong>${esc(e.titulo || e.modulo || '')}</strong><span>${esc(e.responsable_nombre || e.unidad || '')}</span></button>`).join('') : '<p>Sin actividades</p>'}</div>
            </section>`);
        }
        document.getElementById('ci-view-container').innerHTML = `<div class="ci-week-grid">${columns.join('')}</div>`;
    }

    function renderMes() {
        const [year, month] = state.periodo.split('-').map(Number);
        const first = new Date(year, month - 1, 1);
        const last = new Date(year, month, 0);
        setText('ci-cal-title', `${MESES[month - 1]} ${year}`);
        const byDate = groupBy(eventos(), e => e.fecha_limite);
        const cells = [];
        DIAS.forEach(d => cells.push(`<div class="ci-weekday">${d}</div>`));
        const prevLast = new Date(year, month - 1, 0).getDate();
        for (let i = 0; i < first.getDay(); i++) {
            cells.push(`<div class="ci-day ci-day-muted"><span class="ci-day-number">${prevLast - first.getDay() + i + 1}</span></div>`);
        }
        const today = new Date().toISOString().slice(0, 10);
        for (let d = 1; d <= last.getDate(); d++) {
            const iso = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
            const evs = byDate[iso] || [];
            cells.push(`<div class="ci-day ${today === iso ? 'ci-day-today' : ''}" onclick="ciAbrirDia('${iso}')">
                <div class="flex items-center justify-between"><span class="ci-day-number">${d}</span>${evs.length ? `<span class="text-xs text-slate-400">${evs.length}</span>` : ''}</div>
                ${evs.slice(0, 3).map(e => `<div class="ci-event-pill ci-${e.color || e.color_calculado || 'azul'}">${esc(e.titulo || e.modulo)}</div>`).join('')}
                ${evs.length > 3 ? `<div class="text-[11px] text-slate-500 mt-1">+${evs.length - 3} más</div>` : ''}
            </div>`);
        }
        const totalBody = first.getDay() + last.getDate();
        for (let i = 1; i <= (7 - (totalBody % 7 || 7)); i++) {
            cells.push(`<div class="ci-day ci-day-muted"><span class="ci-day-number">${i}</span></div>`);
        }
        document.getElementById('ci-view-container').innerHTML = `<div class="ci-calendar-grid">${cells.join('')}</div>`;
    }

    function renderAnio() {
        const year = Number(state.anio || new Date().getFullYear());
        setText('ci-cal-title', `Vista anual ${year}`);
        const byDate = groupBy(annual(), e => e.fecha_limite);
        let html = '<div class="ci-annual-grid">';
        for (let m = 1; m <= 12; m++) {
            const first = new Date(year, m - 1, 1), last = new Date(year, m, 0);
            let days = DIAS.map(d => `<div class="text-slate-500 font-bold">${d[0]}</div>`).join('');
            for (let i = 0; i < first.getDay(); i++) days += '<div></div>';
            for (let d = 1; d <= last.getDate(); d++) {
                const iso = `${year}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
                const evs = byDate[iso] || [];
                const color = evs.some(e => (e.color || e.color_calculado) === 'rojo') ? 'rojo' : evs.some(e => (e.color || e.color_calculado) === 'naranja') ? 'naranja' : evs.some(e => (e.color || e.color_calculado) === 'amarillo') ? 'amarillo' : evs.some(e => (e.color || e.color_calculado) === 'verde') ? 'verde' : evs.length ? 'azul' : '';
                days += `<button class="ci-mini-day ${evs.length ? `has-event ci-${color}` : ''}" onclick="ciAbrirDia('${iso}')">${d}</button>`;
            }
            html += `<div class="ci-mini-month"><div class="ci-mini-title">${MESES[m - 1]}</div><div class="ci-mini-grid">${days}</div></div>`;
        }
        html += '</div>';
        document.getElementById('ci-view-container').innerHTML = html;
    }

    function renderAgenda() {
        setText('ci-cal-title', `Agenda ${state.periodo}`);
        const groups = groupBy(eventos(), e => e.fecha_limite || 'Sin fecha');
        const html = Object.keys(groups).sort().map(fecha => `<section class="ci-agenda-day">
            <button onclick="ciAbrirDia('${esc(fecha)}')" class="ci-agenda-date"><i data-lucide="calendar-day" class="w-4 h-4"></i>${esc(fecha)}</button>
            <div>${groups[fecha].map(e => `<button onclick="ciAbrirEntregable(${Number(e.id)})" class="ci-agenda-item"><span class="ci-dot ci-${e.color || e.color_calculado || 'azul'}"></span><span><strong>${esc(e.titulo || '')}</strong><small>${esc(e.modulo || '')} · ${esc(e.responsable_nombre || e.unidad || 'Sin asignar')}</small></span><em>${esc(e.estado || '')}</em></button>`).join('')}</div>
        </section>`).join('') || '<p class="py-8 text-center text-slate-500">Sin actividades para el filtro seleccionado.</p>';
        document.getElementById('ci-view-container').innerHTML = `<div class="ci-agenda">${html}</div>`;
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function renderAlertas(alertas) {
        const cont = document.getElementById('ci-alertas-list'); if (!cont) return;
        cont.innerHTML = alertas.length ? alertas.slice(0, 7).map(a => `<button onclick="ciAbrirEntregable(${Number(a.id)})" class="w-full text-left rounded-xl border ci-${a.nivel || 'azul'} p-3 text-xs"><strong>${esc(a.fecha_limite || '')}</strong><br>${esc(a.mensaje || '')}</button>`).join('') : '<p class="text-sm text-slate-500">Sin alertas críticas para el periodo.</p>';
    }

    function renderMisPendientes() {
        const cont = document.getElementById('ci-mis-pendientes'); if (!cont) return;
        const rows = state.misPendientes || [];
        cont.innerHTML = rows.length ? rows.slice(0, 7).map(e => `<button onclick="ciAbrirEntregable(${Number(e.id)})" class="ci-personal-pending"><span class="ci-dot ci-${e.color || e.color_calculado || 'azul'}"></span><span><strong>${esc(e.titulo || '')}</strong><small>${esc(e.fecha_limite || '')} · ${esc(e.unidad || e.modulo || '')}</small></span></button>`).join('') : '<p class="text-sm text-slate-500">No tienes entregables pendientes asignados.</p>';
    }

    function renderChecklist() {
        const box = document.getElementById('ci-checklist-list'); if (!box) return;
        const data = state.checklist || {}, summary = data.resumen || {}, rows = data.asignaciones || [];
        setText('ci-checklist-summary', `${summary.aprobadas || 0}/${summary.exigibles || 0} exigibles aprobadas · ${summary.no_aplica || 0} no aplica · ${summary.cumplimiento || 0}%`);
        box.innerHTML = rows.length ? rows.map(item => {
            const o = item.obligacion || {}, reqs = item.requisitos || [];
            const hasAttendance=reqs.some(r=>/ram|asistencia|listado/i.test(String(r.nombre||'')));
            return `<article class="ci-checklist-card"><div class="ci-checklist-head"><div><small>${esc(o.componente || '')} ${o.numero ? `· ${esc(o.numero)}` : ''}</small><strong>${esc(o.titulo || '')}</strong><span>${esc(item.unidad || 'Todas las UDS')} · ${esc(item.responsable_rol || item.responsable_nombre || 'Sin asignar')}</span></div><span class="ci-list-status ci-${item.estado === 'APROBADO' ? 'verde' : item.estado === 'NO_APLICA' ? 'gris' : item.estado === 'DEVUELTO' ? 'rojo' : 'azul'}">${esc(item.estado || '')}</span></div><div class="ci-checklist-reqs">${reqs.map(r => `<span><i data-lucide="square-check" class="w-3 h-3"></i>${esc(r.nombre)}${r.obligatorio ? '' : ' (opcional)'}</span>`).join('')}</div>${item.fecha_estado==='PENDIENTE_ASIGNACION'?'<p class="text-xs text-amber-300 mt-2">FECHA PENDIENTE DE ASIGNACIÓN</p>':''}${item.justificacion_no_aplica ? `<p class="text-xs text-slate-400 mt-2">No aplica: ${esc(item.justificacion_no_aplica)}</p>` : ''}<div class="flex flex-wrap gap-2 mt-3">${hasAttendance&&item.unidad?`<button onclick="ciGenerarRAM('${esc(item.unidad)}','${esc(item.periodo)}')" class="ci-btn ci-btn-primary"><i data-lucide="download" class="w-4 h-4"></i> Generar listado RAM</button>`:''}<button onclick="ciAbrirEvidencias('CHECKLIST',${Number(item.id)})" class="ci-btn ci-btn-success"><i data-lucide="paperclip" class="w-4 h-4"></i> Evidencias</button><button onclick="ciEstadoChecklist(${Number(item.id)},'EN_PROGRESO')" class="ci-btn ci-btn-muted">En progreso</button><button onclick="ciNoAplica(${Number(item.id)})" class="ci-btn ci-btn-muted">No aplica</button></div></article>`;
        }).join('') : '<p class="text-sm text-slate-500">No hay obligaciones asignadas para este mes.</p>';
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }
    function renderComplianceBoard() { const box=document.getElementById('ci-compliance-board'); if(!box)return; const data=state.cumplimiento||{},rows=data.por_uds||[]; box.innerHTML=`<h4 class="font-semibold text-slate-100 mb-2">Cumplimiento por UDS</h4><p class="text-xs text-slate-400 mb-3">Aprobadas ÷ exigibles; NO APLICA justificado se excluye.</p>${rows.length?`<div class="ci-preview-table-wrap"><table class="ci-preview-table"><thead><tr><th>UDS/UCA</th><th>Aprobadas</th><th>Exigibles</th><th>No aplica</th><th>%</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.nombre)}</td><td>${Number(r.aprobadas)}</td><td>${Number(r.exigibles)}</td><td>${Number(r.no_aplica)}</td><td><strong>${Number(r.cumplimiento)}%</strong></td></tr>`).join('')}</tbody></table></div>`:'<p class="text-sm text-slate-500">Sin datos de cumplimiento para este periodo.</p>'}`; }

    function nuevaObligacion() {
        openModal('Nueva obligación institucional', `<div class="grid gap-3 md:grid-cols-2"><input id="ci-ob-componente" class="ci-input" placeholder="Componente"><input id="ci-ob-numero" class="ci-input" placeholder="Número"><input id="ci-ob-titulo" class="ci-input md:col-span-2" placeholder="Actividad u obligación"><input id="ci-ob-unidad" class="ci-input" placeholder="UDS/UCA"><select id="ci-ob-rol" class="ci-input"><option value="">Rol responsable</option><option>DOCENTE</option><option>COORDINADOR</option><option>PSICOSOCIAL</option><option>NUTRICIONISTA</option><option>AUXILIAR_ENFERMERIA</option></select><textarea id="ci-ob-requisitos" class="ci-input md:col-span-2" placeholder="Un requisito por línea: Acta, Listado, Fotografías..."></textarea></div><button onclick="ciCrearObligacion()" class="ci-btn ci-btn-primary mt-4">Crear obligación</button>`);
    }

    async function crearObligacion() {
        const requirements = (document.getElementById('ci-ob-requisitos')?.value || '').split(/\n+/).map(x => x.trim()).filter(Boolean).map(nombre => ({ nombre, tipo: 'EVIDENCIA', obligatorio: true }));
        const payload = { componente: val('ci-ob-componente'), numero: val('ci-ob-numero'), titulo: val('ci-ob-titulo'), unidad: val('ci-ob-unidad'), responsable_rol: val('ci-ob-rol'), periodo: state.periodo, requisitos: requirements };
        await api('/checklist', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        closeModal(); message('Obligación institucional creada.'); await cargarDashboard();
    }

    async function estadoChecklist(id, estado, motivo = '') {
        await api(`/checklist/${id}/estado`, { method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ estado, motivo }) });
        message('Estado de checklist actualizado.'); await cargarDashboard();
    }

    async function noAplica(id) {
        const reason = prompt('Justificación obligatoria para NO APLICA:') || '';
        if (!reason.trim()) return message('Debes escribir una justificación para NO APLICA.', 'error');
        await estadoChecklist(id, 'NO_APLICA', reason.trim());
    }

    async function importarChecklist() {
        const input=document.getElementById('ci-checklist-file'), file=input?.files?.[0];
        if(!file)return;
        const fd=new FormData(); fd.append('file',file);
        try { const data=await api('/checklist/importar',{method:'POST',body:fd}); state.checklistImport=data; abrirPreviewChecklist(data); }
        catch(err){ message(err.message||'No se pudo leer la lista de chequeo.','error'); }
        finally { if(input)input.value=''; }
    }
    function abrirPreviewChecklist(data) {
        const rows=(data.propuestas||[]).map((p,i)=>`<tr data-ci-check-import="${i}"><td><input class="ci-chk-use" type="checkbox" checked></td><td><input class="ci-input ci-chk-comp" value="${esc(p.componente||'')}"></td><td><input class="ci-input ci-chk-act" value="${esc(p.actividad||'')}"><small class="text-slate-400">Confianza ${Number(p.confianza||0)}%</small></td><td><input class="ci-input ci-chk-role" value="${esc(p.responsables_sugeridos||'')}"></td><td><textarea class="ci-input ci-chk-req">${esc(p.entregables||'')}</textarea></td><td><input type="date" class="ci-input ci-chk-date" value="${esc(p.fecha_sugerida||'')}">${p.fecha_sugerida?'':'<small class="text-amber-300">FECHA PENDIENTE DE ASIGNACIÓN</small>'}</td></tr>`).join('');
        openModal(`<h3 class="text-xl font-semibold text-white mb-2">Actividades detectadas</h3><p class="text-sm text-slate-400 mb-3">Edita o desmarca propuestas antes de incorporarlas. Las fechas ausentes no se inventan.</p><div class="ci-preview-table-wrap"><table class="ci-preview-table"><thead><tr><th>Incluir</th><th>Componente</th><th>Actividad</th><th>TH a cargo</th><th>Entregables</th><th>Fecha</th></tr></thead><tbody>${rows}</tbody></table></div><button onclick="ciConfirmarChecklistImportado()" class="ci-btn ci-btn-success mt-4">Confirmar propuestas</button>`);
    }
    async function confirmarChecklistImportado() {
        const data=state.checklistImport; if(!data)return;
        const proposals=[...document.querySelectorAll('[data-ci-check-import]')].map(tr=>({ignorar:!tr.querySelector('.ci-chk-use').checked,componente:tr.querySelector('.ci-chk-comp').value,actividad:tr.querySelector('.ci-chk-act').value,responsable_nombre:tr.querySelector('.ci-chk-role').value,entregables:tr.querySelector('.ci-chk-req').value,fecha_sugerida:tr.querySelector('.ci-chk-date').value}));
        const result=await api(`/checklist/importar/${data.importacion_id}/confirmar`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({periodo:state.periodo,propuestas:proposals})});
        closeModal(); state.checklistImport=null; message(`${result.resultado?.creadas||0} obligaciones incorporadas.`); await cargarDashboard();
    }

    function renderCumplimiento(rows) {
        const cont = document.getElementById('ci-cumplimiento-coordinador'); if (!cont) return;
        cont.innerHTML = rows.length ? rows.slice(0, 6).map(r => `<div><div class="flex justify-between text-xs mb-1"><span class="text-slate-300">${esc(r.nombre)}</span><span>${esc(r.porcentaje)}%</span></div><div class="ci-progress"><div class="ci-progress-bar" style="width:${Number(r.porcentaje || 0)}%"></div></div><p class="text-[11px] text-slate-500 mt-1">${r.entregados}/${r.total} entregados · ${r.vencidos} vencidos</p></div>`).join('') : '<p class="text-sm text-slate-500">Sin datos de cumplimiento.</p>';
    }

    function renderDashboardWidget(resumen, alertas) {
        const dash = document.getElementById('dashboard');
        if (!dash) return;
        let widget = document.getElementById('ci-dashboard-widget');
        if (!widget) {
            widget = document.createElement('div');
            widget.id = 'ci-dashboard-widget';
            widget.className = 'ci-dashboard-widget';
            const bar = dash.querySelector('.dashboard-current-datetime-bar');
            bar?.insertAdjacentElement('afterend', widget) || dash.prepend(widget);
        }
        widget.innerHTML = `<div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3"><div><h3 class="font-bold text-slate-100 flex items-center gap-2"><i data-lucide="calendar-clock" class="w-5 h-5 text-blue-300"></i> Calendario inteligente del mes</h3><p class="text-sm text-slate-400">${resumen.entregables_mes || 0} entregables · ${resumen.proximos || 0} próximos · ${resumen.vencidos || 0} vencidos · ${resumen.entregados || 0} entregados.</p>${alertas?.length ? `<p class="text-xs text-amber-200 mt-1">${esc(alertas[0].mensaje)}</p>` : ''}</div><button onclick="mostrarSeccion('calendario-inteligente')" class="ci-btn ci-btn-primary">Abrir calendario</button></div>`;
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function groupBy(arr, fn) {
        return (arr || []).reduce((acc, item) => { const key = fn(item); if (!key) return acc; (acc[key] ||= []).push(item); return acc; }, {});
    }

    async function abrirDia(iso) {
        state.selectedDate = iso;
        const sourceEvents = state.vista === 'anio' ? annual() : eventos();
        const dayEvents = (sourceEvents.length ? sourceEvents : annual()).filter(e => e.fecha_limite === iso);
        openModal(`Entregables del ${iso}`, dayEvents.length ? dayEvents.map(eventDetailHtml).join('') : '<p class="text-slate-500">No hay entregables en esta fecha.</p>');
    }

    async function abrirEntregable(id) {
        const data = await api(`/entregables/${encodeURIComponent(id)}`);
        openModal('Detalle del entregable', eventDetailHtml(data.entregable));
    }

    function eventDetailHtml(e) {
        const id = Number(e.id || 0);
        return `<div class="rounded-xl border border-slate-700 bg-slate-950/60 p-4 mb-3">
            <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                <div><h4 class="font-bold text-slate-100">${esc(e.titulo || '')}</h4><p class="text-sm text-slate-400">${esc(e.descripcion || '')}</p><p class="text-xs text-slate-500 mt-1">${esc(e.modulo || '')} · ${esc(e.unidad || '')} · ${esc(e.coordinador || '')}</p></div>
                <span class="ci-list-status ci-${e.color || e.color_calculado || 'azul'}">${esc(e.estado || '')}</span>
            </div>
            <div class="grid gap-2 md:grid-cols-3 mt-3 text-sm text-slate-300"><p><strong>Fecha:</strong> ${esc(e.fecha_limite || '')}</p><p><strong>Responsable:</strong> ${esc(e.responsable_nombre || '')}${e.responsable_rol ? ` (${esc(e.responsable_rol)})` : ''}</p><p><strong>Prioridad:</strong> ${esc(e.prioridad || '')}</p></div>
            ${e.serie_id ? `<p class="text-xs text-cyan-300 mt-2"><strong>Recurrencia:</strong> ${esc(e.recurrencia || '')} · instancia ${Number(e.instancia_numero || 1)} · hasta ${esc(e.recurrencia_hasta || '')}</p>` : ''}
            <div class="mt-3 flex flex-wrap gap-2">${/ram|asistencia/i.test(String(e.modulo||e.tipo_formato||''))&&e.unidad?`<button onclick="ciGenerarRAM('${esc(e.unidad)}','${esc(String(e.fecha_limite||state.periodo).slice(0,7))}')" class="ci-btn ci-btn-primary"><i data-lucide="download" class="w-4 h-4"></i> Generar listado RAM</button>`:''}<button onclick="ciAbrirModulo('${esc(e.modulo || '')}')" class="ci-btn ci-btn-muted">Abrir módulo</button><button onclick="ciMarcarEntregado(${id})" class="ci-btn ci-btn-success">Marcar entregado</button><button onclick="ciEliminarEntregable(${id})" class="ci-btn ci-btn-danger">Eliminar</button></div>
            <div class="mt-3 grid gap-2 md:grid-cols-[1fr_auto_auto]"><input id="ci-evidencia-${id}" type="file" multiple class="ci-input"><button onclick="ciSubirEvidencia(${id})" class="ci-btn ci-btn-primary">Subir archivos</button><button onclick="ciAbrirEvidencias('ENTREGABLE',${id})" class="ci-btn ci-btn-muted">Historial</button></div>
        </div>`;
    }

    function openModal(title, body) {
        closeModal();
        document.body.insertAdjacentHTML('beforeend', `<div id="ci-modal-backdrop" class="ci-modal-backdrop"><div class="ci-modal"><div class="flex items-start justify-between gap-3 mb-4"><h3 class="text-xl font-bold text-slate-100">${esc(title)}</h3><button onclick="ciCerrarModal()" class="ci-btn ci-btn-muted">Cerrar</button></div>${body}</div></div>`);
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }
    function closeModal() { document.getElementById('ci-modal-backdrop')?.remove(); }

    function abrirModalNuevo() {
        openModal('Nuevo entregable operativo', `<div class="grid gap-3 md:grid-cols-2">
            <input id="ci-new-titulo" class="ci-input" placeholder="Actividad o entregable">
            <input id="ci-new-fecha" type="date" class="ci-input" value="${new Date().toISOString().slice(0,10)}">
            <select id="ci-new-modulo" class="ci-input"><option>RPP</option><option>Bienestarina</option><option>RAM/Asistencia</option><option>Nutrición</option><option>Talento Humano</option><option>Planeación Pedagógica</option><option>Reportes Gerenciales</option><option>Cumplimiento ICBF</option></select>
            <input id="ci-new-formato" class="ci-input" placeholder="Formato">
            <input id="ci-new-coordinador" class="ci-input" placeholder="Coordinador">
            <input id="ci-new-unidad" class="ci-input" placeholder="Unidad/UDS">
            <input id="ci-new-responsable" class="ci-input" placeholder="Responsable">
            <select id="ci-new-responsable-rol" class="ci-input"><option value="">Rol responsable</option><option>DOCENTE</option><option>COORDINADOR</option><option>PSICOSOCIAL</option><option>NUTRICIONISTA</option><option>AUXILIAR_ENFERMERIA</option><option>AUXILIAR_ADMINISTRATIVO</option></select>
            <select id="ci-new-prioridad" class="ci-input"><option>Alta</option><option selected>Media</option><option>Baja</option></select>
            <select id="ci-new-recurrencia" class="ci-input" onchange="ciActualizarRecurrencia()"><option value="ninguna">No repetir</option><option value="diaria">Diaria</option><option value="semanal">Semanal</option><option value="mensual">Mensual</option></select>
            <input id="ci-new-recurrencia-intervalo" type="number" min="1" max="52" value="1" class="ci-input" aria-label="Intervalo de recurrencia" disabled>
            <input id="ci-new-recurrencia-hasta" type="date" class="ci-input md:col-span-2" aria-label="Repetir hasta" disabled>
            <textarea id="ci-new-descripcion" class="ci-input md:col-span-2" placeholder="Descripción u observaciones"></textarea>
        </div><div class="mt-4"><button onclick="ciCrearEntregable()" class="ci-btn ci-btn-primary">Guardar entregable</button></div>`);
    }

    async function crearEntregable() {
        const payload = {
            titulo: document.getElementById('ci-new-titulo')?.value,
            fecha_limite: document.getElementById('ci-new-fecha')?.value,
            modulo: document.getElementById('ci-new-modulo')?.value,
            tipo_formato: document.getElementById('ci-new-formato')?.value,
            coordinador: document.getElementById('ci-new-coordinador')?.value,
            unidad: document.getElementById('ci-new-unidad')?.value,
            responsable_nombre: document.getElementById('ci-new-responsable')?.value,
            responsable_rol: document.getElementById('ci-new-responsable-rol')?.value,
            prioridad: document.getElementById('ci-new-prioridad')?.value,
            recurrencia: document.getElementById('ci-new-recurrencia')?.value || 'ninguna',
            recurrencia_intervalo: Number(document.getElementById('ci-new-recurrencia-intervalo')?.value || 1),
            recurrencia_hasta: document.getElementById('ci-new-recurrencia-hasta')?.value || null,
            descripcion: document.getElementById('ci-new-descripcion')?.value,
            requiere_evidencia: true,
        };
        await api('/entregables', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        closeModal(); message('Entregable creado correctamente.'); await cargarDashboard();
    }

    function actualizarRecurrencia() {
        const active = (document.getElementById('ci-new-recurrencia')?.value || 'ninguna') !== 'ninguna';
        const interval = document.getElementById('ci-new-recurrencia-intervalo');
        const until = document.getElementById('ci-new-recurrencia-hasta');
        if (interval) interval.disabled = !active;
        if (until) {
            until.disabled = !active;
            if (active && !until.value) until.value = document.getElementById('ci-new-fecha')?.value || '';
        }
    }

    async function cargarCronograma() {
        const input = document.getElementById('ci-cronograma-file');
        const file = input?.files?.[0];
        if (!file) return;
        const fd = new FormData(); fd.append('file', file);
        try {
            message('Leyendo cronograma. En unos segundos se abrirá la vista previa editable...');
            const data = await api('/cargar-cronograma', { method: 'POST', body: fd });
            if (data.job_id) {
                message('Cronograma recibido. Se está procesando en segundo plano para evitar error del túnel.');
                input.value = '';
                esperarJobCalendario(data.job_id);
                return;
            }
            if (data.preview) {
                state.previewCronograma = data.preview;
                abrirPreviewCronograma(data.preview);
                input.value = '';
                message(`Cronograma leído: ${data.preview.actividades?.length || 0} actividades detectadas. Revisa y guarda.`);
                return;
            }
            const r = data.resultado || {};
            message(`Cronograma procesado: ${r.creados || 0} creados, ${r.duplicados || 0} duplicados, ${r.errores?.length || 0} errores.`);
            input.value = ''; await cargarDashboard();
        } catch (err) {
            message(err?.message || 'No se pudo procesar el cronograma cargado.', 'error');
            input.value = '';
        }
    }

    function abrirPreviewCronograma(preview) {
        const actividades = preview.actividades || [];
        const rows = actividades.slice(0, 250).map((a, idx) => previewRowHtml(a, idx)).join('') || '<tr><td colspan="9" class="px-4 py-6 text-center text-slate-500">No se detectaron actividades válidas.</td></tr>';
        const warnings = [ ...(preview.advertencias || []), ...(preview.errores || []).slice(0, 5).map(e => `Fila ${e.fila}: ${e.error}`) ];
        const warnHtml = warnings.length ? `<div class="ci-preview-warning"><strong>Revisión requerida:</strong><ul>${warnings.map(w => `<li>${esc(w)}</li>`).join('')}</ul></div>` : '';
        openModal('Vista previa del cronograma', `
            <div class="ci-preview-summary">
                <div><strong>${Number(preview.actividades?.length || 0)}</strong><span>Detectadas</span></div>
                <div><strong>${Number(preview.validas || 0)}</strong><span>Válidas</span></div>
                <div><strong>${Number(preview.invalidas || 0)}</strong><span>Con error</span></div>
                <div><strong>${Number(preview.duplicados_en_archivo || 0)}</strong><span>Duplicadas</span></div>
            </div>
            ${warnHtml}
            <p class="text-sm text-slate-400 mb-3">Corrige fechas, títulos, responsables, unidad o módulo antes de guardar. Las filas marcadas como descartar no serán creadas.</p>
            <div class="ci-preview-table-wrap"><table class="ci-preview-table">
                <thead><tr><th>Guardar</th><th>Fecha</th><th>Actividad</th><th>Responsable</th><th>Coordinador</th><th>Unidad</th><th>Módulo</th><th>Estado</th><th>Observación</th></tr></thead>
                <tbody>${rows}</tbody>
            </table></div>
            ${actividades.length > 250 ? '<p class="text-xs text-amber-300 mt-2">Se muestran las primeras 250 actividades para proteger el rendimiento. Todas las actividades quedan disponibles en la vista previa interna.</p>' : ''}
            <div class="mt-4 flex flex-wrap gap-2">
                <button onclick="ciConfirmarCronograma()" class="ci-btn ci-btn-success"><i data-lucide="save" class="w-4 h-4"></i> Guardar en calendario</button>
                <button onclick="ciCerrarModal()" class="ci-btn ci-btn-muted">Cancelar</button>
            </div>
        `);
    }

    function abrirPreviewExterno(preview) {
        state.previewCronograma=preview;
        if(preview?.periodo){state.periodo=preview.periodo;state.anio=preview.periodo.slice(0,4);}
        abrirPreviewCronograma(preview);
    }

    function previewRowHtml(a, idx) {
        const disabled = a.ok === false ? '' : 'checked';
        const err = (a.errores || []).length ? `<p class="text-[11px] text-rose-300">${esc(a.errores.join('; '))}</p>` : '';
        const warn = (a.advertencias || []).length ? `<p class="text-[11px] text-amber-300">${esc(a.advertencias.join('; '))}</p>` : '';
        return `<tr data-preview-index="${idx}">
            <td><input type="checkbox" class="ci-prev-guardar" ${disabled}></td>
            <td><input type="date" class="ci-input ci-prev-fecha" value="${esc(a.fecha_limite || a.fecha || '')}">${err}</td>
            <td><input class="ci-input ci-prev-titulo" value="${esc(a.titulo || '')}">${warn}</td>
            <td><input class="ci-input ci-prev-responsable" value="${esc(a.responsable_nombre || '')}"></td>
            <td><input class="ci-input ci-prev-coordinador" value="${esc(a.coordinador || '')}"></td>
            <td><input class="ci-input ci-prev-unidad" value="${esc(a.unidad || '')}"></td>
            <td><input class="ci-input ci-prev-modulo" value="${esc(a.modulo || 'General')}"></td>
            <td><select class="ci-input ci-prev-estado"><option value="programado" ${a.estado === 'programado' ? 'selected' : ''}>Programado</option><option value="pendiente" ${a.estado === 'pendiente' ? 'selected' : ''}>Pendiente</option><option value="entregado" ${a.estado === 'entregado' ? 'selected' : ''}>Entregado</option><option value="cerrado" ${a.estado === 'cerrado' ? 'selected' : ''}>Cerrado</option></select></td>
            <td><input class="ci-input ci-prev-observacion" value="${esc(a.observaciones || a.observacion || '')}"><small class="block text-slate-400 mt-1">Confianza ${Number(a.confianza || 0)}%</small></td>
        </tr>`;
    }

    function recopilarPreviewActividades() {
        return [...document.querySelectorAll('[data-preview-index]')].map((tr) => ({
            descartar: !tr.querySelector('.ci-prev-guardar')?.checked,
            fecha_limite: tr.querySelector('.ci-prev-fecha')?.value || '',
            titulo: tr.querySelector('.ci-prev-titulo')?.value || '',
            responsable_nombre: tr.querySelector('.ci-prev-responsable')?.value || '',
            coordinador: tr.querySelector('.ci-prev-coordinador')?.value || '',
            unidad: tr.querySelector('.ci-prev-unidad')?.value || '',
            modulo: tr.querySelector('.ci-prev-modulo')?.value || 'General',
            estado: tr.querySelector('.ci-prev-estado')?.value || 'programado',
            observaciones: tr.querySelector('.ci-prev-observacion')?.value || '',
            prioridad: 'Media',
            requiere_evidencia: true,
        }));
    }

    async function confirmarCronograma() {
        const preview = state.previewCronograma;
        if (!preview?.cronograma_id) { message('No hay cronograma en vista previa.', 'error'); return; }
        const actividades = recopilarPreviewActividades();
        const seleccionadas = actividades.filter(a => !a.descartar);
        if (!seleccionadas.length) { message('Selecciona al menos una actividad para guardar.', 'error'); return; }
        const invalidas = seleccionadas.filter(a => !a.fecha_limite || !a.titulo);
        if (invalidas.length) { message('Hay actividades seleccionadas sin fecha o sin título. Corrígelas antes de guardar.', 'error'); return; }
        try {
            const data = await api('/confirmar-cronograma', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cronograma_id: preview.cronograma_id, actividades })
            });
            const r = data.resultado || {};
            closeModal();
            state.previewCronograma = null;
            message(`Cronograma guardado: ${r.creados || 0} creados, ${r.duplicados || 0} duplicados, ${r.errores?.length || 0} errores.`);
            await cargarDashboard();
        } catch (err) {
            message(err?.message || 'No se pudo guardar el cronograma.', 'error');
        }
    }

    function exportarExcel() {
        const qs = new URLSearchParams({ periodo: state.periodo, anio: state.anio, ...state.filtros });
        window.descargarArchivoAutenticado(`${API}/exportar-excel?${qs.toString()}`).catch((error) => message(error.message, 'error'));
    }

    function exportarPdf() {
        const qs = new URLSearchParams({ periodo: state.periodo, anio: state.anio, ...state.filtros });
        window.descargarArchivoAutenticado(`${API}/exportar-pdf?${qs.toString()}`).catch((error) => message(error.message, 'error'));
    }

    async function subirEvidencia(id) {
        const input = document.getElementById(`ci-evidencia-${id}`);
        const files = [...(input?.files || [])];
        if (!files.length) { message('Selecciona al menos un archivo de evidencia.', 'error'); return; }
        const fd = new FormData(); files.forEach(file => fd.append('files', file)); fd.append('entregable_id', id);
        await api('/evidencias/upload', { method: 'POST', body: fd });
        message(`${files.length} evidencia(s) cargada(s). Ahora puedes enviarlas a revisión.`); await abrirEvidencias('ENTREGABLE', id);
    }

    async function abrirEvidencias(entity, id) {
        try {
            const data = await api(`/evidencias/${entity}/${id}`);
            const rows = data.evidencias || [];
            const history = rows.length ? rows.map(e => `<div class="ci-checklist-card"><div class="flex justify-between gap-3"><div><strong>${esc(e.nombre_original)}</strong><p class="text-xs text-slate-400">Versión ${Number(e.version)} · ${Math.max(1, Math.ceil(Number(e.tamano_bytes || 0)/1024))} KB · SHA-256 ${esc(String(e.sha256 || '').slice(0,12))}…</p></div><span class="ci-list-status ci-${e.estado === 'APROBADA' ? 'verde' : e.estado === 'DEVUELTA' ? 'rojo' : 'azul'}">${esc(e.estado)}</span></div>${e.observacion_revision ? `<p class="text-sm text-amber-200 mt-2">${esc(e.observacion_revision)}</p>` : ''}<button onclick="ciDescargarEvidencia(${Number(e.id)})" class="ci-btn ci-btn-muted mt-2">Descargar</button></div>`).join('') : '<p class="text-slate-400">Todavía no hay evidencias cargadas.</p>';
            openModal(`<h3 class="text-xl font-semibold text-white mb-2">Evidencias e historial</h3><p class="text-sm text-slate-400 mb-4">Los originales se conservan con versión e integridad verificable.</p><div class="grid gap-2 md:grid-cols-[1fr_auto]"><input id="ci-evidence-files" type="file" multiple class="ci-input"><button onclick="ciSubirEvidenciasEntidad('${entity}',${id})" class="ci-btn ci-btn-primary">Cargar</button></div><div class="flex flex-wrap gap-2 my-4"><button onclick="ciEnviarEvidencias('${entity}',${id})" class="ci-btn ci-btn-success">Enviar a revisión</button><button onclick="ciRevisarEvidencias('${entity}',${id},'APROBADA')" class="ci-btn ci-btn-primary">Aprobar</button><button onclick="ciRevisarEvidencias('${entity}',${id},'DEVUELTA')" class="ci-btn ci-btn-muted">Devolver</button></div><div class="grid gap-3">${history}</div>`);
        } catch (err) { message(err.message || 'No se pudo abrir el historial.', 'error'); }
    }
    async function subirEvidenciasEntidad(entity, id) { const files=[...(document.getElementById('ci-evidence-files')?.files||[])]; if(!files.length){message('Selecciona al menos un archivo.','error');return;} const fd=new FormData(); files.forEach(f=>fd.append('files',f)); await api(`/evidencias/${entity}/${id}`,{method:'POST',body:fd}); message('Evidencias cargadas.'); await abrirEvidencias(entity,id); }
    async function enviarEvidencias(entity,id) { await api(`/evidencias/${entity}/${id}/enviar`,{method:'POST'}); closeModal(); message('Evidencias enviadas a revisión.'); await cargarDashboard(); }
    async function revisarEvidencias(entity,id,decision) { const observacion=decision==='DEVUELTA' ? prompt('Indica qué debe corregirse:') : ''; if(decision==='DEVUELTA' && !observacion)return; await api(`/evidencias/${entity}/${id}/revision`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision,observacion})}); closeModal(); message(decision==='APROBADA'?'Evidencias aprobadas.':'Evidencias devueltas para corrección.'); await cargarDashboard(); }
    function descargarEvidencia(id) { window.descargarArchivoAutenticado(`${API}/evidencias/${id}/descargar`).catch(error=>message(error.message,'error')); }
    function generarRAM(unidad,periodo) { const parts=String(periodo||state.periodo).split('-'); if(!unidad){message('Selecciona una UDS/UCA antes de generar el listado.','error');return;} window.descargarArchivoAutenticado(`/api/descargar/${encodeURIComponent(unidad)}/ram?mes=${Number(parts[1])}&anio=${Number(parts[0])}`).then(()=>message('Listado RAM oficial generado. Las asistencias diarias permanecen vacías.')).catch(error=>message(error.message,'error')); }

    async function marcarEntregado(id) { await api(`/entregables/${id}/entregar`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({}) }); closeModal(); message('Entregable marcado como entregado.'); await cargarDashboard(); }
    async function eliminarEntregable(id) { if (!confirm('¿Eliminar este entregable del calendario?')) return; await api(`/entregables/${id}`, { method: 'DELETE' }); closeModal(); message('Entregable eliminado.'); await cargarDashboard(); }

    function abrirModulo(modulo) {
        const m = String(modulo || '').toLowerCase(); closeModal();
        if (m.includes('nutric')) return mostrarSeccion('salud-nutricion');
        if (m.includes('talento')) return mostrarSeccion('talento');
        if (m.includes('plane')) return mostrarSeccion('planeacion-pedagogica');
        if (m.includes('reporte')) return mostrarSeccion('reportes-gerenciales');
        if (m.includes('cumplimiento')) return mostrarSeccion('cumplimiento');
        if (m.includes('coordinador')) return mostrarSeccion('gestion-coordinador');
        return mostrarSeccion('formatos');
    }

    function setPeriodo(value) { if (value) { state.periodo = value; state.anio = value.slice(0,4); state.weekAnchor = `${value}-01`; const anio = document.getElementById('ci-anio'); if (anio) anio.value = state.anio; cargarDashboard(); } }
    function setAnio(value) { if (value) { state.anio = value; cargarDashboard(); } }
    function moverMes(delta) {
        if (state.vista === 'semana') {
            const d = new Date(`${state.weekAnchor}T12:00:00`); d.setDate(d.getDate() + (delta * 7));
            state.weekAnchor = isoLocal(d); state.periodo = state.weekAnchor.slice(0, 7); state.anio = state.weekAnchor.slice(0, 4);
        } else {
            const [y, m] = state.periodo.split('-').map(Number); const d = new Date(y, m - 1 + delta, 1);
            state.periodo = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; state.anio = String(d.getFullYear());
        }
        const p=document.getElementById('ci-periodo'); if(p)p.value=state.periodo; const a=document.getElementById('ci-anio'); if(a)a.value=state.anio; cargarDashboard();
    }
    function cambiarVista(vista) {
        state.vista = vista;
        if (vista === 'semana' && !String(state.weekAnchor).startsWith(state.periodo)) state.weekAnchor = `${state.periodo}-01`;
        renderVista();
    }
    function aplicarFiltros() { state.filtros = { coordinador: val('ci-filtro-coordinador'), unidad: val('ci-filtro-unidad'), modulo: val('ci-filtro-modulo'), estado: val('ci-filtro-estado') }; Object.keys(state.filtros).forEach(k => { if (!state.filtros[k]) delete state.filtros[k]; }); cargarDashboard(); }
    function limpiarFiltros() { ['ci-filtro-coordinador','ci-filtro-unidad','ci-filtro-modulo','ci-filtro-estado'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; }); state.filtros = {}; cargarDashboard(); }
    function val(id) { return document.getElementById(id)?.value || ''; }

    window.calendarioInteligenteInit = init;
    window.ciSetPeriodo = setPeriodo;
    window.ciSetAnio = setAnio;
    window.ciMoverMes = moverMes;
    window.ciCambiarVista = cambiarVista;
    window.ciAplicarFiltros = aplicarFiltros;
    window.ciLimpiarFiltros = limpiarFiltros;
    window.ciAbrirDia = abrirDia;
    window.ciAbrirEntregable = abrirEntregable;
    window.ciAbrirModalNuevo = abrirModalNuevo;
    window.ciCrearEntregable = crearEntregable;
    window.ciActualizarRecurrencia = actualizarRecurrencia;
    window.ciNuevaObligacion = nuevaObligacion;
    window.ciCrearObligacion = crearObligacion;
    window.ciEstadoChecklist = estadoChecklist;
    window.ciNoAplica = noAplica;
    window.ciImportarChecklist = importarChecklist;
    window.ciConfirmarChecklistImportado = confirmarChecklistImportado;
    window.ciCargarCronograma = cargarCronograma;
    window.ciConfirmarCronograma = confirmarCronograma;
    window.ciAbrirPreviewExterno = abrirPreviewExterno;
    window.ciExportarExcel = exportarExcel;
    window.ciExportarPdf = exportarPdf;
    window.ciSubirEvidencia = subirEvidencia;
    window.ciAbrirEvidencias = abrirEvidencias;
    window.ciSubirEvidenciasEntidad = subirEvidenciasEntidad;
    window.ciEnviarEvidencias = enviarEvidencias;
    window.ciRevisarEvidencias = revisarEvidencias;
    window.ciDescargarEvidencia = descargarEvidencia;
    window.ciGenerarRAM = generarRAM;
    window.ciMarcarEntregado = marcarEntregado;
    window.ciEliminarEntregable = eliminarEntregable;
    window.ciCerrarModal = closeModal;
    window.ciAbrirModulo = abrirModulo;

    injectNavAndSection();
    document.addEventListener('DOMContentLoaded', injectNavAndSection);
})();
