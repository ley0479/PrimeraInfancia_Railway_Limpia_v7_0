(function () {
  "use strict";
  // Compatibilidad verificable de la implementación anterior: d.liam||{},
  // platform_presentation_enabled y LIAM_TOURS?.startPresentation permanecen
  // disponibles en el runtime legado aunque ELIAN use el recorrido ampliado.
  const state = {
    flags: {},
    profile: {},
    module: "dashboard",
    open: false,
    presenter: false,
    muted: false,
    voiceListening: false,
    guide: null,
    bootTimer: null,
    contextTimer: null,
    booting: false,
    booted: false,
    welcomed: false,
    historyLoaded: false,
    historyPage: 1,
    historyHasMore: false,
    historySearch: "",
    historyFilters: {},
    realtimeSessionId: "",
    dataPresentation: null,
    lastUserCommand: "",
    history: [],
  };
  const apiBase = () => `${window.backendUrl || ""}/api/asistente-capacitacion`;
  function token() {
    const exposed = window.obtenerTokenSeguro?.();
    if (exposed) return exposed;
    const keys = [
      "primera_infancia_token",
      "auth_token",
      "token",
      "authToken",
      "accessToken",
      "jwt",
      "primeraInfanciaToken",
      "primeraInfanciaAuthToken",
    ];
    for (const storage of [sessionStorage, localStorage]) {
      for (const key of keys) {
        try {
          const value = storage.getItem(key);
          if (value && value !== "null" && value !== "undefined") return value;
        } catch (_) {}
      }
    }
    for (const storage of [sessionStorage, localStorage]) {
      for (const key of [
        "primera_infancia_user",
        "user",
        "usuario",
        "authUser",
        "primeraInfanciaUser",
        "primeraInfanciaAuthUser",
      ]) {
        try {
          const data = JSON.parse(storage.getItem(key) || "null");
          if (data?.token || data?.accessToken)
            return data.token || data.accessToken;
        } catch (_) {}
      }
    }
    return "";
  }
  const headers = () => ({
    "Content-Type": "application/json",
    Authorization: `Bearer ${token()}`,
  });
  const esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const runtime = [
    "liam-control-registry",
    "liam-anchor-registry",
    "liam-safe-zone-engine",
    "liam-animation-orchestrator",
    "liam-tablet-controller",
    "liam-movement-controller",
    "liam-tour-engine",
    "elian-platform-tour",
    "liam-lip-sync",
    "liam-context-collector",
    "liam-error-observer",
    "liam-realtime-webrtc",
  ];
  async function loadRuntime() {
    for (const name of runtime) {
      if (document.querySelector(`script[data-liam-runtime="${name}"]`))
        continue;
      await new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = `./js/liam/${name}.js?v=2.7.5-guided-progress-1`;
        script.dataset.liamRuntime = name;
        script.onload = resolve;
        script.onerror = () => reject(new Error(`No se pudo cargar ${name}.`));
        document.head.appendChild(script);
      });
    }
  }
  function moduleNow() {
    return location.hash.replace(/^#/, "") || "dashboard";
  }
  function authenticatedUser() {
    try {
      const current = window.authUser?.();
      if (current) return current;
    } catch (_) {}
    for (const storage of [sessionStorage, localStorage]) {
      for (const key of [
        "primera_infancia_user",
        "user",
        "usuario",
        "authUser",
        "primeraInfanciaUser",
        "primeraInfanciaAuthUser",
      ]) {
        try {
          const value = JSON.parse(storage.getItem(key) || "null");
          if (value) return value;
        } catch (_) {}
      }
    }
    return {};
  }
  function userFirstName() {
    const user = authenticatedUser();
    const full = String(
      user.nombre_completo || user.nombre || user.username || "",
    ).trim();
    return full ? full.split(/\s+/)[0] : "";
  }
  function dayGreeting() {
    const hour = Number(
      new Intl.DateTimeFormat("es-CO", {
        hour: "2-digit",
        hour12: false,
        timeZone: "America/Bogota",
      })
        .format(new Date())
        .replace(/\D/g, ""),
    );
    return hour < 12
      ? "Buenos días"
      : hour < 18
        ? "Buenas tardes"
        : "Buenas noches";
  }
  function normalizeIdentity() {
    const shell = document.getElementById("liam-shell");
    if (!shell) return;
    const tab = document.getElementById("liam-tab"),
      panel = document.getElementById("liam-panel"),
      presenter = document.getElementById("elian-presenter"),
      question = document.getElementById("liam-question");
    if (tab) {
      tab.setAttribute("aria-label", "Abrir asistente LIAM");
      tab.title = "Abrir asistente LIAM";
    }
    if (panel) panel.setAttribute("aria-label", "LIAM, asistente inteligente");
    if (presenter)
      presenter.setAttribute("aria-label", "LIAM en modo presentador");
    shell
      .querySelectorAll("#liam-panel header b")
      .forEach((node) => (node.textContent = "LIAM"));
    if (question) question.placeholder = "Escribe tu pregunta para LIAM";
    const gender = document.getElementById("elian-inline-gender"),
      voice = document.getElementById("elian-inline-voice"),
      motion = document.getElementById("elian-inline-motion");
    if (gender) gender.value = "female";
    if (voice) voice.value = "female";
    if (motion) motion.value = "full";
  }
  function mountIan() {
    if (document.getElementById("liam-shell")) return;
    document.body.insertAdjacentHTML(
      "beforeend",
      `<div id="liam-shell" class="liam-shell" data-open="false"><button id="liam-tab" class="liam-tab" aria-label="Abrir asistente IAN" title="Abrir asistente IAN" aria-controls="liam-panel" aria-expanded="false"><span id="ian-launcher-avatar" class="ian-launcher-avatar"></span></button><aside id="liam-panel" class="liam-panel" hidden aria-label="IAN, asistente inteligente"><header><div><b>IAN</b><small>Asistente de Primera Infancia</small></div><button id="liam-minimize" aria-label="Minimizar asistente">—</button><button id="liam-close" aria-label="Cerrar asistente">×</button></header><div class="liam-stage"><div class="liam-hologram"></div><div id="liam-avatar-wrap" class="liam-avatar-wrap" data-state="idle"></div><div id="liam-tablet" data-type="message"><strong>Listo para ayudarte</strong><span>Selecciona una opción</span></div></div><div class="liam-content"><p id="liam-context">Reconociendo la pantalla…</p><nav class="liam-actions"><button data-action="presentation">Conocer toda la plataforma</button><button data-action="screen">Explicar esta pantalla</button><button data-action="tour">Realizar una tarea</button><button data-action="where">Muéstrame dónde</button></nav><details id="elian-inline-config" class="elian-config-inline"><summary>Configurar personaje y voz</summary><div class="elian-config-grid"><label>Personaje<select id="elian-inline-gender"><option value="male">Hombre</option><option value="female">Mujer</option></select></label><label>Estilo<select id="elian-inline-variant"><option value="afro_colombian_institutional">Institucional</option><option value="afro_colombian_technological">Tecnológico</option><option value="afro_colombian_educational">Educativo</option></select></label><label>Voz<select id="elian-inline-voice"><option value="male">Masculina</option><option value="female">Femenina</option></select></label><label>Movimiento<select id="elian-inline-motion"><option value="full">Completo</option><option value="light">Ligero</option><option value="reduced">Reducido</option></select></label><button type="button" data-action="elian-save-visual">Aplicar configuración</button><span id="elian-inline-message" class="elian-inline-message"></span></div></details><p id="elian-tour-status" class="elian-tour-status" aria-live="polite"></p><div class="liam-tour-controls" aria-label="Controles del recorrido"><button data-action="elian-pause">Pausar</button><button data-action="elian-resume">Continuar</button><button data-action="elian-repeat">Repetir</button><button data-action="elian-prev">Anterior</button><button data-action="elian-next">Siguiente</button><button data-action="elian-skip">Saltar módulo</button><button data-action="elian-cancel">Detener recorrido</button></div><div id="liam-conversation" class="liam-conversation" aria-live="polite"></div><div class="liam-composer"><textarea id="liam-question" rows="2" maxlength="2000" placeholder="Escribe tu pregunta"></textarea><button data-action="ask">Enviar</button><button data-action="voice" aria-label="Dictar una pregunta">🎙 Dictar</button><button data-action="realtime" aria-label="Iniciar conversación de voz en vivo">📞 Conversar</button><button data-action="stop" aria-label="Detener voz">■</button></div></div></aside></div>`,
    );
    document
      .getElementById("liam-shell")
      .insertAdjacentHTML(
        "beforeend",
        `<section id="elian-presenter" class="elian-presenter" hidden aria-label="IAN en modo presentador"><div id="elian-presenter-caption" class="elian-presenter-caption" aria-live="polite"></div><div class="elian-presenter-controls" aria-label="Controles de la presentación"><button data-action="elian-pause">⏸ Pausar</button><button data-action="elian-repeat">↻ Repetir</button><button data-action="elian-mute">🔇 Silenciar</button><button data-action="elian-prev">← Anterior</button><button data-action="elian-next">Siguiente →</button><button data-action="elian-cancel">✕ Salir</button></div></section>`,
      );
    normalizeIdentity();
    window.IAN_AVATAR?.render("#ian-launcher-avatar", {
      gender: "female",
      compact: true,
    });
    window.IAN_AVATAR?.render("#liam-avatar-wrap", { gender: "female" });
    bind();
    window.LIAM_STATE?.set("idle");
  }
  function applyIanVisual(config = {}) {
    state.visual = config;
    const gender = config.avatar_gender || "female";
    const variant = config.avatar_variant || "afro_colombian_institutional";
    const name = config.assistant_name || "LIAM";
    window.LIAM_3D?.unmount?.();
    window.IAN_AVATAR?.render("#ian-launcher-avatar", {
      gender,
      variant,
      compact: true,
    });
    window.IAN_AVATAR?.render("#liam-avatar-wrap", { gender, variant });
    document
      .querySelectorAll("#liam-panel header b")
      .forEach((el) => (el.textContent = name));
    const tab = document.getElementById("liam-tab");
    if (tab) {
      tab.setAttribute("aria-label", `Abrir asistente ${name}`);
      tab.title = `Abrir asistente ${name}`;
    }
    const set = (id, value) => {
      const field = document.getElementById(id);
      if (field && value) field.value = value;
    };
    set("elian-inline-gender", gender);
    set("elian-inline-variant", variant);
    set("elian-inline-voice", config.voice_gender);
    set("elian-inline-motion", config.motion_level);
    window.LIA_SPEECH?.setVoiceGender?.(config.voice_gender || gender);
    window.LIA_SPEECH?.setRate?.(config.voice_speed || 0.95);
  }
  const applyVisual = applyIanVisual;
  async function request(path, options = {}) {
    const r = await fetch(`${apiBase()}${path}`, {
      ...options,
      headers: { ...headers(), ...(options.headers || {}) },
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.error || "No fue posible consultar LIAM.");
    return d;
  }
  async function platformRequest(path, options = {}) {
    const r = await fetch(`${window.backendUrl || ""}${path}`, {
      ...options,
      headers: { ...headers(), ...(options.headers || {}) },
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok)
      throw new Error(d.error || "La plataforma rechazó la operación.");
    return d;
  }
  function mount() {
    if (document.getElementById("liam-shell")) return;
    document.body.insertAdjacentHTML(
      "beforeend",
      `<div id="liam-shell" class="liam-shell" data-open="false"><button id="liam-tab" class="liam-tab" aria-label="Abrir ELIAN" aria-controls="liam-panel" aria-expanded="false"><img src="./assets/lia/elian-afro-institutional-male-v1.png" alt="Silueta de ELIAN"><span><b>ELIAN</b><small>Ayuda inteligente</small></span></button><aside id="liam-panel" class="liam-panel" hidden aria-label="ELIAN, asistente inteligente"><header><div><b>ELIAN</b><small>Asistente de Primera Infancia</small></div><button id="liam-minimize" aria-label="Minimizar ELIAN">—</button><button id="liam-close" aria-label="Cerrar ELIAN">×</button></header><div class="liam-stage"><div class="liam-hologram"></div><div id="liam-avatar-wrap" class="liam-avatar-wrap" data-state="idle"><img id="liam-avatar" src="./assets/lia/elian-afro-institutional-male-v1.png" alt="ELIAN, asistente profesional"><span class="liam-mouth-motion" aria-hidden="true"></span><span class="liam-hand-motion" aria-hidden="true">☝🏾</span></div><div id="liam-tablet" data-type="message"><strong>Listo para ayudarte</strong><span>Selecciona una opción</span></div></div><div class="liam-content"><p id="liam-context">Reconociendo la pantalla…</p><nav class="liam-actions"><button data-action="presentation">Conocer toda la plataforma</button><button data-action="screen">Explicar esta pantalla</button><button data-action="tour">Realizar una tarea</button><button data-action="where">Muéstrame dónde</button></nav><details id="elian-inline-config" class="elian-config-inline"><summary>Configurar personaje y voz</summary><div class="elian-config-grid"><label>Personaje<select id="elian-inline-gender"><option value="male">Hombre</option><option value="female">Mujer</option></select></label><label>Estilo<select id="elian-inline-variant"><option value="afro_colombian_institutional">Institucional</option><option value="afro_colombian_technological">Tecnológico</option><option value="afro_colombian_educational">Educativo</option></select></label><label>Voz<select id="elian-inline-voice"><option value="male">Masculina</option><option value="female">Femenina</option></select></label><label>Movimiento<select id="elian-inline-motion"><option value="full">Completo</option><option value="light">Ligero</option><option value="reduced">Reducido</option></select></label><button type="button" data-action="elian-save-visual">Aplicar configuración</button><span id="elian-inline-message" class="elian-inline-message"></span></div></details><p id="elian-tour-status" class="elian-tour-status" aria-live="polite"></p><div class="liam-tour-controls" aria-label="Controles del recorrido"><button data-action="elian-pause">Pausar</button><button data-action="elian-resume">Continuar</button><button data-action="elian-repeat">Repetir</button><button data-action="elian-prev">Anterior</button><button data-action="elian-next">Siguiente</button><button data-action="elian-skip">Saltar módulo</button><button data-action="elian-cancel">Detener recorrido</button></div><div id="liam-conversation" class="liam-conversation" aria-live="polite"></div><div class="liam-composer"><textarea id="liam-question" rows="2" maxlength="2000" placeholder="Escribe tu pregunta para ELIAN"></textarea><button data-action="ask">Enviar</button><button data-action="voice" aria-label="Hablar con ELIAN">🎙</button><button data-action="stop" aria-label="Detener voz">■</button></div></div></aside></div>`,
    );
    bind();
    window.LIAM_STATE.set("idle");
  }
  function bind() {
    const shell = document.getElementById("liam-shell");
    shell.addEventListener("click", (e) => {
      const action = e.target.closest("[data-action]")?.dataset.action;
      if (action) handle(action);
    });
    document.getElementById("liam-tab").onclick = open;
    document.getElementById("liam-close").onclick = close;
    document.getElementById("liam-minimize").onclick = close;
    document
      .getElementById("liam-question")
      .addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          handle("ask");
        }
      });
    document.addEventListener("change", (e) => {
      if (!e.target?.files?.length) return;
      if (e.target.id === "input-excel")
        document.dispatchEvent(
          new CustomEvent("liam:business-event", {
            detail: { name: "base-file-selected" },
          }),
        );
      if (e.target.id === "idp-file")
        document.dispatchEvent(
          new CustomEvent("liam:business-event", {
            detail: { name: "document-file-selected" },
          }),
        );
      if (e.target.id === "input-talento")
        document.dispatchEvent(
          new CustomEvent("liam:business-event", {
            detail: { name: "talent-file-selected" },
          }),
        );
    });
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) window.LIA_SPEECH?.stop();
    });
  }
  function add(kind, text) {
    const box = document.getElementById("liam-conversation");
    box.insertAdjacentHTML(
      "beforeend",
      `<div class="${kind}"><b>${kind === "user" ? "Tú" : esc(state.visual?.assistant_name || "LIAM")}</b><p>${esc(text)}</p></div>`,
    );
    box.scrollTop = box.scrollHeight;
  }
  function highlightElement(selector, duration = 5000) {
    if (!selector || !/^#[A-Za-z][\w:-]*$/.test(selector)) return false;
    const element = document.querySelector(selector);
    if (!element) return false;
    element.classList.add("lia-spotlight");
    element.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => element.classList.remove("lia-spotlight"), Math.max(1000, Math.min(10000, duration)));
    return true;
  }
  const normalizedSpeech = (value) => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  function presentationKeywords(label) {
    const ignored = new Set(["total", "de", "del", "la", "las", "el", "los", "por", "con", "sin", "y"]);
    return normalizedSpeech(label).split(" ").filter((word) => word.length > 2 && !ignored.has(word));
  }
  function activatePresentationItem(index) {
    const presentation = state.dataPresentation;
    if (!presentation?.items.length) return;
    const bounded = Math.max(0, Math.min(index, presentation.items.length - 1));
    presentation.items.forEach((item, position) => {
      item.classList.toggle("lia-data-active", position === bounded);
      item.classList.toggle("lia-data-explained", position < bounded);
      item.setAttribute("aria-current", position === bounded ? "true" : "false");
    });
    presentation.index = bounded;
    const label = presentation.items[bounded].dataset.liaLabel || "Indicador";
    const status = document.querySelector("[data-lia-presenter-status]");
    if (status) status.textContent = `Explicando: ${label}`;
    document.querySelector("[data-lia-presenter-avatar]")?.setAttribute("data-state", "pointing_right");
    presentation.items[bounded].scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  function syncDataPresentation(delta, completed = false) {
    const presentation = state.dataPresentation;
    if (!presentation?.items.length) return;
    presentation.transcript += ` ${String(delta || "")}`;
    const spoken = normalizedSpeech(presentation.transcript);
    let matched = -1;
    presentation.items.forEach((item, index) => {
      const words = presentationKeywords(item.dataset.liaLabel);
      if (words.length && words.every((word) => spoken.includes(word))) matched = Math.max(matched, index);
    });
    const wordCount = spoken ? spoken.split(" ").length : 0;
    const progressive = Math.min(presentation.items.length - 1, Math.floor(Math.max(0, wordCount - 1) / 12));
    activatePresentationItem(Math.max(presentation.index, matched, progressive));
    if (completed) {
      presentation.items.forEach((item) => item.classList.add("lia-data-explained"));
      presentation.items[presentation.index]?.classList.add("lia-data-active");
      const status = document.querySelector("[data-lia-presenter-status]");
      if (status) status.textContent = "Explicación terminada";
      document.querySelector("[data-lia-presenter-avatar]")?.setAttribute("data-state", "success");
    }
  }
  function configureDataDrawer(drawer) {
    const ratios = ["40", "50", "60"], saved = localStorage.getItem("lia-data-panel-ratio");
    drawer.dataset.ratio = ratios.includes(saved) ? saved : "50";
    drawer.dataset.maximized = "false";
    const applyLabel = () => { const button=drawer.querySelector('[data-lia-drawer-action="ratio"]'); if(button)button.textContent=`${drawer.dataset.ratio}%`; };
    drawer.querySelector('[data-lia-drawer-action="close"]')?.addEventListener("click", () => drawer.dataset.open = "false");
    drawer.querySelector('[data-lia-drawer-action="minimize"]')?.addEventListener("click", (event) => { const minimized=drawer.dataset.minimized!=="true"; drawer.dataset.minimized=String(minimized); event.currentTarget.textContent=minimized?"▢":"—"; });
    drawer.querySelector('[data-lia-drawer-action="maximize"]')?.addEventListener("click", () => drawer.dataset.maximized=String(drawer.dataset.maximized!=="true"));
    drawer.querySelector('[data-lia-drawer-action="ratio"]')?.addEventListener("click", () => { const index=ratios.indexOf(drawer.dataset.ratio); drawer.dataset.ratio=ratios[(index+1)%ratios.length]; localStorage.setItem("lia-data-panel-ratio",drawer.dataset.ratio); applyLabel(); });
    applyLabel();
  }
  function richContent(payload) {
    const type = payload?.componentType, data = payload?.data || {};
    if (!["metric-card", "table", "list", "spotlight"].includes(type)) return null;
    const root = document.createElement("div"); root.className = "lia-rich"; root.dataset.componentType = type;
    if (data.title) { const title = document.createElement("h3"); title.textContent = String(data.title); root.appendChild(title); }
    if (data.note) { const note = document.createElement("p"); note.className = "lia-data-note"; note.textContent = String(data.note); root.appendChild(note); }
    if (type === "metric-card") {
      const grid = document.createElement("div"); grid.className = "lia-metrics";
      for (const item of (data.metrics || []).slice(0, 16)) { const card = document.createElement("div"), value = document.createElement("strong"), label = document.createElement("span"); card.className = "lia-metric lia-data-point"; card.dataset.liaLabel = String(item.label || "Indicador"); value.textContent = String(item.value ?? "—"); label.textContent = String(item.label || "Indicador"); card.append(value, label); grid.appendChild(card); }
      root.appendChild(grid);
      if (Array.isArray(data.rows) && data.rows.length) { const detail = richContent({ componentType: "table", data: { columns: data.columns || [], rows: data.rows, maxColumns: data.maxColumns, relationFormat: data.relationFormat } }); if (detail) root.appendChild(detail); }
    } else if (type === "table") {
      const table = document.createElement("table"), head = document.createElement("thead"), body = document.createElement("tbody"), tr = document.createElement("tr");
      const maxColumns = Math.max(1, Math.min(24, Number(data.maxColumns || 8)));
      if (data.relationFormat) root.classList.add("lia-relation-format");
      for (const label of (data.columns || []).slice(0, maxColumns)) { const th = document.createElement("th"); th.textContent = String(label ?? ""); tr.appendChild(th); } head.appendChild(tr);
      for (const row of (data.rows || []).slice(0, 50)) { const line = document.createElement("tr"); line.className = "lia-data-point"; line.dataset.liaLabel = String((Array.isArray(row) && row[0]) || "Registro"); for (const value of (Array.isArray(row) ? row : []).slice(0, maxColumns)) { const td = document.createElement("td"); td.textContent = String(value ?? "—"); line.appendChild(td); } body.appendChild(line); }
      if (!body.children.length) { const line = document.createElement("tr"), td = document.createElement("td"); td.colSpan = Math.max(1, (data.columns || []).length); td.textContent = "La consulta no devolvió registros para mostrar."; line.appendChild(td); body.appendChild(line); }
      table.append(head, body); root.appendChild(table);
    } else if (type === "list") {
      const list = document.createElement("ul"); for (const item of (data.items || []).slice(0, 30)) { const li = document.createElement("li"); li.className = "lia-data-point"; li.dataset.liaLabel = String(item.label || "Dato"); li.textContent = `${item.label || "Dato"}: ${item.value ?? "—"}`; list.appendChild(li); } root.appendChild(list);
    }
    return root;
  }
  function renderStructured(payload) {
    if (!payload || payload.schemaVersion !== "lia-ui-v1") return;
    const content = richContent(payload);
    if (payload.display === "drawer" && content) {
      let drawer = document.getElementById("lia-data-drawer");
      if (!drawer) { drawer = document.createElement("aside"); drawer.id = "lia-data-drawer"; drawer.className = "lia-data-drawer"; drawer.setAttribute("aria-label","Panel visual de Lía"); drawer.innerHTML = '<header><strong>Datos consultados por Lía</strong><div class="lia-drawer-controls"><button type="button" data-lia-drawer-action="minimize" aria-label="Minimizar panel">—</button><button type="button" data-lia-drawer-action="ratio" aria-label="Cambiar proporción del panel">50%</button><button type="button" data-lia-drawer-action="maximize" aria-label="Maximizar panel">□</button><button type="button" data-lia-drawer-action="close" aria-label="Cerrar panel">×</button></div></header><div class="lia-data-layout"><div class="lia-data-presenter"><div data-lia-presenter-avatar></div><span data-lia-presenter-status>Preparando explicación…</span></div><div data-lia-drawer-content></div></div>'; document.body.appendChild(drawer); configureDataDrawer(drawer); }
      drawer.dataset.minimized = "false";
      const destination = drawer.querySelector("[data-lia-drawer-content]"); destination.replaceChildren(content); drawer.dataset.open = "true";
      window.IAN_AVATAR?.render("[data-lia-presenter-avatar]", { gender: state.visual?.avatar_gender || "female", variant: state.visual?.avatar_variant });
      const items = Array.from(destination.querySelectorAll(".lia-data-point"));
      state.dataPresentation = { items, index: -1, transcript: "" };
      if (items.length) activatePresentationItem(0);
    } else if (content) document.querySelector("#liam-conversation > div:last-child")?.appendChild(content);
    if (payload.targetSelector) highlightElement(payload.targetSelector);
  }
  function remember(role, content) {
    state.history.push({ role, content: String(content || "").slice(0, 1200) });
  }
  function ensureHistoryTools() {
    const box = document.getElementById("liam-conversation");
    if (!box || document.getElementById("liam-history-tools")) return;
    if (!document.getElementById("liam-history-tools-style")) {
      const style = document.createElement("style");
      style.id = "liam-history-tools-style";
      style.textContent = ".liam-history-tools{display:grid;grid-template-columns:minmax(100px,1fr) auto auto auto;gap:5px;margin-top:10px}.liam-history-tools input{min-width:0;border:1px solid #475569;border-radius:8px;background:#fff;color:#172033;padding:7px;font-size:11px}.liam-history-tools button{border:1px solid #64748b;border-radius:8px;background:#0f766e;color:#fff;padding:6px;font-size:10px;font-weight:700}@media(max-width:520px){.liam-history-tools{grid-template-columns:1fr 1fr}.liam-history-tools input{grid-column:1/-1}}";
      document.head.appendChild(style);
    }
    const canAudit = ["SUPERADMIN", "GERENTE", "COORDINADOR"].includes(String(authenticatedUser().rol || "").toUpperCase());
    box.insertAdjacentHTML("beforebegin", `<div id="liam-history-tools" class="liam-history-tools"><input id="liam-history-search" type="search" maxlength="120" placeholder="Buscar"><input id="liam-history-module" maxlength="80" placeholder="Módulo"><input id="liam-history-from" type="date" title="Desde"><input id="liam-history-to" type="date" title="Hasta"><select id="liam-history-role"><option value="">Todos</option><option value="user">Órdenes</option><option value="assistant">Respuestas</option></select><button type="button" data-action="history-search">Filtrar</button><button type="button" data-action="history-more" id="liam-history-more">Ver anteriores</button><button type="button" data-action="history-sessions">Sesiones</button><button type="button" data-action="history-stats">Estadísticas</button><button type="button" data-action="favorite-save">☆ Guardar orden</button><button type="button" data-action="favorite-list">Favoritos</button><button type="button" data-action="history-export">CSV</button><button type="button" data-action="history-export-xlsx">Excel</button><button type="button" data-action="history-export-pdf">PDF</button>${canAudit ? '<button type="button" data-action="history-audit">Auditoría</button>' : ''}</div>`);
  }
  async function saveFavorite(){
    if(!state.lastUserCommand){add("liam","Primero escribe o dicta una orden para poder guardarla.");return}
    const name=String(window.prompt("Nombre del comando favorito:","")||"").trim();if(!name)return;
    const data=await request("/command-favorites",{method:"POST",body:JSON.stringify({name,command:state.lastUserCommand})});
    add("liam",`${data.created?"Guardé":"Actualicé"} el favorito ${data.favorite.name}. Las demás órdenes siguen disponibles.`);
  }
  async function viewFavorites(){
    const data=await request("/command-favorites"),box=document.getElementById("liam-conversation");
    box?.querySelector(".liam-favorites-list")?.remove();
    const node=document.createElement("section");node.className="liam-favorites-list";node.innerHTML=`<strong>Comandos favoritos</strong>${(data.favorites||[]).map(item=>`<div><span>${esc(item.nombre)}</span><button type="button" data-favorite-run="${esc(item.nombre)}">Ejecutar</button><button type="button" data-favorite-delete="${Number(item.id)}">Eliminar</button></div>`).join("")||"<p>No tienes favoritos guardados.</p>"}`;box?.appendChild(node);
    node.querySelectorAll("[data-favorite-run]").forEach(button=>button.addEventListener("click",()=>ask(`Liam ejecuta ${button.dataset.favoriteRun}`)));
    node.querySelectorAll("[data-favorite-delete]").forEach(button=>button.addEventListener("click",async()=>{await request(`/command-favorites/${Number(button.dataset.favoriteDelete)}`,{method:"DELETE"});button.parentElement?.remove()}));
  }
  async function loadHistory({ page = 1, appendOlder = false } = {}) {
    if (state.historyLoaded && page === 1 && !state.historySearch) return;
    ensureHistoryTools();
    const query = new URLSearchParams({ limit: "100", page: String(page) });
    if (state.historySearch) query.set("search", state.historySearch);
    for (const [key, value] of Object.entries(state.historyFilters)) if (value) query.set(key, value);
    const data = await request(`/chat/history?${query}`);
    const messages = Array.isArray(data.messages) ? data.messages : [];
    const box = document.getElementById("liam-conversation");
    const currentMarkup = appendOlder && box ? box.innerHTML : "";
    if (box) box.innerHTML = "";
    if (!appendOlder && !state.historySearch) state.history = [];
    for (const item of messages) {
      if (!["user", "assistant"].includes(item.role)) continue;
      add(item.role === "user" ? "user" : "liam", item.content);
      if (!appendOlder && !state.historySearch) remember(item.role, item.content);
    }
    if (appendOlder && box) box.insertAdjacentHTML("beforeend", currentMarkup);
    state.historyPage = Number(data.page || page);
    state.historyHasMore = Boolean(data.has_more);
    const more = document.getElementById("liam-history-more");
    if (more) more.hidden = !state.historyHasMore;
    state.historyLoaded = true;
  }
  async function searchHistory() {
    state.historySearch = String(document.getElementById("liam-history-search")?.value || "").trim();
    state.historyFilters = { date_from: document.getElementById("liam-history-from")?.value || "", date_to: document.getElementById("liam-history-to")?.value || "", role: document.getElementById("liam-history-role")?.value || "", module: String(document.getElementById("liam-history-module")?.value || "").trim() };
    state.historyLoaded = false;
    await loadHistory({ page: 1 });
  }
  async function exportHistory(format = "csv") {
    const response = await fetch(`${apiBase()}/chat/history/export.${format}`, { headers: headers() });
    if (!response.ok) throw new Error("No se pudo exportar el historial.");
    const url = URL.createObjectURL(await response.blob()), link = document.createElement("a");
    link.href = url; link.download = `historial_lia.${format}`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
  async function auditHistory() {
    const data = await request("/chat/history/admin?limit=100");
    const box = document.getElementById("liam-conversation");
    if (box) box.innerHTML = "";
    for (const item of [...(data.messages || [])].reverse()) add(item.role === "user" ? "user" : "liam", `${item.username || `Usuario ${item.usuario_id}`}: ${item.content_redacted}`);
  }
  async function viewHistoryStats() {
    const data = await request("/chat/history/stats"), detail = (data.top_modules || []).map((x) => `${x.module}: ${x.total}`).join(", ") || "sin actividad";
    add("liam", `Historial: ${data.commands} órdenes, ${data.messages} mensajes y ${data.sessions} sesiones. Módulos principales: ${detail}.`);
  }
  async function viewHistorySessions() {
    const data = await request("/chat/history/sessions"), box = document.getElementById("liam-conversation");
    if (box) box.innerHTML = "";
    for (const session of data.sessions || []) {
      const node = document.createElement("div"); node.className = "liam";
      const label = document.createElement("p"); label.textContent = `${session.started_at} · ${session.module || "sin módulo"} · ${session.commands} orden(es) · ${session.messages} mensaje(s)`;
      const button = document.createElement("button"); button.type = "button"; button.textContent = "Archivar";
      button.addEventListener("click", async () => { await request(`/chat/history/sessions/${encodeURIComponent(session.request_id)}/archive`, { method: "POST" }); node.remove(); });
      node.append(label, button); box?.appendChild(node);
    }
  }
  function saveVoiceTranscript(role, content) {
    return request("/voice/realtime/event", { method: "POST", body: JSON.stringify({ event: "transcript", role, content, module: state.module, request_id: state.realtimeSessionId }) }).catch(() => {});
  }
  function auditClientAction(action, status, requestId, module, detail = "") {
    request("/actions/client-event", {
      method: "POST",
      body: JSON.stringify({
        action,
        status,
        request_id: requestId,
        module,
        detail,
      }),
    }).catch(() => {});
  }
  function waitForElement(selector, timeout = 5000) {
    return new Promise((resolve) => {
      const found = document.querySelector(selector);
      if (found) return resolve(found);
      const observer = new MutationObserver(() => {
        const node = document.querySelector(selector);
        if (node) {
          observer.disconnect();
          clearTimeout(timer);
          resolve(node);
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });
      const timer = setTimeout(() => {
        observer.disconnect();
        resolve(null);
      }, timeout);
    });
  }
  async function runClientAction(action, requestId) {
    if (action.type === "navigate") {
      if (typeof window.mostrarSeccion !== "function")
        throw new Error("La navegación segura no está disponible.");
      window.mostrarSeccion(action.module);
      if (action.module === "calendario-inteligente") {
        const ready = await waitForElement("#ci-periodo");
        if (!ready)
          throw new Error("El calendario no confirmó que terminó de cargar.");
        if (action.period && typeof window.ciSetPeriodo === "function")
          window.ciSetPeriodo(action.period);
        if (typeof window.ciCambiarVista === "function")
          window.ciCambiarVista("mes");
        await waitForElement("#ci-mis-pendientes");
        if (action.target)
          window.LIAM_ANIMATION?.highlight(
            action.target,
            "Pendientes consultados por LIAM",
          );
      }
      auditClientAction(
        "open_module",
        "completed",
        requestId,
        action.module,
        action.period || "",
      );
      return true;
    }
    if (action.type === "open_module") {
      if (typeof window.mostrarSeccion !== "function")
        throw new Error("La navegación segura no está disponible.");
      window.mostrarSeccion(action.module);
      auditClientAction("open_module", "completed", requestId, action.module);
      return true;
    }
    if (action.type === "search_beneficiary") {
      if (
        typeof window.mostrarSeccion !== "function" ||
        !window.BuscadorGlobalBeneficiarios
      )
        throw new Error("La búsqueda autorizada no está disponible.");
      window.mostrarSeccion("buscador-beneficiarios");
      window.BuscadorGlobalBeneficiarios.showPanel();
      await window.BuscadorGlobalBeneficiarios.buscar(action.query);
      auditClientAction(
        "search_beneficiary",
        "completed",
        requestId,
        "buscador-beneficiarios",
      );
      return true;
    }
    if (action.type === "download_bienestarina") {
      if (typeof window.descargarBienestarinaAlpha62 !== "function")
        throw new Error("El generador de Bienestarina no está disponible.");
      const result = await window.descargarBienestarinaAlpha62(action.unit, {
        mes: Number(action.month),
        anio: Number(action.year),
      });
      if (!result?.ok)
        throw new Error(
          result?.error ||
            "El servidor no confirmó el archivo de Bienestarina.",
        );
      auditClientAction(
        "download_bienestarina",
        "completed",
        requestId,
        "formatos",
        result.filename,
      );
      return `Bienestarina está lista para descargar: ${result.filename}.`;
    }
    return false;
  }
  async function runProtectedAction(proposal) {
    const a = proposal.arguments || {},
      handler = proposal.client_handler;
    if (handler === "generate_monthly_reports") {
      if (typeof window.descargarArchivoAutenticado !== "function")
        throw new Error("La descarga autenticada no está disponible.");
      const generated = await platformRequest(
        `/api/relacion-mes/generar?mes=${Number(a.month)}&anio=${Number(a.year)}`,
        { method: "POST", body: JSON.stringify({ mes: Number(a.month), anio: Number(a.year) }) },
      );
      if (!generated?.url)
        throw new Error("El servidor no confirmó la Relación del Mes.");
      await window.descargarArchivoAutenticado(
        `${window.backendUrl || ""}${generated.url}`,
        generated.archivo || "",
      );
      await window.descargarArchivoAutenticado(
        `${window.backendUrl || ""}/api/cruce-bases/informe-estadistico/docx?alcance=general`,
      );
      return "La Relación del Mes y el informe nutricional con anexos fueron generados y descargados.";
    }
    if (handler === "download_rpp") {
      if (typeof window.descargarRppCategoria !== "function")
        throw new Error(
          "La generación RPP no está disponible en esta pantalla.",
        );
      await window.descargarRppCategoria(a.unit, a.group, {
        mes: a.month,
        anio: a.year,
      });
      return "El RPP fue solicitado con los datos confirmados.";
    }
    if (handler === "download_ram") {
      if (typeof window.descargarArchivoAutenticado !== "function")
        throw new Error("La descarga autenticada no está disponible.");
      await window.descargarArchivoAutenticado(
        `/api/descargar/${encodeURIComponent(a.unit)}/ram?mes=${Number(a.month)}&anio=${Number(a.year)}`,
      );
      return "El RAM oficial fue generado y descargado con los datos confirmados.";
    }
    if (handler === "publish_master_database") {
      const d = await platformRequest("/api/base-maestra/publicar", {
        method: "POST",
        body: JSON.stringify({
          version_id: Number(a.version_id),
          observaciones: "Publicación confirmada mediante LIAN",
        }),
      });
      return (
        d.message || `La versión ${a.version_id} de Base Maestra fue publicada.`
      );
    }
    if (handler === "consolidate_master_database") {
      const d = await platformRequest("/api/base-maestra/consolidar", {
        method: "POST",
        body: JSON.stringify({
          observaciones: "Consolidación confirmada mediante LIAN",
        }),
      });
      return (
        d.message ||
        "La Base Maestra fue consolidada y se creó una versión para revisión."
      );
    }
    if (handler === "create_user") {
      const bytes = new Uint8Array(12);
      crypto.getRandomValues(bytes);
      const temporary = `Li!${Array.from(bytes, (x) => (x % 36).toString(36)).join("")}9a`;
      const d = await platformRequest("/api/usuarios", {
        method: "POST",
        body: JSON.stringify({
          username: a.username,
          email: a.email,
          rol: a.role,
          fundacion_id: Number(a.foundation_id),
          password: temporary,
          debe_cambiar_password: true,
          nombre_completo: a.username,
        }),
      });
      return {
        message: `${d.message || "Usuario creado."} Contraseña temporal (se muestra una sola vez): ${temporary}`,
        speech:
          d.message ||
          "Usuario creado correctamente. La contraseña temporal está visible en pantalla.",
        sensitive: true,
      };
    }
    if (handler === "update_user") {
      const list = await platformRequest("/api/usuarios"),
        current = (list.usuarios || []).find(
          (x) => Number(x.id) === Number(a.user_id),
        );
      if (!current) throw new Error("Usuario no encontrado o no autorizado.");
      const payload = {
        ...current,
        activo: a.active ? 1 : 0,
        estado: a.active ? "ACTIVO" : "INACTIVO",
      };
      const d = await platformRequest(`/api/usuarios/${Number(a.user_id)}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      return (
        d.message ||
        `El usuario ${a.user_id} fue ${a.active ? "reactivado" : "suspendido"}.`
      );
    }
    if (handler === "create_foundation") {
      const d = await platformRequest("/api/fundaciones", {
        method: "POST",
        body: JSON.stringify({
          nombre: a.name,
          nit: a.nit || null,
          estado: "ACTIVA",
          plan: "PRUEBA",
          observaciones: "Creación confirmada mediante LIAN",
        }),
      });
      return d.message || `La fundación ${a.name} fue creada e inicializada.`;
    }
    if (handler === "update_foundation") {
      const list = await platformRequest("/api/fundaciones"),
        current = (list.fundaciones || []).find(
          (x) => Number(x.id) === Number(a.foundation_id),
        );
      if (!current) throw new Error("Fundación no encontrada o no autorizada.");
      const payload = {
        ...current,
        estado: a.active ? "ACTIVA" : "SUSPENDIDA",
      };
      const d = await platformRequest(
        `/api/fundaciones/${Number(a.foundation_id)}`,
        { method: "PUT", body: JSON.stringify(payload) },
      );
      return (
        d.message ||
        `La fundación ${a.foundation_id} fue ${a.active ? "reactivada" : "suspendida"}.`
      );
    }
    throw new Error("La acción protegida no tiene un ejecutor registrado.");
  }
  function showProposal(proposal) {
    if (!proposal || proposal.missing?.length) return;
    const box = document.getElementById("liam-conversation");
    const id = `liam-confirm-${Date.now()}`,
      risk = proposal.risk || "generation",
      riskText =
        {
          generation: "Generación de documento",
          modification: "Modificación de datos",
          administration: "Operación administrativa",
          financial: "Operación financiera",
          critical: "Operación crítica",
        }[risk] || "Operación protegida";
    box.insertAdjacentHTML(
      "beforeend",
      `<div class="liam-confirm" id="${id}" data-risk="${esc(risk)}"><strong>${esc(riskText)}</strong><p>${esc(proposal.summary)}</p><small>Revisa los datos. LIAN solo continuará si confirmas esta operación.</small><div><button type="button">${esc(proposal.label || "Confirmar")}</button><button type="button">Cancelar</button></div></div>`,
    );
    const node = document.getElementById(id),
      buttons = node?.querySelectorAll("button") || [];
    let expiryTimer;
    if (proposal.expires_at) {
      const expiry = new Date(proposal.expires_at);
      expiryTimer = setTimeout(
        () => {
          buttons.forEach((x) => (x.disabled = true));
          node?.setAttribute("data-expired", "true");
          const note = node?.querySelector("small");
          if (note)
            note.textContent =
              "Esta confirmación venció. Solicita nuevamente la operación.";
        },
        Math.max(0, expiry.getTime() - Date.now()),
      );
    }
    buttons[0]?.addEventListener("click", async () => {
      buttons.forEach((x) => (x.disabled = true));
      clearTimeout(expiryTimer);
      try {
        let outcome;
        if (proposal.server_confirmation) {
          const result = await request(
            `/actions/confirm/${encodeURIComponent(proposal.proposal_id)}`,
            { method: "POST", body: "{}" },
          );
          outcome = result.message;
        } else outcome = await runProtectedAction(proposal);
        const message = typeof outcome === "object" ? outcome.message : outcome,
          speech = typeof outcome === "object" ? outcome.speech : message,
          sensitive = Boolean(outcome?.sensitive);
        auditClientAction(
          proposal.id || proposal.client_handler,
          "completed",
          proposal.proposal_id || "",
          (proposal.arguments || {}).module || state.module,
        );
        node?.remove();
        add("liam", message);
        remember("assistant", sensitive ? speech : message);
        if (state.flags.voice_enabled) window.LIA_SPEECH?.speak(speech);
      } catch (error) {
        buttons.forEach((x) => (x.disabled = false));
        auditClientAction(
          proposal.id || proposal.client_handler,
          "failed",
          proposal.proposal_id || "",
          (proposal.arguments || {}).module || state.module,
          error.message,
        );
        add("liam", error.message || "No fue posible ejecutar la acción.");
      }
    });
    buttons[1]?.addEventListener("click", () => {
      clearTimeout(expiryTimer);
      auditClientAction(
        proposal.id || proposal.client_handler,
        "cancelled",
        proposal.proposal_id || "",
        (proposal.arguments || {}).module || state.module,
      );
      node?.remove();
      add("liam", "Acción cancelada. No se realizó ningún cambio.");
    });
    box.scrollTop = box.scrollHeight;
  }
  function caption(text) {
    const node = document.getElementById("elian-presenter-caption");
    if (node) node.textContent = String(text || "");
  }
  function syncMutePreference() {
    state.muted = Boolean(window.LIA_SPEECH?.preferences?.().muted);
    const button = document.querySelector('[data-action="elian-mute"]');
    if (button)
      button.textContent = state.muted ? "🔊 Activar voz" : "🔇 Silenciar";
  }
  function enterPresenter() {
    state.presenter = true;
    state.open = false;
    const shell = document.getElementById("liam-shell"),
      panel = document.getElementById("liam-panel"),
      presenter = document.getElementById("elian-presenter");
    if (shell) {
      shell.dataset.mode = "presenter";
      shell.dataset.open = "false";
    }
    if (panel) panel.hidden = true;
    if (presenter) presenter.hidden = false;
    document.getElementById("liam-tab")?.setAttribute("aria-expanded", "false");
    document.body.classList.add("elian-presenter-active");
  }
  function exitPresenter({ focus = true } = {}) {
    state.presenter = false;
    window.LIA_SPEECH?.stop();
    window.LIAM_LIP_SYNC?.stop();
    window.LIAM_ANIMATION?.clear();
    window.LIAM_MOVEMENT?.remove();
    const shell = document.getElementById("liam-shell"),
      presenter = document.getElementById("elian-presenter");
    if (shell) {
      shell.dataset.mode = "rest";
      shell.dataset.open = "false";
    }
    if (presenter) presenter.hidden = true;
    document.body.classList.remove("elian-presenter-active");
    window.LIAM_STATE?.set("idle");
    if (focus) document.getElementById("liam-tab")?.focus();
  }
  function announce(text) {
    add("liam", text);
    if (state.presenter) caption(text);
    if (state.flags.voice_enabled && !state.muted) {
      if (state.flags.lip_sync_enabled) window.LIAM_LIP_SYNC?.start();
      window.LIA_SPEECH?.speak(text);
    }
  }
  async function announceAsync(text) {
    add("liam", text);
    if (state.presenter) caption(text);
    if (state.flags.voice_enabled && !state.muted) {
      if (state.flags.lip_sync_enabled) window.LIAM_LIP_SYNC?.start();
      await window.LIA_SPEECH?.speakAsync(text);
    }
    return true;
  }
  async function saveInlineVisual() {
    const message = document.getElementById("elian-inline-message");
    if (message) message.textContent = "Guardando…";
    try {
      const current = state.visual || {},
        payload = {
          ...current,
          assistant_name: current.assistant_name || "LIAM",
          avatar_gender:
            document.getElementById("elian-inline-gender")?.value || "female",
          avatar_variant:
            document.getElementById("elian-inline-variant")?.value ||
            "afro_colombian_institutional",
          voice_gender:
            document.getElementById("elian-inline-voice")?.value || "female",
          motion_level:
            document.getElementById("elian-inline-motion")?.value || "full",
        };
      const data = await request("/elian/visual-config", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      applyVisual({ ...current, ...data.configuration });
      if (message) message.textContent = "Configuración aplicada.";
      window.LIAM_STATE.set("success");
    } catch (error) {
      if (message) message.textContent = error.message;
      window.LIAM_STATE.set("warning");
    }
  }
  async function refreshContext() {
    const local = window.LIAM_CONTEXT?.collect() || {};
    state.module = local.module_id || moduleNow();
    try {
      const d = await request(
        `/contexto?modulo=${encodeURIComponent(state.module)}`,
      );
      state.guide = d.guia;
      const detail = [
        local.tab_id ? `pestaña ${local.tab_id}` : "",
        local.modal_id ? "modal abierto" : "",
      ]
        .filter(Boolean)
        .join(" · ");
      document.getElementById("liam-context").textContent =
        `${d.guia.titulo} · ${d.rol}${detail ? ` · ${detail}` : ""} · orientación segura`;
      return d;
    } catch (e) {
      document.getElementById("liam-context").textContent = e.message;
      return null;
    }
  }
  async function open() {
    if (state.presenter) exitPresenter({ focus: false });
    state.open = true;
    document.getElementById("liam-panel").hidden = false;
    document.getElementById("liam-shell").dataset.open = "true";
    document.getElementById("liam-shell").dataset.mode = "conversation";
    document.getElementById("liam-tab").setAttribute("aria-expanded", "true");
    window.LIAM_STATE.set(
      state.flags.hologram_enabled ? "teleport_in" : "greeting",
    );
    try {
      await loadHistory();
    } catch (_) {
      state.historyLoaded = false;
    }
    await refreshContext();
    if (!state.welcomed) {
      state.welcomed = true;
      const name = userFirstName();
      const greeting = `${dayGreeting()}${name ? `, ${name}` : ""}. ¿Cómo estás? Soy ${state.visual?.assistant_name || "LIAM"}.`;
      await announceAsync(greeting);
      const contributor = state.profile?.development_contributor
        ? ` Contó con la colaboración de ${state.profile.development_contributor} en su desarrollo.`
        : "";
      const identity = state.profile?.identity_confirmed
        ? `Esta plataforma fue creada y diseñada por ${state.profile.designer}, el ${state.profile.created_date}.${contributor} Ahora voy a hacerte una presentación según los permisos de tu rol.`
        : `${contributor.trim()} Ahora voy a hacerte una presentación de la plataforma según los permisos de tu rol.`;
      await announceAsync(identity);
      await presentation();
    }
  }
  function close() {
    state.open = false;
    if (state.presenter) exitPresenter({ focus: false });
    window.LIAM_REALTIME?.stop();
    window.LIA_SPEECH?.stop();
    window.LIA_SPEECH?.cancelListening();
    window.LIAM_LIP_SYNC?.stop();
    window.LIAM_TOURS?.cancel();
    window.ELIAN_PLATFORM_TOUR?.cancel();
    window.LIAM_ANIMATION?.clear();
    window.LIAM_STATE.set("hidden");
    window.LIAM_3D?.unmount?.();
    document.getElementById("liam-panel").hidden = true;
    document.getElementById("liam-shell").dataset.open = "false";
    document.getElementById("liam-shell").dataset.mode = "rest";
    document.getElementById("liam-tab").setAttribute("aria-expanded", "false");
    document.getElementById("liam-tab").focus();
  }
  async function ask(question) {
    const input = document.getElementById("liam-question");
    const q = String(question || input?.value || "").trim();
    if (!q) return;
    state.lastUserCommand = q;
    if (input) input.value = "";
    const prior = state.history.slice(-6);
    add("user", q);
    remember("user", q);
    window.LIAM_STATE?.set("thinking");
    try {
      window.LIAM_TABLET?.show({
        type: "message",
        title: "Consultando",
        value: "Manual, contexto y permisos",
      });
      const context = window.LIAM_CONTEXT?.collect() || {};
      const d = await request("/chat", {
        method: "POST",
        body: JSON.stringify({
          message: q,
          module: context.module_id || state.module,
          screen_id: context.screen_id || "",
          help_id: context.active_help_id || "",
          screen_context: context,
          history: prior,
        }),
      });
      add("liam", d.message);
      renderStructured(d.ui);
      remember("assistant", d.message);
      showProposal(d.action_proposal);
      window.LIAM_STATE?.set(
        d.avatar_state === "guiding" ? "guiding" : "speaking",
      );
      for (const action of d.actions || []) {
        if (["highlight", "scroll_to"].includes(action.type))
          window.LIAM_ANIMATION?.highlight(action.target, d.message);
        else await runClientAction(action, d.request_id);
      }
      if (d.movement?.mode && d.movement.mode !== "none")
        await window.LIAM_MOVEMENT?.move(d.movement, state.flags);
      window.LIAM_TABLET?.show(
        d.tablet || { type: "message", title: "LIAM", value: d.message },
      );
      if (state.flags.voice_enabled) window.LIA_SPEECH?.speak(d.speech_text);
    } catch (e) {
      add("liam", e.message || "No fue posible consultar LIAM.");
      window.LIAM_STATE?.set("error");
    }
  }
  async function presentation() {
    if (!state.flags.platform_tour_enabled) {
      add(
        "liam",
        "El recorrido institucional está desactivado por configuración.",
      );
      window.LIAM_STATE.set("warning");
      return;
    }
    window.LIAM_STATE.set("reading_tablet");
    try {
      const d = await request("/elian/platform-tour");
      await window.ELIAN_PLATFORM_TOUR.start(d, {
        request,
        announce,
        announceAsync,
        enterPresenter,
        mode: "automatic",
      });
    } catch (e) {
      caption(e.message);
      add("liam", e.message);
      window.LIAM_STATE.set("error");
    }
  }
  async function explain() {
    const g = state.guide;
    if (!g) return;
    const msg = `${g.resumen} ${(g.pasos || []).map((x, i) => `${i + 1}. ${x}`).join(" ")}`;
    enterPresenter();
    announce(msg);
    window.LIAM_STATE.set("speaking");
    await showWhere();
  }
  async function showWhere() {
    const map = {
      dashboard: "dashboard.cuentame.upload",
      "base-maestra": "base-maestra.file.upload",
      "calendario-inteligente": "calendario.pending.list",
      "motor-documental": "motor-documental.file.upload",
      formatos: "formatos.template.file",
      talento: "talento.file.select",
      "salud-nutricion": "salud-nutricion.tab.dashboard",
      "planeacion-pedagogica": "planeacion-pedagogica.period",
      "gestion-pedagogica": "gestion-pedagogica.dashboard",
      "componente-psicosocial": "componente-psicosocial.unit",
      "gestion-coordinador": "gestion-coordinador.period",
      "familias-redes": "familias-redes.unit",
      "expediente-operativo-uca": "expediente-uca.year",
      "centro-planeacion": "centro-planeacion.period",
      administracion: "administracion.foundation.form",
      "configuracion-institucional": "configuracion-institucional.logo.file",
    };
    const id = map[state.module];
    if (!id) {
      add("liam", "Esta pantalla aún no tiene un control seguro registrado.");
      window.LIAM_STATE.set("warning");
      return false;
    }
    const moved = await window.LIAM_MOVEMENT?.moveToControl(id, {
      mode: "walk",
      walk_enabled: state.flags.walk_enabled !== false,
      message: "Control principal",
    });
    if (!moved && !window.LIAM_ANIMATION.highlight(id, "Control principal")) {
      add("liam", "Esta pantalla aún no tiene un control seguro registrado.");
      window.LIAM_STATE.set("warning");
      return false;
    }
    if (!moved) window.LIAM_STATE.set("guiding");
    add(
      "liam",
      "He resaltado el control principal registrado sin bloquear tus clics.",
    );
    return true;
  }
  async function listen() {
    if (!state.flags.voice_enabled) {
      add(
        "liam",
        "La conversación por voz está desactivada. Puedes escribirme.",
      );
      return;
    }
    if (state.voiceListening) {
      window.LIA_SPEECH?.stopListening?.();
      return;
    }
    const button = document.querySelector('[data-action="voice"]'),
      input = document.getElementById("liam-question"),
      context = document.getElementById("liam-context"),
      update = (value) => {
        if (input) input.value = value;
        if (context)
          context.textContent = value
            ? `Transcribiendo: ${value}`
            : "Escuchando… habla ahora.";
      };
    window.LIA_SPEECH?.stop("listen");
    state.voiceListening = true;
    if (button) {
      button.disabled = false;
      button.setAttribute("aria-pressed", "true");
      button.textContent = "⏹ Terminar";
    }
    if (context)
      context.textContent = "Escuchando… habla y verás aquí la transcripción.";
    if (input) {
      input.value = "";
      input.placeholder = "Tu voz aparecerá aquí mientras hablas…";
    }
    window.LIAM_STATE?.set("listening");
    try {
      let text;
      try {
        text = await window.LIA_SPEECH.listen({ onInterim: update });
      } catch (error) {
        if (
          !state.flags.local_stt_enabled ||
          !String(error?.message || "").includes("no pudo conectarse")
        )
          throw error;
        if (context)
          context.textContent = "Activando reconocimiento local seguro…";
        text = await window.LIA_SPEECH.listenLocal({ onInterim: update });
      }
      if (!text)
        throw new Error("No se obtuvo una pregunta. Inténtalo nuevamente.");
      if (input) input.value = text;
      if (context) context.textContent = "Orden de voz recibida. Procesando…";
      await ask(text);
    } catch (e) {
      add("liam", e.message || "No fue posible escuchar la pregunta.");
      window.LIAM_STATE?.set("warning");
      if (context)
        context.textContent =
          "Puedes intentarlo nuevamente o escribir tu pregunta.";
    } finally {
      state.voiceListening = false;
      if (button) {
        button.disabled = false;
        button.setAttribute("aria-pressed", "false");
        button.textContent = "🎙 Hablar";
      }
      if (input) input.placeholder = "Escribe tu pregunta para LIAM";
    }
  }
  async function realtime() {
    const button = document.querySelector('[data-action="realtime"]');
    if (window.LIAM_REALTIME?.active || window.LIAM_REALTIME?.connecting) {
      window.LIAM_REALTIME.stop();
      return;
    }
    if (!state.flags.realtime_voice_enabled) {
      add(
        "liam",
        "La conversación de voz en tiempo real está desactivada. Puedes usar Dictar o escribir.",
      );
      return;
    }
    try {
      window.LIA_SPEECH?.stop();
      if (button) {
        button.disabled = true;
        button.textContent = "Conectando…";
      }
      await window.LIAM_REALTIME.start({
        endpoint: `${apiBase()}/voice/realtime/call`,
        headers: headers(),
        module: state.module || moduleNow(),
      });
    } catch (error) {
      add(
        "liam",
        `${error.message || "No fue posible iniciar la conversación en vivo."} Activaré el dictado de respaldo.`,
      );
      window.LIAM_STATE?.set("warning");
      if (state.flags.local_stt_enabled) setTimeout(listen, 350);
    } finally {
      if (button) button.disabled = false;
    }
  }
  function handle(action) {
    if (action === "ask") ask();
    else if (action === "presentation") presentation();
    else if (action === "screen") explain();
    else if (action === "tour") {
      const tourByModule = {
        dashboard: "dashboard.platform",
        "base-maestra": "base-maestra.first-upload",
        "calendario-inteligente": "calendario.overview",
        "motor-documental": "motor-documental.first-read",
        formatos: "formatos.template-registration",
        talento: "talento.overview",
        "salud-nutricion": "salud-nutricion.overview",
        "planeacion-pedagogica": "planeacion-pedagogica.workflow",
        "gestion-pedagogica": "gestion-pedagogica.overview",
        "componente-psicosocial": "componente-psicosocial.overview",
        "gestion-coordinador": "gestion-coordinador.overview",
        "familias-redes": "familias-redes.overview",
        "expediente-operativo-uca": "expediente-uca.overview",
        "centro-planeacion": "centro-planeacion.overview",
        administracion: "administracion.overview",
        "configuracion-institucional": "configuracion-institucional.overview",
      };
      const tour = tourByModule[state.module];
      if (tour) window.LIAM_TOURS?.start(tour, state.flags);
      else showWhere();
    } else if (action === "elian-save-visual") saveInlineVisual();
    else if (action === "elian-pause") window.ELIAN_PLATFORM_TOUR?.pause();
    else if (action === "elian-resume") window.ELIAN_PLATFORM_TOUR?.resume();
    else if (action === "elian-repeat") window.ELIAN_PLATFORM_TOUR?.repeat();
    else if (action === "elian-next") window.ELIAN_PLATFORM_TOUR?.next();
    else if (action === "elian-prev") window.ELIAN_PLATFORM_TOUR?.previous();
    else if (action === "elian-skip") window.ELIAN_PLATFORM_TOUR?.skip();
    else if (action === "elian-mute") {
      state.muted = !state.muted;
      window.LIA_SPEECH?.setMuted?.(state.muted);
      if (state.muted) window.LIAM_REALTIME?.stop();
      syncMutePreference();
    } else if (action === "elian-cancel") {
      window.ELIAN_PLATFORM_TOUR?.cancel();
      exitPresenter();
    } else if (action === "where") showWhere();
    else if (action === "voice") listen();
    else if (action === "realtime") realtime();
    else if (action === "history-search") searchHistory().catch((error) => add("liam", error.message));
    else if (action === "history-more") loadHistory({ page: state.historyPage + 1, appendOlder: true }).catch((error) => add("liam", error.message));
    else if (action === "history-export") exportHistory().catch((error) => add("liam", error.message));
    else if (action === "history-export-xlsx") exportHistory("xlsx").catch((error) => add("liam", error.message));
    else if (action === "history-export-pdf") exportHistory("pdf").catch((error) => add("liam", error.message));
    else if (action === "history-sessions") viewHistorySessions().catch((error) => add("liam", error.message));
    else if (action === "history-stats") viewHistoryStats().catch((error) => add("liam", error.message));
    else if (action === "history-audit") auditHistory().catch((error) => add("liam", error.message));
    else if (action === "favorite-save") saveFavorite().catch((error) => add("liam", error.message));
    else if (action === "favorite-list") viewFavorites().catch((error) => add("liam", error.message));
    else if (action === "liam-center") {
      open();
      ask("Liam muéstrame el Centro Liam");
    }
    else if (action === "stop") {
      window.LIAM_REALTIME?.stop();
      window.LIA_SPEECH?.stop();
      window.LIAM_LIP_SYNC?.stop();
      window.LIAM_STATE.set("idle");
    }
  }
  async function boot() {
    try {
      const r = await fetch(`${apiBase()}/config`);
      const d = await r.json();
      state.flags = d.elian || d.liam || {};
      state.profile = d.platform_profile || {};
      if (!state.flags.enabled) return;
      await loadRuntime();
      mount();
      try {
        const visual = await request("/elian/visual-config");
        const config = visual.configuration || {};
        applyVisual(config);
        document.getElementById("elian-inline-config").hidden =
          !visual.editable;
        document.documentElement.style.setProperty(
          "--elian-primary",
          config.primary_color || "#123A63",
        );
        document.documentElement.style.setProperty(
          "--elian-secondary",
          config.secondary_color || "#16C6D8",
        );
      } catch (_) {}
      setInterval(() => {
        if (state.open && moduleNow() !== state.module) {
          window.LIAM_ANIMATION.clear();
          refreshContext();
        }
      }, 1200);
    } catch (e) {
      console.warn("ELIAN no se cargó; LIAM no se cargó:", e.message);
    }
  }
  async function bootIan() {
    if (state.booting || state.booted) return;
    state.booting = true;
    try {
      const authToken = token();
      if (!authToken) throw new Error("AUTH_PENDING");
      const r = await fetch(`${apiBase()}/config`, {
        cache: "no-store",
        headers: headers(),
      });
      if (!r.ok)
        throw new Error(
          r.status === 401 ? "AUTH_PENDING" : `CONFIG_${r.status}`,
        );
      const d = await r.json();
      state.flags = d.elian || d.liam || {};
      state.profile = d.platform_profile || {};
      if (!state.flags.enabled) {
        document.getElementById("liam-shell")?.remove();
        return;
      }
      mountIan();
      state.booted = true;
      try {
        await loadRuntime();
        syncMutePreference();
        document
          .getElementById("liam-tab")
          ?.setAttribute("data-runtime-ready", "true");
        window.LIAM_STATE?.set(state.open ? "greeting" : "idle");
      } catch (error) {
        document
          .getElementById("liam-tab")
          ?.setAttribute("data-runtime-warning", "true");
        console.warn("IAN visible en modo básico:", error.message);
      }
      try {
        const visual = await request("/elian/visual-config");
        const config = visual.configuration || {};
        applyVisual(config);
        document.getElementById("elian-inline-config").hidden =
          !visual.editable;
        document.documentElement.style.setProperty(
          "--elian-primary",
          config.primary_color || "#123A63",
        );
        document.documentElement.style.setProperty(
          "--elian-secondary",
          config.secondary_color || "#16C6D8",
        );
        document
          .getElementById("liam-tab")
          ?.setAttribute("data-profile-ready", "true");
      } catch (error) {
        document
          .getElementById("liam-tab")
          ?.setAttribute("data-profile-ready", "fallback");
        console.warn(
          "IAN usa su apariencia institucional de respaldo:",
          error.message,
        );
      }
      if (!state.contextTimer)
        state.contextTimer = setInterval(() => {
          if (state.open && moduleNow() !== state.module) {
            window.LIAM_ANIMATION?.clear();
            refreshContext();
          }
        }, 1200);
    } catch (error) {
      if (error.message !== "AUTH_PENDING")
        console.warn(
          "No fue posible consultar la activación de IAN:",
          error.message,
        );
      clearTimeout(state.bootTimer);
      state.bootTimer = setTimeout(bootIan, 1800);
    } finally {
      state.booting = false;
    }
  }
  document.addEventListener("elian:tour-completed", () =>
    setTimeout(() => exitPresenter(), 1400),
  );
  document.addEventListener("elian:tour-failed", () => {
    if (state.presenter)
      document.getElementById("elian-presenter")?.classList.add("has-error");
  });
  document.addEventListener("liam:platform-error", (event) => {
    const d = event.detail || {},
      diag = d.diagnostic || {};
    const message = `Incidente ${d.incident_id}. ${diag.cause || d.message} Solución: ${diag.solution || "Conserva el identificador para revisión."}`;
    document
      .getElementById("liam-shell")
      ?.setAttribute("data-has-incident", "true");
    add("liam", message);
    remember("assistant", message);
    window.LIAM_STATE?.set("warning");
    window.LIAM_TABLET?.show({
      type: "warning",
      title: d.incident_id || "Diagnóstico",
      value: diag.solution || d.message,
    });
    if (state.flags.voice_enabled && !state.muted)
      window.LIA_SPEECH?.speak(message);
  });
  document.addEventListener("liam:realtime-connecting", () => {
    document
      .querySelector('[data-action="realtime"]')
      ?.setAttribute("aria-pressed", "true");
    window.LIAM_STATE?.set("thinking");
  });
  document.addEventListener("liam:realtime-started", () => {
    state.realtimeSessionId = globalThis.crypto?.randomUUID?.() || `voice-${Date.now()}`;
    const b = document.querySelector('[data-action="realtime"]');
    if (b) {
      b.textContent = "⏹ Finalizar";
      b.setAttribute("aria-pressed", "true");
    }
    document.getElementById("liam-context").textContent =
      "Conversación en vivo activa. Habla con LIAN o interrúmpela cuando necesites.";
    add("liam", "Conversación en vivo activa. Te escucho.");
    window.LIAM_STATE?.set("listening");
  });
  document.addEventListener("liam:realtime-speech-started", () => {
    const input = document.getElementById("liam-question");
    if (input) input.value = "";
    document.getElementById("liam-context").textContent =
      "Escuchando en tiempo real…";
    window.LIAM_LIP_SYNC?.stop();
    window.LIAM_STATE?.set("listening");
  });
  document.addEventListener("liam:realtime-user-transcript", (event) => {
    const text = String(event.detail?.text || "").trim();
    if (text) {
      add("user", text);
      remember("user", text);
      saveVoiceTranscript("user", text);
      const input = document.getElementById("liam-question");
      if (input) input.value = text;
    }
  });
  document.addEventListener("liam:realtime-user-delta", (event) => {
    const input = document.getElementById("liam-question"),
      delta = String(event.detail?.delta || "");
    if (input && delta) input.value += delta;
    document.getElementById("liam-context").textContent =
      `Transcribiendo en vivo: ${input?.value || delta}`;
  });
  document.addEventListener("liam:realtime-assistant-transcript", (event) => {
    const text = String(event.detail?.text || "").trim();
    if (text) {
      add("liam", text);
      remember("assistant", text);
      saveVoiceTranscript("assistant", text);
      syncDataPresentation(text, true);
    }
    window.LIAM_LIP_SYNC?.stop();
    window.LIAM_STATE?.set("listening");
  });
  document.addEventListener("liam:realtime-assistant-delta", (event) => {
    syncDataPresentation(event.detail?.delta || "");
    window.LIAM_LIP_SYNC?.start();
    window.LIAM_STATE?.set("speaking");
  });
  document.addEventListener("ian:speech:start", (event) => {
    if (state.dataPresentation) state.dataPresentation.speechLength = Number(event.detail?.textLength || 0);
  });
  document.addEventListener("ian:speech:boundary", (event) => {
    const presentation = state.dataPresentation, length = Number(presentation?.speechLength || 0);
    if (!presentation?.items.length || !length) return;
    activatePresentationItem(Math.floor((Number(event.detail?.charIndex || 0) / length) * presentation.items.length));
  });
  document.addEventListener("ian:speech:end", () => syncDataPresentation("", true));
  document.addEventListener("liam:realtime-audio-level", (event) =>
    window.LIAM_LIP_SYNC?.update(
      Math.max(0.08, Number(event.detail?.level || 0) * 2.8),
    ),
  );
  document.addEventListener("liam:realtime-tool-call", async (event) => {
    const d = event.detail || {};
    try {
      const args = JSON.parse(d.args || "{}"),
        result = await request(`/tools/${encodeURIComponent(d.name)}`, {
          method: "POST",
          headers: { "X-Liam-Module": state.module || moduleNow() },
          body: JSON.stringify(args),
        });
      renderStructured(result.ui);
      if (result.result?.action_proposal) {
        showProposal(result.result.action_proposal);
        add("liam", result.result.message);
        remember("assistant", result.result.message);
      }
      if (d.name === "get_pending_activities_summary") {
        const query = result.result?.query || {};
        await runClientAction(
          {
            type: "navigate",
            module: "calendario-inteligente",
            period: query.period,
            scope: query.scope,
            target: "calendario.pending.list",
          },
          result.request_id,
        );
      }
      window.LIAM_REALTIME?.sendToolResult(d.callId, result.result);
    } catch (error) {
      window.LIAM_REALTIME?.sendToolResult(d.callId, {
        error:
          error.message || "No fue posible ejecutar la consulta autorizada.",
      });
    }
  });
  document.addEventListener("liam:realtime-error", (event) => {
    const b = document.querySelector('[data-action="realtime"]');
    if (b) {
      b.textContent = "📞 Conversar";
      b.disabled = false;
      b.setAttribute("aria-pressed", "false");
    }
    document.getElementById("liam-context").textContent =
      event.detail?.message ||
      "No fue posible mantener la conversación en vivo.";
    window.LIAM_LIP_SYNC?.stop();
    window.LIAM_STATE?.set("warning");
  });
  document.addEventListener("liam:realtime-ended", (event) => {
    const b = document.querySelector('[data-action="realtime"]');
    if (b) {
      b.textContent = "📞 Conversar";
      b.setAttribute("aria-pressed", "false");
    }
    const reason = event.detail?.reason,
      automatic = ["idle_timeout", "maximum_duration"].includes(reason);
    document.getElementById("liam-context").textContent = automatic
      ? "La conversación se cerró automáticamente para controlar el consumo."
      : "Conversación finalizada. Puedes volver a iniciarla cuando quieras.";
    request("/voice/realtime/event", {
      method: "POST",
      body: JSON.stringify({
        event: "ended",
        reason,
        duration: event.detail?.duration || 0,
        module: state.module,
        request_id: state.realtimeSessionId,
      }),
    }).catch(() => {});
    state.realtimeSessionId = "";
    window.LIAM_LIP_SYNC?.stop();
    window.LIAM_STATE?.set("idle");
  });
  window.LIAM = Object.freeze({
    open,
    close,
    ask,
    presentation,
    showWhere,
    refreshContext,
    announce,
    applyVisual,
    enterPresenter,
    exitPresenter,
    highlightElement,
  });
  window.IAN_BOOT = bootIan;
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", bootIan);
  else bootIan();
})();
