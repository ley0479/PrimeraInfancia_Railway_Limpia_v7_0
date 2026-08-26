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

    require("mount=mountIan" in controller, "La interfaz activa no usa el montaje corregido de IAN")
    require("ian-launcher-avatar" in controller, "Falta la silueta única del lanzador")
    require("IAN_AVATAR.render('#liam-avatar-wrap'" in controller, "El panel no reutiliza el avatar del lanzador")
    require("liam-mouth-motion" not in controller[controller.index("function mountIan"):controller.index("mount=mountIan")], "La interfaz activa todavía superpone una boca")
    for layer in ("ian-head-layer", "ian-mouth-layer", "ian-arm-left", "ian-arm-right", "ian-eyes"):
        require(layer in renderer, f"Falta capa SVG real: {layer}")
    require("data-gender" in renderer and "data-variant" in renderer, "El SVG no admite género y variante")
    require("background:transparent!important" in css and "box-shadow:none!important" in css, "El lanzador todavía dibuja un cuadro")
    require(".ian-mouth-open" in css and "[data-state=speaking]" in css, "La boca interna no responde al estado de voz")
    require("ian-wave" in css and "ian-point-left" in css and "ian-point-right" in css, "Los brazos no tienen gestos reales")
    require("ian-avatar.css" in index, "La hoja correctiva no llega al navegador")
    require("'walking_up'" in state and "'walking_down'" in state and "'collapsed'" in state, "La máquina de estados está incompleta")
    print("IAN_LAYERED_AVATAR_CONTRACT_V7_PASS")


if __name__ == "__main__":
    main()
