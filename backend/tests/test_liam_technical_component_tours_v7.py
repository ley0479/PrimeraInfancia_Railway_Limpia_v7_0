"""Contrato de recorridos pedagógicos y psicosociales de LIAM."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
read = lambda relative: (ROOT / relative).read_text(encoding="utf-8")

controls = read("frontend/js/liam/liam-control-registry.js")
anchors = read("frontend/js/liam/liam-anchor-registry.js")
tours = read("frontend/js/liam/liam-tour-engine.js")
controller = read("frontend/js/liam/liam-controller.js")

for tour_id in ("planeacion-pedagogica.workflow", "gestion-pedagogica.overview", "componente-psicosocial.overview"):
    assert tour_id in tours and tour_id in controller

for prefix in ("planeacion-pedagogica.", "gestion-pedagogica.", "componente-psicosocial."):
    assert prefix in controls

assert "liam.anchor.pedagogy" in anchors
assert "liam.anchor.management" in anchors
assert "liam.anchor.psychosocial" in anchors
assert "diagnósticos automáticos" in tours
assert ".click()" not in tours

print("LIAM_TECHNICAL_COMPONENT_TOURS_V7_PASS")
