(function () {
  'use strict';
  const byId = (id) => document.getElementById(id);
  const base = () => window.backendUrl || '';
  const state = { profiles: [], loads: [], communities: [] };

  async function request(path, options = {}) {
    const response = await fetch(`${base()}${path}`, { credentials: 'include', ...options });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || `No fue posible completar la solicitud (${response.status}).`);
    return body;
  }
  function option(value, label) { const node = document.createElement('option'); node.value = String(value ?? ''); node.textContent = String(label ?? ''); return node; }
  function fill(select, items, placeholder, label) {
    select.replaceChildren(option('', placeholder));
    items.forEach((item) => select.appendChild(option(item.id, label(item))));
    select.disabled = !items.length;
  }
  function status(message, error = false) {
    const node = byId('sn-icbf-status'); if (!node) return;
    node.textContent = message; node.className = `mt-1 text-xs ${error ? 'text-amber-300' : 'text-slate-400'}`;
  }
  async function loadRelated() {
    const profileId = Number(byId('sn-icbf-profile')?.value || 0);
    if (!profileId) return;
    const [loads, communities] = await Promise.all([request(`/api/programas-icbf/perfiles/${profileId}/cargas`), request(`/api/programas-icbf/perfiles/${profileId}/comunidades`)]);
    state.loads = loads.cargas || []; state.communities = communities.comunidades || [];
    fill(byId('sn-icbf-load'), state.loads, 'Seleccione una carga', (item) => `Carga ${item.id} · ${item.total_registros} registros`);
    fill(byId('sn-icbf-community'), state.communities, 'Seleccione una comunidad', (item) => item.nombre);
    byId('sn-icbf-generate').disabled = !(state.loads.length && state.communities.length);
    status(state.communities.length ? 'Contexto listo para revisión. Selecciona carga, comunidad, periodo y formato.' : 'La carga está disponible, pero aún faltan asignaciones explícitas de comunidad.', !state.communities.length);
  }
  async function load() {
    try {
      const data = await request('/api/programas-icbf/perfiles'); state.profiles = data.perfiles || [];
      byId('sn-icbf-program-context')?.classList.remove('hidden');
      fill(byId('sn-icbf-profile'), state.profiles, 'No configurado', (item) => `${item.nombre} · ${item.estado}`);
      const preferred = state.profiles.find((item) => item.codigo === 'SERVICIO_INTEGRADO_DESNUTRICION_EXTRAMURAL') || state.profiles[0];
      if (preferred) { byId('sn-icbf-profile').value = String(preferred.id); await loadRelated(); }
      else status('No existe un perfil multiprograma configurado para esta fundación.', true);
    } catch (error) {
      byId('sn-icbf-generate').disabled = true;
      if (error.message.includes('(404)')) byId('sn-icbf-program-context')?.classList.add('hidden');
      else { byId('sn-icbf-program-context')?.classList.remove('hidden'); status(error.message, true); }
    }
  }
  async function generate() {
    const payload = { comunidad_id: Number(byId('sn-icbf-community').value), formato: byId('sn-icbf-format').value, periodo: byId('sn-icbf-period').value };
    const loadId = Number(byId('sn-icbf-load').value);
    if (!loadId || !payload.comunidad_id || !payload.periodo) { const message = 'Selecciona carga, comunidad y periodo antes de preparar el archivo.'; status(message, true); return { ok: false, error: message }; }
    try {
      byId('sn-icbf-generate').disabled = true; status('Preparando copias verificables…');
      const result = await request(`/api/programas-icbf/cargas/${loadId}/generar`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const files = result.archivos || [];
      status(`Generación ${result.id}: ${files.length} archivo(s). Los hechos pendientes permanecen vacíos.`);
      if (result.paquete_descarga) await window.descargarArchivoAutenticado(`${base()}${result.paquete_descarga}`);
      else if (files[0]) await window.descargarArchivoAutenticado(`${base()}${files[0].descarga}`);
      return { ok: true, generation: result };
    } catch (error) { status(error.message, true); return { ok: false, error: error.message }; }
    finally { byId('sn-icbf-generate').disabled = false; }
  }
  function init() {
    if (!byId('sn-icbf-program-context')) return;
    byId('sn-icbf-refresh')?.addEventListener('click', load);
    byId('sn-icbf-profile')?.addEventListener('change', loadRelated);
    byId('sn-icbf-generate')?.addEventListener('click', generate);
    const today = new Date(); byId('sn-icbf-period').value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    load();
  }
  window.ICBFProgramas = Object.freeze({ load, loadRelated, generate });
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', init) : init();
})();
