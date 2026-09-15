let backupsEstadoCache = null;
let backupsListaCache = [];
let backupsInicializado = false;

function backupsFormatoBytes(bytes) {
    const n = Number(bytes || 0);
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

function backupsFecha(fecha) {
    if (!fecha) return '';
    const d = new Date(fecha);
    return Number.isNaN(d.getTime()) ? String(fecha) : d.toLocaleString('es-CO');
}

function backupsMensaje(texto, tipo = 'success') {
    if (typeof mostrarMensaje === 'function') {
        mostrarMensaje('backups-message', texto, tipo);
        return;
    }
    const box = document.getElementById('backups-message');
    if (!box) return;
    box.textContent = texto;
    box.classList.remove('hidden');
}

async function backupsInit() {
    if (backupsInicializado) {
        await backupsCargar();
        return;
    }
    backupsInicializado = true;
    await backupsCargar();
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

async function backupsCargar() {
    try {
        const [estadoResp, listaResp] = await Promise.all([
            fetch(`${backendUrl}/api/backups/estado`).then(manejarRespuestaJson),
            fetch(`${backendUrl}/api/backups`).then(manejarRespuestaJson),
        ]);
        backupsEstadoCache = estadoResp.estado || {};
        backupsListaCache = Array.isArray(listaResp.backups) ? listaResp.backups : [];
        backupsRenderEstado();
        backupsRender();
    } catch (error) {
        backupsMensaje(error.message || 'No se pudieron cargar los backups.', 'error');
    }
}

function backupsRenderEstado() {
    const estado = backupsEstadoCache || {};
    const total = document.getElementById('backup-stat-total');
    const validos = document.getElementById('backup-stat-validos');
    const errores = document.getElementById('backup-stat-errores');
    const diario = document.getElementById('backup-stat-diario');
    if (total) total.textContent = estado.total || 0;
    if (validos) validos.textContent = estado.validos || 0;
    if (errores) errores.textContent = estado.errores || 0;
    if (diario) diario.textContent = estado.backup_diario_hoy ? 'Creado hoy' : 'Pendiente';

    const cont = document.getElementById('backups-estado');
    if (!cont) return;
    const ultimo = estado.ultimo || null;
    cont.innerHTML = `
        <div class="rounded-xl border border-slate-800 bg-slate-900/70 p-3">
            <p class="text-xs uppercase tracking-wide text-slate-500">Último backup</p>
            <p class="mt-1 text-slate-200">${escaparHtml(ultimo?.archivo || 'Sin backup registrado')}</p>
            <p class="text-xs text-slate-500">${escaparHtml(backupsFecha(ultimo?.fecha_creacion))}</p>
        </div>
        <div class="rounded-xl border border-slate-800 bg-slate-900/70 p-3">
            <p class="text-xs uppercase tracking-wide text-slate-500">Carpeta</p>
            <p class="mt-1 break-all text-xs text-slate-300">${escaparHtml(estado.carpeta || '')}</p>
        </div>
        <div class="rounded-xl border border-slate-800 bg-slate-900/70 p-3">
            <p class="text-xs uppercase tracking-wide text-slate-500">Base protegida</p>
            <p class="mt-1 break-all text-xs text-slate-300">${escaparHtml(estado.database || '')}</p>
        </div>
    `;
}

function backupsRender() {
    const tbody = document.getElementById('backups-list');
    if (!tbody) return;
    const filtro = normalizarFiltro(document.getElementById('backups-filtro')?.value || '');
    let lista = backupsListaCache || [];
    if (filtro) {
        lista = lista.filter((b) => normalizarFiltro(`${b.archivo} ${b.motivo} ${b.descripcion}`).includes(filtro));
    }
    if (!lista.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-slate-500">No hay backups para mostrar.</td></tr>';
        return;
    }
    tbody.innerHTML = lista.map((b) => {
        const estado = String(b.estado || '').toUpperCase();
        const estadoClass = estado === 'VALIDO'
            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
            : 'border-rose-500/30 bg-rose-500/10 text-rose-300';
        return `
            <tr class="hover:bg-slate-900/50">
                <td class="px-4 py-3 text-xs">${escaparHtml(backupsFecha(b.fecha_creacion))}</td>
                <td class="px-4 py-3"><span class="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs">${escaparHtml(b.motivo || '')}</span><p class="mt-1 text-xs text-slate-500">${escaparHtml(b.descripcion || '')}</p></td>
                <td class="px-4 py-3 max-w-[220px]"><p class="truncate text-slate-300" title="${escaparHtml(b.archivo || '')}">${escaparHtml(b.archivo || '')}</p><p class="text-[10px] text-slate-600">${escaparHtml((b.sha256 || '').slice(0, 12))}</p></td>
                <td class="px-4 py-3 text-xs">${backupsFormatoBytes(b.tamano_bytes)}</td>
                <td class="px-4 py-3"><span class="rounded-lg border px-2 py-1 text-xs ${estadoClass}">${escaparHtml(estado || 'PENDIENTE')}</span><p class="mt-1 text-[10px] text-slate-500">${escaparHtml(b.integridad || '')}</p></td>
                <td class="px-4 py-3">
                    <div class="flex flex-wrap gap-2">
                        <button onclick="backupsValidar(${Number(b.id)})" class="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2 py-1 text-xs text-cyan-300 hover:bg-cyan-500/20">Validar</button>
                        <button onclick="backupsDescargar(${Number(b.id)})" class="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-2 py-1 text-xs text-indigo-300 hover:bg-indigo-500/20">Descargar</button>
                        <button onclick="backupsRestaurar(${Number(b.id)})" class="rounded-lg border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-300 hover:bg-amber-500/20">Restaurar</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

async function backupsCrearManual() {
    const descripcion = prompt('Descripción del backup:', 'Backup manual creado desde el módulo Backups.');
    if (descripcion === null) return;
    try {
        backupsMensaje('Creando backup manual...', 'success');
        await fetch(`${backendUrl}/api/backups/crear`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ motivo: 'MANUAL', descripcion })
        }).then(manejarRespuestaJson);
        backupsMensaje('Backup creado correctamente.', 'success');
        await backupsCargar();
    } catch (error) {
        backupsMensaje(error.message || 'No se pudo crear el backup.', 'error');
    }
}

async function backupsValidar(id) {
    try {
        await fetch(`${backendUrl}/api/backups/${encodeURIComponent(id)}/validar`, { method: 'POST' }).then(manejarRespuestaJson);
        backupsMensaje('Backup validado correctamente.', 'success');
        await backupsCargar();
    } catch (error) {
        backupsMensaje(error.message || 'Backup inválido.', 'error');
    }
}

function backupsDescargar(id) {
    window.descargarArchivoAutenticado(`${backendUrl}/api/backups/${encodeURIComponent(id)}/descargar`)
        .catch((error) => backupsMensaje(error.message || 'No se pudo descargar el backup.', 'error'));
}

async function backupsRestaurar(id) {
    const texto = prompt('Restaurar reemplaza la base actual. Escribe RESTAURAR para confirmar:');
    if (texto !== 'RESTAURAR') {
        backupsMensaje('Restauración cancelada.', 'error');
        return;
    }
    try {
        const passwordActual = prompt('Confirma tu identidad ingresando tu contraseña actual:');
        if (!passwordActual) {
            backupsMensaje('Restauración cancelada: falta reautenticación.', 'error');
            return;
        }
        const data = await fetch(`${backendUrl}/api/backups/${encodeURIComponent(id)}/restaurar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ confirmar: 'RESTAURAR', password_actual: passwordActual })
        }).then(manejarRespuestaJson);
        backupsMensaje(data.message || 'Backup restaurado. Reinicia el backend para finalizar.', 'success');
        await backupsCargar();
    } catch (error) {
        backupsMensaje(error.message || 'No se pudo restaurar el backup.', 'error');
    }
}

window.backupsInit = backupsInit;
window.backupsCargar = backupsCargar;
window.backupsRender = backupsRender;
window.backupsCrearManual = backupsCrearManual;
window.backupsValidar = backupsValidar;
window.backupsDescargar = backupsDescargar;
window.backupsRestaurar = backupsRestaurar;
