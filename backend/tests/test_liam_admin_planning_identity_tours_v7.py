"""Contrato de recorridos administrativos y de identidad visual."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
read = lambda relative: (ROOT / relative).read_text(encoding="utf-8")
controls = read("frontend/js/liam/liam-control-registry.js")
anchors = read("frontend/js/liam/liam-anchor-registry.js")
tours = read("frontend/js/liam/liam-tour-engine.js")
controller = read("frontend/js/liam/liam-controller.js")

for tour_id in ("centro-planeacion.overview", "administracion.overview", "configuracion-institucional.overview"):
    assert tour_id in tours and tour_id in controller
for prefix in ("centro-planeacion.", "administracion.", "configuracion-institucional."):
    assert prefix in controls
for anchor in ("liam.anchor.planning", "liam.anchor.admin", "liam.anchor.identity"):
    assert anchor in anchors
assert "LIAM solo explica el formulario y nunca lo ejecuta" in tours
assert "identidad global como respaldo" in tours
assert "No se exponen contraseñas" in tours
assert ".click()" not in tours
print("LIAM_ADMIN_PLANNING_IDENTITY_TOURS_V7_PASS")
