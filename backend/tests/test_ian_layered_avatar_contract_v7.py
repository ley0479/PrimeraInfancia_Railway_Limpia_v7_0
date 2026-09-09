from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    controller = (ROOT / "frontend/js/liam/liam-controller.js").read_text(encoding="utf-8")
    renderer = (ROOT / "frontend/js/liam/ian-avatar-renderer.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend/css/ian-avatar.css").read_text(encoding="utf-8")
    index = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    state = (ROOT / "frontend/js/liam/liam-state-machine.js").read_text(encoding="utf-8")
    movement = (ROOT / "frontend/js/liam/liam-movement-controller.js").read_text(encoding="utf-8")
    tour = (ROOT / "frontend/js/liam/elian-platform-tour.js").read_text(encoding="utf-8")
    orchestrator = (ROOT / "frontend/js/liam/liam-animation-orchestrator.js").read_text(encoding="utf-8")
    speech = (ROOT / "frontend/js/lia-assistant/speech-controller.js").read_text(encoding="utf-8")
    lips = (ROOT / "frontend/js/liam/liam-lip-sync.js").read_text(encoding="utf-8")
    guard = (ROOT / "frontend/js/liam/ian-visibility-guard.js").read_text(encoding="utf-8")

    require("mountIan();const r=await fetch" in controller, "El arranque no invoca directamente el montaje corregido de IAN")
    require("if(!authToken)throw new Error('AUTH_PENDING');mountIan();const r=await fetch" in controller, "IAN todavía espera al endpoint antes de hacerse visible")
    require("bootIan" in controller and "cache:'no-store'" in controller, "Falta el arranque resistente a caché")
    require("headers:headers()" in controller, "La configuración protegida de IAN se consulta sin autenticación")
    require("AUTH_PENDING" in controller and "setTimeout(()=>{state.booting=false;bootIan()}" in controller, "IAN no reintenta después del inicio de sesión")
    require("[sessionStorage,localStorage]" in controller, "IAN no busca la sesión en los dos almacenamientos usados por la plataforma")
    for key in ("authToken", "accessToken", "primeraInfanciaToken", "primeraInfanciaAuthToken"):
        require(key in controller, f"IAN no reconoce la clave de sesión compatible: {key}")
    require("ian-launcher-avatar" in controller, "Falta la silueta única del lanzador")
    require("render('#liam-avatar-wrap'" in controller, "El panel no reutiliza el avatar del lanzador")
    require("lia-human-v1.png" in controller, "No se restauró la ilustración 2D institucional anterior")
    require("ian-avatar-rig" in renderer and "trustedAsset" in renderer, "La identidad visual no está montada en el rig validado")
    require("rigMarkup" in renderer and "clipPath" in renderer and "mask" in renderer, "El avatar no separa cabeza, cuerpo y brazos")
    require("avatar_asset_path" in controller, "La selección visual guardada no llega al avatar 2D")
    require("liam-mouth-motion" not in controller[controller.index("function mountIan"):controller.index("function applyIanVisual")], "La interfaz activa todavía superpone una boca")
    for layer in ("ian-head-layer", "ian-mouth-layer", "ian-arm-left", "ian-arm-right", "ian-eyes"):
        require(layer in renderer, f"Falta capa SVG real: {layer}")
    require("ian-eyelids" in renderer, "Falta el parpadeo independiente del rostro aprobado")
    require("data-gender" in renderer and "data-variant" in renderer, "El SVG no admite género y variante")
    require("background:transparent!important" in css and "box-shadow:none!important" in css, "El lanzador todavía dibuja un cuadro")
    require(".ian-mouth-open" in css and "[data-state=speaking]" in css, "La boca interna no responde al estado de voz")
    require("ian-wave" in css and "ian-point-left" in css and "ian-point-right" in css, "Los brazos no tienen gestos reales")
    require("[data-state=pointing_left] .ian-avatar-rig .ian-arm-left" in css, "El objetivo izquierdo no activa el brazo visual izquierdo")
    require("[data-state=pointing_right] .ian-avatar-rig .ian-arm-right" in css, "El objetivo derecho no activa el brazo visual derecho")
    require("ian-avatar.css" in index, "La hoja correctiva no llega al navegador")
    require(index.index("ian-avatar-renderer.js") < index.index("liam-controller.js"), "El SVG no se carga antes del controlador")
    require(index.index("liam-state-machine.js") < index.index("liam-controller.js"), "El estado básico no se carga antes del controlador")
    require("ian-visibility-guard.js" in index, "La guardia de visibilidad no llega al navegador")
    require("window.IAN_BOOT?.()" in guard and "ian-visibility-fallback" in guard, "La guardia no recupera un montaje fallido")
    require("app&&!app.classList.contains('hidden')" in guard, "La guardia depende únicamente del formato del token")
    require("removeFallback" in guard and "document.getElementById('liam-shell')" in guard, "La guardia puede duplicar el asistente")
    require("display','block','important'" in guard and "visibility','visible','important'" in guard, "La guardia no corrige ocultamiento CSS")
    require("'walking_up'" in state and "'walking_down'" in state and "'collapsed'" in state, "La máquina de estados está incompleta")
    require("avatar.animate" in movement and "getBoundingClientRect" in movement, "La caminata no mueve un elemento visible hacia el control")
    require("LIAM_SAFE_ZONES?.placement" in movement, "El movimiento no valida una zona segura")
    require("ian-tour-avatar" in movement and "pointer-events:none" in css, "El avatar del recorrido puede bloquear clics")
    require("LIAM_MOVEMENT?.moveToControl" in tour, "El recorrido automático no está conectado al movimiento")
    require(".ian-avatar-visual, .ian-avatar-svg" in orchestrator, "Los estados no alcanzan la imagen principal y el respaldo SVG")
    for motion in ("ian-image-breathe", "ian-image-greeting", "ian-image-thinking", "ian-image-speaking"):
        require(motion in css, f"Falta movimiento humanizado para imagen: {motion}")
    approved_face = ROOT / "frontend/assets/lia/elian-afro-institutional-female-v1.png"
    png = approved_face.read_bytes()
    require(png[:8] == b'\x89PNG\r\n\x1a\n' and png[25] == 6, "La identidad aprobada debe conservar transparencia RGBA real")
    for event in ("start", "audio-ready", "play", "pause", "resume", "end", "error", "boundary"):
        require(f"'{event}'" in speech, f"Falta evento de voz: {event}")
    require("LIAM_LIP_SYNC?.pause" in speech and "LIAM_LIP_SYNC?.resume" in speech, "Pausa y reanudación no controlan la boca")
    require("shapeFor" in lips and "ian:speech:viseme" in lips, "Falta el respaldo labial por formas internas")
    require("mode:'timed-text-fallback'" in lips, "No se declara honestamente el modo de sincronización disponible")
    print("IAN_LAYERED_AVATAR_CONTRACT_V7_PASS")


if __name__ == "__main__":
    main()
