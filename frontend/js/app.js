console.info('[ALPHA73] app.js activo: fix mínimo Bienestarina frontend');
function getBackendUrl() {
    if (window.PRIMERA_INFANCIA_CONFIG?.sameOriginApi === true && window.location.origin) {
        return window.location.origin.replace(/\/$/, '');
    }
    const localMode = window.PRIMERA_INFANCIA_CONFIG?.localMode === true;
    const override = localMode
        ? (localStorage.getItem('PRIMERA_INFANCIA_BACKEND_URL') || sessionStorage.getItem('PRIMERA_INFANCIA_BACKEND_URL'))
        : '';
    if (override && /^https?:\/\//i.test(override.trim())) {
        return override.trim().replace(/\/$/, '');
    }

    const configUrl = window.PRIMERA_INFANCIA_CONFIG?.backendUrl || document.querySelector('meta[name="primera-infancia-backend-url"]')?.content;
    if (configUrl && /^https?:\/\//i.test(configUrl.trim())) {
        return configUrl.trim().replace(/\/$/, '');
    }

    const host = window.location.hostname || '127.0.0.1';
    const protocol = window.location.protocol && window.location.protocol.startsWith('http') ? window.location.protocol : 'http:';
    const port = window.location.port || '';
    const origin = window.location.origin && window.location.origin !== 'null' ? window.location.origin : '';

    // Cuando la plataforma se abre desde archivo local, se conserva el modo tradicional.
    if (window.location.protocol === 'file:' || !window.location.hostname) {
        return 'http://127.0.0.1:5000';
    }

    // Modo túnel online: el backend sirve también el frontend por el mismo puerto.
    // Así Cloudflare/ngrok exponen un solo enlace y las llamadas /api no intentan ir a :5000 remoto.
    const tunnelHostPatterns = [
        'trycloudflare.com',
        'ngrok-free.app',
        'ngrok.io',
        'loca.lt',
        'localhost.run'
    ];
    const isKnownTunnelHost = tunnelHostPatterns.some((pattern) => host.endsWith(pattern));
    const isSameOriginBackend = window.PRIMERA_INFANCIA_CONFIG?.sameOriginApi === true ||
        isKnownTunnelHost ||
        port === '5000' ||
        (protocol === 'https:' && !port);

    if (origin && isSameOriginBackend) {
        return origin;
    }

    return `${protocol}//${host}:5000`;
}

const backendUrl = getBackendUrl();
window.backendUrl = backendUrl;
window.getBackendUrl = getBackendUrl;
const AUTH_TOKEN_KEY = 'primeraInfanciaAuthToken';
const AUTH_USER_KEY = 'primeraInfanciaAuthUser';
let usuarioActual = null;

const MENU_POR_ROL = {
    SUPERADMIN: ['dashboard', 'buscador-beneficiarios', 'calendario-inteligente', 'administracion', 'panel-comercial', 'gerencia-general', 'acceso-compartido', 'configuracion-institucional', 'manual-operativo', 'ajustes', 'administrador-disenos', 'backups', 'calidad-datos', 'base-maestra', 'motor-plantillas', 'plantillas-oficiales', 'paquete-mensual', 'reportes-gerenciales', 'facturacion', 'planeacion-pedagogica', 'gestion-pedagogica', 'gestion-coordinador', 'cuentas-cobro', 'relacion-mes', 'formatos', 'nutricion', 'salud-nutricion', 'talento', 'cumplimiento', 'expediente-operativo-uca', 'biblioteca-icbf', 'motor-gestion-proyecto', 'centro-planeacion', 'supervision-calidad', 'familias-redes', 'componente-psicosocial', 'ambientes-protectores', 'integrity-stability'],
    GERENTE: ['dashboard', 'buscador-beneficiarios', 'calendario-inteligente', 'administracion', 'panel-comercial', 'gerencia-general', 'acceso-compartido', 'configuracion-institucional', 'manual-operativo', 'ajustes', 'administrador-disenos', 'backups', 'calidad-datos', 'base-maestra', 'motor-plantillas', 'plantillas-oficiales', 'paquete-mensual', 'reportes-gerenciales', 'facturacion', 'planeacion-pedagogica', 'gestion-pedagogica', 'gestion-coordinador', 'cuentas-cobro', 'relacion-mes', 'formatos', 'nutricion', 'salud-nutricion', 'talento', 'cumplimiento', 'expediente-operativo-uca', 'biblioteca-icbf', 'motor-gestion-proyecto', 'centro-planeacion', 'supervision-calidad', 'familias-redes', 'componente-psicosocial', 'ambientes-protectores', 'integrity-stability'],
    COORDINADOR: ['dashboard', 'buscador-beneficiarios', 'calendario-inteligente', 'ajustes', 'calidad-datos', 'base-maestra', 'planeacion-pedagogica', 'gestion-pedagogica', 'gestion-coordinador', 'formatos', 'relacion-mes', 'paquete-mensual', 'reportes-gerenciales', 'cumplimiento', 'expediente-operativo-uca', 'biblioteca-icbf', 'motor-gestion-proyecto', 'centro-planeacion', 'supervision-calidad', 'familias-redes', 'componente-psicosocial', 'ambientes-protectores', 'integrity-stability'],
    DOCENTE: ['dashboard', 'buscador-beneficiarios', 'calendario-inteligente', 'ajustes', 'planeacion-pedagogica', 'gestion-pedagogica', 'gestion-coordinador', 'formatos', 'expediente-operativo-uca', 'biblioteca-icbf', 'motor-gestion-proyecto', 'centro-planeacion', 'supervision-calidad'],
    NUTRICIONISTA: ['dashboard', 'buscador-beneficiarios', 'calendario-inteligente', 'ajustes', 'calidad-datos', 'base-maestra', 'salud-nutricion', 'nutricion', 'expediente-operativo-uca', 'biblioteca-icbf', 'motor-gestion-proyecto', 'centro-planeacion', 'supervision-calidad'],
    PSICOSOCIAL: ['dashboard', 'buscador-beneficiarios', 'calendario-inteligente', 'ajustes', 'planeacion-pedagogica', 'gestion-pedagogica', 'gestion-coordinador', 'expediente-operativo-uca', 'biblioteca-icbf', 'motor-gestion-proyecto', 'centro-planeacion', 'supervision-calidad', 'familias-redes', 'componente-psicosocial'],
    AUXILIAR_ADMINISTRATIVO: ['dashboard', 'buscador-beneficiarios', 'calendario-inteligente', 'ajustes', 'calidad-datos', 'base-maestra', 'motor-plantillas', 'plantillas-oficiales', 'paquete-mensual', 'reportes-gerenciales', 'facturacion', 'planeacion-pedagogica', 'gestion-pedagogica', 'gestion-coordinador', 'cuentas-cobro', 'relacion-mes', 'formatos', 'talento', 'cumplimiento', 'expediente-operativo-uca', 'biblioteca-icbf', 'motor-gestion-proyecto', 'centro-planeacion', 'supervision-calidad']
};
if (!MENU_POR_ROL.COORDINADOR.includes('talento')) MENU_POR_ROL.COORDINADOR.push('talento');
['SUPERADMIN','GERENTE','COORDINADOR','AUXILIAR_ADMINISTRATIVO'].forEach(rol=>{if(!MENU_POR_ROL[rol].includes('administrativo-financiero'))MENU_POR_ROL[rol].push('administrativo-financiero')});
['SUPERADMIN','GERENTE','COORDINADOR','AUXILIAR_ADMINISTRATIVO','DOCENTE','NUTRICIONISTA','PSICOSOCIAL'].forEach(rol=>{if(!MENU_POR_ROL[rol].includes('motor-documental'))MENU_POR_ROL[rol].push('motor-documental')});
['SUPERADMIN','GERENTE'].forEach(rol=>{if(!MENU_POR_ROL[rol].includes('integraciones-configuracion'))MENU_POR_ROL[rol].push('integraciones-configuracion')});

const allowedBaseExtensions = ['.xlsx', '.xls', '.xlsm', '.csv', '.txt', '.tsv', '.tab', '.dat', '.ods', '.html', '.htm', '.json', '.docx', '.pdf'];
const allowedTemplateExtensions = ['.xlsx', '.xls', '.xlsm', '.csv', '.txt', '.doc', '.docx', '.pdf', '.png', '.jpg', '.jpeg', '.zip', '.rar'];
const allowedNutritionExtensions = ['.xlsx', '.xls', '.xlsm', '.csv', '.txt'];
const allowedTalentExtensions = ['.xlsx', '.xls', '.xlsm', '.csv', '.txt', '.zip', '.docx'];
const allowedDocumentExtensions = ['.pdf', '.doc', '.docx', '.xlsx', '.xls', '.xlsm', '.csv', '.ppt', '.pptx', '.txt', '.png', '.jpg', '.jpeg', '.zip', '.rar'];

let estadoDiagnostico = {
    unidades: {},
    stats: {
        total_usuarios: 0,
        alertas_cobertura: 0,
        unidades_sin_cobertura: [],
        proximos_retiros: 0,
        proximos_retiros_lista: [],
        falta_nutricion: 0,
        grupos_edad_totales: {}
    }
};

window.estadoDiagnostico = estadoDiagnostico;
let plantillasRegistradas = [];
let talentoRegistrado = [];
let talentoEstructuraMaestra = null;
let estadoSeleccionCuentame = {
    archivoToken: '',
    archivoNombre: '',
    totalUsuarios: 0,
    unidades: [],
    seleccionadas: new Set()
};
window.estadoSeleccionCuentame = estadoSeleccionCuentame;

const GRUPOS_EDAD_DASHBOARD = [
    { clave: '0 A 6 MESES Y GESTANTES', etiqueta: '0 a 6 meses y gestantes', statId: 'stat-edad-0-6-gestantes', formato: '0_6_GESTANTES' },
    { clave: '6 A 11 MESES 29 DIAS', etiqueta: '6 a 11 meses y 29 días', statId: 'stat-edad-6-11', formato: '6_11_MESES' },
    { clave: '1 A 2 ANOS 11 MESES', etiqueta: '1 a 2 años 11 meses', statId: 'stat-edad-1-2', formato: '1_2_ANOS' },
    { clave: '3 A 5 ANOS 11 MESES', etiqueta: '3 a 5 años 11 meses', statId: 'stat-edad-3-5', formato: '3_5_ANOS' }
];

const UNIDADES_OPERATIVAS_INVALIDAS = new Set(['', 'ACTIVO', 'ACTIVA', 'INACTIVO', 'INACTIVA', 'PENDIENTE', 'RETIRADO', 'RETIRADA', 'SIN UNIDAD']);



const AUTH_TOKEN_COMPAT_KEYS = [
    AUTH_TOKEN_KEY,
    'token',
    'authToken',
    'accessToken',
    'jwt',
    'primeraInfanciaToken',
    'primeraInfanciaAuthToken'
];

const AUTH_USER_COMPAT_KEYS = [
    AUTH_USER_KEY,
    'user',
    'usuario',
    'authUser',
    'primeraInfanciaUser',
    'primeraInfanciaAuthUser'
];

function leerStorageSeguro(storage, key) {
    try {
        return storage.getItem(key);
    } catch (_) {
        return null;
    }
}

function escribirStorageSeguro(storage, key, value) {
    try {
        storage.setItem(key, value);
    } catch (_) {}
}

function borrarStorageSeguro(storage, key) {
    try {
        storage.removeItem(key);
    } catch (_) {}
}

function authToken() {
    for (const storage of [sessionStorage, localStorage]) {
        for (const key of AUTH_TOKEN_COMPAT_KEYS) {
            const token = leerStorageSeguro(storage, key);
            if (token && token !== 'null' && token !== 'undefined') return token;
        }
    }

    const user = authUser();
    return user?.token || user?.accessToken || '';
}

function authUser() {
    for (const storage of [sessionStorage, localStorage]) {
        for (const key of AUTH_USER_COMPAT_KEYS) {
            const raw = leerStorageSeguro(storage, key);
            if (!raw || raw === 'null' || raw === 'undefined') continue;
            try {
                return JSON.parse(raw);
            } catch (_) {}
        }
    }
    return null;
}

function guardarSesion(token, usuario, recordar = false) {
    limpiarSesionLocal(false);

    const storage = recordar ? localStorage : sessionStorage;
    const userData = { ...(usuario || {}), token };

    escribirStorageSeguro(storage, AUTH_TOKEN_KEY, token || '');
    escribirStorageSeguro(storage, AUTH_USER_KEY, JSON.stringify(userData));

    // Compatibilidad con funciones antiguas o módulos nuevos que busquen otros nombres.
    escribirStorageSeguro(storage, 'token', token || '');
    escribirStorageSeguro(storage, 'authToken', token || '');
    escribirStorageSeguro(storage, 'accessToken', token || '');
    escribirStorageSeguro(storage, 'primeraInfanciaToken', token || '');
    escribirStorageSeguro(storage, 'usuario', JSON.stringify(userData));
    escribirStorageSeguro(storage, 'authUser', JSON.stringify(userData));

    usuarioActual = userData;
}

function limpiarSesionLocal(recargarUsuario = true) {
    for (const storage of [sessionStorage, localStorage]) {
        AUTH_TOKEN_COMPAT_KEYS.forEach((key) => borrarStorageSeguro(storage, key));
        AUTH_USER_COMPAT_KEYS.forEach((key) => borrarStorageSeguro(storage, key));
    }
    if (recargarUsuario) usuarioActual = null;
}

function limpiarAuth() {
    limpiarSesionLocal();
}

function esUrlBackend(url) {
    return url.startsWith(backendUrl) || url.startsWith('/api/');
}

function prepararHeadersAutenticados(init = {}) {
    const token = authToken();
    const headers = new Headers(init.headers || {});
    if (token) {
        if (!headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);
        if (!headers.has('X-Auth-Token')) headers.set('X-Auth-Token', token);
    }
    return headers;
}

function appendAuthToken(url) {
    // Compatibilidad segura: los tokens se envían exclusivamente en encabezados HTTP.
    return String(url || '');
}
window.appendAuthToken = appendAuthToken;

const fetchOriginalPrimeraInfancia = window.fetch.bind(window);
window.fetch = function(input, init = {}) {
    const url = typeof input === 'string' ? input : input?.url || '';
    if (esUrlBackend(url)) {
        init = { ...init, headers: prepararHeadersAutenticados(init) };
    }
    return fetchOriginalPrimeraInfancia(input, init);
};


function nombreDescargaDesdeRespuesta(response, fallback = 'descarga') {
    const disposition = response.headers.get('Content-Disposition') || '';
    const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8) {
        try { return decodeURIComponent(utf8[1].replace(/["']/g, '')); } catch (_) {}
    }
    const normal = disposition.match(/filename="?([^";]+)"?/i);
    return normal?.[1] || fallback;
}

async function descargarArchivoAutenticado(url, filename = '') {
    const response = await fetch(url, { method: 'GET' });
    if (!response.ok) {
        let message = `No se pudo descargar el archivo (${response.status}).`;
        try {
            const data = await response.json();
            message = data.error || data.message || message;
        } catch (_) {}
        throw new Error(message);
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = filename || nombreDescargaDesdeRespuesta(response, 'descarga');
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    return true;
}

async function abrirArchivoAutenticado(url) {
    const response = await fetch(url, { method: 'GET' });
    if (!response.ok) {
        let message = `No se pudo abrir el archivo (${response.status}).`;
        try { message = (await response.json()).error || message; } catch (_) {}
        throw new Error(message);
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const opened = window.open(objectUrl, '_blank', 'noopener');
    if (!opened) {
        URL.revokeObjectURL(objectUrl);
        throw new Error('El navegador bloqueó la nueva pestaña. Habilita ventanas emergentes para este sitio.');
    }
    setTimeout(() => URL.revokeObjectURL(objectUrl), 120000);
    return true;
}

window.descargarArchivoAutenticado = descargarArchivoAutenticado;
window.abrirArchivoAutenticado = abrirArchivoAutenticado;

function mostrarLogin(mensaje = '') {
    document.getElementById('login-screen')?.classList.remove('hidden');
    document.getElementById('app-shell')?.classList.add('hidden');
    const msg = document.getElementById('login-message');
    if (msg && mensaje) msg.textContent = mensaje;
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function mostrarAplicacion() {
    document.getElementById('login-screen')?.classList.add('hidden');
    document.getElementById('app-shell')?.classList.remove('hidden');
}

async function iniciarSesionDesdeToken() {
    const token = authToken();
    if (!token) {
        mostrarLogin();
        return false;
    }
    try {
        const resp = await fetch(`${backendUrl}/api/auth/me`);
        if (!resp.ok) throw new Error('Sesión inválida');
        const data = await resp.json();
        usuarioActual = data.usuario || authUser();
        if (usuarioActual) {
            sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(usuarioActual));
        }
        if (usuarioActual?.debe_cambiar_password) {
            mostrarCambioPasswordObligatorio();
            return false;
        }
        if (typeof window.cargarIdentidadEfectiva === 'function') {
            await window.cargarIdentidadEfectiva(true);
        }
        mostrarAplicacion();
        aplicarPermisosFrontend();
        if (window.ThemeManager && typeof ThemeManager.initSessionTheme === 'function') {
            try { await ThemeManager.initSessionTheme(); } catch (_) {}
        }
        return true;
    } catch (error) {
        limpiarSesionLocal();
        mostrarLogin();
        return false;
    }
}

function crearIdSolicitudLogin() {
    try {
        if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
            return globalThis.crypto.randomUUID();
        }
    } catch (_) {}
    return `login-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function leerRespuestaJsonSegura(response) {
    const raw = await response.text();
    if (!raw) return {};
    try {
        return JSON.parse(raw);
    } catch (_) {
        return {
            error: response.ok
                ? 'El servidor respondió en un formato inesperado.'
                : `El servidor devolvió una respuesta técnica no válida (HTTP ${response.status}).`
        };
    }
}

function mensajeErrorLogin(response, data, requestId) {
    const code = String(data?.code || '').trim();
    const traceId = String(data?.trace_id || response.headers.get('X-Trace-Id') || '').trim();
    const logFile = String(data?.log_file || '').trim();

    if (response.status === 503 && code === 'LOGIN_DATABASE_BUSY') {
        return data?.error || 'La base local está ocupada. Espera dos segundos e intenta una sola vez.';
    }
    if (response.status === 429) {
        const retry = Number(data?.retry_after || 0);
        return retry
            ? `Demasiados intentos. Espera ${retry} segundos antes de volver a intentar.`
            : (data?.error || 'Demasiados intentos. Intenta nuevamente más tarde.');
    }
    if (response.status >= 500) {
        const parts = [data?.error || 'Error técnico del servidor.'];
        if (traceId) parts.push(`Código: ${traceId}.`);
        if (logFile) parts.push(`Registro: ${logFile}.`);
        else parts.push('Ejecuta DIAGNOSTICAR_LOGIN_TUNEL.bat y revisa data/logs.');
        return parts.join(' ');
    }
    return data?.error || `No se pudo iniciar sesión (HTTP ${response.status}; solicitud ${requestId}).`;
}

let loginEnCurso = false;

function esperarLogin(ms) {
    return new Promise((resolve) => setTimeout(resolve, Math.max(0, Number(ms) || 0)));
}

async function solicitarLoginConReintento(username, password, requestId, msg) {
    const maxIntentos = 2;
    for (let intento = 0; intento < maxIntentos; intento += 1) {
        const controller = new AbortController();
        // PostgreSQL remoto mediante el proxy público de Railway puede tardar
        // varios segundos en el primer checkout/conexión. Cinco segundos
        // cancelaba logins válidos justo antes de recibir la respuesta.
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        try {
            const loginUrl = `${backendUrl}/api/auth/login`;
            console.warn('[AUTH_BROWSER_DEBUG] request', {
                requestId,
                pageUrl: location.href,
                pageOrigin: location.origin,
                backendUrl,
                url: loginUrl,
                method: 'POST',
                json: { username, password: '[REDACTED]' },
                passwordLength: String(password || '').length
            });
            const resp = await fetchOriginalPrimeraInfancia(loginUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Client-Request-ID': requestId
                },
                body: JSON.stringify({ username, password }),
                signal: controller.signal
            });
            const data = await leerRespuestaJsonSegura(resp);
            console.warn('[AUTH_BROWSER_DEBUG] response', {
                requestId,
                finalUrl: resp.url,
                status: resp.status,
                ok: resp.ok,
                headers: {
                    requestId: resp.headers.get('X-Auth-Request-ID') || resp.headers.get('X-Client-Request-ID'),
                    instanceId: resp.headers.get('X-Auth-Instance-ID'),
                    environment: resp.headers.get('X-Auth-Environment'),
                    databaseBackend: resp.headers.get('X-Auth-Database-Backend'),
                    databaseTarget: resp.headers.get('X-Auth-Database-Target'),
                    envSha256: resp.headers.get('X-Auth-Env-SHA256')
                },
                body: data && typeof data === 'object'
                    ? { ...data, token: data.token ? '[REDACTED]' : data.token }
                    : data
            });
            const busy = resp.status === 503 && String(data?.code || '') === 'LOGIN_DATABASE_BUSY';
            if (busy && intento + 1 < maxIntentos) {
                const retryMs = Math.min(1000, Math.max(250, Number(data?.retry_after || 1) * 500));
                if (msg) msg.textContent = 'La base estaba ocupada. Reintentando automáticamente...';
                await esperarLogin(retryMs);
                continue;
            }
            return { resp, data };
        } catch (error) {
            if (error?.name === 'AbortError') {
                throw new Error(`El servidor no respondió a tiempo. Solicitud: ${requestId}. Revisa data/logs.`);
            }
            throw error;
        } finally {
            clearTimeout(timeoutId);
        }
    }
    throw new Error(`No fue posible completar el inicio de sesión. Solicitud: ${requestId}.`);
}

function configurarFormularioLogin() {
    const form = document.getElementById('login-form');
    if (!form || form.dataset.bound === '1') return;
    form.dataset.bound = '1';
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (loginEnCurso) return;

        const username = document.getElementById('login-username')?.value.trim();
        const password = document.getElementById('login-password')?.value || '';
        const recordar = document.getElementById('login-recordar')?.checked || false;
        const msg = document.getElementById('login-message');
        const submitButton = form.querySelector('button[type="submit"]');
        const requestId = crearIdSolicitudLogin();

        loginEnCurso = true;
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.setAttribute('aria-busy', 'true');
            submitButton.dataset.originalText = submitButton.textContent || 'Ingresar';
            submitButton.textContent = 'Validando...';
        }
        if (msg) msg.textContent = 'Validando credenciales...';

        try {
            const { resp, data } = await solicitarLoginConReintento(username, password, requestId, msg);
            if (!resp.ok) {
                throw new Error(mensajeErrorLogin(resp, data, requestId));
            }
            if (!data.token || !data.usuario) {
                throw new Error(`El servidor no devolvió una sesión válida. Solicitud: ${requestId}.`);
            }
            limpiarSesionLocal();
            guardarSesion(data.token, data.usuario, recordar);
            if (msg) msg.textContent = '';
            if (data.usuario?.debe_cambiar_password) {
                mostrarCambioPasswordObligatorio();
            } else {
                location.reload();
            }
        } catch (error) {
            if (msg) {
                msg.textContent = error?.message || 'No fue posible comunicarse con el servidor. Revisa el túnel y ejecuta el diagnóstico.';
            }
        } finally {
            loginEnCurso = false;
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.removeAttribute('aria-busy');
                submitButton.textContent = submitButton.dataset.originalText || 'Ingresar';
            }
        }
    });
}

let passwordResetToken = '';

function mostrarPanelRestablecimiento({ token = '', mostrarCodigo = false, codigo = '', mensaje = '' } = {}) {
    passwordResetToken = token || '';
    mostrarLogin();
    document.getElementById('login-form')?.classList.add('hidden');
    document.getElementById('forced-password-panel')?.classList.add('hidden');
    document.getElementById('password-reset-panel')?.classList.remove('hidden');
    document.getElementById('reset-code-container')?.classList.toggle('hidden', !mostrarCodigo);
    const codeInput = document.getElementById('reset-code');
    if (codeInput) codeInput.value = codigo || '';
    const codeBox = document.getElementById('local-recovery-code-box');
    if (codeBox) {
        codeBox.classList.toggle('hidden', !codigo);
        codeBox.textContent = codigo
            ? `Código temporal: ${codigo}. Se muestra una sola vez y vence pronto.`
            : '';
    }
    const modeMessage = document.getElementById('reset-mode-message');
    if (modeMessage && mensaje) modeMessage.textContent = mensaje;
    const resetMessage = document.getElementById('reset-password-message');
    if (resetMessage) resetMessage.textContent = '';
}

async function recuperarPassword() {
    const identifier = document.getElementById('login-username')?.value.trim();
    const msg = document.getElementById('login-message');
    if (!identifier) {
        if (msg) msg.textContent = 'Escribe el usuario o correo para iniciar la recuperación.';
        return;
    }
    if (msg) msg.textContent = 'Generando instrucciones seguras...';
    try {
        const response = await fetchOriginalPrimeraInfancia(`${backendUrl}/api/auth/recuperar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: identifier })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const retry = Number(data.retry_after || 0);
            throw new Error(retry
                ? `Demasiados intentos. Espera ${retry} segundos antes de volver a solicitar recuperación.`
                : (data.error || 'No se pudo iniciar la recuperación.'));
        }
        if (data.delivery === 'local_code' && data.local_recovery_code) {
            mostrarPanelRestablecimiento({
                token: data.local_recovery_code,
                mostrarCodigo: true,
                codigo: data.local_recovery_code,
                mensaje: 'Modo local: usa el código temporal mostrado. Esta alternativa se desactiva cuando el túnel público está activo.'
            });
            return;
        }
        if (data.delivery === 'development_token' && data.development_reset_token) {
            mostrarPanelRestablecimiento({
                token: data.development_reset_token,
                mostrarCodigo: true,
                codigo: data.development_reset_token,
                mensaje: 'Modo de desarrollo: token temporal de un solo uso.'
            });
            return;
        }
        if (msg) {
            msg.textContent = data.delivery === 'email'
                ? 'Revisa tu correo. El enlace es de un solo uso y vence pronto.'
                : (data.message || 'Si la cuenta existe, recibirás instrucciones de recuperación.');
        }
    } catch (error) {
        if (msg) msg.textContent = error.message || 'No se pudo generar la recuperación. Revisa la conexión e inténtalo de nuevo.';
    }
}

function mostrarCambioPasswordObligatorio() {
    mostrarLogin();
    document.getElementById('login-form')?.classList.add('hidden');
    document.getElementById('password-reset-panel')?.classList.add('hidden');
    document.getElementById('forced-password-panel')?.classList.remove('hidden');
}

function leerTokenRestablecimiento() {
    const queryToken = new URLSearchParams(window.location.search).get('reset_token') || '';
    const hash = String(window.location.hash || '').replace(/^#/, '');
    const hashQuery = hash.includes('?') ? hash.slice(hash.indexOf('?') + 1) : hash;
    const fragmentToken = new URLSearchParams(hashQuery).get('reset_token') || '';
    return fragmentToken || queryToken;
}

function prepararRestablecimientoDesdeUrl() {
    const token = leerTokenRestablecimiento();
    if (!token) return false;
    // El fragmento no se envía al servidor y se retira de la barra de direcciones.
    history.replaceState(null, '', `${window.location.pathname}#restablecer`);
    mostrarPanelRestablecimiento({
        token,
        mostrarCodigo: false,
        mensaje: 'El enlace es de un solo uso. Crea una contraseña nueva antes de que expire.'
    });
    return true;
}

function volverAlLoginDesdeRecuperacion() {
    passwordResetToken = '';
    history.replaceState(null, '', `${window.location.pathname}#login`);
    document.getElementById('password-reset-panel')?.classList.add('hidden');
    document.getElementById('forced-password-panel')?.classList.add('hidden');
    document.getElementById('login-form')?.classList.remove('hidden');
    const codeInput = document.getElementById('reset-code');
    if (codeInput) codeInput.value = '';
    const resetPassword = document.getElementById('reset-password');
    const resetConfirm = document.getElementById('reset-password-confirm');
    if (resetPassword) resetPassword.value = '';
    if (resetConfirm) resetConfirm.value = '';
}

async function restablecerPasswordDesdeEnlace() {
    const typedCode = document.getElementById('reset-code')?.value.trim() || '';
    const token = typedCode || passwordResetToken;
    const password = document.getElementById('reset-password')?.value || '';
    const confirmPassword = document.getElementById('reset-password-confirm')?.value || '';
    const msg = document.getElementById('reset-password-message');
    if (!token) { if (msg) msg.textContent = 'Escribe el código o abre nuevamente el enlace de recuperación.'; return; }
    if (!password) { if (msg) msg.textContent = 'Escribe una contraseña nueva.'; return; }
    if (password !== confirmPassword) { if (msg) msg.textContent = 'Las contraseñas no coinciden.'; return; }
    if (msg) msg.textContent = 'Validando recuperación...';
    try {
        const response = await fetchOriginalPrimeraInfancia(`${backendUrl}/api/auth/restablecer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, password })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const retry = Number(data.retry_after || 0);
            throw new Error(retry
                ? `Demasiados intentos. Espera ${retry} segundos.`
                : (data.error || 'No se pudo cambiar la contraseña.'));
        }
        volverAlLoginDesdeRecuperacion();
        const loginMsg = document.getElementById('login-message');
        if (loginMsg) loginMsg.textContent = data.message || 'Contraseña actualizada. Inicia sesión.';
    } catch (error) {
        if (msg) msg.textContent = error.message || 'No se pudo cambiar la contraseña.';
    }
}

async function cambiarPasswordObligatorio() {
    const current = document.getElementById('forced-current-password')?.value || '';
    const password = document.getElementById('forced-new-password')?.value || '';
    const confirm = document.getElementById('forced-new-password-confirm')?.value || '';
    const msg = document.getElementById('forced-password-message');
    if (password !== confirm) { if (msg) msg.textContent = 'Las contraseñas no coinciden.'; return; }
    try {
        const response = await fetch(`${backendUrl}/api/auth/cambiar-password`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password_actual: current, password_nueva: password })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'No se pudo cambiar la contraseña.');
        limpiarSesionLocal();
        // La clave nueva ya quedó persistida como hash en PostgreSQL. Retirar
        // del DOM la clave inicial evita que el formulario o el autocompletado
        // parezcan restaurarla al volver al login.
        ['forced-current-password', 'forced-new-password', 'forced-new-password-confirm', 'login-password'].forEach((id) => {
            const input = document.getElementById(id);
            if (input) input.value = '';
        });
        document.getElementById('forced-password-panel')?.classList.add('hidden');
        document.getElementById('login-form')?.classList.remove('hidden');
        if (msg) msg.textContent = '';
        const loginMsg = document.getElementById('login-message');
        if (loginMsg) loginMsg.textContent = 'Contraseña guardada permanentemente. Escribe la nueva clave para iniciar sesión; si el navegador sugiere la anterior, elimínala o actualízala en su gestor de contraseñas.';
        document.getElementById('login-password')?.focus();
    } catch (error) {
        if (msg) msg.textContent = error.message || 'No se pudo cambiar la contraseña.';
    }
}

window.restablecerPasswordDesdeEnlace = restablecerPasswordDesdeEnlace;
window.volverAlLoginDesdeRecuperacion = volverAlLoginDesdeRecuperacion;
window.cambiarPasswordObligatorio = cambiarPasswordObligatorio;

async function cerrarSesion() {
    try { await fetch(`${backendUrl}/api/auth/logout`, { method: 'POST' }); } catch (_) {}
    if (typeof window.limpiarIdentidadInstitucional === 'function') {
        try { await window.limpiarIdentidadInstitucional(); } catch (_) {}
    }
    limpiarSesionLocal();
    location.reload();
}

function aplicarPermisosFrontend() {
    const user = usuarioActual || authUser();
    if (!user) return;
    const rol = user.rol || 'DOCENTE';
    const permitidos = new Set([...(MENU_POR_ROL[rol] || []), ...((user.menus || []))]);
    document.querySelectorAll('[id^="nav-"]').forEach((btn) => {
        const seccion = btn.id.replace('nav-', '');
        btn.classList.toggle('hidden', !permitidos.has(seccion));
    });
    if (window.MenuInstitucionalLateral && typeof MenuInstitucionalLateral.aplicarPermisos === 'function') {
        MenuInstitucionalLateral.aplicarPermisos();
    }
    const info = document.getElementById('auth-user-info');
    if (info) {
        info.innerHTML = `<div class="text-right"><p class="text-sm font-semibold text-slate-200">${escaparHtml(user.nombre_completo || user.username || '')}</p><p class="text-[11px] text-slate-400">${escaparHtml(user.rol || '')} · ${escaparHtml(user.fundacion_nombre || 'Fundación')}</p></div>`;
    }
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

async function initApp() {
    if (typeof lucide !== 'undefined') lucide.createIcons();
    configurarFormularioLogin();
    if (prepararRestablecimientoDesdeUrl()) return;
    const autorizado = await iniciarSesionDesdeToken();
    if (!autorizado) return;
    lucide.createIcons();
    if (window.MenuInstitucionalLateral && typeof MenuInstitucionalLateral.init === 'function') {
        MenuInstitucionalLateral.init();
    }
    const seccionInicial = (window.location.hash || '').replace('#', '') || 'dashboard';
    mostrarSeccion(['dashboard', 'buscador-beneficiarios', 'calendario-inteligente', 'administracion', 'panel-comercial', 'gerencia-general', 'acceso-compartido', 'configuracion-institucional', 'manual-operativo', 'ajustes', 'administrador-disenos', 'backups', 'calidad-datos', 'base-maestra', 'motor-plantillas', 'plantillas-oficiales', 'paquete-mensual', 'reportes-gerenciales', 'facturacion', 'formatos', 'nutricion', 'salud-nutricion', 'talento', 'cumplimiento', 'planeacion-pedagogica', 'gestion-pedagogica', 'gestion-coordinador', 'cuentas-cobro', 'relacion-mes', 'expediente-operativo-uca', 'biblioteca-icbf', 'motor-gestion-proyecto', 'centro-planeacion', 'supervision-calidad', 'familias-redes', 'componente-psicosocial', 'ambientes-protectores', 'integrity-stability', 'motor-documental'].includes(seccionInicial) ? seccionInicial : 'dashboard');

    const inputExcel = document.getElementById('input-excel');
    const dropZone = document.getElementById('drop-zone');

    inputExcel.addEventListener('change', (e) => {
        const nombre = e.target.files[0]?.name || 'Arrastra o selecciona la base de datos (.xlsx, .xls, .xlsm, .csv, .txt, .tsv, .json, .docx o .pdf)';
        document.getElementById('texto-archivo').innerText = nombre;
        resetSelectorUnidadesCuentame();
        limpiarMensajes();
    });

    dropZone.addEventListener('dragover', (event) => {
        event.preventDefault();
        dropZone.classList.add('border-indigo-500', 'bg-slate-900/70');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('border-indigo-500', 'bg-slate-900/70');
    });

    dropZone.addEventListener('drop', (event) => {
        event.preventDefault();
        dropZone.classList.remove('border-indigo-500', 'bg-slate-900/70');
        const file = event.dataTransfer.files[0];
        if (file) {
            document.getElementById('input-excel').files = event.dataTransfer.files;
            document.getElementById('texto-archivo').innerText = file.name;
            resetSelectorUnidadesCuentame();
            limpiarMensajes();
        }
    });

    fetchPlantillas();
    fetchTalento();
    inicializarPeriodoEntregable();
    document.getElementById('entregable-periodo')?.addEventListener('change', fetchEntregablesOperacion);
    fetchDocumentosInstitucionales();
    fetchEntregablesOperacion();
    evaluarOperacionICBF(false);
    if (typeof calendarioInteligenteInit === 'function') calendarioInteligenteInit(); // dashboard widget
    if (window.CruceBases) CruceBases.init();
    if (typeof cargarPanelPrincipalBaseMaestra === 'function') cargarPanelPrincipalBaseMaestra({ silent: true });
    if (typeof cargarConfiguracionInstitucional === 'function') cargarConfiguracionInstitucional(true);
}

function mostrarSeccion(seccion) {
    const user = usuarioActual || authUser();
    const rol = user?.rol || 'DOCENTE';
    const permitidos = new Set([...(MENU_POR_ROL[rol] || []), ...((user?.menus || []))]);
    if (permitidos.size && !permitidos.has(seccion)) {
        seccion = permitidos.has('dashboard') ? 'dashboard' : Array.from(permitidos)[0];
    }
    if (window.location.hash !== `#${seccion}`) {
        history.replaceState(null, '', `#${seccion}`);
    }
    const afSection = document.getElementById('administrativo-financiero');
    if (afSection) afSection.classList.toggle('hidden', seccion !== 'administrativo-financiero');
    const icSection = document.getElementById('integraciones-configuracion');
    if (icSection) icSection.classList.toggle('hidden', seccion !== 'integraciones-configuracion');
    ['dashboard', 'buscador-beneficiarios', 'calendario-inteligente', 'administracion', 'panel-comercial', 'gerencia-general', 'acceso-compartido', 'configuracion-institucional', 'manual-operativo', 'ajustes', 'administrador-disenos', 'backups', 'calidad-datos', 'base-maestra', 'motor-plantillas', 'plantillas-oficiales', 'paquete-mensual', 'reportes-gerenciales', 'facturacion', 'formatos', 'nutricion', 'salud-nutricion', 'talento', 'cumplimiento', 'planeacion-pedagogica', 'gestion-pedagogica', 'gestion-coordinador', 'cuentas-cobro', 'relacion-mes', 'expediente-operativo-uca', 'biblioteca-icbf', 'motor-gestion-proyecto', 'centro-planeacion', 'supervision-calidad', 'familias-redes', 'componente-psicosocial', 'ambientes-protectores', 'integrity-stability', 'motor-documental'].forEach(id => {
        const section = document.getElementById(id);
        if (section) section.classList.toggle('hidden', id !== seccion);
    });
    ['nav-dashboard', 'nav-buscador-beneficiarios', 'nav-calendario-inteligente', 'nav-administracion', 'nav-panel-comercial', 'nav-gerencia-general', 'nav-acceso-compartido', 'nav-configuracion-institucional', 'nav-manual-operativo', 'nav-ajustes', 'nav-administrador-disenos', 'nav-backups', 'nav-calidad-datos', 'nav-base-maestra', 'nav-motor-plantillas', 'nav-plantillas-oficiales', 'nav-paquete-mensual', 'nav-reportes-gerenciales', 'nav-facturacion', 'nav-formatos', 'nav-nutricion', 'nav-salud-nutricion', 'nav-talento', 'nav-cumplimiento', 'nav-planeacion-pedagogica', 'nav-gestion-pedagogica', 'nav-gestion-coordinador', 'nav-cuentas-cobro', 'nav-relacion-mes', 'nav-expediente-operativo-uca', 'nav-biblioteca-icbf', 'nav-motor-gestion-proyecto', 'nav-centro-planeacion', 'nav-supervision-calidad', 'nav-familias-redes', 'nav-componente-psicosocial', 'nav-ambientes-protectores', 'nav-integrity-stability', 'nav-motor-documental'].forEach(id => {
        const boton = document.getElementById(id);
        if (boton) {
            boton.classList.toggle('bg-indigo-600/10', id === `nav-${seccion}`);
            boton.classList.toggle('text-indigo-400', id === `nav-${seccion}`);
            boton.classList.toggle('text-slate-400', id !== `nav-${seccion}`);
        }
    });
    if (window.MenuInstitucionalLateral && typeof MenuInstitucionalLateral.marcarActivo === 'function') {
        MenuInstitucionalLateral.marcarActivo(seccion);
    }
    if (seccion === 'dashboard' && typeof cargarPanelPrincipalBaseMaestra === 'function') {
        cargarPanelPrincipalBaseMaestra({ silent: true });
    }
    if (seccion === 'buscador-beneficiarios' && window.BuscadorGlobalBeneficiarios && typeof BuscadorGlobalBeneficiarios.showPanel === 'function') {
        BuscadorGlobalBeneficiarios.showPanel();
    }
    if (seccion === 'calendario-inteligente' && typeof calendarioInteligenteInit === 'function') {
        calendarioInteligenteInit();
    }
    if (seccion === 'expediente-operativo-uca' && typeof giuInit === 'function') {
        giuInit();
    }
    if (seccion === 'biblioteca-icbf' && typeof bibliotecaIcbfInit === 'function') {
        bibliotecaIcbfInit();
    }
    if (seccion === 'motor-gestion-proyecto' && typeof motorGestionProyectoInit === 'function') {
        motorGestionProyectoInit();
    }
    if (seccion === 'centro-planeacion' && typeof centroPlaneacionInit === 'function') {
        centroPlaneacionInit();
    }
    if (seccion === 'supervision-calidad' && typeof supervisionCalidadInit === 'function') {
        supervisionCalidadInit();
    }
    if (seccion === 'ambientes-protectores' && typeof ambientesProtectoresInit === 'function') {
        ambientesProtectoresInit();
    }
    if (seccion === 'administrativo-financiero' && typeof administrativoFinancieroInit === 'function') {
        administrativoFinancieroInit();
    }
    if (seccion === 'integraciones-configuracion' && typeof integracionesConfiguracionInit === 'function') {
        integracionesConfiguracionInit();
    }
    if (seccion === 'familias-redes' && typeof familiasRedesInit === 'function') {
        familiasRedesInit();
    }
    if (seccion === 'componente-psicosocial' && typeof componentePsicosocialInit === 'function') {
        componentePsicosocialInit();
    }
    if (seccion === 'integrity-stability' && typeof integrityStabilityInit === 'function') {
        integrityStabilityInit();
    }
    if (seccion === 'motor-documental' && typeof idpDocumentalInit === 'function') {
        idpDocumentalInit();
    }
    if (seccion === 'motor-documental' && typeof centroDocumentalInit === 'function') {
        centroDocumentalInit();
    }
    if (seccion === 'planeacion-pedagogica' && typeof ppInit === 'function') {
        ppInit();
    }
    if (seccion === 'gestion-pedagogica' && typeof gpMostrarVista === 'function') {
        gpMostrarVista('dashboard');
    }
    if (seccion === 'gestion-coordinador' && typeof gcInit === 'function') {
        gcInit();
    }
    if (seccion === 'salud-nutricion' && typeof snInit === 'function') {
        snInit();
    }
    if (seccion === 'administracion') {
        cargarAdministracion();
    }
    if (seccion === 'facturacion' && typeof facturacionInit === 'function') {
        facturacionInit();
    }
    if (seccion === 'panel-comercial' && typeof panelComercialInit === 'function') {
        panelComercialInit();
    }
    if (seccion === 'gerencia-general' && typeof gerenciaGeneralInit === 'function') {
        gerenciaGeneralInit();
    }
    if (seccion === 'acceso-compartido' && typeof accesoCompartidoInit === 'function') {
        accesoCompartidoInit();
    }
    if (seccion === 'ajustes' && typeof ajustesUIInit === 'function') {
        ajustesUIInit();
    }
    if (seccion === 'configuracion-institucional' && typeof configInstitucionalInit === 'function') {
        configInstitucionalInit();
    }
    if (seccion === 'manual-operativo' && typeof manualOperativoInit === 'function') {
        manualOperativoInit();
    }
    if (seccion === 'administrador-disenos' && window.ThemeManager && typeof ThemeManager.initAdmin === 'function') {
        ThemeManager.initAdmin();
        if (typeof ThemeManager.bindBuilderEvents === 'function') ThemeManager.bindBuilderEvents();
    }
    if (seccion === 'backups' && typeof backupsInit === 'function') {
        backupsInit();
    }
    if (seccion === 'calidad-datos' && typeof calidadDatosInit === 'function') {
        calidadDatosInit();
    }
    if (seccion === 'base-maestra' && typeof baseMaestraInit === 'function') {
        baseMaestraInit();
    }
    if (seccion === 'motor-plantillas' && typeof motorPlantillasInit === 'function') {
        motorPlantillasInit();
    }
    if (seccion === 'plantillas-oficiales' && typeof plantillasOficialesInit === 'function') {
        plantillasOficialesInit();
    }
    if (seccion === 'paquete-mensual' && typeof pmInit === 'function') {
        pmInit();
    }
    if (seccion === 'reportes-gerenciales' && typeof rgInit === 'function') {
        rgInit();
    }
    if (seccion === 'cuentas-cobro') {
        inicializarCuentasCobro();
    }
    if (seccion === 'relacion-mes') {
        inicializarRelacionMes();
    }
}

function limpiarMensajes() {
    const box = document.getElementById('message-box');
    box.className = 'mt-4 hidden rounded-xl px-4 py-3 text-sm';
    box.innerText = '';
}

function mostrarMensaje(id, texto, tipo = 'success') {
    const box = document.getElementById(id);
    if (!box) return;
    box.className = `mt-4 rounded-xl px-4 py-3 text-sm ${tipo === 'success' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'}`;
    box.innerText = texto;
    box.classList.remove('hidden');
}

function validarArchivo(file, allowedExtensions, tamanoMaxMB) {
    if (!file) {
        return 'No se seleccionó ningún archivo.';
    }
    const nombre = file.name.toLowerCase();
    const valido = allowedExtensions.some(ext => nombre.endsWith(ext));
    if (!valido) {
        return `Extensión no permitida. Utiliza ${allowedExtensions.join(', ')}.`;
    }
    const tamanoMb = file.size / 1024 / 1024;
    if (tamanoMb > tamanoMaxMB) {
        return `El archivo es demasiado grande. Tamaño máximo ${tamanoMaxMB} MB.`;
    }
    return null;
}

function actualizarBarraProgreso(valor) {
    const contenedor = document.getElementById('progress-container');
    const barra = document.getElementById('progress-bar');
    if (!contenedor || !barra) return;
    contenedor.classList.remove('hidden');
    barra.style.width = `${valor}%`;
}

function ocultarProgreso() {
    const contenedor = document.getElementById('progress-container');
    const barra = document.getElementById('progress-bar');
    if (!contenedor || !barra) return;
    barra.style.width = '0%';
    contenedor.classList.add('hidden');
}

function mostrarCargando(texto = 'Procesando base de datos y formatos oficiales...') {
    const overlay = document.getElementById('loading-overlay');
    const label = document.getElementById('loading-text');
    if (label) label.innerText = texto;
    if (overlay) overlay.classList.remove('hidden');
}

function ocultarCargando() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.add('hidden');
}

function manejarRespuestaJson(respuesta) {
    if (!respuesta.ok) {
        if (respuesta.status === 401) {
            limpiarAuth();
            mostrarLogin('Sesión vencida. Ingrese nuevamente.');
        }
        return respuesta.json().then(json => {
            const error = new Error(json.error || 'Error en el servidor');
            error.status = respuesta.status;
            error.data = json;
            throw error;
        });
    }
    return respuesta.json();
}


function escaparHtml(valor) {
    return String(valor ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function normalizarFiltro(valor) {
    return String(valor || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim()
        .toUpperCase()
        .replace(/\s+/g, ' ');
}

function normalizarGrupoEdad(valor, tipoBeneficiario = '') {
    const grupo = normalizarFiltro(valor);
    const tipo = normalizarFiltro(tipoBeneficiario);

    if (tipo.includes('GESTANTE') || grupo.includes('GESTANTE') || grupo.includes('0 A 5') || grupo.includes('0 A 6') || grupo.includes('MENOR DE SEIS')) {
        return '0 A 6 MESES Y GESTANTES';
    }
    if (grupo.includes('6 A 11')) {
        return '6 A 11 MESES 29 DIAS';
    }
    if (grupo.includes('1 A 2') || grupo.includes('1 ANO A 2') || grupo.includes('1 ANOS A 2')) {
        return '1 A 2 ANOS 11 MESES';
    }
    if (grupo.includes('3 A 5') || grupo.includes('3 ANOS A 5')) {
        return '3 A 5 ANOS 11 MESES';
    }
    if (grupo.includes('5 ANOS EN ADELANTE')) {
        return '5 ANOS EN ADELANTE';
    }
    return grupo;
}

function formatearEdadCompleta(edadMeses, tipoBeneficiario = '') {
    const tipo = normalizarFiltro(tipoBeneficiario);
    if (tipo.includes('GESTANTE')) return 'Gestante';

    const totalMeses = Math.max(0, parseInt(edadMeses || 0, 10) || 0);
    const anios = Math.floor(totalMeses / 12);
    const meses = totalMeses % 12;
    const partes = [];

    if (anios > 0) {
        partes.push(`${anios} año${anios === 1 ? '' : 's'}`);
    }
    if (meses > 0 || partes.length === 0) {
        partes.push(`${meses} mes${meses === 1 ? '' : 'es'}`);
    }

    return partes.join(' y ');
}

function fechaPlantillaLegible(fecha) {
    if (!fecha) return '';
    const parsed = new Date(fecha);
    return Number.isNaN(parsed.getTime()) ? String(fecha) : parsed.toLocaleString();
}

function unidadTieneUsuarios(data) {
    const total = Number(data?.total_usuarios || 0);
    const lista = Array.isArray(data?.datos_completos) ? data.datos_completos.length : 0;
    return total > 0 || lista > 0;
}

function obtenerUnidadesConDatos() {
    const unidades = estadoDiagnostico.unidades || {};
    return Object.keys(unidades)
        .filter((unidad) => !UNIDADES_OPERATIVAS_INVALIDAS.has(normalizarFiltro(unidad)))
        .filter((unidad) => unidadTieneUsuarios(unidades[unidad]))
        .sort((a, b) => a.localeCompare(b, 'es'));
}

function contarGrupo(grupos, claveNormalizada) {
    if (!grupos) return 0;
    return Object.keys(grupos).reduce((total, key) => {
        return total + (normalizarGrupoEdad(key) === claveNormalizada ? Number(grupos[key] || 0) : 0);
    }, 0);
}

function formatoRppPorGrupo(claveGrupo) {
    const grupoNormalizado = normalizarGrupoEdad(claveGrupo || '');
    const grupo = GRUPOS_EDAD_DASHBOARD.find((item) => item.clave === grupoNormalizado);
    return grupo?.formato || null;
}

function aplicarFiltroEdad(clave) {
    const filtro = document.getElementById('filtro-edad');
    if (filtro) {
        filtro.value = clave;
    }
    renderTablaUnidades();
}

function actualizarTarjetas(stats = {}) {
    document.getElementById('stat-total').innerText = stats.total_usuarios || 0;
    document.getElementById('stat-cobertura').innerText = stats.alertas_cobertura || 0;
    document.getElementById('stat-retiros').innerText = stats.proximos_retiros || 0;
    document.getElementById('stat-nutricion').innerText = stats.falta_nutricion || 0;

    const grupos = stats.grupos_edad_totales || {};
    GRUPOS_EDAD_DASHBOARD.forEach((grupo) => {
        const el = document.getElementById(grupo.statId);
        if (el) el.innerText = contarGrupo(grupos, grupo.clave);
    });

    const detalleCobertura = document.getElementById('detalle-cobertura');
    if (detalleCobertura) {
        const unidades = Array.isArray(stats.unidades_sin_cobertura) ? stats.unidades_sin_cobertura : [];
        detalleCobertura.innerHTML = unidades.length
            ? unidades.slice(0, 5).map((u) => `<span class="block truncate">${escaparHtml(u.unidad)}: ${escaparHtml(u.total)} / ${escaparHtml(u.meta || 20)}</span>`).join('')
            : '';
    }

    const detalleRetiros = document.getElementById('detalle-retiros');
    if (detalleRetiros) {
        const retiros = Array.isArray(stats.proximos_retiros_lista) ? stats.proximos_retiros_lista : [];
        detalleRetiros.innerHTML = retiros.length
            ? retiros.slice(0, 5).map((u) => `<span class="block truncate">${escaparHtml(u.nombre)} · ${escaparHtml(u.unidad)} · ${escaparHtml(u.edad_completa || formatearEdadCompleta(u.edad_meses))}</span>`).join('')
            : '';
    }
}


function fetchUnidadesRegistradas() {
    fetch(`${backendUrl}/api/unidades`)
        .then(manejarRespuestaJson)
        .then((data) => {
            const unidades = data.unidades || [];
            unidades.forEach((item) => {
                const nombre = item.nombre;
                if (!nombre || UNIDADES_OPERATIVAS_INVALIDAS.has(normalizarFiltro(nombre))) return;
                if (!unidadTieneUsuarios(item)) return;
                if (!estadoDiagnostico.unidades[nombre]) {
                    estadoDiagnostico.unidades[nombre] = {
                        total_usuarios: item.total_usuarios || 0,
                        alerta_cobertura: (item.total_usuarios || 0) > 0 && (item.total_usuarios || 0) < 20,
                        usuarios_criticos: [],
                        nutricion_pendiente: 0,
                        grupos_edad: {},
                        datos_completos: []
                    };
                }
            });
            actualizarFiltrosUnidades();
            renderTablaUnidades();
        })
        .catch((error) => console.error('No se pudieron cargar unidades registradas', error));
}

function actualizarFiltrosUnidades() {
    const selectUnidad = document.getElementById('filtro-unidad');
    const selectAgregar = document.getElementById('nueva-unidad-nombre');
    const unidades = obtenerUnidadesConDatos();

    if (selectUnidad) {
        const seleccionado = selectUnidad.value;
        selectUnidad.innerHTML = '<option value="">Todas las unidades</option>' + unidades.map((unidad) => `
            <option value="${escaparHtml(unidad)}">${escaparHtml(unidad)}</option>
        `).join('');

        if (unidades.includes(seleccionado)) {
            selectUnidad.value = seleccionado;
        }
    }

    if (selectAgregar) {
        const seleccionadoAgregar = selectAgregar.value;
        selectAgregar.innerHTML = '<option value="">Selecciona una unidad detectada</option>' + unidades.map((unidad) => `
            <option value="${escaparHtml(unidad)}">${escaparHtml(unidad)}</option>
        `).join('');
        selectAgregar.disabled = unidades.length === 0;
        if (unidades.includes(seleccionadoAgregar)) {
            selectAgregar.value = seleccionadoAgregar;
        }
    }
}

function obtenerUsuariosFiltrados() {
    const filtroUnidad = normalizarFiltro(document.getElementById('filtro-unidad')?.value || '');
    const filtroEdad = normalizarGrupoEdad(document.getElementById('filtro-edad')?.value || '');
    const unidades = estadoDiagnostico.unidades || {};

    const resultado = [];
    obtenerUnidadesConDatos().forEach((unidad) => {
        if (filtroUnidad && normalizarFiltro(unidad) !== filtroUnidad) return;
        const data = unidades[unidad] || {};
        const usuarios = Array.isArray(data.datos_completos) ? data.datos_completos : [];
        usuarios.forEach((usuario) => {
            const grupo = normalizarGrupoEdad(usuario.GrupoEdad || usuario.grupo_edad || '', usuario.TipoBeneficiario || usuario.tipo_beneficiario || '');
            if (filtroEdad && grupo !== filtroEdad) return;
            resultado.push({ unidad, usuario: { ...usuario, GrupoEdadNormalizado: grupo } });
        });
    });
    return resultado;
}

function renderUsuariosFiltrados(usuarios) {
    const contenedor = document.getElementById('usuarios-filtrados');
    const resumen = document.getElementById('resumen-filtros');
    const unidadSeleccionada = document.getElementById('filtro-unidad')?.value || '';
    const edadSeleccionada = document.getElementById('filtro-edad')?.value || '';
    const filtroUnidadTexto = unidadSeleccionada || 'Todas las unidades';
    const filtroEdadTexto = edadSeleccionada || 'Todos los grupos';

    if (resumen) {
        resumen.innerText = `Filtro activo: ${filtroUnidadTexto} · ${filtroEdadTexto} · ${usuarios.length} usuario(s) encontrados.`;
    }

    if (!contenedor) return;

    const formatoSeleccionado = formatoRppPorGrupo(edadSeleccionada);
    const botonDescargaFiltro = unidadSeleccionada && formatoSeleccionado
        ? `<button onclick="descargar('${escaparHtml(unidadSeleccionada)}', '${escaparHtml(formatoSeleccionado)}')" class="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 text-xs font-medium text-white transition">
                Descargar RPP de este filtro
           </button>`
        : '';

    if (usuarios.length === 0) {
        contenedor.classList.remove('hidden');
        contenedor.innerHTML = `
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <p class="text-sm text-slate-500">No hay usuarios para el filtro seleccionado.</p>
                ${botonDescargaFiltro}
            </div>
        `;
        return;
    }

    contenedor.classList.remove('hidden');
    const filas = usuarios.slice(0, 80).map(({ unidad, usuario }) => `
        <tr class="border-b border-slate-800/70">
            <td class="px-3 py-2 text-slate-300">${escaparHtml(unidad)}</td>
            <td class="px-3 py-2 text-slate-200 font-medium">${escaparHtml(usuario.Nombre || '')}</td>
            <td class="px-3 py-2">${escaparHtml(usuario.Documento || usuario.NUI || '')}</td>
            <td class="px-3 py-2">${escaparHtml(usuario.EdadCompleta || usuario.edad_completa || formatearEdadCompleta(usuario.EdadMeses, usuario.TipoBeneficiario || usuario.tipo_beneficiario || ''))}</td>
            <td class="px-3 py-2">${escaparHtml(usuario.GrupoEdad || usuario.GrupoEdadNormalizado || '')}</td>
            <td class="px-3 py-2">${escaparHtml(usuario.Acudiente || '')}</td>
            <td class="px-3 py-2">${escaparHtml(usuario.Parentesco || '')}</td>
        </tr>
    `).join('');

    const aviso = usuarios.length > 80
        ? `<p class="mt-3 text-xs text-amber-400">Mostrando los primeros 80 de ${usuarios.length}. Usa los filtros para reducir la lista.</p>`
        : '';

    contenedor.innerHTML = `
        <div class="mb-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <h3 class="font-medium text-slate-200">Usuarios filtrados</h3>
            <div class="flex items-center gap-2">
                <span class="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs text-indigo-300">${usuarios.length} resultado(s)</span>
                ${botonDescargaFiltro}
            </div>
        </div>
        <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-400">
                <thead class="bg-slate-950 text-slate-300 uppercase">
                    <tr>
                        <th class="px-3 py-2">Unidad</th>
                        <th class="px-3 py-2">Nombre</th>
                        <th class="px-3 py-2">Documento/NUI</th>
                        <th class="px-3 py-2">Edad y meses</th>
                        <th class="px-3 py-2">Grupo</th>
                        <th class="px-3 py-2">Acudiente</th>
                        <th class="px-3 py-2">Parentesco</th>
                    </tr>
                </thead>
                <tbody>${filas}</tbody>
            </table>
        </div>
        ${aviso}
    `;
}


function renderTablaUnidades() {
    const tablaCuerpo = document.getElementById('tabla-cuerpo');
    if (!tablaCuerpo) return;

    const unidades = estadoDiagnostico.unidades || {};
    const filtroUnidad = normalizarFiltro(document.getElementById('filtro-unidad')?.value || '');
    const filtroEdad = normalizarGrupoEdad(document.getElementById('filtro-edad')?.value || '');
    const usuariosFiltrados = obtenerUsuariosFiltrados();

    tablaCuerpo.innerHTML = '';
    const nombresUnidades = obtenerUnidadesConDatos();
    const unidadesVisibles = nombresUnidades.filter((unidad) => !filtroUnidad || normalizarFiltro(unidad) === filtroUnidad);

    if (unidadesVisibles.length === 0) {
        tablaCuerpo.innerHTML = `<tr><td colspan="6" class="px-6 py-8 text-center text-slate-500">No hay unidades con usuarios para mostrar en este filtro.</td></tr>`;
        renderUsuariosFiltrados([]);
        return;
    }

    unidadesVisibles.forEach(unidad => {
        const data = unidades[unidad] || {};
        const usuariosUnidad = Array.isArray(data.datos_completos) ? data.datos_completos : [];
        const usuariosUnidadFiltrados = usuariosUnidad.filter((usuario) => {
            const grupo = normalizarGrupoEdad(usuario.GrupoEdad || '', usuario.TipoBeneficiario || '');
            return !filtroEdad || grupo === filtroEdad;
        });
        const totalReal = Number(data.total_usuarios || usuariosUnidad.length || 0);
        const totalVisible = filtroEdad ? usuariosUnidadFiltrados.length : totalReal;

        let criticosHTML = `<span class="text-xs text-emerald-400 flex items-center gap-1"><i data-lucide="check-circle" class="w-3.5 h-3.5"></i> Sin novedades de gravedad</span>`;
        if (Array.isArray(data.usuarios_criticos) && data.usuarios_criticos.length > 0) {
            criticosHTML = data.usuarios_criticos.slice(0, 3).map(c => `
                <div class="text-xs text-rose-400 bg-rose-500/10 p-1.5 rounded border border-rose-500/20 mb-1">
                    <strong>${escaparHtml(c.nombre)}:</strong> ${escaparHtml(c.motivo)}
                </div>
            `).join('');
        }

        const alertaCobertura = totalReal > 0 && totalReal < 20 && !filtroEdad;
        const claseBadge = alertaCobertura
            ? 'bg-rose-500/10 text-rose-500 border-rose-500/30'
            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
        const textoCobertura = filtroEdad
            ? `${totalVisible} usuario(s) en grupo`
            : `${totalReal} / 20 ${totalReal >= 20 ? '(Completo)' : '(Falta Cupo)'}`;

        const grupos = data.grupos_edad || {};
        const detalleGrupos = GRUPOS_EDAD_DASHBOARD
            .map((g) => ({ etiqueta: g.etiqueta, total: contarGrupo(grupos, g.clave) }))
            .filter((g) => g.total > 0)
            .map((g) => `${g.etiqueta}: ${g.total}`)
            .join(' · ');

        const docenteAsignado = data.docente_asignado || data.docente || (window.CruceBases ? CruceBases.docentePorUnidad(unidad) : '') || 'Sin agente educativo asignado';

        const rppLinks = GRUPOS_EDAD_DASHBOARD.map((g) => {
            const totalGrupo = contarGrupo(grupos, g.clave);
            return `
                <button type="button" data-rpp-download="1" data-rpp-unidad="${escaparHtml(unidad)}" data-rpp-grupo="${escaparHtml(g.formato)}" class="relative z-10 text-indigo-400 hover:text-indigo-300 text-xs flex items-center gap-1 cursor-pointer pointer-events-auto">
                    <i data-lucide="download" class="w-3.5 h-3.5"></i> ${escaparHtml(g.etiqueta)} (${totalGrupo})
                </button>
            `;
        }).join('');

        tablaCuerpo.insertAdjacentHTML('beforeend', `
            <tr class="hover:bg-slate-900/50 transition">
                <td class="px-6 py-4 font-semibold text-slate-200">
                    ${escaparHtml(unidad)}
                    ${detalleGrupos ? `<div class="mt-1 text-[11px] font-normal text-slate-500">${escaparHtml(detalleGrupos)}</div>` : ''}
                </td>
                <td class="px-6 py-4">
                    <span class="px-2.5 py-1 rounded-lg border text-xs font-medium ${claseBadge}">${escaparHtml(textoCobertura)}</span>
                </td>
                <td class="px-6 py-4 text-xs text-slate-300">
                    <div class="font-medium text-slate-200">${escaparHtml(docenteAsignado)}</div>
                </td>
                <td class="px-6 py-4 max-w-xs">${criticosHTML}</td>
                <td class="px-6 py-4 text-xs ${data.nutricion_pendiente > 0 ? 'text-cyan-400 font-medium' : 'text-slate-500'}">
                    ${data.nutricion_pendiente > 0 ? `${data.nutricion_pendiente} Niños sin Peso/Talla` : 'Al día'}
                </td>
                <td class="px-6 py-4 space-y-1">
                    <button onclick="descargar('${escaparHtml(unidad)}', 'ram')" class="text-indigo-400 hover:text-indigo-300 text-xs flex items-center gap-1"><i data-lucide="download" class="w-3.5 h-3.5"></i> Asistencia / RAM</button>
                    <button onclick="descargar('${escaparHtml(unidad)}', 'bienestarina')" class="text-indigo-400 hover:text-indigo-300 text-xs flex items-center gap-1"><i data-lucide="download" class="w-3.5 h-3.5"></i> Bienestarina</button>
                    <button onclick="CruceBases.descargarUsuariosUnidad('${escaparHtml(unidad)}', 'excel')" class="text-emerald-400 hover:text-emerald-300 text-xs flex items-center gap-1"><i data-lucide="file-down" class="w-3.5 h-3.5"></i> Descargar usuarios Excel</button>
                    <button onclick="CruceBases.descargarUsuariosUnidad('${escaparHtml(unidad)}', 'pdf')" class="text-rose-400 hover:text-rose-300 text-xs flex items-center gap-1"><i data-lucide="file-text" class="w-3.5 h-3.5"></i> Descargar usuarios PDF</button>
                    <button onclick="CruceBases.imprimirUsuariosUnidad('${escaparHtml(unidad)}')" class="text-amber-400 hover:text-amber-300 text-xs flex items-center gap-1"><i data-lucide="printer" class="w-3.5 h-3.5"></i> Imprimir usuarios</button>
                    <div class="pt-1 text-[10px] uppercase tracking-wide text-slate-500">RPP por categoría</div>
                    ${rppLinks}
                </td>
            </tr>
        `);
    });

    renderUsuariosFiltrados(usuariosFiltrados);
    lucide.createIcons();
}

function agregarUnidadManual() {
    const nombreInput = document.getElementById('nueva-unidad-nombre');
    const detalleInput = document.getElementById('nueva-unidad-detalle');
    const nombre = nombreInput?.value.trim();
    const detalle = detalleInput?.value.trim();

    if (!nombre) {
        mostrarMensaje('message-box', 'Selecciona una unidad detectada en el archivo.', 'error');
        return;
    }

    fetch(`${backendUrl}/api/unidades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, direccion: detalle, telefono: '' })
    })
        .then(manejarRespuestaJson)
        .then((data) => {
            const unidad = data.unidad?.nombre || nombre;
            if (unidad && estadoDiagnostico.unidades[unidad]) {
                document.getElementById('filtro-unidad').value = unidad;
                renderTablaUnidades();
            }
            if (detalleInput) detalleInput.value = '';
            mostrarMensaje('message-box', data.message || 'Unidad guardada correctamente.', 'success');
        })
        .catch((error) => {
            mostrarMensaje('message-box', error.message || 'No se pudo agregar la unidad.', 'error');
        });
}



function procesarResultadoBase(resultado) {
    actualizarTarjetas(resultado.stats || {});

    if ((resultado.stats?.alertas_cobertura || 0) > 0 || (resultado.stats?.proximos_retiros || 0) > 0) {
        document.getElementById('ping-alerta')?.classList.remove('hidden');
    }

    estadoDiagnostico = resultado;
    window.estadoDiagnostico = estadoDiagnostico;
    if (window.CruceBases) CruceBases.cargarUltimoCruce();
    actualizarFiltrosUnidades();
    renderTablaUnidades();
    if (typeof lucide !== 'undefined') lucide.createIcons();

    const errores = Array.isArray(resultado.errores_formatos) && resultado.errores_formatos.length
        ? ` Algunos formatos tuvieron observaciones: ${resultado.errores_formatos.length}.`
        : '';
    const procesamiento = resultado.procesamiento || {};
    const unidadesProcesadas = procesamiento.total_unidades_formatos || resultado.stats?.unidades_procesadas || Object.keys(resultado.unidades || {}).length;
    const registrosFormatos = procesamiento.total_usuarios_formatos || resultado.stats?.total_usuarios_formatos || resultado.stats?.total_usuarios || 0;
    const registrosBase = procesamiento.total_usuarios_base_maestra || resultado.stats?.total_usuarios_base_maestra || registrosFormatos;
    const mensajeBase = procesamiento.modo === 'unidades_seleccionadas'
        ? `Base Maestra actualizada con ${registrosBase} registro(s). Formatos generados solo para ${unidadesProcesadas} unidad(es) seleccionada(s), ${registrosFormatos} registro(s).`
        : `Base procesada correctamente. Formatos generados para todas las unidades detectadas (${unidadesProcesadas}).`;
    mostrarMensaje('message-box', `${mensajeBase}${errores}`, 'success');
}


function aplicarPanelPrincipalBaseMaestra(resultado, opciones = {}) {
    if (!resultado || !resultado.fuente_activa) return false;
    actualizarTarjetas(resultado.stats || {});

    if ((resultado.stats?.alertas_cobertura || 0) > 0 || (resultado.stats?.proximos_retiros || 0) > 0) {
        document.getElementById('ping-alerta')?.classList.remove('hidden');
    }

    estadoDiagnostico = resultado;
    window.estadoDiagnostico = estadoDiagnostico;
    actualizarFiltrosUnidades();
    renderTablaUnidades();
    if (window.CruceBases && typeof CruceBases.cargarOpcionesInforme === 'function') {
        try { CruceBases.cargarOpcionesInforme(); } catch (_) {}
    }
    if (typeof lucide !== 'undefined') lucide.createIcons();

    const version = resultado.version_activa || {};
    const total = resultado.stats?.total_usuarios || 0;
    const status = document.getElementById('bmp-status-text');
    if (status) {
        status.textContent = `Panel alimentado desde Base Maestra v${version.version_numero || version.id || 'activa'} · ${total} usuario(s) activos.`;
    }
    if (!opciones.silent) {
        const mensaje = `Panel principal actualizado desde Base Maestra publicada: ${total} usuario(s), ${resultado.stats?.total_unidades || 0} unidad(es).`;
        if (typeof mostrarMensaje === 'function') mostrarMensaje('bmp-message', mensaje, 'success');
    }
    return true;
}
window.aplicarPanelPrincipalBaseMaestra = aplicarPanelPrincipalBaseMaestra;

function consultarJobOperativo(jobId) {
    const token = authToken();
    return fetch(`${backendUrl}/api/jobs/${encodeURIComponent(jobId)}`, {
        headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'X-Auth-Token': token || '',
            'X-Requested-With': 'XMLHttpRequest'
        }
    }).then(manejarRespuestaJson);
}

function esperarJobOperativo(jobId, onComplete, messageTarget = 'message-box') {
    let intentos = 0;
    const maxIntentos = 180; // hasta 9 minutos, útil para bases grandes por túnel

    const tick = () => {
        intentos += 1;
        consultarJobOperativo(jobId)
            .then((data) => {
                const job = data.job || data;
                const progreso = Number(job.progreso || 0);
                if (Number.isFinite(progreso)) actualizarBarraProgreso(Math.max(1, Math.min(100, progreso)));
                if (job.etapa) mostrarCargando(`${job.etapa} (${Math.round(progreso)}%)`);

                if (job.estado === 'completado') {
                    ocultarProgreso();
                    ocultarCargando();
                    try {
                        onComplete(job.resultado || {});
                    } catch (error) {
                        console.error(error);
                        mostrarMensaje(messageTarget, 'El proceso terminó, pero hubo un error actualizando el tablero.', 'error');
                    }
                    return;
                }

                if (job.estado === 'error') {
                    ocultarProgreso();
                    ocultarCargando();
                    const detalle = job.error || 'El proceso en segundo plano falló.';
                    mostrarMensaje(messageTarget, `Error procesando en segundo plano: ${detalle}`, 'error');
                    console.error('Job operativo fallido', job);
                    return;
                }

                if (intentos >= maxIntentos) {
                    ocultarProgreso();
                    ocultarCargando();
                    mostrarMensaje(messageTarget, 'El proceso sigue tardando demasiado. Revisa los logs del backend o intenta con una base más liviana.', 'error');
                    return;
                }

                setTimeout(tick, 3000);
            })
            .catch((error) => {
                if (intentos >= maxIntentos) {
                    ocultarProgreso();
                    ocultarCargando();
                    mostrarMensaje(messageTarget, error.message || 'No se pudo consultar el avance del proceso.', 'error');
                    return;
                }
                setTimeout(tick, 3000);
            });
    };

    mostrarMensaje(messageTarget, 'La solicitud fue recibida. Puedes seguir el avance de la fundación actual sin mantener una conexión larga.', 'success');
    actualizarBarraProgreso(1);
    tick();
}

function resetSelectorUnidadesCuentame() {
    estadoSeleccionCuentame = {
        archivoToken: '',
        archivoNombre: '',
        totalUsuarios: 0,
        unidades: [],
        seleccionadas: new Set()
    };
    window.estadoSeleccionCuentame = estadoSeleccionCuentame;

    const contenedor = document.getElementById('selector-unidades-container');
    const lista = document.getElementById('selector-unidades-lista');
    const resumen = document.getElementById('selector-unidades-resumen');
    const contador = document.getElementById('selector-unidades-contador');
    const buscar = document.getElementById('selector-unidades-buscar');
    if (contenedor) contenedor.classList.add('hidden');
    if (lista) lista.innerHTML = '<div class="px-4 py-5 text-center text-sm text-slate-500">Sin unidades detectadas todavía.</div>';
    if (resumen) resumen.innerText = 'Carga una base para ver las unidades disponibles.';
    if (contador) contador.innerText = '0 seleccionadas';
    if (buscar) buscar.value = '';
}

function obtenerFormatosSeleccionadosAlpha68() {
    const checks = Array.from(document.querySelectorAll('[data-alpha68-formato]:checked'));
    const seleccion = checks.map((item) => String(item.value || item.dataset.alpha68Formato || '').trim()).filter(Boolean);
    if (seleccion.includes('paquete_completo')) {
        return ['paquete_completo'];
    }
    return Array.from(new Set(seleccion));
}
window.obtenerFormatosSeleccionadosAlpha68 = obtenerFormatosSeleccionadosAlpha68;

function actualizarResumenFormatosAlpha68() {
    const destino = document.getElementById('alpha68-formatos-resumen');
    if (!destino) return;
    const seleccion = obtenerFormatosSeleccionadosAlpha68();
    if (!seleccion.length) {
        destino.textContent = 'Sin selección: se conserva el comportamiento histórico y se generarán todos los formatos disponibles.';
        return;
    }
    const nombres = {
        rpp: 'RPP', bienestarina: 'Bienestarina', ram: 'RAM',
        relacion_mensual: 'Relación mensual', listado_usuarios: 'Listado de usuarios',
        listado_asistencia_usuarios: 'Asistencia de usuarios',
        distribucion_alimentos: 'Distribución de alimentos', paquete_completo: 'Paquete completo'
    };
    destino.textContent = `Se procesará solo: ${seleccion.map((v) => nombres[v] || v).join(', ')}.`;
}
window.actualizarResumenFormatosAlpha68 = actualizarResumenFormatosAlpha68;

function seleccionarFormatosAlpha68(modo) {
    const checks = Array.from(document.querySelectorAll('[data-alpha68-formato]'));
    if (modo === 'todo') {
        checks.forEach((check) => { check.checked = check.value === 'paquete_completo'; });
    } else if (modo === 'limpiar') {
        checks.forEach((check) => { check.checked = false; });
    } else if (modo === 'basicos') {
        checks.forEach((check) => { check.checked = ['rpp','bienestarina','ram'].includes(check.value); });
    }
    actualizarResumenFormatosAlpha68();
}
window.seleccionarFormatosAlpha68 = seleccionarFormatosAlpha68;

document.addEventListener('change', (ev) => {
    if (ev.target && ev.target.matches('[data-alpha68-formato]')) {
        if (ev.target.value === 'paquete_completo' && ev.target.checked) {
            document.querySelectorAll('[data-alpha68-formato]').forEach((check) => {
                if (check !== ev.target) check.checked = false;
            });
        } else if (ev.target.checked) {
            const pack = document.querySelector('[data-alpha68-formato][value="paquete_completo"]');
            if (pack) pack.checked = false;
        }
        actualizarResumenFormatosAlpha68();
    }
});

function periodoFormatosSeleccionado() {
    const ahora = new Date();
    const mesInput = document.getElementById('periodo-formatos-mes');
    const anioInput = document.getElementById('periodo-formatos-anio');
    let mes = Number(mesInput?.value || (ahora.getMonth() + 1));
    let anio = Number(anioInput?.value || ahora.getFullYear());
    if (!Number.isInteger(mes) || mes < 1 || mes > 12) mes = ahora.getMonth() + 1;
    if (!Number.isInteger(anio) || anio < 2020 || anio > 2100) anio = ahora.getFullYear();
    return { mes, anio };
}
window.periodoFormatosSeleccionado = periodoFormatosSeleccionado;

function inicializarPeriodoFormatos() {
    const ahora = new Date();
    const mesInput = document.getElementById('periodo-formatos-mes');
    const anioInput = document.getElementById('periodo-formatos-anio');
    if (mesInput && !mesInput.value) mesInput.value = String(ahora.getMonth() + 1);
    if (mesInput) mesInput.value = mesInput.value || String(ahora.getMonth() + 1);
    if (anioInput && !anioInput.value) anioInput.value = String(ahora.getFullYear());
}
document.addEventListener('DOMContentLoaded', inicializarPeriodoFormatos);

function anexarOpcionesCuentame(formData) {
    const periodo = periodoFormatosSeleccionado();
    formData.append('mes', String(periodo.mes));
    formData.append('anio', String(periodo.anio));
    formData.append('año', String(periodo.anio));
    formData.append('max_usuarios_formato', document.getElementById('max-usuarios-formato')?.value || '20');
    formData.append('bienestarina_por_hoja', document.getElementById('bienestarina-por-hoja')?.value || '14');
    formData.append('fecha_entrega_bienestarina', document.getElementById('fecha-entrega-bienestarina')?.value || '');
    formData.append('lote_bienestarina', document.getElementById('lote-bienestarina')?.value || '');
    formData.append('cantidad_bienestarina', document.getElementById('cantidad-bienestarina')?.value || '');
    const formatosSeleccionados = obtenerFormatosSeleccionadosAlpha68();
    formData.append('formatos_seleccionados', formatosSeleccionados.join(','));
    return formData;
}

function actualizarContadorSelectorUnidades() {
    const contador = document.getElementById('selector-unidades-contador');
    if (!contador) return;
    const seleccionadas = estadoSeleccionCuentame.unidades.filter((u) => estadoSeleccionCuentame.seleccionadas.has(String(u.nombre || '')));
    const totalRegistros = seleccionadas.reduce((sum, u) => sum + Number(u.total || 0), 0);
    contador.innerText = `${seleccionadas.length} seleccionada(s) · ${totalRegistros} registro(s)`;
}

function unidadesSeleccionadasDesdeDOM() {
    const marcadas = Array.from(document.querySelectorAll('#selector-unidades-lista input[type="checkbox"]:checked'))
        .map((input) => input.value || input.dataset.unidad || '')
        .map((unidad) => String(unidad || '').trim())
        .filter(Boolean);
    return Array.from(new Set([...Array.from(estadoSeleccionCuentame.seleccionadas || []), ...marcadas]));
}

function _badgeDiagnosticoFormato(nombre, listo, version) {
    const clases = listo
        ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
        : 'border-rose-500/30 bg-rose-500/10 text-rose-200';
    const estado = listo ? 'Listo' : 'Pendiente';
    const versionTexto = version ? ` · V${escaparHtml(version)}` : '';
    return `<span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs ${clases}">${escaparHtml(nombre)}: ${estado}${versionTexto}</span>`;
}

function _renderDiagnosticoFormatoUnidad(data) {
    const unidad = data?.unidad || {};
    const plantillas = data?.plantillas || {};
    const preparado = data?.preparado || {};
    const razones = Array.isArray(data?.razones) ? data.razones : [];
    const participantes = Number(data?.participantes?.total || 0);
    const minuta = data?.rppMinuta || {};
    const storage = data?.storage || {};
    const volumenOk = Boolean(storage.databaseInsideDataDir && storage.persistentVolumeDeclared);
    const razonesHtml = razones.length
        ? `<ul class="mt-3 space-y-1 text-xs text-amber-200">${razones.map((razon) => `<li>• ${escaparHtml(razon)}</li>`).join('')}</ul>`
        : '<p class="mt-3 text-xs text-emerald-300">No se detectaron bloqueos previos para esta UDS y periodo.</p>';

    return `
        <article class="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div class="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    <h4 class="font-semibold text-slate-100">${escaparHtml(unidad.normalizada || unidad.solicitada || 'UDS sin nombre')}</h4>
                    <p class="mt-1 text-xs text-slate-400">${participantes} participante(s) encontrado(s) · Catálogo UDS: ${unidad.conocida ? 'coincide' : 'sin coincidencia'}</p>
                </div>
                <span class="inline-flex w-fit rounded-full border px-2.5 py-1 text-xs ${volumenOk ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' : 'border-amber-500/30 bg-amber-500/10 text-amber-200'}">
                    Volumen /data: ${volumenOk ? 'configurado' : 'por comprobar'}
                </span>
            </div>
            <div class="mt-3 flex flex-wrap gap-2">
                ${_badgeDiagnosticoFormato('RPP', preparado.rpp, plantillas.rpp?.version)}
                ${_badgeDiagnosticoFormato('Bienestarina', preparado.bienestarina, plantillas.bienestarina?.version)}
                ${_badgeDiagnosticoFormato('RAM', preparado.ram, plantillas.ram?.version)}
            </div>
            <p class="mt-3 text-xs text-slate-400">Minuta RPP: ${minuta.disponible ? `${escaparHtml(minuta.codigo || 'configurada')} · ${Number(minuta.grupos || 0)} grupo(s) · ${Number(minuta.productos || 0)} producto(s)` : 'no disponible'}.</p>
            ${razonesHtml}
        </article>`;
}

async function diagnosticarFormatosSeleccionados() {
    const destino = document.getElementById('formatos-preflight-result');
    if (!destino) return;

    const seleccionadas = unidadesSeleccionadasDesdeDOM();
    const filtroUnidad = String(document.getElementById('filtro-unidad')?.value || '').trim();
    const unidadesDetectadas = Array.isArray(estadoSeleccionCuentame.unidades)
        ? estadoSeleccionCuentame.unidades.map((item) => String(item?.nombre || '').trim()).filter(Boolean)
        : [];
    const unidades = Array.from(new Set(
        seleccionadas.length ? seleccionadas : (filtroUnidad ? [filtroUnidad] : unidadesDetectadas.slice(0, 1))
    )).slice(0, 12);

    destino.classList.remove('hidden');
    if (!unidades.length) {
        destino.innerHTML = '<p class="text-sm text-amber-200">Primero analiza una base o selecciona una UDS para ejecutar el diagnóstico previo.</p>';
        return;
    }

    const token = authToken();
    if (!token) {
        destino.innerHTML = '<p class="text-sm text-rose-200">La sesión no está activa. Inicia sesión nuevamente.</p>';
        return;
    }

    const periodo = periodoFormatosSeleccionado();
    destino.innerHTML = `<div class="flex items-center gap-2 text-sm text-cyan-200"><span class="h-4 w-4 animate-spin rounded-full border-2 border-cyan-300 border-t-transparent"></span> Revisando ${unidades.length} UDS para ${String(periodo.mes).padStart(2, '0')}/${periodo.anio}...</div>`;

    try {
        const resultados = [];
        for (const unidad of unidades) {
            const query = new URLSearchParams({
                unidad,
                mes: String(periodo.mes),
                anio: String(periodo.anio),
            });
            const respuesta = await fetch(`${backendUrl}/api/formatos/diagnostico?${query.toString()}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'X-Auth-Token': token,
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });
            resultados.push(await manejarRespuestaJson(respuesta));
        }

        const truncado = seleccionadas.length > unidades.length
            ? `<p class="mt-3 text-xs text-amber-200">Se mostraron las primeras ${unidades.length} UDS seleccionadas para evitar una consulta demasiado pesada.</p>`
            : '';
        destino.innerHTML = `
            <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h3 class="text-sm font-semibold text-cyan-100">Diagnóstico previo de formatos</h3>
                    <p class="text-xs text-slate-400">No muestra nombres ni documentos; solo disponibilidad, conteos y causas de bloqueo.</p>
                </div>
                <span class="text-xs text-slate-500">Periodo ${String(periodo.mes).padStart(2, '0')}/${periodo.anio}</span>
            </div>
            <div class="mt-4 grid gap-3">${resultados.map(_renderDiagnosticoFormatoUnidad).join('')}</div>
            ${truncado}`;
        if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (error) {
        destino.innerHTML = `<p class="text-sm text-rose-200">No fue posible completar el diagnóstico: ${escaparHtml(error?.message || error)}</p>`;
    }
}
window.diagnosticarFormatosSeleccionados = diagnosticarFormatosSeleccionados;

function toggleUnidadSeleccionada(input) {
    const unidad = String(input?.value || input?.dataset?.unidad || '').trim();
    if (!unidad) return;
    if (input.checked) {
        estadoSeleccionCuentame.seleccionadas.add(unidad);
    } else {
        estadoSeleccionCuentame.seleccionadas.delete(unidad);
    }
    window.estadoSeleccionCuentame = estadoSeleccionCuentame;
    actualizarContadorSelectorUnidades();
}

function renderSelectorUnidades() {
    const contenedor = document.getElementById('selector-unidades-container');
    const lista = document.getElementById('selector-unidades-lista');
    const resumen = document.getElementById('selector-unidades-resumen');
    if (!contenedor || !lista) return;

    const unidades = Array.isArray(estadoSeleccionCuentame.unidades) ? estadoSeleccionCuentame.unidades : [];
    contenedor.classList.toggle('hidden', unidades.length === 0);

    const filtro = (document.getElementById('selector-unidades-buscar')?.value || '').trim().toLowerCase();
    const visibles = unidades.filter((u) => String(u.nombre || '').toLowerCase().includes(filtro));

    if (resumen) {
        resumen.innerText = `${estadoSeleccionCuentame.totalUsuarios || 0} registro(s) en ${unidades.length} unidad(es). Archivo: ${estadoSeleccionCuentame.archivoNombre || 'base cargada'}.`;
    }

    if (!visibles.length) {
        lista.innerHTML = '<div class="px-4 py-5 text-center text-sm text-slate-500">No hay unidades que coincidan con la búsqueda.</div>';
        actualizarContadorSelectorUnidades();
        return;
    }

    lista.innerHTML = visibles.map((u) => {
        const nombre = String(u.nombre || 'SIN UNIDAD');
        const checked = estadoSeleccionCuentame.seleccionadas.has(nombre) ? 'checked' : '';
        return `
            <label class="flex items-center gap-3 px-4 py-3 hover:bg-slate-900/80 cursor-pointer transition">
                <input type="checkbox" value="${escaparHtml(nombre)}" data-unidad="${escaparHtml(nombre)}" onchange="toggleUnidadSeleccionada(this)" ${checked} class="h-4 w-4 rounded border-slate-600 bg-slate-950 text-indigo-500 focus:ring-indigo-500" />
                <span class="flex-1 min-w-0">
                    <span class="block text-sm font-medium text-slate-200 truncate">${escaparHtml(nombre)}</span>
                    <span class="block text-xs text-slate-500">${Number(u.total || 0)} registro(s) · ${Number(u.activos || 0)} activo(s) · ${Number(u.gestantes || 0)} gestante(s)</span>
                </span>
            </label>`;
    }).join('');

    actualizarContadorSelectorUnidades();
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function seleccionarTodasUnidades(marcar = true) {
    const unidades = Array.isArray(estadoSeleccionCuentame.unidades) ? estadoSeleccionCuentame.unidades : [];
    if (!unidades.length) {
        mostrarMensaje('message-box', 'Primero analiza una base para detectar unidades.', 'error');
        return;
    }
    estadoSeleccionCuentame.seleccionadas = marcar
        ? new Set(unidades.map((u) => String(u.nombre || '')).filter(Boolean))
        : new Set();
    renderSelectorUnidades();
}

function manejarErrorAuthProcesamiento(xhr, resultado) {
    if (xhr.status === 401) {
        limpiarSesionLocal();
        mostrarLogin('Sesión expirada o token inválido. Inicia sesión nuevamente.');
        mostrarMensaje('message-box', resultado.error || 'Sesión expirada o token inválido. Inicia sesión nuevamente.', 'error');
        return true;
    }

    if (xhr.status === 403) {
        mostrarMensaje('message-box', resultado.error || 'No tienes permiso para cargar esta base de datos.', 'error');
        return true;
    }
    return false;
}

function enviarFormularioProcesamientoCuentame(formData, textoCargando) {
    const token = authToken();
    // El flujo interactivo siempre solicita el contrato síncrono. HTTP 202 queda
    // reservado para una operación masiva que lo pida expresamente.
    formData.set('sync', '1');
    formData.set('modo_ejecucion', 'sincrono');
    const tablaCuerpo = document.getElementById('tabla-cuerpo');
    if (tablaCuerpo) {
        tablaCuerpo.innerHTML = `<tr><td colspan="6" class="px-6 py-8 text-center text-indigo-400 animate-pulse">Preparando los datos y generando únicamente los formatos y unidades seleccionados...</td></tr>`;
    }
    limpiarMensajes();
    mostrarCargando(textoCargando || 'Procesando base de datos y formatos oficiales...');

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${backendUrl}/api/procesar`, true);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.setRequestHeader('X-Auth-Token', token);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

    xhr.upload.onprogress = function (event) {
        if (event.lengthComputable) {
            const porcentaje = Math.round((event.loaded / event.total) * 100);
            actualizarBarraProgreso(Math.max(1, Math.min(95, porcentaje)));
        }
    };

    xhr.onload = function () {
        ocultarProgreso();
        ocultarCargando();

        let resultado = {};
        try {
            resultado = xhr.responseText ? JSON.parse(xhr.responseText) : {};
        } catch (_) {
            resultado = {};
        }

        if (manejarErrorAuthProcesamiento(xhr, resultado)) return;

        if (xhr.status === 202 && resultado.job_id) {
            esperarJobOperativo(resultado.job_id, procesarResultadoBase, 'message-box');
            return;
        }

        if (xhr.status >= 400) {
            const mensaje524 = xhr.status === 524
                ? 'El procesamiento síncrono superó el tiempo disponible. Reduce la cantidad de UDS o formatos y vuelve a intentar.'
                : [
                    resultado.error || `Error técnico del servidor (${xhr.status}).`,
                    resultado.detalle || '',
                    resultado.trace_id ? `Referencia: ${resultado.trace_id}` : '',
                ].filter(Boolean).join(' ');
            mostrarMensaje('message-box', mensaje524, 'error');
            return;
        }

        try {
            procesarResultadoBase(resultado);
        } catch (error) {
            mostrarMensaje('message-box', 'La base se procesó, pero hubo un error al actualizar el tablero.', 'error');
            console.error(error);
        }
    };

    xhr.onerror = function () {
        ocultarProgreso();
        ocultarCargando();
        mostrarMensaje('message-box', 'Ocurrió un error de conexión con el backend de Python.', 'error');
    };

    xhr.send(formData);
}

function detectarUnidadesBase() {
    const fileInput = document.getElementById('input-excel');
    const file = fileInput?.files?.[0];
    const error = validarArchivo(file, allowedBaseExtensions, 30);
    if (error) {
        mostrarMensaje('message-box', error, 'error');
        return;
    }

    const token = authToken();
    if (!token) {
        limpiarSesionLocal();
        mostrarLogin('Debe iniciar sesión para cargar la base de datos.');
        mostrarMensaje('message-box', 'Debe iniciar sesión para cargar la base de datos.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('solo_detectar_unidades', '1');
    anexarOpcionesCuentame(formData);

    limpiarMensajes();
    mostrarCargando('Analizando la base Cuéntame y detectando unidades de atención...');

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${backendUrl}/api/procesar`, true);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.setRequestHeader('X-Auth-Token', token);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

    xhr.upload.onprogress = function (event) {
        if (event.lengthComputable) {
            const porcentaje = Math.round((event.loaded / event.total) * 100);
            actualizarBarraProgreso(Math.max(1, Math.min(95, porcentaje)));
        }
    };

    xhr.onload = function () {
        ocultarProgreso();
        ocultarCargando();

        let resultado = {};
        try {
            resultado = xhr.responseText ? JSON.parse(xhr.responseText) : {};
        } catch (_) {
            resultado = {};
        }

        if (manejarErrorAuthProcesamiento(xhr, resultado)) return;

        if (xhr.status >= 400) {
            mostrarMensaje('message-box', resultado.error || `No se pudieron detectar unidades (${xhr.status}).`, 'error');
            return;
        }

        estadoSeleccionCuentame.archivoToken = resultado.archivo_token || '';
        estadoSeleccionCuentame.archivoNombre = resultado.archivo || file.name;
        estadoSeleccionCuentame.totalUsuarios = Number(resultado.total_usuarios || 0);
        estadoSeleccionCuentame.unidades = Array.isArray(resultado.unidades) ? resultado.unidades : [];
        estadoSeleccionCuentame.seleccionadas = new Set();
        window.estadoSeleccionCuentame = estadoSeleccionCuentame;
        renderSelectorUnidades();
        mostrarMensaje('message-box', resultado.mensaje || 'Unidades detectadas. Selecciona cuáles deseas procesar.', 'success');
    };

    xhr.onerror = function () {
        ocultarProgreso();
        ocultarCargando();
        mostrarMensaje('message-box', 'Ocurrió un error de conexión con el backend de Python.', 'error');
    };

    xhr.send(formData);
}

function procesarUnidadesSeleccionadas(procesarTodo = false) {
    const token = authToken();
    if (!token) {
        limpiarSesionLocal();
        mostrarLogin('Debe iniciar sesión para procesar la base de datos.');
        mostrarMensaje('message-box', 'Debe iniciar sesión para procesar la base de datos.', 'error');
        return;
    }

    const seleccionadas = unidadesSeleccionadasDesdeDOM();
    estadoSeleccionCuentame.seleccionadas = new Set(seleccionadas);
    window.estadoSeleccionCuentame = estadoSeleccionCuentame;
    actualizarContadorSelectorUnidades();
    if (!procesarTodo && seleccionadas.length === 0) {
        mostrarMensaje('message-box', 'Selecciona al menos una unidad o usa la opción Procesar todo.', 'error');
        return;
    }

    const formData = new FormData();
    anexarOpcionesCuentame(formData);

    if (estadoSeleccionCuentame.archivoToken) {
        formData.append('archivo_token', estadoSeleccionCuentame.archivoToken);
    } else {
        const file = document.getElementById('input-excel')?.files?.[0];
        const error = validarArchivo(file, allowedBaseExtensions, 30);
        if (error) {
            mostrarMensaje('message-box', 'Primero analiza la base para detectar unidades.', 'error');
            return;
        }
        formData.append('file', file);
    }

    if (procesarTodo) {
        formData.append('procesar_todo', '1');
    } else {
        formData.append('unidades_seleccionadas', JSON.stringify(seleccionadas));
        formData.append('unidades_seleccionadas_csv', seleccionadas.join('|'));
        seleccionadas.forEach((unidad) => {
            formData.append('unidad_seleccionada', unidad);
            formData.append('unidades_seleccionadas[]', unidad);
        });
    }

    const texto = procesarTodo
        ? 'Procesando todas las unidades de la base Cuéntame...'
        : `Procesando ${seleccionadas.length} unidad(es) seleccionada(s)...`;
    enviarFormularioProcesamientoCuentame(formData, texto);
}

function subirYProcesar() {
    detectarUnidadesBase();
}

function esGrupoRppDescargaAlpha61(fmt) {
    const normalizado = String(fmt || '').trim().toUpperCase();
    return ['0_6_GESTANTES', '6_11_MESES', '1_2_ANOS', '3_5_ANOS'].includes(normalizado)
        || String(fmt || '').toLowerCase().startsWith('rpp_');
}

function descargar(unidad, formato) {
    const fmtOriginal = String(formato || '').trim();
    const fmt = fmtOriginal.toLowerCase();
    if (fmt.includes('bienestarina')) {
        // ALPHA73: fix mínimo diferencial. Bienestarina solo usa su endpoint específico por UDS.
        const urlBienestarina = `${backendUrl}/api/bienestarina/descargar?unidad=${encodeURIComponent(unidad)}`;
        console.info('[ALPHA73] Descarga Bienestarina por endpoint específico:', { unidad, url: urlBienestarina });
        descargarArchivoFormatoAlpha63({
            url: urlBienestarina,
            unidad,
            formato: 'Bienestarina',
            nombreBase: `BIENESTARINA_${String(unidad).replace(/[^A-Za-z0-9]+/g, '_')}.xlsx`
        });
        return;
    }
    if (esGrupoRppDescargaAlpha61(fmtOriginal)) {
        const periodo = periodoFormatosSeleccionado();
        descargarArchivoFormatoAlpha63({
            url: `${backendUrl}/api/rpp/descargar?unidad=${encodeURIComponent(unidad)}&grupo=${encodeURIComponent(fmtOriginal)}&mes=${encodeURIComponent(periodo.mes)}&anio=${encodeURIComponent(periodo.anio)}`,
            unidad,
            formato: `RPP ${fmtOriginal}`,
            nombreBase: `RPP_${String(unidad).replace(/[^A-Za-z0-9]+/g, '_')}_${fmtOriginal}.xlsx`
        });
        return;
    }
    const periodo = periodoFormatosSeleccionado();
    const queryPeriodo = `mes=${encodeURIComponent(periodo.mes)}&anio=${encodeURIComponent(periodo.anio)}`;
    descargarArchivoFormatoAlpha63({
        url: `${backendUrl}/api/descargar/${encodeURIComponent(unidad)}/${encodeURIComponent(formato)}?${queryPeriodo}`,
        unidad,
        formato,
        nombreBase: `${String(unidad).replace(/[^A-Za-z0-9]+/g, '_')}_${String(formato).replace(/[^A-Za-z0-9]+/g, '_')}_${periodo.anio}_${String(periodo.mes).padStart(2, '0')}.xlsx`
    });
}

async function descargarArchivoFormatoAlpha63({ url, unidad, formato, nombreBase }) {
    try {
        const token = authToken();
        if (!token) throw new Error('La sesión no está activa. Inicia sesión nuevamente.');
        const response = await fetch(url, {
            method: 'GET',
            credentials: 'same-origin',
            headers: {
                'Authorization': `Bearer ${token}`,
                'X-Auth-Token': token,
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const contentType = (response.headers.get('content-type') || '').toLowerCase();

        if (!response.ok || contentType.includes('application/json')) {
            let data = {};
            try {
                data = await response.json();
            } catch (error) {
                data = {};
            }
            const msg = data.mensaje || data.error || `No se pudo descargar ${formato} para esta UDS.`;
            if (typeof mostrarMensaje === 'function') {
                mostrarMensaje('message-box', msg, 'error');
            } else {
                alert(msg);
            }
            console.warn('Descarga de formato no realizada:', { unidad, formato, data });
            return;
        }

        const blob = await response.blob();
        if (!blob || blob.size === 0) {
            throw new Error(`El archivo de ${formato} llegó vacío.`);
        }

        let filename = nombreBase || `FORMATO_${String(unidad).replace(/[^A-Za-z0-9]+/g, '_')}.xlsx`;
        const disposition = response.headers.get('content-disposition') || '';
        const match = disposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i);
        if (match && match[1]) {
            filename = decodeURIComponent(match[1].replace(/"/g, '').trim());
        }

        const blobUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1500);

        if (typeof mostrarMensaje === 'function') {
            mostrarMensaje('message-box', `${formato} descargado para ${unidad}.`, 'success');
        }
    } catch (error) {
        const msg = `No se pudo descargar ${formato} para ${unidad}: ${error.message || error}`;
        if (typeof mostrarMensaje === 'function') {
            mostrarMensaje('message-box', msg, 'error');
        } else {
            alert(msg);
        }
        console.error('Error descargando formato:', { unidad, formato, error });
    }
}

async function descargarBienestarinaAlpha62(unidad) {
    if (!unidad) {
        alert('Debe seleccionar una UDS antes de descargar Bienestarina.');
        return;
    }
    const url = `${backendUrl}/api/bienestarina/descargar?unidad=${encodeURIComponent(unidad)}`;
    return descargarArchivoFormatoAlpha63({
        url,
        unidad,
        formato: 'Bienestarina',
        nombreBase: `BIENESTARINA_${String(unidad).replace(/[^A-Za-z0-9]+/g, '_')}.xlsx`
    });
}

async function descargarRppCategoria(unidad, grupo) {
    if (!unidad || !grupo) {
        alert('Debe seleccionar una unidad y un grupo etario para descargar RPP.');
        return;
    }
    const periodo = periodoFormatosSeleccionado();
    const url = `${backendUrl}/api/rpp/descargar?unidad=${encodeURIComponent(unidad)}&grupo=${encodeURIComponent(grupo)}&mes=${encodeURIComponent(periodo.mes)}&anio=${encodeURIComponent(periodo.anio)}`;
    if (typeof mostrarMensaje === 'function') {
        mostrarMensaje('message-box', `Generando RPP ${grupo} para ${unidad}...`, 'success');
    }
    return descargarArchivoFormatoAlpha63({
        url,
        unidad,
        formato: `RPP ${grupo}`,
        nombreBase: `RPP_${String(unidad).replace(/[^A-Za-z0-9]+/g, '_')}_${grupo}.xlsx`
    });
}
window.descargarRppCategoria = descargarRppCategoria;

// Los botones RPP se crean dinámicamente al renderizar la Base Maestra.
// Delegar el clic evita depender de JavaScript inline, funciona con un solo
// clic y mantiene el evento aunque la tabla sea reconstruida.
document.addEventListener('click', (event) => {
    const button = event.target?.closest?.('[data-rpp-download="1"]');
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();
    if (button.dataset.rppBusy === '1') return;
    button.dataset.rppBusy = '1';
    button.disabled = true;
    descargarRppCategoria(button.dataset.rppUnidad, button.dataset.rppGrupo)
        .finally(() => {
            button.dataset.rppBusy = '0';
            button.disabled = false;
        });
});

function subirPlantilla() {
    const input = document.getElementById('input-template');
    const tipo = document.getElementById('template-type').value;
    const version = document.getElementById('template-version').value.trim() || '1.0';
    const file = input.files[0];
    const error = validarArchivo(file, allowedTemplateExtensions, 20);
    if (error) {
        mostrarMensaje('template-message', error, 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('tipo', tipo);
    formData.append('version', version);

    fetch(`${backendUrl}/api/plantillas`, { method: 'POST', body: formData })
        .then(manejarRespuestaJson)
        .then((data) => {
            mostrarMensaje('template-message', data.message, 'success');
            input.value = '';
            fetchPlantillas();
        })
        .catch((error) => {
            mostrarMensaje('template-message', error.message || 'Error al subir plantilla.', 'error');
        });
}

function fetchPlantillas() {
    fetch(`${backendUrl}/api/plantillas`)
        .then(manejarRespuestaJson)
        .then((data) => {
            const lista = document.getElementById('plantillas-list');
            plantillasRegistradas = Array.isArray(data.plantillas) ? data.plantillas : [];

            if (!lista) return;

            if (plantillasRegistradas.length === 0) {
                lista.innerHTML = `<tr><td colspan="6" class="px-6 py-8 text-center text-slate-500">No hay plantillas registradas aún.</td></tr>`;
                return;
            }

            lista.innerHTML = plantillasRegistradas.map((item) => {
                const estado = String(item.estado || (item.activa ? 'activo' : 'inactivo')).toLowerCase();
                const estadoClase = estado === 'activo'
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                    : 'bg-slate-500/10 text-slate-300 border-slate-500/30';

                return `
                    <tr class="hover:bg-slate-900/50 transition">
                        <td class="px-6 py-4">${escaparHtml(item.nombre_original || item.nombre || '')}</td>
                        <td class="px-6 py-4">${escaparHtml(item.tipo || '')}</td>
                        <td class="px-6 py-4">${escaparHtml(item.version || item['versión'] || '1.0')}</td>
                        <td class="px-6 py-4">${escaparHtml(fechaPlantillaLegible(item.fecha_carga || item.fecha_ultima_actualizacion))}</td>
                        <td class="px-6 py-4">
                            <span class="rounded-lg border px-2.5 py-1 text-xs ${estadoClase}">${escaparHtml(estado)}</span>
                        </td>
                        <td class="px-6 py-4">
                            <div class="flex flex-wrap gap-2">
                                <button onclick="editarPlantilla(${Number(item.id)})" class="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-xs text-cyan-300 hover:bg-cyan-500/20 transition">Editar</button>
                                <button onclick="eliminarPlantilla(${Number(item.id)}, false)" class="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-300 hover:bg-amber-500/20 transition">Eliminar</button>
                                <button onclick="eliminarPlantilla(${Number(item.id)}, true)" class="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-300 hover:bg-rose-500/20 transition">Borrar</button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        })
        .catch((error) => {
            console.error('Error al cargar plantillas', error);
        });
}

function editarPlantilla(id) {
    const plantilla = plantillasRegistradas.find((item) => Number(item.id) === Number(id));
    if (!plantilla) {
        mostrarMensaje('template-message', 'No se encontró la plantilla seleccionada.', 'error');
        return;
    }

    const tipo = prompt('Tipo de plantilla:', plantilla.tipo || 'Otros');
    if (tipo === null) return;

    const version = prompt('Versión:', plantilla.version || plantilla['versión'] || '1.0');
    if (version === null) return;

    const estadoActual = plantilla.estado || (plantilla.activa ? 'activo' : 'inactivo');
    const estado = prompt('Estado: activo o inactivo', estadoActual);
    if (estado === null) return;

    fetch(`${backendUrl}/api/plantillas/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            tipo: tipo.trim() || plantilla.tipo || 'Otros',
            version: version.trim() || '1.0',
            estado: estado.trim() || estadoActual || 'activo'
        })
    })
        .then(manejarRespuestaJson)
        .then((data) => {
            mostrarMensaje('template-message', data.message || 'Plantilla actualizada.', 'success');
            fetchPlantillas();
        })
        .catch((error) => {
            mostrarMensaje('template-message', error.message || 'No se pudo actualizar la plantilla.', 'error');
        });
}

function eliminarPlantilla(id, permanente = false) {
    const plantilla = plantillasRegistradas.find((item) => Number(item.id) === Number(id));
    const nombre = plantilla?.nombre_original || plantilla?.nombre || 'esta plantilla';

    const mensaje = permanente
        ? `Vas a BORRAR permanentemente ${nombre}. Se eliminará de la lista y se intentará borrar el archivo físico. ¿Continuar?`
        : `Vas a ELIMINAR/DESACTIVAR ${nombre}. Se conserva el historial y el archivo. ¿Continuar?`;

    if (!confirm(mensaje)) return;

    const url = `${backendUrl}/api/plantillas/${encodeURIComponent(id)}${permanente ? '?hard=1' : ''}`;
    fetch(url, { method: 'DELETE' })
        .then(manejarRespuestaJson)
        .then((data) => {
            mostrarMensaje('template-message', data.message || 'Operación realizada.', 'success');
            fetchPlantillas();
        })
        .catch((error) => {
            mostrarMensaje('template-message', error.message || 'No se pudo eliminar la plantilla.', 'error');
        });
}

function subirNutricion() {
    const input = document.getElementById('input-nutricion');
    const file = input.files[0];
    const error = validarArchivo(file, allowedNutritionExtensions, 20);
    if (error) {
        mostrarMensaje('nutricion-message', error, 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    fetch(`${backendUrl}/api/nutricion`, { method: 'POST', body: formData })
        .then(manejarRespuestaJson)
        .then((data) => {
            mostrarMensaje('nutricion-message', data.message, 'success');
            document.getElementById('nutri-al-dia').innerText = data.status.al_dia || 0;
            document.getElementById('nutri-proximo').innerText = data.status.proximo_vencer || 0;
            document.getElementById('nutri-vencido').innerText = data.status.vencido || 0;
            input.value = '';
            renderBoaNutricion(data.boa || {});
            fetchBoaNutricion();
        })
        .catch((error) => {
            mostrarMensaje('nutricion-message', error.message || 'Error al procesar nutrición.', 'error');
        });
}


function estadoNutricionClase(valor) {
    const v = normalizarFiltro(valor);
    if (v.includes('DESNUTRICION') || v.includes('RIESGO') || v.includes('VENCIDO')) return 'text-rose-300';
    if (v.includes('PENDIENTE') || v.includes('PROXIMO')) return 'text-amber-300';
    if (v.includes('ADECUADO') || v.includes('AL DIA')) return 'text-emerald-300';
    return 'text-slate-300';
}

function renderBoaNutricion(boa = {}) {
    const resumenBox = document.getElementById('nutricion-boa-resumen');
    const body = document.getElementById('nutricion-boa-list');
    if (!resumenBox || !body) return;
    const resumen = boa.resumen || {};
    const detalles = Array.isArray(boa.detalles) ? boa.detalles : [];
    const cards = [
        ['Adecuado', resumen.ADECUADO || 0],
        ['Riesgo', resumen.RIESGO || 0],
        ['Desnutrición', resumen.DESNUTRICION || 0],
        ['Pendiente', resumen.PENDIENTE || 0]
    ];
    resumenBox.innerHTML = cards.map(([label, value]) => `
        <div class="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
            <p class="text-xs text-slate-400">${escaparHtml(label)}</p>
            <p class="mt-1 text-2xl font-bold ${estadoNutricionClase(label)}">${escaparHtml(value)}</p>
        </div>
    `).join('');
    if (!detalles.length) {
        body.innerHTML = '<tr><td colspan="9" class="px-3 py-8 text-center text-slate-500">No hay registros de peso y talla todavía.</td></tr>';
        return;
    }
    body.innerHTML = detalles.slice(0, 250).map(item => `
        <tr class="hover:bg-slate-900/50">
            <td class="px-3 py-2">${escaparHtml(item.unidad || '')}</td>
            <td class="px-3 py-2 font-medium text-slate-200">${escaparHtml(item.nombre || '')}</td>
            <td class="px-3 py-2">${escaparHtml(item.documento || '')}</td>
            <td class="px-3 py-2">${escaparHtml(item.peso || '')}</td>
            <td class="px-3 py-2">${escaparHtml(item.talla || '')}</td>
            <td class="px-3 py-2 ${estadoNutricionClase(item.estado_nutricional)}">${escaparHtml(item.estado_nutricional || '')}</td>
            <td class="px-3 py-2 ${estadoNutricionClase(item.estado_control)}">${escaparHtml(item.estado_control || '')}</td>
            <td class="px-3 py-2">${escaparHtml(item.trimestre || '')}</td>
            <td class="px-3 py-2">${escaparHtml(item.fecha_proximo_control || '')}</td>
        </tr>
    `).join('');
}

function fetchBoaNutricion() {
    fetch(`${backendUrl}/api/nutricion/boa`)
        .then(manejarRespuestaJson)
        .then((data) => renderBoaNutricion(data.boa || {}))
        .catch((error) => console.error('No se pudo cargar BOA nutrición', error));
}

function subirTalento() {
    const input = document.getElementById('input-talento');
    const file = input.files[0];
    const error = validarArchivo(file, allowedTalentExtensions, 20);
    if (error) {
        mostrarMensaje('talento-message', error, 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    fetch(`${backendUrl}/api/talento`, { method: 'POST', body: formData })
        .then(manejarRespuestaJson)
        .then((data) => {
            mostrarMensaje('talento-message', data.message, 'success');
            if (data.integracion) renderTalentoIntegracion(data.integracion);
            input.value = '';
            fetchTalento();
        })
        .catch((error) => {
            mostrarMensaje('talento-message', error.message || 'Error al procesar talento humano.', 'error');
        });
}

function fetchTalento() {
    const contenedor = document.getElementById('talento-list');
    if (!contenedor) return;

    fetch(`${backendUrl}/api/talento`)
        .then(manejarRespuestaJson)
        .then((data) => {
            talentoRegistrado = Array.isArray(data.talento) ? data.talento : [];
            renderTalento();
            if (data.integracion) {
                renderTalentoIntegracion(data.integracion);
            } else {
                fetchTalentoIntegracion();
            }
        })
        .catch((error) => {
            console.error('No se pudo cargar talento humano', error);
            contenedor.innerHTML = '<tr><td colspan="10" class="px-6 py-8 text-center text-rose-400">No se pudo cargar talento humano.</td></tr>';
        });
    fetchTalentoIntegral();
    fetch(`${backendUrl}/api/base-maestra/resumen`)
        .then(manejarRespuestaJson)
        .then((data) => {
            talentoEstructuraMaestra = data?.estructura_talento || null;
            renderEquipoCoordinadores();
        })
        .catch((error) => console.error('No se pudo cargar la estructura maestra de Talento Humano', error));
}

let thIntegralBound=false;
async function actualizarTalentoIntegral(){
    const button=document.getElementById('th-integral-actualizar');
    const status=document.getElementById('th-integral-estado');
    if(button?.disabled)return;
    if(button){button.disabled=true;button.textContent='Sincronizando...'}
    if(status){status.className='mt-2 text-xs text-cyan-300';status.textContent='Sincronizando la fuente maestra antes de actualizar el tablero...'}
    try{
        const syncResponse=await fetch(`${backendUrl}/api/talento-core/sincronizar`,{method:'POST'});
        const syncData=await manejarRespuestaJson(syncResponse);
        const total=Number(syncData?.resultado?.talento_base||0);
        const dashboard=await fetchTalentoIntegral();
        const visible=Number(dashboard?.resumen?.colaboradores_activos||0);
        if(status){
            status.className=`mt-2 text-xs ${visible?'text-emerald-300':'text-amber-300'}`;
            status.textContent=visible
                ? `Tablero actualizado: ${visible} colaborador(es) activo(s).`
                : total
                    ? 'La fuente fue sincronizada, pero no hay colaboradores activos para esta fundación.'
                    : 'La fuente maestra está vacía. Primero carga o registra Talento Humano.';
        }
    }catch(error){
        if(status){status.className='mt-2 text-xs text-rose-400';status.textContent=error.message||'No se pudo sincronizar y actualizar el tablero.'}
    }finally{
        if(button){button.disabled=false;button.textContent='Actualizar tablero'}
    }
}
async function fetchTalentoIntegral(){
    const box=document.getElementById('th-integral-resumen'); if(!box)return;
    try{
        const response=await fetch(`${backendUrl}/api/talento-core/integral/dashboard`); const data=await manejarRespuestaJson(response); const r=data.resumen||{};
        box.innerHTML=[['Colaboradores',r.colaboradores_activos],['Documentos',r.documentos],['Vencidos',r.documentos_vencidos],['Formaciones',r.formaciones_programadas],['Evaluaciones borrador',r.evaluaciones_borrador]].map(([l,v])=>`<div class="rounded-xl border border-slate-800 p-3"><p class="text-xs text-slate-500">${escaparHtml(l)}</p><p class="text-2xl font-bold">${escaparHtml(v||0)}</p></div>`).join('');
        const options='<option value="">Selecciona colaborador</option>'+(data.personas||[]).map(p=>`<option value="${p.id}">${escaparHtml(p.nombre)} · ${escaparHtml(p.unidad||'Sin UCA')}</option>`).join(''); document.querySelectorAll('.th-persona').forEach(x=>x.innerHTML=options);
        document.getElementById('th-integral-documentos').innerHTML=(data.documentos||[]).slice(0,12).map(x=>`<div class="py-2 border-b border-slate-800"><strong>${escaparHtml(x.persona_nombre)}</strong> · ${escaparHtml(x.tipo)} · ${escaparHtml(x.fecha_vencimiento||'Sin vencimiento')}</div>`).join('')||'Sin alertas documentales.';
        document.getElementById('th-integral-capacidades').innerHTML=(data.mapa_capacidades||[]).map(x=>`<div class="py-2 border-b border-slate-800">${escaparHtml(x.capacidad)} · ${escaparHtml(x.nivel)}: ${escaparHtml(x.total)}</div>`).join('')||'Aún no se han registrado capacidades.';
        if(!thIntegralBound){[['th-documento-form','documentos'],['th-formacion-form','formaciones']].forEach(([id,entity])=>{const f=document.getElementById(id);f?.addEventListener('submit',async e=>{e.preventDefault();try{await manejarRespuestaJson(await fetch(`${backendUrl}/api/talento-core/integral/${entity}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(f)))}));f.reset();mostrarMensaje('talento-message','Expediente actualizado.','success');fetchTalentoIntegral()}catch(err){mostrarMensaje('talento-message',err.message,'error')}})});thIntegralBound=true}
        return data;
    }catch(error){box.innerHTML='<p class="text-rose-400">No se pudo cargar el tablero integral.</p>';console.error(error);throw error}
}

function renderTalentoIntegracion(integracion = {}) {
    const contenedor = document.getElementById('talento-integracion-resumen');
    if (!contenedor) return;
    contenedor.querySelectorAll('[data-ti]').forEach((el) => {
        const key = el.getAttribute('data-ti');
        el.textContent = integracion[key] ?? 0;
    });
    const estado = document.getElementById('talento-integracion-estado');
    if (estado) {
        const ultimo = integracion.ultimo_evento;
        estado.textContent = ultimo?.fecha_accion
            ? `Última sincronización: ${fechaPlantillaLegible(ultimo.fecha_accion)} por ${ultimo.usuario || 'sistema'}`
            : 'Aún no hay sincronización registrada.';
    }
}

function fetchTalentoIntegracion() {
    const contenedor = document.getElementById('talento-integracion-resumen');
    if (!contenedor) return;
    fetch(`${backendUrl}/api/talento/integracion`)
        .then(manejarRespuestaJson)
        .then((data) => renderTalentoIntegracion(data.integracion || {}))
        .catch((error) => console.error('No se pudo cargar integración de talento humano', error));
}

function sincronizarTalentoGlobal() {
    mostrarMensaje('talento-message', 'Sincronizando talento humano con todos los módulos...', 'success');
    fetch(`${backendUrl}/api/talento/sincronizar-global`, { method: 'POST' })
        .then(manejarRespuestaJson)
        .then((data) => {
            renderTalentoIntegracion(data.integracion || {});
            mostrarMensaje('talento-message', data.message || 'Talento Humano sincronizado con toda la plataforma.', 'success');
            fetchTalento();
            if (typeof gpCargarDashboard === 'function') {
                try { gpCargarDashboard(); } catch (_) {}
            }
            if (typeof gcCargarDashboard === 'function') {
                try { gcCargarDashboard(); } catch (_) {}
            }
        })
        .catch((error) => {
            mostrarMensaje('talento-message', error.message || 'No se pudo sincronizar talento humano.', 'error');
        });
}


function talentoTipoTexto(item = {}) {
    return normalizarFiltro([item.tipo_equipo, item.cargo, item.perfil, item.rol_normalizado].filter(Boolean).join(' '));
}

function talentoEsCoordinador(item = {}) {
    return talentoTipoTexto(item).includes('COORDINADOR');
}

function talentoEtiquetaTipo(item = {}) {
    const tipo = talentoTipoTexto(item);
    if (tipo.includes('DOCENTE') || tipo.includes('AGENTE')) return 'AGENTE EDUCATIVO';
    if (tipo.includes('COORDINADOR')) return 'COORDINADOR';
    if (tipo.includes('NUTRIC')) return 'NUTRICIONISTA';
    if (tipo.includes('ENFERMER') || tipo.includes('SALUD')) return 'ENFERMERÍA';
    if (tipo.includes('PSICOSOCIAL') || tipo.includes('PSICOLOG')) return 'PSICOSOCIAL';
    if (tipo.includes('PEDAGOG')) return 'PEDAGOGÍA';
    if (tipo.includes('ADMINISTR')) return 'ADMINISTRATIVO';
    if (tipo.includes('SABEDOR') || tipo.includes('ARTISTA')) return 'APOYO CULTURAL';
    return item.tipo_equipo || item.cargo || 'APOYO';
}

function talentoCoordinadorPorUnidad(items = talentoRegistrado) {
    const mapa = {};
    (items || []).forEach((item) => {
        if (!talentoEsCoordinador(item)) return;
        const unidadKey = normalizarFiltro(item.unidad || '');
        if (unidadKey && item.nombre) mapa[unidadKey] = item.nombre;
        try {
            const unidades = JSON.parse(item.unidades || '[]');
            if (Array.isArray(unidades)) {
                unidades.forEach((unidad) => {
                    const key = normalizarFiltro(unidad || '');
                    if (key && item.nombre) mapa[key] = item.nombre;
                });
            }
        } catch (_) {}
    });
    return mapa;
}

function talentoCoordinadorVisible(item = {}, mapa = {}) {
    if (item.coordinador) return item.coordinador;
    if (talentoEsCoordinador(item)) return item.nombre || 'Coordinador sin nombre';
    const key = normalizarFiltro(item.unidad || '');
    return mapa[key] || '';
}

function renderEquipoCoordinadores() {
    const contenedor = document.getElementById('equipo-coordinadores');
    if (!contenedor) return;

    const estructura = talentoEstructuraMaestra || {};
    const equiposMaestros = Array.isArray(estructura.equipos) ? estructura.equipos : [];
    if (equiposMaestros.length) {
        contenedor.innerHTML = equiposMaestros.map((equipo, indice) => {
            const cargos = Object.entries(equipo.cargos || {}).sort((a, b) => a[0].localeCompare(b[0], 'es'));
            const botones = `<button type="button" onclick="talentoFiltrarEquipo(${indice}, '')" class="rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-1 text-xs text-cyan-200">Ver todos: ${escaparHtml(equipo.total_personas || 0)}</button>` + cargos.map(([cargo, total]) => `<button type="button" onclick="talentoFiltrarEquipo(${indice}, decodeURIComponent('${encodeURIComponent(cargo)}'))" class="rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-1 text-xs text-violet-200 hover:bg-violet-500/20">${escaparHtml(cargo)}: ${escaparHtml(total)}</button>`).join('');
            const filas = (equipo.integrantes || []).map(persona => `<tr data-th-rol="${escaparHtml(persona.rol_normalizado || '')}"><td class="px-3 py-2 text-slate-200">${escaparHtml(persona.nombre || '')}</td><td class="px-3 py-2">${escaparHtml(persona.cargo || persona.rol_normalizado || '')}</td><td class="px-3 py-2">${escaparHtml(persona.unidad_servicio || '—')}</td><td class="px-3 py-2">${escaparHtml(persona.telefono || persona.correo || '—')}</td></tr>`).join('');
            return `<details data-th-equipo="${indice}" data-th-filtro="" class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <summary class="cursor-pointer list-none"><div class="flex flex-wrap items-center justify-between gap-3"><div><p class="font-semibold text-slate-100">${escaparHtml(equipo.coordinador)}</p><p class="mt-1 text-xs text-slate-500">${escaparHtml(equipo.total_personas || 0)} integrantes</p></div><div class="flex flex-wrap gap-1">${botones}</div></div></summary>
                <div class="mt-3 flex flex-wrap items-center justify-between gap-2"><span data-th-resultado class="text-xs font-semibold text-emerald-300">Mostrando todo el equipo: ${escaparHtml(equipo.total_personas || 0)} personas</span><button type="button" onclick="talentoImprimirEquipo(${indice})" class="rounded-xl border border-amber-500/40 px-3 py-2 text-xs text-amber-300 hover:bg-amber-500/10">Imprimir selección</button></div>
                <div class="mt-4 overflow-auto"><table class="w-full min-w-[680px] text-xs"><thead class="bg-slate-950 text-slate-300"><tr><th class="px-3 py-2 text-left">Nombre</th><th class="px-3 py-2 text-left">Cargo</th><th class="px-3 py-2 text-left">Unidad</th><th class="px-3 py-2 text-left">Contacto</th></tr></thead><tbody>${filas}</tbody></table></div>
            </details>`;
        }).join('');
        const estado = document.getElementById('talento-equipos-estado');
        if (estado) estado.textContent = `Carga #${estructura.carga_id || '—'} · ${estructura.total_coordinadores || 0} coordinadores · ${estructura.total_personas || 0} personas únicas · ${estructura.asignados_por_unidad || 0} integrantes vinculados por unidad · ${estructura.duplicados_omitidos || 0} duplicados omitidos · ${(estructura.unidades_ambiguas || []).length} unidades requieren revisión`;
        return;
    }

    const activos = (talentoRegistrado || []).filter((item) => String(item.estado || (item.activo ? 'activo' : 'inactivo')).toLowerCase() === 'activo');
    const coordinadorPorUnidad = talentoCoordinadorPorUnidad(activos);
    const grupos = {};

    activos.forEach((item) => {
        const coordinador = talentoCoordinadorVisible(item, coordinadorPorUnidad) || 'Sin coordinador asignado';
        if (!grupos[coordinador]) {
            grupos[coordinador] = { total: 0, agentes: 0, psicosocial: 0, enfermeria: 0, nutricion: 0, pedagogia: 0, administrativo: 0, apoyo: 0, unidades: new Set() };
        }
        const g = grupos[coordinador];
        g.total += 1;
        if (item.unidad) g.unidades.add(item.unidad);
        const tipo = talentoTipoTexto(item);
        if (tipo.includes('DOCENTE') || tipo.includes('AGENTE')) g.agentes += 1;
        else if (tipo.includes('PSICOSOCIAL') || tipo.includes('PSICOLOG')) g.psicosocial += 1;
        else if (tipo.includes('NUTRIC')) g.nutricion += 1;
        else if (tipo.includes('ENFERMER') || tipo.includes('SALUD')) g.enfermeria += 1;
        else if (tipo.includes('PEDAGOG')) g.pedagogia += 1;
        else if (tipo.includes('ADMINISTR')) g.administrativo += 1;
        else g.apoyo += 1;
    });

    const nombres = Object.keys(grupos).sort((a, b) => a.localeCompare(b, 'es'));
    if (nombres.length === 0) {
        contenedor.innerHTML = '<p class="text-slate-500">No hay equipos registrados todavía.</p>';
        return;
    }

    contenedor.innerHTML = nombres.map((nombre) => {
        const g = grupos[nombre];
        return `
            <div class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <p class="font-semibold text-slate-100">${escaparHtml(nombre)}</p>
                <p class="mt-1 text-xs text-slate-500">${g.unidades.size} unidad(es) asociada(s) · ${g.total} persona(s)</p>
                <div class="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <span>Agentes educativos: <strong class="text-slate-200">${g.agentes}</strong></span>
                    <span>Psicosocial: <strong class="text-slate-200">${g.psicosocial}</strong></span>
                    <span>Enfermería: <strong class="text-slate-200">${g.enfermeria}</strong></span>
                    <span>Nutrición: <strong class="text-slate-200">${g.nutricion}</strong></span>
                    <span>Pedagogía: <strong class="text-slate-200">${g.pedagogia}</strong></span>
                    <span>Administrativo: <strong class="text-slate-200">${g.administrativo}</strong></span>
                    <span>Apoyo/Sabedor: <strong class="text-slate-200">${g.apoyo}</strong></span>
                </div>
            </div>
        `;
    }).join('');
}

function talentoFiltrarEquipo(indice, rol) {
    const panel = document.querySelector(`[data-th-equipo="${Number(indice)}"]`);
    if (!panel) return;
    panel.open = true;
    panel.dataset.thFiltro = rol || '';
    let visibles = 0;
    panel.querySelectorAll('[data-th-rol]').forEach((fila) => {
        const mostrar = !rol || fila.dataset.thRol === rol;
        fila.classList.toggle('hidden', !mostrar);
        if (mostrar) visibles += 1;
    });
    const resultado = panel.querySelector('[data-th-resultado]');
    if (resultado) resultado.textContent = rol ? `${rol}: ${visibles} personas` : `Mostrando todo el equipo: ${visibles} personas`;
}

function talentoVentanaImpresion(titulo, subtitulo, personas) {
    const ventana = window.open('', '_blank', 'width=1000,height=750');
    if (!ventana) return mostrarMensaje('talento-message', 'El navegador bloqueó la ventana de impresión.', 'error');
    const filas = personas.map(persona => `<tr><td>${escaparHtml(persona.nombre || '')}</td><td>${escaparHtml(persona.cargo || persona.rol_normalizado || '')}</td><td>${escaparHtml(persona.unidad_servicio || persona.unidad || '—')}</td><td>${escaparHtml(persona.telefono || persona.correo || '—')}</td></tr>`).join('');
    ventana.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escaparHtml(titulo)}</title><style>body{font-family:Arial,sans-serif;margin:28px;color:#111}h1{font-size:20px;margin-bottom:4px}p{margin:4px 0 18px;color:#444}table{width:100%;border-collapse:collapse;font-size:12px}th,td{border:1px solid #bbb;padding:7px;text-align:left}th{background:#eee}@media print{button{display:none}}</style></head><body><h1>${escaparHtml(titulo)}</h1><p>${escaparHtml(subtitulo)} · ${personas.length} personas</p><table><thead><tr><th>Nombre</th><th>Cargo</th><th>Unidad</th><th>Contacto</th></tr></thead><tbody>${filas}</tbody></table><script>window.onload=()=>window.print()<\/script></body></html>`);
    ventana.document.close();
}

function talentoImprimirEquipo(indice) {
    const equipo = talentoEstructuraMaestra?.equipos?.[Number(indice)];
    const panel = document.querySelector(`[data-th-equipo="${Number(indice)}"]`);
    if (!equipo || !panel) return;
    const rol = panel.dataset.thFiltro || '';
    const personas = (equipo.integrantes || []).filter(persona => !rol || persona.rol_normalizado === rol);
    talentoVentanaImpresion(`Equipo de ${equipo.coordinador}`, rol ? `Cargo seleccionado: ${rol}` : 'Equipo completo', personas);
}

function talentoImprimirTodos() {
    const equipos = talentoEstructuraMaestra?.equipos || [];
    const personas = equipos.flatMap(equipo => (equipo.integrantes || []).map(persona => ({ ...persona, coordinador_impresion: equipo.coordinador })));
    if (!personas.length) return mostrarMensaje('talento-message', 'No hay equipos disponibles para imprimir.', 'error');
    talentoVentanaImpresion('Coordinadores y equipos de Talento Humano', `${equipos.length} coordinadores`, personas);
}

function renderTalento() {
    const contenedor = document.getElementById('talento-list');
    if (!contenedor) return;

    if (!Array.isArray(talentoRegistrado) || talentoRegistrado.length === 0) {
        contenedor.innerHTML = '<tr><td colspan="10" class="px-6 py-8 text-center text-slate-500">No hay talento humano registrado todavía.</td></tr>';
        renderEquipoCoordinadores();
        return;
    }

    const coordinadorPorUnidad = talentoCoordinadorPorUnidad(talentoRegistrado);
    contenedor.innerHTML = talentoRegistrado.map((item) => {
        const estado = String(item.estado || (item.activo ? 'activo' : 'inactivo')).toLowerCase();
        const tipoVisible = talentoEtiquetaTipo(item);
        const coordinadorVisible = talentoCoordinadorVisible(item, coordinadorPorUnidad);
        return `
            <tr class="hover:bg-slate-900/50 transition">
                <td class="px-4 py-3 font-medium text-slate-200">${escaparHtml(item.unidad || '')}</td>
                <td class="px-4 py-3">${escaparHtml(item.nombre || '')}</td>
                <td class="px-4 py-3">${escaparHtml(item.documento || '')}</td>
                <td class="px-4 py-3">${escaparHtml(tipoVisible)}</td>
                <td class="px-4 py-3">${escaparHtml(item.cargo || '')}</td>
                <td class="px-4 py-3">${escaparHtml(item.direccion || '')}</td>
                <td class="px-4 py-3">${escaparHtml(item.telefono || '')}</td>
                <td class="px-4 py-3">${escaparHtml(coordinadorVisible || '')}<div class="text-[11px] text-slate-500">${escaparHtml(estado)}</div></td>
                <td class="px-4 py-3">${escaparHtml(item.contrato || '')}</td>
                <td class="px-4 py-3">
                    ${item.solo_lectura ? '<span class="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-300">Base Maestra</span>' : `
                    <div class="flex flex-wrap gap-2">
                        <button onclick="editarTalento(${Number(item.id)})" class="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 text-xs text-cyan-300 hover:bg-cyan-500/20">Editar</button>
                        <button onclick="eliminarTalento(${Number(item.id)}, false)" class="rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-300 hover:bg-amber-500/20">Eliminar</button>
                        <button onclick="eliminarTalento(${Number(item.id)}, true)" class="rounded-lg border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-xs text-rose-300 hover:bg-rose-500/20">Borrar</button>
                    </div>`}
                </td>
            </tr>
        `;
    }).join('');
    renderEquipoCoordinadores();
}

function guardarTalentoManual() {
    const data = {
        nombre: document.getElementById('talento-nombre')?.value.trim() || '',
        documento: document.getElementById('talento-documento')?.value.trim() || '',
        tipo_equipo: document.getElementById('talento-tipo-equipo')?.value.trim() || 'DOCENTE',
        cargo: document.getElementById('talento-cargo')?.value.trim() || 'AGENTE EDUCATIVO',
        unidad: document.getElementById('talento-unidad')?.value.trim() || '',
        direccion: document.getElementById('talento-direccion')?.value.trim() || '',
        telefono: document.getElementById('talento-telefono')?.value.trim() || '',
        coordinador: document.getElementById('talento-coordinador')?.value.trim() || '',
        contrato: document.getElementById('talento-contrato')?.value.trim() || '',
        estado: 'activo'
    };

    if (!data.nombre || !data.documento) {
        mostrarMensaje('talento-message', 'Nombre y documento son obligatorios.', 'error');
        return;
    }

    fetch(`${backendUrl}/api/talento`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
        .then(manejarRespuestaJson)
        .then((resp) => {
            mostrarMensaje('talento-message', resp.message || 'Talento humano guardado.', 'success');
            if (resp.integracion) renderTalentoIntegracion(resp.integracion);
            ['talento-nombre', 'talento-documento', 'talento-cargo', 'talento-unidad', 'talento-direccion', 'talento-telefono', 'talento-coordinador', 'talento-contrato'].forEach((id) => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            fetchTalento();
        })
        .catch((error) => mostrarMensaje('talento-message', error.message || 'No se pudo guardar talento humano.', 'error'));
}

function editarTalento(id) {
    const item = talentoRegistrado.find((row) => Number(row.id) === Number(id));
    if (!item) return;

    const nombre = prompt('Nombre completo:', item.nombre || '');
    if (nombre === null) return;
    const documento = prompt('Documento:', item.documento || '');
    if (documento === null) return;
    const tipo_equipo = prompt('Tipo equipo: DOCENTE, COORDINADOR, PSICOSOCIAL, ENFERMERIA, PEDAGOGIA, ADMINISTRATIVO', item.tipo_equipo || 'DOCENTE');
    if (tipo_equipo === null) return;
    const cargo = prompt('Cargo:', item.cargo || 'AGENTE EDUCATIVO');
    if (cargo === null) return;
    const unidad = prompt('Unidad / comunidad:', item.unidad || '');
    if (unidad === null) return;
    const direccion = prompt('Dirección:', item.direccion || '');
    if (direccion === null) return;
    const telefono = prompt('Teléfono:', item.telefono || '');
    if (telefono === null) return;
    const coordinador = prompt('Coordinador responsable:', item.coordinador || '');
    if (coordinador === null) return;
    const contrato = prompt('Contrato / equipo:', item.contrato || '');
    if (contrato === null) return;
    const estado = prompt('Estado: activo o inactivo', item.estado || 'activo');
    if (estado === null) return;

    fetch(`${backendUrl}/api/talento/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, documento, tipo_equipo, cargo, unidad, direccion, telefono, coordinador, contrato, estado })
    })
        .then(manejarRespuestaJson)
        .then((resp) => {
            mostrarMensaje('talento-message', resp.message || 'Talento humano actualizado.', 'success');
            if (resp.integracion) renderTalentoIntegracion(resp.integracion);
            fetchTalento();
        })
        .catch((error) => mostrarMensaje('talento-message', error.message || 'No se pudo actualizar talento humano.', 'error'));
}

function eliminarTalento(id, permanente = false) {
    const item = talentoRegistrado.find((row) => Number(row.id) === Number(id));
    const nombre = item?.nombre || 'este registro';
    const pregunta = permanente
        ? `Vas a borrar permanentemente ${nombre}. ¿Continuar?`
        : `Vas a desactivar ${nombre}. ¿Continuar?`;
    if (!confirm(pregunta)) return;

    fetch(`${backendUrl}/api/talento/${encodeURIComponent(id)}${permanente ? '?hard=1' : ''}`, { method: 'DELETE' })
        .then(manejarRespuestaJson)
        .then((resp) => {
            mostrarMensaje('talento-message', resp.message || 'Operación realizada.', 'success');
            if (resp.integracion) renderTalentoIntegracion(resp.integracion);
            fetchTalento();
        })
        .catch((error) => mostrarMensaje('talento-message', error.message || 'No se pudo eliminar talento humano.', 'error'));
}

function subirDocumentoInstitucional() {
    const input = document.getElementById('input-documento');
    const file = input.files[0];
    const error = validarArchivo(file, allowedDocumentExtensions, 50);
    if (error) {
        mostrarMensaje('documento-message', error, 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('tipo', document.getElementById('doc-type').value);
    formData.append('titulo', document.getElementById('doc-title').value.trim() || file.name);
    formData.append('version', document.getElementById('doc-version').value.trim() || '1.0');

    fetch(`${backendUrl}/api/documentos-institucionales`, { method: 'POST', body: formData })
        .then(manejarRespuestaJson)
        .then((data) => {
            const reglas = data.reglas_inferidas ? ` Reglas creadas: ${data.reglas_inferidas}.` : '';
            const detalle = data.indexado ? ` Indexado para busqueda y asistente.${reglas}` : ' Guardado; este formato no permite extraccion local de texto.';
            mostrarMensaje('documento-message', `${data.message}${detalle}`, 'success');
            input.value = '';
            fetchDocumentosInstitucionales();
            evaluarOperacionICBF(false);
        })
        .catch((error) => {
            mostrarMensaje('documento-message', error.message || 'Error al cargar documento.', 'error');
        });
}

function inicializarPeriodoEntregable() {
    const input = document.getElementById('entregable-periodo');
    if (!input) return;
    input.value = new Date().toISOString().slice(0, 7);
}

function fetchDocumentosInstitucionales() {
    const contenedor = document.getElementById('documentos-list');
    if (!contenedor) return;
    fetch(`${backendUrl}/api/documentos-institucionales`)
        .then(manejarRespuestaJson)
        .then((data) => {
            const documentos = data.documentos || [];
            if (documentos.length === 0) {
                contenedor.innerHTML = '<p>No hay documentos institucionales cargados.</p>';
                return;
            }
            contenedor.innerHTML = documentos.slice(0, 5).map((doc) => `
                <div class="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                    <p class="text-slate-200">${doc.tipo}: ${doc.titulo}</p>
                    <p class="text-xs">Versión ${doc.version} · ${doc.estado}</p>
                </div>
            `).join('');
        })
        .catch(() => {
            contenedor.innerHTML = '<p>No se pudo cargar el centro documental.</p>';
        });
}

function estadoEntregableClase(estado) {
    const e = normalizarFiltro(estado);
    if (e === 'CARGADO') return 'text-emerald-400';
    if (e === 'VENCIDO') return 'text-rose-400';
    if (e === 'PROXIMO') return 'text-amber-400';
    return 'text-slate-400';
}

function fetchEntregablesOperacion() {
    const contenedor = document.getElementById('entregables-list');
    if (!contenedor) return;
    const periodo = document.getElementById('entregable-periodo')?.value || new Date().toISOString().slice(0, 7);
    fetch(`${backendUrl}/api/entregables-operacion?periodo=${encodeURIComponent(periodo)}`)
        .then(manejarRespuestaJson)
        .then((data) => {
            const tablero = data.tablero || [];
            const resumen = data.resumen || {};

            ['total', 'cargados', 'pendientes', 'proximos', 'vencidos'].forEach((key) => {
                const el = document.getElementById(`entregables-${key}`);
                if (el) el.innerText = resumen[key] ?? 0;
            });

            if (tablero.length === 0) {
                contenedor.innerHTML = '<p class="text-slate-500">No hay entregables configurados para este periodo.</p>';
                return;
            }

            contenedor.innerHTML = `
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs text-slate-400">
                        <thead class="bg-slate-900 text-slate-300 uppercase">
                            <tr>
                                <th class="px-3 py-2">Entregable</th>
                                <th class="px-3 py-2">Categoría</th>
                                <th class="px-3 py-2">Fecha límite</th>
                                <th class="px-3 py-2">Responsable</th>
                                <th class="px-3 py-2">Estado</th>
                                <th class="px-3 py-2">Observaciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${tablero.map((item) => `
                                <tr class="border-b border-slate-800/70">
                                    <td class="px-3 py-2 font-medium text-slate-200">${escaparHtml(item.tipo || '')}</td>
                                    <td class="px-3 py-2">${escaparHtml(item.categoria || '')}</td>
                                    <td class="px-3 py-2">${escaparHtml(item.fecha_limite || '')}</td>
                                    <td class="px-3 py-2">${escaparHtml(item.responsable || '')}</td>
                                    <td class="px-3 py-2 ${estadoEntregableClase(item.estado)}">${escaparHtml(item.estado || '')}</td>
                                    <td class="px-3 py-2">${escaparHtml(item.observaciones || '')}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        })
        .catch(() => {
            contenedor.innerHTML = '<p>No se pudieron cargar los entregables.</p>';
        });
}

function subirEntregableOperacion() {
    const input = document.getElementById('input-entregable');
    const file = input.files[0];
    const error = validarArchivo(file, allowedDocumentExtensions, 50);
    if (error) {
        mostrarMensaje('entregable-message', error, 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('tipo', document.getElementById('entregable-tipo').value);
    formData.append('periodo', document.getElementById('entregable-periodo').value || new Date().toISOString().slice(0, 7));
    formData.append('unidad', document.getElementById('entregable-unidad').value.trim());
    formData.append('fecha_limite', document.getElementById('entregable-fecha-limite')?.value || '');
    formData.append('responsable', document.getElementById('entregable-responsable')?.value.trim() || '');
    formData.append('categoria', document.getElementById('entregable-categoria')?.value.trim() || '');
    formData.append('observaciones', document.getElementById('entregable-observaciones')?.value.trim() || '');

    fetch(`${backendUrl}/api/entregables-operacion`, { method: 'POST', body: formData })
        .then(manejarRespuestaJson)
        .then((data) => {
            mostrarMensaje('entregable-message', data.message, 'success');
            input.value = '';
            fetchEntregablesOperacion();
            evaluarOperacionICBF(false);
        })
        .catch((error) => {
            mostrarMensaje('entregable-message', error.message || 'Error al cargar entregable.', 'error');
        });
}

function renderCumplimiento(data) {
    if (!data) return;
    document.getElementById('cumplimiento-general').innerText = `${data.cumplimiento_general || 0}%`;
    document.getElementById('cumplimiento-beneficiarios').innerText = data.indicadores?.beneficiarios_activos || 0;
    document.getElementById('cumplimiento-retiro').innerText = data.indicadores?.edad_retiro || 0;
    document.getElementById('cumplimiento-nutricion').innerText = data.indicadores?.peso_talla_vencido || 0;

    const componentes = document.getElementById('componentes-cumplimiento');
    componentes.innerHTML = Object.entries(data.componentes || {}).map(([nombre, valor]) => `
        <div class="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <p class="text-xs text-slate-400">${nombre}</p>
            <p class="mt-2 text-2xl font-bold ${valor >= 80 ? 'text-emerald-400' : valor >= 50 ? 'text-amber-400' : 'text-rose-400'}">${valor}%</p>
        </div>
    `).join('');

    const matriz = document.getElementById('matriz-estandares');
    matriz.innerHTML = (data.matriz_estandares || []).map((item) => `
        <tr class="hover:bg-slate-900/50">
            <td class="px-4 py-3 text-slate-200">${item.estandar}</td>
            <td class="px-4 py-3">${item.cumple ? '<span class="text-emerald-400">Si</span>' : '<span class="text-rose-400">No</span>'}</td>
            <td class="px-4 py-3">${item.evidencia}</td>
        </tr>
    `).join('');

    const incumplimientos = document.getElementById('lista-incumplimientos');
    if (!Array.isArray(data.incumplimientos) || data.incumplimientos.length === 0) {
        incumplimientos.innerHTML = '<p class="text-emerald-400">Sin incumplimientos detectados.</p>';
        return;
    }
    incumplimientos.innerHTML = data.incumplimientos.map((item) => `
        <div class="rounded-xl border border-rose-500/20 bg-rose-500/10 p-3">
            <p class="font-medium text-rose-300">${item.tipo}</p>
            <p class="text-slate-300">${item.detalle}</p>
        </div>
    `).join('');
}

function evaluarOperacionICBF(guardar = true) {
    fetch(`${backendUrl}/api/cumplimiento/evaluar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    })
        .then(manejarRespuestaJson)
        .then(renderCumplimiento)
        .catch((error) => {
            console.error('Error al evaluar cumplimiento', error);
            if (guardar) {
                alert(error.message || 'Error al evaluar la operacion.');
            }
        });
}

function preguntarAsistenteICBF() {
    const pregunta = document.getElementById('asistente-pregunta').value.trim();
    if (!pregunta) return;
    const respuesta = document.getElementById('asistente-respuesta');
    respuesta.innerText = 'Consultando documentos institucionales...';

    fetch(`${backendUrl}/api/asistente-icbf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pregunta })
    })
        .then(manejarRespuestaJson)
        .then((data) => {
            const fuentes = (data.fuentes || []).map(f => `${f.tipo}: ${f.titulo} v${f.version}`).join(' | ');
            respuesta.innerText = fuentes ? `${data.respuesta}\n\nFuente: ${fuentes}` : data.respuesta;
        })
        .catch((error) => {
            respuesta.innerText = error.message || 'Error al consultar asistente.';
        });
}

function generarInformeICBF() {
    fetch(`${backendUrl}/api/informes/supervision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    })
        .then(manejarRespuestaJson)
        .then((data) => {
            evaluarOperacionICBF(false);
            descargarArchivoAutenticado(`${backendUrl}${data.url}`)
                .catch((error) => alert(error.message || 'No se pudo descargar el informe ICBF.'));
        })
        .catch((error) => {
            alert(error.message || 'Error al generar informe ICBF.');
        });
}


function periodoMesActual() {
    return new Date().toISOString().slice(0, 7);
}

function inicializarCuentasCobro() {
    const mes = document.getElementById('cuenta-mes');
    if (mes && !mes.value) mes.value = periodoMesActual();
    cargarCuentasCobro();
}

function cargarCuentasCobro() {
    const plantillasBody = document.getElementById('cuentas-plantillas-list');
    const generadasBody = document.getElementById('cuentas-generadas-list');
    if (!plantillasBody && !generadasBody) return;

    fetch(`${backendUrl}/api/cuentas-cobro/plantillas`)
        .then(manejarRespuestaJson)
        .then(data => {
            const plantillas = data.plantillas || [];
            if (plantillasBody) {
                plantillasBody.innerHTML = plantillas.length ? plantillas.map(p => `
                    <tr class="hover:bg-slate-900/50">
                        <td class="px-4 py-3 text-slate-200">${escaparHtml(p.docente_nombre || '')}</td>
                        <td class="px-4 py-3">${escaparHtml(p.unidad || '')}</td>
                        <td class="px-4 py-3 text-xs">${escaparHtml(p.nombre_original || '')}</td>
                    </tr>
                `).join('') : '<tr><td colspan="3" class="px-4 py-8 text-center text-slate-500">No hay plantillas cargadas.</td></tr>';
            }
        })
        .catch(error => mostrarMensaje('cuentas-message', error.message || 'No se pudieron cargar plantillas.', 'error'));

    const periodo = document.getElementById('cuenta-mes')?.value || '';
    fetch(`${backendUrl}/api/cuentas-cobro?periodo=${encodeURIComponent(periodo)}`)
        .then(manejarRespuestaJson)
        .then(data => {
            const generadas = data.generadas || [];
            if (generadasBody) {
                generadasBody.innerHTML = generadas.length ? generadas.map(g => `
                    <tr class="hover:bg-slate-900/50">
                        <td class="px-4 py-3 text-slate-200">${escaparHtml(g.docente_nombre || '')}</td>
                        <td class="px-4 py-3">${escaparHtml(g.periodo || '')}</td>
                        <td class="px-4 py-3">${escaparHtml(g.numero_cuenta || '')}</td>
                        <td class="px-4 py-3"><button onclick="descargarArchivoGenerado('${escaparHtml(g.nombre_archivo || '')}')" class="text-cyan-300 hover:text-cyan-200 text-xs">Descargar</button></td>
                    </tr>
                `).join('') : '<tr><td colspan="4" class="px-4 py-8 text-center text-slate-500">No hay cuentas generadas para el periodo.</td></tr>';
            }
        })
        .catch(error => mostrarMensaje('cuentas-message', error.message || 'No se pudieron cargar cuentas generadas.', 'error'));
}

function subirPlantillasCuentaCobro() {
    const input = document.getElementById('cuenta-template-file');
    const file = input?.files?.[0];
    if (!file) {
        mostrarMensaje('cuentas-message', 'Selecciona un DOCX o ZIP con cuentas de cobro.', 'error');
        return;
    }
    const nombre = file.name.toLowerCase();
    if (!nombre.endsWith('.docx') && !nombre.endsWith('.zip')) {
        mostrarMensaje('cuentas-message', 'Solo se aceptan .docx o .zip para cuentas de cobro.', 'error');
        return;
    }
    const formData = new FormData();
    formData.append('file', file);
    mostrarCargando('Subiendo plantillas de cuenta de cobro...');
    fetch(`${backendUrl}/api/cuentas-cobro/plantillas`, { method: 'POST', body: formData })
        .then(manejarRespuestaJson)
        .then(data => {
            ocultarCargando();
            mostrarMensaje('cuentas-message', data.message || 'Plantillas cargadas.', 'success');
            input.value = '';
            cargarCuentasCobro();
        })
        .catch(error => {
            ocultarCargando();
            mostrarMensaje('cuentas-message', error.message || 'No se pudieron subir las plantillas.', 'error');
        });
}

function generarCuentasCobro() {
    const periodo = document.getElementById('cuenta-mes')?.value || periodoMesActual();
    const [anio, mes] = periodo.split('-');
    const payload = {
        anio: Number(anio),
        mes: Number(mes),
        ciudad: document.getElementById('cuenta-ciudad')?.value || 'Ciudad de prueba',
        numero_inicial: document.getElementById('cuenta-numero-inicial')?.value || ''
    };
    mostrarCargando('Generando cuentas de cobro del mes...');
    fetch(`${backendUrl}/api/cuentas-cobro/generar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(manejarRespuestaJson)
        .then(data => {
            ocultarCargando();
            mostrarMensaje('cuentas-message', data.message || 'Cuentas generadas.', 'success');
            cargarCuentasCobro();
        })
        .catch(error => {
            ocultarCargando();
            mostrarMensaje('cuentas-message', error.message || 'No se pudieron generar las cuentas.', 'error');
        });
}

function descargarArchivoGenerado(nombre) {
    if (!nombre) return;
    descargarArchivoAutenticado(`${backendUrl}/api/descargar-archivo/${encodeURIComponent(nombre)}`).catch(error => alert(error.message));
}

function inicializarRelacionMes() {
    const periodo = document.getElementById('relacion-periodo');
    if (periodo && !periodo.value) periodo.value = periodoMesActual();
}

function generarRelacionMes() {
    const periodo = document.getElementById('relacion-periodo')?.value || periodoMesActual();
    const [anio, mes] = periodo.split('-');
    mostrarCargando('Generando relación del mes...');
    fetch(`${backendUrl}/api/relacion-mes/generar?anio=${encodeURIComponent(anio)}&mes=${encodeURIComponent(mes)}`)
        .then(manejarRespuestaJson)
        .then(data => {
            ocultarCargando();
            mostrarMensaje('relacion-message', data.message || 'Relación generada.', 'success');
            const cont = document.getElementById('relacion-descarga');
            if (cont && data.archivo) {
                cont.innerHTML = `<button onclick="descargarArchivoGenerado('${escaparHtml(data.archivo)}')" class="rounded-xl bg-emerald-600 hover:bg-emerald-500 px-4 py-2 text-sm font-medium text-white">Descargar ${escaparHtml(data.archivo)}</button>`;
            }
        })
        .catch(error => {
            ocultarCargando();
            mostrarMensaje('relacion-message', error.message || 'No se pudo generar la relación del mes.', 'error');
        });
}


const adminState = {
    fundaciones: [],
    usuarios: [],
    roles: [],
    editandoFundacionId: null,
    editandoUsuarioId: null,
};

function adminEsSuperadmin() {
    return String((usuarioActual || authUser() || {}).rol || '').toUpperCase() === 'SUPERADMIN';
}

function adminValor(id, value) {
    const element = document.getElementById(id);
    if (!element) return;
    if (element.type === 'checkbox') element.checked = Boolean(value);
    else element.value = value == null ? '' : String(value);
}

function adminObtener(id) {
    const element = document.getElementById(id);
    if (!element) return '';
    return element.type === 'checkbox' ? element.checked : element.value;
}

function adminResumenDependencias(data) {
    const dependencies = data?.dependencias || {};
    const details = Array.isArray(dependencies.detalle) ? dependencies.detalle.slice(0, 6) : [];
    const detailText = details.map(item => `${item.tabla}: ${item.registros}`).join('\n');
    return `Registros relacionados detectados: ${Number(dependencies.total || 0)}${detailText ? `\n\nPrincipales:\n${detailText}` : ''}`;
}

async function cargarAdministracion() {
    try {
        const [foundationResponse, userResponse] = await Promise.all([
            fetch(`${backendUrl}/api/fundaciones`).then(manejarRespuestaJson),
            fetch(`${backendUrl}/api/usuarios`).then(manejarRespuestaJson)
        ]);
        adminState.fundaciones = foundationResponse.fundaciones || [];
        adminState.usuarios = userResponse.usuarios || [];
        adminState.roles = userResponse.roles || [];
        const foundationPanel = document.getElementById('fundacion-form-panel');
        foundationPanel?.classList.toggle('hidden', !adminEsSuperadmin());
        renderFundaciones(adminState.fundaciones);
        renderUsuarios(adminState.usuarios, adminState.fundaciones, adminState.roles);
    } catch (error) {
        mostrarMensaje('admin-message', error.message || 'No se pudo cargar administración.', 'error');
    }
}

function renderFundaciones(fundaciones) {
    const tbody = document.getElementById('fundaciones-list');
    const select = document.getElementById('usuario-fundacion');
    if (select) {
        const active = fundaciones.filter(item => String(item.estado || '').toUpperCase() === 'ACTIVA');
        const inactive = fundaciones.filter(item => String(item.estado || '').toUpperCase() !== 'ACTIVA');
        const activeOptions = active.map(item => `<option value="${item.id}">${escaparHtml(item.nombre)}</option>`).join('');
        const inactiveOptions = inactive.map(item => {
            const estado = String(item.estado || 'INACTIVA').toUpperCase();
            return `<option value="${item.id}" disabled>${escaparHtml(item.nombre)} — ${escaparHtml(estado)}</option>`;
        }).join('');
        const emptyOption = active.length ? '' : '<option value="">No hay fundaciones activas disponibles</option>';
        select.innerHTML = `${emptyOption}${activeOptions}${inactiveOptions}`;
        select.disabled = !adminEsSuperadmin();
    }
    if (!tbody) return;
    tbody.innerHTML = fundaciones.length ? fundaciones.map(foundation => {
        const state = String(foundation.estado || 'ACTIVA').toUpperCase();
        const deleted = state === 'ELIMINADA';
        const currentTenant = Number((usuarioActual || authUser() || {}).fundacion_id || 0) === Number(foundation.id);
        const actions = adminEsSuperadmin() ? [
            !deleted ? `<button onclick="editarFundacion(${foundation.id})" class="text-cyan-300 text-xs hover:underline">Editar</button>` : '',
            state === 'ACTIVA'
                ? `<button ${currentTenant ? 'disabled title="No puedes suspender tu fundación actual" class="text-slate-600 text-xs cursor-not-allowed"' : `onclick="cambiarEstadoFundacion(${foundation.id}, 'SUSPENDIDA')" class="text-amber-300 text-xs hover:underline"`}>Suspender</button>`
                : `<button onclick="cambiarEstadoFundacion(${foundation.id}, 'ACTIVA')" class="text-emerald-300 text-xs hover:underline">${deleted ? 'Restaurar' : 'Activar'}</button>`,
            !deleted && !currentTenant
                ? `<button onclick="eliminarFundacion(${foundation.id})" class="text-rose-300 text-xs hover:underline">Eliminar</button>`
                : '',
        ].filter(Boolean).join(' ') : '<span class="text-slate-600">Solo lectura</span>';
        return `
            <tr class="border-b border-slate-800 ${deleted ? 'opacity-60' : ''}">
                <td class="px-3 py-2 font-medium text-slate-200">${escaparHtml(foundation.nombre)}</td>
                <td class="px-3 py-2">${escaparHtml(foundation.nit || '')}</td>
                <td class="px-3 py-2">${escaparHtml(foundation.plan || '')}</td>
                <td class="px-3 py-2">${escaparHtml(state)}</td>
                <td class="px-3 py-2">${escaparHtml(foundation.fecha_vencimiento || '')}</td>
                <td class="px-3 py-2 space-x-2 whitespace-nowrap">${actions}</td>
            </tr>`;
    }).join('') : '<tr><td colspan="6" class="px-3 py-6 text-center text-slate-500">Sin fundaciones.</td></tr>';
}

function renderUsuarios(users, foundations, roles) {
    const tbody = document.getElementById('usuarios-list');
    const roleSelect = document.getElementById('usuario-rol');
    if (roleSelect) {
        const allowedRoles = adminEsSuperadmin() ? roles : roles.filter(role => role !== 'SUPERADMIN');
        roleSelect.innerHTML = allowedRoles.map(role => `<option value="${role}">${role}</option>`).join('');
    }
    if (!tbody) return;
    const currentUserId = Number((usuarioActual || authUser() || {}).id || 0);
    tbody.innerHTML = users.length ? users.map(user => {
        const state = String(user.estado || (user.activo ? 'ACTIVO' : 'INACTIVO')).toUpperCase();
        const active = Number(user.activo || 0) === 1 && state === 'ACTIVO';
        const deleted = state === 'ELIMINADO';
        const self = Number(user.id) === currentUserId;
        const actions = [
            `<button onclick="editarUsuario(${user.id})" class="text-cyan-300 text-xs hover:underline">Editar</button>`,
            !self && !deleted
                ? (active
                    ? `<button onclick="cambiarEstadoUsuario(${user.id}, false)" class="text-amber-300 text-xs hover:underline">Desactivar</button>`
                    : `<button onclick="cambiarEstadoUsuario(${user.id}, true)" class="text-emerald-300 text-xs hover:underline">Activar</button>`)
                : (deleted ? `<button onclick="cambiarEstadoUsuario(${user.id}, true)" class="text-emerald-300 text-xs hover:underline">Restaurar</button>` : ''),
            !self && !deleted
                ? `<button onclick="restablecerPasswordUsuario(${user.id})" class="text-violet-300 text-xs hover:underline">Restablecer clave</button>`
                : '',
            !self && !deleted
                ? `<button onclick="eliminarUsuario(${user.id})" class="text-rose-300 text-xs hover:underline">Eliminar</button>`
                : '',
        ].filter(Boolean).join(' ');
        return `
            <tr class="border-b border-slate-800 ${deleted ? 'opacity-60' : ''}">
                <td class="px-3 py-2 font-medium text-slate-200">${escaparHtml(user.username)}</td>
                <td class="px-3 py-2">${escaparHtml(user.email)}</td>
                <td class="px-3 py-2">${escaparHtml(user.rol)}</td>
                <td class="px-3 py-2">${escaparHtml(user.fundacion_nombre || '')}</td>
                <td class="px-3 py-2">${escaparHtml(state)}${user.debe_cambiar_password ? ' · CAMBIO PENDIENTE' : ''}</td>
                <td class="px-3 py-2 space-x-2 whitespace-nowrap">${actions}</td>
            </tr>`;
    }).join('') : '<tr><td colspan="6" class="px-3 py-6 text-center text-slate-500">Sin usuarios.</td></tr>';
}

function limpiarFormularioFundacion() {
    adminState.editandoFundacionId = null;
    ['fundacion-nombre', 'fundacion-nit', 'fundacion-representante', 'fundacion-email', 'fundacion-telefono',
     'fundacion-vencimiento', 'fundacion-direccion', 'fundacion-municipio', 'fundacion-departamento',
     'fundacion-observaciones'].forEach(id => adminValor(id, ''));
    adminValor('fundacion-plan', 'PRUEBA');
    const title = document.getElementById('fundacion-form-title');
    const button = document.getElementById('fundacion-save-button');
    if (title) title.textContent = 'Crear fundación';
    if (button) button.textContent = 'Guardar fundación';
    document.getElementById('fundacion-cancel-button')?.classList.add('hidden');
}

function cancelarEdicionFundacion() {
    limpiarFormularioFundacion();
}

function editarFundacion(id) {
    const foundation = adminState.fundaciones.find(item => Number(item.id) === Number(id));
    if (!foundation) return;
    adminState.editandoFundacionId = Number(id);
    adminValor('fundacion-nombre', foundation.nombre);
    adminValor('fundacion-nit', foundation.nit);
    adminValor('fundacion-representante', foundation.representante);
    adminValor('fundacion-email', foundation.email);
    adminValor('fundacion-telefono', foundation.telefono);
    adminValor('fundacion-plan', foundation.plan || 'PRUEBA');
    adminValor('fundacion-vencimiento', foundation.fecha_vencimiento);
    adminValor('fundacion-direccion', foundation.direccion);
    adminValor('fundacion-municipio', foundation.municipio);
    adminValor('fundacion-departamento', foundation.departamento);
    adminValor('fundacion-observaciones', foundation.observaciones);
    const title = document.getElementById('fundacion-form-title');
    const button = document.getElementById('fundacion-save-button');
    if (title) title.textContent = `Editar fundación: ${foundation.nombre}`;
    if (button) button.textContent = 'Guardar cambios';
    document.getElementById('fundacion-cancel-button')?.classList.remove('hidden');
    document.getElementById('fundacion-form-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function guardarFundacion() {
    const data = {
        nombre: String(adminObtener('fundacion-nombre') || '').trim(),
        nit: String(adminObtener('fundacion-nit') || '').trim(),
        representante: String(adminObtener('fundacion-representante') || '').trim(),
        email: String(adminObtener('fundacion-email') || '').trim(),
        telefono: String(adminObtener('fundacion-telefono') || '').trim(),
        plan: adminObtener('fundacion-plan'),
        fecha_vencimiento: adminObtener('fundacion-vencimiento') || null,
        direccion: String(adminObtener('fundacion-direccion') || '').trim(),
        municipio: String(adminObtener('fundacion-municipio') || '').trim(),
        departamento: String(adminObtener('fundacion-departamento') || '').trim(),
        observaciones: String(adminObtener('fundacion-observaciones') || '').trim(),
        estado: 'ACTIVA'
    };
    if (!data.nombre) {
        mostrarMensaje('admin-message', 'Escribe el nombre de la fundación.', 'error');
        return;
    }
    const editingId = adminState.editandoFundacionId;
    if (editingId) {
        const current = adminState.fundaciones.find(item => Number(item.id) === Number(editingId));
        data.estado = current?.estado || 'ACTIVA';
        data.fecha_inicio = current?.fecha_inicio || null;
    }
    try {
        const response = await fetch(editingId ? `${backendUrl}/api/fundaciones/${editingId}` : `${backendUrl}/api/fundaciones`, {
            method: editingId ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const json = await manejarRespuestaJson(response);
        mostrarMensaje('admin-message', json.message || 'Fundación guardada.', 'success');
        limpiarFormularioFundacion();
        await cargarAdministracion();
    } catch (error) {
        if (error?.data?.code === 'FUNDACION_EXISTENTE' && error.data.fundacion) {
            await cargarAdministracion();
            const existing = error.data.fundacion;
            if (error.data.reutilizable) {
                adminValor('usuario-fundacion', existing.id);
                mostrarMensaje(
                    'admin-message',
                    `${existing.nombre} ya estaba registrada y quedó seleccionada para crear usuarios.`,
                    'success'
                );
            } else {
                mostrarMensaje(
                    'admin-message',
                    `${existing.nombre} ya existe con estado ${String(existing.estado || 'INACTIVA').toUpperCase()}. Reactívala desde la lista; no debes crearla nuevamente.`,
                    'error'
                );
            }
            return;
        }
        mostrarMensaje('admin-message', error.message || 'No se pudo guardar la fundación.', 'error');
    }
}

async function crearFundacion() { return guardarFundacion(); }

async function cambiarEstadoFundacion(id, state) {
    const action = state === 'ACTIVA' ? 'activar' : 'suspender';
    if (!confirm(`¿Confirmas ${action} esta fundación?`)) return;
    try {
        const response = await fetch(`${backendUrl}/api/fundaciones/${id}?estado=${encodeURIComponent(state)}`, { method: 'DELETE' });
        const json = await manejarRespuestaJson(response);
        mostrarMensaje('admin-message', json.message || 'Estado actualizado.', 'success');
        await cargarAdministracion();
    } catch (error) {
        mostrarMensaje('admin-message', error.message || 'No se pudo cambiar el estado.', 'error');
    }
}

async function eliminarFundacion(id) {
    try {
        const dependencyData = await fetch(`${backendUrl}/api/fundaciones/${id}/dependencias`).then(manejarRespuestaJson);
        const foundation = dependencyData.fundacion || {};
        const confirmation = `${adminResumenDependencias(dependencyData)}\n\nLa eliminación será lógica: conservará la información para auditoría, cerrará sesiones y bloqueará la fundación.\n\n¿Eliminar ${foundation.nombre || 'esta fundación'}?`;
        if (!confirm(confirmation)) return;
        const response = await fetch(`${backendUrl}/api/fundaciones/${id}?accion=eliminar`, { method: 'DELETE' });
        const json = await manejarRespuestaJson(response);
        mostrarMensaje('admin-message', json.message || 'Fundación eliminada.', 'success');
        await cargarAdministracion();
    } catch (error) {
        mostrarMensaje('admin-message', error.message || 'No se pudo eliminar la fundación.', 'error');
    }
}

function limpiarFormularioUsuario() {
    adminState.editandoUsuarioId = null;
    ['usuario-nombre', 'usuario-telefono', 'usuario-username', 'usuario-email', 'usuario-password'].forEach(id => adminValor(id, ''));
    adminValor('usuario-forzar-cambio', false);
    const title = document.getElementById('usuario-form-title');
    const button = document.getElementById('usuario-save-button');
    if (title) title.textContent = 'Crear usuario';
    if (button) button.textContent = 'Guardar usuario';
    document.getElementById('usuario-cancel-button')?.classList.add('hidden');
}

function cancelarEdicionUsuario() {
    limpiarFormularioUsuario();
}

function editarUsuario(id) {
    const user = adminState.usuarios.find(item => Number(item.id) === Number(id));
    if (!user) return;
    adminState.editandoUsuarioId = Number(id);
    adminValor('usuario-fundacion', user.fundacion_id);
    adminValor('usuario-rol', user.rol);
    adminValor('usuario-nombre', user.nombre_completo);
    adminValor('usuario-telefono', user.telefono);
    adminValor('usuario-username', user.username);
    adminValor('usuario-email', user.email);
    adminValor('usuario-password', '');
    adminValor('usuario-forzar-cambio', Boolean(user.debe_cambiar_password));
    const title = document.getElementById('usuario-form-title');
    const button = document.getElementById('usuario-save-button');
    if (title) title.textContent = `Editar usuario: ${user.username}`;
    if (button) button.textContent = 'Guardar cambios';
    document.getElementById('usuario-cancel-button')?.classList.remove('hidden');
    document.getElementById('usuario-form-title')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

async function guardarUsuario() {
    const editingId = adminState.editandoUsuarioId;
    const current = adminState.usuarios.find(item => Number(item.id) === Number(editingId));
    const password = String(adminObtener('usuario-password') || '');
    const data = {
        username: String(adminObtener('usuario-username') || '').trim(),
        email: String(adminObtener('usuario-email') || '').trim(),
        rol: adminObtener('usuario-rol'),
        fundacion_id: Number(adminObtener('usuario-fundacion') || 0),
        nombre_completo: String(adminObtener('usuario-nombre') || '').trim(),
        telefono: String(adminObtener('usuario-telefono') || '').trim(),
        debe_cambiar_password: Boolean(adminObtener('usuario-forzar-cambio')),
    };
    if (!editingId || password) data.password = password;
    if (editingId) {
        data.activo = Number(current?.activo || 0);
        data.estado = current?.estado || (data.activo ? 'ACTIVO' : 'INACTIVO');
    }
    if (!data.username || !data.email || (!editingId && !password)) {
        mostrarMensaje('admin-message', 'Usuario, correo y contraseña inicial son obligatorios.', 'error');
        return;
    }
    try {
        const response = await fetch(editingId ? `${backendUrl}/api/usuarios/${editingId}` : `${backendUrl}/api/usuarios`, {
            method: editingId ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const json = await manejarRespuestaJson(response);
        mostrarMensaje('admin-message', json.message || 'Usuario guardado.', 'success');
        limpiarFormularioUsuario();
        await cargarAdministracion();
    } catch (error) {
        mostrarMensaje('admin-message', error.message || 'No se pudo guardar el usuario.', 'error');
    }
}

async function crearUsuario() { return guardarUsuario(); }

async function cambiarEstadoUsuario(id, activate) {
    const action = activate ? 'activar' : 'desactivar';
    if (!confirm(`¿Confirmas ${action} este usuario?`)) return;
    try {
        let response;
        if (activate) {
            const user = adminState.usuarios.find(item => Number(item.id) === Number(id));
            response = await fetch(`${backendUrl}/api/usuarios/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: user.username,
                    email: user.email,
                    rol: user.rol,
                    fundacion_id: user.fundacion_id,
                    nombre_completo: user.nombre_completo,
                    telefono: user.telefono,
                    activo: 1,
                    estado: 'ACTIVO'
                })
            });
        } else {
            response = await fetch(`${backendUrl}/api/usuarios/${id}?accion=desactivar&estado=INACTIVO`, { method: 'DELETE' });
        }
        const json = await manejarRespuestaJson(response);
        mostrarMensaje('admin-message', json.message || 'Estado de usuario actualizado.', 'success');
        await cargarAdministracion();
    } catch (error) {
        mostrarMensaje('admin-message', error.message || 'No se pudo cambiar el estado del usuario.', 'error');
    }
}

async function desactivarUsuario(id) { return cambiarEstadoUsuario(id, false); }

async function eliminarUsuario(id) {
    try {
        const dependencyData = await fetch(`${backendUrl}/api/usuarios/${id}/dependencias`).then(manejarRespuestaJson);
        const user = dependencyData.usuario || {};
        const confirmation = `${adminResumenDependencias(dependencyData)}\n\nLa eliminación será lógica: conservará la trazabilidad y cerrará todas las sesiones.\n\n¿Eliminar al usuario ${user.username || ''}?`;
        if (!confirm(confirmation)) return;
        const response = await fetch(`${backendUrl}/api/usuarios/${id}?accion=eliminar`, { method: 'DELETE' });
        const json = await manejarRespuestaJson(response);
        mostrarMensaje('admin-message', json.message || 'Usuario eliminado.', 'success');
        await cargarAdministracion();
    } catch (error) {
        mostrarMensaje('admin-message', error.message || 'No se pudo eliminar el usuario.', 'error');
    }
}

async function restablecerPasswordUsuario(id) {
    const user = adminState.usuarios.find(item => Number(item.id) === Number(id));
    if (!user) return;
    const reactivate = !(Number(user.activo || 0) === 1 && String(user.estado || '').toUpperCase() === 'ACTIVO');
    const message = reactivate
        ? `Se generará una contraseña temporal, se reactivará ${user.username} y deberá cambiarla al ingresar. ¿Continuar?`
        : `Se generará una contraseña temporal para ${user.username}, se cerrarán sus sesiones y deberá cambiarla al ingresar. ¿Continuar?`;
    if (!confirm(message)) return;
    try {
        const response = await fetch(`${backendUrl}/api/usuarios/${id}/restablecer-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reactivar: reactivate })
        });
        const json = await manejarRespuestaJson(response);
        if (json.temporary_password) mostrarCredencialTemporal(json.temporary_password);
        mostrarMensaje('admin-message', json.message || 'Contraseña restablecida.', 'success');
        await cargarAdministracion();
    } catch (error) {
        mostrarMensaje('admin-message', error.message || 'No se pudo restablecer la contraseña.', 'error');
    }
}

function mostrarCredencialTemporal(password) {
    const panel = document.getElementById('admin-temp-password-panel');
    const input = document.getElementById('admin-temp-password');
    if (input) input.value = password || '';
    panel?.classList.remove('hidden');
    panel?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function cerrarCredencialTemporal() {
    const input = document.getElementById('admin-temp-password');
    if (input) input.value = '';
    document.getElementById('admin-temp-password-panel')?.classList.add('hidden');
}

function copiarCredencialTemporal() {
    const input = document.getElementById('admin-temp-password');
    if (!input?.value) return;
    navigator.clipboard?.writeText(input.value).then(() => {
        mostrarMensaje('admin-message', 'Contraseña temporal copiada. Entrégala por un canal seguro.', 'success');
    }).catch(() => {
        input.select();
        document.execCommand('copy');
        mostrarMensaje('admin-message', 'Contraseña temporal copiada.', 'success');
    });
}

window.addEventListener('DOMContentLoaded', initApp);
