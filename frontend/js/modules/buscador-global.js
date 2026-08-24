/* Alpha70 — Buscador global integrado al menú lateral.
 * Capa visual y de consulta no invasiva. No altera Base Maestra ni formatos.
 */
(function () {
  'use strict';

  const TOKEN_KEY = 'primeraInfanciaAuthToken';
  let root = null;
  let input = null;
  let resultsBox = null;
  let modal = null;
  let debounceTimer = null;
  let lastResults = [];

  function backend() {
    return window.backendUrl || window.getBackendUrl?.() || window.getConfiguredBackendUrl?.() || window.location.origin;
  }

  function htmlEscape(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function isLoginVisible() {
    const login = document.getElementById('login-screen') || document.querySelector('#login, .login-container, [data-view="login"]');
    return !!(login && !login.classList.contains('hidden') && login.offsetParent !== null);
  }

  function crearEstilos() {
    if (document.getElementById('alpha70-buscador-style')) return;
    const style = document.createElement('style');
    style.id = 'alpha70-buscador-style';
    style.textContent = `
      #buscador-global-panel{font-family:Inter,system-ui,sans-serif}
      #buscador-global-panel .a70-card{background:rgba(15,23,42,.72);border:1px solid rgba(148,163,184,.22);box-shadow:0 18px 60px rgba(0,0,0,.20);border-radius:20px;overflow:hidden}
      #buscador-global-panel .a70-head{display:flex;align-items:center;gap:12px;padding:14px;border-bottom:1px solid rgba(148,163,184,.15)}
      #buscador-global-panel .a70-icon{width:38px;height:38px;border-radius:14px;background:linear-gradient(135deg,#2563eb,#06b6d4);display:flex;align-items:center;justify-content:center;color:white;font-weight:800;flex:0 0 auto}
      #buscador-global-panel input{flex:1;background:rgba(2,6,23,.72);border:1px solid rgba(148,163,184,.25);border-radius:14px;color:white;padding:12px 14px;font-size:14px;outline:none;width:100%}
      #buscador-global-panel input:focus{border-color:rgba(34,211,238,.65);box-shadow:0 0 0 3px rgba(34,211,238,.14)}
      #buscador-global-panel .a70-hint{padding:10px 14px;color:#94a3b8;font-size:12px;border-bottom:1px solid rgba(148,163,184,.10)}
      #buscador-global-panel .a70-results{max-height:520px;overflow:auto;padding:12px;display:none}
      #buscador-global-panel .a70-item{border:1px solid rgba(148,163,184,.13);background:rgba(30,41,59,.58);border-radius:15px;padding:12px;margin-bottom:9px;cursor:pointer;color:#dbeafe}
      #buscador-global-panel .a70-item:hover{border-color:rgba(34,211,238,.5);background:rgba(30,64,175,.32)}
      #buscador-global-panel .a70-name{font-size:14px;font-weight:800;color:#fff}.a70-meta{font-size:12px;color:#94a3b8;margin-top:5px;line-height:1.45}
      #alpha70-modal{position:fixed;inset:0;background:rgba(2,6,23,.76);z-index:9995;display:none;align-items:center;justify-content:center;padding:18px}
      #alpha70-modal .a70-modal-card{width:min(940px,96vw);max-height:88vh;overflow:auto;background:#0f172a;border:1px solid rgba(148,163,184,.25);border-radius:22px;box-shadow:0 30px 90px rgba(0,0,0,.45);color:#e2e8f0}
      #alpha70-modal .a70-modal-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;padding:18px;border-bottom:1px solid rgba(148,163,184,.15)}
      #alpha70-modal .a70-title{font-weight:800;font-size:20px;color:white}.a70-close{background:#1e293b;color:white;border:1px solid rgba(148,163,184,.25);border-radius:10px;padding:7px 10px;cursor:pointer}
      #alpha70-modal .a70-body{padding:18px;display:grid;gap:14px}.a70-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}.a70-field{background:#111827;border:1px solid rgba(148,163,184,.14);border-radius:14px;padding:10px}.a70-label{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#38bdf8}.a70-value{margin-top:4px;color:#f8fafc;font-weight:600}.a70-actions{display:flex;flex-wrap:wrap;gap:8px}.a70-btn{border:1px solid rgba(56,189,248,.35);background:rgba(14,165,233,.12);color:#bae6fd;border-radius:12px;padding:9px 11px;font-size:12px;cursor:pointer}.a70-warn{border-color:rgba(251,191,36,.35);background:rgba(251,191,36,.1);color:#fde68a}.a70-table{width:100%;border-collapse:collapse;font-size:12px}.a70-table td,.a70-table th{border-bottom:1px solid rgba(148,163,184,.13);padding:8px;text-align:left}.a70-table th{color:#93c5fd}
      @media (max-width:720px){#alpha70-modal .a70-modal-card{max-height:92vh}}
    `;
    document.head.appendChild(style);
  }

  function crearUI() {
    if (isLoginVisible()) return;
    crearEstilos();
    const panel = document.getElementById('buscador-global-panel');
    if (!panel) return;
    if (document.getElementById('alpha70-buscador-root')) return;
    root = document.createElement('div');
    root.id = 'alpha70-buscador-root';
    root.innerHTML = `
      <div class="a70-card">
        <div class="a70-head">
          <div class="a70-icon">🔎</div>
          <input id="alpha70-buscador-input" type="search" autocomplete="off" placeholder="Buscar por documento, nombre, UDS, docente, coordinador o grupo etario…" aria-label="Buscar beneficiario" />
        </div>
        <div class="a70-hint">Escribe al menos 2 caracteres. Consulta cualquier participante de la Base Maestra publicada por nombre, documento, NUI, unidad, docente, coordinador, grupo o estado.</div>
        <div id="alpha70-buscador-results" class="a70-results"></div>
      </div>`;
    panel.innerHTML = '';
    panel.appendChild(root);
    input = document.getElementById('alpha70-buscador-input');
    resultsBox = document.getElementById('alpha70-buscador-results');
    input.addEventListener('input', onInput);
    crearModal();
  }

  function crearModal() {
    if (document.getElementById('alpha70-modal')) return;
    modal = document.createElement('div');
    modal.id = 'alpha70-modal';
    modal.innerHTML = `<div class="a70-modal-card"><div class="a70-modal-head"><div><div class="a70-title">Ficha del beneficiario</div><div id="alpha70-modal-sub" class="a70-meta"></div></div><button class="a70-close" id="alpha70-close">Cerrar</button></div><div id="alpha70-modal-body" class="a70-body"></div></div>`;
    document.body.appendChild(modal);
    document.getElementById('alpha70-close').addEventListener('click', () => modal.style.display = 'none');
    modal.addEventListener('click', (ev) => { if (ev.target === modal) modal.style.display = 'none'; });
  }

  function onInput() {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (q.length < 2) {
      resultsBox.style.display = 'none';
      resultsBox.innerHTML = '';
      return;
    }
    debounceTimer = setTimeout(() => buscar(q), 250);
  }

  async function buscar(q) {
    try {
      crearUI();
      resultsBox.style.display = 'block';
      resultsBox.innerHTML = '<div class="a70-meta" style="padding:8px">Buscando…</div>';
      const url = `${backend()}/api/buscador/beneficiarios?q=${encodeURIComponent(q)}&limit=20`;
      const res = await fetch(url);
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || 'No se pudo buscar');
      lastResults = data.resultados || [];
      renderResultados(lastResults);
    } catch (err) {
      resultsBox.style.display = 'block';
      resultsBox.innerHTML = `<div class="a70-meta a70-warn" style="padding:10px;border-radius:12px">${htmlEscape(err.message || err)}</div>`;
    }
  }

  function renderResultados(items) {
    if (!items.length) {
      resultsBox.innerHTML = '<div class="a70-meta" style="padding:8px">Sin coincidencias.</div>';
      return;
    }
    resultsBox.innerHTML = items.map((it, idx) => `
      <div class="a70-item" data-idx="${idx}">
        <div class="a70-name">${htmlEscape(it.nombre_completo || 'SIN NOMBRE')}</div>
        <div class="a70-meta">Doc: ${htmlEscape(it.documento || '—')} · NUI: ${htmlEscape(it.nui || '—')} · UDS: ${htmlEscape(it.unidad || '—')} · Grupo: ${htmlEscape(it.grupo_etario || '—')} · Estado: ${htmlEscape(it.estado || '—')}</div>
      </div>`).join('');
    [...resultsBox.querySelectorAll('.a70-item')].forEach((el) => {
      el.addEventListener('click', () => abrirDetalle(lastResults[Number(el.dataset.idx)]));
    });
  }

  async function abrirDetalle(item) {
    try {
      const doc = item.documento_normalizado || item.documento || item.nombre_completo;
      const url = `${backend()}/api/buscador/beneficiarios/${encodeURIComponent(doc)}`;
      const res = await fetch(url);
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || 'No se pudo cargar ficha');
      renderFicha(data.ficha || data);
      if (resultsBox) resultsBox.style.display = 'none';
    } catch (err) {
      renderFicha({ beneficiario: item, alertas: [{ mensaje: err.message || String(err) }] });
    }
  }

  function accionSeccion(seccion) {
    if (typeof window.mostrarSeccion === 'function') window.mostrarSeccion(seccion);
    if (modal) modal.style.display = 'none';
  }

  function descargar(url) {
    window.abrirArchivoAutenticado(url).catch((error) => alert(error.message || 'No se pudo abrir el archivo.'));
  }

  function textoAlerta(a) {
    if (typeof a === 'string') return a;
    return a?.mensaje || a?.descripcion || a?.tipo || JSON.stringify(a);
  }

  function renderFicha(ficha) {
    const b = ficha.beneficiario || {};
    const saludItems = Array.isArray(ficha.salud_nutricion) ? ficha.salud_nutricion : (ficha.salud_nutricion ? [ficha.salud_nutricion] : []);
    const salud = saludItems[0] || {};
    const equipo = ficha.equipo_interdisciplinario || ficha.equipo || [];
    const alertas = ficha.alertas || [];
    const unidad = b.unidad || '';
    const doc = b.documento || '';
    document.getElementById('alpha70-modal-sub').textContent = `${b.nombre_completo || 'Beneficiario'} · ${doc || 'sin documento'}`;
    const body = document.getElementById('alpha70-modal-body');
    body.innerHTML = `
      <div class="a70-grid">
        ${campo('Documento', doc)}${campo('Tipo documento', b.tipo_documento)}${campo('Edad', b.edad || b.edad_meses)}${campo('Grupo etario', b.grupo_etario)}${campo('UDS', unidad)}${campo('Docente/agente', b.docente)}${campo('Coordinador', b.coordinador)}${campo('Estado', b.estado)}
      </div>
      <div class="a70-actions">
        <button class="a70-btn" data-go="base-maestra">Ver en Base Maestra</button>
        <button class="a70-btn" data-go="salud-nutricion">Ver Salud/Nutrición</button>
        <button class="a70-btn" data-url="${backend()}/api/rpp/descargar?unidad=${encodeURIComponent(unidad)}&grupo=${encodeURIComponent(grupoRpp(b.grupo_etario))}">Ver RPP</button>
        <button class="a70-btn" data-url="${backend()}/api/descargar/${encodeURIComponent(unidad)}/ram">Ver RAM</button>
        <button class="a70-btn" data-url="${backend()}/api/bienestarina/descargar?unidad=${encodeURIComponent(unidad)}">Ver Bienestarina</button>
        <button class="a70-btn" onclick="window.print()">Exportar ficha</button>
      </div>
      <div class="a70-field"><div class="a70-label">Salud y nutrición</div><div class="a70-value">Peso: ${htmlEscape(salud.peso || '—')} · Talla: ${htmlEscape(salud.talla || '—')} · Diagnóstico: ${htmlEscape(salud.diagnostico || salud.estado || salud.diagnostico_nutricional || '—')}</div></div>
      <div class="a70-field"><div class="a70-label">Alertas</div><div class="a70-value">${alertas.map(textoAlerta).map(htmlEscape).join('<br>') || 'Sin alertas críticas detectadas.'}</div></div>
      <div class="a70-field"><div class="a70-label">Equipo asociado a la UDS</div>${tablaEquipo(equipo)}</div>`;
    body.querySelectorAll('[data-go]').forEach((btn) => btn.addEventListener('click', () => accionSeccion(btn.dataset.go)));
    body.querySelectorAll('[data-url]').forEach((btn) => btn.addEventListener('click', () => descargar(btn.dataset.url)));
    modal.style.display = 'flex';
  }

  function campo(label, value) {
    return `<div class="a70-field"><div class="a70-label">${htmlEscape(label)}</div><div class="a70-value">${htmlEscape(value || '—')}</div></div>`;
  }

  function tablaEquipo(equipo) {
    if (!Array.isArray(equipo) || !equipo.length) return '<div class="a70-meta">Sin equipo registrado para esta UDS.</div>';
    return `<table class="a70-table"><thead><tr><th>Nombre</th><th>Cargo</th><th>Teléfono</th></tr></thead><tbody>${equipo.map(e => `<tr><td>${htmlEscape(e.nombre)}</td><td>${htmlEscape(e.cargo || e.rol || '')}</td><td>${htmlEscape(e.telefono || '')}</td></tr>`).join('')}</tbody></table>`;
  }

  function grupoRpp(grupo) {
    const g = String(grupo || '').toLowerCase();
    if (g.includes('6') && g.includes('11')) return '6_11_MESES';
    if (g.includes('1') && g.includes('2')) return '1_2_ANOS';
    if (g.includes('3') && g.includes('5')) return '3_5_ANOS';
    return '0_6_GESTANTES';
  }

  function showPanel() {
    if (isLoginVisible()) return;
    crearUI();
    setTimeout(() => input?.focus(), 80);
  }

  function init() {
    // Alpha70: no crear buscador flotante. Solo preparar estilos/modal; la UI se muestra en el menú lateral.
    if (isLoginVisible()) return;
    crearEstilos();
    crearModal();
  }

  window.BuscadorGlobalBeneficiarios = { init, showPanel, buscar, abrirDetalle };
  document.addEventListener('DOMContentLoaded', () => setTimeout(init, 900));
})();
